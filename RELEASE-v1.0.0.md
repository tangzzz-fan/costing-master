# Costing Master v1.0.0 发布说明（草案）

> 状态：草案，未发布。发布前须关闭 `docs/release-blockers.md` 中全部 P0 项，并完成 G6 人工签认。
>
> 基线版本：v0.13.0（commit 7135a09）。本文档描述 v1.0.0 的发布范围、适用依据和已知限制。

## 一、版本信息

| 项 | 内容 |
|---|---|
| 目标版本 | v1.0.0 |
| 基线版本 | v0.13.0 |
| 定位 | 面向中国工程造价实务的文件审核与工作流辅助 Skill |
| 默认市场 | 江苏省苏州市；地区优先级 苏州/江苏 > 上海 > 浙江 > 其他长三角 > 全国参考 |
| 适用标准 | GB/T 50500-2024 及 9 本工程量计算标准；GB 50500-2013 过渡项目 |
| 不适用范围 | 海外计价规则、国际合同范本、非中国标准计价项目、法律定性和签章成果 |

## 二、v1.0.0 包含的能力

| 能力 | 入口 |
|---|---|
| 清单特征与漏项检查 | `workflows/boq-missing-items-check.md` |
| 预算、投标报价、清标 | `workflows/pricing-and-bid-review.md` |
| 结算审核与审减台账 | `workflows/settlement-audit.md` |
| 合同商务风险 | `workflows/contract-risk-review.md` |
| 变更签证与索赔 | `workflows/change-visa-audit.md` |
| 材料价差与信息价 | `workflows/material-price-analysis.md` |
| 进度款审核 | `workflows/progress-payment-audit.md` |
| 成本管理与目标成本 | `workflows/cost-management.md` |
| 地铁车站与盾构专项 | `workflows/metro-rail-transit-audit.md` |
| 文件抽取与证据链 | `workflows/document-extraction-and-evidence.md` |
| 企业级交付与归档 | `workflows/enterprise-delivery.md` |
| 交付前二次审核 | `workflows/second-pass-review.md` |
| 规则治理与任务清单 | `rules/README.md`、`templates/task-manifest.md` |
| 工程量快速估算 | `scripts/metro_quantity_estimator.py` |
| 地区适用性判断 | `scripts/test_project_applicability.py` |
| 单价样本校验与参考区间 | `scripts/check_unit_price_data.py` |

## 三、适用依据版本

| 依据 | 版本与状态 |
|---|---|
| GB/T 50500-2024 | 住建部公告 2024 年第 212 号，2025-09-01 实施，已核对原文 |
| GB 50500-2013 | 2025-09-01 废止，旧合同过渡参考 |
| C01–C09 九本计算标准 | 编号与名称已登记，发布/实施日期待人工核对 |
| 江苏/苏州 | 江苏省住建厅公告〔2025〕第12号，2026-06-01 实施；苏州建函建〔2026〕72号待核对原文 |
| 上海 | 沪建标定〔2025〕521号，2026-01-01 实施 |
| 浙江 | 浙建建发〔2026〕90号，2026-11-01 实施；原文待补充 |

完整登记和审核状态见 `references/standards-index.md`，版本对应关系见 `references/version-compatibility.md`。

## 四、已知限制与数据缺口

| 限制 | 影响 | 当前处理 |
|---|---|---|
| 标准索引 26 条仍为「待人工审核」 | 引用标准编号、日期和地方执行时间时需人工复核 | 见 `docs/release-blockers.md` P0-01 |
| C01–C09 缺发布/实施日期 | 无法自动判断九本标准的适用时点 | P0-02 |
| 单价库无真实成交样本 | 参考区间为经验值，不能作为报价、审核或结算依据 | P1-01，单价指南已声明 |
| 项目实证不足 | 工程量公式和适用性断言基于公开数据与模拟场景，不替代图纸和清单 | P1-02、P1-03 |
| 工程量估算为 sanity check | 误差通常在 10%–20%，端头井、异形段需单独计算 | `references/metro-rail-transit.md` 第五节 |
| 谈判案例为教学示例 | 金额和结果均为演示数据，不对应真实项目 | P1-04，已在参考文件声明 |
| 不替代算量软件、定额库和签章 | 输出为工作底稿，须由专业人员复核 | `SKILL.md` 不适用边界 |

## 五、安装与升级

```bash
git clone https://github.com/tangzzz-fan/costing-master.git ~/.claude/skills/costing-master
```

从 v0.13.0 升级：更新仓库后重跑 CI 七步，并核对 `references/standards-index.md` 的审核状态；交付包需重新记录四元组。

## 六、发布判定

```text
P0-01 至 P0-07 全部关闭
+ P1-01 至 P1-07 在本文件中有对应声明
+ CI 七步通过
+ G6 签认（项目负责人 + 造价专业人员）
= 可发布 v1.0.0
```

## 七、签认

| 角色 | 姓名 | 日期 | 结论 |
|---|---|---|---|
| 项目负责人 | | | |
| 造价专业人员 | | | |

## 八、变更记录

各版本变更见 `CHANGELOG.md`；发布阻断项见 `docs/release-blockers.md`。
