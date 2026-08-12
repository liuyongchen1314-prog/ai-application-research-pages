#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[3]
BACKEND = ROOT / "_后台与版本维护资料_请勿删除"
ENGINE = BACKEND / "05_V7每日更新程序"
FRONTEND = ENGINE / "frontend"
HTML = ROOT / "02_开始AI研究系统.html"
SNAPSHOT = ENGINE / "docs" / "public_v7" / "data" / "latest-v7.json"
PUBLIC = ENGINE / "docs" / "public_v7"
INTRADAY = PUBLIC / "data" / "intraday"
REFRESH_LOG = PUBLIC / "data" / "refresh-log.json"
LIVE_MARKETS = PUBLIC / "data" / "live-markets.json"
INDEX = PUBLIC / "index.json"
REBUILD = BACKEND / "10_V7.9全量重建"
CONTRACT = REBUILD / "01_不可破坏业务契约" / "V7_9_不可破坏业务契约.json"
AUDIT = REBUILD / "02_全量重建审计" / "V7_9_估值审计摘要.json"
TEMPLATE = FRONTEND / "V7_9_页面模板.html"
APP = FRONTEND / "V7_9_统一前端.js"
STYLE = FRONTEND / "V7_9_统一样式.css"
BEIJING = ZoneInfo("Asia/Shanghai")


def read_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def atomic_text(path: pathlib.Path, value: str) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(value, "utf-8")
    temp.replace(path)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalize_beijing(value: str | None) -> str | None:
    if not value:
        return value
    parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BEIJING)
    else:
        parsed = parsed.astimezone(BEIJING)
    return parsed.isoformat()


def validate_contract(data: dict, contract: dict) -> None:
    valuation = data.get("valuation_current") or {}
    companies = [
        *(data.get("companies", {}).get("hardware") or []),
        *(data.get("companies", {}).get("application") or []),
    ]
    expected = contract["universe"]
    actual = {
        "total": len(companies),
        "hardware": sum(row.get("scope") == "hardware" for row in companies),
        "application": sum(row.get("scope") == "application" for row in companies),
    }
    if actual != expected:
        raise SystemExit(f"冻结公司范围变化: {actual} != {expected}")
    company_codes = {row.get("code") for row in companies}
    strategy = data.get("strategy_current") or {}
    if set(valuation) != company_codes:
        raise SystemExit("估值对象未覆盖唯一142家公司池")
    if set(strategy) != company_codes:
        raise SystemExit("操作策略未覆盖唯一142家公司池")
    forbidden = set(contract["valuation_contract"]["trading_fields_forbidden"])
    for code, record in valuation.items():
        low, high = record.get("current_low"), record.get("current_high")
        if not all(isinstance(v, (int, float)) and v > 0 for v in (low, high)) or low >= high:
            raise SystemExit(f"{code} 缺少有效数值合理估值范围")
        leaked = forbidden & set(record)
        if leaked:
            raise SystemExit(f"{code} 估值对象混入交易字段: {sorted(leaked)}")
        if record.get("formal_closed") and record.get("evidence_state") != "正式闭环":
            raise SystemExit(f"{code} 正式闭环标记缺少对应证据状态")
    allowed = set(contract["strategy_contract"]["allowed_actions"])
    for code, record in strategy.items():
        if record.get("action") not in allowed:
            raise SystemExit(f"{code} 操作行动不在契约允许范围")


