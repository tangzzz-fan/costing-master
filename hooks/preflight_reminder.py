#!/usr/bin/env python3
"""Print a non-blocking rule-governance reminder before a task starts."""

from __future__ import annotations


def main() -> int:
    print(
        "规则调用提醒：复杂造价任务先读取 rules/README.md，"
        "复制 templates/task-manifest.md，记录规则 ID、workflow、证据和人工 gate。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
