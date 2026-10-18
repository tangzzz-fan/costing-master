# Costing Master 能力与场景清单

> 面向江苏苏州市场，优先江浙沪地区文件；项目所在地文件始终优先。
>
> 状态说明：已实现 = 有 workflow/reference/template 和测试用例；部分实现 = 有参考或模板但仍需补充；规划 = 已列入 ROADMAP。

## 一、预算与计价场景

| 场景 | 典型任务 | 对应 workflow/reference/template | 状态 |
|---|---|---|---|
| 投资估算/目标成本初测 | 单方指标、含量指标、目标成本框架 | `references/zaojia-indicators.md`、`references/cost-management.md`、`templates/target-cost-estimate.md` | 部分实现 |
| 设计概算/施工图预算 | 清单组价、取费、计税、预算汇总 | `workflows/pricing-and-bid-review.md`、`templates/comprehensive-unit-price-analysis.md`、`references/fee-composition.md` | 已实现 |
| 最高投标限价 | 限价编制、价格来源、发布说明 | `workflows/pricing-and-bid-review.md`、`templates/bid-price-analysis-table.md`、`references/fee-composition.md` | 已实现 |
| 投标报价分析 | 总价、单价分布、金额集中度、异常报价 | `workflows/pricing-and-bid-review.md`、`templates/bid-price-analysis-table.md` | 已实现 |
| 清标/报价澄清 | 算术误差、漏项、异常单价、应足额计取费用 | `workflows/pricing-and-bid-review.md`、`templates/clearance-question-list.md` | 已实现 |
| 综合单价组价 | 人材机、管理费、利润、风险、辅助工作 | `references/boq-and-pricing.md`、`templates/comprehensive-unit-price-analysis.md` | 已实现 |
| 定额套用与换算 | 清单量/定额量、换算、补充子目 | `references/quota-application-and-conversion.md`、`references/software-and-quotas.md` | 已实现 |
| 措施项目费 | 安全生产措施费、文明施工、环境保护、临时设施、其他措施 | `references/fee-composition.md`、`references/boq-and-pricing.md` | 已实现 |
| 其他项目费 | 暂列金额、暂估价、计日工、总承包服务费 | `references/fee-composition.md`、`references/boq-and-pricing.md` | 已实现 |
| 增值税与取费 | 税前全费用、增值税单列、地方费用文件 | `references/fee-composition.md` | 已实现 |
| 材料调差 | 基准期、施工期、风险幅度、信息价、询价 | `workflows/material-price-analysis.md`、`references/material-price-adjustment.md`、`templates/material-price-adjustment-table.md` | 已实现 |
| 成本管理/动态成本 | 目标成本、合同成本、动态成本、偏差分析 | `workflows/cost-management.md`、`templates/cost-variance-analysis-table.md` | 已实现 |
| 地铁车站/盾构预算 | 车站、地连墙、盾构、管片、交通导改、监测 | `workflows/metro-rail-transit-audit.md`、`references/metro-rail-transit.md`、`input-specs/metro-boq.md` | 已实现，待地方文件人工审核 |
| 结算/决算/审计 | 结算审核、审减/审增、决算、审计 | `workflows/settlement-audit.md`、`references/audit-and-settlement.md` | 已实现 |

## 二、其他常用功能

| 功能 | 输出 | 对应 workflow/reference/template | 状态 |
|---|---|---|---|
| 清单特征与漏项检查 | 特征检查表、疑似漏项、量价交叉验证 | `workflows/boq-missing-items-check.md`、`references/boq-check-rules.md` | 已实现 |
| 合同造价风险识别 | 风险台账、条款引用、谈判关注点 | `workflows/contract-risk-review.md`、`references/contract-and-risk.md` | 已实现 |
| 变更签证审核 | 签证审核表、证据链、重复计取提示 | `workflows/change-visa-audit.md`、`references/change-order-and-claims.md` | 已实现 |
| 索赔费用审核 | 事件事实、时效、数量、单价、附件 | `workflows/change-visa-audit.md`、`templates/metro-claim-evidence-checklist.md` | 已实现 |
| 进度款审核 | 已完产值、预付款扣回、质保金、甲供材 | `workflows/progress-payment-audit.md`、`templates/progress-payment-audit-table.md` | 已实现 |
| 竣工结算审核 | 结算组成、审减/审增、付款扣回 | `workflows/settlement-audit.md`、`templates/settlement-audit-report.md` | 已实现 |
| 审减/审增台账 | 问题分类、金额、依据、判断等级 | `templates/settlement-deduction-register.md` | 已实现 |
| 算量指标反查 | 钢筋、混凝土、模板、砌体含量异常 | `workflows/quantity-indicator-check.md`、`templates/quantity-indicator-check-table.md` | 已实现 |
| 管理层摘要 | 风险排序、金额影响、下一步动作 | `templates/management-summary.md` | 已实现 |
| 文件抽取与证据索引 | 文件清单、证据索引、资料完整性、OCR/版本风险 | `workflows/document-extraction-and-evidence.md`、`templates/evidence-index.md`、`input-specs/document-intake.md` | 已实现 |
| 地区标准与版本门控 | 江苏/苏州、上海、浙江执行时间、地方资料 | `references/standards-index.md`、`references/region-jiangsu-shanghai-zhejiang.md` | 已实现，待人工审核 |
| 新旧标准混用检查 | 2013/2024 混用、地方过渡 | `references/standard-transition-check.md`、`test-cases/standard-change.case.md` | 已实现 |
| 质量评估与回归 | 覆盖率、数据来源、CI 四步、质量报告 | `references/evaluation-and-regression.md`、`scripts/eval_workflows.py`、`templates/quality-report.md` | 已实现 |
| 企业级交付 | 角色分离、交付包、审核记录、审计轨迹、签认边界、归档 | `workflows/enterprise-delivery.md`、`references/enterprise-delivery.md`、`templates/delivery-package.md`、`templates/review-record.md` | 已实现 |

## 三、不适用与边界

- 不替代算量软件、BIM、GTJ/GQI、GCCP 或地方定额库。
- 不替代注册造价工程师签章、企业审批、评标委员会判断、审计机关结论或法律意见。
- 不在缺少图纸、合同、清单、地勘、信息价期别等关键资料时给确定金额结论。
- 不编造定额编号、费率、材料价格、工程量、签证签字或监测数据。
- 地铁/盾构、DWG 图纸和 OCR 扫描件只按现有能力边界处理，不承诺完整算量。

## 四、典型使用路径

- 预算：清单 → 特征/漏项 → 组价 → 取费/计税 → 最高投标限价/投标报价 → 清标。
- 结算：资料清单 → 证据索引 → 变更/签证 → 材料调差 → 进度款/结算审核 → 管理层摘要。
- 成本：目标成本 → 合同成本 → 动态成本 → 偏差分析 → 管理层摘要。
- 地铁：车站/区间清单 → 车站/盾构特征 → 变更/监测 → 材料调差 → 进度款/结算。
- 标准变动：核对公告 → 更新索引/影响矩阵 → 更新测试场景 → 回归 → 人工审核。

## 五、相关入口

- `README.md`：项目定位、安装、目录结构。
- `SKILL.md`：触发词、使用原则、workflow/reference/template 导航。
- `ROADMAP.md`：版本计划和人工审核 gate。
- `test-cases/README.md`：测试覆盖矩阵和数据来源规则。
