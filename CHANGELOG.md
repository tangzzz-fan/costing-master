# Changelog

## v1.0.0 — 2026-10-19

- 稳定发布：清单检查、预算与投标、结算审核、合同风险、变更签证、材料调差、进度款、成本管理、地铁专项、文件抽取、企业交付和二次审核共 12 条工作流
- 新增 `docs/release-blockers.md`：P0/P1 发布阻断清单和发布判定
- 新增 `RELEASE-v1.0.0.md`：发布范围、适用依据、已知限制、未关闭缺口和签认
- 新增 `references/version-compatibility.md`：版本四元组、兼容判定、升级和回滚
- 新增 `examples/delivery-package-viii-ts-08.md` 和 `examples/review-record-viii-ts-08.md`：交付包和审核记录实例
- 补充已知限制章节：标准索引待人工审核、C01–C09 缺日期、单价库无真实样本、公式验证含模拟数据、谈判案例为教学示例
- 发布决定：在 P0-01 至 P0-07 未全部关闭的情况下按缺口声明发布，缺口见发布说明第五节
- bump version 1.0.0

## 已知限制（截至 v1.0.0）

- 标准索引 27 条中 26 条仍为「待人工审核」，仅 S01 完成原文核对待签认；标准编号、日期和地方执行时间引用前需人工复核。
- C01–C09 九本工程量计算标准缺发布日和实施日，无法自动判断九本标准的适用时点。
- 单价库无真实成交样本，参考区间为经验值，不得作为报价、审核或结算依据。
- 工程量估算公式仅用于合理性判断，MQ-01/02/05 使用模拟数据，不能替代设计图纸和算量软件。
- 谈判案例为教学示例，金额和谈判结果不对应真实项目。
- 不适用于海外计价规则、国际合同范本和非中国标准计价项目，也不替代签章、评标或法律意见。

## v0.13.0 — 2026-10-19

- 新增 `scripts/metro_quantity_estimator.py`：地铁车站和盾构区间工程量快速估算，输出 11 项车站工程量和 5 项区间工程量，并与设计值对比误差
- 新增 `scripts/test_project_applicability.py`：按招标公告或合同日期判断江浙沪项目适用的国家标准和地方规则，8 个场景断言
- 新增 `scripts/test_metro_quantity.py`：地铁工程量校核公式验证，5 个公式误差断言和适用边界说明
- 新增 `scripts/check_unit_price_data.py`：单价样本 CSV 校验、参考区间计算和异常样本标记，支持 `--template` 打印表头
- 新增 `scripts/test_unit_price_data.py`：单价校验逻辑 9 项断言，数据取自单价收集指南示例
- 新增 `references/negotiation-strategy.md`：谈判准备、9 类争议点应对、话术模板和 2 个教学示例案例
- 新增 `江浙沪单价数据收集指南.md`：数据来源、抽取步骤、参照区间口径、质量控制和任务安排
- 新增 `第一阶段进展报告.md` 和 `全部任务完成总结报告.md`
- 补全 `test-cases/project-applicability.case.md`、`test-cases/metro-quantity-check.case.md`、`test-cases/standards-verification.case.md` 的数据来源、期望行为和失败表现章节
- `scripts/eval_workflows.py` 增加地区适用性断言和工程量公式断言两步，新增步骤摘要输出
- CI 由四步扩展为七步，增加规则治理、地区适用性断言、工程量公式断言和运行并发取消
- `rules/rule-registry.json` 补齐 3 个测试用例的规则覆盖，规则测试、workflow 和测试用例覆盖率均为 100%
- 核实标准日期：GB/T 50500-2024 为住建部公告 2024 年第 212 号，签发 2024-11-26，住建部官网发布 2024-12-30，2025-09-01 实施
- 核实地方文件日期：江苏省住建厅公告〔2025〕第12号落款 2025-12-19，官网发布 2025-12-22，2026-06-01 实施，同时废止苏建价〔2014〕448 号
- 修正 `test-cases/metro-unit-price-data.template.md` 和 `审核报告-标准与地区资料.md` 的重复标题
- 谈判案例标注为教学示例，修正案例内金额口径和公告年份
- 单价指南的参考区间标注为经验区间，待真实样本替换
- 统一测试脚本 docstring 的规则 ID 与 `rules/rule-registry.json`
- 忽略本地 `.workbuddy/` 记忆目录
- bump version 0.13.0

