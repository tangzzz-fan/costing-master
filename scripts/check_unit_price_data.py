#!/usr/bin/env python3
"""
单价样本校验与参考区间计算工具

输入：UTF-8 CSV（可用 Excel 另存），必需列见 REQUIRED_COLUMNS
输出：按地区和清单项分组的样本数、最小值、最大值、中位数、平均值、参考区间、异常提示
用途：江浙沪地铁工程单价数据收集后的入库校验和参考区间计算
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

REQUIRED_COLUMNS = [
    "地区",
    "清单项",
    "单位",
    "单价",
    "项目名称",
    "数据期别",
    "来源链接",
]

MIN_SAMPLES = 3
LOWER_FACTOR = 0.85
UPPER_FACTOR = 1.15
OUTLIER_FACTOR = 0.50


def load_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = [name.strip() for name in (reader.fieldnames or [])]
        missing = [name for name in REQUIRED_COLUMNS if name not in fieldnames]
        if missing:
            return [], [f"missing column: {', '.join(missing)}"]
        rows = [
            {(key or "").strip(): (value or "").strip() for key, value in row.items()}
            for row in reader
        ]
    return rows, errors


def parse_price(value: str) -> float | None:
    text = value.replace(",", "").replace("，", "").strip()
    if not text:
        return None
    try:
        price = float(text)
    except ValueError:
        return None
    return price if price > 0 else None


def validate_rows(rows: list[dict[str, str]]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    seen: dict[tuple[str, str, str], int] = {}
    for index, row in enumerate(rows, start=2):
        label = f"row {index}"
        empty = [name for name in REQUIRED_COLUMNS if not row.get(name)]
        if empty:
            errors.append(f"{label}: empty field {', '.join(empty)}")
            continue
        if parse_price(row["单价"]) is None:
            errors.append(f"{label}: invalid price '{row['单价']}'")
        link = row["来源链接"]
        if not (link.startswith("http://") or link.startswith("https://")):
            errors.append(f"{label}: source link must start with http:// or https://")
        key = (row["地区"], row["清单项"], row["项目名称"])
        if key in seen:
            errors.append(
                f"{label}: duplicate sample with row {seen[key]} ({key[0]}/{key[1]}/{key[2]})"
            )
        else:
            seen[key] = index
    for (region, item), group in group_rows(rows).items():
        if len(group) < MIN_SAMPLES:
            warnings.append(
                f"{region}/{item}: only {len(group)} sample(s), "
                f"{MIN_SAMPLES} recommended; treat interval as preliminary"
            )
    return errors, warnings


def group_rows(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        price = parse_price(row.get("单价", ""))
        if price is None:
            continue
        groups.setdefault((row["地区"], row["清单项"]), []).append(row)
    return groups


def round_to_ten(value: float) -> float:
    return round(value / 10) * 10


def summarize(rows: list[dict[str, str]], region: str, item: str) -> dict:
    group = group_rows(rows)[(region, item)]
    pairs = [(row, parse_price(row["单价"])) for row in group]
    pairs = [(row, price) for row, price in pairs if price is not None]
    prices = sorted(price for _, price in pairs)
    median = statistics.median(prices)
    mean = statistics.fmean(prices)
    low = round_to_ten(median * LOWER_FACTOR)
    high = round_to_ten(median * UPPER_FACTOR)
    outliers = [row for row, price in pairs if abs(price - median) > median * OUTLIER_FACTOR]
    return {
        "region": region,
        "item": item,
        "unit": group[0]["单位"],
        "count": len(group),
        "min": prices[0],
        "max": prices[-1],
        "median": median,
        "mean": mean,
        "low": low,
        "high": high,
        "outliers": [row["项目名称"] for row in outliers],
        "projects": [row["项目名称"] for row in group],
        "periods": sorted({row["数据期别"] for row in group}),
    }


def build_report(rows: list[dict[str, str]], errors: list[str], warnings: list[str]) -> str:
    lines = ["# 单价样本校验报告", ""]
    lines.append(f"- samples: {len(rows)}")
    lines.append(f"- groups: {len(group_rows(rows))}")
    lines.append(f"- errors: {len(errors)}")
    lines.append(f"- warnings: {len(warnings)}")
    lines.append("")
    lines.append("| 地区 | 清单项 | 单位 | 样本数 | 最小值 | 最大值 | 中位数 | 平均值 | 参考区间 | 异常样本 |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---|---|")
    for region, item in sorted(group_rows(rows)):
        summary = summarize(rows, region, item)
        outlier_text = "、".join(summary["outliers"]) if summary["outliers"] else "无"
        lines.append(
            f"| {summary['region']} | {summary['item']} | {summary['unit']} | "
            f"{summary['count']} | {summary['min']:,.0f} | {summary['max']:,.0f} | "
            f"{summary['median']:,.0f} | {summary['mean']:,.0f} | "
            f"{summary['low']:,.0f} ~ {summary['high']:,.0f} | {outlier_text} |"
        )
    lines.append("")
    lines.append("## 错误")
    lines.append("")
    if errors:
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 警告")
    lines.append("")
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- 无")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="校验单价样本并计算参考区间")
    parser.add_argument("csv", nargs="?", help="样本 CSV 路径")
    parser.add_argument(
        "--template",
        action="store_true",
        help="打印必需列，便于在 Excel 中建立表头",
    )
    args = parser.parse_args()

    if args.template:
        print(",".join(REQUIRED_COLUMNS))
        return 0

    if not args.csv:
        parser.print_help()
        return 2

    path = Path(args.csv)
    if not path.exists():
        print(f"missing file: {path}")
        return 2

    rows, load_errors = load_rows(path)
    if load_errors:
        print("\n".join(load_errors))
        return 1

    errors, warnings = validate_rows(rows)
    print(build_report(rows, errors, warnings))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
