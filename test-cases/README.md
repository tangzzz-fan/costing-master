# 测试用例索引

本目录用于人工验收和 Agent 自测。每个用例包含数据来源、输入资料、期望行为和失败表现；执行时先加载对应 workflow，再对照期望行为检查输出。

> 新版本功能规则：每个新增功能版本必须新增至少一个对应测试用例，数据优先使用真实实际内容。详见“回归约定”。

## 工作流覆盖矩阵

| 工作流 | 测试用例 | 示例 | 数据来源 | 验收重点 |
|---|---|---|---|---|
| `workflows/settlement-audit.md` | `test-cases/settlement-audit.case.md` | `examples/settlement-audit-example.md` | 模拟/教学 | 结算组成、审减证据、规费/增值税口径、质保金扣回 |
| `workflows/cost-management.md` | `test-cases/cost-management.case.md` | `examples/cost-management-example.md` | 模拟/教学 | 目标/合同/动态/结算成本分列、偏差闭合、未确认变更单列 |
| `workflows/pricing-and-bid-review.md` | `test-cases/pricing-and-bid-review.case.md` | `examples/pricing-and-bid-review-example.md` | 模拟/教学 | 组价边界、不平衡报价、清标问题、不代替评标 |
| `workflows/metro-rail-transit-audit.md` | `test-cases/suzhou-metro-station.case.md` | `examples/suzhou-metro-station-verification.md` | 真实公开项目框架 + 模拟成本数据 | 地铁车站/盾构、变更签证、材料调差、进度款、结算 |
| `workflows/document-extraction-and-evidence.md` | `test-cases/document-extraction-and-evidence.case.md` | `examples/document-extraction-example.md` | 真实公开资料 + 缺失清单 | 文件识别、字段抽取、证据索引、资料完整性、OCR/版本边界 |
| `workflows/enterprise-delivery.md` | `test-cases/enterprise-delivery.case.md` | `examples/enterprise-delivery-example.md` | 真实公开项目框架 + 现有测试证据（成本细节为模拟） | 角色分离、交付包、审核记录、签认边界、版本兼容 |
| `workflows/boq-missing-items-check.md` | `test-cases/boq-feature-missing.case.md` | `examples/boq-check-example.md` | 模拟/教学 | 特征缺失、疑似漏项、量价交叉验证、不直接组价 |
| `workflows/contract-risk-review.md` | `test-cases/contract-risk.case.md` | `examples/contract-risk-example.md` | 模拟/教学 | 风险分级、条款引用、不做法定性 |
| `workflows/change-visa-audit.md` | `test-cases/duplicate-visa.case.md` | `examples/change-visa-example.md` | 模拟/教学 | 重复计取、证据链、书面指令、人工确认 |
| `workflows/material-price-analysis.md` | `test-cases/material-adjustment.case.md` | — | 模拟/教学 | 基准期/施工期、风险幅度、只调超出部分 |
| `workflows/progress-payment-audit.md` | `test-cases/progress-payment.case.md` | `examples/progress-payment-example.md` | 模拟/教学 | 未确认签证、预付款扣回、质保金、付款上限 |
| `workflows/quantity-indicator-check.md` | `test-cases/rebar-indicator.case.md` | — | 模拟/教学 | 含量反算、结构形式匹配、不直接判定算量错误 |
| `workflows/second-pass-review.md` | `test-cases/second-pass-review.case.md` | — | 模拟/教学 | 证据链、结论降级、禁止交付条件 |

## 专项用例

| 主题 | 测试用例 | 数据来源 | 验收重点 |
|---|---|---|---|
| 新旧标准混用 | `test-cases/standard-transition.case.md` | 模拟/教学 | 合同约定优先、地方过渡文件、软件模板 |
| 综合单价分析 | `test-cases/unit-price-analysis.case.md` | 模拟/教学 | 套项思路、清单量/定额量、缺资料时不报确定单价 |
| 苏州地铁车站土建结算 | `test-cases/suzhou-metro-station.case.md` | 真实公开项目框架 + 模拟成本数据 | 地铁车站/盾构、变更签证、材料调差、进度款、结算审核、地区资料 |
| 混合文件抽取与证据链 | `test-cases/document-extraction-and-evidence.case.md` | 真实公开资料 + 缺失清单 | 文件识别、字段抽取、证据索引、资料完整性、OCR/版本边界 |
| 评估与回归 | `test-cases/evaluation-and-regression.case.md` | 真实公开 + 现有用例 | 覆盖率、数据来源、CI 四步、质量报告、人工语义审核 |
| 标准变动与地方执行 | `test-cases/standard-change.case.md` | 真实公开标准/地方通知（江苏/苏州 + 浙江） | 标准版本识别、地方执行时间、合同日期划断、影响矩阵、测试更新 |
| Excel 输出 | `test-cases/excel-output.case.md` | 真实公开项目框架 + 现有测试证据（成本细节为模拟） | 工作簿结构、公式、证据列、判断等级、版本与签认边界 |
| 规则调用治理 | `test-cases/rule-governance.case.md` | 真实公开项目框架 + 仓库规则登记（成本细节为模拟） | 任务清单、规则 ID、preflight/postflight、规则覆盖率、人工 gate |
| 项目标准适用性判断 | `test-cases/project-applicability.case.md` | 模拟（基于真实地方通知和执行时间） | 江浙沪执行时间、招标/合同日期划断、边界日期处理、国有/非国有资金适用 |
| 地铁工程量校核公式验证 | `test-cases/metro-quantity-check.case.md` | 真实公开（MQ-03/04）+ 模拟（MQ-01/02/05，基于真实车站规模） | 公式准确性、误差分析、适用边界、修正系数、使用原则 |
| 标准文本验证 | `test-cases/standards-verification.case.md` | 真实公开官方文件待核对 | 标准编号、名称、日期、官方来源、链接可访问性、地方文号验证 |

## 回归约定

- 每个新增功能版本必须新增至少一个对应测试用例，并登记在本表。
- 新用例的数据优先使用真实实际内容：公开招标/合同/项目资料、真实标准文件，或经脱敏的真实项目文件。
- 无法公开或未取得的合同、清单、签证、图纸等，标记为“缺失/需原件”，不得虚构内容。
- 纯计算演练可以使用模拟数据，但必须标注“模拟”，且不能替代真实数据用例。
- 修改 workflow、template、reference 或 SKILL.md 后，至少回归本矩阵中受影响的用例。
- 新增 workflow 时，必须同时新增至少一个 `test-cases/*.case.md` 并在本表登记。
- 校验脚本 `scripts/validate.py` 会检查本表是否覆盖全部 `workflows/*.md`。
- `scripts/check_rule_governance.py` 会检查规则登记、任务清单章节、规则测试覆盖率、workflow 覆盖率和测试用例覆盖率；`scripts/eval_workflows.py` 会调用该检查。
- 复杂任务应使用 `templates/task-manifest.md` 记录规则 ID、workflow、证据和人工 gate。
- 苏州地铁场景的确定性计算由 `scripts/test_scenarios.py` 自动断言；证据分级、结论强度等语义判断仍按用例人工验收。
- 现有标注“模拟/教学”的用例，将在后续版本逐步补充真实数据用例；新增功能不得只提供模拟数据。
