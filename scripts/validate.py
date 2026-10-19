#!/usr/bin/env python3
"""Validate the costing-master skill repository.

Checks:
- SKILL.md frontmatter (name, description, optional metadata.version)
- version consistency across SKILL.md, README.md and CHANGELOG.md
- all backtick-referenced repository paths exist
- all relative markdown links exist
- every workflow/template/reference/input-spec is listed in SKILL.md
- README reference tree matches the files on disk
- every workflow has a test case in test-cases/README.md
- every test case is listed and has expected/failure sections
- markdown tables have consistent column counts and no duplicate headings
- code fences are balanced
- Excel CSV templates exist with the expected UTF-8 BOM and headers
- no emoji icons in repository text files
- rule registry and task manifest checks are in scripts/check_rule_governance.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ERRORS: list[str] = []

EMOJI_PATTERN = re.compile(
    "[" + chr(0x1F000) + "-" + chr(0x1FAFF)
    + chr(0x2600) + "-" + chr(0x27BF)
    + chr(0x2B00) + "-" + chr(0x2BFF)
    + chr(0xFE0F) + "]"
)

EXCEL_HEADERS = {
    "boq-feature-check.csv": [
        "序号", "清单编码", "项目名称", "单位", "项目特征摘要",
        "缺失/异常字段", "影响", "建议补充内容", "依据来源", "判断等级",
    ],
    "bid-price-analysis.csv": [
        "序号", "清单编码", "项目名称", "单位", "工程量", "投标单价",
        "评标基准/控制价单价", "单价偏离度", "合价", "合价占比",
        "风险类型", "判断等级",
    ],
    "material-price-adjustment.csv": [
        "序号", "材料名称", "规格", "单位", "调差数量", "基准期价",
        "施工期价", "风险幅度", "可调单价", "调差金额", "价格来源", "判断等级",
    ],
    "progress-payment-audit.csv": ["项目", "金额(元)", "依据", "说明"],
    "settlement-deduction-register.csv": [
        "序号", "单位工程/专业", "清单编码/签证编号", "问题类型",
        "报审金额(元)", "建议调整金额(元)", "调整方向", "依据来源",
        "判断等级", "需补资料/人工确认",
    ],
    "cost-variance-analysis.csv": [
        "序号", "成本科目/专业", "目标成本(元)", "动态成本(元)",
        "偏差金额(元)", "偏差比例", "偏差类型", "原因", "判断等级",
        "建议动作", "责任人",
    ],
    "evidence-index.csv": [
        "证据编号", "文件名", "类型/版本", "页码/行号/工作表",
        "关键事实", "关联问题", "可靠性", "缺失/备注",
    ],
    "comprehensive-unit-price.csv": [
        "序号", "费用名称", "计算基数", "费率/单价", "金额(元)", "备注",
    ],
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def markdown_files() -> list[Path]:
    return sorted(
        p for p in ROOT.rglob("*.md") if ".git" not in p.parts
    )


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_frontmatter() -> None:
    path = ROOT / "SKILL.md"
    text = read(path)
    if not text.startswith("---\n"):
        ERRORS.append("SKILL.md: missing YAML frontmatter")
        return
    end = text.find("\n---\n", 4)
    if end == -1:
        ERRORS.append("SKILL.md: unterminated YAML frontmatter")
        return

    frontmatter = text[4:end]
    name_match = re.search(r"^name:\s*(\S+)", frontmatter, re.MULTILINE)
    if not name_match:
        ERRORS.append("SKILL.md: missing name")
    else:
        name = name_match.group(1).strip("'\"")
        if name != ROOT.name:
            ERRORS.append(
                f"SKILL.md: name '{name}' does not match directory '{ROOT.name}'"
            )

    description_match = re.search(r"^description:\s*(.*)$", frontmatter, re.MULTILINE)
    if not description_match:
        ERRORS.append("SKILL.md: missing description")
    else:
        description = frontmatter.split("description:", 1)[1]
        if len(description) > 1536:
            ERRORS.append(
                f"SKILL.md: description is {len(description)} chars (limit 1536)"
            )

    version = None
    in_metadata = False
    for line in frontmatter.splitlines():
        if re.match(r"^metadata:\s*$", line):
            in_metadata = True
            continue
        if in_metadata and re.match(r"^\S", line):
            in_metadata = False
        if in_metadata:
            match = re.match(r"\s+version:\s*['\"]?([^'\"\s]+)", line)
            if match:
                version = match.group(1)
                break

    if version:
        readme = read(ROOT / "README.md")
        readme_version = re.search(r"当前版本：v([0-9.]+)", readme)
        if readme_version and readme_version.group(1) != version:
            ERRORS.append(
                "version mismatch: SKILL.md metadata.version "
                f"{version} vs README 当前版本 {readme_version.group(1)}"
            )
        changelog = read(ROOT / "CHANGELOG.md")
        if f"## v{version}" not in changelog:
            ERRORS.append(
                f"version mismatch: v{version} not found in CHANGELOG.md"
            )


def check_paths() -> None:
    path_pattern = re.compile(
        r"`((?:references|workflows|templates|input-specs|examples|test-cases|"
        r"rules|hooks)/"
        r"[^`\s]+\.md)`"
    )
    link_pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

    for path in markdown_files():
        text = read(path)
        for match in path_pattern.finditer(text):
            target = match.group(1)
            if "*" in target:
                continue
            if not (ROOT / target).exists():
                ERRORS.append(f"{rel(path)}: missing referenced path `{target}`")

        for match in link_pattern.finditer(text):
            target = match.group(1).split("#", 1)[0].strip()
            if not target or target.startswith(
                ("http://", "https://", "mailto:", "/")
            ):
                continue
            if not (path.parent / target).resolve().exists() and not (
                ROOT / target
            ).exists():
                ERRORS.append(f"{rel(path)}: broken relative link '{target}'")


def check_skill_navigation() -> None:
    skill = read(ROOT / "SKILL.md")
    for folder in ("references", "workflows", "templates", "input-specs"):
        for path in sorted((ROOT / folder).glob("*.md")):
            if path.name not in skill:
                ERRORS.append(
                    f"SKILL.md: {folder}/{path.name} is not listed in navigation"
                )


def check_readme_tree() -> None:
    readme = read(ROOT / "README.md")
    block = re.search(r"```text\n(costing-master/.*?)```", readme, re.DOTALL)
    if not block:
        ERRORS.append("README.md: directory tree block not found")
        return

    listed: set[str] = set()
    in_references = False
    for line in block.group(1).splitlines():
        if line.strip().endswith("references/"):
            in_references = True
            continue
        if in_references:
            match = re.match(r"│\s+[├└]──\s+(\S+\.md)", line)
            if match:
                listed.add(match.group(1))
            elif not line.startswith("│"):
                in_references = False

    actual = {p.name for p in (ROOT / "references").glob("*.md")}
    for name in sorted(actual - listed):
        ERRORS.append(f"README.md: reference tree missing {name}")
    for name in sorted(listed - actual):
        ERRORS.append(f"README.md: reference tree lists non-existent {name}")


def check_test_coverage() -> None:
    matrix_path = ROOT / "test-cases" / "README.md"
    matrix = read(matrix_path)
    workflows = {p.name for p in (ROOT / "workflows").glob("*.md")}
    cases = {p.name for p in (ROOT / "test-cases").glob("*.case.md")}

    if "| 数据来源 |" not in matrix:
        ERRORS.append("test-cases/README.md: missing 数据来源 column")

    listed_workflows: set[str] = set()
    listed_cases: set[str] = set()
    for line in matrix.splitlines():
        if not line.startswith("|"):
            continue
        workflow_match = re.search(r"`workflows/([^`]+\.md)`", line)
        case_match = re.search(r"`test-cases/([^`]+\.case\.md)`", line)
        if workflow_match:
            listed_workflows.add(workflow_match.group(1))
            if not case_match:
                ERRORS.append(
                    f"test-cases/README.md: workflow "
                    f"{workflow_match.group(1)} has no test case"
                )
        if case_match:
            listed_cases.add(case_match.group(1))

    for name in sorted(workflows - listed_workflows):
        ERRORS.append(f"test-cases/README.md: workflow {name} is not covered")
    for name in sorted(listed_workflows - workflows):
        ERRORS.append(f"test-cases/README.md: unknown workflow {name}")
    for name in sorted(cases - listed_cases):
        ERRORS.append(f"test-cases/README.md: test case {name} is not listed")
    for name in sorted(listed_cases - cases):
        ERRORS.append(f"test-cases/README.md: unknown test case {name}")

    for path in sorted((ROOT / "test-cases").glob("*.case.md")):
        text = read(path)
        if "## 数据来源" not in text:
            ERRORS.append(f"{rel(path)}: missing '## 数据来源'")
        if "## 期望行为" not in text:
            ERRORS.append(f"{rel(path)}: missing '## 期望行为'")
        if "## 失败表现" not in text:
            ERRORS.append(f"{rel(path)}: missing '## 失败表现'")


def check_excel_templates() -> None:
    folder = ROOT / "templates" / "excel"
    for name, expected in EXCEL_HEADERS.items():
        path = folder / name
        if not path.exists():
            ERRORS.append(f"missing Excel template: {rel(path)}")
            continue
        raw = path.read_bytes()
        if not raw.startswith(b"\xef\xbb\xbf"):
            ERRORS.append(f"{rel(path)}: missing UTF-8 BOM")
        try:
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle))
        except OSError as exc:
            ERRORS.append(f"{rel(path)}: cannot read ({exc})")
            continue
        if not rows:
            ERRORS.append(f"{rel(path)}: empty template")
            continue
        header = rows[0]
        if header != expected:
            ERRORS.append(
                f"{rel(path)}: header mismatch: got {header}, expected {expected}"
            )
        if any(not cell.strip() for cell in header):
            ERRORS.append(f"{rel(path)}: blank header cell")
        if len(header) != len(set(header)):
            ERRORS.append(f"{rel(path)}: duplicate header cell")


def check_no_emoji() -> None:
    suffixes = {".md", ".yml", ".yaml", ".py", ".json", ".csv"}
    for path in sorted(ROOT.rglob("*")):
        if (
            not path.is_file()
            or ".git" in path.parts
            or path.suffix not in suffixes
        ):
            continue
        for line_number, line in enumerate(read(path).splitlines(), 1):
            match = EMOJI_PATTERN.search(line)
            if match:
                ERRORS.append(
                    f"{rel(path)}:{line_number}: emoji icon "
                    f"U+{ord(match.group(0)):04X} is not allowed"
                )


def check_markdown() -> None:
    for path in markdown_files():
        text = read(path)
        lines = text.splitlines()

        if text.count("```") % 2 != 0:
            ERRORS.append(f"{rel(path)}: unbalanced code fences")

        headings: set[str] = set()
        for line in lines:
            if line.startswith("#"):
                heading = line.strip()
                if heading in headings:
                    ERRORS.append(f"{rel(path)}: duplicate heading '{heading}'")
                headings.add(heading)

        index = 0
        while index < len(lines):
            line = lines[index]
            if (
                line.strip().startswith("|")
                and index + 1 < len(lines)
                and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[index + 1])
            ):
                columns = line.count("|")
                row = index + 2
                while row < len(lines) and lines[row].strip().startswith("|"):
                    if lines[row].count("|") != columns:
                        ERRORS.append(
                            f"{rel(path)}:{row + 1}: table row has "
                            f"{lines[row].count('|')} columns, expected {columns}"
                        )
                    row += 1
                index = row
            else:
                index += 1


def main() -> int:
    check_frontmatter()
    check_paths()
    check_skill_navigation()
    check_readme_tree()
    check_test_coverage()
    check_markdown()
    check_excel_templates()
    check_no_emoji()

    if ERRORS:
        print(f"FAILED: {len(ERRORS)} validation error(s)")
        for error in ERRORS:
            print(f"  - {error}")
        return 1

    print(
        f"OK: validated {len(markdown_files())} markdown files "
        f"and {len(EXCEL_HEADERS)} Excel templates"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
