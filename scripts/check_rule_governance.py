#!/usr/bin/env python3
"""Validate rule registration, the task manifest contract, and rule coverage.

Checks:
- rules/rule-registry.json exists, parses, and has the required fields
- rule IDs are unique and use the R-000 format
- statuses, dates, enforcement values, and referenced paths are valid
- every active rule has at least one test
- every workflow is covered by at least one active rule
- every test case is covered by at least one active rule
- templates/task-manifest.md exists and contains the required sections
- the registry version matches SKILL.md metadata.version
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "rules" / "rule-registry.json"
MANIFEST_PATH = ROOT / "templates" / "task-manifest.md"

REQUIRED_RULE_FIELDS = (
    "id",
    "title",
    "status",
    "effective_date",
    "source",
    "workflows",
    "references",
    "templates",
    "tests",
    "enforcement",
    "owner",
)
VALID_STATUSES = {"draft", "active", "deprecated", "superseded"}
VALID_ENFORCEMENT = {"script", "manual", "script+manual", "checklist+manual"}
PATH_FIELDS = ("workflows", "references", "templates", "tests")
REQUIRED_MANIFEST_SECTIONS = (
    "任务基本信息",
    "适用规则",
    "使用文件",
    "证据编号",
    "质检与审核",
    "交付状态",
)
ERRORS: list[str] = []


def fail(message: str) -> None:
    ERRORS.append(message)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def registry_version() -> str | None:
    skill = read(ROOT / "SKILL.md")
    match = re.search(
        r"^\s+version:\s*[\"']?([0-9.]+)",
        skill,
        re.MULTILINE,
    )
    return match.group(1) if match else None


def load_registry() -> dict | None:
    if not REGISTRY_PATH.exists():
        fail("rules/rule-registry.json: file is missing")
        return None
    try:
        data = json.loads(read(REGISTRY_PATH))
    except json.JSONDecodeError as exc:
        fail(f"rules/rule-registry.json: invalid JSON ({exc})")
        return None
    if not isinstance(data, dict):
        fail("rules/rule-registry.json: top-level value must be an object")
        return None
    return data


def check_date(value: object, label: str) -> None:
    if not isinstance(value, str):
        fail(f"{label}: date must be a string")
        return
    try:
        date.fromisoformat(value)
    except ValueError:
        fail(f"{label}: invalid ISO date '{value}'")


def check_paths(rule_id: str, field: str, values: object) -> None:
    if not isinstance(values, list):
        fail(f"{rule_id}.{field}: must be a list")
        return
    for value in values:
        if not isinstance(value, str) or not value.strip():
            fail(f"{rule_id}.{field}: path must be a non-empty string")
            continue
        if field == "tests" and not value.endswith(".case.md"):
            fail(f"{rule_id}.tests: test path must end with .case.md: {value}")
        if field in {"workflows", "references", "templates"} and not value.endswith(
            ".md"
        ):
            fail(f"{rule_id}.{field}: path must end with .md: {value}")
        if not (ROOT / value).exists():
            fail(f"{rule_id}.{field}: referenced path does not exist: {value}")


def check_registry(data: dict) -> list[dict]:
    rules = data.get("rules")
    if not isinstance(rules, list) or not rules:
        fail("rules/rule-registry.json: 'rules' must be a non-empty list")
        return []

    check_date(data.get("last_reviewed"), "registry.last_reviewed")
    version = data.get("version")
    skill_version = registry_version()
    if not isinstance(version, str):
        fail("rules/rule-registry.json: version must be a string")
    elif skill_version and version != skill_version:
        fail(
            "version mismatch: rule registry "
            f"{version} vs SKILL.md metadata.version {skill_version}"
        )

    seen_ids: set[str] = set()
    for index, rule in enumerate(rules):
        label = f"rules[{index}]"
        if not isinstance(rule, dict):
            fail(f"{label}: rule must be an object")
            continue
        rule_id = rule.get("id", label)
        if not isinstance(rule_id, str) or not re.fullmatch(r"R-\d{3}", rule_id):
            fail(f"{label}.id: must use R-000 format")
        if rule_id in seen_ids:
            fail(f"{rule_id}: duplicate rule ID")
        seen_ids.add(rule_id)

        for field in REQUIRED_RULE_FIELDS:
            if field not in rule:
                fail(f"{rule_id}.{field}: required field is missing")
        if not rule.get("title"):
            fail(f"{rule_id}.title: must be non-empty")
        if rule.get("status") not in VALID_STATUSES:
            fail(f"{rule_id}.status: invalid status {rule.get('status')!r}")
        if rule.get("enforcement") not in VALID_ENFORCEMENT:
            fail(f"{rule_id}.enforcement: invalid value {rule.get('enforcement')!r}")
        if not rule.get("owner"):
            fail(f"{rule_id}.owner: must be non-empty")
        if not rule.get("source"):
            fail(f"{rule_id}.source: must be non-empty")
        check_date(rule.get("effective_date"), f"{rule_id}.effective_date")

        for field in PATH_FIELDS:
            check_paths(rule_id, field, rule.get(field, []))

        if rule.get("status") == "active":
            if not rule.get("tests"):
                fail(f"{rule_id}: active rule must have at least one test")
            if not any(
                rule.get(field) for field in ("workflows", "references", "templates")
            ):
                fail(
                    f"{rule_id}: active rule must reference a workflow, "
                    "reference, or template"
                )
    return [rule for rule in rules if isinstance(rule, dict)]


def check_manifest() -> None:
    if not MANIFEST_PATH.exists():
        fail("templates/task-manifest.md: file is missing")
        return
    text = read(MANIFEST_PATH)
    for section in REQUIRED_MANIFEST_SECTIONS:
        if section not in text:
            fail(f"templates/task-manifest.md: missing section '{section}'")


def check_coverage(rules: list[dict]) -> tuple[set[str], set[str]]:
    active = [rule for rule in rules if rule.get("status") == "active"]
    covered_workflows = {
        Path(path).name
        for rule in active
        for path in rule.get("workflows", [])
        if isinstance(path, str)
    }
    covered_cases = {
        Path(path).name
        for rule in active
        for path in rule.get("tests", [])
        if isinstance(path, str)
    }
    all_workflows = {path.name for path in (ROOT / "workflows").glob("*.md")}
    all_cases = {path.name for path in (ROOT / "test-cases").glob("*.case.md")}

    for name in sorted(all_workflows - covered_workflows):
        fail(f"workflow is not covered by any active rule: {name}")
    for name in sorted(all_cases - covered_cases):
        fail(f"test case is not covered by any active rule: {name}")
    return covered_workflows, covered_cases


def main() -> int:
    data = load_registry()
    rules: list[dict] = []
    if data is not None:
        rules = check_registry(data)
    check_manifest()

    if not (ROOT / "rules" / "README.md").exists():
        fail("rules/README.md: file is missing")

    covered_workflows, covered_cases = check_coverage(rules)
    active = [rule for rule in rules if rule.get("status") == "active"]
    with_tests = sum(1 for rule in active if rule.get("tests"))
    all_workflows = {path.name for path in (ROOT / "workflows").glob("*.md")}
    all_cases = {path.name for path in (ROOT / "test-cases").glob("*.case.md")}
    workflow_coverage = (
        100.0 * len(all_workflows & covered_workflows) / len(all_workflows)
        if all_workflows
        else 100.0
    )
    case_coverage = (
        100.0 * len(all_cases & covered_cases) / len(all_cases) if all_cases else 100.0
    )
    test_coverage = 100.0 * with_tests / len(active) if active else 0.0

    if ERRORS:
        print(f"FAILED: {len(ERRORS)} rule governance error(s)")
        for error in ERRORS:
            print(f"  - {error}")
        return 1

    print(
        f"OK: {len(rules)} rules ({len(active)} active), "
        f"{with_tests}/{len(active)} with tests ({test_coverage:.0f}%), "
        f"workflows {len(all_workflows & covered_workflows)}/{len(all_workflows)} "
        f"({workflow_coverage:.0f}%), "
        f"test cases {len(all_cases & covered_cases)}/{len(all_cases)} "
        f"({case_coverage:.0f}%)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
