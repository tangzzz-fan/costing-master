# 规则调用治理验收用例

## 数据来源

真实公开项目框架：苏州轨道交通 VIII-TS-08 标段（公开招标/项目框架资料，见 `test-cases/fixtures/suzhou-metro-viii-ts-08/`）。
规则登记来源：本仓库现行 `rules/rule-registry.json`、`rules/README.md`、`templates/task-manifest.md` 和 `scripts/check_rule_governance.py`。
项目成本细节为模拟数字，仅用于验证任务清单和规则调用流程；缺少的合同、清单、签证和结算原件仍标记为缺失，不虚构。

## 输入资料

- 项目基本信息：苏州轨道交通 VIII-TS-08 标段，江苏苏州，地铁车站/区间土建。
- 用户任务：对该项目结算资料做一次初步审核，输出需补资料清单、规则调用清单和交付状态。
- 可用资料：公开项目框架、现有测试证据、规则登记和任务清单模板。
- 缺失资料：施工合同及补充协议、已标价工程量清单、完整结算书、变更签证原件、材料信息价期别、现场影像。

## 期望行为

1. 在执行审核前读取 `rules/README.md`，按任务类型选择规则，并复制 `templates/task-manifest.md` 建立任务清单。
2. 任务清单至少登记以下规则 ID，并说明触发原因：
   - R-001 缺资料先列清单
   - R-002 证据可追溯
   - R-004 判断等级和结论强度
   - R-005 2024 版费用和增值税口径
   - R-007 变更签证和索赔证据链
   - R-009 标准和地方规则新鲜度
   - R-013 地区优先级与跨地区隔离
3. 任务清单记录对应 workflow、reference、template、证据编号、资料缺失项和人工确认点。
4. 输出把缺失资料放入《需补资料清单》，只给初步风险提示和复核路径，不给确定审减金额或签章结论。
5. 交付状态只能是“草稿”或“工作底稿”；不得写成“已签认”或由 AI 签认。
6. 运行 `python3 scripts/check_rule_governance.py`，返回 `OK`，且规则测试覆盖率、workflow 覆盖率和测试用例覆盖率均为 100%。
7. 运行 `python3 scripts/eval_workflows.py`，质量报告的规则治理检查为 `PASS`，缺口为 `None`。

## 失败表现

- 输出没有任务清单，或任务清单没有规则 ID、workflow、证据编号和人工 gate。
- 引用了未登记的规则 ID，或规则登记路径不存在。
- 关键规则没有测试用例；workflow 或测试用例未被任何 active 规则覆盖。
- 缺少合同、清单、签证或信息价时仍给出确定审减金额、确定费率或“可交付签章”结论。
- 把 AI 写成审核人、签认人或盖章人。
- `scripts/check_rule_governance.py` 返回非零，或覆盖率低于 100%。
- 用修改预期结果、删除测试或编造规则的方式让覆盖率通过。

## 验收命令

```bash
python3 scripts/check_rule_governance.py
python3 scripts/validate.py
python3 scripts/eval_workflows.py
```
