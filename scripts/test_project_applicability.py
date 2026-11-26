#!/usr/bin/env python3
"""
项目标准适用性判断测试脚本

测试目标：验证江浙沪地区项目按招标/合同日期判断适用标准和地方规则的逻辑准确性
数据来源：真实公开的江苏、上海、浙江住建部门通知和模拟项目信息
测试用例：test-cases/project-applicability.case.md

关联规则：R-009（标准和地方规则新鲜度）、R-013（地区优先级与跨地区隔离）
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "data" / "standards-registry.json"


def load_standards_registry() -> dict:
    """从单一事实源 data/standards-registry.json 加载标准与地方规则配置。"""
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _find_regional_rule(registry: dict, region: str) -> Optional[dict]:
    for item in registry.get("local_rules", []):
        if item.get("status") != "current" or item.get("is_exchange_standard"):
            continue
        if item.get("region") == region or region in item.get("aliases", []):
            return item
    return None


def determine_applicable_standard(
    region: str,
    date: str,
    date_type: str,
    registry: Optional[dict] = None,
) -> Dict[str, str]:
    """
    判断项目适用的国家标准和地方规则（直接消费 data/standards-registry.json）。

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
    data = registry if registry is not None else load_standards_registry()
    rule = _find_regional_rule(data, region)
    if rule is None:
        return {
            "standard": "未知",
            "local_rule": "未知",
            "basis": f"地区 {region} 不在支持范围内",
            "level": "错误"
        }

    standards_by_id = {s.get("id"): s for s in data.get("standards", [])}
    current_nat = standards_by_id.get("S01", {})
    legacy_nat = standards_by_id.get("S02", {})
    national_date = datetime.strptime(current_nat["effective_date"], "%Y-%m-%d")
    local_date = datetime.strptime(rule["effective_date"], "%Y-%m-%d")
    project_date = datetime.strptime(date, "%Y-%m-%d")
    transition_rule = rule.get("transition_rule", "")

    # 判断地方规则（先判断地方，再确定国家标准）
    if project_date < local_date:
        local_rule = rule.get("predecessor_id", "旧规则")
        if not rule.get("bundle_national_with_local", True) and project_date >= national_date:
            national_standard = current_nat["code"]
            basis = f"{transition_rule}；国家标准已执行但地方配套仍用旧版"
        else:
            national_standard = legacy_nat["code"]
            basis = transition_rule
    else:
        local_rule = rule["id"]
        national_standard = current_nat["code"]
        basis = f"{region}地方配套自{local_date.strftime('%Y-%m-%d')}起施行"

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
