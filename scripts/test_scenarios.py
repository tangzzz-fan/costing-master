#!/usr/bin/env python3
"""Execute deterministic business assertions for the Suzhou metro test scenario.

This complements scripts/validate.py:
- validate.py checks structure, paths, coverage, tables, and emoji.
- test_scenarios.py checks the actual arithmetic and expected classifications.
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = ROOT / "test-cases" / "fixtures" / "suzhou-metro-viii-ts-08"
SCENARIO_PATH = FIXTURE_DIR / "scenario.json"
FAILURES: list[str] = []


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def money(value: object) -> Decimal:
    return Decimal(str(value))


def rounded(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def check_amount(name: str, actual: Decimal, expected: Decimal) -> None:
    if abs(actual - expected) > Decimal("0.01"):
        FAILURES.append(f"{name}: got {actual}, expected {expected}")


def check_equal(name: str, actual: object, expected: object) -> None:
    if actual != expected:
        FAILURES.append(f"{name}: got {actual!r}, expected {expected!r}")


def check_contains(name: str, path: Path, needle: str) -> None:
    if needle not in read(path):
        FAILURES.append(f"{name}: missing '{needle}' in {path.relative_to(ROOT)}")


def check_progress_payment(data: dict) -> None:
    p = data["progress_payment"]
    expected = p["expected"]

    approved = money(p["reported_completed"]) - money(p["unconfirmed_visa"])
    current = approved * money(p["payment_ratio"])
    threshold = money(data["project"]["contract_amount"]) * money(
        p["advance_threshold_ratio"]
    )
    advance = current * money(p["advance_deduction_ratio"])
    retention = current * money(p["retention_ratio"])
    net = current - advance - retention

    check_amount("progress.approved_value", approved, money(expected["approved_value"]))
    check_amount("progress.current_payment", current, money(expected["current_payment"]))
    check_amount(
        "progress.advance_threshold", rounded(threshold), money(expected["advance_threshold"])
    )
    if money(p["cumulative_completed"]) < threshold:
        FAILURES.append("progress: cumulative completed value is below the 30% threshold")
    check_amount(
        "progress.advance_deduction", advance, money(expected["advance_deduction"])
    )
    check_amount("progress.retention", retention, money(expected["retention"]))
    check_amount("progress.net_payment", net, money(expected["net_payment"]))


def check_material_adjustment(data: dict) -> None:
    m = data["material_adjustment"]
    supported = Decimal("0")
    for item in m["items"]:
        base = money(item["base_price"])
        current = money(item["current_price"])
        risk = money(item["risk_ratio"])
        quantity = money(item["quantity"])

        if current > base:
            unit = current - base * (Decimal("1") + risk)
        elif current < base:
            unit = current - base * (Decimal("1") - risk)
        else:
            unit = Decimal("0")

        unit = max(unit, Decimal("0")) if current > base else min(unit, Decimal("0"))
        amount = unit * quantity
        supported += amount

        check_amount(f"material.{item['name']}.unit", unit, money(item["expected_unit"]))
        check_amount(
            f"material.{item['name']}.amount", amount, money(item["expected_amount"])
        )

    gap = money(m["claimed_amount"]) - supported
    check_amount(
        "material.supported_total", supported, money(m["expected_supported_total"])
    )
    check_amount("material.gap", gap, money(m["expected_gap"]))


def check_settlement(data: dict) -> None:
    s = data["settlement"]
    component_sum = sum((money(value) for value in s["components"].values()), Decimal("0"))
    difference = money(s["reported_total"]) - component_sum

    check_amount(
        "settlement.component_sum", component_sum, money(s["expected_component_sum"])
    )
    check_amount("settlement.difference", difference, money(s["expected_difference"]))

    issue_types = {issue["id"]: issue["type"] for issue in s["issues"]}
    check_equal("settlement.S-01", issue_types.get("S-01"), "suspected_duplicate")
    check_equal("settlement.S-02", issue_types.get("S-02"), "pending_evidence")
    check_equal("settlement.S-03", issue_types.get("S-03"), "unsupported_adjustment")
    check_equal("settlement.S-04", issue_types.get("S-04"), "pending_evidence")
    check_equal("settlement.S-05", issue_types.get("S-05"), "certain_arithmetic")

    certain = [
        issue_id
        for issue_id, issue_type in issue_types.items()
        if issue_type.startswith("certain") and issue_id != "S-05"
    ]
    if certain:
        FAILURES.append(
            "settlement: unexpected certain classifications: " + ", ".join(certain)
        )


def check_document_consistency() -> None:
    check_contains(
        "progress fixture",
        FIXTURE_DIR / "progress-payment-application.md",
        "48,048,000",
    )
    check_contains(
        "material fixture",
        FIXTURE_DIR / "material-price-basis.md",
        "2,370,000",
    )
    check_contains(
        "settlement fixture",
        FIXTURE_DIR / "settlement-report.md",
        "25,228,636.39",
    )
    check_contains(
        "metro test case",
        ROOT / "test-cases" / "suzhou-metro-station.case.md",
        "不直接给出最终审定价",
    )
    check_contains(
        "metro test case",
        ROOT / "test-cases" / "suzhou-metro-station.case.md",
        "疑似重复",
    )
    check_contains(
        "verification report",
        ROOT / "examples" / "suzhou-metro-station-verification.md",
        "48,048,000",
    )
    check_contains(
        "verification report",
        ROOT / "examples" / "suzhou-metro-station-verification.md",
        "2,370,000",
    )


def main() -> int:
    data = json.loads(read(SCENARIO_PATH))
    check_progress_payment(data)
    check_material_adjustment(data)
    check_settlement(data)
    check_document_consistency()

    if FAILURES:
        print(f"FAILED: {len(FAILURES)} business assertion(s)")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1

    print("OK: Suzhou metro scenario business assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
