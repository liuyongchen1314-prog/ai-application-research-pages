#!/usr/bin/env python3
"""Audit real source coverage without promoting legacy labels to formal closure."""
from __future__ import annotations

import datetime as dt
import json
import pathlib

from snapshot_io import save_snapshot

ROOT = pathlib.Path(__file__).resolve().parents[1]
LATEST = ROOT / "docs/public_v7/data/latest-v7.json"
OUTPUT = ROOT / "docs/public_v7/data/evidence-audit-v79.json"


def contains_source(value, needle: str) -> bool:
    return needle in json.dumps(value, ensure_ascii=False)


def main() -> None:
    data = json.loads(LATEST.read_text("utf-8"))
    valuations = data.get("valuation_current") or {}
    financials = data.get("company_financials") or {}
    announcements = data.get("announcements") or {}
    rows = []
    for code, valuation in sorted(valuations.items()):
        financial = financials.get(code) or {}
        notices = announcements.get(code) or []
        official = bool((financial.get("latest_report") or {}).get("report_date")) and any(bool(x.get("url")) for x in notices if isinstance(x, dict))
        eastmoney = contains_source(financial, "东方财富") or contains_source(valuation.get("eps_source"), "东方财富")
        ths = contains_source(financial, "同花顺") or contains_source(valuation.get("evidence_sources"), "同花顺已核")
        broker = contains_source(valuation.get("revision_metrics"), "研报") and bool((valuation.get("revision_metrics") or {}).get("as_of"))
        bridge = valuation.get("model_kind") != "enterprise_value" or all(valuation.get(k) is not None for k in ("cash", "debt", "diluted_shares"))
        horizon = bool((valuation.get("institution_check") or {}).get("comparison_horizon"))
        dates_distinct = valuation.get("report_date") != valuation.get("capture_date") or not valuation.get("report_date")
        formal = all((official, eastmoney, ths, broker, bridge, horizon, dates_distinct))
        rows.append({
            "code": code,
            "name": valuation.get("name"),
            "scope": valuation.get("scope"),
            "official_disclosure": official,
            "eastmoney": eastmoney,
            "tonghuashun": ths,
            "broker_research": broker,
            "ev_equity_share_bridge": bridge,
            "currency_horizon_checked": horizon,
            "report_capture_dates_distinct": dates_distinct,
            "formal_close_eligible": formal,
            "current_range": valuation.get("current"),
            "evidence_state": valuation.get("evidence_state"),
        })
    summary = {
        "schema": "v79-evidence-audit-1",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "companies": len(rows),
        "coverage": {key: sum(bool(row[key]) for row in rows) for key in ("official_disclosure", "eastmoney", "tonghuashun", "broker_research", "ev_equity_share_bridge", "currency_horizon_checked", "report_capture_dates_distinct", "formal_close_eligible")},
        "policy": "只有公告/财报、东方财富、同花顺、券商研报及模型桥接与币种期限均可核验时，才允许正式闭环；旧65家标签不自动升级。",
        "rows": rows,
    }
    OUTPUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), "utf-8")
    data["valuation_evidence_audit"] = {"latest": OUTPUT.name, "companies": len(rows), "coverage": summary["coverage"], "formal_close_eligible": summary["coverage"]["formal_close_eligible"]}
    save_snapshot(data)
    print(json.dumps({"status": "PASS", **data["valuation_evidence_audit"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
