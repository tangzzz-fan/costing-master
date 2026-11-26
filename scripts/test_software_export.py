#!/usr/bin/env python3
"""
软件导出清单体检逻辑测试。

数据：
- 真实公开清单：江苏政府采购网《2025 年城市安全建设-市管 12 座桥梁
  轻量化监测设备安装》汉桥分部分项清单摘录。
- 问题样例：在上述真实清单基础上改造，仅用于验证检查规则。

覆盖：
- CSV/XLSX/GBK 读取
- 标题行、表头、分部行、合计行识别
- 编码、五要素、量价、合计、单位、精度、2024 规费等检查
- 问题回填 CSV 表头、BOM、退出码和 CLI 边界
"""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import zipfile
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

from check_software_export import (
    ISSUE_HEADERS,
    analyze_sheet,
    analyze_workbook,
    load_sheets,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = ROOT / "test-cases" / "fixtures" / "software-export"
REAL_CSV = FIXTURE_DIR / "hanqiao-real-boq.csv"
ISSUE_CSV = FIXTURE_DIR / "hanqiao-export-issues.csv"
SCRIPT = ROOT / "scripts" / "check_software_export.py"


def analyze(path: Path, standard: str = "2024"):
    sheets = load_sheets(path)
    return [analyze_sheet(sheet, standard, Decimal("0.02")) for sheet in sheets]


def problems(result) -> list[str]:
    return [issue.problem for issue in result.issues]


def levels(result, level: str) -> int:
    return sum(1 for issue in result.issues if issue.level == level)


def column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def build_xlsx(source: Path, target: Path) -> None:
    """Build a minimal xlsx with one sheet and shared strings."""
    rows = list(csv.reader(source.open(encoding="utf-8-sig", newline="")))
    shared: list[str] = []
    positions: dict[str, int] = {}

    def shared_index(value: str) -> int:
        if value not in positions:
            positions[value] = len(shared)
            shared.append(value)
        return positions[value]

    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            if value == "":
                continue
            reference = f"{column_name(column_index)}{row_index}"
            try:
                float(value.replace(",", ""))
            except ValueError:
                cells.append(
                    f'<c r="{reference}" t="s"><v>{shared_index(value)}</v></c>'
                )
            else:
                cells.append(f'<c r="{reference}"><v>{escape(value)}</v></c>')
        sheet_rows.append(f'<row r="{row_index}">' + "".join(cells) + "</row>")

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>" + "".join(sheet_rows) + "</sheetData></worksheet>"
    )
    shared_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared)}" uniqueCount="{len(shared)}">'
        + "".join(f"<si><t>{escape(item)}</t></si>" for item in shared)
        + "</sst>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="分部分项" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
        'Target="sharedStrings.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/sharedStrings.xml", shared_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_real_boq_header_and_items() -> None:
    result = analyze(REAL_CSV)[0]
    assert result.recognized, result.skip_reason
    assert result.header_row == 6, result.header_row
    assert len(result.items) == 21, len(result.items)
    assert result.sections == 4, result.sections
    assert result.totals == 2, result.totals
    assert result.sum_total == Decimal("216994.83"), result.sum_total
    assert result.last_total == Decimal("216994.84"), result.last_total
    print("[通过] 真实公开清单：表头第 6 行、21 个清单项、合计 216,994.84")


def test_real_boq_has_no_false_errors() -> None:
    result = analyze(REAL_CSV)[0]
    assert levels(result, "错误") == 0, problems(result)
    assert levels(result, "警告") == 8, levels(result, "警告")
    assert levels(result, "提示") == 5, levels(result, "提示")
    assert any("项目特征为空" in problem for problem in problems(result))
    assert any("四舍五入差异" in problem for problem in problems(result))
    print("[通过] 真实清单无误报错误；8 条特征缺失、5 条四舍五入提示")