## v0.12.0 — 2026-10-19

- 新增 `rules/rule-registry.json`：登记 14 条规则，包含规则 ID、来源、状态、生效日期、关联 workflow/reference/template/test、执行方式和审核人
- 新增 `rules/README.md`：规则生命周期、任务清单、preflight/postflight、hooks、覆盖率、历史资料检索和新增规则流程
- 新增 `templates/task-manifest.md`：复杂任务规则清单模板，记录规则 ID、使用文件、证据编号、质检和交付状态
- 新增 `scripts/check_rule_governance.py`：检查规则字段、唯一 ID、日期、路径、任务清单章节、规则测试覆盖率、workflow 覆盖率和测试用例覆盖率
- `scripts/eval_workflows.py` 集成规则治理检查，质量报告增加规则数、规则测试覆盖率、workflow/测试用例规则覆盖率和 CI 检查行
- 新增 `hooks/`：可选的 Claude Code preflight/postflight 提醒脚本和示例配置，默认不启用
- 新增 `test-cases/rule-governance.case.md`，并登记测试覆盖矩阵；规则治理用例纳入 R-010 测试
- `scripts/validate.py` 支持 `rules/` 和 `hooks/` 路径校验
- 修正 README 安装地址为当前远程仓库地址
- 忽略 Python 缓存文件
- SKILL/README/CAPABILITIES/ROADMAP/质量报告模板同步
- bump version 0.12.0

## v0.11.0 — 2026-10-18

- 新增 `references/excel-output-guide.md`：Excel 适用场景、工作簿结构、公式规范、证据列、数据验证和签认边界
- 新增 `templates/excel/`：8 个 Excel 兼容 CSV 表头模板（清单、报价、调差、进度款、结算台账、成本偏差、证据索引、综合单价）
- 新增 `test-cases/excel-output.case.md`：使用苏州地铁公开项目框架和现有证据验证 Excel 输出实践
- `scripts/validate.py` 增加 Excel CSV 模板存在性、UTF-8 BOM 和表头检查
- SKILL/README/CAPABILITIES/测试矩阵同步
- bump version 0.11.0

## v0.10.0 — 2026-10-18

- 新增 `references/enterprise-delivery.md`：角色分离、交付物清单、G1-G6 审核 gate、审计轨迹、版本兼容、保密与归档
- 新增 `templates/review-record.md` 和 `templates/delivery-package.md`
- 新增 `workflows/enterprise-delivery.md`：内部审核、对外交付包和归档工作流
- 新增 `test-cases/enterprise-delivery.case.md` 和 `examples/enterprise-delivery-example.md`
- 明确 AI 只做工作底稿，不签认、不盖章、不代替注册造价工程师
- SKILL/README/CAPABILITIES/测试矩阵同步
- bump version 0.10.0

## v0.9.2 — 2026-10-18

- 新增 `test-cases/fixtures/standard-change/scenario.json`：苏州/浙江标准变动适用性测试数据
- 新增 `scripts/test_standard_change.py`：A/B/C/D 四项目旧版/新版标准与地方规则断言
- 扩充 `test-cases/standard-change.case.md`：苏州 2026-06-01 实际变更 + 浙江 2026-11-01 即将变更
- `standards-index.md` 增加历史版本 L00（江苏 2014 版）和 L04（浙江 2018 版）
- CI 增加标准变动断言步骤，形成结构、业务、标准变动、评估四步
- 质量报告模板增加标准变动检查
- bump version 0.9.2

## v0.9.1 — 2026-10-18

- `references/standards-index.md` 增加标准影响矩阵和机器可读登记（v0.4）
- `test-cases/fixtures/suzhou-metro-viii-ts-08/scenario.json` 增加 `standard_version`、`local_rules_id`、`last_reviewed` 和 `legacy_project`
- `scripts/eval_workflows.py` 增加标准新鲜度检查：标准/地方规则登记、废止标志、12 个月核对期限
- 新增 `test-cases/standard-change.case.md`：使用真实公开的江苏/苏州标准执行通知，测试标准变动、合同日期划断和影响矩阵
- `templates/quality-report.md` 增加标准新鲜度字段
- 新增 `CAPABILITIES.md`：预算/计价场景和其他常用功能清单
- README/SKILL/测试矩阵同步

