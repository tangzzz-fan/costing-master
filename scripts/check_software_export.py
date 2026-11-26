#!/usr/bin/env python3
"""软件导出清单体检与问题回填工具。

用途：
- 读取广联达 GCCP/GBQ、新点、斯维尔、品茗、鲁班等计价软件导出的
  Excel/CSV 清单计价表，自动识别多级合并表头、分部层级、清单行和合计行。
- 检查清单编码、五要素、量价合价、分部小计树、合计闭合、跨表勾稽、公式完整
  性、单位、精度、结构化项目特征要素、2024 版费用口径等常见导出问题。
- 输出可直接回填到软件的问题清单（CSV，UTF-8 BOM）和 Markdown 体检报告。

边界：
- 不读取或修改 .GBQ/.GCCP/.24jz/.24jk/.24jt 等专有源文件；请先在软件中
  导出 Excel/CSV。
- 不替代软件自带校验、交易平台 XSD 校验、清标工具或评标委员会判断。
- 不编造定额编号、单价、费率或工程量；所有问题只标记为确定问题、疑似
  问题、待补资料或人工确认。

用法：
    python3 scripts/check_software_export.py 清单.xlsx --standard 2024 \
        --out 问题回填.csv --md 体检报告.md
    python3 scripts/check_software_export.py --template
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zipfile
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

from boq_parser import (
    CANONICAL_HEADERS,
    FIELD_ALIASES,
    Item,
    Sheet,
    clean_text,
    column_map,
    decimal_places,
    detect_header,
    format_decimal,
    format_money,
    is_boq_header,
    is_subtotal_name,
    is_total_name,
    load_sheets,
    map_header_row,
    md_cell,
    normalize_unit,
    parse_decimal,
    record_value,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FEATURE_RULES_PATH = ROOT / "data" / "boq-feature-rules.json"

ISSUE_HEADERS = [
    "序号",
    "问题编号",
    "单位工程/工作表",
    "数据行号",
    "清单编码",
    "清单名称",
    "字段",
    "原值",
    "问题类型",
    "建议处理",
    "判断等级",
    "依据/说明",
    "软件回填状态",
    "复核人",
]

UNIT_RULES = [
    (
        ("混凝土", "砼", "砂浆", "砌块", "砖", "土方", "回填", "碎石", "砂石", "垫层"),
        {"m3"},
        {"m2", "m", "t", "kg"},
    ),
    (("钢筋", "型钢", "钢板", "钢材", "铁件"), {"t", "kg"}, {"m3", "m2"}),
    (
        ("模板", "防水", "卷材", "涂料", "楼地面", "墙面", "天棚", "吊顶"),
        {"m2"},
        {"m3"},
    ),
    (("电缆", "电线", "管道", "桥架", "钢管", "栏杆", "扶手", "母线"), {"m"}, {"m3", "m2", "t"}),
    (("门", "窗"), {"m2", "樘", "扇", "套"}, {"m3"}),
    (
        (
            "设备",
            "柜",
            "箱",
            "泵",
            "风机",
            "灯具",
            "面板",
            "插座",
            "探测器",
            "摄像机",
            "控制器",
            "仪表",
            "温度计",
            "应变计",
            "挠度仪",
        ),
        {"台", "套", "个", "件", "组"},
        {"m", "m2", "m3"},
    ),
]


@dataclass
class Issue:
    rule_id: str
    sheet: str
    row: int
    code: str
    name: str
    field: str
    value: str
    problem: str
    suggestion: str
    level: str
    judgment: str
    basis: str

    def as_row(self, index: int) -> list[str]:
        return [
            str(index),
            self.rule_id,
            self.sheet,
            str(self.row),
            self.code,
            self.name,
            self.field,
            self.value,
            self.problem,
            self.suggestion,
            self.judgment,
            self.basis,
            "",
            "",
        ]


@dataclass
class SectionNode:
    row: int
    name: str
    declared_total: Decimal | None
    items: list[Item] = field(default_factory=list)
    child_sections: list["SectionNode"] = field(default_factory=list)


@dataclass
class SheetResult:
    name: str
    recognized: bool = False
    header_row: int | None = None
    skip_reason: str = ""
    sheet_role: str = "unknown"
    items: list[Item] = field(default_factory=list)
    sections: int = 0
    totals: int = 0
    quota_rows: int = 0
    sum_total: Decimal | None = None
    last_total: Decimal | None = None
    issues: list[Issue] = field(default_factory=list)


def load_feature_rules(path: Path | None = None) -> list[dict]:
    target = path or DEFAULT_FEATURE_RULES_PATH
    if not target.exists():
        return []
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rules = data.get("rules", []) if isinstance(data, dict) else []
    compiled: list[dict] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        elements = []
        for elem in rule.get("required_elements", []):
            pattern = elem.get("pattern", "")
            if not pattern:
                continue
            try:
                regex = re.compile(pattern)
            except re.error:
                continue
            elements.append(
                {
                    "name": elem.get("name", ""),
                    "regex": regex,
                    "hint": elem.get("hint", ""),
                }
            )
        compiled.append(
            {
                "id": rule.get("id", ""),
                "category": rule.get("category", ""),
                "source": rule.get("source", "references/boq-check-rules.md"),
                "match_keywords": rule.get("match_keywords", []),
                "exclude_keywords": rule.get("exclude_keywords", []),
                "required_elements": elements,
            }
        )
    return compiled


def check_feature_completeness(
    name: str, feature: str, feature_rules: list[dict]
) -> list[tuple[str, str, str]]:
    """Return list of (category, missing_names_str, source_and_hint) for missing required elements."""
    if not name or not feature or not feature_rules:
        return []
    combined = f"{name} {feature}"
    findings: list[tuple[str, str, str]] = []
    for rule in feature_rules:
        if any(ex in name for ex in rule["exclude_keywords"]):
            continue
        if not any(kw in name for kw in rule["match_keywords"]):
            continue
        missing_names: list[str] = []
        hints: list[str] = []
        for elem in rule["required_elements"]:
            if not elem["regex"].search(combined):
                missing_names.append(elem["name"])
                if elem["hint"]:
                    hints.append(elem["hint"])
        if missing_names:
            findings.append(
                (
                    rule["category"],
                    "、".join(missing_names),
                    f"{rule['source']}；{'；'.join(hints)}" if hints else rule["source"],
                )
            )
        break
    return findings


def has_invisible(value: str) -> bool:
    return bool(re.search(r"[\u200b\u200c\u200d\ufeff\u00a0\t\u3000]", value or ""))


def unit_warning(name: str, unit: str) -> str:
    normalized = normalize_unit(unit)
    if not normalized:
        return ""
    for keywords, expected, suspicious in UNIT_RULES:
        if any(keyword in name for keyword in keywords):
            if normalized in suspicious:
                return (
                    f"名称提示单位应为 {'/'.join(sorted(expected))}，"
                    f"实际为 {unit}；需人工确认是否单位错列"
                )
    return ""


def add_issue(
    issues: list[Issue],
    sheet: str,
    row: int,
    code: str,
    name: str,
    field_name: str,
    value: str,
    problem: str,
    suggestion: str,
    level: str,
    judgment: str,
    basis: str,
    rule_id: str,
) -> None:
    issues.append(
        Issue(
            rule_id=rule_id,
            sheet=sheet,
            row=row,
            code=code,
            name=name,
            field=field_name,
            value=value,
            problem=problem,
            suggestion=suggestion,
            level=level,
            judgment=judgment,
            basis=basis,
        )
    )


def check_standard_row(
    issues: list[Issue],
    sheet: str,
    row: int,
    name: str,
    standard: str,
) -> None:
    text = re.sub(r"\s+", "", name or "")
    if not text:
        return
    if "规费" in text:
        if standard == "2024":
            add_issue(
                issues,
                sheet,
                row,
                "",
                name,
                "项目名称",
                name,
                "2024 版项目出现“规费”独立费用行，疑似旧模板或旧口径",
                "核对项目适用标准和软件计价模板；2024 版不应把规费作为独立费用项，确认后调整费用结构",
                "警告",
                "疑似问题",
                "GB/T 50500-2024 费用组成口径；项目合同和软件项目设置",
                "SW-09",
            )
        elif standard == "unknown":
            add_issue(
                issues,
                sheet,
                row,
                "",
                name,
                "项目名称",
                name,
                "检测到“规费”行，需确认项目适用标准版本",
                "按招标/合同日期确认适用 2013 版还是 2024 版；2013 版可单列规费，2024 版不应单列",
                "提示",
                "人工确认",
                "GB/T 50500-2024 与 GB 50500-2013 过渡规则",
                "SW-09",
            )
    if standard == "2024" and "税金" in text and "增值税" not in text:
        add_issue(
            issues,
            sheet,
            row,
            "",
            name,
            "项目名称",
            name,
            "2024 版项目出现“税金”旧称，疑似旧模板",
            "核对是否应为增值税，确认税率、计税方式和软件模板",
            "警告",
            "疑似问题",
            "GB/T 50500-2024 增值税计列口径",
            "SW-09",
        )


def classify_sheet_role(name: str, recognized_boq: bool) -> str:
    clean = re.sub(r"\s+", "", name or "")
    if "汇总" in clean or "总表" in clean:
        if "其他项目" in clean:
            return "other_items"
        if "措施" in clean:
            return "measure"
        return "summary"
    if "总价措施" in clean or ("措施" in clean and not recognized_boq):
        return "measure"
    if "单价措施" in clean and "分部分项" not in clean:
        return "unit_measure"
    if "其他项目" in clean:
        return "other_items"
    if recognized_boq:
        return "boq"
    return "unknown"


def _audit_formula_consistency(
    sheet: Sheet,
    result: SheetResult,
    mapping: dict[str, int],
    total_rows: list[tuple[int, Decimal | None, str]],
) -> None:
    if not sheet.is_xlsx:
        return

    # 1. Flag formula cells missing cached <v> values (unrecalculated XLSX)
    missing_cache_rows: list[int] = []
    for item in result.items:
        if item.total_missing_cache or item.price_missing_cache:
            missing_cache_rows.append(item.row)
    if missing_cache_rows:
        sample_rows = ", ".join(str(r) for r in missing_cache_rows[:5])
        suffix = f" 等共 {len(missing_cache_rows)} 行" if len(missing_cache_rows) > 5 else ""
        add_issue(
            result.issues,
            sheet.name,
            missing_cache_rows[0],
            "",
            "",
            "公式缓存",
            f"第 {sample_rows} 行{suffix}",
            "存在未计算缓存值的公式单元格，无法获取准确数值",
            "请先在 Excel 或 WPS 中打开该工作簿并重新保存，使公式缓存值写入后再体检",
            "警告",
            "待补资料",
            "XLSX 公式缓存完整性（SW-12）",
            "SW-12",
        )

    # 2. Check hardcoded overrides in 合价 column when >= 70% of items use formulas
    total_col = mapping.get("合价")
    if total_col is not None and len(result.items) >= 5:
        valued_items = [item for item in result.items if item.total is not None]
        if len(valued_items) >= 5:
            formula_items = [item for item in valued_items if item.total_has_formula]
            ratio = len(formula_items) / len(valued_items)
            if ratio >= 0.70 and len(formula_items) < len(valued_items):
                for item in valued_items:
                    if not item.total_has_formula:
                        add_issue(
                            result.issues,
                            sheet.name,
                            item.row,
                            item.code,
                            item.name,
                            "合价",
                            item.total_text,
                            "同列多数清单项使用 Excel 公式，本行合价疑似手工写死静态数值",
                            "核对本行合价是否被人手工覆盖或调总价，在原软件中确认量价公式一致性",
                            "警告",
                            "疑似问题",
                            f"XLSX 公式一致性审计（本表 {len(formula_items)}/{len(valued_items)} 行含公式，SW-12）",
                            "SW-12",
                        )

    # 3. Check hardcoded overrides in subtotal/total rows when >= 70% use formulas
    if total_col is not None and len(total_rows) >= 3:
        valued_totals = [(r, v, n) for r, v, n in total_rows if v is not None and "本页" not in n]
        if len(valued_totals) >= 3:
            formula_totals = [
                (r, v, n)
                for r, v, n in valued_totals
                if (meta := sheet.cell_meta.get((r, total_col))) is not None and meta.has_formula
            ]
            if len(formula_totals) / len(valued_totals) >= 0.70 and len(formula_totals) < len(valued_totals):
                formula_row_set = {r for r, _, _ in formula_totals}
                for r, v, n in valued_totals:
                    if r not in formula_row_set:
                        add_issue(
                            result.issues,
                            sheet.name,
                            r,
                            "",
                            n,
                            "合计",
                            format_money(v),
                            "同表多数小计/合计行使用公式，本合计行疑似手工写死数值",
                            "核对是否人为修改小计/合计值，确认与明细汇总关系",
                            "警告",
                            "疑似问题",
                            "XLSX 公式一致性审计（SW-12）",
                            "SW-12",
                        )


def _check_top_sections(
    result: SheetResult,
    top_sections: list[SectionNode],
    tolerance: Decimal,
) -> None:
    """Validate section subtotal tree for top-subtotal layouts (e.g. outline BOQ exports)."""
    if not top_sections:
        return

    # Link parent sections (no direct items) to subsequent leaf sections until next parent
    leaf_sections: list[SectionNode] = []
    parent_sections: list[SectionNode] = []
    current_parent: SectionNode | None = None

    for sec in top_sections:
        if sec.items:
            leaf_sections.append(sec)
            if current_parent is not None:
                current_parent.child_sections.append(sec)
        else:
            if sec.declared_total is not None:
                current_parent = sec
                parent_sections.append(sec)

    # 1. Verify each leaf section with declared total against its direct items
    for sec in leaf_sections:
        if sec.declared_total is None:
            continue
        items_sum = sum(
            (item.total for item in sec.items if item.total is not None),
            Decimal("0"),
        )
        diff = sec.declared_total - items_sum
        if abs(diff) > tolerance:
            add_issue(
                result.issues,
                result.name,
                sec.row,
                "",
                sec.name,
                "分部小计",
                format_money(sec.declared_total),
                "分部小计与分部明细合价汇总不一致",
                f"分部「{sec.name}」明细合计 {format_money(items_sum)}，"
                f"分部小计 {format_money(sec.declared_total)}，"
                f"差额 {format_money(diff)}；核对分部内是否有漏行、隐藏行或四舍五入差异",
                "错误",
                "确定问题",
                "分部小计逐级闭合校验（SW-05）",
                "SW-05",
            )

    # 2. Verify parent sections against their child leaf sections
    for parent in parent_sections:
        if parent.declared_total is None or not parent.child_sections:
            continue
        child_totals = [
            child.declared_total
            for child in parent.child_sections
            if child.declared_total is not None
        ]
        if len(child_totals) != len(parent.child_sections):
            continue
        children_sum = sum(child_totals, Decimal("0"))
        diff = parent.declared_total - children_sum
        if abs(diff) > tolerance:
            add_issue(
                result.issues,
                result.name,
                parent.row,
                "",
                parent.name,
                "分部合计",
                format_money(parent.declared_total),
                "上级分部汇总与下属分部小计之和不一致",
                f"下属分部小计合计 {format_money(children_sum)}，"
                f"上级分部汇总 {format_money(parent.declared_total)}，"
                f"差额 {format_money(diff)}；核对汇总层级和漏计分部",
                "错误",
                "确定问题",
                "分部小计逐级闭合校验（SW-05）",
                "SW-05",
            )


def analyze_sheet(
    sheet: Sheet,
    standard: str,
    tolerance: Decimal,
    feature_rules: list[dict] | None = None,
) -> SheetResult:
    result = SheetResult(name=sheet.name)
    header = detect_header(sheet.rows)
    if header is None:
        result.sheet_role = classify_sheet_role(sheet.name, recognized_boq=False)
        result.skip_reason = "未识别到清单表头（需要项目编码、项目名称、工程量、单价/合价列）"
        return result

    mapping, header_index, data_start = header
    result.recognized = True
    result.sheet_role = classify_sheet_role(sheet.name, recognized_boq=True)
    result.header_row = sheet.rows[header_index][0]
    fields = column_map(mapping)
    rules = feature_rules if feature_rules is not None else load_feature_rules()

    if "计量单位" not in fields:
        add_issue(
            result.issues,
            sheet.name,
            result.header_row,
            "",
            "",
            "计量单位",
            "",
            "未识别到计量单位列",
            "在软件导出设置中保留计量单位列，或补充导出标准清单计价表",
            "警告",
            "待补资料",
            "清单五要素；软件导出包完整性",
            "SW-01",
        )
    if "项目特征" not in fields:
        add_issue(
            result.issues,
            sheet.name,
            result.header_row,
            "",
            "",
            "项目特征",
            "",
            "未识别到项目特征列，无法检查特征完整性",
            "补充导出项目特征描述列后再检查漏项和组价风险",
            "警告",
            "待补资料",
            "清单五要素；GB/T 50500-2024 项目特征要求",
            "SW-01",
        )
    if "合价" not in fields:
        add_issue(
            result.issues,
            sheet.name,
            result.header_row,
            "",
            "",
            "合价",
            "",
            "未识别到合价列，跳过合价与合计闭合检查",
            "补充合价列，或确认该表为未标价招标清单",
            "警告",
            "待补资料",
            "清单计价表结构",
            "SW-01",
        )
    if "综合单价" not in fields:
        add_issue(
            result.issues,
            sheet.name,
            result.header_row,
            "",
            "",
            "综合单价",
            "",
            "未识别到综合单价列，跳过单价异常和量价乘积检查",
            "补充综合单价列；如为未标价招标清单，可忽略本提示",
            "提示",
            "待补资料",
            "清单计价表结构",
            "SW-01",
        )

    total_rows: list[tuple[int, Decimal | None, str]] = []
    seen_codes: dict[str, int] = {}
    seen_items: dict[tuple[str, str, str], int] = {}
    first_header_mapping = dict(mapping)

    # Section tracking for both top-subtotal and bottom-subtotal layouts
    top_sections: list[SectionNode] = []
    current_top_section: SectionNode | None = None
    bottom_section_items: list[Item] = []
    bottom_section_name: str = ""

    price_col = mapping.get("综合单价")
    total_col = mapping.get("合价")

    for position in range(data_start, len(sheet.rows)):
        row_number, cells = sheet.rows[position]
        values = {
            field_name: record_value(cells, fields, field_name)
            for field_name in CANONICAL_HEADERS
        }
        if not any(value.strip() for value in cells):
            continue
        if not any(values[field_name].strip() for field_name in CANONICAL_HEADERS):
            continue

        repeated = map_header_row(cells)
        if is_boq_header(repeated):
            if repeated == first_header_mapping:
                continue
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                "",
                "",
                "工作表",
                "",
                "同一工作表检测到第二个不同的清单表头，后续行未处理",
                "按单位工程或表类型拆分导出，一个工作表只保留一张清单计价表",
                "警告",
                "待补资料",
                "软件导出包结构；清单表识别边界",
                "SW-01",
            )
            break

        code = values["项目编码"]
        name = values["项目名称"]
        feature = values["项目特征"]
        unit = values["计量单位"]
        qty_text = values["工程量"]
        price_text = values["综合单价"]
        total_text = values["合价"]
        provisional_text = values["暂估价"]
        quota_code = values["定额编号"]

        qty = parse_decimal(qty_text)
        price = parse_decimal(price_text)
        total = parse_decimal(total_text)
        provisional = parse_decimal(provisional_text)

        check_standard_row(
            result.issues, sheet.name, row_number, name, standard
        )

        if is_total_name(name):
            total_rows.append((row_number, total, name))
            if is_subtotal_name(name) and total is not None and bottom_section_items:
                sec_sum = sum(
                    (it.total for it in bottom_section_items if it.total is not None),
                    Decimal("0"),
                )
                diff = total - sec_sum
                if abs(diff) > tolerance:
                    label = bottom_section_name or name
                    add_issue(
                        result.issues,
                        sheet.name,
                        row_number,
                        "",
                        name,
                        "分部小计",
                        format_money(total),
                        "分部小计与分部明细合价汇总不一致",
                        f"分部「{label}」明细合计 {format_money(sec_sum)}，"
                        f"小计行 {format_money(total)}，差额 {format_money(diff)}；"
                        "核对分部内是否有漏行、隐藏行或手工改价",
                        "错误",
                        "确定问题",
                        "分部小计逐级闭合校验（SW-05）",
                        "SW-05",
                    )
                bottom_section_items = []
                bottom_section_name = ""
            continue

        if not code and quota_code:
            result.quota_rows += 1
            continue

        if not code and name and (price is None or qty is None):
            result.sections += 1
            sec_node = SectionNode(row=row_number, name=name, declared_total=total)
            top_sections.append(sec_node)
            current_top_section = sec_node
            if total is None:
                bottom_section_name = name
                bottom_section_items = []
            continue

        if not code and not name:
            continue

        if not code:
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                "",
                name,
                "项目编码",
                "",
                "清单行缺项目编码",
                "在软件中补齐清单编码；如该行为分部标题、定额子目或说明行，请在导出时排除或标记",
                "警告",
                "待补资料",
                "清单五要素；GB/T 50500-2024 项目编码要求",
                "SW-02",
            )

        price_meta = (
            sheet.cell_meta.get((row_number, price_col))
            if price_col is not None
            else None
        )
        total_meta = (
            sheet.cell_meta.get((row_number, total_col))
            if total_col is not None
            else None
        )

        item = Item(
            row=row_number,
            code=code,
            name=name,
            feature=feature,
            unit=unit,
            qty_text=qty_text,
            price_text=price_text,
            total_text=total_text,
            provisional_text=provisional_text,
            quota_code=quota_code,
            qty=qty,
            price=price,
            total=total,
            provisional=provisional,
            price_has_formula=bool(price_meta and price_meta.has_formula),
            total_has_formula=bool(total_meta and total_meta.has_formula),
            price_missing_cache=bool(price_meta and price_meta.missing_cached_value),
            total_missing_cache=bool(total_meta and total_meta.missing_cached_value),
        )
        result.items.append(item)
        if current_top_section is not None:
            current_top_section.items.append(item)
        bottom_section_items.append(item)

        if code:
            normalized_code = code.strip().upper()
            duplicate_key = normalized_code
            if normalized_code.isdigit() and len(normalized_code) == 11:
                duplicate_key = normalized_code.zfill(12)
            if duplicate_key in seen_codes:
                add_issue(
                    result.issues,
                    sheet.name,
                    row_number,
                    code,
                    name,
                    "项目编码",
                    code,
                    f"清单编码重复（首次出现于第 {seen_codes[duplicate_key]} 行）",
                    "核对是否重复列项或复制行未改编码；同一单位工程内清单编码应唯一",
                    "错误",
                    "确定问题",
                    "清单编码唯一性；软件导出数据完整性",
                    "SW-02",
                )
            else:
                seen_codes[duplicate_key] = row_number
            if normalized_code.isdigit() and len(normalized_code) == 11:
                add_issue(
                    result.issues,
                    sheet.name,
                    row_number,
                    code,
                    name,
                    "项目编码",
                    code,
                    "清单编码为 11 位，疑似 Excel 数值格式丢失前导零",
                    "把项目编码列设为文本后重新导出，核对是否为 12 位编码",
                    "警告",
                    "人工确认",
                    "12 位清单项目编码规则",
                    "SW-02",
                )
            elif not (
                re.fullmatch(r"\d{12}", normalized_code)
                or re.fullmatch(r"[A-Z]{1,3}\d+", normalized_code)
                or normalized_code.startswith(("补", "B"))
            ):
                add_issue(
                    result.issues,
                    sheet.name,
                    row_number,
                    code,
                    name,
                    "项目编码",
                    code,
                    "清单编码格式不在常见 12 位、行业字母编码或补充编码范围内",
                    "核对编码是否被截断、合并或错误导入；按招标清单编码执行",
                    "警告",
                    "人工确认",
                    "清单项目编码规则；招标文件",
                    "SW-02",
                )

        if not name:
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                code,
                "",
                "项目名称",
                "",
                "清单行缺项目名称",
                "在软件中补齐项目名称，避免清标时无法对应清单项",
                "错误",
                "确定问题",
                "清单五要素",
                "SW-03",
            )
        if not unit:
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                code,
                name,
                "计量单位",
                "",
                "清单行缺计量单位",
                "补齐计量单位，并与工程量计算标准核对",
                "警告",
                "待补资料",
                "清单五要素",
                "SW-03",
            )
        if "项目特征" in fields and not feature:
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                code,
                name,
                "项目特征",
                "",
                "项目特征为空",
                "补充影响组价的规格、材质、强度等级、厚度、部位等特征；软件中项目特征为空会导致组价和清标风险",
                "警告",
                "待补资料",
                "GB/T 50500-2024 项目特征描述要求",
                "SW-08",
            )
        elif "项目特征" in fields and feature:
            for category, missing_str, basis_hint in check_feature_completeness(
                name, feature, rules
            ):
                add_issue(
                    result.issues,
                    sheet.name,
                    row_number,
                    code,
                    name,
                    "项目特征",
                    feature,
                    f"{category}项目特征疑似缺少关键要素：{missing_str}",
                    f"对照设计图纸与做法表核实并补全：{missing_str}",
                    "警告",
                    "疑似问题",
                    basis_hint,
                    "SW-08",
                )

        if qty is None:
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                code,
                name,
                "工程量",
                qty_text,
                "工程量缺失或不是有效数字",
                "核对工程量列是否被合并、隐藏或导成了文本；补齐后重新导出",
                "警告",
                "待补资料",
                "清单五要素；软件导出字段完整性",
                "SW-03",
            )
        elif qty < 0:
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                code,
                name,
                "工程量",
                qty_text,
                "工程量为负数",
                "核对是否为冲减行、变更扣减或录入错误；负数量必须有明确依据",
                "错误",
                "确定问题",
                "清单工程量非负；变更扣减依据",
                "SW-06",
            )
        elif qty == 0:
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                code,
                name,
                "工程量",
                qty_text,
                "工程量为 0",
                "确认是否为暂列、备选或未发生项目；如非必要，避免保留 0 工程量清单项",
                "提示",
                "人工确认",
                "清单项目设置",
                "SW-06",
            )
        if price is None:
            if "综合单价" in fields:
                add_issue(
                    result.issues,
                    sheet.name,
                    row_number,
                    code,
                    name,
                    "综合单价",
                    price_text,
                    "综合单价缺失或不是有效数字",
                    "核对是否为未标价招标清单、暂估价或单价被隐藏；补齐后再核对合价",
                    "警告",
                    "待补资料",
                    "清单计价表结构",
                    "SW-03",
                )
        elif price < 0:
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                code,
                name,
                "综合单价",
                price_text,
                "综合单价为负数",
                "核对是否录入错误；负单价只能用于有明确合同依据的冲减",
                "错误",
                "确定问题",
                "综合单价非负；合同变更依据",
                "SW-06",
            )
        elif price == 0:
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                code,
                name,
                "综合单价",
                price_text,
                "综合单价为 0",
                "确认是否为甲供材、暂估价、漏报价或已包含在其他清单项；零单价必须在澄清中说明",
                "警告",
                "人工确认",
                "投标报价完整性；甲供材/暂估价口径",
                "SW-06",
            )
        if total is None:
            if "合价" in fields:
                add_issue(
                    result.issues,
                    sheet.name,
                    row_number,
                    code,
                    name,
                    "合价",
                    total_text,
                    "合价缺失或不是有效数字",
                    "补齐合价；如软件按公式计算，请检查公式是否被删除或导出为文本",
                    "警告",
                    "待补资料",
                    "清单计价表结构",
                    "SW-03",
                )
        elif qty is not None and price is not None:
            expected = qty * price
            difference = total - expected
            rounding_allowance = abs(qty) * Decimal("0.005") + tolerance
            if abs(difference) > tolerance:
                if abs(difference) <= rounding_allowance:
                    add_issue(
                        result.issues,
                        sheet.name,
                        row_number,
                        code,
                        name,
                        "合价",
                        total_text,
                        "合价与按显示综合单价计算存在四舍五入差异",
                        f"按显示单价 {format_decimal(price)} × {format_decimal(qty)} 计算为 "
                        f"{format_money(expected)}，合价为 {format_money(total)}，"
                        f"差额 {format_money(difference)}；可能由单价未显示的小数位造成，"
                        "核对软件单价精度和导出小数位后确认",
                        "提示",
                        "人工确认",
                        "江苏省电子招投标数据交换标准 6.0.4 计算规则；精度要求见 references/software-and-quotas.md 8.3",
                        "SW-04",
                    )
                else:
                    add_issue(
                        result.issues,
                        sheet.name,
                        row_number,
                        code,
                        name,
                        "合价",
                        total_text,
                        "合价不等于工程量×综合单价",
                        f"按 {format_decimal(qty)} × {format_decimal(price)} 计算应为 {format_money(expected)}，"
                        f"当前合价 {format_money(total)}；在软件中核对公式、四舍五入或手工改价",
                        "错误",
                        "确定问题",
                        "江苏省电子招投标数据交换标准 6.0.4：综合合价=综合单价×数量",
                        "SW-04",
                    )
        elif price == 0 and total not in (None, Decimal("0")):
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                code,
                name,
                "合价",
                total_text,
                "综合单价为 0 但合价不为 0",
                "核对单价是否漏填或合价是否手工修改",
                "错误",
                "确定问题",
                "综合合价=综合单价×数量",
                "SW-04",
            )

        if provisional is not None and price is not None and provisional > price:
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                code,
                name,
                "暂估价",
                provisional_text,
                "暂估单价大于综合单价",
                "核对暂估价与综合单价的包含关系，避免重复计取或高估",
                "警告",
                "人工确认",
                "暂估价口径；招标文件和合同",
                "SW-06",
            )

        if decimal_places(qty_text) > 6:
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                code,
                name,
                "工程量",
                qty_text,
                "工程量小数位超过 6 位",
                "按工程量计算标准和软件设置核对精度，避免导出精度失真",
                "提示",
                "人工确认",
                "江苏省电子招投标数据交换标准格式与精度要求；见 references/software-and-quotas.md 8.3：清单工程量最多 6 位",
                "SW-06",
            )
        if decimal_places(total_text) > 2:
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                code,
                name,
                "合价",
                total_text,
                "金额小数位超过 2 位",
                "核对软件金额精度和四舍五入设置，按标准保留 2 位",
                "提示",
                "人工确认",
                "江苏省电子招投标数据交换标准格式与精度要求；见 references/software-and-quotas.md 8.3：金额最多 2 位",
                "SW-06",
            )
        if decimal_places(price_text) > 2:
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                code,
                name,
                "综合单价",
                price_text,
                "综合单价小数位超过 2 位",
                "核对综合单价精度；人材机单价可按 4 位，但综合单价和金额通常保留 2 位",
                "提示",
                "人工确认",
                "江苏省电子招投标数据交换标准格式与精度要求；见 references/software-and-quotas.md 8.3：金额最多 2 位",
                "SW-06",
            )

        unit_message = unit_warning(name, unit)
        if unit_message:
            add_issue(
                result.issues,
                sheet.name,
                row_number,
                code,
                name,
                "计量单位",
                unit,
                unit_message,
                "对照项目特征和工程量计算标准确认单位；如为不同计量口径，补充换算说明",
                "警告",
                "疑似问题",
                "清单五要素；工程量计算标准",
                "SW-07",
            )

        item_key = (re.sub(r"\s+", "", name), re.sub(r"\s+", "", feature), normalize_unit(unit))
        if name and unit:
            if item_key in seen_items:
                add_issue(
                    result.issues,
                    sheet.name,
                    row_number,
                    code,
                    name,
                    "项目名称",
                    name,
                    f"同名、同特征、同单位的清单项重复出现（首次出现于第 {seen_items[item_key]} 行）",
                    "核对是否为不同部位/标段重复列项；如确需分列，应在项目特征或部位中区分",
                    "警告",
                    "疑似问题",
                    "清单列项唯一性；项目特征描述",
                    "SW-10",
                )
            else:
                seen_items[item_key] = row_number

        for field_name in ("项目编码", "项目名称", "计量单位", "项目特征"):
            raw_value = values[field_name]
            if has_invisible(raw_value):
                add_issue(
                    result.issues,
                    sheet.name,
                    row_number,
                    code,
                    name,
                    field_name,
                    raw_value,
                    "字段含不可见字符、全角空格或制表符",
                    "清理字段中的空格和不可见字符，避免平台一致性校验失败",
                    "警告",
                    "确定问题",
                    "江苏省电子招投标数据交换标准格式与精度要求；见 references/software-and-quotas.md 8.3",
                    "SW-11",
                )

    # Check top-subtotal section tree
    _check_top_sections(result, top_sections, tolerance)

    # Audit XLSX formula consistency (SW-12)
    _audit_formula_consistency(sheet, result, mapping, total_rows)

    result.totals = len(total_rows)
    result.sum_total = sum(
        (item.total for item in result.items if item.total is not None),
        Decimal("0"),
    )
    non_page_totals = [
        (row, value, name)
        for row, value, name in total_rows
        if "本页" not in name and value is not None
    ]
    grand_totals = [
        (row, value, name)
        for row, value, name in non_page_totals
        if not is_subtotal_name(name)
    ]
    check_totals = grand_totals if grand_totals else non_page_totals

    if check_totals:
        result.last_total = check_totals[-1][1]
        if len(check_totals) <= 2 and result.items:
            difference = result.last_total - result.sum_total
            if abs(difference) > tolerance:
                row_number = check_totals[-1][0]
                add_issue(
                    result.issues,
                    sheet.name,
                    row_number,
                    "",
                    check_totals[-1][2],
                    "合计",
                    format_money(result.last_total),
                    "合计行与清单项合价汇总不一致",
                    f"清单项合价合计 {format_money(result.sum_total)}，"
                    f"合计行 {format_money(result.last_total)}，"
                    f"差额 {format_money(difference)}；核对是否有漏行、隐藏行、分部小计或重复合计",
                    "错误",
                    "确定问题",
                    "江苏省电子招投标数据交换标准 6.0.4：分部分项工程项目费=清单项明细合计",
                    "SW-05",
                )
        elif len(check_totals) > 2:
            add_issue(
                result.issues,
                sheet.name,
                check_totals[-1][0],
                "",
                "",
                "合计",
                "",
                "检测到多个合计行，未自动判断汇总层级",
                "按单位工程或标段拆分后分别核对，避免把一个单位工程的合计与全部清单项比较",
                "警告",
                "人工确认",
                "清单汇总层级；单位工程/单项工程/项目汇总",
                "SW-05",
            )
    elif result.items:
        add_issue(
            result.issues,
            sheet.name,
            result.header_row or 0,
            "",
            "",
            "合计",
            "",
            "未找到可用的合计行，无法核对清单项汇总闭合",
            "补充分部分项合计行，或与单位工程汇总表、单项工程汇总表交叉核对",
            "警告",
            "待补资料",
            "清单汇总层级；软件导出包完整性",
            "SW-05",
        )

    return result


def _extract_fee_table_rows(sheet: Sheet) -> list[tuple[int, str, Decimal | None, str]]:
    """Extract (row_num, label, amount, raw_line) from summary/measure/other-item tables."""
    extracted: list[tuple[int, str, Decimal | None, str]] = []
    amount_col: int | None = None
    name_col: int | None = None

    for _, cells in sheet.rows[:15]:
        for idx, cell in enumerate(cells):
            norm = re.sub(r"\s+", "", cell or "")
            if any(k in norm for k in ("项目名称", "费用名称", "汇总内容", "费用项目")):
                name_col = idx
            if any(k in norm for k in ("金额", "合价", "费金额")):
                amount_col = idx
        if name_col is not None and amount_col is not None:
            break

    for row_num, cells in sheet.rows:
        if not any(str(c).strip() for c in cells):
            continue
        label = ""
        amount: Decimal | None = None
        if name_col is not None and name_col < len(cells):
            label = clean_text(cells[name_col])
        if amount_col is not None and amount_col < len(cells):
            amount = parse_decimal(cells[amount_col])
        if not label:
            for c in cells:
                c_clean = clean_text(c)
                if c_clean and parse_decimal(c_clean) is None:
                    label = c_clean
                    break
        if amount is None:
            for c in reversed(cells):
                val = parse_decimal(c)
                if val is not None:
                    amount = val
                    break
        if label:
            extracted.append((row_num, label, amount, " ".join(clean_text(c) for c in cells if c)))
    return extracted


def _find_fee_amount(
    rows: list[tuple[int, str, Decimal | None, str]],
    keywords: tuple[str, ...],
    exclude: tuple[str, ...] = (),
) -> tuple[int, str, Decimal] | None:
    for row_num, label, amount, _ in rows:
        compact = re.sub(r"\s+", "", label)
        if amount is None:
            continue
        if any(ex in compact for ex in exclude):
            continue
        if any(kw in compact for kw in keywords):
            return row_num, label, amount
    return None


def _reconcile_workbook(
    sheets: list[Sheet],
    results: list[SheetResult],
    standard: str,
    tolerance: Decimal,
) -> list[Issue]:
    """Cross-sheet reconciliation for multi-sheet export packages (SW-13)."""
    issues: list[Issue] = []
    sheet_by_name = {sheet.name: sheet for sheet in sheets}
    summary_sheets = [
        sheet_by_name[r.name]
        for r in results
        if not r.recognized and r.sheet_role == "summary"
    ]
    if not summary_sheets:
        # Also detect unnamed summary sheets by content
        for r in results:
            if r.recognized:
                continue
            sheet = sheet_by_name[r.name]
            fee_rows = _extract_fee_table_rows(sheet)
            if _find_fee_amount(fee_rows, ("分部分项工程",)) and _find_fee_amount(
                fee_rows, ("措施项目", "其他项目", "增值税", "工程造价")
            ):
                summary_sheets.append(sheet)
                r.sheet_role = "summary"

    if not summary_sheets:
        return issues

    # Aggregate detail sheet totals
    boq_results = [r for r in results if r.recognized and r.sheet_role == "boq"]
    boq_total = sum(
        (r.last_total if r.last_total is not None else (r.sum_total or Decimal("0")) for r in boq_results),
        Decimal("0"),
    )

    # Measure sheets (recognized unit_measure + fee-table lump measure sheets)
    measure_totals: list[Decimal] = []
    for r in results:
        if r.sheet_role == "unit_measure" and r.recognized:
            measure_totals.append(r.last_total if r.last_total is not None else (r.sum_total or Decimal("0")))
        elif r.sheet_role == "measure" and not r.recognized:
            fee_rows = _extract_fee_table_rows(sheet_by_name[r.name])
            hit = _find_fee_amount(fee_rows, ("合计", "措施项目费合计", "小计"))
            if hit:
                measure_totals.append(hit[2])
            else:
                # Sum non-header numeric rows
                vals = [amt for _, lbl, amt, _ in fee_rows if amt is not None and not any(k in lbl for k in ("表", "汇总", "项目名称"))]
                if vals:
                    measure_totals.append(sum(vals, Decimal("0")))

    # Other-items sheets
    other_totals: list[Decimal] = []
    tax_inclusive_specialty_provisional: Decimal | None = None
    for r in results:
        if r.sheet_role == "other_items":
            fee_rows = _extract_fee_table_rows(sheet_by_name[r.name])
            for _, lbl, amt, raw in fee_rows:
                if amt is not None and "专业工程暂估价" in re.sub(r"\s+", "", lbl):
                    if "含税" in raw or "含增值税" in raw or standard == "2024":
                        tax_inclusive_specialty_provisional = amt
            hit = _find_fee_amount(fee_rows, ("合计", "其他项目费合计"))
            if hit:
                other_totals.append(hit[2])
            else:
                sub_items = [
                    _find_fee_amount(fee_rows, ("暂列金额",)),
                    _find_fee_amount(fee_rows, ("专业工程暂估价",)),
                    _find_fee_amount(fee_rows, ("计日工",)),
                    _find_fee_amount(fee_rows, ("总承包服务费",)),
                ]
                present = [x[2] for x in sub_items if x is not None]
                if present:
                    other_totals.append(sum(present, Decimal("0")))

    for summary_sheet in summary_sheets:
        fee_rows = _extract_fee_table_rows(summary_sheet)
        for row_num, lbl, _, _ in fee_rows:
            check_standard_row(issues, summary_sheet.name, row_num, lbl, standard)

        # 1. Reconcile 分部分项工程费
        boq_hit = _find_fee_amount(fee_rows, ("分部分项工程",), exclude=("措施",))
        if boq_hit and boq_results:
            diff = boq_hit[2] - boq_total
            if abs(diff) > tolerance:
                add_issue(
                    issues,
                    summary_sheet.name,
                    boq_hit[0],
                    "",
                    boq_hit[1],
                    "跨表勾稽",
                    format_money(boq_hit[2]),
                    "汇总表分部分项工程费与分部分项清单明细合计不一致",
                    f"汇总表列示 {format_money(boq_hit[2])}，明细表合计 {format_money(boq_total)}，"
                    f"差额 {format_money(diff)}；核对是否有未导出单位工程或手工修改汇总表",
                    "错误",
                    "确定问题",
                    "导出包跨表勾稽校验（SW-13）",
                    "SW-13",
                )

        # 2. Reconcile 措施项目费
        measure_hit = _find_fee_amount(fee_rows, ("措施项目",), exclude=("安全", "文明"))
        if measure_hit and measure_totals:
            m_sum = sum(measure_totals, Decimal("0"))
            diff = measure_hit[2] - m_sum
            if abs(diff) > tolerance:
                add_issue(
                    issues,
                    summary_sheet.name,
                    measure_hit[0],
                    "",
                    measure_hit[1],
                    "跨表勾稽",
                    format_money(measure_hit[2]),
                    "汇总表措施项目费与措施明细表合计不一致",
                    f"汇总表列示 {format_money(measure_hit[2])}，措施表合计 {format_money(m_sum)}，"
                    f"差额 {format_money(diff)}；核对单价措施与总价措施是否完整导出",
                    "错误",
                    "确定问题",
                    "导出包跨表勾稽校验（SW-13）",
                    "SW-13",
                )

        # 3. Reconcile 其他项目费
        other_hit = _find_fee_amount(fee_rows, ("其他项目",))
        if other_hit and other_totals:
            o_sum = sum(other_totals, Decimal("0"))
            diff = other_hit[2] - o_sum
            if abs(diff) > tolerance:
                add_issue(
                    issues,
                    summary_sheet.name,
                    other_hit[0],
                    "",
                    other_hit[1],
                    "跨表勾稽",
                    format_money(other_hit[2]),
                    "汇总表其他项目费与其他项目明细表合计不一致",
                    f"汇总表列示 {format_money(other_hit[2])}，其他项目表合计 {format_money(o_sum)}，"
                    f"差额 {format_money(diff)}；核对暂列金额、暂估价、计日工、总承包服务费",
                    "错误",
                    "确定问题",
                    "导出包跨表勾稽校验（SW-13）",
                    "SW-13",
                )

        # 4. Check 2024 VAT base double-taxation on tax-inclusive 专业工程暂估价
        vat_hit = _find_fee_amount(fee_rows, ("增值税", "销项税额"))
        if standard == "2024" and vat_hit and boq_hit and measure_hit and other_hit:
            if tax_inclusive_specialty_provisional is None:
                spec_hit = _find_fee_amount(fee_rows, ("专业工程暂估价",))
                if spec_hit:
                    tax_inclusive_specialty_provisional = spec_hit[2]
            if tax_inclusive_specialty_provisional and tax_inclusive_specialty_provisional > 0:
                gross_base = boq_hit[2] + measure_hit[2] + other_hit[2]
                net_base = gross_base - tax_inclusive_specialty_provisional
                for rate in (Decimal("0.09"), Decimal("0.03")):
                    vat_on_gross = (gross_base * rate).quantize(Decimal("0.01"))
                    vat_on_net = (net_base * rate).quantize(Decimal("0.01"))
                    if (
                        abs(vat_hit[2] - vat_on_gross) <= max(tolerance, Decimal("1.00"))
                        and abs(vat_hit[2] - vat_on_net) > max(tolerance, Decimal("1.00"))
                    ):
                        add_issue(
                            issues,
                            summary_sheet.name,
                            vat_hit[0],
                            "",
                            vat_hit[1],
                            "增值税基数",
                            format_money(vat_hit[2]),
                            "疑似对含税专业工程暂估价重复计取增值税",
                            f"当前增值税 {format_money(vat_hit[2])} 接近按含专业工程暂估价基数 "
                            f"{format_money(gross_base)} × {int(rate * 100)}% = {format_money(vat_on_gross)} 计算；"
                            f"若专业工程暂估价 {format_money(tax_inclusive_specialty_provisional)} 为含税价，"
                            f"扣除后增值税应约 {format_money(vat_on_net)}，请核对含税口径",
                            "警告",
                            "疑似问题",
                            "GB/T 50500-2024 增值税计税基数口径（SW-13）",
                            "SW-13",
                        )
                        break

    return issues


def analyze_workbook(
    sheets: list[Sheet],
    standard: str,
    tolerance: Decimal,
    feature_rules: list[dict] | None = None,
) -> tuple[list[SheetResult], list[Issue]]:
    rules = feature_rules if feature_rules is not None else load_feature_rules()
    results = [
        analyze_sheet(sheet, standard, tolerance, feature_rules=rules)
        for sheet in sheets
    ]
    package_issues = _reconcile_workbook(sheets, results, standard, tolerance)
    return results, package_issues


def build_summary(
    results: list[SheetResult], package_issues: list[Issue] | None = None
) -> str:
    recognized = [result for result in results if result.recognized]
    skipped = [result for result in results if not result.recognized]
    issues = [issue for result in results for issue in result.issues] + list(
        package_issues or []
    )
    errors = sum(1 for issue in issues if issue.level == "错误")
    warnings = sum(1 for issue in issues if issue.level == "警告")
    tips = sum(1 for issue in issues if issue.level == "提示")
    items = sum(len(result.items) for result in recognized)
    lines = [
        "# 软件导出清单体检摘要",
        "",
        f"- 识别工作表：{len(recognized)}",
        f"- 跳过工作表：{len(skipped)}",
        f"- 清单项：{items}",
        f"- 问题：错误 {errors}，警告 {warnings}，提示 {tips}",
        "",
        "## 工作表",
        "",
        "| 工作表 | 表头行 | 清单项 | 分部/合计行 | 定额子目行 | 明细合价 | 合计行 | 差额 | 问题 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        if not result.recognized:
            lines.append(
                f"| {md_cell(result.name)} | - | - | - | - | - | - | - | 跳过：{md_cell(result.skip_reason)} |"
            )
            continue
        difference = ""
        if result.last_total is not None and result.sum_total is not None:
            difference = format_money(result.last_total - result.sum_total)
        lines.append(
            f"| {md_cell(result.name)} | {result.header_row or ''} | {len(result.items)} | "
            f"{result.sections + result.totals} | {result.quota_rows} | "
            f"{format_money(result.sum_total)} | {format_money(result.last_total)} | "
            f"{difference} | {len(result.issues)} |"
        )
    lines.extend(["", "## 问题"])
    lines.append("")
    if issues:
        lines.append(
            "| 序号 | 工作表 | 行号 | 清单编码 | 清单名称 | 问题 | 判断等级 |"
        )
        lines.append("|---|---|---:|---|---|---|---|")
        for index, issue in enumerate(issues[:200], start=1):
            lines.append(
                f"| {index} | {md_cell(issue.sheet)} | {issue.row} | "
                f"{md_cell(issue.code)} | {md_cell(issue.name)} | "
                f"{md_cell(issue.problem)} | {issue.judgment} |"
            )
        if len(issues) > 200:
            lines.append(f"| ... | 另有 {len(issues) - 200} 条问题，见问题回填 CSV | | | | | |")
    else:
        lines.append("- 未发现自动检查问题；仍需人工核对软件设置、地区资料、平台规则和清标要求。")
    lines.extend(
        [
            "",
            "## 边界",
            "",
            "- 本检查只读取导出的 Excel/CSV，不读取或修改 .GBQ/.GCCP/.24jz/.24jk/.24jt 等源文件。",
            "- 自动检查不能替代软件自带校验、交易平台 XSD 校验、清标工具、评标委员会或注册造价工程师判断。",
            "- 问题回填清单需由专业人员复核，并在软件中修改后重新导出、再次体检。",
        ]
    )
    return "\n".join(lines)


def write_issue_csv(
    results: list[SheetResult],
    path: Path,
    max_issues: int,
    package_issues: list[Issue] | None = None,
) -> int:
    issues = [issue for result in results for issue in result.issues] + list(
        package_issues or []
    )
    issues = issues[:max_issues]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(ISSUE_HEADERS)
        for index, issue in enumerate(issues, start=1):
            writer.writerow(
                [clean_text(value) for value in issue.as_row(index)]
            )
    return len(issues)


def print_template() -> None:
    print("规范表头：")
    print(",".join(CANONICAL_HEADERS))
    print()
    print("支持的表头别名：")
    for field_name, aliases in FIELD_ALIASES.items():
        print(f"- {field_name}: {'、'.join(aliases)}")
    print()
    print("问题回填 CSV 表头：")
    print(",".join(ISSUE_HEADERS))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="检查计量计价软件导出的清单表，输出问题回填清单"
    )
    parser.add_argument("path", nargs="?", help="导出的 .xlsx/.xlsm/.csv 文件")
    parser.add_argument(
        "--standard",
        choices=("2024", "2013", "unknown"),
        default="unknown",
        help="项目适用标准版本；默认 unknown，只提示不判定",
    )
    parser.add_argument("--out", help="问题回填 CSV 输出路径")
    parser.add_argument("--md", help="Markdown 体检报告输出路径")
    parser.add_argument("--sheet", help="只处理指定工作表")
    parser.add_argument(
        "--feature-rules",
        help="自定义项目特征必填规则 JSON 路径（默认 data/boq-feature-rules.json）",
    )
    parser.add_argument(
        "--tolerance",
        default="0.02",
        help="量价乘积、分部小计和合计的容差，默认 0.02 元",
    )
    parser.add_argument(
        "--max-issues",
        type=int,
        default=500,
        help="问题回填 CSV 最多输出条数，默认 500",
    )
    parser.add_argument(
        "--template",
        action="store_true",
        help="打印规范表头、别名和问题回填表头",
    )
    args = parser.parse_args()

    if args.template:
        print_template()
        return 0
    if not args.path:
        parser.print_help()
        return 2

    path = Path(args.path)
    if not path.exists():
        print(f"文件不存在：{path}")
        return 2
    suffix = path.suffix.lower()
    if suffix == ".xls":
        print("暂不直接解析 .xls；请在 Excel/WPS 中另存为 .xlsx 或 CSV 后重试。")
        return 2
    if suffix in {".gbq", ".gccp", ".24jz", ".24jk", ".24jt"}:
        print(
            "不解析软件专有文件或电子招投标源文件；请先在计价软件中导出 Excel/CSV。"
            "江苏 .24jz/.24jk/.24jt 的结构和一致性校验以交易平台/软件 XSD 校验为准。"
        )
        return 2

    try:
        sheets = load_sheets(path)
    except (ValueError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(f"读取失败：{exc}")
        return 1

    if args.sheet:
        sheets = [sheet for sheet in sheets if sheet.name == args.sheet]
        if not sheets:
            print(f"未找到工作表：{args.sheet}")
            return 2

    try:
        tolerance = Decimal(args.tolerance)
    except InvalidOperation:
        print(f"容差不是有效数字：{args.tolerance}")
        return 2
    if tolerance < 0:
        print(f"容差不能为负数：{args.tolerance}")
        return 2
    if args.max_issues < 1:
        print(f"--max-issues 必须大于 0：{args.max_issues}")
        return 2

    feature_rules = (
        load_feature_rules(Path(args.feature_rules))
        if args.feature_rules
        else load_feature_rules()
    )

    results, package_issues = analyze_workbook(
        sheets, args.standard, tolerance, feature_rules=feature_rules
    )
    if not any(result.recognized for result in results):
        print("未识别到清单计价表。请确认导出的是分部分项清单计价表，或使用 --template 查看表头要求。")
        for result in results:
            print(f"- {result.name}: {result.skip_reason}")
        return 1

    summary = build_summary(results, package_issues)
    print(summary)

    if args.out:
        written = write_issue_csv(
            results, Path(args.out), args.max_issues, package_issues=package_issues
        )
        print(f"\n问题回填 CSV：{args.out}（{written} 条）")
    if args.md:
        Path(args.md).write_text(summary + "\n", encoding="utf-8")
        print(f"Markdown 报告：{args.md}")

    issues = [issue for result in results for issue in result.issues] + package_issues
    return 1 if any(issue.level == "错误" for issue in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
