# 评估与回归体系参考

> 本文件说明如何评估 Skill 的结构、计算、证据和语义质量，以及如何在版本更新后做回归。
>
> 评估不能只靠“看起来对”；需要区分结构校验、确定性计算、真实数据用例和人工语义审核。

## 一、评估层级

| 层级 | 评估内容 | 工具 | 是否可自动 |
|---|---|---|---|
| L1 结构 | frontmatter、路径、表格、目录树、workflow 覆盖、数据来源声明、emoji | `scripts/validate.py` | 是 |
| L2 确定性计算 | 进度款、材料调差、结算组成差异、问题分类 | `scripts/test_scenarios.py` | 是 |
| L3 真实数据用例 | 公开项目页、标准/地区文件、缺失资料清单、证据索引 | 测试用例 + 人工/语义审核 | 部分 |
| L4 语义质量 | 证据链、结论强度、缺资料降级、专业判断 | 人工审核/LLM 评估 | 否，必须人工复核 |
| L5 发布 | 版本、CHANGELOG、CI、审核记录 | 发布检查清单 | 人工签认 |

## 二、Golden case 规则

- Golden case 是带预期结果的结构化测试数据，放在 `test-cases/fixtures/` 下，使用 `scenario.json` 或等价格式。
- 必须包含：数据来源、输入、预期输出、适用版本、最近核对日期。
- 预期值必须能从输入和合同/标准/计算规则推导；不能凭“感觉”写。
- 使用真实公开数据或脱敏实际数据；无法公开的资料标记缺失，不虚构。
- 纯计算演练可以使用模拟数据，但必须标注“模拟”，且不能替代真实数据用例。
- 修改 golden case 必须有对应测试和人工审核记录。

## 三、质量指标

- Workflow 覆盖率：100%，每个 `workflows/*.md` 必须在 `test-cases/README.md` 登记测试用例。
- 数据来源声明率：100%，每个 `test-cases/*.case.md` 必须有 `## 数据来源`。
- 真实数据用例：每个新增功能版本至少一个，使用公开项目资料、真实标准或脱敏实际文件。
- 确定性断言：覆盖进度款、材料调差、结算差异等可计算逻辑；断言失败必须阻断 CI。
- CI 通过率：结构校验、业务断言、标准变动断言、规则治理检查和评估报告全部通过。
- 规则覆盖率：active 规则有测试的比例、workflow 被规则覆盖的比例、测试用例被规则覆盖的比例均达到 100%。
- 语义质量：由人工按用例的“期望行为/失败表现”验收，不能由 CI 完全替代。

## 四、回归触发条件

- 新增或修改 workflow、template、reference、input-spec、SKILL.md。
- 标准、法规、地方文件或价格信息更新。
- 修复计算、证据或结论强度问题。
- 新增真实项目场景或 golden case。
- 版本发布前。

## 五、回归流程

1. 运行 `python3 scripts/validate.py`。
2. 运行 `python3 scripts/test_scenarios.py`。
3. 运行 `python3 scripts/test_standard_change.py`。
4. 运行 `python3 scripts/check_rule_governance.py`，确认规则路径、任务清单和覆盖率。
5. 运行 `python3 scripts/eval_workflows.py`。
6. 按受影响的用例做人工语义验收，重点看证据链、结论强度和缺资料降级。
7. 更新 `CHANGELOG.md`、版本号和 `test-cases/README.md`。
8. 由人工审核人签认后发布。

## 六、质量报告

质量报告使用 `templates/quality-report.md`，至少包括：

- 评估范围、版本、日期、数据来源。
- workflow 覆盖率、数据来源声明率、真实数据用例数、确定性断言数。
- 规则总数、active 规则测试覆盖率、workflow 规则覆盖率和测试用例规则覆盖率。
- CI 七步结果和规则治理检查结果。
- 失败用例、未覆盖项和缺口。
- 人工审核点、结论和签认。

## 七、限制

- LLM 输出具有非确定性；语义质量不能只用字符串匹配判断。
- 公开项目资料往往缺少合同、清单、签证和结算原件；缺失必须标记，不能用模拟内容补齐。
- 真实数据可能含商业秘密和个人信息；入库前必须脱敏或仅保留公开字段。
- 评估脚本只能验证结构和计算，不替代造价专业判断、合同解释或法律意见。
- 指标不是目标本身；不能为了提高覆盖率而编造测试或预期结果。

## 八、规则调用治理

随着 reference、template、测试和历史项目增加，仅靠 SKILL.md 的文字提醒，不能保证每条规则都被调用。v0.12.0 已落地以下控制点：

| 控制点 | 作用 | 落地方式 |
|---|---|---|
| 规则登记 | 每条规则有唯一 ID、来源、适用范围、生效日期、关联 workflow/template/test、审核状态 | `rules/rule-registry.json`、`rules/README.md` |
| 任务清单 | 每个任务记录使用的 workflow、reference、template、规则 ID 和输出成果 | `templates/task-manifest.md`；任务开始时生成，交付时随包保存 |
| Preflight 路由 | 按任务类型选择必须执行的 workflow 和必须检查的规则 | SKILL.md 路由表 + 任务清单 + `hooks/preflight_reminder.py` |
| Postflight 校验 | 检查输出是否有必需章节、证据编号、计算闭合、质检摘要和规则清单 | `scripts/check_rule_governance.py` + 模板契约 |
| Hooks | 在用户提交任务、写文件或结束回复前注入检查或阻断 | `hooks/README.md`、`hooks/settings.example.json` |
| 测试覆盖 | 每条规则至少对应一个测试用例；规则变更触发回归 | `scripts/check_rule_governance.py` + `scripts/eval_workflows.py` |
| 检索/索引 | 历史资料增长后，不全量加载，按任务检索相关 reference | 规则字段、任务类型路由和规则 ID 反查 |
| 人工 gate | 高风险规则、标准适用、交付签认必须人工确认 | 二次审核、企业级交付、签认记录 |

原则：

- 不要让 SKILL.md 无限变长；它只做路由和原则，细节放在带 ID 的规则文件。
- 关键规则要有机器可检查的产物，不能只写在说明里。
- 规则变更要有影响矩阵、测试和版本记录；旧规则要标记废止。
- 规则覆盖率、数据来源、标准新鲜度和交付签认应进入质量报告。

v0.12.0 的验收标准：规则登记路径有效；active 规则测试覆盖率、workflow 覆盖率和测试用例覆盖率均为 100%；任务清单模板包含必需章节；规则治理检查由 CI 的评估步骤执行。

## 九、关联文件

- `scripts/validate.py`
- `scripts/test_scenarios.py`
- `scripts/check_rule_governance.py`
- `scripts/eval_workflows.py`
- `rules/rule-registry.json`
- `rules/README.md`
- `templates/task-manifest.md`
- `templates/quality-report.md`
- `test-cases/README.md`
- `test-cases/fixtures/suzhou-metro-viii-ts-08/scenario.json`