def test_issue_fixture_flags_expected_rules() -> None:
    result = analyze(ISSUE_CSV)[0]
    found = problems(result)
    expected = [
        "清单编码重复",
        "合价不等于工程量×综合单价",
        "工程量为负数",
        "清单行缺项目编码",
        "综合单价为 0",
        "同名、同特征、同单位的清单项重复出现",
        "清单编码为 11 位",
        "2024 版项目出现“规费”",
        "合计行与清单项合价汇总不一致",
        "名称提示单位应为",
    ]
    for needle in expected:
        assert any(needle in problem for problem in found), needle
    assert levels(result, "错误") >= 5, levels(result, "错误")
    assert sum(1 for issue in result.issues if issue.level == "错误") >= 5
    assert not any(
        "清单编码重复" in issue.problem
        for issue in result.issues
        if issue.code == "30501999999"
    ), "11 位编码不应误报重复"
    print("[通过] 问题样例覆盖编码、算术、负数、缺项、零单价、重复项、规费、合计")


def test_xlsx_reader_matches_csv() -> None:
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "清单.xlsx"
        build_xlsx(REAL_CSV, target)
        results = analyze(target)
        assert len(results) == 1, len(results)
        assert results[0].name == "分部分项", results[0].name
        assert len(results[0].items) == 21, len(results[0].items)
        assert levels(results[0], "错误") == 0, problems(results[0])
    print("[通过] XLSX（共享字符串）读取与 CSV 结果一致")


def test_gbk_csv_reader() -> None:
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "清单-gbk.csv"
        text = REAL_CSV.read_text(encoding="utf-8-sig")
        target.write_bytes(text.encode("gb18030"))
        results = analyze(target)
        assert len(results[0].items) == 21, len(results[0].items)
    print("[通过] GBK/GB18030 导出的 CSV 可读取")


def test_cli_outputs_and_exit_codes() -> None:
    with tempfile.TemporaryDirectory() as folder:
        issues_csv = Path(folder) / "问题回填.csv"
        report_md = Path(folder) / "体检报告.md"
        real = run_cli(
            str(REAL_CSV),
            "--standard",
            "2024",
            "--out",
            str(issues_csv),
            "--md",
            str(report_md),
        )
        assert real.returncode == 0, real.stdout + real.stderr
        assert issues_csv.read_bytes().startswith(b"\xef\xbb\xbf")
        with issues_csv.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        assert rows[0] == ISSUE_HEADERS, rows[0]
        assert len(rows) > 1
        assert "# 软件导出清单体检摘要" in report_md.read_text(encoding="utf-8")

        issues = run_cli(str(ISSUE_CSV), "--standard", "2024")
        assert issues.returncode == 1, issues.stdout + issues.stderr
        assert "错误" in issues.stdout

    template = run_cli("--template")
    assert template.returncode == 0
    assert "项目编码" in template.stdout
    assert "问题编号" in template.stdout

    print("[通过] CLI 退出码、问题回填 BOM/表头和 Markdown 报告")


def test_cli_rejects_proprietary_files() -> None:
    with tempfile.TemporaryDirectory() as folder:
        fake = Path(folder) / "清单.24jz"
        fake.write_text("<xml/>", encoding="utf-8")
        result = run_cli(str(fake))
        assert result.returncode == 2, result.returncode
        assert "不解析" in result.stdout
    print("[通过] .24jz 等专有文件提示改用 Excel/CSV，不越界解析")


def test_cli_requires_input() -> None:
    result = run_cli()
    assert result.returncode == 2, result.returncode
    print("[通过] 无输入时返回用法提示")


def mutated_copy(folder: str, replacements: list[tuple[str, str]]) -> Path:
    text = REAL_CSV.read_text(encoding="utf-8-sig")
    for old, new in replacements:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    target = Path(folder) / "清单-改造.csv"
    target.write_text(text, encoding="utf-8-sig")
    return target


def test_full_width_space_is_flagged() -> None:
    with tempfile.TemporaryDirectory() as folder:
        target = mutated_copy(folder, [(",靶标,", ",靶\u3000标,")])
        result = analyze(target)[0]
        hits = [
            issue
            for issue in result.issues
            if issue.rule_id == "SW-11" and issue.field == "项目名称"
        ]
        assert hits, problems(result)
        assert hits[0].level == "警告", hits[0].level
    print("[通过] 项目名称含全角空格时命中 SW-11")


