#!/usr/bin/env python3
"""Independent V7.9 trading strategy layer.

The strategy consumes fair-value ranges, but can never write them.  Evidence
quality changes position size and stop strictness; it does not mechanically
turn every company into "observe" or "do not participate".
"""
from __future__ import annotations

import math
import statistics
from typing import Any


ACTIONS = ("重点参与", "试仓", "等待突破", "持有", "减仓", "回避/退出", "暂不参与")


def finite(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def sma(values: list[float], period: int, offset: int = 0) -> float | None:
    end = len(values) - offset
    return average(values[end - period : end]) if end >= period else None


def period_return(bars: list[list[Any]], period: int) -> float | None:
    if len(bars) <= period:
        return None
    start, end = finite(bars[-period - 1][2]), finite(bars[-1][2])
    return end / start - 1 if start and end else None


def percentiles(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted((value, key) for key, value in values.items() if math.isfinite(value))
    size = len(ordered)
    return {
        key: 100.0 * (index / (size - 1) if size > 1 else 1.0)
        for index, (_, key) in enumerate(ordered)
    }


def technical(bars: list[list[Any]], relative_strength: float | None) -> dict[str, Any]:
    if len(bars) < 220:
        return {"history": len(bars), "stage": "历史不足", "stage_score": 0, "strict_stage2": False}
    close = [float(row[2]) for row in bars]
    high = [float(row[3]) for row in bars]
    low = [float(row[4]) for row in bars]
    volume = [float(row[5] or 0) for row in bars]
    price = close[-1]
    ma20, ma50, ma150, ma200 = sma(close, 20), sma(close, 50), sma(close, 150), sma(close, 200)
    ma200_old = sma(close, 200, 20)
    window = min(252, len(bars))
    high52, low52 = max(high[-window:]), min(low[-window:])
    checks = [
        price > ma150 and price > ma200,
        ma150 > ma200,
        ma200_old is not None and ma200 > ma200_old,
        ma50 > ma150 and ma50 > ma200,
        price > ma50,
        price >= low52 * 1.30,
        price >= high52 * 0.75,
        (relative_strength or 0) >= 70,
    ]
    score = sum(checks)
    strict = all(checks)
    stage4 = price < ma200 and ma200_old is not None and ma200 < ma200_old
    stage = "第二阶段确认" if strict else "第二阶段候选" if score >= 6 and price > ma200 else "弱势阶段" if stage4 else "整理过渡"

    blocks = []
    for start, end in ((-65, -45), (-45, -25), (-25, -5)):
        median = statistics.median(close[start:end])
        spread = (max(high[start:end]) - min(low[start:end])) / median if median else 99.0
        blocks.append((spread, average(volume[start:end]) or 0.0))
    spreads = [item[0] for item in blocks]
    volumes = [item[1] for item in blocks]
    contracting = spreads[0] > spreads[1] * 1.05 and spreads[1] > spreads[2] * 1.05
    volume_dry = volumes[2] < volumes[0] * 0.85
    pivot = max(high[-21:-1])
    volume20 = average(volume[-21:-1]) or 0.0
    breakout = price > pivot and volume[-1] >= volume20 * 1.25
    near_high = price >= high52 * 0.85
    vcp = "确认突破" if contracting and volume_dry and breakout else "形成中" if contracting and volume_dry and near_high else "候选" if contracting or (spreads[2] < spreads[0] * 0.75 and near_high) else "未形成"
    support = max(min(low[-15:]), (ma50 or price) * 0.97)
    stop = min(price * 0.98, support)
    return {
        "history": len(bars),
        "price": price,
        "ma20": ma20,
        "ma50": ma50,
        "ma150": ma150,
        "ma200": ma200,
        "high52": high52,
        "low52": low52,
        "stage": stage,
        "stage_score": score,
        "strict_stage2": strict,
        "stage4": stage4,
        "vcp": vcp,
        "pivot": pivot,
        "breakout": breakout,
        "stop": stop,
        "volume_ratio": volume[-1] / volume20 if volume20 else None,
        "relative_strength": relative_strength,
        "return_20d": period_return(bars, 20),
    }


def valuation_position(price: float | None, low: float, high: float) -> str:
    if price is None:
        return "无法判断"
    if price < low * 0.85:
        return "明显低估"
    if price < low:
        return "合理偏低"
    if price <= high:
        return "合理区间"
    if price <= high * 1.15:
        return "偏高"
    return "明显偏高"


def strategy_action(
    valuation: dict[str, Any], tech: dict[str, Any], sector_strength: str
) -> tuple[str, str]:
    # 估值位置使用正式发布价；均线、阶段和枢轴仍使用日K收盘计算。
    price = finite(valuation.get("price_as_of")) or finite(tech.get("price"))
    low, high = float(valuation["current_low"]), float(valuation["current_high"])
    position = valuation_position(price, low, high)
    if price is None or tech.get("history", 0) < 220:
        return "暂不参与", "行情或长期趋势历史不足，无法定义可执行止损"
    if tech.get("stage4"):
        return "回避/退出", "长期均线转弱且价格位于200日线下方"
    if position == "明显偏高":
        return "减仓", "价格显著高于合理区间上沿，趋势强也不能抬高内在价值"
    if position == "偏高":
        return ("持有", "已有仓位可按趋势持有，但新仓赔率不足") if tech.get("strict_stage2") else ("减仓", "估值偏贵且趋势未完整确认")
    if tech.get("strict_stage2") and tech.get("breakout") and sector_strength == "强":
        return "重点参与", "估值可接受、第二阶段确认、放量突破且板块强"
    if tech.get("strict_stage2") and tech.get("vcp") in {"形成中", "候选", "确认突破"} and sector_strength != "弱":
        return "试仓", "估值与趋势通过，买点接近；用小仓和结构止损表达不确定性"
    if tech.get("strict_stage2"):
        return "持有", "趋势保持但当前不是低风险新买点；已有仓位继续跟踪"
    if (
        tech.get("stage_score", 0) >= 5
        and (tech.get("relative_strength") or 0) >= 70
        and sector_strength == "强"
        and position in {"明显低估", "合理偏低", "合理区间"}
    ):
        return "试仓", "板块与相对强弱领先、估值可接受；趋势未全过，用小仓和更紧止损参与"
    if tech.get("stage") == "第二阶段候选":
        return "等待突破", "估值可接受但趋势尚差关键条件，等待突破确认而非抄底"
    if position in {"明显低估", "合理偏低", "合理区间"}:
        return "等待突破", "估值有吸引力但趋势未确认，价格便宜不等于立即买入"
    return "回避/退出", "估值与趋势都未形成正向赔率"


def strategy_terms(action: str, valuation: dict[str, Any], tech: dict[str, Any]) -> dict[str, Any]:
    price = finite(valuation.get("price_as_of")) or finite(tech.get("price"))
    pivot = finite(tech.get("pivot"))
    stop = finite(tech.get("stop"))
    low, high = float(valuation["current_low"]), float(valuation["current_high"])
    if action == "重点参与":
        first_zone = [pivot, pivot * 1.03] if pivot else [price * 0.99, price * 1.01]
        initial = "计划仓位的20%–25%"
    elif action == "试仓":
        anchor = max(value for value in (low, finite(tech.get("ma50")) or 0, price * 0.98) if value)
        first_zone = [anchor * 0.99, anchor * 1.02]
        initial = "计划仓位的10%–15%"
    else:
        first_zone = None
        initial = "不新增" if action in {"等待突破", "持有", "回避/退出", "暂不参与"} else "先减计划仓位的1/3"
    entry = average(first_zone) if first_zone else price
    risk = entry - stop if entry and stop and entry > stop else None
    reward = high - entry if entry else None
    rr = reward / risk if risk and reward and reward > 0 else None
    strict_stop = valuat