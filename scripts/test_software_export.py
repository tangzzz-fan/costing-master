#!/usr/bin/env python3
"""
软件导出清单体检逻辑测试。

数据：
- 真实公开清单：江苏政府采购网《2025 年城市安全建设-市管 12 座桥梁
  轻量化监测设备安装》汉桥分部分项清单摘录。
- 问题样例：在上述真实清单基础上改造，仅用于验证检查规则。

覆盖：
- CSV/XLSX/GBK 读取
- 标题行、表头、分部行、合计行识别
- 编码、五要素、量价、合计、单位、精度、2024 规费等检查
- 问题回填 CSV 表头、BOM、退出码和 CLI 边界
"""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import zipfile
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

from check_software_export import (
    ISSUE_HEADERS,
    analyze_sheet,
    load_sheets,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = ROOT / "test-cases" / "fixtures" / "software-export"
REAL_CSV = FIXTURE_DIR / "hanqiao-real-boq.csv"
ISSUE_CSV = FIXTURE_DIR / "hanqiao-export-issues.csv"
SCRIPT = ROOT / "scripts" / "check_software_export.py"


def analyze(path: Path, standard: str = "2024"):
    sheets = load_sheets(path)
    return [analyze_sheet(sheet, standard, Decimal("0.02")) for sheet in sheets]


def problems(result) -> list[str]:
    return [issue.problem for issue in result.issues]


def levels(result, level: str) -> int:
    return sum(1 for issue in result.issues if issue.level == level)


def column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def build_xlsx(source: Path, target: Path) -> None:
    """Build a minimal xlsx with one sheet and shared strings."""
    rows = list(csv.reader(source.open(encoding="utf-8-sig", newline="")))
    shared: list[str] = []
    positions: dict[str, int] = {}

    def shared_index(value: str) -> int:
        if value not in positions:
            positions[value] = len(shared)
            shared.append(value)
        return positions[value]

    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            if value == "":
                continue
            reference = f"{column_name(column_index)}{row_index}"
            try:
                float(value.replace(",", ""))
            except ValueError:
                cells.append(
                    f'<c r="{reference}" t="s"><v>{shared_index(value)}</v></c>'
                )
            else:
                cells.append(f'<c r="{reference}"><v>{escape(value)}</v></c>')
        sheet_rows.append(f'<row r="{row_index}">' + "".join(cells) + "</row>")

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>" + "".join(sheet_rows) + "</sheetData></worksheet>"
    )
    shared_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared)}" uniqueCount="{len(shared)}">'
        + "".join(f"<si><t>{escape(item)}</t></si>" for item in shared)
        + "</sst>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="分部分项" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
        'Target="sharedStrings.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/sharedStrings.xml", shared_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_real_boq_header_and_items() -> None:
    result = analyze(REAL_CSV)[0]
    assert result.recognized, result.skip_reason
    assert result.header_row == 6, result.header_row
    assert len(result.items) == 21, len(result.items)
    assert result.sections == 4, result.sections
    assert result.totals == 2, result.totals
    assert result.sum_total == Decimal("216994.83"), result.sum_total
    assert result.last_total == Decimal("216994.84"), result.last_total
    print("[通过] 真实公开清单：表头第 6 行、21 个清单项、合计 216,994.84")


def test_real_boq_has_no_false_errors() -> None:
    result = analyze(REAL_CSV)[0]
    assert levels(result, "错误") == 0, problems(result)
    assert levels(result, "警告") == 8, levels(result, "警告")
    assert levels(result, "提示") == 5, levels(result, "提示")
    assert any("项目特征为空" in problem for problem in problems(result))
    assert any("四舍五入差异" in problem for problem in problems(result))
    print("[通过] 真实清单无误报错误；8 条特征缺失、5 条四舍五入提示")


def test_issue_fixture_flags_expected_rules() -> None:
    result = analyze(ISSUE_CSV)[0]
    found = problems(result)
    expected = [
        "清单编码重复",
        "合价不等于工程量×综合单价",
        "工程量为负数",
        "清单行缺项目编码",
        "综合单价为 0",
        "同名、同特征、同单位的清单项重复出现",
        "清单编码为 11 位",
        "2024 版项目出现“规费”",
        "合计行与清单项合价汇总不一致",
        "名称提示单位应为",
    ]
    for needle in expected:
        assert any(needle in problem for problem in found), needle
    assert levels(result, "错误") >= 5, levels(result, "错误")
    assert sum(1 for issue in result.issues if issue.level == "错误") >= 5
    assert not any(
        "清单编码重复" in issue.problem
        for issue in result.issues
        if issue.code == "30501999999"
    ), "11 位编码不应误报重复"
    print("[通过] 问题样例覆盖编码、算术、负数、缺项、零单价、重复项、规费、合计")