## v0.9.0 — 2026-10-18

- 新增 `references/evaluation-and-regression.md`：评估层级、golden case、质量指标、回归流程和限制
- 新增 `templates/quality-report.md`：质量评估与回归报告模板
- 新增 `scripts/eval_workflows.py`：workflow 覆盖率、测试用例登记率、数据来源声明率、真实/模拟用例数和 CI 结果报告
- 新增 `test-cases/evaluation-and-regression.case.md`
- CI 增加评估步骤，形成结构校验、业务断言、评估报告三步
- README/SKILL/测试矩阵同步

## v0.8.0 — 2026-10-18

- 新增 `references/file-extraction-and-evidence.md`：文件类型、抽取流程、证据索引、可靠性分级、资料完整性和安全边界
- 新增 `input-specs/document-intake.md`：混合文件、扫描件、邮件、会议纪要的输入规范
- 新增 `templates/evidence-index.md`：证据索引与资料完整性清单
- 新增 `workflows/document-extraction-and-evidence.md`：文件抽取与证据链工作流
- 新增 `test-cases/document-extraction-and-evidence.case.md` 和真实公开资料测试清单
- 测试用例索引增加“数据来源”列和真实数据规则；每个新功能版本必须有对应测试用例
- SKILL/README/测试矩阵同步

## v0.7.1 — 2026-10-18

- 新增 `scripts/test_scenarios.py`：苏州地铁场景确定性业务断言，覆盖进度款扣回、材料调差、结算组成差异和问题分类
- 新增 `test-cases/fixtures/suzhou-metro-viii-ts-08/scenario.json`：机器可读测试数据
- CI 增加业务断言步骤，结构校验和业务断言分开执行
- README 和测试用例索引补充自动化测试说明

## v0.7.0 — 2026-10-18

- 新增 `references/metro-rail-transit.md`：地铁车站/盾构清单特征、合同风险、变更索赔、材料调差、进度/结算和江浙沪计价依据
- 新增 `input-specs/metro-boq.md`
- 新增 `templates/metro-boq-feature-check-table.md`、`templates/metro-claim-evidence-checklist.md`
- 新增 `workflows/metro-rail-transit-audit.md`
- 苏州地铁测试场景接入工作流和回归矩阵
- `standards-index`、`region-jiangsu-shanghai-zhejiang`、`software-and-quotas` 等增加城市轨道交通专项索引和交叉引用
- SKILL/README/测试矩阵同步

## v0.6.0 — 2026-10-18

- 新增 `workflows/pricing-and-bid-review.md`：预算/最高投标限价、投标报价分析、清标澄清工作流
- 新增 `templates/bid-price-analysis-table.md`、`templates/clearance-question-list.md`
- 新增 `test-cases/pricing-and-bid-review.case.md`、`examples/pricing-and-bid-review-example.md`
- `references/boq-and-pricing.md` 增加工作流和清标模板导航
- SKILL/README/测试用例矩阵同步

## v0.5.0 — 2026-10-18

- 新增 `workflows/cost-management.md`：目标成本、动态成本、成本偏差和管理层摘要工作流
- 新增 `templates/cost-variance-analysis-table.md`、`templates/target-cost-estimate.md`
- 新增 `test-cases/cost-management.case.md`、`examples/cost-management-example.md`
- `references/cost-management.md` 增加确定/预计/风险分列、结算成本边界和模板导航
- `templates/management-summary.md` 增加数据日期和成本口径字段
- SKILL/README/测试用例矩阵同步

## v0.4.2 — 2026-10-18

- 新增 `references/standards-index.md` 草案：标准、法规、9 本计算标准、地方资料索引和更新检查清单（标准条目待人工审核）
- 新增 `references/region-jiangsu-shanghai-zhejiang.md` 草案：江苏/苏州、上海、浙江地区优先级、执行时间、本地规则和项目适用清单（待人工审核）
- 新增 `ROADMAP.md`：v0.4.2 至 v1.0.0 版本计划、人工审核 gate 和发布检查清单
- 默认服务市场设为江苏苏州；SKILL/README 增加地区优先级和导航
- 更新省级定额、取费、市场询价和造价指标中的江浙沪优先口径

