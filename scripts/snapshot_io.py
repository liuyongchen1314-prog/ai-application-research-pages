#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import re
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
LATEST = ROOT / "docs" / "public_v7" / "data" / "latest-v7.json"
RELEASE = "V7.9.1"


def atomic_write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def load_snapshot() -> dict:
    return json.loads(LATEST.read_text("utf-8"))


def _date(value: object) -> str | None:
    match = re.search(r"(20\d{2})[-/]?(\d{2})[-/]?(\d{2})", str(value or ""))
    return "-".join(match.groups()) if match else None


def synchronize_runtime_views(data: dict) -> None:
    """Keep embedded cards in sync with the only runtime quote/valuation objects."""
    quotes = data.get("quotes") or {}
    valuation = data.get("valuation_current") or {}
    strategy = data.get("strategy_current") or {}
    for scope in ("hardware", "application"):
        for company in (data.get("companies") or {}).get(scope) or []:
            code = company.get("code")
            quote = quotes.get(code) or {}
            price = quote.get("price", quote.get("close"))
            if isinstance(price, (int, float)):
                company["price"] = price
            change = quote.get("change_pct", quote.get("change"))
            if isinstance(change, (int, float)):
                company["change"] = change
            quote_date = _date(quote.get("timestamp") or quote.get("date"))
            if quote_date:
                company["price_date"] = quote_date
            current = valuation.get(code) or {}
            if current:
                company["current"] = current.get("current") or company.get("current")
                company["year_end"] = current.get("year_end") or company.get("year_end")
                company["next_year_start"] = current.get("next_year_start") or company.get("next_year_start")
                company["twelve"] = current.get("twelve_month") or current.get("twelve") or company.get("twelve")
                current["price_as_of"] = company.get("price")
                current["price_date"] = company.get("price_date")
            action = strategy.get(code) or {}
            if action:
                company["action"] = action.get("action") or company.get("action")


def save_snapshot(data: dict) -> None:
    """Write the only runtime snapshot. Pretty, mirror and full-history copies are forbidden."""
    synchronize_runtime_views(data)
    data["version"] = RELEASE
    data["frontend_release"] = RELEASE
    data.setdefault("public_data", {})["unified_market_urls"] = [
        "https://liuyongchen1314-prog.github.io/ai-application-research-pages/data/latest-v7.json",
        "https://liuyongchen1314-prog.github.io/ai-application-research-pages/mirror/latest-v7.json",
    ]
    data["public_data"]["repository"] = "liuyongchen1314-prog/ai-application-research-pages"
    data["public_data"]["schedule_cn"] = "美股06:50；A股/港股/韩国16:35；财报估值18:10；公告审计22:10"
    atomic_write(LATEST, json.dumps(data, ensure_ascii=False, separators=(",", ":")))