def test_xlsx_reader_matches_csv() -> None:
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "清单.xlsx"
        build_xlsx(REAL_CSV, target)
        results = analyze(target)
        assert len(results) == 1, len(results)
        assert results[0].name == "分部分项", results[0].name
        assert len(results[0].items) == 21, len(results[0].items)
        assert levels(results[0], "错误") == 0, problems(results[0])
    print("[通过] XLSX（共享字符串）读取与 CSV 结果一致")


def test_gbk_csv_reader() -> None:
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "清单-gbk.csv"
        text = REAL_CSV.read_text(encoding="utf-8-sig")
        target.write_bytes(text.encode("gb18030"))
        results = analyze(target)
        assert len(results[0].items) == 21, len(results[0].items)
    print("[通过] GBK/GB18030 导出的 CSV 可读取")


def test_cli_outputs_and_exit_codes() -> None:
    with tempfile.TemporaryDirectory() as folder:
        issues_csv = Path(folder) / "问题回填.csv"
        report_md = Path(folder) / "体检报告.md"
        real = run_cli(
            str(REAL_CSV),
            "--standard",
            "2024",
            "--out",
            str(issues_csv),
            "--md",
            str(report_md),
        )
        assert real.returncode == 0, real.stdout + real.stderr
        assert issues_csv.read_bytes().startswith(b"\xef\xbb\xbf")
        with issues_csv.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        assert rows[0] == ISSUE_HEADERS, rows[0]
        assert len(rows) > 1
        assert "# 软件导出清单体检摘要" in report_md.read_text(encoding="utf-8")

        issues = run_cli(str(ISSUE_CSV), "--standard", "2024")
        assert issues.returncode == 1, issues.stdout + issues.stderr
        assert "错误" in issues.stdout

    template = run_cli("--template")
    assert template.returncode == 0
    assert "项目编码" in template.stdout
    assert "问题编号" in template.stdout

    print("[通过] CLI 退出码、问题回填 BOM/表头和 Markdown 报告")


def test_cli_rejects_proprietary_files() -> None:
    with tempfile.TemporaryDirectory() as folder:
        fake = Path(folder) / "清单.24jz"
        fake.write_text("<xml/>", encoding="utf-8")
        result = run_cli(str(fake))
        assert result.returncode == 2, result.returncode
        assert "不解析" in result.stdout
    print("[通过] .24jz 等专有文件提示改用 Excel/CSV，不越界解析")


def test_cli_requires_input() -> None:
    result = run_cli()
    assert result.returncode == 2, result.returncode
    print("[通过] 无输入时返回用法提示")


def mutated_copy(folder: str, replacements: list[tuple[str, str]]) -> Path:
    text = REAL_CSV.read_text(encoding="utf-8-sig")
    for old, new in replacements:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    target = Path(folder) / "清单-改造.csv"
    target.write_text(text, encoding="utf-8-sig")
    return target


def test_full_width_space_is_flagged() -> None:
    with tempfile.TemporaryDirectory() as folder:
        target = mutated_copy(folder, [(",靶标,", ",靶\u3000标,")])
        result = analyze(target)[0]
        hits = [
            issue
            for issue in result.issues
            if issue.rule_id == "SW-11" and issue.field == "项目名称"
        ]
        assert hits, problems(result)
        assert hits[0].level == "警告", hits[0].level
    print("[通过] 项目名称含全角空格时命中 SW-11")


def test_precision_beyond_two_decimals_is_flagged() -> None:
    with tempfile.TemporaryDirectory() as folder:
        target = mutated_copy(folder, [(",6925.87,", ",6925.872,")])
        result = analyze(target)[0]
        hits = [issue for issue in result.issues if "金额小数位超过 2 位" in issue.problem]
        assert hits, problems(result)
        assert hits[0].level == "提示", hits[0].level
        assert hits[0].field == "合价", hits[0].field
    print("[通过] 合价小数位超过 2 位时命中精度检查")


def main() -> int:
    tests = [
        test_real_boq_header_and_items,
        test_real_boq_has_no_false_errors,
        test_issue_fixture_flags_expected_rules,
        test_full_width_space_is_flagged,
        test_precision_beyond_two_decimals_is_flagged,
        test_xlsx_reader_matches_csv,
        test_gbk_csv_reader,
        test_cli_outputs_and_exit_codes,
        test_cli_rejects_proprietary_files,
        test_cli_requires_input,
    ]
    for test in tests:
        test()
    print(f"OK: software export checks validated ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
