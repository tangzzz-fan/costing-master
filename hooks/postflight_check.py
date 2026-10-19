#!/usr/bin/env python3
"""Print a non-blocking delivery reminder after a task finishes."""

from __future__ import annotations

from pathlib import Path


def main() -> int:
    summary = Path("质检摘要.md")
    if summary.exists():
        print(
            "交付提醒：已发现质检摘要.md；确认 task-manifest、证据索引、"
            "规则 ID 和人工签认记录齐全。"
        )
    else:
        print(
            "交付提醒：未发现质检摘要.md；涉及金额、审核意见或报价的成果"
            "只能作为草稿，不得标记为可交付签章。"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
