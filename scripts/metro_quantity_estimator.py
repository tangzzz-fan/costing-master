#!/usr/bin/env python3
"""
地铁车站工程量快速估算工具

功能：输入车站基本参数，一键估算主要工程量
用途：辅助资深工程师快速判断清单工程量合理性
使用场景：进度款审核、投标报价复核、结算审核
适用范围：地下两层/三层岛式或侧式车站标准段

重要说明：
1. 本工具只能用于快速估算和合理性判断（sanity check）
2. 不能替代设计图纸和算量软件
3. 估算值与实际值误差通常在 10-20%，属于正常范围
4. 端头井、异形段、特殊构造需单独计算

作者：jove
版本：v1.0
日期：2026-10-19
"""

import math
from typing import Dict, Optional


class MetroStationEstimator:
    """地铁车站工程量快速估算器"""

    def __init__(self):
        """初始化估算器，设置典型含量指标"""

        # 典型车站断面参数（基于苏州、上海、杭州地铁项目）
        self.typical_params = {
            "two_level_island": {
                "name": "地下两层岛式车站",
                "standard_width": 20.0,  # m，标准段宽度
                "excavation_depth": 18.0,  # m，平均开挖深度
                "diaphragm_wall_depth": 32.0,  # m，地连墙深度
                "floor_thickness": 1.2,  # m，底板厚度
                "side_wall_height": 8.0,  # m，侧墙平均高度
                "roof_thickness": 1.0,  # m，顶板厚度
            },
            "three_level_island": {
                "name": "地下三层岛式车站",
                "standard_width": 22.0,
                "excavation_depth": 25.0,
                "diaphragm_wall_depth": 40.0,
                "floor_thickness": 1.5,
                "side_wall_height": 12.0,
                "roof_thickness": 1.2,
            }
        }

        # 材料含量指标（kg/m³ 或 m²/m³）
        self.material_content = {
            "rebar": {
                "floor_c40p12": 120,  # kg/m³，底板钢筋含量
                "side_wall_c35p10": 110,  # kg/m³，侧墙钢筋含量
                "roof_c35": 100,  # kg/m³，顶板钢筋含量
                "diaphragm_wall_c30": 80,  # kg/m³，地连墙钢筋含量
            },
            "formwork": {
                "floor": 0.5,  # m²/m³，底板模板（只有底面）
                "side_wall": 2.0,  # m²/m³，侧墙模板（两面）
                "roof": 2.0,  # m²/m³，顶板模板（两面）
            }
        }

        # 盾构区间参数
        self.tunnel_params = {
            "typical": {
                "outer_diameter": 6.2,  # m，外径
                "inner_diameter": 5.5,  # m，内径
                "ring_width": 1.5,  # m，环宽
                "segment_thickness": 0.35,  # m，管片厚度
            }
        }

    def estimate_station(
        self,
        length: float,
        width: Optional[float] = None,
        station_type: str = "two_level_island",
        custom_params: Optional[Dict] = None
    ) -> Dict[str, float]:
        """
        估算地铁车站主要工程量

        参数：
            length: 车站长度（m）
            width: 车站宽度（m），不提供则使用典型值
            station_type: 车站类型（"two_level_island" 或 "three_level_island"）
            custom_params: 自定义参数，覆盖典型值

        返回：
            工程量估算结果字典
        """

        # 获取车站参数
        params = self.typical_params[station_type].copy()
        if width:
            params["standard_width"] = width
        if custom_params:
            params.update(custom_params)

        # 基本尺寸
        L = length
        W = params["standard_width"]
        H_exc = params["excavation_depth"]
        H_wall = params["diaphragm_wall_depth"]

        # 1. 地下连续墙
        perimeter = (L + W) * 2
        diaphragm_wall_area = perimeter * H_wall

        # 2. 钻孔灌注桩（假设每10m一根，墙内侧加强）
        pile_count = int(perimeter / 10)
        pile_depth = H_wall
        pile_length_total = pile_count * pile_depth

        # 3. 基坑土方开挖
        pit_area = L * W
        soil_volume = pit_area * H_exc

        # 4. 底板混凝土
        floor_thickness = params["floor_thickness"]
        floor_area = L * W
        floor_concrete = floor_area * floor_thickness

        # 5. 侧墙混凝土（两侧）
        side_wall_height = params["side_wall_height"]
        side_wall_length = L * 2  # 两侧长边
        side_wall_thickness = 0.8  # m，典型侧墙厚度
        side_wall_concrete = side_wall_length * side_wall_height * side_wall_thickness

        # 6. 顶板混凝土
        roof_thickness = params["roof_thickness"]
        roof_area = L * W
        roof_concrete = roof_area * roof_thickness

        # 7. 主体结构混凝土合计
        main_structure_concrete = floor_concrete + side_wall_concrete + roof_concrete

        # 8. 地连墙混凝土（墙厚1.0m）
        wall_thickness = 1.0
        diaphragm_wall_concrete = diaphragm_wall_area * wall_thickness

        # 9. 防水工程（底板+侧墙+顶板面积）
        waterproof_area = floor_area + (perimeter * H_exc) + roof_area

        # 10. 钢筋工程量（按含量指标估算）
        rebar_floor = floor_concrete * self.material_content["rebar"]["floor_c40p12"]
        rebar_side_wall = side_wall_concrete * self.material_content["rebar"]["side_wall_c35p10"]
        rebar_roof = roof_concrete * self.material_content["rebar"]["roof_c35"]
        rebar_diaphragm_wall = diaphragm_wall_concrete * self.material_content["rebar"]["diaphragm_wall_c30"]
        rebar_total = rebar_floor + rebar_side_wall + rebar_roof + rebar_diaphragm_wall

        # 11. 模板工程量
        formwork_floor = floor_area  # 只有底面
        formwork_side_wall = side_wall_length * side_wall_height * 2  # 两面
        formwork_roof = roof_area * 2  # 两面
        formwork_total = formwork_floor + formwork_side_wall + formwork_roof

        # 返回结果
        return {
            "station_type": params["name"],
            "station_length": L,
            "station_width": W,
            "excavation_depth": H_exc,
            "quantities": {
                "diaphragm_wall_area": round(diaphragm_wall_area, 0),  # m²
                "pile_length": round(pile_length_total, 0),  # m
                "soil_volume": round(soil_volume, 0),  # m³
                "floor_concrete": round(floor_concrete, 0),  # m³
                "side_wall_concrete": round(side_wall_concrete, 0),  # m³
                "roof_concrete": round(roof_concrete, 0),  # m³
                "main_structure_concrete": round(main_structure_concrete, 0),  # m³
                "diaphragm_wall_concrete": round(diaphragm_wall_concrete, 0),  # m³
                "waterproof_area": round(waterproof_area, 0),  # m²
                "rebar_total": round(rebar_total / 1000, 1),  # 吨（从kg转换）
                "formwork_total": round(formwork_total, 0),  # m²
            }
        }

    def estimate_tunnel(
        self,
        length: float,
        outer_diameter: Optional[float] = None,
        ring_width: Optional[float] = None
    ) -> Dict[str, float]:
        """
        估算盾构区间主要工程量

        参数：
            length: 隧道长度（m）
            outer_diameter: 外径（m），不提供则使用典型值6.2m
            ring_width: 环宽（m），不提供则使用典型值1.5m

        返回：
            工程量估算结果字典
        """

        # 获取参数
        D_outer = outer_diameter or self.tunnel_params["typical"]["outer_diameter"]
        D_inner = self.tunnel_params["typical"]["inner_diameter"]
        ring_w = ring_width or self.tunnel_params["typical"]["ring_width"]

        # 1. 管片环数
        ring_count = int(length / ring_w)

        # 2. 管片混凝土量（环体积公式）
        ring_volume = math.pi * (D_outer**2 - D_inner**2) / 4 * ring_w
        segment_concrete = ring_volume * ring_count

        # 3. 盾构掘进工程量（按米计）
        tunnel_length = length

        # 4. 管片钢筋量（按150kg/m³估算）
        rebar_content = 150  # kg/m³
        segment_rebar = segment_concrete * rebar_content

        # 5. 注浆量（环背空隙注浆，按掘进长度计）
        grouting_per_meter = 0.8  # m³/m，经验值
        grouting_volume = tunnel_length * grouting_per_meter

        return {
            "tunnel_length": length,
            "outer_diameter": D_outer,
            "ring_width": ring_w,
            "quantities": {
                "ring_count": ring_count,  # 环
                "segment_concrete": round(segment_concrete, 0),  # m³
                "tunnel_excavation": round(tunnel_length, 0),  # m
                "segment_rebar": round(segment_rebar / 1000, 1),  # 吨
                "grouting_volume": round(grouting_volume, 0),  # m³
            }
        }

    def compare_with_design(
        self,
        estimated: Dict,
        design_values: Dict
    ) -> Dict:
        """
        对比估算值与设计值，计算误差

        参数：
            estimated: 估算结果字典
            design_values: 设计值字典（清单工程量）

        返回：
            对比结果字典
        """

        comparison = {}

        for key, est_value in estimated["quantities"].items():
            if key in design_values:
                design_value = design_values[key]
                error = est_value - design_value
                error_rate = abs(error) / design_value if design_value != 0 else 0

                # 判断合理性
                if error_rate < 0.10:
                    status = "合理"
                elif error_rate < 0.20:
                    status = "基本合理"
                else:
                    status = "需核对"

                comparison[key] = {
                    "estimated": est_value,
                    "design": design_value,
                    "error": round(error, 1),
                    "error_rate": f"{error_rate:.2%}",
                    "status": status
                }

        return comparison


