#!/usr/bin/env python3
"""软件导出清单体检与问题回填工具。

用途：
- 读取广联达 GCCP/GBQ、新点、斯维尔、品茗、鲁班等计价软件导出的
  Excel/CSV 清单计价表，自动识别表头和清单行。
- 检查清单编码、五要素、量价合价、合计闭合、单位、精度、2024 版费用
  口径等常见导出问题。
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
import io
import re
import sys
import unicodedata
import zipfile
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

CANONICAL_HEADERS = [
    "序号",
    "项目编码",
    "项目名称",
    "项目特征",
    "计量单位",
    "工程量",
    "综合单价",
    "合价",
    "暂估价",
    "定额编号",
    "备注",
]

FIELD_ALIASES = {
    "序号": ["序号", "序", "no", "no."],
    "项目编码": [
        "项目编码",
        "清单编码",
        "编码",
        "项目编号",
        "清单编号",
        "项目代码",
        "清单项目编码",
    ],
    "项目名称": ["项目名称", "清单名称", "名称", "子目名称", "项目"],
    "项目特征": [
        "项目特征",
        "项目特征描述",
        "特征描述",
        "特征",
        "项目特征及工作内容",
    ],
    "计量单位": ["计量单位", "单位", "单位名称"],
    "工程量": ["工程量", "数量", "清单工程量", "工程数量", "计算工程量"],
    "综合单价": [
        "综合单价",
        "单价",
        "综合单价元",
        "单价元",
        "全费用综合单价",
    ],
    "合价": ["合价", "金额", "合价元", "金额元", "总价", "合计金额"],
    "暂估价": ["暂估价", "其中暂估价", "暂估单价", "暂估价元"],
    "定额编号": [
        "定额编号",
        "定额号",
        "子目编号",
        "定额子目编号",
        "定额项目编号",
    ],
    "备注": ["备注", "说明", "备注说明"],
}

CORE_FIELDS = ("项目编码", "项目名称", "计量单位", "工程量", "综合单价", "合价")
TOTAL_WORDS = ("合计", "小计", "总计", "本页小计", "分部分项合计", "单位工程合计")
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

UNIT_ALIASES = {
    "㎡": "m2",
    "m²": "m2",
    "平方米": "m2",
    "m³": "m3",
    "立方米": "m3",
    "米": "m",
    "吨": "t",
    "千克": "kg",
    "公斤": "kg",
    "台班": "台班",
}


def normalize_header(value: object) -> str:
    """Normalize a header cell for alias matching."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"\s+", "", text)
    text = text.replace("：", "").replace(":", "")
    text = re.sub(r"[（(][^）)]*[）)]", "", text)
    return text.lower()


ALIAS_TO_FIELD: dict[str, str] = {}
for _field, _aliases in FIELD_ALIASES.items():
    for _alias in _aliases:
        ALIAS_TO_FIELD[normalize_header(_alias)] = _field


