#!/usr/bin/env python3
"""
项目标准适用性判断测试脚本

测试目标：验证江浙沪地区项目按招标/合同日期判断适用标准和地方规则的逻辑准确性
数据来源：真实公开的江苏、上海、浙江住建部门通知和模拟项目信息
测试用例：test-cases/project-applicability.case.md

关联规则：R-008（标准变动检查）、R-009（地区资料核对）
"""

from datetime import datetime
from typing import Dict, Tuple


# 地区执行时间配置（基于真实公开文件）
REGIONAL_CONFIG = {
    "江苏/苏州": {
        "national_standard_date": datetime(2025, 9, 1),  # GB/T 50500-2024
        "local_rule_date": datetime(2026, 6, 1),  # 苏州建函建〔2026〕72号
        "old_local_rule": "L00",  # 江苏省2014版
        "new_local_rule": "L01",  # 2026版江苏省消耗量指标
        "transition_rule": "2026-06-01前已发布招标公告或已签订合同的项目，按原规定执行"
    },
    "江苏/南京": {
        "national_standard_date": datetime(2025, 9, 1),
        "local_rule_date": datetime(2026, 6, 1),
        "old_local_rule": "L00",
        "new_local_rule": "L01",
        "transition_rule": "同苏州"
    },
    "上海": {
        "national_standard_date": datetime(2025, 9, 1),
        "local_rule_date": datetime(2026, 1, 1),  # 沪建标定〔2025〕521号
        "old_local_rule": "旧规则",  # 沪建管〔2014〕872号
        "new_local_rule": "L02",  # 2025版应用规则
        "transition_rule": "2026-01-01前已发布招标公告或已签订合同的项目，按原规则执行"
    },
    "浙江/杭州": {
        "national_standard_date": datetime(2025, 9, 1),
        "local_rule_date": datetime(2026, 11, 1),  # 浙建建发〔2026〕90号
        "old_local_rule": "L04",  # 2018版
        "new_local_rule": "L03",  # 2025版
        "transition_rule": "按招标公告发布日或合同签订日判断；2018版执行至2026-10-31"
    },
    "浙江/宁波": {
        "national_standard_date": datetime(2025, 9, 1),
        "local_rule_date": datetime(2026, 11, 1),
        "old_local_rule": "L04",
        "new_local_rule": "L03",
        "transition_rule": "同杭州"
    }
}


def determine_applicable_standard(
    region: str,
    date: str,
    date_type: str
) -> Dict[str, str]:
    """
    判断项目适用的国家标准和地方规则

    参数：
        region: 地区（江苏/苏州、江苏/南京、上海、浙江/杭州、浙江/宁波）
        date: 关键日期（YYYY-MM-DD格式）
        date_type: 日期类型（招标公告、合同签订）

    返回：
        {
            "standard": "GB 50500-2013" 或 "GB/T 50500-2024",
            "local_rule": "L00/L01/L02/L03/L04/旧规则",
            "basis": "判断依据",
            "level": "确定"
        }
    """
    if region not in REGIONAL_CONFIG:
        return {
            "standard": "未知",
            "local_rule": "未知",
            "basis": f"地区 {region} 不在支持范围内",
            "level": "错误"
        }

    config = REGIONAL_CONFIG[region]
    project_date = datetime.strptime(date, "%Y-%m-%d")

    # 判断地方规则（先判断地方，再确定国家标准）
    if project_date < config["local_rule_date"]:
        # 地方配套尚未执行，按原规定
        local_rule = config["old_local_rule"]

        # 浙江特殊情况：国家标准2025-09-01已执行，但地方配套2026-11-01才执行
        # 这种情况下国家标准用新版，地方配套用旧版
        if region.startswith("浙江") and project_date >= config["national_standard_date"]:
            national_standard = "GB/T 50500-2024"
            basis = f"{config['transition_rule']}；国家标准已执行但地方配套仍用旧版"
        else:
            # 江苏、上海：地方配套执行前，整体按原规定（国家标准也用旧版）
            national_standard = "GB 50500-2013"
            basis = f"{config['transition_rule']}"
    else:
        # 地方配套已执行，全部用新版
        local_rule = config["new_local_rule"]
        national_standard = "GB/T 50500-2024"
        basis = f"{region}地方配套自{config['local_rule_date'].strftime('%Y-%m-%d')}起施行"

    return {
        "standard": national_standard,
        "local_rule": local_rule,
        "basis": basis,
        "level": "确定"
    }


