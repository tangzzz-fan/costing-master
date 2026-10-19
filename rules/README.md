# 规则调用治理

> 规则登记、任务清单、preflight/postflight 和规则覆盖率的统一入口。
>
> `rules/rule-registry.json` 是机器可读的唯一规则台账；`SKILL.md` 只负责路由和原则，不重复维护规则细节。

## 一、目的

造价文件、标准、地方规则和历史项目资料会持续增加。仅依靠 `SKILL.md` 的文字提醒，无法保证每次任务都调用正确的 workflow、reference、template 和判断规则。本目录把关键规则变成可编号、可检索、可测试、可审核的登记项。

治理目标：

- 每个关键规则有唯一 ID、来源、适用范围、生效日期和审核状态。
- 每个复杂任务有任务清单，记录使用了哪些规则、文件、证据和人工确认点。
- 每条生效规则至少关联一个测试用例；每个 workflow 和测试用例至少被一条规则覆盖。
- 规则变更触发回归测试；废止规则保留历史，不直接删除。
- 输出前的检查由脚本和 CI 执行，不依赖模型记忆。

## 二、规则清单

| 规则 ID | 规则 | 触发场景 | 执行方式 | 主要测试 |
|---|---|---|---|---|
| R-001 | 缺资料先列清单 | 合同、清单、图纸、信息价期别等关键资料缺失 | 清单 + 人工确认 | 结算审核、文件抽取、清单漏项 |
| R-002 | 证据可追溯 | 审核意见、风险判断、金额调整、指标反查 | 脚本检查 + 人工确认 | 结算审核、文件抽取、企业交付、钢筋指标 |
| R-003 | 禁止凭空造价 | 组价、报价、补项、定额套用、材料价格 | 脚本检查 + 人工确认 | 综合单价、投标报价、清单漏项 |
| R-004 | 判断等级和结论强度 | 证据不足、事实争议、责任未定、金额待确认 | 清单 + 人工确认 | 重复签证、结算审核、成本管理 |
| R-005 | 2024 版费用和增值税口径 | 2024 版项目结算、进度款、预算和报价 | 清单 + 人工确认 | 结算审核、标准过渡、进度款、投标报价 |
| R-006 | 材料调差只调风险幅度外部分 | 信息价、询价、基准期和施工期价差 | 脚本检查 + 人工确认 | 材料调差、苏州地铁场景 |
| R-007 | 变更签证和索赔证据链 | 变更、签证、索赔、合同风险 | 清单 + 人工确认 | 重复签证、合同风险、苏州地铁场景 |
| R-008 | 交付前二次审核 | 涉及金额、审核意见、报价或交付包 | 脚本检查 + 人工确认 | 二次审核 |
| R-009 | 标准和地方规则新鲜度 | 标准版本、地方执行时间、合同日期划断 | 脚本检查 + 人工确认 | 标准变动、标准过渡、评估回归、苏州地铁场景 |
| R-010 | 新增功能必须有真实数据测试 | 新增 workflow、template、reference 或规则 | 脚本检查 + 人工确认 | 评估回归、标准变动、文件抽取、规则治理 |
| R-011 | AI 不签认，企业交付需人工签认 | 对外交付、审核记录、签章、归档 | 清单 + 人工确认 | 企业交付、合同风险 |
| R-012 | 文件抽取和 OCR/DWG 能力边界 | 扫描件、混合文件、图纸、版本识别 | 清单 + 人工确认 | 文件抽取、苏州地铁场景 |
| R-013 | 地区优先级与跨地区隔离 | 江苏/苏州、上海、浙江及其他地区 | 清单 + 人工确认 | 苏州地铁场景、标准变动 |
| R-014 | Excel 输出公式、证据和签认边界 | 台账、计算表、报价分析、成本分析 | 脚本检查 + 人工确认 | Excel 输出 |

## 三、规则生命周期

| 状态 | 含义 | 要求 |
|---|---|---|
| draft | 规则草案，尚未生效 | 可用于内部讨论；不得作为交付依据 |
| active | 现行有效 | 必须有来源、生效日期、关联文件、至少一个测试和审核人 |
| deprecated | 已废止，保留历史 | 保留原 ID 和废止日期；新任务不得引用；测试可保留作回归 |
| superseded | 被新规则替代 | 记录替代规则 ID；引用时同时检查新旧规则 |

规则 ID 一经发布不重复使用。规则内容变化时，优先新增版本或在 `source`、`effective_date` 和 `last_reviewed` 中记录变更；涉及金额口径、标准适用或法律边界的变更，必须走人工审核。

## 四、任务清单

复杂任务开始时，复制 `templates/task-manifest.md`，至少记录：

- 任务基本信息：任务编号、日期、项目、地区、阶段、成果类型、执行人。
- 适用规则：规则 ID、触发原因、执行状态。
- 使用文件：workflow、reference、template、input-spec 和项目文件。
- 证据编号：证据索引中的编号、文件名、页码/行号或条款号。
- 质检与审核：二次审核结论、未通过项、人工确认点和签认人。
- 交付状态：草稿、工作底稿、可提交审核、已签认；不得把 AI 写成签认人。

任务清单不替代正式审核记录。对外交付仍按 `references/enterprise-delivery.md` 和 `templates/review-record.md` 执行。

## 五、Preflight 与 Postflight

