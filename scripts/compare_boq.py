#!/usr/bin/env python3
"""工程量清单双版本对比引擎（招标/投标、改前/改后、合同/结算）。

支持模式：
- tender-bid          : 招标清单 vs 投标报价（检测缺项/多项、名称/特征/单位/工程量/暂估价篡改）
- revision            : 修改前 vs 修改后导出包（统计体检问题关闭率、残余问题、新引入问题与金额变动）
- contract-settlement : 合同清单 vs 结算送审清单（自动分流原量项、超/减量项±15%调价提示、单价改动项、新增项、漏减项并校验差额闭合）

边界：
- 不解析 .GBQ/.GCCP/.24jz/.24jk/.24jt 等专有文件；仅处理软件导出的 Excel/CSV。
- 对比结果作为清标、复检和结算审核的工作底稿，不替代评标委员会或注册造价工程师判断。
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

from boq_parser import (
    Item,
    clean_text,
    extract_boq_items,
    format_decimal,
    format_money,
    load_sheets,
    md_cell,
    normalize_unit,
)
from check_software_export import analyze_workbook

DIFF_HEADERS = [
    "序号",
    "模式",
    "差异类型",
    "清单编码",
    "项目名称",
    "基线行号",
    "对比行号",
    "基线值",
    "对比值",
    "金额差额(元)",
    "级别",
    "判断等级",
    "说明/建议",
]


def _norm_code(code: str) -> str:
    cleaned = (code or "").strip().upper()
    if cleaned.isdigit() and len(cleaned) == 11:
        return cleaned.zfill(12)
    return cleaned


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _load_items_from_file(path: Path, sheet_name: str | None = None) -> tuple[list[Item], Decimal]:
    sheets = load_sheets(path)
    if sheet_name:
        sheets = [s for s in sheets if s.name == sheet_name]
        if not sheets:
            raise ValueError(f"未找到工作表：{sheet_name}")
    all_items: list[Item] = []
    for sheet in sheets:
        items, _, _ = extract_boq_items(sheet)
        all_items.extend(items)
    total_sum = sum(
        (item.total for item in all_items if item.total is not None),
        Decimal("0"),
    )
    return all_items, total_sum


def _index_by_code(items: list[Item]) -> dict[str, Item]:
    indexed: dict[str, Item] = {}
    for item in items:
        key = _norm_code(item.code) or f"ROW-{item.row}"
        if key not in indexed:
            indexed[key] = item
    return indexed


@dataclass
class DiffRecord:
    mode: str
    category: str
    code: str
    name: str
    base_row: str
    comp_row: str
    base_val: str
    comp_val: str
    amount_delta: Decimal | None
    level: str
    judgment: str
    note: str

    def as_row(self, index: int) -> list[str]:
        return [
            str(index),
            self.mode,
            self.category,
            self.code,
            self.name,
            self.base_row,
            self.comp_row,
            self.base_val,
            self.comp_val,
            format_money(self.amount_delta) if self.amount_delta is not None else "",
            self.level,
            self.judgment,
            self.note,
        ]


@dataclass
class CompareSummary:
    mode: str
    base_file: str
    comp_file: str
    base_count: int
    comp_count: int
    base_total: Decimal
    comp_total: Decimal
    records: list[DiffRecord]
    extra_metrics: dict[str, str]


def compare_tender_bid(
    base_path: Path,
    comp_path: Path,
    tolerance: Decimal,
    sheet_name: str | None = None,
) -> CompareSummary:
    base_items, base_total = _load_items_from_file(base_path, sheet_name)
    comp_items, comp_total = _load_items_from_file(comp_path, sheet_name)
    base_map = _index_by_code(base_items)
    comp_map = _index_by_code(comp_items)
    records: list[DiffRecord] = []

    for code, b_item in base_map.items():
        if code not in comp_map:
            records.append(
                DiffRecord(
                    mode="tender-bid",
                    category="投标缺项",
                    code=b_item.code,
                    name=b_item.name,
                    base_row=str(b_item.row),
                    comp_row="-",
                    base_val=format_decimal(b_item.qty),
                    comp_val="缺失",
                    amount_delta=-(b_item.total or Decimal("0")),
                    level="错误",
                    judgment="确定问题",
                    note="招标清单存在该项，投标文件缺失；需核查是否漏报或删项",
                )
            )
            continue

        c_item = comp_map[code]
        if _norm_text(b_item.name) != _norm_text(c_item.name):
            records.append(
                DiffRecord(
                    mode="tender-bid",
                    category="项目名称篡改",
                    code=b_item.code,
                    name=b_item.name,
                    base_row=str(b_item.row),
                    comp_row=str(c_item.row),
                    base_val=b_item.name,
                    comp_val=c_item.name,
                    amount_delta=None,
                    level="错误",
                    judgment="确定问题",
                    note="投标清单项目名称与招标清单不一致，不得擅自修改招标清单项",
                )
            )
        if b_item.feature and _norm_text(b_item.feature) != _norm_text(c_item.feature):
            records.append(
                DiffRecord(
                    mode="tender-bid",
                    category="项目特征篡改",
                    code=b_item.code,
                    name=b_item.name,
                    base_row=str(b_item.row),
                    comp_row=str(c_item.row),
                    base_val=b_item.feature,
                    comp_val=c_item.feature,
                    amount_delta=None,
                    level="错误",
                    judgment="确定问题",
                    note="投标清单项目特征描述与招标清单不一致，需清标澄清",
                )
            )
        if normalize_unit(b_item.unit) != normalize_unit(c_item.unit):
            records.append(
                DiffRecord(
                    mode="tender-bid",
                    category="计量单位篡改",
                    code=b_item.code,
                    name=b_item.name,
                    base_row=str(b_item.row),
                    comp_row=str(c_item.row),
                    base_val=b_item.unit,
                    comp_val=c_item.unit,
                    amount_delta=None,
                    level="错误",
                    judgment="确定问题",
                    note="投标清单计量单位与招标清单不一致，影响综合单价口径",
                )
            )
        if b_item.qty is not None and c_item.qty is not None:
            if abs(b_item.qty - c_item.qty) > Decimal("0.000001"):
                records.append(
                    DiffRecord(
                        mode="tender-bid",
                        category="招标工程量篡改",
                        code=b_item.code,
                        name=b_item.name,
                        base_row=str(b_item.row),
                        comp_row=str(c_item.row),
                        base_val=format_decimal(b_item.qty),
                        comp_val=format_decimal(c_item.qty),
                        amount_delta=(c_item.total or Decimal("0")) - (b_item.total or Decimal("0")),
                        level="错误",
                        judgment="确定问题",
                        note="投标工程量与招标清单不一致，违反招标清单工程量不得更改要求",
                    )
                )
        if (
            b_item.provisional is not None
            and b_item.provisional > 0
            and (c_item.provisional is None or abs(b_item.provisional - c_item.provisional) > tolerance)
        ):
            records.append(
                DiffRecord(
                    mode="tender-bid",
                    category="暂估价不一致",
                    code=b_item.code,
                    name=b_item.name,
                    base_row=str(b_item.row),
                    comp_row=str(c_item.row),
                    base_val=format_money(b_item.provisional),
                    comp_val=format_money(c_item.provisional),
                    amount_delta=None,
                    level="错误",
                    judgment="确定问题",
                    note="暂估价与招标清单不一致，投标不得擅自修改暂估价",
                )
            )

    for code, c_item in comp_map.items():
        if code not in base_map:
            records.append(
                DiffRecord(
                    mode="tender-bid",
                    category="投标多项",
                    code=c_item.code,
                    name=c_item.name,
                    base_row="-",
                    comp_row=str(c_item.row),
                    base_val="无",
                    comp_val=format_decimal(c_item.qty),
                    amount_delta=c_item.total or Decimal("0"),
                    level="错误",
                    judgment="确定问题",
                    note="投标文件出现招标清单之外的新增清单项，需清标核查",
                )
            )

    return CompareSummary(
        mode="tender-bid",
        base_file=str(base_path),
        comp_file=str(comp_path),
        base_count=len(base_items),
        comp_count=len(comp_items),
        base_total=base_total,
        comp_total=comp_total,
        records=records,
        extra_metrics={"发现篡改/缺多项": str(len(records))},
    )


def compare_revision(
    before_path: Path,
    after_path: Path,
    standard: str,
    tolerance: Decimal,
    sheet_name: str | None = None,
) -> CompareSummary:
    before_sheets = load_sheets(before_path)
    after_sheets = load_sheets(after_path)
    if sheet_name:
        before_sheets = [s for s in before_sheets if s.name == sheet_name]
        after_sheets = [s for s in after_sheets if s.name == sheet_name]

    before_res, before_pkg = analyze_workbook(before_sheets, standard, tolerance)
    after_res, after_pkg = analyze_workbook(after_sheets, standard, tolerance)

    before_issues = [i for r in before_res for i in r.issues] + before_pkg
    after_issues = [i for r in after_res for i in r.issues] + after_pkg

    def sig(issue) -> tuple[str, str, str, str]:
        return (issue.rule_id, _norm_code(issue.code), issue.field, issue.problem)

    before_counter = Counter(sig(i) for i in before_issues)
    after_counter = Counter(sig(i) for i in after_issues)

    closed_counter = before_counter - after_counter
    new_counter = after_counter - before_counter
    remaining_counter = before_counter & after_counter

    closed_count = sum(closed_counter.values())
    remaining_count = sum(remaining_counter.values())
    new_count = sum(new_counter.values())

    records: list[DiffRecord] = []
    for (rule_id, code, field_name, prob), count in sorted(closed_counter.items()):
        records.append(
            DiffRecord(
                mode="revision",
                category="问题已关闭",
                code=code,
                name=f"[{rule_id}] {field_name}",
                base_row="-",
                comp_row="-",
                base_val=f"出现 {count} 次",
                comp_val="已消除",
                amount_delta=None,
                level="提示",
                judgment="已闭合",
                note=prob,
            )
        )
    for (rule_id, code, field_name, prob), count in sorted(remaining_counter.items()):
        records.append(
            DiffRecord(
                mode="revision",
                category="问题仍存在",
                code=code,
                name=f"[{rule_id}] {field_name}",
                base_row="-",
                comp_row="-",
                base_val=f"原 {before_counter[(rule_id, code, field_name, prob)]} 次",
                comp_val=f"现 {count} 次",
                amount_delta=None,
                level="警告",
                judgment="待修正",
                note=prob,
            )
        )
    for (rule_id, code, field_name, prob), count in sorted(new_counter.items()):
        # Check severity in after_issues
        matched_levels = [
            i.level for i in after_issues if sig(i) == (rule_id, code, field_name, prob)
        ]
        lvl = "错误" if "错误" in matched_levels else "警告"
        records.append(
            DiffRecord(
                mode="revision",
                category="新引入问题",
                code=code,
                name=f"[{rule_id}] {field_name}",
                base_row="-",
                comp_row="-",
                base_val="无",
                comp_val=f"新增 {count} 次",
                amount_delta=None,
                level=lvl,
                judgment="需核查",
                note=prob,
            )
        )

    before_items = [i for r in before_res for i in r.items]
    after_items = [i for r in after_res for i in r.items]
    before_total = sum((i.total for i in before_items if i.total is not None), Decimal("0"))
    after_total = sum((i.total for i in after_items if i.total is not None), Decimal("0"))
    after_errors = sum(1 for i in after_issues if i.level == "错误")

    closure_rate = (
        f"{(100.0 * closed_count / len(before_issues)):.1f}%"
        if before_issues
        else "100.0%"
    )
    return CompareSummary(
        mode="revision",
        base_file=str(before_path),
        comp_file=str(after_path),
        base_count=len(before_items),
        comp_count=len(after_items),
        base_total=before_total,
        comp_total=after_total,
        records=records,
        extra_metrics={
            "改前问题总数": str(len(before_issues)),
            "改后问题总数": str(len(after_issues)),
            "已关闭问题": str(closed_count),
            "仍存在问题": str(remaining_count),
            "新引入问题": str(new_count),
            "问题关闭率": closure_rate,
            "改后剩余确定错误": str(after_errors),
        },
    )


def compare_contract_settlement(
    contract_path: Path,
    settlement_path: Path,
    tolerance: Decimal,
    qty_threshold: Decimal,
    sheet_name: str | None = None,
) -> CompareSummary:
    c_items, c_total = _load_items_from_file(contract_path, sheet_name)
    s_items, s_total = _load_items_from_file(settlement_path, sheet_name)
    c_map = _index_by_code(c_items)
    s_map = _index_by_code(s_items)
    records: list[DiffRecord] = []

    counts = {
        "合同内原量项": 0,
        "工程量变化项": 0,
        "超阈值调价提示项": 0,
        "合同单价被改动项": 0,
        "新增清单项": 0,
        "合同内缺失项": 0,
    }
    category_deltas: dict[str, Decimal] = {
        "合同内原量项": Decimal("0"),
        "工程量变化项": Decimal("0"),
        "合同单价被改动项": Decimal("0"),
        "新增清单项": Decimal("0"),
        "合同内缺失项": Decimal("0"),
    }

    for code, c_item in c_map.items():
        c_amt = c_item.total or Decimal("0")
        if code not in s_map:
            counts["合同内缺失项"] += 1
            delta = -c_amt
            category_deltas["合同内缺失项"] += delta
            records.append(
                DiffRecord(
                    mode="contract-settlement",
                    category="合同内缺失项（疑似漏减/未实施）",
                    code=c_item.code,
                    name=c_item.name,
                    base_row=str(c_item.row),
                    comp_row="-",
                    base_val=format_money(c_amt),
                    comp_val="0.00",
                    amount_delta=delta,
                    level="警告",
                    judgment="疑似问题",
                    note="合同清单存在而结算书缺失，核实是否为甩项、未实施或漏报",
                )
            )
            continue

        s_item = s_map[code]
        s_amt = s_item.total or Decimal("0")
        delta = s_amt - c_amt

        price_changed = (
            c_item.price is not None
            and s_item.price is not None
            and abs(s_item.price - c_item.price) > tolerance
        )
        qty_changed = (
            c_item.qty is not None
            and s_item.qty is not None
            and abs(s_item.qty - c_item.qty) > Decimal("0.000001")
        )

        if price_changed:
            counts["合同单价被改动项"] += 1
            category_deltas["合同单价被改动项"] += delta
            records.append(
                DiffRecord(
                    mode="contract-settlement",
                    category="合同单价被改动",
                    code=c_item.code,
                    name=c_item.name,
                    base_row=str(c_item.row),
                    comp_row=str(s_item.row),
                    base_val=format_money(c_item.price),
                    comp_val=format_money(s_item.price),
                    amount_delta=delta,
                    level="错误",
                    judgment="疑似问题",
                    note="结算综合单价与合同不一致，需核查是否触发工程量超幅调价或合同变更调价依据",
                )
            )
        elif qty_changed:
            counts["工程量变化项"] += 1
            category_deltas["工程量变化项"] += delta
            ratio = (
                (s_item.qty - c_item.qty) / c_item.qty
                if c_item.qty not in (None, Decimal("0"))
                else None
            )
            over_threshold = ratio is not None and abs(ratio) > qty_threshold
            if over_threshold:
                counts["超阈值调价提示项"] += 1
                pct = f"{ratio * Decimal('100'):+.1f}%"
                records.append(
                    DiffRecord(
                        mode="contract-settlement",
                        category="工程量变化（超调价阈值）",
                        code=c_item.code,
                        name=c_item.name,
                        base_row=str(c_item.row),
                        comp_row=str(s_item.row),
                        base_val=format_decimal(c_item.qty),
                        comp_val=f"{format_decimal(s_item.qty)} ({pct})",
                        amount_delta=delta,
                        level="警告",
                        judgment="人工确认",
                        note=f"工程量变化幅度 {pct} 超过 ±{qty_threshold * Decimal('100'):.0f}%，核对合同调价条款与不平衡报价风险",
                    )
                )
            else:
                pct = f"{ratio * Decimal('100'):+.1f}%" if ratio is not None else "N/A"
                records.append(
                    DiffRecord(
                        mode="contract-settlement",
                        category="工程量变化（阈值内）",
                        code=c_item.code,
                        name=c_item.name,
                        base_row=str(c_item.row),
                        comp_row=str(s_item.row),
                        base_val=format_decimal(c_item.qty),
                        comp_val=f"{format_decimal(s_item.qty)} ({pct})",
                        amount_delta=delta,
                        level="提示",
                        judgment="人工确认",
                        note="工程量变化在合同常规幅度内，核对竣工图与计量依据",
                    )
                )
        else:
            counts["合同内原量项"] += 1
            category_deltas["合同内原量项"] += delta

    for code, s_item in s_map.items():
        if code not in c_map:
            counts["新增清单项"] += 1
            s_amt = s_item.total or Decimal("0")
            category_deltas["新增清单项"] += s_amt
            records.append(
                DiffRecord(
                    mode="contract-settlement",
                    category="新增清单项",
                    code=s_item.code,
                    name=s_item.name,
                    base_row="-",
                    comp_row=str(s_item.row),
                    base_val="无",
                    comp_val=format_money(s_amt),
                    amount_delta=s_amt,
                    level="警告",
                    judgment="人工确认",
                    note="合同清单外新增项目，核对变更指令、签证证据链及新组价/类似价适用顺序",
                )
            )

    delta_sum = sum(category_deltas.values(), Decimal("0"))
    expected_delta = s_total - c_total
    closure_diff = delta_sum - expected_delta

    return CompareSummary(
        mode="contract-settlement",
        base_file=str(contract_path),
        comp_file=str(settlement_path),
        base_count=len(c_items),
        comp_count=len(s_items),
        base_total=c_total,
        comp_total=s_total,
        records=records,
        extra_metrics={
            "合同内原量项": str(counts["合同内原量项"]),
            "工程量变化项": f"{counts['工程量变化项']}（其中超阈值 {counts['超阈值调价提示项']} 项）",
            "合同单价被改动项": str(counts["合同单价被改动项"]),
            "新增清单项": str(counts["新增清单项"]),
            "合同内缺失项": str(counts["合同内缺失项"]),
            "分类差额汇总": format_money(delta_sum),
            "总价净差额": format_money(expected_delta),
            "闭合差额": format_money(closure_diff),
        },
    )


def render_markdown(summary: CompareSummary) -> str:
    lines = [
        f"# 工程量清单对比报告（{summary.mode}）",
        "",
        f"- 基线文件：{summary.base_file}（{summary.base_count} 项，合价 {format_money(summary.base_total)} 元）",
        f"- 对比文件：{summary.comp_file}（{summary.comp_count} 项，合价 {format_money(summary.comp_total)} 元）",
        f"- 总价差额：{format_money(summary.comp_total - summary.base_total)} 元",
        "",
        "## 关键统计",
        "",
        "| 指标 | 数值 |",
        "|---|---|",
    ]
    for k, v in summary.extra_metrics.items():
        lines.append(f"| {md_cell(k)} | {md_cell(v)} |")

    lines.extend(["", "## 差异明细", ""])
    if summary.records:
        lines.append("| 序号 | 差异类型 | 清单编码 | 项目名称 | 基线值 | 对比值 | 金额差额(元) | 判断等级 |")
        lines.append("|---:|---|---|---|---|---|---:|---|")
        for idx, rec in enumerate(summary.records[:200], start=1):
            delta_str = format_money(rec.amount_delta) if rec.amount_delta is not None else "-"
            lines.append(
                f"| {idx} | {md_cell(rec.category)} | {md_cell(rec.code)} | {md_cell(rec.name)} | "
                f"{md_cell(rec.base_val)} | {md_cell(rec.comp_val)} | {delta_str} | {rec.judgment} |"
            )
    else:
        lines.append("- 未发现清单差异。")
    lines.extend(
        [
            "",
            "## 边界声明",
            "",
            "- 本对比报告为工作底稿，不替代评标委员会判断、法律定性或注册造价工程师签章。",
        ]
    )
    return "\n".join(lines)


def write_diff_csv(summary: CompareSummary, path: Path) -> int:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(DIFF_HEADERS)
        for idx, rec in enumerate(summary.records, start=1):
            writer.writerow([clean_text(v) for v in rec.as_row(idx)])
    return len(summary.records)


def _check_input_path(path: Path) -> int | None:
    if not path.exists():
        print(f"文件不存在：{path}")
        return 2
    suffix = path.suffix.lower()
    if suffix in {".gbq", ".gccp", ".24jz", ".24jk", ".24jt"}:
        print(f"不解析软件专有文件：{path}；请先导出 Excel/CSV。")
        return 2
    if suffix not in {".csv", ".xlsx", ".xlsm"}:
        print(f"不支持的文件格式：{path}")
        return 2
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="工程量清单双版本对比工具（tender-bid / revision / contract-settlement）"
    )
    parser.add_argument("base", help="基线清单文件（招标清单 / 修改前 / 合同清单）")
    parser.add_argument("target", help="对比清单文件（投标报价 / 修改后 / 结算送审）")
    parser.add_argument(
        "--mode",
        choices=("tender-bid", "revision", "contract-settlement"),
        required=True,
        help="对比模式",
    )
    parser.add_argument(
        "--standard",
        choices=("2024", "2013", "unknown"),
        default="2024",
        help="revision 模式使用的标准版本（默认 2024）",
    )
    parser.add_argument(
        "--tolerance",
        default="0.02",
        help="金额容差（默认 0.02 元）",
    )
    parser.add_argument(
        "--qty-threshold",
        default="0.15",
        help="contract-settlement 模式工程量变化提示阈值（默认 0.15 即 ±15%）",
    )
    parser.add_argument("--sheet", help="只对比指定工作表")
    parser.add_argument("--out", help="差异明细 CSV 输出路径（UTF-8 BOM）")
    parser.add_argument("--md", help="Markdown 对比报告输出路径")
    args = parser.parse_args()

    base_path = Path(args.base)
    target_path = Path(args.target)
    for p in (base_path, target_path):
        code = _check_input_path(p)
        if code is not None:
            return code

    try:
        tolerance = Decimal(args.tolerance)
        qty_threshold = Decimal(args.qty_threshold)
    except InvalidOperation:
        print("容差或阈值参数不是有效数字")
        return 2

    try:
        if args.mode == "tender-bid":
            summary = compare_tender_bid(base_path, target_path, tolerance, args.sheet)
            has_error = any(r.level == "错误" for r in summary.records)
        elif args.mode == "revision":
            summary = compare_revision(
                base_path, target_path, args.standard, tolerance, args.sheet
            )
            has_error = int(summary.extra_metrics.get("改后剩余确定错误", "0")) > 0
        else:
            summary = compare_contract_settlement(
                base_path, target_path, tolerance, qty_threshold, args.sheet
            )
            has_error = any(r.level == "错误" for r in summary.records)
    except (ValueError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(f"读取或对比失败：{exc}")
        return 2

    md = render_markdown(summary)
    print(md)
    if args.out:
        written = write_diff_csv(summary, Path(args.out))
        print(f"\n差异明细 CSV：{args.out}（{written} 条）")
    if args.md:
        Path(args.md).write_text(md + "\n", encoding="utf-8")
        print(f"Markdown 报告：{args.md}")

    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())
