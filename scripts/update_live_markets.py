#!/usr/bin/env python3
"""Build the lightweight four-market live panel without touching valuation prices.

The formal V7 snapshot remains completed-session data.  This file is a separate,
short-lived display feed used by the browser and must never become an input to
valuation or strategy calculations.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import tempfile
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo


ROOT = pathlib.Path(__file__).resolve().parents[1]
LATEST = ROOT / "docs" / "public_v7" / "data" / "latest-v7.json"
OUTPUT = ROOT / "docs" / "public_v7" / "data" / "live-markets.json"
RELEASE = "V7.9.3"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/144 Safari/537.36",
    "Referer": "https://gu.qq.com/",
    "Accept": "application/json,text/plain,*/*",
}
TENCENT = {
    "china": [("sh000001", "上证指数"), ("sz399006", "创业板指"), ("sh000688", "科创50")],
    "hk": [("hkHSI", "恒生指数"), ("hkHSTECH", "恒生科技")],
}
YAHOO = {
    "us": [("^IXIC", "纳斯达克"), ("^SOX", "费城半导体"), ("SMH", "AI芯片ETF")],
    "korea": [("^KS11", "韩国KOSPI"), ("^KQ11", "韩国KOSDAQ"), ("000660.KS", "SK海力士")],
}


def atomic_write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        try:
            os.unlink(temp)
        except FileNotFoundError:
            pass


def request(url: str, *, encoding: str = "utf-8", timeout: int = 18) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode(encoding, errors="replace")


def normalize_date(value: object) -> str | None:
    raw = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(raw) >= 8:
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return None


def tencent_items(group: str) -> list[dict]:
    wanted = TENCENT[group]
    text = request("https://qt.gtimg.cn/q=" + ",".join(symbol for symbol, _ in wanted), encoding="gbk")
    names = dict(wanted)
    rows: list[dict] = []
    for line in text.splitlines():
        if '="' not in line:
            continue
        left, raw = line.split('="', 1)
        symbol = left.replace("v_", "").strip()
        values = raw.rsplit('"', 1)[0].split("~")
        if symbol not in names or len(values) < 6:
            continue
        try:
            price, previous = float(values[3]), float(values[4])
        except (TypeError, ValueError):
            continue
        stamp = values[30] if len(values) > 30 else ""
        rows.append({
            "symbol": symbol,
            "name": names[symbol],
            "price": price,
            "previous_close": previous,
            "change_pct": price / previous - 1 if previous else None,
            "date": normalize_date(stamp),
            "as_of": stamp or normalize_date(stamp),
            "source": "腾讯即时行情",
            "realtime": True,
        })
    if len(rows) != len(wanted):
        raise RuntimeError(f"{group}即时行情覆盖{len(rows)}/{len(wanted)}")
    return rows


def yahoo_item(symbol: str, name: str) -> dict:
    encoded = urllib.parse.quote(symbol, safe="")
    payload = json.loads(request(f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=5d&interval=5m&includePrePost=true"))
    chart = ((payload.get("chart") or {}).get("result") or [None])[0]
    if not chart:
        raise RuntimeError(str((payload.get("chart") or {}).get("error") or "Yahoo无数据"))
    meta = chart.get("meta") or {}
    price = meta.get("regularMarketPrice")
    # `chartPreviousClose` is the beginning of the requested 5-day chart, not
    # yesterday's close.  Using it creates false 5-day moves in the live card.
    previous = meta.get("regularMarketPreviousClose") or meta.get("previousClose") or meta.get("chartPreviousClose")
    stamp = meta.get("regularMarketTime")
    if price is None or previous in (None, 0):
        raise RuntimeError(f"{symbol}缺少即时价或昨收")
    timezone = ZoneInfo(meta.get("exchangeTimezoneName") or "UTC")
    as_of = dt.datetime.fromtimestamp(int(stamp), dt.timezone.utc).astimezone(timezone) if stamp else None
    return {
        "symbol": symbol,
        "name": name,
        "price": float(price),
        "previous_close": float(previous),
        "change_pct": float(price) / float(previous) - 1,
        "date": as_of.date().isoformat() if as_of else None,
        "as_of": as_of.isoformat() if as_of else None,
        "source": "海外即时行情",
        "realtime": True,
    }


def completed_benchmark(latest: dict, key: str, name: str) -> dict | None:
    record = (latest.get("benchmarks") or {}).get(key) or {}
    daily = record.get("daily") or []
    if len(daily) < 2:
        return None
    previous, current = daily[-2], daily[-1]
    close, prior = float(current[2]), float(previous[2])
    return {
        "symbol": record.get("symbol") or key,
        "name": name,
        "price": close,
        "previous_close": prior,
        "change_pct": close / prior - 1 if prior else None,
        "date": str(current[0]),
        "as_of": str(current[0]) + " 收盘",
        "source": "正式收盘快照",
        "realtime": False,
    }


def fallback_markets(latest: dict) -> dict[str, list[dict]]:
    result = {"china": [], "hk": [], "us": [], "korea": []}
    for key, name in (("CSI300", "沪深300"), ("CHINEXT", "创业板指"), ("STAR50", "科创50")):
        if row := completed_benchmark(latest, key, name):
            result["china"].append(row)
    for key, name in (("HSI", "恒生指数"), ("HSTECH", "恒生科技")):
        if row := completed_benchmark(latest, key, name):
            result["hk"].append(row)
    context = latest.get("market_context") or {}
    for group in ("us", "korea"):
        for item in (context.get(group) or {}).get("items") or []:
            result[group].append({
                "symbol": item.get("ticker"),
                "name": item.get("name") or item.get("ticker"),
                "price": item.get("close"),
                "previous_close": None,
                "change_pct": item.get("change_pct"),
                "date": item.get("date"),
                "as_of": str(item.get("date") or "") + " 收盘",
                "source": "正式收盘快照",
                "realtime": False,
            })
    return result


def valid_rows(rows: list[dict]) -> bool:
    return bool(rows) and all(
        isinstance(row.get("price"), (int, float))
        and isinstance(row.get("change_pct"), (int, float))
        and abs(float(row["change_pct"])) < 0.5
        for row in rows
    )


def validate_same_session(rows: list[dict], formal_rows: list[dict]) -> None:
    """Reject a live percentage that disagrees with the same completed session."""
    formal = {row.get("symbol"): row for row in formal_rows}
    for row in rows:
        old = formal.get(row.get("symbol"))
        if not old or row.get("date") != old.get("date"):
            continue
        if abs(float(row["change_pct"]) - float(old["change_pct"])) > 0.005:
            raise RuntimeError(f"{row.get('symbol')}即时涨跌与同日正式收盘偏离超过0.5个百分点")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="只用已验证正式快照生成面板")
    args = parser.parse_args()
    latest = json.loads(LATEST.read_text("utf-8"))
    markets = fallback_markets(latest)
    errors: dict[str, str] = {}
    if not args.offline:
        for group in ("china", "hk"):
            try:
                rows = tencent_items(group)
                validate_same_session(rows, markets[group])
                if valid_rows