def test_precision_beyond_two_decimals_is_flagged() -> None:
    with tempfile.TemporaryDirectory() as folder:
        target = mutated_copy(folder, [(",6925.87,", ",6925.872,")])
        result = analyze(target)[0]
        hits = [issue for issue in result.issues if "金额小数位超过 2 位" in issue.problem]
        assert hits, problems(result)
        assert hits[0].level == "提示", hits[0].level
        assert hits[0].field == "合价", hits[0].field
    print("[通过] 合价小数位超过 2 位时命中精度检查")


def build_custom_xlsx(
    target: Path,
    sheets_spec: list[tuple[str, list[list[object]], list[str]]],
) -> None:
    """Build multi-sheet xlsx supporting formulas and mergeCells.

    Each cell in rows can be:
    - str / int / float: static value
    - tuple ("formula", formula_str, cached_val_or_None): formula cell
    """
    shared: list[str] = []
    positions: dict[str, int] = {}

    def shared_index(value: str) -> int:
        if value not in positions:
            positions[value] = len(shared)
            shared.append(value)
        return positions[value]

    sheet_entries = []
    rel_entries = []
    ct_entries = []
    sheet_xmls: list[tuple[str, str]] = []

    for idx, (sheet_name, rows, merges) in enumerate(sheets_spec, start=1):
        sheet_rows = []
        for row_index, row in enumerate(rows, start=1):
            cells = []
            for column_index, cell in enumerate(row, start=1):
                if cell == "" or cell is None:
                    continue
                ref = f"{column_name(column_index)}{row_index}"
                if isinstance(cell, tuple) and cell[0] == "formula":
                    _, formula_str, cached = cell
                    if cached is None:
                        cells.append(f'<c r="{ref}"><f>{escape(formula_str)}</f></c>')
                    else:
                        cells.append(
                            f'<c r="{ref}"><f>{escape(formula_str)}</f><v>{escape(str(cached))}</v></c>'
                        )
                else:
                    text = str(cell)
                    try:
                        float(text.replace(",", ""))
                    except ValueError:
                        cells.append(
                            f'<c r="{ref}" t="s"><v>{shared_index(text)}</v></c>'
                        )
                    else:
                        cells.append(f'<c r="{ref}"><v>{escape(text)}</v></c>')
            sheet_rows.append(f'<row r="{row_index}">' + "".join(cells) + "</row>")

        merge_xml = ""
        if merges:
            merge_xml = (
                f'<mergeCells count="{len(merges)}">'
                + "".join(f'<mergeCell ref="{m}"/>' for m in merges)
                + "</mergeCells>"
            )

        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData>" + "".join(sheet_rows) + "</sheetData>" + merge_xml + "</worksheet>"
        )
        sheet_xmls.append((f"xl/worksheets/sheet{idx}.xml", xml))
        sheet_entries.append(
            f'<sheet name="{escape(sheet_name)}" sheetId="{idx}" r:id="rId{idx}"/>'
        )
        rel_entries.append(
            f'<Relationship Id="rId{idx}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{idx}.xml"/>'
        )
        ct_entries.append(
            f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )

    ss_rel_id = len(sheets_spec) + 1
    rel_entries.append(
        f'<Relationship Id="rId{ss_rel_id}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
        'Target="sharedStrings.xml"/>'
    )
    shared_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared)}" uniqueCount="{len(shared)}">'
        + "".join(f"<si><t>{escape(item)}</t></si>" for item in shared)
        + "</sst>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>" + "".join(sheet_entries) + "</sheets></workbook>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(rel_entries)
        + "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(ct_entries)
        + '<Override PartName="/xl/sharedStrings.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/sharedStrings.xml", shared_xml)
        for member, content in sheet_xmls:
            archive.writestr(member, content)


