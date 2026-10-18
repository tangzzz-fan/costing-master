#!/usr/bin/env python3
"""Evaluate coverage, data sources, and regression status for the skill repository.

The report is written to stdout by default. Use --output to save a Markdown file.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, timedelta
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


def load_registry() -> dict | None:
    text = read(ROOT / "references" / "standards-index.md")
    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def standard_freshness(registry: dict | None) -> tuple[dict[str, str], list[str]]:
    gaps: list[str] = []
    info = {
        "standard": "未登记",
        "local_rules": "未登记",
        "scenario_last_reviewed": "未登记",
        "standard_last_reviewed": "未登记",
        "local_last_reviewed": "未登记",
        "stale": "unknown",
        "legacy_project": "unknown",
    }
    scenario_path = (
        ROOT / "test-cases" / "fixtures" / "suzhou-metro-viii-ts-08" / "scenario.json"
    )
    if registry is None:
        return info, ["standards-index.md machine-readable registry missing or invalid"]
    if not scenario_path.exists():
        return info, ["Suzhou metro scenario.json missing"]

    scenario = json.loads(read(scenario_path))
    code = scenario.get("standard_version")
    local_id = scenario.get("local_rules_id")
    legacy = bool(scenario.get("legacy_project"))
    reviewed = parse_date(scenario.get("last_reviewed"))
    today = date.today()
    cutoff = today - timedelta(days=365)
    info["legacy_project"] = "yes" if legacy else "no"
    info["scenario_last_reviewed"] = str(scenario.get("last_reviewed", "missing"))

    if reviewed is None:
        gaps.append("scenario last_reviewed missing or invalid")
    elif reviewed < cutoff:
        gaps.append(f"scenario last_reviewed is older than 12 months: {reviewed}")

    standards = {item.get("code"): item for item in registry.get("standards", [])}
    standard = standards.get(code)
    if not standard:
        gaps.append(f"standard not registered: {code}")
    else:
        status = standard.get("status")
        info["standard"] = f"{code} ({status})"
        info["standard_last_reviewed"] = str(
            standard.get("last_reviewed", "missing")
        )
        if status == "superseded" and not legacy:
            gaps.append(
                f"scenario uses superseded standard without legacy flag: {code}"
            )
        if status == "current":
            effective = parse_date(standard.get("effective_date"))
            if effective and effective > today:
                gaps.append(f"standard marked current but effective in future: {code}")
        standard_reviewed = parse_date(standard.get("last_reviewed"))
        if standard_reviewed is None:
            gaps.append(f"standard last_reviewed missing: {code}")
        elif standard_reviewed < cutoff:
            gaps.append(f"standard last_reviewed older than 12 months: {code}")

    local_rules = {item.get("id"): item for item in registry.get("local_rules", [])}
    local = local_rules.get(local_id)
    if not local:
        gaps.append(f"local rule not registered: {local_id}")
    else:
        status = local.get("status")
        info["local_rules"] = (
            f"{local_id} {local.get('region')} ({status})"
        )
        info["local_last_reviewed"] = str(local.get("last_reviewed", "missing"))
        if status in {"superseded", "upcoming"} and not legacy:
            gaps.append(
                "scenario uses non-current local rule without legacy flag: "
                f"{local_id} ({status})"
            )
        local_reviewed = parse_date(local.get("last_reviewed"))
        if local_reviewed is None:
            gaps.append(f"local rule last_reviewed missing: {local_id}")
        elif local_reviewed < cutoff:
            gaps.append(f"local rule last_reviewed older than 12 months: {local_id}")

    info["stale"] = "yes" if gaps else "no"
    return info, gaps


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
    freshness, freshness_gaps = standard_freshness(load_registry())
    gaps.extend(freshness_gaps)
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
            "## Standard Freshness",
            "",
            "| Item | Value |",
            "|---|---|",
            f"| Scenario standard | {freshness['standard']} |",
            f"| Scenario local rules | {freshness['local_rules']} |",
            f"| Scenario last reviewed | {freshness['scenario_last_reviewed']} |",
            f"| Standard last reviewed | {freshness['standard_last_reviewed']} |",
            f"| Local rule last reviewed | {freshness['local_last_reviewed']} |",
            f"| Stale | {freshness['stale']} |",
            f"| Legacy project | {freshness['legacy_project']} |",
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
