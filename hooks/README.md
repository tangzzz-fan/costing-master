# Claude Code Hooks 示例

> 本目录提供可选的规则调用提醒 hooks。默认不启用；是否启用由使用者按团队规范决定。
>
> Hooks 只做提醒，不替代 `scripts/check_rule_governance.py`、CI 和人工审核。

## 一、作用

| Hook | 触发时点 | 作用 |
|---|---|---|
| `UserPromptSubmit` | 用户提交任务后 | 提醒先读取规则、建立任务清单 |
| `Stop` | 一轮回复结束前 | 提醒检查质检摘要、证据索引和签认边界 |

## 二、启用方式

把 `hooks/settings.example.json` 中的 `hooks` 配置合并到项目级 `.claude/settings.json`，或在用户级设置中配置。命令中的相对路径以项目根目录为准。

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 hooks/preflight_reminder.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 hooks/postflight_check.py"
          }
        ]
      }
    ]
  }
}
```

配置后先在一个测试项目验证输出，不要直接用于正式交付项目。

## 三、脚本说明

- `hooks/preflight_reminder.py`：输出规则调用提醒，不阻断任务。
- `hooks/postflight_check.py`：检查当前目录是否有 `质检摘要.md`，输出交付提醒，不阻断回复。
- `hooks/settings.example.json`：可直接合并的示例配置。

## 四、边界

- Hooks 不能判断造价结论是否正确，也不能替代二次审核。
- 需要阻断写文件时，应使用 `PreToolUse` 加项目自定义校验，并由团队审核脚本逻辑；本仓库不默认启用阻断。
- 规则登记和覆盖率以 `rules/rule-registry.json` 和 `scripts/check_rule_governance.py` 为准。
- 不要把 hooks 输出当作签认、审批或法律意见。