def test_xlsx_merged_multi_row_header() -> None:
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "merged-header.xlsx"
        rows = [
            ["分部分项工程清单与计价表", "", "", "", "", "", "", ""],
            ["序号", "项目编码", "项目名称", "项目特征描述", "计量单位", "工程量", "金额（元）", ""],
            ["", "", "", "", "", "", "综合单价", "合价"],
            ["1", "010502001001", "矩形柱", "C30现浇商品混凝土，泵送", "m3", "10", "500.00", "5000.00"],
            ["", "", "合计", "", "", "", "", "5000.00"],
        ]
        merges = ["A1:H1", "A2:A3", "B2:B3", "C2:C3", "D2:D3", "E2:E3", "F2:F3", "G2:H2"]
        build_custom_xlsx(target, [("分部分项", rows, merges)])
        result = analyze(target)[0]
        assert result.recognized, result.skip_reason
        assert len(result.items) == 1, len(result.items)
        assert result.items[0].price == Decimal("500.00")
        assert result.items[0].total == Decimal("5000.00")
        assert levels(result, "错误") == 0, problems(result)
    print("[通过] XLSX 两行横向/纵向合并表头准确识别")


def test_xlsx_formula_hardcode_and_missing_cache() -> None:
    with tempfile.TemporaryDirectory() as folder:
        # 1. 9 formulas + 1 hardcoded override -> exactly 1 SW-12 hit
        target = Path(folder) / "formula-override.xlsx"
        rows: list[list[object]] = [
            ["序号", "项目编码", "项目名称", "项目特征", "计量单位", "工程量", "综合单价", "合价"],
        ]
        for i in range(1, 11):
            r = i + 1
            total_cell: object = (
                "1000.00" if i == 6 else ("formula", f"F{r}*G{r}", "1000.00")
            )
            rows.append([
                str(i), f"0105020010{i:02d}", f"构件{i}", "C30混凝土", "m3", "10", "100.00", total_cell
            ])
        rows.append(["", "", "合计", "", "", "", "", ("formula", "SUM(H2:H11)", "10000.00")])
        build_custom_xlsx(target, [("分部分项", rows, [])])
        res = analyze(target)[0]
        sw12 = [issue for issue in res.issues if issue.rule_id == "SW-12"]
        assert len(sw12) == 1, sw12
        assert sw12[0].row == 7 and sw12[0].judgment == "疑似问题", sw12[0]

        # 2. Pure value XLSX (0 formulas) -> 0 SW-12 false alarms
        pure_target = Path(folder) / "pure-value.xlsx"
        pure_rows = [
            ["序号", "项目编码", "项目名称", "项目特征", "计量单位", "工程量", "综合单价", "合价"],
            *[
                [str(i), f"0105020010{i:02d}", f"构件{i}", "C30混凝土", "m3", "10", "100.00", "1000.00"]
                for i in range(1, 11)
            ],
            ["", "", "合计", "", "", "", "", "10000.00"],
        ]
        build_custom_xlsx(pure_target, [("分部分项", pure_rows, [])])
        pure_res = analyze(pure_target)[0]
        assert not [issue for issue in pure_res.issues if issue.rule_id == "SW-12"]

        # 3. Formula missing cached <v> -> graceful SW-12 待补资料
        nocache_target = Path(folder) / "no-cache.xlsx"
        nocache_rows: list[list[object]] = [
            ["序号", "项目编码", "项目名称", "项目特征", "计量单位", "工程量", "综合单价", "合价"],
            ["1", "010502001001", "矩形柱", "C30混凝土", "m3", "10", "500.00", ("formula", "F2*G2", None)],
            ["", "", "合计", "", "", "", "", ("formula", "SUM(H2:H2)", None)],
        ]
        build_custom_xlsx(nocache_target, [("分部分项", nocache_rows, [])])
        nocache_res = analyze(nocache_target)[0]
        assert any(
            issue.rule_id == "SW-12" and "缓存" in issue.problem
            for issue in nocache_res.issues
        ), problems(nocache_res)
    print("[通过] XLSX 公式审计（SW-12）：抓手工覆盖、纯值不误报、缺缓存优雅提示")


