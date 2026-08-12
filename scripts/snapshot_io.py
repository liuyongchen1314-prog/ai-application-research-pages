#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import re
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
LATEST = ROOT / "docs" / "public_v7" / "data" / "latest-v7.json"
RELEASE = "V7.9.3"


def _finite(value: object) -> float | None:
    try:
        number = float(value)
        return number if number == number and abs(number) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _classify(price: object, current: dict) -> tuple[str, str]:
    p, low, high = _finite(price), _finite(current.get("current_low")), _finite(current.get("current_high"))
    buy_low = _finite(current.get("buy_low"))
    if p is None or low is None or high is None or low <= 0 or low >= high:
        return "无法判断", "观察"
    buy_low = buy_low if buy_low is not None else low * 0.85
    if p < buy_low:
        return "明显低估", "通过"
    if p < low:
        return "合理偏低", "通过"
    if p <= high:
        return "合理区间", "通过"
    if p <= high * 1.15:
        return "偏高观察", "观察"
    return "明显偏高", "不通过"


def _rewrite_generated_copy(company: dict, current: dict, action: dict) -> None:
    """Remove stale generated V7.6 price/action prose without touching research facts."""
    core = re.split(r"；最新价|；当前行动：|；当前操作为", str(company.get("one_liner") or ""), maxsplit=1)[0].rstrip("。；")
    if core:
        company["one_liner"] = (
            f"{core}；最新价{company.get('price', '—')}，{RELEASE}当前合理区间{current.get('current', '待核验')}，"
            f"估值状态为“{current.get('status', '待核验')}”；当前行动为“{action.get('action', '等待突破')}”。"
        )
    forward_status = current.get("forward_scenario_status")
    if forward_status in ("formal", "research") and current.get("forward_scenario"):
        forward_text = (
            f"六个月研究情景{current['forward_scenario']}（截至{current.get('forward_scenario_date') or '待更新'}）"
        )
    else:
        forward_text = "六个月情景暂不估算"
    valuation_text = (
        f"估值日{current.get('valuation_as_of') or current.get('price_date') or '待更新'}。"
        f"当前研究区间{current.get('current') or '待核验'}；{forward_text}。"
        f"证据状态：{current.get('evidence_state') or '待复核'}。"
        "六个月情景是盈利与估值假设下的合理价值测算，不是股价预测；未来12个月目标已取消公开展示。"
    )
    for detail in company.get("details") or []:
        title = str(detail.get("title") or detail.get("chapter") or "")
        if "估值与时间跨度" in title or "估值模型" in title:
            if "body" in detail:
                detail["body"] = valuation_text
            else:
                detail["content"] = valuation_text
        if "出现哪些信号才考虑买入" in title and isinstance(detail.get("items"), list):
            detail["items"] = [
                f"当前行动：{action.get('action') or '等待突破'}。{action.get('reason') or '等待趋势、估值和风险条件共同确认'}；"
                f"第一买入区：{_strategy_zone(action)}。"
            ]
            if "content" in detail:
                detail["content"] = valuation_text
    signal = company.get("signal") if isinstance(company.get("signal"), dict) else {}
    for key in ("positive", "risk", "neutral", "failed"):
        rows = signal.get(key)
        if isinstance(rows, list):
            signal[key] = [x for x in rows if "等待当前估值模型更新" not in str(x) and "V7.6当前合理区间" not in str(x)]


def _strategy_zone(action: dict) -> str:
    low, high = _finite(action.get("first_buy_zone_low")), _finite(action.get("first_buy_zone_high"))
    if low is not None and high is not None:
        return f"{low:.2f}–{high:.2f}"
    label = action.get("action")
    return {
        "等待突破": "当前不买，等待突破",
        "持有": "持仓管理，不新增",
        "减仓": "减仓管理，不新增",
        "回避/退出": "不设买入区",
        "暂不参与": "不设买入区",
    }.get(label, "尚未形成买点")


def _normalize_fund_flow_summary(data: dict) -> None:
    flows = data.get("fund_flows") or {}
    snapshot = str(data.get("snapshot_date") or "")
    dates = [str(row.get("last_date") or "") for row in flows.values() if isinstance(row, dict)]
    current = sum(value == snapshot for value in dates)
    latest = max((value for value in dates if value), default=None)
    total = sum(1 for row in ((data.get("companies") or {}).get("hardware") or []) + ((data.get("companies") or {}).get("application") or []) if not str(row.get("code") or "").endswith(".HK"))
    history5 = sum(len((row or {}).get("daily") or []) >= 5 for row in flows.values() if isinstance(row, dict))
    data["fund_flow_summary"] = {
        "coverage_current": current,
        "coverage_total_cache": len(flows),
        "history_5d": history5,
        "total_a_share": total,
        "status": "正常" if total and current >= int(total * .9) else "部分可用" if total and current >= int(total * .5) else "数据不足",
        "current_session": snapshot,
        "cache_latest_date": latest,
        "source": "东方财富/腾讯公开订单规模资金流",
        "note": "仅把与当前交易日一致的数据计入当前覆盖；旧日期只作为历史缓存。大单/小单不是投资者真实身份。",
    }


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
                quote["date"] = quote_date
                company["price_date"] = quote_date
            current = valuation.get(code) or {}
            if current:
                company["current"] = current.get("current") or company.get("current")
                company["year_end"] = current.get("year_end") or company.get("year_end")
                company["next_year_start"] = current.get("next_year_start") or company.get("next_year_start")
                company["twelve"] = current.get("twelve_month") or current.get("twelve") or company.get("twelve")
                current["price_as_of"] = company.get("price")
                current["price_date"] = company.get("price_date")
                status, gate = _classify(company.get("price"), current)
                current["status"] = status
                current["valuation_judgement"] = status
                current["valuation_gate"] = gate
                current["decision_gate"] = gate
                company["valuation_status"] = status
            action = strategy.get(code) or {}
            if action:
                company["action"] = action.get("action") or company.get("action")
            if current and action:
                _rewrite_generated_copy(company, current, action)


def save_snapshot(data: dict) -> None:
    """Write the only runtime snapshot. Pretty, mirror and full-history copies are forbidden."""
    synchronize_runtime_views(data)
    data["embedded_snapshot"] = data.get("snapshot_date") or data.get("embedded_snapshot")
    _normalize_fund_flow_summary(data)
    data["version"] = RELEASE
    data["frontend_release"] = RELEASE
    if isinstance(data.get("refresh_summary"), dict):
        data["refresh_summary"]["version"] = RELEASE
    data.setdefault("public_data", {})["unified_market_urls"] = [
        "https://liuyongchen1314-prog.github.io/ai-application-research-pages/data/latest-v7.json",
        "https://liuyongchen1314-prog.github.io/ai-application-research-pages/mirror/latest-v7.json",
    ]
    data["public_data"]["repository"] = "liuyongchen1314-prog/ai-application-research-pages"
    data["public_data"]["schedule_cn"] = "美股06:50；A股/港股/韩国16:35；财报估值18:10；公告审计22:10"
    atomic_write(LATEST, json.dumps(data, ensure_ascii=False, separators=(",", ":")))