## v0.4.1 — 2026-10-18

### 修正

- 修正 GB/T 50500-2024 章节结构、综合单价口径、材料调差公式、结算审核时限来源、12位项目编码标签、费用组成人员归属和无限风险对比表
- 按 2024 版拆分安全生产措施费、文明施工费、环境保护费和临时设施费；修正安全生产措施费“不可竞争”的绝对表述
- 增值税计税基数排除含税的专业工程暂估价，避免重复计税
- 修正管理费取费基数和比例表述、缺陷责任期退还质保金表述、斯维尔厂商名称和竣工结算英文术语
- 标注审减率、地区系数、暂列金额比例和 2025 年指标为经验参考或待更新数据；成都示例改为项目所在地占位口径
- 同步 README 目录结构与版本路线

### 新增

- 新增 `test-cases/settlement-audit.case.md`、`test-cases/README.md` 覆盖矩阵
- 新增 `examples/progress-payment-example.md`、`examples/change-visa-example.md`
- 新增 `scripts/validate.py` 和 `.github/workflows/validate.yml`
- 新增仓库禁用 emoji 约定，并加入校验脚本

### 调整

- 合并 SKILL.md 重复的自检章节，质检模板补充质检时间、检查人、可交付签章字段
- DWG 第三方 AutoLISP 脚本改为用户确认后手动执行的可选步骤
- README 增加开发校验说明；SKILL.md 增加 `metadata.version`

## v0.4.0 — 2026-05-27

- 新增 `references/dwg-cad-handling.md`：DWG/CAD 三级处理能力模型（L1文本/L2几何/L3模型算量），能力判断流程，QCAD轻量提取操作指南，诚实表述模板
- 新增 `references/market-pricing-fallback.md`：信息价缺失时的五级定价降级方法，地区系数参考，主要材料暂估方法，定价输出格式规范
- `workflows/second-pass-review.md`：步骤4从纯定性扩展为定性+定量检查（合价验算、含量反算、单方验算、单价分布），增加基准匹配偏差判断逻辑
- `workflows/quantity-indicator-check.md`：新增步骤0 — 按清单文件规模选择处理策略（≤3/4-15/>15张计价表），按专业分组+重复编码跨sheet核查
- `input-specs/excel-boq.md`：新增广联达/GCCP标准导出格式快速识别（6类工作表+标准列结构），大型BOQ三级处理策略

## v0.3.0 — 2026-05-26

- 新增 `references/quota-application-and-conversion.md`：定额套用与换算实操，清单量与定额量区分，端到端组价示例
- 新增 `references/rebar-flat-method-basics.md`：钢筋平法基础知识，含钢量异常信号及复核提示
- 新增 `references/standard-transition-check.md`：GB 50500-2013与GB/T 50500-2024过渡期混用风险检查
- 新增 `workflows/progress-payment-audit.md`：进度款审核Agent工作流，预付款扣回+质保金+甲供材
- 新增 `workflows/quantity-indicator-check.md`：算量指标反查Agent工作流
- 新增 `templates/progress-payment-audit-table.md`、`templates/quantity-indicator-check-table.md`
- 新增安装/市政清单专项检查规则

## v0.2.0 — 2026-05-26

- 将 Skill 定位从知识参考扩展为文件审核工作流辅助
- 新增 `input-specs/`：定义清单、合同、结算书、签证变更、材料价格表的输入规范
- 新增 `workflows/`：提供结算审核、清单漏项检查、合同风险识别、签证审核、材料价格分析工作流
- 新增 `templates/`：提供结算审核报告、审减台账、合同风险台账、材料调差表等交付模板
- 新增 `examples/` 和 `test-cases/`：真实任务示例和人工验收用例
- 新增 `references/boq-check-rules.md` 和 `references/cost-management.md`
- 强化证据引用、缺资料处理、价格/定额防胡编和人工确认规则
- 新增二次审核工作流和质检报告模板

## v0.1.0 — 2026-05-26

- 初始造价知识库版本
- 覆盖 GB/T 50500-2024、清单计价、综合单价、合同风险、变更签证、材料调差、结算审核等基础 reference
