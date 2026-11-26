#!/usr/bin/env python3
"""共享的清单表格读取、合并单元格还原、公式元数据解析与表头识别模块。

供 `scripts/check_software_export.py` 与 `scripts/compare_boq.py` 共用，
零第三方依赖（仅使用 Python 标准库）。
"""

from __future__ import annotations

import csv
import io
import re
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
        return Decimal(text)
    except InvalidOperation:
        return None


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
    return format(value.normalize(), "f")


def md_cell(value: object) -> str:
    text = clean_text(value).replace("|", "／")
    return text or " "


@dataclass
class CellMeta:
    value: str = ""
    has_formula: bool = False
    formula: str = ""
    missing_cached_value: bool = False
    from_merge: bool = False


@dataclass
class Sheet:
    name: str
    rows: list[tuple[int, list[str]]]
    cell_meta: dict[tuple[int, int], CellMeta] = field(default_factory=dict)
    merged_ranges: list[tuple[int, int, int, int]] = field(default_factory=list)
    is_xlsx: bool = False


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
    provisional: Decimal | None = None
    price_has_formula: bool = False
    total_has_formula: bool = False
    total_missing_cache: bool = False
    price_missing_cache: bool = False


def _col_index(ref: str) -> int:
    letters = re.sub(r"[^A-Za-z]", "", ref or "").upper()
    if not letters:
        return 0
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def _parse_cell_ref(ref: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"([A-Za-z]+)(\d+)", (ref or "").strip())
    if not match:
        return None
    col = _col_index(match.group(1))
    row = int(match.group(2))
    return row, col


def _parse_merge_ranges(root: ET.Element) -> list[tuple[int, int, int, int]]:
    ranges: list[tuple[int, int, int, int]] = []
    for node in root.iter():
        if not node.tag.endswith("}mergeCell"):
            continue
        ref = node.get("ref") or ""
        if ":" not in ref:
            continue
        start_ref, end_ref = ref.split(":", 1)
        start = _parse_cell_ref(start_ref)
        end = _parse_cell_ref(end_ref)
        if start and end:
            r1, c1 = start
            r2, c2 = end
            ranges.append((min(r1, r2), min(c1, c2), max(r1, r2), max(c1, c2)))
    return ranges


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