| 阶段 | 检查内容 | 执行方式 |
|---|---|---|
| Preflight | 任务类型、项目地区、标准版本、合同类型、资料完整性、适用 workflow 和规则 ID | `SKILL.md` 路由表、任务清单、`hooks/preflight_reminder.py` |
| 执行中 | 证据编号、计算闭合、地区依据、判断等级、人工确认点 | workflow、template、二次审核 |
| Postflight | 必需章节、规则 ID、证据索引、质检摘要、交付状态、签认边界 | `scripts/check_rule_governance.py`、`workflows/second-pass-review.md`、`hooks/postflight_check.py` |
| CI | 规则登记、路径、覆盖率、测试和结构校验 | `scripts/check_rule_governance.py` 由 `scripts/eval_workflows.py` 调用 |

Preflight 的最低问题清单：

1. 项目所在地和适用标准版本是否明确。
2. 合同类型、计价方式和风险分配是否明确。
3. 关键资料是否齐全；缺失项是否进入需补资料清单。
4. 任务属于快速参考模式还是项目工作模式。
5. 需要哪些规则 ID、workflow、reference 和 template。
6. 是否存在必须人工确认的 standard、合同、法律或签认 gate。

Postflight 的最低检查：

1. 输出中是否出现规则 ID 或明确引用规则名称。
2. 每条金额调整是否有证据编号和计算过程。
3. 是否把疑似问题写成确定结论。
4. 是否在缺少地区依据时给出确定费率或价格。
5. 是否生成 `质检摘要.md` 并给出可交付/不可交付结论。
6. 是否保留人工签认栏，且未把 AI 写成签认人。

## 六、Hooks

`hooks/` 提供可选的 Claude Code hooks 示例，用于在任务开始和结束时注入提醒。Hooks 默认不启用，需由使用者按 `hooks/README.md` 合并到自己的 `.claude/settings.json`。

Hooks 只能提醒，不能替代 CI。真正的规则登记和覆盖率检查由 `scripts/check_rule_governance.py` 执行；涉及金额、合同、法律和签认的判断仍必须人工复核。

## 七、覆盖率与 CI

`python3 scripts/check_rule_governance.py` 检查：

- 规则 ID 唯一，必填字段完整，状态和日期有效。
- 规则引用的 workflow、reference、template 和测试路径存在。
- 每条 active 规则至少有一个测试。
- 每个 workflow 至少被一条 active 规则覆盖。
- 每个测试用例至少被一条 active 规则覆盖。
- `templates/task-manifest.md` 存在并包含必需章节。

`python3 scripts/eval_workflows.py` 会调用上述检查，并把规则总数、规则测试覆盖率、workflow 覆盖率和测试用例覆盖率写入质量报告。

质量门槛：

| 指标 | 目标 |
|---|---:|
| Active 规则有测试的比例 | 100% |
| Workflow 被规则覆盖的比例 | 100% |
| 测试用例被规则覆盖的比例 | 100% |
| 规则登记路径有效率 | 100% |
| 任务清单必需章节完整率 | 100% |

## 八、历史资料增长后的检索

规则和历史资料增长后，不要把所有 reference 一次性加载。按以下顺序检索：

1. 先从任务类型定位 workflow，例如结算审核、材料调差、变更签证、企业交付。
2. 从 `rules/rule-registry.json` 的 `workflows`、`references`、`templates` 和 `tests` 字段找相关规则和文件。
3. 用规则 ID 在仓库中反查，例如 `rg "R-006"`，确认相关 workflow、template 和测试。
4. 只加载命中的 reference 和 template；项目历史资料按项目编号、地区、阶段和证据编号另库存放，不混入规则台账。
5. 规则数量超过 50 条时，按地区、阶段、专业和任务类型增加标签，并保持 ID 稳定；不要用文件名代替规则 ID。

## 九、新增或变更规则

1. 在 `rules/rule-registry.json` 新增规则或修改现有规则，填写来源、生效日期、关联文件、测试、执行方式和审核人。
2. 至少新增或更新一个测试用例，并在 `test-cases/README.md` 登记。
3. 运行 `python3 scripts/check_rule_governance.py`，确认路径和覆盖率。
4. 运行 `python3 scripts/validate.py`、`python3 scripts/test_scenarios.py`、`python3 scripts/test_standard_change.py` 和 `python3 scripts/eval_workflows.py`。
5. 更新 `CHANGELOG.md`、版本号和必要的 SKILL/README 导航。
6. 由人工审核规则范围、标准依据、自动检查边界和人工 gate。

废止规则时，把 `status` 改为 `deprecated` 或 `superseded`，保留原 ID、废止日期和替代规则；不要直接删除历史规则。

## 十、人工 gate 与边界

- 规则登记不能替代注册造价工程师、企业审核人、法务或评标委员会判断。
- 自动检查只能验证结构、路径、覆盖率和部分计算；语义证据、结论强度和合同解释必须人工复核。
- 高风险规则包括：标准适用、费用和税率口径、材料调差、合同风险、索赔时效、签认和交付。
- 规则覆盖率不是目的；不得为了凑覆盖率编造测试、规则或预期结果。

## 十一、关联文件

- `rules/rule-registry.json`
- `templates/task-manifest.md`
- `scripts/check_rule_governance.py`
- `scripts/eval_workflows.py`
- `hooks/README.md`
- `workflows/second-pass-review.md`
- `references/evaluation-and-regression.md`
- `references/enterprise-delivery.md`
