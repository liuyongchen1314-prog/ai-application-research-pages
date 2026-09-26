#!/usr/bin/env python3
"""DEPRECATED V7.6-era all-in-one generator.

V7.9.4 deliberately disables this entrypoint because it independently fetched
quotes, classified trend/action, and rendered a second webpage. Keeping it
executable would violate the single-source architecture.
"""
raise SystemExit(
    "已停用：scripts/更新研究系统.py 是旧版重复引擎。"
    "请使用 v7_guard.py + rebuild_valuation.py + rebuild_strategy.py + build_public_site.py。"
)
