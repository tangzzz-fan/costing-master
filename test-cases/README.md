# 测试用例索引

本目录用于人工验收和 Agent 自测。每个用例包含“模拟输入 / 期望行为 / 失败表现”，不需要真实项目文件；执行时先加载对应 workflow，再对照期望行为检查输出。

## 工作流覆盖矩阵

| 工作流 | 测试用例 | 示例 | 验收重点 |
|---|---|---|---|
| `workflows/settlement-audit.md` | `test-cases/settlement-audit.case.md` | `examples/settlement-audit-example.md` | 结算组成、审减证据、规费/增值税口径、质保金扣回 |
| `workflows/cost-management.md` | `test-cases/cost-management.case.md` | `examples/cost-management-example.md` | 目标/合同/动态/结算成本分列、偏差闭合、未确认变更单列 |
| `workflows/pricing-and-bid-review.md` | `test-cases/pricing-and-bid-review.case.md` | `examples/pricing-and-bid-review-example.md` | 组价边界、不平衡报价、清标问题、不代替评标 |
| `workflows/metro-rail-transit-audit.md` | `test-cases/suzhou-metro-station.case.md` | `examples/suzhou-metro-station-verification.md` | 地铁车站/盾构、变更签证、材料调差、进度款、结算 |
| `workflows/boq-missing-items-check.md` | `test-cases/boq-feature-missing.case.md` | `examples/boq-check-example.md` | 特征缺失、疑似漏项、量价交叉验证、不直接组价 |
| `workflows/contract-risk-review.md` | `test-cases/contract-risk.case.md` | `examples/contract-risk-example.md` | 风险分级、条款引用、不做法定性 |
| `workflows/change-visa-audit.md` | `test-cases/duplicate-visa.case.md` | `examples/change-visa-example.md` | 重复计取、证据链、书面指令、人工确认 |
| `workflows/material-price-analysis.md` | `test-cases/material-adjustment.case.md` | — | 基准期/施工期、风险幅度、只调超出部分 |
| `workflows/progress-payment-audit.md` | `test-cases/progress-payment.case.md` | `examples/progress-payment-example.md` | 未确认签证、预付款扣回、质保金、付款上限 |
| `workflows/quantity-indicator-check.md` | `test-cases/rebar-indicator.case.md` | — | 含量反算、结构形式匹配、不直接判定算量错误 |
| `workflows/second-pass-review.md` | `test-cases/second-pass-review.case.md` | — | 证据链、结论降级、禁止交付条件 |

## 专项用例

| 主题 | 测试用例 | 验收重点 |
|---|---|---|
| 新旧标准混用 | `test-cases/standard-transition.case.md` | 合同约定优先、地方过渡文件、软件模板 |
| 综合单价分析 | `test-cases/unit-price-analysis.case.md` | 套项思路、清单量/定额量、缺资料时不报确定单价 |
| 苏州地铁车站土建结算 | `test-cases/suzhou-metro-station.case.md` | 地铁车站/盾构、变更签证、材料调差、进度款、结算审核、地区资料 |

## 回归约定

- 修改 workflow、template、reference 或 SKILL.md 后，至少回归本矩阵中受影响的用例。
- 新增 workflow 时，必须同时新增至少一个 `test-cases/*.case.md` 并在本表登记。
- 校验脚本 `scripts/validate.py` 会检查本表是否覆盖全部 `workflows/*.md`。