def normalize_unit(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    text = re.sub(r"\s+", "", text)
    return UNIT_ALIASES.get(text, text)


def clean_text(value: object) -> str:
    text = str(value or "")
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return re.sub(r"\s+", " ", text).strip()


def clean_numeric(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.strip().replace(",", "").replace("，", "").replace(" ", "")
    text = text.replace("元", "")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    return text


def parse_decimal(value: object) -> Decimal | None:
    text = clean_numeric(value)
    if text in {"", "-", "—", "－", "/", "／", "--"}:
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    return number


def decimal_places(value: object) -> int:
    text = clean_numeric(value)
    if "." not in text:
        return 0
    fraction = re.sub(r"[^0-9]", "", text.split(".", 1)[1])
    return len(fraction.rstrip("0"))


def format_money(value: Decimal | None) -> str:
    if value is None:
        return ""
    return f"{value.quantize(Decimal('0.01')):,.2f}"


def format_decimal(value: Decimal | None) -> str:
    if value is None:
        return ""
    text = format(value.normalize(), "f")
    return text


def md_cell(value: object) -> str:
    text = clean_text(value).replace("|", "／")
    return text or " "


@dataclass
class Sheet:
    name: str
    rows: list[tuple[int, list[str]]]


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
class Item:
    row: int
    code: str
    name: str
    feature: str
    unit: str
    qty_text: str
    price_text: str
    total_text: str
    provisional_text: str
    quota_code: str
    qty: Decimal | None
    price: Decimal | None
    total: Decimal | None


@dataclass
class SheetResult:
    name: str
    recognized: bool = False
    header_row: int | None = None
    skip_reason: str = ""
    items: list[Item] = field(default_factory=list)
    sections: int = 0
    totals: int = 0
    quota_rows: int = 0
    sum_total: Decimal | None = None
    last_total: Decimal | None = None
    issues: list[Issue] = field(default_factory=list)


def _col_index(ref: str) -> int:
    letters = re.sub(r"[^A-Za-z]", "", ref or "").upper()
    if not letters:
        return 0
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for node in root:
        if not node.tag.endswith("}si"):
            continue
        parts = [
            child.text or ""
            for child in node.iter()
            if child.tag.endswith("}t") and child.text
        ]
        values.append("".join(parts))
    return values


def _parse_xlsx_sheet(xml: bytes, shared: list[str]) -> list[tuple[int, list[str]]]:
    root = ET.fromstring(xml)
    rows: list[tuple[int, list[str]]] = []
    for row_index, row in enumerate(
        (node for node in root.iter() if node.tag.endswith("}row")), start=1
    ):
        row_number = int(row.get("r") or row_index)
        cells: list[str] = []
        for cell in (node for node in row if node.tag.endswith("}c")):
            reference = cell.get("r") or ""
            column = _col_index(reference) if reference else len(cells)
            while len(cells) <= column:
                cells.append("")
            cell_type = cell.get("t")
            value = ""
            if cell_type == "inlineStr":
                value = "".join(
                    node.text or ""
                    for node in cell.iter()
                    if node.tag.endswith("}t")
                )
            else:
                raw = None
                for child in cell:
                    if child.tag.endswith("}v"):
                        raw = child.text
                        break
                if raw is not None:
                    if cell_type == "s" and raw.isdigit() and int(raw) < len(shared):
                        value = shared[int(raw)]
                    elif cell_type == "b":
                        value = "TRUE" if raw == "1" else "FALSE"
                    else:
                        value = raw
            cells[column] = value
        rows.append((row_number, cells))
    return rows


def _resolve_target(target: str) -> str:
    target = (target or "").lstrip("/")
    if target.startswith("xl/"):
        return target
    if target.startswith("../"):
        target = target[3:]
    return "xl/" + target


def load_xlsx_sheets(path: Path) -> list[Sheet]:
    sheets: list[Sheet] = []
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rel_map: dict[str, str] = {}
        if "xl/_rels/workbook.xml.rels" in names:
            rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            for rel in rels:
                rel_id = rel.get("Id")
                target = rel.get("Target")
                if rel_id and target:
                    rel_map[rel_id] = _resolve_target(target)
        shared = _shared_strings(archive)
        for node in workbook.iter():
            if not node.tag.endswith("}sheet"):
                continue
            name = node.get("name") or "Sheet"
            rel_id = ""
            for key, value in node.attrib.items():
                if key.endswith("}id"):
                    rel_id = value
                    break
            target = rel_map.get(rel_id, "")
            if target not in names:
                continue
            sheets.append(
                Sheet(name=name, rows=_parse_xlsx_sheet(archive.read(target), shared))
            )
    return sheets


def _decode_csv(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def load_csv_sheets(path: Path) -> list[Sheet]:
    text = _decode_csv(path)
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
    rows: list[tuple[int, list[str]]] = []
    for index, raw_row in enumerate(csv.reader(io.StringIO(text), dialect), start=1):
        rows.append((index, [str(cell) for cell in raw_row]))
    return [Sheet(name=path.stem, rows=rows)]


def load_sheets(path: Path) -> list[Sheet]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return load_csv_sheets(path)
    if suffix in {".xlsx", ".xlsm"}:
        return load_xlsx_sheets(path)
    raise ValueError(f"unsupported file type: {suffix or '(none)'}")


def map_header_row(cells: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, cell in enumerate(cells):
        field = ALIAS_TO_FIELD.get(normalize_header(cell))
        if field and field not in mapping:
            mapping[field] = index
    return mapping


def map_two_header_rows(top: list[str], bottom: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    width = max(len(top), len(bottom))
    for index in range(width):
        top_field = ALIAS_TO_FIELD.get(
            normalize_header(top[index] if index < len(top) else "")
        )
        bottom_field = ALIAS_TO_FIELD.get(
            normalize_header(bottom[index] if index < len(bottom) else "")
        )
        if bottom_field and bottom_field not in mapping:
            mapping[bottom_field] = index
        elif top_field and top_field not in mapping:
            mapping[top_field] = index
    return mapping


def is_boq_header(mapping: dict[str, int]) -> bool:
    fields = set(mapping)
    if "项目编码" not in fields or "项目名称" not in fields:
        return False
    if "工程量" not in fields:
        return False
    if "综合单价" not in fields and "合价" not in fields:
        return False
    return len(fields & set(CORE_FIELDS)) >= 4


def header_score(mapping: dict[str, int]) -> tuple[int, int]:
    return len(set(mapping) & set(CORE_FIELDS)), len(mapping)


def detect_header(
    rows: list[tuple[int, list[str]]]
) -> tuple[dict[str, int], int, int] | None:
    """Return (field -> column, header row index in rows, data start index)."""
    best: tuple[tuple[int, int, int, int], int, int, dict[str, int]] | None = None
    limit = min(30, len(rows))
    for index in range(limit):
        mapping = map_header_row(rows[index][1])
        if is_boq_header(mapping):
            core, fields = header_score(mapping)
            span = 1
            candidate_key = (core, fields, -span, -index)
            candidate = (candidate_key, index, index + 1, mapping)
            if best is None or candidate[0] > best[0]:
                best = candidate
        if index + 1 < len(rows):
            combined = map_two_header_rows(rows[index][1], rows[index + 1][1])
            if is_boq_header(combined):
                core, fields = header_score(combined)
                span = 2
                candidate_key = (core, fields, -span, -index)
                candidate = (candidate_key, index, index + 2, combined)
                if best is None or candidate[0] > best[0]:
                    best = candidate
    if best is None:
        return None
    _, index, data_start, mapping = best
    return mapping, index, data_start


def column_map(mapping: dict[str, int]) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for field, index in mapping.items():
        result[field] = [index]
    return result


def record_value(
    cells: list[str], mapping: dict[str, list[int]], field: str
) -> str:
    for index in mapping.get(field, []):
        if index < len(cells) and str(cells[index]).strip():
            return str(cells[index]).strip()
    return ""


def is_total_name(name: str) -> bool:
    text = re.sub(r"\s+", "", name or "")
    return (
        text in TOTAL_WORDS
        or text.endswith("合计")
        or text.endswith("小计")
        or text == "总计"
    )


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


def analyze_sheet(
    sheet: Sheet, standard: str, tolerance: Decimal
) -> SheetResult:
    result = SheetResult(name=sheet.name)
    header = detect_header(sheet.rows)
    if header is None:
        result.skip_reason = "未识别到清单表头（需要项目编码、项目名称、工程量、单价/合价列）"
        return result

    mapping, header_index, data_start = header
    result.recognized = True
    result.header_row = sheet.rows[header_index][0]
    fields = column_map(mapping)

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
            continue

        if not code and quota_code:
            result.quota_rows += 1
            continue

        if not code and name and (price is None or qty is None):
            result.sections += 1
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
        )
        result.items.append(item)

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
    if non_page_totals:
        result.last_total = non_page_totals[-1][1]
        if len(non_page_totals) <= 2 and result.items:
            difference = result.last_total - result.sum_total
            if abs(difference) > tolerance:
                row_number = non_page_totals[-1][0]
                add_issue(
                    result.issues,
                    sheet.name,
                    row_number,
                    "",
                    non_page_totals[-1][2],
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
        elif len(non_page_totals) > 2:
            add_issue(
                result.issues,
                sheet.name,
                non_page_totals[-1][0],
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


def build_summary(results: list[SheetResult]) -> str:
    recognized = [result for result in results if result.recognized]
    skipped = [result for result in results if not result.recognized]
    issues = [issue for result in results for issue in result.issues]
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


def write_issue_csv(results: list[SheetResult], path: Path, max_issues: int) -> int:
    issues = [issue for result in results for issue in result.issues]
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
        "--tolerance",
        default="0.02",
        help="量价乘积和合计的容差，默认 0.02 元",
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

    results = [
        analyze_sheet(sheet, args.standard, tolerance) for sheet in sheets
    ]
    if not any(result.recognized for result in results):
        print("未识别到清单计价表。请确认导出的是分部分项清单计价表，或使用 --template 查看表头要求。")
        for result in results:
            print(f"- {result.name}: {result.skip_reason}")
        return 1

    summary = build_summary(results)
    print(summary)

    if args.out:
        written = write_issue_csv(results, Path(args.out), args.max_issues)
        print(f"\n问题回填 CSV：{args.out}（{written} 条）")
    if args.md:
        Path(args.md).write_text(summary + "\n", encoding="utf-8")
        print(f"Markdown 报告：{args.md}")

    issues = [issue for result in results for issue in result.issues]
    return 1 if any(issue.level == "错误" for issue in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
