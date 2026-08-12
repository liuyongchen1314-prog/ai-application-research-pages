#!/usr/bin/env python3
"""Cross-layer release regression for V7.9.2.

This intentionally tests the failures that static file-existence checks missed:
quote/session dates, company cards, valuation status, strategy reference prices,
stale V7.6 prose, action filters and release HTML generation.
"""
from __future__ import annotations

import hashlib
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "docs" / "public_v7"
LATEST = PUBLIC / "data" / "latest-v7.json"
HTML = PUBLIC / "index.html"
INDEX = PUBLIC / "index.json"


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    data = json.loads(LATEST.read_text("utf-8"))
    companies = [
        *((data.get("companies") or {}).get("hardware") or []),
        *((data.get("companies") or {}).get("application") or []),
    ]
    quotes = data.get("quotes") or {}
    valuation = data.get("valuation_current") or {}
    strategy = data.get("strategy_current") or {}
    codes = {row.get("code") for row in companies}
    if (len(companies), len(codes)) != (142, 142):
        fail("company pool is not 142 unique records")
    if set(quotes) != codes or set(valuation) != codes or set(strategy) != codes:
        fail("quote/valuation/strategy pool differs from the company pool")
    if data.get("snapshot_date") != data.get("embedded_snapshot"):
        fail("embedded snapshot still points to an old date")
    for company in companies:
        code = company["code"]
        quote, value, action = quotes[code], valuation[code], strategy[code]
        expected = data["market_freshness"]["hk" if code.endswith(".HK") else "china"]["date"]
        if quote.get("session_complete") is not True or quote.get("date") != expected:
            fail(f"{code}: quote is not the completed market session")
        if company.get("price") != quote.get("price") or company.get("price_date") != quote.get("date"):
            fail(f"{code}: card differs from quote")
        if company.get("valuation_status") != value.get("status"):
            fail(f"{code}: card differs from valuation status")
        if action.get("reference_price") != quote.get("price") or action.get("reference_price_date") != quote.get("date"):
            fail(f"{code}: strategy reference differs from quote")
        visible = json.dumps({"one_liner": company.get("one_liner"), "details": company.get("details"), "signal": company.get("signal")}, ensure_ascii=False)
        if any(token in visible for token in ("V7.6当前合理区间", "估值日2026-08-07", "等待当前估值模型更新")):
            fail(f"{code}: stale generated valuation copy remains")
    fund = data.get("fund_flow_summary") or {}
    actual_current = sum(str((row or {}).get("last_date") or "") == str(data.get("snapshot_date")) for row in (data.get("fund_flows") or {}).values())
    if int(fund.get("coverage_current") or 0) != actual_current:
        fail("fund-flow summary counts stale cache as current")
    html = HTML.read_text("utf-8")
    required = (
        "AI研究系统 V7.9.2",
        "data-strategy-action",
        "当前不买｜等待突破",
        "检查完成，当前已是最新",
        "当前 / 前瞻合理区间",
        "A股 ${v74MarketDate",
    )
    missing = [token for token in required if token not in html]
    if missing:
        fail(f"release HTML missing required UI: {missing}")
    if any(token in html for token in ("__V79_CSS__", "__V79_SNAPSHOT_JSON__", "__V79_APP_JS__", "__V7_BUILD_TIME__")):
        fail("release HTML contains an unresolved build token")
    index = json.loads(INDEX.read_text("utf-8"))
    if index.get("snapshot_sha256") != hashlib.sha256(LATEST.read_bytes()).hexdigest():
        fail("public index hash differs from the latest snapshot")
    print(json.dumps({
        "status": "PASS",
        "release": "V7.9.2",
        "companies": 142,
        "market_dates": data.get("market_freshness"),
        "action_counts": (data.get("strategy_meta") or {}).get("action_counts"),
        "fund_flow_current": fund.get("coverage_current"),
        "fund_flow_cache": fund.get("coverage_total_cache"),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