def demo_station_estimate():
    """演示：估算苏州地铁VIII-TS-08站工程量"""

    print("=" * 80)
    print("地铁车站工程量快速估算 - 示例")
    print("=" * 80)
    print()

    estimator = MetroStationEstimator()

    # 输入参数（苏州地铁VIII-TS-08站）
    station_length = 180  # m
    station_width = 20    # m

    # 估算工程量
    result = estimator.estimate_station(
        length=station_length,
        width=station_width,
        station_type="two_level_island"
    )

    # 输出估算结果
    print(f"车站类型：{result['station_type']}")
    print(f"车站尺寸：{result['station_length']}m × {result['station_width']}m")
    print(f"开挖深度：{result['excavation_depth']}m")
    print()
    print("估算工程量：")
    print("-" * 80)

    for key, value in result["quantities"].items():
        # 转换键名为中文
        name_map = {
            "diaphragm_wall_area": "地下连续墙面积（m²）",
            "pile_length": "钻孔灌注桩（m）",
            "soil_volume": "基坑土方开挖（m³）",
            "floor_concrete": "底板混凝土（m³）",
            "side_wall_concrete": "侧墙混凝土（m³）",
            "roof_concrete": "顶板混凝土（m³）",
            "main_structure_concrete": "主体结构混凝土合计（m³）",
            "diaphragm_wall_concrete": "地连墙混凝土（m³）",
            "waterproof_area": "防水工程（m²）",
            "rebar_total": "钢筋工程量（吨）",
            "formwork_total": "模板工程量（m²）",
        }
        print(f"  {name_map.get(key, key)}: {value:>10,.0f}" if isinstance(value, (int, float)) else f"  {name_map.get(key, key)}: {value}")

    print()

    # 对比设计值（来自清单）
    design_values = {
        "diaphragm_wall_area": 13_120,
        "pile_length": 8_400,
        "soil_volume": 67_200,
        "floor_concrete": 4_200,
        "side_wall_concrete": 6_800,
        "roof_concrete": 3_200,
        "waterproof_area": 28_000,
    }

    print("=" * 80)
    print("估算值 vs 设计值对比")
    print("=" * 80)
    print()

    comparison = estimator.compare_with_design(result, design_values)

    print(f"{'清单项':<20} {'估算值':>12} {'设计值':>12} {'误差':>10} {'误差率':>8} {'判断':<10}")
    print("-" * 80)

    name_map = {
        "diaphragm_wall_area": "地连墙面积（m²）",
        "pile_length": "钻孔灌注桩（m）",
        "soil_volume": "基坑土方（m³）",
        "floor_concrete": "底板混凝土（m³）",
        "side_wall_concrete": "侧墙混凝土（m³）",
        "roof_concrete": "顶板混凝土（m³）",
        "waterproof_area": "防水工程（m²）",
    }

    for key, comp in comparison.items():
        name = name_map.get(key, key)
        print(f"{name:<20} {comp['estimated']:>12,.0f} {comp['design']:>12,.0f} "
              f"{comp['error']:>10,.1f} {comp['error_rate']:>8} {comp['status']:<10}")

    print()
    print("说明：")
    print("  - 误差 < 10%：合理")
    print("  - 误差 10-20%：基本合理（标准段估算正常范围）")
    print("  - 误差 > 20%：需核对（可能有端头井、异形段等特殊构造）")
    print()


