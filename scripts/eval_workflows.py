#!/usr/bin/env python3
"""Evaluate coverage, data sources, and regression status for the skill repository.

The report is written to stdout by default. Use --output to save a Markdown file.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def markdown_files(folder: str) -> list[Path]:
    return sorted((ROOT / folder).glob("*.md"))


def run_step(name: str, command: list[str]) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, *command],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = (result.stdout or result.stderr).strip()
    return result.returncode == 0, output or f"{name} completed"


def data_source(path: Path) -> str:
    text = read(path)
    match = re.search(r"## 数据来源\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    section = match.group(1) if match else ""
    if section.strip().startswith("模拟"):
        return "模拟/教学"
    has_real = "真实公开" in section
    has_simulated = "模拟" in section
    if has_real and has_simulated:
        return "真实公开+模拟"
    if has_real:
        return "真实公开"
    if has_simulated:
        return "模拟/教学"
    return "未分类"


def version() -> str:
    match = re.search(
        r"^\s+version:\s*[\"']?([0-9.]+)",
        read(ROOT / "SKILL.md"),
        re.MULTILINE,
    )
    return match.group(1) if match else "unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="optional Markdown report path")
    args = parser.parse_args()

    matrix = read(ROOT / "test-cases" / "README.md")
    workflows = markdown_files("workflows")
    cases = sorted((ROOT / "test-cases").glob("*.case.md"))
    examples = markdown_files("examples")
    references = markdown_files("references")
    templates = markdown_files("templates")
    input_specs = markdown_files("input-specs")
    scenarios = sorted((ROOT / "test-cases").glob("fixtures/**/scenario.json"))

    listed_workflows = set(re.findall(r"`workflows/([^`]+\.md)`", matrix))
    listed_cases = set(re.findall(r"`test-cases/([^`]+\.case\.md)`", matrix))
    workflow_names = {p.name for p in workflows}
    case_names = {p.name for p in cases}

    workflow_coverage = (
        100.0
        if not workflow_names
        else 100.0 * len(workflow_names & listed_workflows) / len(workflow_names)
    )
    case_listing = (
        100.0
        if not case_names
        else 100.0 * len(case_names & listed_cases) / len(case_names)
    )

    sources = {p: data_source(p) for p in cases}
    source_counts: dict[str, int] = {}
    for source in sources.values():
        source_counts[source] = source_counts.get(source, 0) + 1
    declared = sum(1 for source in sources.values() if source != "未分类")
    source_coverage = 100.0 * declared / len(cases) if cases else 100.0

    validate_ok, validate_output = run_step(
        "validate", ["scripts/validate.py"]
    )
    scenario_ok, scenario_output = run_step(
        "scenarios", ["scripts/test_scenarios.py"]
    )

    gaps: list[str] = []
    if workflow_coverage < 100:
        missing = sorted(workflow_names - listed_workflows)
        gaps.append("workflow coverage gap: " + ", ".join(missing))
    if case_listing < 100:
        missing = sorted(case_names - listed_cases)
        gaps.append("test case listing gap: " + ", ".join(missing))
    if source_coverage < 100:
        missing = sorted(
            p.name for p, source in sources.items() if source == "未分类"
        )
        gaps.append("missing data source: " + ", ".join(missing))
    if not scenarios:
        gaps.append("no scenario.json golden case found")
    if not validate_ok:
        gaps.append("validate.py failed")
    if not scenario_ok:
        gaps.append("test_scenarios.py failed")

    status = "PASS" if not gaps else "FAIL"
    report_lines = [
        "# Costing Master Quality Report",
        "",
        f"- Version: {version()}",
        f"- Generated: {date.today().isoformat()}",
        f"- Status: {status}",
        "",
        "## Counts",
        "",
        "| Item | Count |",
        "|---|---:|",
        f"| Workflows | {len(workflows)} |",
        f"| Test cases | {len(cases)} |",
        f"| Examples | {len(examples)} |",
        f"| References | {len(references)} |",
        f"| Templates | {len(templates)} |",
        f"| Input specs | {len(input_specs)} |",
        f"| Scenario JSON golden cases | {len(scenarios)} |",
        "",
        "## Coverage",
        "",
        "| Metric | Target | Actual | Status |",
        "|---|---:|---:|---|",
        f"| Workflow coverage | 100% | {workflow_coverage:.0f}% | {'PASS' if workflow_coverage == 100 else 'FAIL'} |",
        f"| Test case listing | 100% | {case_listing:.0f}% | {'PASS' if case_listing == 100 else 'FAIL'} |",
        f"| Data source declaration | 100% | {source_coverage:.0f}% | {'PASS' if source_coverage == 100 else 'FAIL'} |",
        "",
        "## Data Sources",
        "",
        "| Source | Cases |",
        "|---|---:|",
    ]
    for source, count in sorted(source_counts.items()):
        report_lines.append(f"| {source} | {count} |")
    report_lines.extend(
        [
            "",
            "## CI Checks",
            "",
            "| Step | Result | Detail |",
            "|---|---|---|",
            f"| validate.py | {'PASS' if validate_ok else 'FAIL'} | {validate_output.replace('|', '/')} |",
            f"| test_scenarios.py | {'PASS' if scenario_ok else 'FAIL'} | {scenario_output.replace('|', '/')} |",
            "",
            "## Gaps",
            "",
        ]
    )
    if gaps:
        report_lines.extend(f"- {gap}" for gap in gaps)
    else:
        report_lines.append("- None")
    report_lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Semantic evidence and conclusion-strength checks still require manual review.",
            "- Simulated/teaching cases are labeled and do not replace real-data cases.",
        ]
    )

    report = "\n".join(report_lines) + "\n"
    print(report)
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
