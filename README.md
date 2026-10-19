# 造价大师 Costing Master

面向中国工程造价实务的 AI Skill，用于辅助工程量清单检查、预算编制、结算审核、合同商务风险识别、变更签证审核、材料价差分析和成本测算。

本项目不是定额库、算量软件或签章工具，而是一个“知识参考 + 文件审核工作流辅助”的 Skill：帮助造价人员从 Excel、PDF、Word、签证单、结算书、材料价格表等资料中抽取关键信息，形成可复核的台账、报告和需补资料清单。

默认服务地区：江苏苏州。项目工作模式下优先使用苏州市/江苏省现行计价依据，其次上海市、浙江省等江浙沪地区文件；跨地区项目以项目所在地文件和合同为准。

详细能力与场景清单见 `CAPABILITIES.md`。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-orange)](https://claude.ai/code)
[![Standard](https://img.shields.io/badge/GB%2FT%2050500--2024-red)](https://ebook.chinabuilding.com.cn/zbooklib/book/detail/show?SiteID=1&bookID=155858)

## 适用用户

- 造价员、预算员、结算员
- 成本管理、项目商务、招投标人员
- 项目经理、成本负责人、咨询审核人员

## 能做什么

| 场景 | 输出成果 |
|---|---|
| 工程量清单检查 | 清单特征检查表、疑似漏项登记表、需补资料清单 |
| 预算/报价辅助 | 综合单价分析框架、取费口径检查、报价异常提示 |
| 结算审核 | 结算审核报告、审减/审增问题台账、付款扣回核对 |
| 进度款审核 | 已完产值复核、预付款扣回、质保金扣留、甲供材扣回 |
| 定额套用与换算 | 套项思路、换算检查、清单量/定额量区分 |
| 合同风险识别 | 合同风险台账、造价条款风险等级、谈判关注点 |
| 变更签证审核 | 签证审核表、证据链评分、重复计取提示 |
| 材料价差分析 | 材料价差计算表、基准期/施工期缺项提示 |
| 算量指标反查 | 钢筋、混凝土、模板、砌体等含量异常提示 |
| 成本管理 | 目标成本初测、动态成本偏差表、管理层摘要 |
| 轨道交通/地铁车站与盾构 | 清单特征检查表、变更索赔证据清单、进度款/结算审核 |
| 资料抽取与证据链 | 证据索引、资料完整性清单、需补资料、OCR/版本风险提示 |
| 企业级交付 | 交付包、审核记录、审计轨迹、签认边界、归档清单 |
| Excel 输出 | 多 sheet 工作簿结构、公式、证据列、判断等级和台账模板 |
| 规则调用治理 | 规则 ID、任务清单、规则覆盖率、preflight/postflight 和人工 gate |

## 不能做什么

- 不替代注册造价工程师签章、企业审批或审计机关结论。
- 不替代法律意见、合同解释、评标委员会判断。
- 不凭空生成定额编号、地方费率、材料价格、税率适用方式或工程量。
- 不在缺少图纸、合同、清单、信息价期别等关键资料时给确定性金额结论。
- 不把内置全国参考指标作为唯一依据；实际工作应优先使用用户上传的项目所在地资料和项目文件。

## 工作模式

| 模式 | 数据来源 | 能做什么 |
|---|---|---|
| 快速参考模式 | 全国参考区间、通用造价知识 | 投资估算、目标成本初测、报价异常提示、需补资料清单 |
| 项目工作模式 | 用户上传的地区资料 + 合同/清单/图纸/价格表 | 预算编制辅助、投标报价校核、结算审核、合同风险识别、材料调差 |

涉及地区差异的信息，应优先提示用户上传项目所在地资料，例如当地定额、费用文件、材料信息价、人工费指导价、机械台班价、价格指数、招标文件、合同文件、企业历史成本数据和供应商询价记录。

## 二次审核机制

复杂任务完成后，Skill 会先生成初稿，再按 `workflows/second-pass-review.md` 执行二次审核，检查证据链、计算闭合、地区依据、专业口径、结论强度、重复/遗漏和人工确认点。

二次审核结果分为：

| 结论 | 含义 |
|---|---|
| 通过 | 初稿具备交付为工作底稿的基本条件 |
| 需修正 | 存在证据、计算、口径或资料问题，需先修改 |
| 禁止交付 | 存在无依据金额、关键计算错误、地区依据缺失却给确定结论等高风险问题 |

质检报告模板见 `templates/second-pass-review-report.md`。

## 规则调用治理

复杂造价任务使用 `rules/README.md` 选择规则，并用 `templates/task-manifest.md` 记录规则 ID、workflow、证据编号和人工确认点。规则登记在 `rules/rule-registry.json`，由 `scripts/check_rule_governance.py` 检查；`scripts/eval_workflows.py` 会把规则覆盖率写入质量报告。可选的 Claude Code hooks 示例见 `hooks/README.md`。

未记录规则 ID、未完成二次审核的成果只能作为草稿，不得标记为可交付签章。

## 目录结构

```text
costing-master/
├── SKILL.md
├── README.md
├── CHANGELOG.md
├── ROADMAP.md
├── CAPABILITIES.md
├── references/
│   ├── standards-index.md
│   ├── region-jiangsu-shanghai-zhejiang.md
│   ├── metro-rail-transit.md
│   ├── file-extraction-and-evidence.md
│   ├── evaluation-and-regression.md
│   ├── enterprise-delivery.md
│   ├── excel-output-guide.md
│   ├── gbt50500-2024.md
│   ├── boq-and-pricing.md
│   ├── boq-check-rules.md
│   ├── quota-application-and-conversion.md
│   ├── rebar-flat-method-basics.md
│   ├── standard-transition-check.md
│   ├── 13-step-cost-management.md
│   ├── contract-and-risk.md
│   ├── change-order-and-claims.md
│   ├── audit-and-settlement.md
│   ├── material-price-adjustment.md
│   ├── cost-management.md
│   ├── fee-composition.md
│   ├── software-and-quotas.md
│   ├── dwg-cad-handling.md
│   ├── zaojia-indicators.md
│   ├── market-pricing-fallback.md
│   └── glossary.md
├── rules/
│   ├── README.md
│   └── rule-registry.json
├── hooks/
│   ├── README.md
│   ├── preflight_reminder.py
│   ├── postflight_check.py
│   └── settings.example.json
├── input-specs/
├── workflows/
├── templates/
├── examples/
└── test-cases/
```

## 典型输入文件

| 文件 | 用途 |
|---|---|
| Excel 清单、报价表、结算表 | 清单检查、报价分析、结算审核 |
| PDF/Word 合同、招标文件 | 合同风险、评标办法、付款和调价条款 |
| 签证单、变更单、会议纪要 | 变更签证审核、证据链检查 |
| 材料价格表、信息价、询价单 | 材料调差、价格异常分析 |
| 图纸说明、做法表 | 清单特征和漏项检查辅助 |

## 建议上传的地区资料

- 项目所在地最新工程造价信息、材料信息价、人工费指导价、机械台班价。
- 江苏/苏州项目：苏州市工程造价信息、江苏省 2026 版消耗量指标/费用参考、苏州建函建〔2026〕72号。
- 上海、浙江项目：当地 2025 版计价规则/计价依据和当期信息价。
- 地铁项目：城市轨道交通工程计价表/消耗量、车站和区间清单、地质资料、监测方案、穿越审批。
- 当地现行计价定额、费用定额、取费文件、地方补充清单规则。
- 招标文件、合同文件、工程量清单、设计说明、答疑澄清。
- 企业历史项目成本数据、已标价工程量清单、综合单价分析表、供应商询价记录。

## 使用示例

```text
请按结算审核工作流，审核我上传的结算书、合同和签证台账。
输出：需补资料清单、审减/审增问题台账、管理层摘要。
```

```text
检查这份工程量清单的项目特征是否完整，重点看混凝土、钢筋、砌体、防水、门窗。
只输出疑似问题和需要人工确认的项，不要直接重新组价。
```

```text
从这份施工合同里识别造价风险，按高/中/低风险输出条款号、原文摘要、风险影响和修改建议。
```

更多示例见 `examples/`，人工验收用例见 `test-cases/`。

## 安装方法

### 项目级安装

```bash
mkdir -p .claude/skills
git clone https://github.com/tangzzz-fan/costing-master.git .claude/skills/costing-master
```

### 用户级安装

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/tangzzz-fan/costing-master.git ~/.claude/skills/costing-master
```

## 开发校验

```bash
python3 scripts/validate.py
python3 scripts/test_scenarios.py
python3 scripts/test_standard_change.py
python3 scripts/check_rule_governance.py
python3 scripts/eval_workflows.py
```

`validate.py` 检查 SKILL.md frontmatter、相对路径和链接、README 目录树、workflow 测试用例覆盖、markdown 表格一致性、重复标题、测试用例数据来源、Excel CSV 模板表头/BOM 和 emoji 禁用规则。

`test_scenarios.py` 执行苏州地铁 VIII-TS-08 场景的确定性业务断言，包括进度款扣回、材料调差、结算组成差异和问题分类。

`test_standard_change.py` 执行苏州/浙江标准变动断言，检查旧版/新版标准、地方规则、招标日期划断和适用性。

`check_rule_governance.py` 检查规则登记、任务清单必需章节、规则测试覆盖率、workflow 覆盖率和测试用例覆盖率。

`eval_workflows.py` 输出质量报告，统计 workflow 覆盖率、测试用例登记率、数据来源声明率、真实/模拟用例数、标准新鲜度、规则治理和 CI 四步结果。GitHub Actions 在 push 和 pull request 时自动运行四步；评估步骤内部同时执行规则治理检查。

仓库约定：正文和模板不使用 emoji 图标；状态标记使用 `[警告]`、`[通过]` 等文字。

## 适用依据

- GB/T 50500-2024《建设工程工程量清单计价标准》
- 苏州市/江苏省现行计价依据、费用文件和造价信息；上海市、浙江省文件按项目所在地适用
- 项目所在地现行建设工程计价依据、费用文件和造价信息
- 项目合同、招标文件、答疑澄清、补充协议
- GF-2017-0201《建设工程施工合同（示范文本）》仅作参考，具体以项目合同约定为准

标准、法规和计价依据的版本、来源与核对状态见 `references/standards-index.md`。

## 版本路线

当前版本：v0.12.0（详见 `CHANGELOG.md`）。v0.12.0 至 v1.0.0 的详细计划见 `ROADMAP.md`。

| 版本 | 状态 | 目标 |
|---|---|---|
| v0.1 | 已发布 | 造价知识库、GB/T 50500-2024 口径、基础 reference |
| v0.2 | 已发布 | 文件输入规范、Agent 工作流、输出模板、示例和测试用例 |
| v0.3 | 已发布 | 定额换算、进度款审核、算量指标反查、新旧标准混用检查 |
| v0.4 | 已发布 | DWG/CAD 处理、市场询价降级、二次审核量化、大型 BOQ 处理策略 |
| v0.4.1 | 已发布 | 2024 版费用口径修正、测试覆盖、示例、CI 和 emoji 禁用校验 |
| v0.4.2 | 已提交，待审核 | 标准、法规与计价依据索引；江浙沪地区资料；更新流程和人工审核清单 |
| v0.5 | 已发布 | 成本管理增强：目标成本、动态成本、偏差分析、管理层摘要 |
| v0.6 | 已发布 | 计价、投标报价与清标分析工作流 |
| v0.7 | 已发布 | 江浙沪地区资料包；地铁车站/盾构专项审核；版本门控 |
| v0.7.1 | 已发布 | 苏州地铁 CI 业务测试：进度款、材料调差、结算差异自动断言 |
| v0.8 | 已发布 | 文件抽取与证据链：证据索引、资料完整性、OCR/版本边界 |
| v0.9 | 已发布 | 评估与回归体系：覆盖率、数据来源、质量报告和 CI 三步 |
| v0.9.1 | 已发布 | 标准变动回归：标准新鲜度、影响矩阵和标准变动测试 |
| v0.9.2 | 已发布 | 苏州/浙江标准变动实际场景测试：旧版/新版适用性断言 |
| v0.10 | 已发布 | 企业级交付：角色分离、交付包、审核记录、审计轨迹和归档 |
| v0.11 | 已发布 | Excel 输出实践：工作簿结构、公式、证据列和 CSV 模板 |
| v0.12 | 已发布 | 规则调用治理：规则登记、任务清单、preflight/postflight、hooks 和覆盖率 |
| v1.0 | 规划 | 企业级文件审核 Skill：可复核台账、报告模板、团队交付规范 |

## 免责声明

本 Skill 输出为工作底稿和专业参考，不构成法律意见、合同解释、评标结论、审计结论或注册造价工程师签章成果。具体项目应以合同文件、招标文件、设计图纸、地方计价依据、现行法律法规和专业人员复核为准。

## License

MIT License.
