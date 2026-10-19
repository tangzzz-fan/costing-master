# Costing Master v1.0.0 发布说明

> 状态：已发布，发布日期 2026-10-19。按项目负责人指示，在标准索引人工审核未完成的情况下发布，缺口在本文件第四节和 `docs/release-blockers.md` 中逐条声明。
>
> 基线版本：v0.13.0（commit 7135a09）。本文档描述 v1.0.0 的发布范围、适用依据、已知限制和缺口声明。

## 一、版本信息

| 项 | 内容 |
|---|---|
| 版本 | v1.0.0 |
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

| ID | 限制 | 影响 | 声明与缓解 |
|---|---|---|---|
| P1-01 | 单价库无真实成交样本 | 参考区间为经验值 | 不作报价、审核或结算依据；见 `江浙沪单价数据收集指南.md` |
| P1-02 | 项目实证不足 | 公式和适用性断言基于公开数据与模拟场景 | 不替代图纸、清单和算量软件；VIII-TS-08 仅作工作流验证 |
| P1-03 | 工程量公式验证数据混合 | MQ-01/02/05 为模拟数据，MQ-03/04 为公开数据 | 仅用于合理性判断，误差范围见 `references/metro-rail-transit.md` |
| P1-04 | 谈判案例为教学示例 | 金额和结果不对应真实项目 | 已在 `references/negotiation-strategy.md` 声明 |
| P1-05 | 单价经验区间未替换 | 区间可能偏离实际市场 | 标注「经验区间，待样本替换」，样本入库后更新 |
| P1-06 | 版本兼容矩阵为新补文件 | 历史版本行按 CHANGELOG 推定 | 以对应提交的 `standards-index.md` 状态行为准 |
| P1-07 | 地方过渡期实例缺失 | 边界日期判断缺真实案例 | 适用性断言覆盖 8 个场景，真实案例待补 |

## 五、未关闭的 P0 缺口

| ID | 缺口 | 当前状态 |
|---|---|---|
| P0-01 | 标准索引人工签认 | 26/27 条待签认，仅 S01 完成原文核对 |
| P0-02 | C01–C09 发布/实施日期 | 未补齐 |
| P0-03 | 标准验证记录 | 已勾选 6 项、未勾选 87 项 |
| P0-04 | 官方原文链接 | 苏州建函建〔2026〕72号、浙建建发〔2026〕90号 缺原文 |
| P0-05 | 江苏 2026 版轨交专篇 | 官方未明确 |
| P0-06 | 交付包与审核记录签认 | 实例已填，签认栏为空 |
| P0-07 | P0/P1 清单闭环 | 清单已建，勾选未完成 |

发布决定：项目负责人 2026-10-19 决定在上述 P0 未关闭的情况下发布 v1.0.0，接受缺口以声明形式随版本公开；P0 关闭后按 patch 版本更新。

## 六、安装与升级

```bash
git clone https://github.com/tangzzz-fan/costing-master.git ~/.claude/skills/costing-master
```

从 v0.13.0 升级：更新仓库后重跑 CI 七步，并核对 `references/standards-index.md` 的审核状态；交付包需重新记录四元组。

## 七、发布判定

原定判定条件：

```text
P0-01 至 P0-07 全部关闭
+ P1-01 至 P1-07 在本文件中有对应声明
+ CI 七步通过
+ G6 签认（项目负责人 + 造价专业人员）
= 可发布 v1.0.0
```

本次实际判定：P0-01 至 P0-07 未全部关闭，P1 声明已补齐，CI 七步通过，签认栏为空；由项目负责人决定按缺口声明发布。P0 关闭后以 patch 版本更新，不追溯修改本文件。

## 八、签认

| 角色 | 姓名 | 日期 | 结论 |
|---|---|---|---|
| 项目负责人 | | 2026-10-19 | 决定按缺口声明发布 v1.0.0 |
| 造价专业人员 | | | 标准索引与地方文件审核待完成 |

## 九、变更记录

各版本变更见 `CHANGELOG.md`；发布阻断项见 `docs/release-blockers.md`。
