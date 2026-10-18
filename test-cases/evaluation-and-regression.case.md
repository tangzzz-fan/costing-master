# 测试用例：评估与回归

## 数据来源

真实公开项目框架 + 现有测试用例；苏州地铁公开来源见 `test-cases/suzhou-metro-station.case.md`，评估脚本读取现有用例和 `scenario.json`。

## 场景

运行以下三步：

```bash
python3 scripts/validate.py
python3 scripts/test_scenarios.py
python3 scripts/eval_workflows.py
```

并检查 `templates/quality-report.md` 的质量报告结构。

## 期望行为

- `validate.py` 通过，markdown 结构、路径、表格、workflow 覆盖和数据来源声明全部正常。
- `test_scenarios.py` 通过，苏州地铁进度款、材料调差、结算差异和问题分类断言正常。
- `eval_workflows.py` 输出质量报告，至少包含版本、日期、workflow 覆盖率 100%、测试用例登记率 100%、数据来源声明率 100%、scenario JSON 数量、CI 三步结果和缺口。
- 质量报告使用 `templates/quality-report.md` 的结构，区分真实公开、真实公开+模拟、模拟/教学数据。
- 报告中明确说明证据分级、结论强度等语义检查仍需人工审核，不能声称已自动完成。
- 没有编造指标、覆盖或通过结果；失败项如实列出。

## 失败表现

- workflow 覆盖率、测试用例登记率或数据来源声明率低于 100%。
- 评估脚本隐藏失败步骤或输出编造的通过结果。
- 质量报告缺少版本、日期、数据来源、失败项或人工审核点。
- 把所有用例都标成“真实数据”，或把模拟数据冒充真实项目数据。
- 声称语义质量、证据分级或结论强度已由 CI 自动验证。
