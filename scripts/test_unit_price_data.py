#!/usr/bin/env python3
"""
单价样本校验与参考区间计算测试

测试用例数据取自《江浙沪单价数据收集指南》第四章示例，仅用于验证计算与校验逻辑
"""

from check_unit_price_data import (
    LOWER_FACTOR,
    UPPER_FACTOR,
    build_report,
    group_rows,
    summarize,
    validate_rows,
)


def sample(region: str, item: str, price: str, project: str) -> dict[str, str]:
    return {
        "地区": region,
        "清单项": item,
        "单位": "元/m²",
        "单价": price,
        "项目名称": project,
        "数据期别": "2026-Q3",
        "来源链接": "https://example.gov.cn/notice/1",
    }


def test_reference_interval_matches_guide():
    rows = [
        sample("江苏/苏州", "地下连续墙", "1180", "项目A"),
        sample("江苏/苏州", "地下连续墙", "1250", "项目B"),
        sample("江苏/苏州", "地下连续墙", "1120", "项目C"),
    ]
    errors, warnings = validate_rows(rows)
    assert not errors, errors
    assert not warnings, warnings
    summary = summarize(rows, "江苏/苏州", "地下连续墙")
    assert summary["count"] == 3
    assert summary["min"] == 1120
    assert summary["max"] == 1250
    assert summary["median"] == 1180
    assert summary["low"] == 1000
    assert summary["high"] == 1360
    assert summary["outliers"] == []
    print("[通过] 参考区间与指南示例一致：1,000 ~ 1,360")


def test_small_sample_warning():
    rows = [
        sample("上海", "盾构掘进", "80000", "项目A"),
        sample("上海", "盾构掘进", "82000", "项目B"),
    ]
    errors, warnings = validate_rows(rows)
    assert not errors, errors
    assert len(warnings) == 1 and "2 sample" in warnings[0], warnings
    print("[通过] 样本不足 3 个时给出警告")


def test_invalid_price_rejected():
    rows = [sample("浙江/杭州", "管片", "abc", "项目A")]
    errors, _ = validate_rows(rows)
    assert any("invalid price" in error for error in errors), errors
    print("[通过] 非数字单价被拒绝")


def test_source_link_required():
    rows = [sample("浙江/杭州", "管片", "30000", "项目A")]
    rows[0]["来源链接"] = "见附件"
    errors, _ = validate_rows(rows)
    assert any("source link" in error for error in errors), errors
    print("[通过] 来源链接必须是 http/https")


def test_duplicate_sample_rejected():
    rows = [
        sample("江苏/苏州", "地连墙", "1200", "项目A"),
        sample("江苏/苏州", "地连墙", "1250", "项目A"),
    ]
    errors, _ = validate_rows(rows)
    assert any("duplicate" in error for error in errors), errors
    print("[通过] 同地区同清单项同项目重复样本被拒绝")


def test_empty_field_rejected():
    rows = [sample("江苏/苏州", "地连墙", "1200", "")]
    errors, _ = validate_rows(rows)
    assert any("empty field" in error for error in errors), errors
    print("[通过] 必填字段为空时报错")


def test_outlier_flagged():
    rows = [
        sample("江苏/苏州", "土方", "100", "项目A"),
        sample("江苏/苏州", "土方", "100", "项目B"),
        sample("江苏/苏州", "土方", "3000", "项目C"),
    ]
    summary = summarize(rows, "江苏/苏州", "土方")
    assert summary["outliers"] == ["项目C"], summary["outliers"]
    print("[通过] 超出中位数 ±50% 的样本被标记为异常")


def test_report_contains_interval():
    rows = [
        sample("江苏/苏州", "地下连续墙", "1180", "项目A"),
        sample("江苏/苏州", "地下连续墙", "1250", "项目B"),
        sample("江苏/苏州", "地下连续墙", "1120", "项目C"),
    ]
    errors, warnings = validate_rows(rows)
    report = build_report(rows, errors, warnings)
    assert "1,000 ~ 1,360" in report, report
    assert "地下连续墙" in report
    assert len(group_rows(rows)) == 1
    print("[通过] 报告包含参考区间和清单项")


def test_factors_are_guide_values():
    assert LOWER_FACTOR == 0.85
    assert UPPER_FACTOR == 1.15
    print("[通过] 参考区间系数为 0.85 / 1.15")


def main() -> int:
    tests = [
        test_reference_interval_matches_guide,
        test_small_sample_warning,
        test_invalid_price_rejected,
        test_source_link_required,
        test_duplicate_sample_rejected,
        test_empty_field_rejected,
        test_outlier_flagged,
        test_report_contains_interval,
        test_factors_are_guide_values,
    ]
    for test in tests:
        test()
    print(f"OK: unit price checks validated ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