def test_section_subtotal_tree_both_layouts() -> None:
    # 1. Top-subtotal layout (hanqiao-real-boq.csv) at tight tolerance 0.005 catches 0.01 diff
    sheets = load_sheets(REAL_CSV)
    tight = analyze_sheet(sheets[0], "2024", Decimal("0.005"))
    sec_hits = [
        issue for issue in tight.issues
        if issue.rule_id == "SW-05" and issue.field == "分部小计"
    ]
    assert len(sec_hits) == 1, sec_hits
    assert "系统软件费用" in sec_hits[0].name and sec_hits[0].row == 23, sec_hits[0]

    # 2. Bottom-subtotal layout with 3 sections; section 2 tampered by +100.00
    with tempfile.TemporaryDirectory() as folder:
        csv_path = Path(folder) / "bottom-subtotals.csv"
        csv_path.write_text(
            "序号,项目编码,项目名称,项目特征,计量单位,工程量,综合单价,合价\n"
            ",,一、土石方工程,,,,,\n"
            "1,010101001001,挖一般土方,三类土、深2m、外运5km,m3,100,20.00,2000.00\n"
            ",,分部小计,,,,,2000.00\n"
            ",,二、混凝土工程,,,,,\n"
            "2,010502001001,矩形柱,C30商品混凝土,m3,10,500.00,5000.00\n"
            ",,分部小计,,,,,5100.00\n"
            ",,三、砌筑工程,,,,,\n"
            "3,010401001001,实心砖墙,240mm厚、M7.5水泥砂浆,m3,10,300.00,3000.00\n"
            ",,分部小计,,,,,3000.00\n"
            ",,分部分项合计,,,,,10000.00\n",
            encoding="utf-8-sig",
        )
        cli = run_cli(str(csv_path), "--standard", "2024")
        assert cli.returncode == 1, cli.stdout
        res = analyze(csv_path)[0]
        bad_sec = [
            issue for issue in res.issues
            if issue.rule_id == "SW-05" and issue.field == "分部小计"
        ]
        assert len(bad_sec) == 1 and bad_sec[0].row == 7, bad_sec
    print("[通过] 分部小计树校验（SW-05）：覆盖顶部小计与底部小计两种布局")