# 测试场景数据（来自 test-cases/project-applicability.case.md）
TEST_SCENARIOS = [
    {
        "id": "PA-01",
        "name": "苏州某商业综合体",
        "region": "江苏/苏州",
        "date": "2026-05-15",
        "date_type": "招标公告",
        "expected_standard": "GB 50500-2013",
        "expected_local_rule": "L00"
    },
    {
        "id": "PA-02",
        "name": "南京某住宅项目",
        "region": "江苏/南京",
        "date": "2026-06-10",
        "date_type": "招标公告",
        "expected_standard": "GB/T 50500-2024",
        "expected_local_rule": "L01"
    },
    {
        "id": "PA-03",
        "name": "杭州某市政工程",
        "region": "浙江/杭州",
        "date": "2026-10-20",
        "date_type": "招标公告",
        "expected_standard": "GB/T 50500-2024",
        "expected_local_rule": "L04"
    },
    {
        "id": "PA-04",
        "name": "宁波某轨道交通工程",
        "region": "浙江/宁波",
        "date": "2026-11-05",
        "date_type": "招标公告",
        "expected_standard": "GB/T 50500-2024",
        "expected_local_rule": "L03"
    },
    {
        "id": "PA-05",
        "name": "上海某办公楼",
        "region": "上海",
        "date": "2025-12-20",
        "date_type": "合同签订",
        "expected_standard": "GB 50500-2013",
        "expected_local_rule": "旧规则"
    },
    {
        "id": "PA-06",
        "name": "上海某医院扩建",
        "region": "上海",
        "date": "2026-01-15",
        "date_type": "招标公告",
        "expected_standard": "GB/T 50500-2024",
        "expected_local_rule": "L02"
    },
    {
        "id": "PA-07",
        "name": "苏州工业园区厂房",
        "region": "江苏/苏州",
        "date": "2026-05-31",
        "date_type": "合同签订",
        "expected_standard": "GB 50500-2013",
        "expected_local_rule": "L00"
    },
    {
        "id": "PA-08",
        "name": "苏州高新区学校",
        "region": "江苏/苏州",
        "date": "2026-06-01",
        "date_type": "招标公告",
        "expected_standard": "GB/T 50500-2024",
        "expected_local_rule": "L01"
    }
]


def test_project_applicability():
    """运行所有测试场景"""
    print("=" * 80)
    print("项目标准适用性判断测试")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for scenario in TEST_SCENARIOS:
        result = determine_applicable_standard(
            region=scenario["region"],
            date=scenario["date"],
            date_type=scenario["date_type"]
        )

        # 检查国家标准
        standard_match = result["standard"] == scenario["expected_standard"]
        # 检查地方规则
        local_rule_match = result["local_rule"] == scenario["expected_local_rule"]

        # 判断是否通过
        test_passed = standard_match and local_rule_match

        if test_passed:
            status = "[通过]"
            passed += 1
        else:
            status = "[失败]"
            failed += 1

        # 输出结果
        print(f"{status} {scenario['id']} {scenario['name']}")
        print(f"  地区：{scenario['region']}")
        print(f"  日期：{scenario['date']} ({scenario['date_type']})")
        print(f"  国家标准：{result['standard']}", end="")
        if not standard_match:
            print(f" [预期: {scenario['expected_standard']}]", end="")
        print()
        print(f"  地方规则：{result['local_rule']}", end="")
        if not local_rule_match:
            print(f" [预期: {scenario['expected_local_rule']}]", end="")
        print()
        print(f"  判断依据：{result['basis']}")
        print()

    # 输出汇总
    print("=" * 80)
    print(f"测试汇总：共 {len(TEST_SCENARIOS)} 个场景")
    print(f"  通过：{passed} 个")
    print(f"  失败：{failed} 个")
    print("=" * 80)

    if failed == 0:
        print()
        print("OK: project applicability assertions passed")
        for scenario in TEST_SCENARIOS:
            result = determine_applicable_standard(
                scenario["region"], scenario["date"], scenario["date_type"]
            )
            print(f"  {scenario['id']} {scenario['region']} {scenario['date']} -> "
                  f"{result['standard']} + {result['local_rule']}")
        return 0
    else:
        print()
        print(f"FAILED: {failed} assertion(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = test_project_applicability()
    exit(exit_code)