def _parse_xlsx_sheet(
    xml: bytes, shared: list[str]
) -> tuple[list[tuple[int, list[str]]], dict[tuple[int, int], CellMeta], list[tuple[int, int, int, int]]]:
    root = ET.fromstring(xml)
    merged_ranges = _parse_merge_ranges(root)

    row_map: dict[int, list[str]] = {}
    cell_meta: dict[tuple[int, int], CellMeta] = {}

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
            has_formula = False
            formula_text = ""
            missing_cache = False

            for child in cell:
                if child.tag.endswith("}f"):
                    has_formula = True
                    formula_text = (child.text or "").strip()
                    break

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
                elif has_formula:
                    missing_cache = True

            cells[column] = value
            cell_meta[(row_number, column)] = CellMeta(
                value=value,
                has_formula=has_formula,
                formula=formula_text,
                missing_cached_value=missing_cache,
            )
        row_map[row_number] = cells

    # Propagate merged cells:
    # - Always propagate within top 30 rows (multi-row headers & title blocks)
    # - Also propagate single-column vertical merges anywhere (e.g., merged feature/unit)
    for r1, c1, r2, c2 in merged_ranges:
        top_left = cell_meta.get((r1, c1))
        top_val = top_left.value if top_left else ""
        if not top_val:
            continue
        is_header_zone = r1 <= 30 and r2 <= 30
        is_vertical_single_col = c1 == c2 and (r2 - r1) <= 10
        if not (is_header_zone or is_vertical_single_col):
            continue
        for r in range(r1, r2 + 1):
            if r not in row_map:
                row_map[r] = []
            row_cells = row_map[r]
            while len(row_cells) <= c2:
                row_cells.append("")
            for c in range(c1, c2 + 1):
                if r == r1 and c == c1:
                    continue
                if not row_cells[c]:
                    row_cells[c] = top_val
                    cell_meta[(r, c)] = CellMeta(
                        value=top_val,
                        has_formula=top_left.has_formula if top_left else False,
                        formula=top_left.formula if top_left else "",
                        missing_cached_value=top_left.missing_cached_value if top_left else False,
                        from_merge=True,
                    )

    rows = [(row_num, row_map[row_num]) for row_num in sorted(row_map)]
    return rows, cell_meta, merged_ranges


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
            rows, cell_meta, merged_ranges = _parse_xlsx_sheet(
                archive.read(target), shared
            )
            sheets.append(
                Sheet(
                    name=name,
                    rows=rows,
                    cell_meta=cell_meta,
                    merged_ranges=merged_ranges,
                    is_xlsx=True,
                )
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
    return [Sheet(name=path.stem, rows=rows, is_xlsx=False)]


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
        field_name = ALIAS_TO_FIELD.get(normalize_header(cell))
        if field_name and field_name not in mapping:
            mapping[field_name] = index
    return mapping


def map_multi_header_rows(row_group: list[list[str]]) -> dict[str, int]:
    """Merge 2 or 3 stacked header rows, preferring bottom-most specific labels."""
    mapping: dict[str, int] = {}
    width = max((len(row) for row in row_group), default=0)
    for index in range(width):
        chosen: str | None = None
        for row in reversed(row_group):
            cell = row[index] if index < len(row) else ""
            field_name = ALIAS_TO_FIELD.get(normalize_header(cell))
            if field_name:
                chosen = field_name
                break
        if chosen and chosen not in mapping:
            mapping[chosen] = index
    return mapping


def map_two_header_rows(top: list[str], bottom: list[str]) -> dict[str, int]:
    return map_multi_header_rows([top, bottom])


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
    """Return (field -> column, header row index in rows, data start index).

    Supports 1-row, 2-row, and 3-row composite headers (including merged top headers).
    """
    best: tuple[tuple[int, int, int, int], int, int, dict[str, int]] | None = None
    limit = min(30, len(rows))
    for index in range(limit):
        for span in (1, 2, 3):
            if index + span > len(rows):
                continue
            group = [rows[index + offset][1] for offset in range(span)]
            mapping = (
                map_header_row(group[0])
                if span == 1
                else map_multi_header_rows(group)
            )
            if is_boq_header(mapping):
                core, fields = header_score(mapping)
                candidate_key = (core, fields, -span, -index)
                candidate = (candidate_key, index, index + span, mapping)
                if best is None or candidate[0] > best[0]:
                    best = candidate
    if best is None:
        return None
    _, index, data_start, mapping = best
    return mapping, index, data_start


def column_map(mapping: dict[str, int]) -> dict[str, list[int]]:
    return {field_name: [index] for field_name, index in mapping.items()}


def record_value(
    cells: list[str], mapping: dict[str, list[int]], field_name: str
) -> str:
    for index in mapping.get(field_name, []):
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


def is_subtotal_name(name: str) -> bool:
    text = re.sub(r"\s+", "", name or "")
    return "小计" in text and "本页" not in text


def extract_boq_items(sheet: Sheet) -> tuple[list[Item], int | None, dict[str, int]]:
    """Extract normalized BOQ items from a recognized sheet (for diff/comparison)."""
    header = detect_header(sheet.rows)
    if header is None:
        return [], None, {}
    mapping, header_index, data_start = header
    fields = column_map(mapping)
    items: list[Item] = []

    for position in range(data_start, len(sheet.rows)):
        row_number, cells = sheet.rows[position]
        if not any(str(value).strip() for value in cells):
            continue
        repeated = map_header_row(cells)
        if is_boq_header(repeated):
            if repeated == mapping:
                continue
            break

        code = record_value(cells, fields, "项目编码")
        name = record_value(cells, fields, "项目名称")
        feature = record_value(cells, fields, "项目特征")
        unit = record_value(cells, fields, "计量单位")
        qty_text = record_value(cells, fields, "工程量")
        price_text = record_value(cells, fields, "综合单价")
        total_text = record_value(cells, fields, "合价")
        provisional_text = record_value(cells, fields, "暂估价")
        quota_code = record_value(cells, fields, "定额编号")

        qty = parse_decimal(qty_text)
        price = parse_decimal(price_text)
        total = parse_decimal(total_text)
        provisional = parse_decimal(provisional_text)

        if is_total_name(name):
            continue
        if not code and quota_code:
            continue
        if not code and name and (price is None or qty is None):
            continue
        if not code and not name:
            continue

        price_col = mapping.get("综合单价")
        total_col = mapping.get("合价")
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

        items.append(
            Item(
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
        )

    return items, sheet.rows[header_index][0], mapping
