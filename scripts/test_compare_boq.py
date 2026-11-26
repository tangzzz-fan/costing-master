#!/usr/bin/env python3
"""工程量清单双版本对比引擎测试（CM-008）。"""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

from compare_boq import (
    DIFF_HEADERS,
    compare_contract_settlement,
    compare_revision,
    compare_tender_bid,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = ROOT / "test-cases" / "fixtures" / "software-export"
REAL_CSV = FIXTURE_DIR / "hanqiao-real-boq.csv"
ISSUE_CSV = FIXTURE_DIR / "hanqiao-export-issues.csv"
SCRIPT = ROOT / "scripts" / "compare_boq.py"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def _write_csv(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8-sig")
    return path


def test_tender_bid_clean_passes() -> None:
    with tempfile.TemporaryDirectory() as folder:
        base = _write_csv(
            Path(folder) / "tender.csv",
            "序号,项目编码,项目名称,项目特征,计量单位,工程量,综合单价,合价,暂估价\n"
            "1,010502001001,矩形柱,C30商品混凝土,m3,100,500.00,50000.00,0\n"
            "2,010401001001,实心砖墙,240mm厚、M7.5砂浆,m3,50,300.00,15000.00,0\n"
            ",,合计,,,,,65000.00,\n",
        )
        bid = _write_csv(
            Path(folder) / "bid.csv",
            "序号,项目编码,项目名称,项目特征,计量单位,工程量,综合单价,合价,暂估价\n"
            "1,010502001001,矩形柱,C30商品混凝土,m3,100,480.00,48000.00,0\n"
            "2,010401001001,实心砖墙,240mm厚、M7.5砂浆,m3,50,295.00,14750.00,0\n"
            ",,合计,,,,,62750.00,\n",
        )
        summary = compare_tender_bid(base, bid, Decimal("0.02"))
        assert len(summary.records) == 0, summary.records
        cli = run_cli(str(base), str(bid), "--mode", "tender-bid")
        assert cli.returncode == 0, cli.stdout
    print("[通过] tender-bid：合规投标无篡改，退出码 0")


def test_tender_bid_catches_four_tamper_types() -> None:
    with tempfile.TemporaryDirectory() as folder:
        base = _write_csv(
            Path(folder) / "tender.csv",
            "序号,项目编码,项目名称,项目特征,计量单位,工程量,综合单价,合价,暂估价\n"
            "1,010502001001,矩形柱,C30商品混凝土,m3,100,500.00,50000.00,0\n"
            "2,010401001001,实心砖墙,240mm厚、M7.5砂浆,m3,50,300.00,15000.00,0\n"
            "3,010902001001,屋面防水卷材,4mm厚SBS,m2,200,60.00,12000.00,0\n"
            ",,合计,,,,,77000.00,\n",
        )
        bid = _write_csv(
            Path(folder) / "bid.csv",
            "序号,项目编码,项目名称,项目特征,计量单位,工程量,综合单价,合价,暂估价\n"
            "1,010502001001,矩形柱,C30商品混凝土,m3,120,500.00,60000.00,0\n"
            "2,010401001001,实心砖墙,240mm厚、M7.5砂浆,m2,50,300.00,15000.00,0\n"
            "4,010999001001,擅自增项,额外项,项,1,1000.00,1000.00,0\n"
            ",,合计,,,,,76000.00,\n",
        )
        summary = compare_tender_bid(base, bid, Decimal("0.02"))
        categories = {r.category for r in summary.records}
        assert "招标工程量篡改" in categories, categories
        assert "计量单位篡改" in categories, categories
        assert "投标缺项" in categories, categories
        assert "投标多项" in categories, categories
        cli = run_cli(str(base), str(bid), "--mode", "tender-bid")
        assert cli.returncode == 1, cli.stdout
    print("[通过] tender-bid：100% 检出改工程量、改单位、缺项、多项（退出码 1）")


def test_tender_bid_catches_name_feature_provisional_tamper() -> None:
    with tempfile.TemporaryDirectory() as folder:
        base = _write_csv(
            Path(folder) / "tender.csv",
            "序号,项目编码,项目名称,项目特征,计量单位,工程量,综合单价,合价,暂估价\n"
            "1,010502001001,矩形柱,C30商品混凝土,m3,100,500.00,50000.00,200.00\n"
            ",,合计,,,,,50000.00,\n",
        )
        bid = _write_csv(
            Path(folder) / "bid.csv",
            "序号,项目编码,项目名称,项目特征,计量单位,工程量,综合单价,合价,暂估价\n"
            "1,010502001001,异形柱,C25商品混凝土,m3,100,500.00,50000.00,150.00\n"
            ",,合计,,,,,50000.00,\n",
        )
        summary = compare_tender_bid(base, bid, Decimal("0.02"))
        categories = {r.category for r in summary.records}
        assert "项目名称篡改" in categories, categories
        assert "项目特征篡改" in categories, categories
        assert "暂估价不一致" in categories, categories
    print("[通过] tender-bid：检出项目名称、项目特征、暂估价篡改")


def test_revision_tracks_issue_closure() -> None:
    summary = compare_revision(ISSUE_CSV, REAL_CSV, "2024", Decimal("0.02"))
    assert int(summary.extra_metrics["已关闭问题"]) >= 8, summary.extra_metrics
    assert int(summary.extra_metrics["改后剩余确定错误"]) == 0, summary.extra_metrics
    cli = run_cli(str(ISSUE_CSV), str(REAL_CSV), "--mode", "revision")
    assert cli.returncode == 0, cli.stdout
    print("[通过] revision：准确统计改前→改后问题关闭率与残余错误数")


def test_contract_settlement_classification_and_closure() -> None:
    with tempfile.TemporaryDirectory() as folder:
        contract = _write_csv(
            Path(folder) / "contract.csv",
            "序号,项目编码,项目名称,项目特征,计量单位,工程量,综合单价,合价\n"
            "1,010502001001,原量项,C30混凝土,m3,100,500.00,50000.00\n"
            "2,010502001002,超量项,C30混凝土,m3,100,400.00,40000.00\n"
            "3,010502001003,减量项,C30混凝土,m3,100,300.00,30000.00\n"
            "4,010502001004,改价项,C30混凝土,m3,100,200.00,20000.00\n"
            "5,010502001005,漏减项,C30混凝土,m3,50,100.00,5000.00\n"
            ",,合计,,,,,145000.00\n",
        )
        settlement = _write_csv(
            Path(folder) / "settlement.csv",
            "序号,项目编码,项目名称,项目特征,计量单位,工程量,综合单价,合价\n"
            "1,010502001001,原量项,C30混凝土,m3,100,500.00,50000.00\n"
            "2,010502001002,超量项,C30混凝土,m3,122,400.00,48800.00\n"
            "3,010502001003,减量项,C30混凝土,m3,82,300.00,24600.00\n"
            "4,010502001004,改价项,C30混凝土,m3,100,250.00,25000.00\n"
            "6,010502001006,新增变更项,C35混凝土,m3,10,600.00,6000.00\n"
            ",,合计,,,,,154400.00\n",
        )
        summary = compare_contract_settlement(
            contract, settlement, Decimal("0.02"), Decimal("0.15")
        )
        categories = [r.category for r in summary.records]
        assert categories.count("工程量变化（超调价阈值）") == 2, categories
        assert "合同单价被改动" in categories, categories
        assert "新增清单项" in categories, categories
        assert "合同内缺失项（疑似漏减/未实施）" in categories, categories
        assert summary.extra_metrics["闭合差额"] == "0.00", summary.extra_metrics
        assert summary.extra_metrics["总价净差额"] == "9,400.00", summary.extra_metrics
    print("[通过] contract-settlement：超量+22%/减量-18%/改价/新增/漏减分类精准且差额 0.00 闭合")


def test_cli_csv_bom_and_markdown_output() -> None:
    with tempfile.TemporaryDirectory() as folder:
        out_csv = Path(folder) / "diff.csv"
        out_md = Path(folder) / "diff.md"
        res = run_cli(
            str(ISSUE_CSV),
            str(REAL_CSV),
            "--mode",
            "revision",
            "--out",
            str(out_csv),
            "--md",
            str(out_md),
        )
        assert res.returncode == 0, res.stdout
        assert out_csv.read_bytes().startswith(b"\xef\xbb\xbf")
        rows = list(csv.reader(out_csv.open(encoding="utf-8-sig", newline="")))
        assert rows[0] == DIFF_HEADERS, rows[0]
        assert len(rows) > 1
        assert "# 工程量清单对比报告（revision）" in out_md.read_text(encoding="utf-8")
    print("[通过] CLI 输出 UTF-8 BOM CSV 表头与 Markdown 报告")


def test_cli_rejects_proprietary_files() -> None:
    with tempfile.TemporaryDirectory() as folder:
        fake = Path(folder) / "招标.24jz"
        fake.write_text("<xml/>", encoding="utf-8")
        res = run_cli(str(fake), str(REAL_CSV), "--mode", "tender-bid")
        assert res.returncode == 2, res.returncode
        assert "不解析" in res.stdout
    print("[通过] 拒绝 .24jz 等专有文件并返回退出码 2")


def test_contract_settlement_within_threshold_not_flagged_over() -> None:
    with tempfile.TemporaryDirectory() as folder:
        contract = _write_csv(
            Path(folder) / "contract.csv",
            "序号,项目编码,项目名称,项目特征,计量单位,工程量,综合单价,合价\n"
            "1,010502001001,柱,C30混凝土,m3,100,500.00,50000.00\n"
            ",,合计,,,,,50000.00\n",
        )
        settlement = _write_csv(
            Path(folder) / "settlement.csv",
            "序号,项目编码,项目名称,项目特征,计量单位,工程量,综合单价,合价\n"
            "1,010502001001,柱,C30混凝土,m3,110,500.00,55000.00\n"
            ",,合计,,,,,55000.00\n",
        )
        summary = compare_contract_settlement(
            contract, settlement, Decimal("0.02"), Decimal("0.15")
        )
        assert summary.records[0].category == "工程量变化（阈值内）"
        assert run_cli(str(contract), str(settlement), "--mode", "contract-settlement").returncode == 0
    print("[通过] contract-settlement：+10% 在阈值内不误报超幅调价")


def test_missing_file_returns_exit_2() -> None:
    res = run_cli("no-such-file.csv", str(REAL_CSV), "--mode", "tender-bid")
    assert res.returncode == 2
    print("[通过] 缺失文件返回退出码 2")


def main() -> int:
    tests = [
        test_tender_bid_clean_passes,
        test_tender_bid_catches_four_tamper_types,
        test_tender_bid_catches_name_feature_provisional_tamper,
        test_revision_tracks_issue_closure,
        test_contract_settlement_classification_and_closure,
        test_contract_settlement_within_threshold_not_flagged_over,
        test_cli_csv_bom_and_markdown_output,
        test_cli_rejects_proprietary_files,
        test_missing_file_returns_exit_2,
    ]
    for test in tests:
        test()
    print(f"OK: compare_boq assertions passed ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
