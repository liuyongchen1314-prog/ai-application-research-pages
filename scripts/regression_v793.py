#!/usr/bin/env python3
"""Release regression for V7.9.3 formal data, live markets and UI contracts."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "docs" / "public_v7"
LATEST = PUBLIC / "data" / "latest-v7.json"
LIVE = PUBLIC / "data" / "live-markets.json"
HTML = PUBLIC / "index.html"
INDEX = PUBLIC / "index.json"
WORKFLOW = ROOT / ".github" / "workflows" / "v7-unified-refresh.yml"


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
        zone = (action.get("first_buy_zone_low"), action.get("first_buy_zone_high"))
        if zone == (0, 0):
            fail(f"{code}: null buy zone was converted to 0-0")
    fund = data.get("fund_flow_summary") or {}
    actual_current = sum(str((row or {}).get("last_date") or "") == str(data.get("snapshot_date")) for row in (data.get("fund_flows") or {}).values())
    if int(fund.get("coverage_current") or 0) != actual_current:
        fail("fund-flow summary counts stale cache as current")

    live = json.loads(LIVE.read_text("utf-8"))
    if live.get("schema") != "v793-live-markets-1" or live.get("release") != "V7.9.3":
        fail("live-market schema or release is wrong")
    if live.get("separate_from_valuation") is not True or live.get("market_count") != 4:
        fail("live markets are not isolated from valuation or do not cover four markets")
    for group in ("china", "hk", "us", "korea"):
        rows = ((live.get("markets") or {}).get(group) or {}).get("items") or []
        if not rows or any(not isinstance(row.get("price"), (int, float)) or not isinstance(row.get("change_pct"), (int, float)) for row in rows):
            fail(f"{group}: live market rows are incomplete")

    workflow = WORKFLOW.read_text("utf-8")
    schedules = re.findall(r"^\s*- cron:", workflow, flags=re.MULTILINE)
    if len(schedules) < 8 or "options: [all, live, us, asia, fundamental, final]" not in workflow:
        fail("workflow does not provide at least eight scheduled runs and a live manual mode")
    if "python scripts/update_live_markets.py" not in workflow:
        fail("workflow does not run the isolated live-market updater")

    html = HTML.read_text("utf-8")
    required = (
        "AI研究系统 V7.9.3",
        "data-strategy-action",
        "当前不买｜等待突破",
        "手动刷新全部数据",
        "工作日后台8个时点自动运行",
        "v793-market-grid",
        "data-live-market",
        "当前 / 前瞻合理区间",
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
        "release": "V7.9.3",
        "companies": 142,
        "scheduled_runs": len(schedules),
        "live_markets": 4,
        "market_dates": data.get("market_freshness"),
        "action_counts": (data.get("strategy_meta") or {}).get("action_counts"),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