def demo_tunnel_estimate():
    """演示：估算盾构区间工程量"""

    print("=" * 80)
    print("盾构区间工程量快速估算 - 示例")
    print("=" * 80)
    print()

    estimator = MetroStationEstimator()

    # 输入参数
    tunnel_length = 1_200  # m

    # 估算工程量
    result = estimator.estimate_tunnel(length=tunnel_length)

    # 输出估算结果
    print(f"区间长度：{result['tunnel_length']}m")
    print(f"盾构外径：{result['outer_diameter']}m")
    print(f"管片环宽：{result['ring_width']}m")
    print()
    print("估算工程量：")
    print("-" * 80)

    name_map = {
        "ring_count": "管片环数（环）",
        "segment_concrete": "管片混凝土（m³）",
        "tunnel_excavation": "盾构掘进（m）",
        "segment_rebar": "管片钢筋（吨）",
        "grouting_volume": "注浆量（m³）",
    }

    for key, value in result["quantities"].items():
        print(f"  {name_map.get(key, key)}: {value:>10,.0f}" if isinstance(value, (int, float)) else f"  {name_map.get(key, key)}: {value}")

    print()

    # 对比设计值
    design_values = {
        "ring_count": 804,
        "segment_concrete": 7_920,
        "tunnel_excavation": 1_200,
    }

    comparison = estimator.compare_with_design(result, design_values)

    print("=" * 80)
    print("估算值 vs 设计值对比")
    print("=" * 80)
    print()

    print(f"{'清单项':<20} {'估算值':>12} {'设计值':>12} {'误差':>10} {'误差率':>8} {'判断':<10}")
    print("-" * 80)

    for key, comp in comparison.items():
        name = name_map.get(key, key)
        print(f"{name:<20} {comp['estimated']:>12,.0f} {comp['design']:>12,.0f} "
              f"{comp['error']:>10,.1f} {comp['error_rate']:>8} {comp['status']:<10}")

    print()


if __name__ == "__main__":
    # 运行演示
    demo_station_estimate()
    print()
    demo_tunnel_estimate()
