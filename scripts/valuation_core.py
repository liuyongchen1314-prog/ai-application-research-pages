#!/usr/bin/env python3
"""Single-source valuation engine (model/release V7.9).

Price/volume never changes fair value.  New financial reports and point-in-time
consensus may change earnings anchors.  V7.9 also validates enterprise-value,
book-value, free-cash-flow and sum-of-the-parts bridges.  A numeric research
range can exist with low confidence, but it is never presented as formally
closed until its evidence gate is complete.
"""
from __future__ import annotations

import copy
import calendar
import datetime as dt
import json
import math
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "valuation_model.json"
LATEST = ROOT / "docs" / "public_v7" / "data" / "latest-v7.json"
RELEASE = "V7.9"


def finite(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def parse_date(value: Any, fallback: dt.date | None = None) -> dt.date:
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return fallback or dt.date.today()


def quote_date(value: Any, fallback: dt.date) -> str:
    """Normalize ISO, YYYYMMDDHHMMSS and slash-separated quote timestamps."""
    raw = str(value or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) >= 8:
        try:
            parsed = dt.date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
            return parsed.isoformat()
        except ValueError:
            pass
    return parse_date(raw, fallback).isoformat()


def fmt_number(value: float) -> str:
    if abs(value) >= 100:
        return str(int(round(value)))
    if abs(value) >= 10:
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{value:.2f}".rstrip("0").rstrip(".")


def fmt_range(low: float, high: float) -> str:
    return f"{fmt_number(low)}–{fmt_number(high)}"


def lerp(a: float, b: float, ratio: float) -> float:
    return a + (b - a) * clamp(ratio, 0.0, 1.0)


def pair(record: dict[str, Any], key: str) -> tuple[float, float] | None:
    value = record.get(key)
    if not isinstance(value, list) or len(value) < 2:
        return None
    low, high = finite(value[0]), finite(value[1])
    return (low, high) if low is not None and high is not None else None


def annual_eps_from_consensus(consensus: dict[str, Any]) -> dict[int, float]:
    result: dict[int, float] = {}
    for index in (1, 2, 3):
        year = finite(consensus.get(f"year{index}"))
        eps = finite(consensus.get(f"eps{index}"))
        if year is not None and eps is not None and eps > 0:
            result[int(year)] = eps
    return result


def ntm_eps(on_date: dt.date, forecasts: dict[int, float]) -> float | None:
    current = forecasts.get(on_date.year)
    following = forecasts.get(on_date.year + 1)
    if current is None or following is None:
        return None
    year_start = dt.date(on_date.year, 1, 1)
    next_start = dt.date(on_date.year + 1, 1, 1)
    elapsed = clamp((on_date - year_start).days / max(1, (next_start - year_start).days), 0.0, 1.0)
    return current * (1.0 - elapsed) + following * elapsed


def pe_at(record: dict[str, Any], months: float) -> tuple[float, float] | None:
    p0 = pair(record, "pe_base_current") or pair(record, "pe_current")
    p6 = pair(record, "pe_base_six") or pair(record, "pe_six") or p0
    p12 = pair(record, "pe_base_twelve") or pair(record, "pe_twelve") or p6
    if p0 is None or p6 is None or p12 is None:
        return None
    total = finite((record.get("dynamic_pe_breakdown") or {}).get("total"))
    multiplier = clamp(1.0 + (total or 0.0), 0.88, 1.08)
    if months <= 6:
        ratio = months / 6.0
        raw = (lerp(p0[0], p6[0], ratio), lerp(p0[1], p6[1], ratio))
    else:
        ratio = (months - 6.0) / 6.0
        raw = (lerp(p6[0], p12[0], ratio), lerp(p6[1], p12[1], ratio))
    return raw[0] * multiplier, raw[1] * multiplier


def effective_pe_multiplier(record: dict[str, Any]) -> float:
    total = finite((record.get("dynamic_pe_breakdown") or {}).get("total"))
    return clamp(1.0 + (total or 0.0), 0.88, 1.08)


def scenario_range(record: dict[str, Any], months: float) -> tuple[float, float]:
    p0 = (finite(record.get("current_low")), finite(record.get("current_high")))
    p6 = (finite(record.get("six_low")), finite(record.get("six_high")))
    p12 = (finite(record.get("twelve_low")), finite(record.get("twelve_high")))
    if None in p0:
        raise ValueError(f"{record.get('code')} missing current scenario range")
    p6 = p6 if None not in p6 else p0
    p12 = p12 if None not in p12 else p6
    if months <= 6:
        ratio = months / 6.0
        return lerp(p0[0], p6[0], ratio), lerp(p0[1], p6[1], ratio)
    ratio = (months - 6.0) / 6.0
    return lerp(p6[0], p12[0], ratio), lerp(p6[1], p12[1], ratio)


def ordered(low: float, high: float, code: str) -> tuple[float, float]:
    if low <= 0 or high <= 0 or low >= high:
        raise ValueError(f"{code} invalid valuation range: {low}, {high}")
    return low, high


def explicit_current(record: dict[str, Any]) -> tuple[float, float]:
    low = finite(record.get("current_low"))
    high = finite(record.get("current_high"))
    if low is None or high is None:
        raise ValueError(f"{record.get('code')} missing numeric research range")
    return ordered(low, high, str(record.get("code")))


def ev_per_share(record: dict[str, Any]) -> tuple[float, float] | None:
    """Close EV -> equity -> per-share with all required bridge inputs."""
    bridge = record.get("ev_bridge") if isinstance(record.get("ev_bridge"), dict) else {}
    metric = finite(bridge.get("metric_value"))
    multiple = pair(bridge, "multiple")
    cash = finite(bridge.get("cash"))
    debt = finite(bridge.get("debt"))
    minority = finite(bridge.get("minority_interest"))
    shares = finite(bridge.get("diluted_shares"))
    currency = str(bridge.get("currency") or "").strip()
    if None in (metric, multiple, cash, debt, minority, shares) or not currency or shares <= 0:
        return None
    low_ev, high_ev = metric * multiple[0], metric * multiple[1]
    low = (low_ev + cash - debt - minority) / shares
    high = (high_ev + cash - debt - minority) / shares
    return ordered(low, high, str(record.get("code")))


def pb_per_share(record: dict[str, Any]) -> tuple[float, float] | None:
    inputs = record.get("pb_inputs") if isinstance(record.get("pb_inputs"), dict) else {}
    bvps = finite(inputs.get("book_value_per_share"))
    multiple = pair(inputs, "multiple")
    if bvps is None or multiple is None or bvps <= 0:
        return None
    return ordered(bvps * multiple[0], bvps * multiple[1], str(record.get("code")))


def fcf_per_share(record: dict[str, Any]) -> tuple[float, float] | None:
    inputs = record.get("fcf_inputs") if isinstance(record.get("fcf_inputs"), dict) else {}
    fcfps = finite(inputs.get("fcf_per_share"))
    multiple = pair(inputs, "multiple")
    if fcfps is None or multiple is None or fcfps <= 0:
        return None
    return ordered(fcfps * multiple[0], fcfps * multiple[1], str(record.get("code")))


def sotp_per_share(record: dict[str, Any]) -> tuple[float, float] | None:
    inputs = record.get("sotp_inputs") if isinstance(record.get("sotp_inputs"), dict) else {}
    segments = inputs.get("segments") if isinstance(inputs.get("segments"), list) else []
    shares = finite(inputs.get("diluted_shares"))
    if not segments or shares is None or shares <= 0:
        return None
    lows, highs = [], []
    for segment in segments:
        low = finite(segment.get("equity_value_low"))
        high = finite(segment.get("equity_value_high"))
        if low is None or high is None:
            return None
        lows.append(low)
        highs.append(high)
    return ordered(sum(lows) / shares, sum(highs) / shares, str(record.get("code")))


def model_kind(record: dict[str, Any]) -> str:
    name = str(record.get("primary_model") or "").upper()
    if "EV/" in name or "企业价值" in name:
        return "enterprise_value"
    if "PB" in name or "市净率" in name:
        return "price_to_book"
    if "SOTP" in name or "分部" in name:
        return "sum_of_parts"
    if "FCF" in name or "现金流" in name:
        return "free_cash_flow"
    if "PE" in name or "EPS" in name or "市盈率" in name:
        return "earnings_multiple"
    return "explicit_research_range"


def evidence_ready(record: dict[str, Any]) -> bool:
    return bool(record.get("formal_closed")) and record.get("evidence_state") == "正式闭环"


def forward_scenario_status(
    record: dict[str, Any], forecasts: dict[int, float]
) -> tuple[str, str]:
    """Decide whether a six-month value scenario is fit for public display."""
    if evidence_ready(record) and bool(record.get("forward_ranges_formal")):
        return "formal", "正式证据与前瞻模型均已闭环"
    research_ready = all(
        (
            record.get("evidence_state") in ("部分闭环", "条件成立"),
            model_kind(record) == "earnings_multiple",
            forecasts.get(2026) is not None,
            forecasts.get(2027) is not None,
            pair(record, "pe_base_current") is not None,
            pair(record, "pe_base_six") is not None,
            record.get("revision_gate") == "通过",
            record.get("realization_gate") == "通过",
            not record.get("missing_inputs"),
        )
    )
    if research_ready:
        return "research", "盈利预测、PE与财报兑现门已通过；仅作六个月研究情景"
    return "unavailable", "前瞻盈利或模型证据未闭环，暂不公开数值"


def current_model_range(
    record: dict[str, Any], forecasts: dict[int, float], as_of: dt.date
) -> tuple[tuple[float, float], str]:
    """Return current fair range and the exact calculation route used."""
    kind = model_kind(record)
    if not evidence_ready(record):
        return explicit_current(record), "low_confidence_numeric_research_range"
    if kind == "earnings_multiple":
        eps = ntm_eps(as_of, forecasts)
        pe = pe_at(record, 0.0)
        if eps is not None and pe is not None:
            return ordered(eps * pe[0], eps * pe[1], str(record.get("code"))), "ntm_eps_x_pe"
    elif kind == "enterprise_value":
        result = ev_per_share(record)
        if result:
            return result, "ev_to_equity_to_per_share"
    elif kind == "price_to_book":
        result = pb_per_share(record)
        if result:
            return result, "book_value_per_share_x_pb"
    elif kind == "sum_of_parts":
        result = sotp_per_share(record)
        if result:
            return result, "sum_of_parts_to_per_share"
    elif kind == "free_cash_flow":
        result = fcf_per_share(record)
        if result:
            return result, "fcf_per_share_x_multiple"
    raise ValueError(f"{record.get('code')} formal model inputs do not close")


def months_between(start: dt.date, target: dt.date) -> float:
    return max(0.0, (target - start).days / 30.4375)


def add_calendar_months(value: dt.date, months: int) -> dt.date:
    index = value.year * 12 + (value.month - 1) + months
    year, month_index = divmod(index, 12)
    month = month_index + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return dt.date(year, month, day)


def classify(price: float | None, low: float, high: float, buy_low: float) -> tuple[str, str]:
    if price is None:
        return "无法判断", "观察"
    if price < buy_low:
        return "明显低估", "通过"
    if price < low:
        return "合理偏低", "通过"
    if price <= high:
        return "合理区间", "通过"
    if price <= high * 1.15:
        return "偏高观察", "观察"
    return "明显偏高", "不通过"


def institutional_check(record: dict[str, Any], consensus: dict[str, Any], twelve: tuple[float, float]) -> dict[str, Any] | None:
    old = record.get("institution_check") if isinstance(record.get("institution_check"), dict) else {}
    target_min = finite(consensus.get("target_min")) or finite(old.get("low"))
    target_max = finite(consensus.get("target_max")) or finite(old.get("high"))
    if target_min is None or target_max is None or target_min <= 0 or target_max <= 0:
        return None
    lo, hi = sorted((target_min, target_max))
    overlap = not (twelve[1] < lo or twelve[0] > hi)
    model_mid = sum(twelve) / 2
    target_mid = (lo + hi) / 2
    return {
        "range": fmt_range(lo, hi),
        "low": lo,
        "high": hi,
        "comparison_horizon": "未来12个月",
        "overlap": overlap,
        "gap_ratio": abs(model_mid / target_mid - 1.0) if target_mid else None,
        "analyst_count": int(finite(consensus.get("analyst_count")) or finite(old.get("analyst_count")) or 0),
        "source": consensus.get("source") or old.get("source") or "公开机构目标带",
        "forecast_date": consensus.get("forecast_date") or old.get("forecast_date"),
        "role": "仅交叉验证，不反推合理价",
    }


def rebuild_record(record: dict[str, Any], financial: dict[str, Any], quote: dict[str, Any], as_of: dt.date) -> dict[str, Any]:
    out = copy.deepcopy(record)
    for trading_field in ("action_level", "action_reason", "action_trigger", "action_model"):
        out.pop(trading_field, None)
    for legacy_field in ("model_kind_v71", "model_kind_v72", "model_kind_v73"):
        out.pop(legacy_field, None)
    out.pop("legacy_ranges", None)
    out["model_kind_frozen"] = out.pop("model_kind", None) or "sector_specific"
    consensus = financial.get("consensus") if isinstance(financial.get("consensus"), dict) else {}
    latest_report = financial.get("latest_report") if isinstance(financial.get("latest_report"), dict) else {}
    forecasts = {year: eps for year, eps in ((2026, finite(record.get("eps_2026"))), (2027, finite(record.get("eps_2027"))), (2028, finite(record.get("eps_2028")))) if eps is not None and eps > 0}
    forecasts.update(annual_eps_from_consensus(consensus))
    year_end = dt.date(as_of.year, 12, 31)
    next_february = dt.date(as_of.year + 1, 2, calendar.monthrange(as_of.year + 1, 2)[1])
    targets = {
        "current": as_of,
        "year_end": year_end,
        "next_year_start": next_february,
        "twelve": add_calendar_months(as_of, 12),
    }
    calculated: dict[str, tuple[float, float]] = {}
    current, calculation_route = current_model_range(record, forecasts, as_of)
    calculated["current"] = current
    pe_capable = (
        evidence_ready(record)
        and model_kind(record) == "earnings_multiple"
        and pair(record, "pe_base_current") is not None
        and ntm_eps(as_of, forecasts) is not None
    )
    for label, target in targets.items():
        if label == "current":
            continue
        months = months_between(as_of, target)
        if pe_capable:
            eps_anchor = ntm_eps(target, forecasts)
            pe_range = pe_at(record, months)
            if eps_anchor is None or pe_range is None:
                calculated[label] = scenario_range(record, months)
            else:
                calculated[label] = (eps_anchor * pe_range[0], eps_anchor * pe_range[1])
                out[f"ntm_{label}"] = eps_anchor
                out[f"pe_{label}"] = list(pe_range)
        else:
            try:
                calculated[label] = scenario_range(record, months)
            except ValueError:
                calculated[label] = current
    # Preserve the explicit six-month view as a useful operational horizon.
    six_month_date = add_calendar_months(as_of, 6)
    six_months = months_between(as_of, six_month_date)
    if pe_capable:
        six_eps, six_pe = ntm_eps(six_month_date, forecasts), pe_at(record, six_months)
        six = (six_eps * six_pe[0], six_eps * six_pe[1]) if six_eps is not None and six_pe else scenario_range(record, six_months)
    else:
        try:
            six = scenario_range(record, six_months)
        except ValueError:
            six = current
    public_forward_status, public_forward_reason = forward_scenario_status(record, forecasts)
    public_forward_range = fmt_range(*six) if public_forward_status != "unavailable" else None
    buy_low, buy_high = current[0] * 0.85, current[0]
    price = finite(quote.get("price")) or finite(record.get("price_as_of"))
    status, gate = classify(price, current[0], current[1], buy_low)
    for year in (2026, 2027, 2028):
        out[f"eps_{year}"] = forecasts.get(year)
    out.update({
        "version": RELEASE,
        "valuation_as_of": as_of.isoformat(),
        "price_as_of": price,
        "price_date": quote_date(quote.get("timestamp") or quote.get("date"), as_of),
        "current_low": current[0], "current_high": current[1], "current": fmt_range(*current),
        "six_low": six[0], "six_high": six[1], "six": fmt_range(*six),
        "forward_public_horizon_months": 6,
        "forward_scenario_status": public_forward_status,
        "forward_scenario": public_forward_range,
        "forward_scenario_date": six_month_date.isoformat(),
        "forward_scenario_note": public_forward_reason,
        "twelve_public": False,
        "year_end_low": calculated["year_end"][0], "year_end_high": calculated["year_end"][1], "year_end": fmt_range(*calculated["year_end"]),
        "year_end_date": targets["year_end"].isoformat(),
        "next_year_start_low": calculated["next_year_start"][0], "next_year_start_high": calculated["next_year_start"][1], "next_year_start": fmt_range(*calculated["next_year_start"]),
        "next_year_start_date": targets["next_year_start"].isoformat(),
        "twelve_low": calculated["twelve"][0], "twelve_high": calculated["twelve"][1], "twelve": fmt_range(*calculated["twelve"]),
        "twelve_date": targets["twelve"].isoformat(),
        "buy_low": buy_low, "buy_high": buy_high, "buy_zone": fmt_range(buy_low, buy_high),
        "status": status, "valuation_judgement": status, "valuation_gate": gate, "decision_gate": gate,
        "blocked": False,
        "formal_closed": evidence_ready(record),
        "evidence_state": record.get("evidence_state") or "证据较弱",
        "audit_stage": record.get("audit_stage") or "P0缺口待补",
        "confidence": record.get("confidence") or "D",
        "confidence_display": record.get("confidence_display") or "低",
        "calculation_route": calculation_route,
        "model_kind": model_kind(record),
        "revaluation_status": "formal_formula_recalculated" if evidence_ready(record) else "numeric_research_range_retained",
        "revaluation_reason": "正式证据与模型输入闭环后重算" if evidence_ready(record) else "保留数值研究区间，同时明确证据等级；不继承V7.6正式结论",
        "latest_report_date": latest_report.get("report_date"),
        "model_source": "唯一生产配置 config/valuation_model.json（V7.9全量重建）",
        "dynamic_pe_multiplier": effective_pe_multiplier(record) if pe_capable else None,
        "primary_model": record.get("primary_model"),
        "cross_check_model": record.get("cross_check_model"),
        "required_inputs": record.get("required_inputs"),
        "model_fit_test": record.get("fit_test"),
        "model_audit_status": record.get("model_audit_status") or record.get("mapping_audit") or "通过",
        "valuation_basis": "正式模型复算" if evidence_ready(record) else "低置信度数值研究区间",
        "price_feedback_policy": "价格、回撤、趋势和量价只触发复核，不反推合理价",
    })
    out["institution_check"] = institutional_check(out, consensus, calculated["twelve"])
    data_inputs = dict(out.get("data_inputs") or {})
    data_inputs.update({
        "report_date": latest_report.get("report_date") or data_inputs.get("report_date"),
        "revenue": finite(latest_report.get("revenue")) if latest_report else data_inputs.get("revenue"),
        "revenue_yoy": finite(latest_report.get("revenue_yoy")) if latest_report else data_inputs.get("revenue_yoy"),
        "net_profit": finite(latest_report.get("net_profit")) if latest_report else data_inputs.get("net_profit"),
        "net_profit_yoy": finite(latest_report.get("net_profit_yoy")) if latest_report else data_inputs.get("net_profit_yoy"),
        "deduct_net_profit": finite(latest_report.get("deduct_net_profit")) if latest_report else data_inputs.get("deduct_net_profit"),
        "deduct_net_profit_yoy": finite(latest_report.get("deduct_net_profit_yoy")) if latest_report else data_inputs.get("deduct_net_profit_yoy"),
        "gross_margin": finite(latest_report.get("gross_margin")) if latest_report else data_inputs.get("gross_margin"),
        "ocf_per_share": finite(latest_report.get("ocf_per_share")) if latest_report else data_inputs.get("ocf_per_share"),
        "consensus_2026_eps": forecasts.get(2026),
        "consensus_2027_eps": forecasts.get(2027),
        "consensus_2028_eps": forecasts.get(2028),
        "analyst_count": int(finite(consensus.get("analyst_count")) or 0),
        "target_min": finite(consensus.get("target_min")),
        "target_max": finite(consensus.get("target_max")),
    })
    out["data_inputs"] = data_inputs
    return out


def rebuild(data: dict[str, Any], config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    quotes = data.get("quotes") if isinstance(data.get("quotes"), dict) else {}
    financials = data.get("company_financials") if isinstance(data.get("company_financials"), dict) else {}
    as_of = parse_date(data.get("snapshot_date") or data.get("embedded_snapshot") or config.get("valuation_date"))
    result: dict[str, dict[str, Any]] = {}
    for record in config.get("records") or []:
        code = str(record["code"])
        result[code] = rebuild_record(record, financials.get(code) or {}, quotes.get(code) or {}, as_of)
    return result


def load_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    config = json.loads(CONFIG.read_text("utf-8"))
    if not LATEST.exists():
        raise FileNotFoundError(f"missing public snapshot: {LATEST}")
    data = json.loads(LATEST.read_text("utf-8"))
    return data, config
