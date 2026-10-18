#!/usr/bin/env python3
"""Assert standard-change applicability for Suzhou and Zhejiang projects."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENARIO_PATH = (
    ROOT / "test-cases" / "fixtures" / "standard-change" / "scenario.json"
)
REGISTRY_PATH = ROOT / "references" / "standards-index.md"
FAILURES: list[str] = []


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_registry() -> dict:
    match = re.search(r"```json\n(.*?)\n```", read(REGISTRY_PATH), re.DOTALL)
    if not match:
        raise ValueError("standards-index.md machine-readable registry missing")
    return json.loads(match.group(1))


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def add_failure(message: str) -> None:
    FAILURES.append(message)


def main() -> int:
    registry = load_registry()
    scenario = json.loads(read(SCENARIO_PATH))

    standards = {item.get("code"): item for item in registry.get("standards", [])}
    local_rules = {item.get("id"): item for item in registry.get("local_rules", [])}

    required_standards = {"GB 50500-2013", "GB/T 50500-2024"}
    required_local = {"L00", "L01", "L03", "L04"}
    for code in sorted(required_standards - set(standards)):
        add_failure(f"standard missing from registry: {code}")
    for local_id in sorted(required_local - set(local_rules)):
        add_failure(f"local rule missing from registry: {local_id}")

    # Cutoff dates must match the registry's old/new local rules.
    checks = [
        ("江苏/苏州", "L00", "superseded_date"),
        ("江苏/苏州", "L01", "effective_date"),
        ("浙江", "L04", "superseded_date"),
        ("浙江", "L03", "effective_date"),
    ]
    for region, local_id, field in checks:
        rule = local_rules.get(local_id, {})
        expected = scenario["cutoffs"].get(region)
        actual = rule.get(field)
        if expected != actual:
            add_failure(
                f"cutoff mismatch {region} {local_id}.{field}: "
                f"scenario {expected}, registry {actual}"
            )

    for project in scenario["projects"]:
        region = project["region"]
        cutoff = parse_date(scenario["cutoffs"][region])
        tender = parse_date(project["tender_date"])

        if region == "江苏/苏州":
            if tender < cutoff:
                expected_standard, expected_local = "GB 50500-2013", "L00"
            else:
                expected_standard, expected_local = "GB/T 50500-2024", "L01"
        elif region == "浙江":
            expected_standard = "GB/T 50500-2024"
            expected_local = "L04" if tender < cutoff else "L03"
        else:
            add_failure(f"unknown region in scenario: {region}")
            continue

        if project["expected_standard"] != expected_standard:
            add_failure(
                f"project {project['id']} standard: "
                f"expected {project['expected_standard']}, computed {expected_standard}"
            )
        if project["expected_local"] != expected_local:
            add_failure(
                f"project {project['id']} local rule: "
                f"expected {project['expected_local']}, computed {expected_local}"
            )

        standard = standards.get(expected_standard, {})
        local = local_rules.get(expected_local, {})
        if not standard:
            add_failure(f"project {project['id']}: standard not registered: {expected_standard}")
        if not local:
            add_failure(f"project {project['id']}: local rule not registered: {expected_local}")

        if project["id"] in {"A", "C"}:
            if local.get("status") != "superseded":
                add_failure(
                    f"project {project['id']} should use a superseded old rule, "
                    f"got {local.get('status')}"
                )
        if project["id"] == "B" and local.get("status") != "current":
            add_failure(f"project B should use a current local rule, got {local.get('status')}")
        if project["id"] == "D":
            effective = parse_date(local.get("effective_date", "9999-12-31"))
            if tender < effective:
                add_failure("project D tender date is before the Zhejiang 2025 effective date")

    if FAILURES:
        print(f"FAILED: {len(FAILURES)} standard change assertion(s)")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1

    print("OK: standard change assertions passed")
    for project in scenario["projects"]:
        print(
            f"  {project['id']} {project['region']} {project['tender_date']} -> "
            f"{project['expected_standard']} + {project['expected_local']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