def main() -> None:
    data = read_json(SNAPSHOT)
    contract = read_json(CONTRACT)
    data["version"] = "V7.9.3"
    data["frontend_release"] = "V7.9.3"
    data["generated_at_cn"] = normalize_beijing(data.get("generated_at_cn"))
    refresh = data.setdefault("refresh_summary", {})
    refresh["version"] = "V7.9.3"
    for row in [refresh.get("last_success"), *(refresh.get("recent_runs") or [])]:
        if isinstance(row, dict):
            row["finished_at_beijing"] = normalize_beijing(
                row.get("finished_at_utc") or row.get("finished_at_beijing")
            )

    intraday_codes = sorted(path.stem.replace("_", ".", 1) for path in INTRADAY.glob("*.json"))
    data.setdefault("coverage", {})["intraday"] = len(intraday_codes)
    data["intraday"] = {
        "schema": "v7-intraday-manifest-1",
        "base": "data/intraday/",
        "success": len(intraday_codes),
        "total": 142,
        "available_codes": intraday_codes,
        "status": "complete" if len(intraday_codes) == 142 else "partial",
    }
    validate_contract(data, contract)

    compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    atomic_text(SNAPSHOT, compact)
    snapshot_hash = sha256_bytes(compact.encode("utf-8"))
    index = {
        "schema": "v7-public-index-3",
        "data_schema": "v7-public-market-1",
        "release": "V7.9.3",
        "latest": "data/latest-v7.json",
        "live_markets": "data/live-markets.json",
        "live_markets_sha256": sha256_bytes(LIVE_MARKETS.read_bytes()) if LIVE_MARKETS.exists() else None,
        "snapshot_sha256": snapshot_hash,
        "snapshot_date": data.get("snapshot_date"),
        "generated_at_cn": data.get("generated_at_cn"),
        "coverage": data.get("coverage"),
        "intraday": data.get("intraday"),
        "market_freshness": data.get("market_freshness"),
        "privacy": "仅公开市场与基础信息",
    }
    atomic_text(INDEX, json.dumps(index, ensure_ascii=False, indent=2))

    if REFRESH_LOG.exists():
        log = read_json(REFRESH_LOG)
        log["version"] = "V7.9.3"
        for row in log.get("runs") or []:
            row["finished_at_beijing"] = normalize_beijing(
                row.get("finished_at_utc") or row.get("finished_at_beijing")
            )
        successes = [row for row in log.get("runs") or [] if row.get("status") == "success"]
        log["last_success"] = successes[0] if successes else None
        atomic_text(REFRESH_LOG, json.dumps(log, ensure_ascii=False, indent=2))

    template = TEMPLATE.read_text("utf-8")
    app = APP.read_text("utf-8")
    style = STYLE.read_text("utf-8")
    for token in ("__V79_CSS__", "__V79_SNAPSHOT_JSON__", "__V79_APP_JS__"):
        if template.count(token) != 1:
            raise SystemExit(f"页面模板占位符异常: {token}")
    html = (
        template.replace("__V79_CSS__", style)
        .replace("__V79_SNAPSHOT_JSON__", compact)
        .replace("__V79_APP_JS__", app)
    )
    if any(token in html for token in ("__V79_CSS__", "__V79_SNAPSHOT_JSON__", "__V79_APP_JS__")):
        raise SystemExit("生成HTML仍含未替换占位符")
    atomic_text(HTML, html)
    atomic_text(PUBLIC / "index.html", html)

    model_families = {}
    for record in data["valuation_current"].values():
        family = record.get("model_family")
        model_families[family] = model_families.get(family, 0) + 1
    audit = {
        "schema": "v79-valuation-audit-summary-1",
        "release": "V7.9.3",
        "valuation_model": data.get("valuation_meta", {}).get("version", "V7.9.3"),
        "snapshot_date": data.get("snapshot_date"),
        "companies": len(data["valuation_current"]),
        "model_family_counts": model_families,
        "numeric_ranges": sum(bool(x.get("current_low") and x.get("current_high")) for x in data["valuation_current"].values()),
        "formal_closed": sum(bool(x.get("formal_closed")) for x in data["valuation_current"].values()),
        "evidence_state_counts": {state: sum(x.get("evidence_state") == state for x in data["valuation_current"].values()) for state in sorted({x.get("evidence_state") for x in data["valuation_current"].values()})},
        "action_counts": data.get("strategy_meta", {}).get("action_counts", {}),
        "valuation_strategy_separated": True,
        "snapshot_sha256": snapshot_hash,
        "contract_sha256": sha256_bytes(CONTRACT.read_bytes()),
        "frontend_sha256": sha256_bytes(app.encode("utf-8")),
        "html_sha256": sha256_bytes(html.encode("utf-8")),
        "note": "完整估值只存在于正式快照；本文件仅保存审计计数与哈希，不复制142家公司全量结果。",
    }
    atomic_text(AUDIT, json.dumps(audit, ensure_ascii=False, indent=2))
    print(json.dumps({"status": "PASS", "release": "V7.9.3", "companies": 142, "snapshot_sha256": snapshot_hash, "html_bytes": len(html.encode("utf-8"))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
