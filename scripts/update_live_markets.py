#!/usr/bin/env python3
"""Build the four-market display feed with exchange-calendar freshness metadata.

V7.9.4 contract:
- this file is display-only and is never an input to valuation/strategy;
- sample time and file-generation time are distinct;
- market phase comes from the exchange calendar, not from a guessed weekday;
- a successful HTTP request is not the same thing as a fresh quote;
- fallback completed-session data is allowed, but is explicitly stale while a market is open.
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

from market_clock import assess, phase

ROOT = pathlib.Path(__file__).resolve().parents[1]
LATEST = ROOT / "docs" / "public_v7" / "data" / "latest-v7.json"
OUTPUT = ROOT / "docs" / "public_v7" / "data" / "live-markets.json"
RELEASE = "V7.9.4"
SCHEMA = "v794-live-markets-2"
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
LOCAL_TZ = {
    "china": ZoneInfo("Asia/Shanghai"),
    "hk": ZoneInfo("Asia/Hong_Kong"),
    "us": ZoneInfo("America/New_York"),
    "korea": ZoneInfo("Asia/Seoul"),
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


def tencent_stamp_iso(stamp: object, group: str) -> str | None:
    raw = "".join(ch for ch in str(stamp or "") if ch.isdigit())
    if len(raw) < 14:
        return None
    try:
        return dt.datetime.strptime(raw[:14], "%Y%m%d%H%M%S").replace(tzinfo=LOCAL_TZ[group]).isoformat()
    except ValueError:
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
        sample_at = tencent_stamp_iso(stamp, group)
        rows.append({
            "symbol": symbol,
            "name": names[symbol],
            "price": price,
            "previous_close": previous,
            "change_pct": price / previous - 1 if previous else None,
            "date": normalize_date(stamp),
            "sample_at": sample_at,
            "as_of": sample_at or normalize_date(stamp),
            "source": "腾讯即时行情",
            "quote_type": "交易所即时行情",
            "realtime": True,
        })
    if len(rows) != len(wanted):
        raise RuntimeError(f"{group}即时行情覆盖{len(rows)}/{len(wanted)}")
    return rows


def yahoo_item(symbol: str, name: str) -> dict:
    encoded = urllib.parse.quote(symbol, safe="")
    payload = json.loads(request(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=5d&interval=5m&includePrePost=true"
    ))
    chart = ((payload.get("chart") or {}).get("result") or [None])[0]
    if not chart:
        raise RuntimeError(str((payload.get("chart") or {}).get("error") or "Yahoo无数据"))
    meta = chart.get("meta") or {}
    price = meta.get("regularMarketPrice")
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
        "sample_at": as_of.isoformat() if as_of else None,
        "as_of": as_of.isoformat() if as_of else None,
        "source": "Yahoo Finance 5分钟行情",
        "quote_type": "海外即时行情",
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
        "sample_at": None,
        "as_of": str(current[0]) + " 收盘",
        "source": "正式收盘快照",
        "quote_type": "正式收盘",
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
                "sample_at": None,
                "as_of": str(item.get("date") or "") + " 收盘",
                "source": "正式收盘快照",
                "quote_type": "正式收盘",
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
        if not old or row.get("date") != old.get("date") or old.get("change_pct") is None:
            continue
        if abs(float(row["change_pct"]) - float(old["change_pct"])) > 0.005:
            raise RuntimeError(f"{row.get('symbol')}即时涨跌与同日正式收盘偏离超过0.5个百分点")


def market_payload(group: str, rows: list[dict], generated_at: dt.datetime) -> dict:
    checks = []
    for row in rows:
        check = assess(
            group,
            sample_at=row.get("sample_at"),
            sample_date=row.get("date"),
            realtime=bool(row.get("realtime")),
            file_generated_at=generated_at,
            now=generated_at,
        )
        row["freshness"] = check
        checks.append(check)
    clock = phase(group, generated_at)
    stale_checks = [x for x in checks if x.get("stale")]
    sample_ages = [x.get("sample_age_minutes") for x in checks if isinstance(x.get("sample_age_minutes"), (int, float))]
    realtime = bool(rows) and all(bool(row.get("realtime")) for row in rows)
    sources = sorted({str(row.get("source") or "未知") for row in rows})
    quote_types = sorted({str(row.get("quote_type") or "未知") for row in rows})
    return {
        "status": "realtime" if realtime else "completed_session_fallback",
        "phase": clock["phase"],
        "exchange_timezone": clock["local_timezone"],
        "exchange_local_time": clock["local_now"],
        "beijing_time": clock["beijing_now"],
        "session_open_local": clock["session_open_local"],
        "session_close_local": clock["session_close_local"],
        "expected_completed_session": clock["expected_completed_session"],
        "source": " / ".join(sources),
        "quote_type": " / ".join(quote_types),
        "fresh": not stale_checks,
        "stale": bool(stale_checks),
        "freshness_reason": "；".join(dict.fromkeys(x.get("reason") for x in stale_checks if x.get("reason"))) if stale_checks else "新鲜度符合当前市场阶段",
        "data_age_minutes": round(max(sample_ages), 1) if sample_ages else None,
        "sample_at": max((row.get("sample_at") for row in rows if row.get("sample_at")), default=None),
        "sample_date": max((row.get("date") for row in rows if row.get("date")), default=None),
        "file_generated_at": generated_at.isoformat(),
        "file_generated_at_beijing": generated_at.astimezone(ZoneInfo("Asia/Shanghai")).isoformat(),
        "items": rows,
    }


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
                if valid_rows(rows):
                    markets[group] = rows
            except Exception as exc:  # keep the completed-session fallback, but freshness will expose staleness
                errors[group] = repr(exc)
        for group, definitions in YAHOO.items():
            rows = []
            for symbol, name in definitions:
                try:
                    rows.append(yahoo_item(symbol, name))
                except Exception as exc:
                    errors[f"{group}:{symbol}"] = repr(exc)
            validate_same_session(rows, markets[group])
            if len(rows) == len(definitions) and valid_rows(rows):
                markets[group] = rows
    missing = [group for group, rows in markets.items() if not valid_rows(rows)]
    if missing:
        raise SystemExit("四市场轻量面板缺失：" + ",".join(missing))

    now = dt.datetime.now(dt.timezone.utc)
    market_data = {group: market_payload(group, rows, now) for group, rows in markets.items()}
    stale_open = [group for group, value in market_data.items() if value.get("phase") == "盘中" and value.get("stale")]
    payload = {
        "schema": SCHEMA,
        "release": RELEASE,
        "generated_at": now.isoformat(),
        "generated_at_beijing": now.astimezone(ZoneInfo("Asia/Shanghai")).isoformat(),
        "workflow_scheduled_cron": os.getenv("WORKFLOW_SCHEDULE") or None,
        "workflow_run_started_at": os.getenv("WORKFLOW_RUN_STARTED_AT") or None,
        "formal_snapshot_date": latest.get("snapshot_date"),
        "strategy_snapshot_date": (latest.get("strategy_meta") or {}).get("snapshot_date"),
        "separate_from_valuation": True,
        "separate_intraday_price_from_close_strategy": True,
        "market_count": 4,
        "stale_open_markets": stale_open,
        "markets": market_data,
        "errors": errors,
    }
    atomic_write(OUTPUT, json.dumps(payload, ensure_ascii=False, indent=2))
    print(json.dumps({
        "status": "PASS_WITH_STALE_WARNING" if stale_open else "PASS",
        "release": RELEASE,
        "market_count": 4,
        "stale_open_markets": stale_open,
        "sources": {group: value["status"] for group, value in market_data.items()},
        "errors": len(errors),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
