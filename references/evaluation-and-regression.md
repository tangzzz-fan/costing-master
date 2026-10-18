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
- CI 通过率：结构校验、业务断言、评估报告三步全部通过。
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
3. 运行 `python3 scripts/eval_workflows.py`。
4. 按受影响的用例做人工语义验收，重点看证据链、结论强度和缺资料降级。
5. 更新 `CHANGELOG.md`、版本号和 `test-cases/README.md`。
6. 由人工审核人签认后发布。

## 六、质量报告

质量报告使用 `templates/quality-report.md`，至少包括：

- 评估范围、版本、日期、数据来源。
- workflow 覆盖率、数据来源声明率、真实数据用例数、确定性断言数。
- CI 三步结果。
- 失败用例、未覆盖项和缺口。
- 人工审核点、结论和签认。

## 七、限制

- LLM 输出具有非确定性；语义质量不能只用字符串匹配判断。
- 公开项目资料往往缺少合同、清单、签证和结算原件；缺失必须标记，不能用模拟内容补齐。
- 真实数据可能含商业秘密和个人信息；入库前必须脱敏或仅保留公开字段。
- 评估脚本只能验证结构和计算，不替代造价专业判断、合同解释或法律意见。
- 指标不是目标本身；不能为了提高覆盖率而编造测试或预期结果。

## 八、关联文件

- `scripts/validate.py`
- `scripts/test_scenarios.py`
- `scripts/eval_workflows.py`
- `templates/quality-report.md`
- `test-cases/README.md`
- `test-cases/fixtures/suzhou-metro-viii-ts-08/scenario.json`