def test_multi_sheet_reconciliation_and_vat_base() -> None:
    with tempfile.TemporaryDirectory() as folder:
        boq_rows: list[list[object]] = [
            ["序号", "项目编码", "项目名称", "项目特征", "计量单位", "工程量", "综合单价", "合价"],
            ["1", "010502001001", "矩形柱", "C30商品混凝土", "m3", "100", "500.00", "50000.00"],
            ["", "", "分部分项合计", "", "", "", "", "50000.00"],
        ]
        measure_rows: list[list[object]] = [
            ["序号", "项目名称", "金额"],
            ["1", "安全生产措施费", "3000.00"],
            ["2", "文明施工费", "2000.00"],
            ["", "合计", "5000.00"],
        ]
        other_rows: list[list[object]] = [
            ["序号", "项目名称", "金额", "备注"],
            ["1", "暂列金额", "5000.00", ""],
            ["2", "专业工程暂估价", "10000.00", "含税"],
            ["", "合计", "15000.00", ""],
        ]

        # 1. Clean balanced 4-sheet workbook (VAT excludes 10000 tax-inclusive provisional: 60000 * 9% = 5400)
        clean_summary: list[list[object]] = [
            ["序号", "汇总内容", "金额(元)"],
            ["1", "分部分项工程费", "50000.00"],
            ["2", "措施项目费", "5000.00"],
            ["3", "其他项目费", "15000.00"],
            ["4", "增值税", "5400.00"],
            ["5", "工程造价", "75400.00"],
        ]
        clean_xlsx = Path(folder) / "clean-pack.xlsx"
        build_custom_xlsx(
            clean_xlsx,
            [
                ("单位工程汇总表", clean_summary, []),
                ("分部分项", boq_rows, []),
                ("总价措施", measure_rows, []),
                ("其他项目", other_rows, []),
            ],
        )
        results, pkg_issues = analyze_workbook(load_sheets(clean_xlsx), "2024", Decimal("0.02"))
        assert not [i for i in pkg_issues if i.rule_id == "SW-13"], pkg_issues

        # 2. Tampered summary (boq mismatch + double-taxed VAT 70000 * 9% = 6300)
        bad_summary: list[list[object]] = [
            ["序号", "汇总内容", "金额(元)"],
            ["1", "分部分项工程费", "52000.00"],
            ["2", "措施项目费", "5000.00"],
            ["3", "其他项目费", "15000.00"],
            ["4", "增值税", "6480.00"],
            ["5", "工程造价", "78480.00"],
        ]
        bad_xlsx = Path(folder) / "bad-pack.xlsx"
        build_custom_xlsx(
            bad_xlsx,
            [
                ("单位工程汇总表", bad_summary, []),
                ("分部分项", boq_rows, []),
                ("总价措施", measure_rows, []),
                ("其他项目", other_rows, []),
            ],
        )
        _, bad_pkg = analyze_workbook(load_sheets(bad_xlsx), "2024", Decimal("0.02"))
        assert any("分部分项工程费" in i.problem and i.level == "错误" for i in bad_pkg), bad_pkg
        assert any("专业工程暂估价重复计取增值税" in i.problem for i in bad_pkg), bad_pkg
    print("[通过] 多表导出包跨表勾稽与 2024 增值税基数校验（SW-13）")


def test_structured_feature_rules_positive_and_negative() -> None:
    with tempfile.TemporaryDirectory() as folder:
        csv_path = Path(folder) / "feature-rules.csv"
        csv_path.write_text(
            "序号,项目编码,项目名称,项目特征,计量单位,工程量,综合单价,合价\n"
            "1,010502001001,矩形柱,现浇商品混凝土，泵送,m3,10,500.00,5000.00\n"
            "2,010502001002,矩形柱,C30现浇商品混凝土，泵送,m3,10,500.00,5000.00\n"
            "3,010902001001,屋面防水卷材,热熔满粘施工,m2,100,60.00,6000.00\n"
            "4,010902001002,屋面防水卷材,4mm厚SBS改性沥青防水卷材，热熔满粘,m2,100,60.00,6000.00\n"
            "5,030801001001,镀锌钢管,螺纹连接，室内明装,m,50,40.00,2000.00\n"
            "6,030801001002,镀锌钢管,DN50，螺纹连接，室内明装,m,50,40.00,2000.00\n"
            ",,合计,,,,,26000.00\n",
            encoding="utf-8-sig",
        )
        res = analyze(csv_path)[0]
        sw08_rows = sorted(
            issue.row for issue in res.issues if issue.rule_id == "SW-08"
        )
        assert sw08_rows == [2, 4, 6], sw08_rows
    print("[通过] 结构化项目特征必填词典（SW-08）：3 组正反向断言精准命中且无误报")


def main() -> int:
    tests = [
        test_real_boq_header_and_items,
        test_real_boq_has_no_false_errors,
        test_issue_fixture_flags_expected_rules,
        test_full_width_space_is_flagged,
        test_precision_beyond_two_decimals_is_flagged,
        test_xlsx_reader_matches_csv,
        test_gbk_csv_reader,
        test_cli_outputs_and_exit_codes,
        test_cli_rejects_proprietary_files,
        test_cli_requires_input,
        test_xlsx_merged_multi_row_header,
        test_xlsx_formula_hardcode_and_missing_cache,
        test_section_subtotal_tree_both_layouts,
        test_multi_sheet_reconciliation_and_vat_base,
        test_structured_feature_rules_positive_and_negative,
    ]
    for test in tests:
        test()
    print(f"OK: software export checks validated ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
