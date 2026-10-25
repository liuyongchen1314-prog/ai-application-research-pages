#!/usr/bin/env python3
"""V7.9.4 unified trend/strategy/CAN SLIM engine.

Authoritative contract:
- valuation_current is read-only input; trading logic never changes fair value.
- this module is the ONLY source for stage, trend score, buy-point score,
  sector strength, market gate, action and CAN SLIM results.
- frontend may display/sort these fields but must not recalculate them.
"""
from __future__ import annotations

import math
import statistics
from collections import Counter
from typing import Any

RELEASE = "V7.9.4"
ACTIONS = (
    "重点参与", "小仓试错", "临近触发", "突破后确认", "缩量回踩观察",
    "普通候选", "等待趋势修复", "不追/回避", "已持仓继续持有", "已持仓减仓或退出",
)
STAGES = ("第二阶段确认", "第二阶段候选", "第一阶段", "第三阶段", "第四阶段", "数据不足")
ACTION_PRIORITY = {name: i for i, name in enumerate(ACTIONS)}
STAGE_PRIORITY = {name: i for i, name in enumerate(STAGES)}


def finite(value: Any) -> float | None:
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def average(values: list[float]) -> float | None:
    values = [x for x in values if x is not None and math.isfinite(x)]
    return sum(values) / len(values) if values else None


def sma(values: list[float], period: int, offset: int = 0) -> float | None:
    end = len(values) - offset
    return average(values[end-period:end]) if end >= period else None


def period_return(bars: list[list[Any]], period: int, offset: int = 0) -> float | None:
    end = len(bars) - 1 - offset
    start = end - period
    if start < 0 or end < 0:
        return None
    a, b = finite(bars[start][2]), finite(bars[end][2])
    return b / a - 1 if a and b else None


def percentiles(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted((v, k) for k, v in values.items() if v is not None and math.isfinite(v))
    n = len(ordered)
    return {k: 100 * (i / (n - 1) if n > 1 else 1.0) for i, (_, k) in enumerate(ordered)}


def _slope(values: list[float], period: int) -> float | None:
    if len(values) <= period:
        return None
    old = sma(values, period, max(5, period // 10))
    now = sma(values, period)
    return now / old - 1 if old and now else None


def _rolling_pivot(bars: list[list[Any]], end: int, lookback: int = 20) -> float | None:
    start = max(0, end - lookback)
    highs = [finite(row[3]) for row in bars[start:end]]
    highs = [x for x in highs if x is not None]
    return max(highs) if highs else None


def _vcp_state(bars: list[list[Any]], price: float, high52: float) -> dict[str, Any]:
    close = [float(x[2]) for x in bars]
    high = [float(x[3]) for x in bars]
    low = [float(x[4]) for x in bars]
    volume = [float(x[5] or 0) for x in bars]
    if len(bars) < 70:
        return {"state": "数据不足", "contracting": None, "volume_dry": None}
    slices = ((-65, -45), (-45, -25), (-25, -5))
    spreads, vols = [], []
    for a, b in slices:
        med = statistics.median(close[a:b])
        spreads.append((max(high[a:b]) - min(low[a:b])) / med if med else 99.0)
        vols.append(average(volume[a:b]) or 0.0)
    contracting = spreads[0] > spreads[1] * 1.04 and spreads[1] > spreads[2] * 1.04
    dry = vols[2] < vols[0] * 0.85
    near_high = price >= high52 * 0.82
    state = "未形成"
    if contracting and dry and near_high:
        state = "形成中"
    elif contracting or (spreads[2] <= spreads[0] * 0.75 and near_high):
        state = "候选形态"
    return {
        "state": state, "contracting": contracting, "volume_dry": dry,
        "spread_early": spreads[0], "spread_mid": spreads[1], "spread_late": spreads[2],
        "volume_early": vols[0], "volume_late": vols[2],
    }


def _breakout_state(bars: list[list[Any]]) -> dict[str, Any]:
    """Recognise same-day and 2-5 day post-breakout confirmation without hindsight."""
    if len(bars) < 40:
        return {"state": "数据不足", "pivot": None, "days_since": None}
    volume = [float(x[5] or 0) for x in bars]
    candidates = []
    for idx in range(max(21, len(bars)-5), len(bars)):
        pivot = _rolling_pivot(bars, idx, 20)
        if not pivot:
            continue
        close = float(bars[idx][2])
        av20 = average(volume[max(0, idx-20):idx]) or 0
        vr = volume[idx] / av20 if av20 else None
        if close > pivot and vr is not None and vr >= 1.15:
            candidates.append((idx, pivot, vr))
    if candidates:
        idx, pivot, vr = candidates[0]
        after = bars[idx:]
        closes = [float(x[2]) for x in after]
        lows = [float(x[4]) for x in after]
        days = len(bars)-1-idx
        failed = any(x < pivot * 0.97 for x in closes)
        held = not failed and closes[-1] >= pivot * 0.99
        retest = any(lo <= pivot * 1.02 for lo in lows[1:]) and closes[-1] >= pivot if len(after) > 1 else False
        if failed:
            state = "突破失败跌回"
        elif 2 <= days <= 5 and held:
            state = "突破后2-5日站稳" if not retest else "突破后回踩确认"
        elif days <= 1 and held:
            state = "当日突破" if days == 0 else "突破次日站稳"
        else:
            state = "突破后观察"
        return {"state": state, "pivot": pivot, "days_since": days, "volume_ratio": vr,
                "held_above": held, "retest_confirmed": retest, "failed": failed}
    pivot = _rolling_pivot(bars, len(bars), 20)
    price = float(bars[-1][2])
    distance = price / pivot - 1 if pivot else None
    return {"state": "未突破", "pivot": pivot, "days_since": None, "volume_ratio": None,
            "held_above": False, "retest_confirmed": False, "failed": False,
            "distance_to_pivot": distance}


def technical(bars: list[list[Any]], rs12: float | None, rs6: float | None, rs3: float | None) -> dict[str, Any]:
    if len(bars) < 220:
        stage_checks={
            "price_above_150_200":False,"ma150_above_200":False,"ma200_rising":False,
            "ma50_above_150_200":False,"price_above_50":False,"above_52w_low_30pct":False,
            "within_25pct_52w_high":False,"rs12_ge_70":False,
        }
        vcp={"state":"数据不足","contracting":False,"volume_dry":False,"spread_early":None,"spread_mid":None,"spread_late":None,"volume_early":None,"volume_late":None}
        breakout={"state":"数据不足","pivot":None,"days_since":None,"volume_ratio":None,"held_above":False,"retest_confirmed":False,"failed":False,"distance_to_pivot":None}
        return {"history":len(bars),"price":finite(bars[-1][2]) if bars else None,"ma20":None,"ma50":None,"ma150":None,"ma200":None,
                "slope50":None,"slope150":None,"slope200":None,"high52":None,"low52":None,"stage":"数据不足","stage_score":0,
                "stage_checks":stage_checks,"strict_stage2":False,"trend_quality_score":0,"vcp":vcp,"breakout":breakout,"pivot":None,"stop":None,
                "volume_ratio":None,"pullback_dry":False,"relative_strength_12m":rs12,"relative_strength_6m":rs6,"relative_strength_3m":rs3,
                "return_20d":period_return(bars,20) if len(bars)>20 else None,"return_60d":period_return(bars,60) if len(bars)>60 else None,
                "data_completeness":20,"blockers":["长期日线不足220根"]}
    close = [float(x[2]) for x in bars]
    high = [float(x[3]) for x in bars]
    low = [float(x[4]) for x in bars]
    volume = [float(x[5] or 0) for x in bars]
    price = close[-1]
    ma20, ma50, ma150, ma200 = (sma(close, n) for n in (20, 50, 150, 200))
    s50, s150, s200 = (_slope(close, n) for n in (50, 150, 200))
    w = min(252, len(bars)); high52, low52 = max(high[-w:]), min(low[-w:])
    stage2_checks = {
        "price_above_150_200": price > ma150 and price > ma200,
        "ma150_above_200": ma150 > ma200,
        "ma200_rising": (s200 or 0) > 0,
        "ma50_above_150_200": ma50 > ma150 and ma50 > ma200,
        "price_above_50": price > ma50,
        "above_52w_low_30pct": price >= low52 * 1.30,
        "within_25pct_52w_high": price >= high52 * 0.75,
        "rs12_ge_70": (rs12 or 0) >= 70,
    }
    stage_score = sum(stage2_checks.values())
    strict = all(stage2_checks.values())
    # Four-stage classification. Stage 3 = topping/distribution after a mature uptrend;
    # Stage 1 = base/bottom with flat long MA; Stage 4 = falling long-term trend.
    if strict:
        stage = "第二阶段确认"
    elif price < ma200 and (s200 or 0) < -0.005:
        stage = "第四阶段"
    elif price >= ma200 and stage_score >= 5:
        stage = "第二阶段候选"
    elif abs(s200 or 0) <= 0.012 and price <= ma200 * 1.08:
        stage = "第一阶段"
    elif price >= ma200 and ((s50 or 0) < 0 or price < ma50) and price >= high52 * 0.7:
        stage = "第三阶段"
    else:
        stage = "第一阶段" if price <= ma200 * 1.05 else "第三阶段"
    vcp = _vcp_state(bars, price, high52)
    breakout = _breakout_state(bars)
    av20 = average(volume[-21:-1]) or 0
    vol_ratio = volume[-1] / av20 if av20 else None
    pullback_dry = bool(vol_ratio is not None and vol_ratio <= 0.8 and (abs(price/ma20-1) <= 0.04 or abs(price/ma50-1) <= 0.04))
    # Trend quality is descriptive, never capped by a buy blocker.
    tq = 0.0
    tq += stage_score / 8 * 45
    tq += min(15, max(0, ((rs12 or 0)-50) * 0.30))
    tq += min(10, max(0, ((rs6 or 0)-50) * 0.20))
    tq += min(8, max(0, ((rs3 or 0)-50) * 0.16))
    tq += 8 if (s50 or 0) > 0 else 2 if (s50 or 0) > -0.01 else 0
    tq += 7 if price >= high52 * 0.85 else 4 if price >= high52 * 0.75 else 0
    tq += 7 if vcp["state"] in {"形成中", "候选形态"} else 0
    tq = round(min(100, max(0, tq)))
    support = max(min(low[-15:]), (ma50 or price) * 0.97)
    stop = min(price * 0.98, support)
    return {
        "history": len(bars), "price": price, "ma20": ma20, "ma50": ma50,
        "ma150": ma150, "ma200": ma200, "slope50": s50, "slope150": s150, "slope200": s200,
        "high52": high52, "low52": low52, "stage": stage, "stage_score": stage_score,
        "stage_checks": stage2_checks, "strict_stage2": strict, "trend_quality_score": tq,
        "vcp": vcp, "breakout": breakout, "pivot": breakout.get("pivot"), "stop": stop,
        "volume_ratio": vol_ratio, "pullback_dry": pullback_dry,
        "relative_strength_12m": rs12, "relative_strength_6m": rs6, "relative_strength_3m": rs3,
        "return_20d": period_return(bars, 20), "return_60d": period_return(bars, 60),
        "data_completeness": 100, "blockers": [],
    }


def _benchmark_metrics(bars: list[list[Any]]) -> dict[str, Any]:
    if len(bars) < 210:
        return {"score": 0, "hard_veto": True, "state": "数据不足", "distribution_days": None}
    close = [float(x[2]) for x in bars]; volume = [float(x[5] or 0) for x in bars]
    p = close[-1]; m50=sma(close,50); m200=sma(close,200); s200=_slope(close,200)
    d25 = 0
    for i in range(max(1, len(bars)-25), len(bars)):
        ret = close[i]/close[i-1]-1
        if ret <= -0.002 and volume[i] > volume[i-1]: d25 += 1
    score = 0
    score += 30 if p > m50 else 10
    score += 25 if p > m200 else 0
    score += 20 if (s200 or 0) > 0 else 5 if (s200 or 0) > -0.005 else 0
    r20=period_return(bars,20); r60=period_return(bars,60)
    score += 10 if (r20 or -1)>0 else 0; score += 10 if (r60 or -1)>0 else 0
    score += 5 if d25 <= 4 else 2 if d25 <= 6 else 0
    hard = p < m200 and (s200 or 0) < -0.005
    state = "绿" if score >= 70 and not hard else "黄" if score >= 45 and not hard else "红"
    return {"score": score, "hard_veto": hard, "state": state, "distribution_days": d25,
            "return_20d": r20, "return_60d": r60, "price": p, "ma50": m50, "ma200": m200, "slope200": s200}


def market_gates(data: dict[str, Any]) -> dict[str, Any]:
    bench = data.get("benchmarks") or {}
    mapping = {"china": ["CHINEXT", "STAR50", "CSI300"], "hk": ["HSTECH", "HSI"]}
    out = {}
    for group, keys in mapping.items():
        rows = []
        for key in keys:
            bars = ((bench.get(key) or {}).get("daily") or [])
            if bars: rows.append((key, _benchmark_metrics(bars)))
        if not rows:
            out[group] = {"state":"数据不足","score":0,"hard_veto":True,"reason":"宽基历史缺失","components":{}}
            continue
        scores=[x[1]["score"] for x in rows]; hard_count=sum(x[1]["hard_veto"] for x in rows)
        score=round(statistics.median(scores)); hard = hard_count >= max(1, len(rows)//2+1)
        state="绿" if score>=70 and not hard else "黄" if score>=45 and not hard else "红"
        out[group]={"state":state,"score":score,"hard_veto":hard,
                    "reason": "主要指数长期趋势硬性否决" if hard else "主要指数趋势与分配日综合",
                    "components":{k:v for k,v in rows}}
    return out


def _sector_metrics(data: dict[str, Any], technicals: dict[str, dict], metadata: dict[str, dict]) -> dict[str, Any]:
    histories=data.get("histories") or {}; bench=data.get("benchmarks") or {}
    groups: dict[str,list[str]]={}
    for code, meta in metadata.items(): groups.setdefault(f"{meta.get('scope')}|{meta.get('sector')}",[]).append(code)
    result={}
    for key,codes in groups.items():
        vals20=[];vals60=[];ab20=[];ab50=[];vrs=[];leaders=[]
        scope=key.split('|',1)[0]
        bkey='HSTECH' if any(c.endswith('.HK') for c in codes) else ('CHINEXT' if scope in {'hardware','application'} else 'CSI300')
        bb=((bench.get(bkey) or {}).get('daily') or [])
        br20=period_return(bb,20); br60=period_return(bb,60)
        for code in codes:
            bars=((histories.get(code) or {}).get('daily') or []); t=technicals.get(code) or {}
            r20=period_return(bars,20);r60=period_return(bars,60)
            if r20 is not None: vals20.append(r20)
            if r60 is not None: vals60.append(r60)
            if len(bars)>=50:
                closes=[float(x[2]) for x in bars]; ab20.append(closes[-1]>=sma(closes,20));ab50.append(closes[-1]>=sma(closes,50))
                av=average([float(x[5] or 0) for x in bars[-21:-1]]) or 0
                vrs.append(float(bars[-1][5] or 0)/av if av else 1)
            leaders.append((t.get('relative_strength_12m') or 0)>=80 and t.get('stage') in {'第二阶段确认','第二阶段候选'})
        m20=statistics.median(vals20) if vals20 else None;m60=statistics.median(vals60) if vals60 else None
        rel20=m20-br20 if m20 is not None and br20 is not None else None;rel60=m60-br60 if m60 is not None and br60 is not None else None
        breadth20=sum(ab20)/len(ab20) if ab20 else None; breadth50=sum(ab50)/len(ab50) if ab50 else None
        volume_change=(statistics.median(vrs)-1) if vrs else None; leader_ratio=sum(leaders)/len(leaders) if leaders else None
        score=0
        score += 20 if (m20 or -1)>0 else 8 if (m20 or -1)>-0.05 else 0
        score += 15 if (m60 or -1)>0 else 6 if (m60 or -1)>-0.08 else 0
        score += 15 if (rel20 or -1)>0 else 5 if (rel20 or -1)>-0.03 else 0
        score += 15 if (rel60 or -1)>0 else 5 if (rel60 or -1)>-0.05 else 0
        score += 15*(breadth20 or 0); score += 10*(breadth50 or 0); score += 5*min(1,max(0,(volume_change or 0)+0.5)); score += 5*(leader_ratio or 0)
        score=round(min(100,max(0,score)))
        strength='强' if score>=70 else '中' if score>=45 else '弱'
        result[key]={"score":score,"strength":strength,"median_20d":m20,"median_60d":m60,
                     "relative_benchmark_20d":rel20,"relative_benchmark_60d":rel60,
                     "breadth_ma20":breadth20,"breadth_ma50":breadth50,"volume_change":volume_change,
                     "leader_ratio":leader_ratio,"benchmark":bkey,"count":len(codes)}
    return result


def valuation_position(price: float | None, low: float, high: float) -> str:
    if price is None: return "无法判断"
    if price < low*.85: return "明显低估"
    if price < low: return "合理偏低"
    if price <= high: return "合理区间"
    if price <= high*1.15: return "偏高"
    return "明显偏高"


def _ann_risks(data: dict, code: str, meta: dict) -> dict[str, Any]:
    anns=(data.get('announcements') or {}).get(code) or []
    titles='｜'.join(str(x.get('title') or '') for x in anns)
    name=str(meta.get('name') or '')
    st=bool(('ST' in name.upper()) and not name.upper().startswith('BEST'))
    delist=any(k in titles for k in ('退市风险','终止上市'))
    unlock=any(k in titles for k in ('解禁','限售股上市流通'))
    reduction=any(k in titles for k in ('减持','股份减持'))
    refinance=any(k in titles for k in ('定向增发','向特定对象发行','可转债','再融资'))
    board='港股' if code.endswith('.HK') else '科创板' if code.startswith('688') else '创业板' if code.startswith(('300','301')) else '主板'
    limit='无A股涨跌停/T+1约束' if code.endswith('.HK') else ('20%涨跌幅、T+1' if board in {'科创板','创业板'} else '通常10%涨跌幅、T+1')
    return {"board":board,"trading_rule":limit,"st":st,"delist_risk":delist,"unlock_notice":unlock,
            "reduction_notice":reduction,"refinancing_notice":refinance,
            "hard_veto":st or delist,"note":"解禁/减持/再融资仅在取得正式公告后标记；规模未知时不擅自判定大额"}


def _official_new_change(data: dict, code: str, tech: dict, fin: dict) -> dict[str, Any]:
    anns=(data.get('announcements') or {}).get(code) or []
    verified=[]
    for a in anns:
        title=str(a.get('title') or '')
        if str(a.get('source') or '').startswith('交易所') and any(k in title for k in ('新产品','项目中标','签订','合同','订单','投产','扩产','收购','重大资产','业绩预告','业绩快报')):
            verified.append({"date":a.get('date'),"title":title,"source":a.get('source')})
    rep=fin.get('latest_report') or {}; earnings_inflection=(finite(rep.get('net_profit_yoy')) or -999)>=30 and (finite(rep.get('revenue_yoy')) or -999)>=15
    price_confirmation=(tech.get('price') or 0)>=(tech.get('high52') or 1)*0.9
    state='pass' if (verified or earnings_inflection) and price_confirmation else 'partial' if (verified or earnings_inflection) else 'unknown'
    evidence="正式公告/盈利拐点 + 价格确认；公司介绍关键词不作为通过证据"
    if state=='unknown': evidence="未取得可验证的正式公告或盈利拐点证据；公司介绍关键词不作为通过证据"
    return {"state":state,"official_events":verified[:5],"earnings_inflection":earnings_inflection,"price_confirmation":price_confirmation,
            "evidence":evidence}


def _cycle_family(valuation: dict, meta: dict) -> bool:
    text=' '.join(map(str,(valuation.get('model_family'),meta.get('sector'),meta.get('subsector')))).lower()
    return any(k in text for k in ('memory','foundry','cycle','存储','晶圆','半导体设备','设备'))


def _can_item(letter: str, name: str, state: str, evidence: str, counter: str = '') -> dict[str,str]:
    return {"letter":letter,"name":name,"state":state,"evidence":evidence,"counter":counter}


def canslim(data: dict, code: str, meta: dict, valuation: dict, tech: dict, sector: dict, market: dict, rules: dict) -> dict[str,Any]:
    fin=(data.get('company_financials') or {}).get(code) or {}; rep=fin.get('latest_report') or {}
    cycle=_cycle_family(valuation,meta); items=[]
    rev=finite(rep.get('revenue_yoy')); dnp=finite(rep.get('deduct_net_profit_yoy')); np=finite(rep.get('net_profit_yoy'))
    if cycle:
        c_state='pass' if rev is not None and rev>=15 and (tech.get('return_60d') or -1)>0 else 'partial' if rev is not None else 'unknown'
        items.append(_can_item('C','最近季度/周期拐点',c_state,f"周期行业：收入同比{rev if rev is not None else '缺失'}%；结合60日价格/行业相对强弱，不机械要求单季利润高增","库存/价格周期数据未齐全时不判满分"))
    else:
        if dnp is not None and rev is not None: c_state='pass' if dnp>=25 and rev>=15 else 'partial' if dnp>0 and rev>0 else 'fail'
        elif np is not None and rev is not None: c_state='partial' if np>0 and rev>0 else 'fail'
        else: c_state='unknown'
        items.append(_can_item('C','最近季度可比盈利与收入',c_state,f"扣非增速={dnp if dnp is not None else '缺失'}；归母增速={np if np is not None else '缺失'}；收入增速={rev if rev is not None else '缺失'}","扣非缺失时归母只能作替代证据，不能直接判通过"))
    annual=fin.get('annual_history') or []
    if len(annual)>=3:
        profits=[finite(x.get('deduct_net_profit') or x.get('net_profit')) for x in annual[-3:]]; roes=[finite(x.get('roe')) for x in annual[-3:]]
        valid=[x for x in profits if x is not None]
        stable=len(valid)==3 and all(x>0 for x in valid) and valid[2]>=valid[1]>=valid[0]
        a_state='pass' if stable and average([x for x in roes if x is not None] or [0])>=12 else 'partial' if len(valid)==3 else 'unknown'
        a_ev='至少3年年度盈利/ROE历史已取得'
    elif cycle:
        a_state='partial' if rev is not None else 'unknown'; a_ev='周期行业使用跨周期盈利/ROE/产能利用率；当前三年结构化历史未齐全'
    else:
        a_state='unknown'; a_ev='缺少至少3年年度盈利质量、稳定性与ROE结构化历史；禁止用2027E/2026E替代'
    items.append(_can_item('A','至少3年年度质量',a_state,a_ev,'预测年度增长不能冒充历史A项'))
    n=_official_new_change(data,code,tech,fin); items.append(_can_item('N','真实新变化',n['state'],n['evidence'],'关键词本身不得直接通过'))
    flows=(data.get('fund_flows') or {}).get(code) or {}; fd=(flows.get('daily') or [])[-10:]
    flow_score=sum((finite(x.get('main')) or 0) for x in fd); supply_bad=rules['reduction_notice'] or rules['refinancing_notice'] or rules['unlock_notice']
    s_state='pass' if tech.get('volume_ratio') and tech['volume_ratio']>=1.15 and flow_score>0 and not supply_bad else 'partial' if fd or tech.get('volume_ratio') is not None else 'unknown'
    if rules['hard_veto']: s_state='fail'
    s_ev=f"近10日主力流代理={flow_score:.0f}；量比={tech.get('volume_ratio')}; 解禁={rules['unlock_notice']} 减持={rules['reduction_notice']} 再融资={rules['refinancing_notice']}"
    if s_state=='unknown': s_ev='缺少资金流与有效量比数据；'+s_ev
    items.append(_can_item('S','供给/需求/筹码',s_state,s_ev,"未取得真实流通股/限售股规模时不假装完整"))
    rs12=tech.get('relative_strength_12m');ind=tech.get('industry_relative_rank')
    l_state='pass' if (rs12 or 0)>=80 and (ind or 0)>=70 and sector.get('strength')!='弱' else 'partial' if (rs12 or 0)>=60 else 'fail' if rs12 is not None else 'unknown'
    l_ev=f"12月RS={rs12}; 行业内相对排名={ind}; 板块={sector.get('strength')}"
    if l_state=='unknown': l_ev='缺少中长期RS/行业排名数据；'+l_ev
    items.append(_can_item('L','持续领涨',l_state,l_ev,"只看20日RS不足以证明领头羊"))
    inst=(data.get('institutional_holdings') or {}).get(code)
    if isinstance(inst,dict) and inst.get('fund_count') is not None:
        change=finite(inst.get('holding_change_pct')); cnt=finite(inst.get('fund_count')) or 0
        i_state='pass' if cnt>=5 and (change is None or change>=0) else 'partial' if cnt>0 else 'fail'; i_ev=f"优质基金/机构数量={cnt}；持仓变化={change}"
    else:
        i_state='unknown'; i_ev='真实机构持仓/基金数量及变化尚未取得；分析师覆盖不再替代I'
    items.append(_can_item('I','机构持仓',i_state,i_ev,'分析师覆盖数量不是机构持仓'))
    m_state='fail' if market.get('hard_veto') else 'pass' if market.get('score',0)>=70 else 'partial' if market.get('score',0)>=45 else 'fail'
    dist=[v.get('distribution_days') for v in (market.get('components') or {}).values() if v.get('distribution_days') is not None]
    items.append(_can_item('M','市场确认',m_state,f"市场灯={market.get('state')} 分数={market.get('score')}；分配日={dist}","不能用单日涨跌代替市场趋势"))
    known=[x for x in items if x['state']!='unknown']; passes=sum(x['state']=='pass' for x in items); fails=sum(x['state']=='fail' for x in items)
    completeness=round(len(known)/7*100)
    verdict='不通过' if fails>=2 or rules['hard_veto'] else '通过' if passes>=5 and completeness>=85 else '部分通过' if completeness>=45 else '数据不足'
    return {"verdict":verdict,"items":items,"pass_count":passes,"fail_count":fails,"data_completeness":completeness,
            "book_original":"C/A/N/S/L/I/M用于成长、供需、领涨与市场确认，不参与合理估值",
            "a_share_localization":"涨跌停、T+1、ST/退市、解禁、减持、再融资、流通约束和预告/正式报告差异进入风险层",
            "system_supplement":"周期行业使用周期拐点适配；缺失数据明确为未知，不以分析师覆盖或关键词补齐"}


def buy_point(valuation: dict, tech: dict, sector: dict, market: dict, rules: dict) -> dict[str,Any]:
    price=finite(valuation.get('price_as_of')) or finite(tech.get('price')); low=float(valuation['current_low']); high=float(valuation['current_high'])
    pos=valuation_position(price,low,high); pivot=finite(tech.get('pivot')); stop=finite(tech.get('stop'))
    dist=(price/pivot-1) if price and pivot else None; br=(tech.get('breakout') or {}).get('state')
    score=0.0
    score += min(30,(tech.get('trend_quality_score') or 0)*0.30)
    score += 15 if tech.get('vcp',{}).get('state')=='形成中' else 10 if tech.get('vcp',{}).get('state')=='候选形态' else 3
    score += 18 if br in {'突破后2-5日站稳','突破后回踩确认'} else 14 if br in {'当日突破','突破次日站稳'} else 10 if dist is not None and -0.05<=dist<=0.01 else 2
    score += 10 if sector.get('strength')=='强' else 6 if sector.get('strength')=='中' else 1
    score += 8 if pos in {'明显低估','合理偏低','合理区间'} else 0
    score += 7 if not market.get('hard_veto') and market.get('score',0)>=45 else 0
    score += 5 if tech.get('pullback_dry') else 0
    score += 4 if (tech.get('volume_ratio') or 0)>=1.15 else 2 if tech.get('volume_ratio') is not None else 0
    score=round(min(100,max(0,score)))
    blockers=[]
    if tech.get('stage') not in {'第二阶段确认','第二阶段候选'}: blockers.append('趋势未确认')
    if dist is not None and dist < -0.08: blockers.append('价格离枢轴过远')
    if dist is not None and dist > 0.08: blockers.append('价格已远离枢轴，不追')
    if br in {'当日突破','突破次日站稳'} and (tech.get('breakout') or {}).get('volume_ratio',0)<1.15: blockers.append('放量不足')
    if pos in {'偏高','明显偏高'}: blockers.append('估值不可接受')
    if market.get('hard_veto'): blockers.append('市场门禁关闭')
    if rules.get('hard_veto'): blockers.append('A股特别风险硬门禁')
    if tech.get('history',0)<220: blockers.append('技术数据不足')
    entry = pivot if pivot else price
    risk=entry-stop if entry and stop and entry>stop else None; reward=high-entry if entry and high>entry else None
    rr=reward/risk if risk and reward else None
    return {"score":score,"blockers":blockers,"distance_to_pivot":dist,"risk_reward_ratio":rr,
            "position":pos,"pivot":pivot,"stop":stop,
            "note":"分数描述当前位置质量；阻断项单列，不再用49分封顶。未知仅表示数据缺失。"}


def _action(valuation: dict, tech: dict, sector: dict, market: dict, bp: dict, rules: dict, held: bool) -> tuple[str,str]:
    pos=bp['position']; stage=tech.get('stage'); tq=tech.get('trend_quality_score',0); score=bp.get('score',0); rr=bp.get('risk_reward_ratio'); br=(tech.get('breakout') or {}).get('state')
    if held:
        if rules.get('hard_veto') or stage=='第四阶段' or pos=='明显偏高' or (tech.get('breakout') or {}).get('failed'):
            return '已持仓减仓或退出','持仓状态下出现长期趋势/估值/特别风险失效条件'
        return '已持仓继续持有','已有仓位且未触发结构失效；不等于建议新开仓'
    if market.get('hard_veto'):
        return ('等待趋势修复','市场总门禁先于个股买点，等待主要指数长期趋势修复') if stage!='第四阶段' else ('不追/回避','市场门禁与个股第四阶段同时否决')
    if rules.get('hard_veto') or stage=='第四阶段' or pos=='明显偏高':
        return '不追/回避','未持仓标的不使用“减仓”；当前存在长期趋势、特别风险或估值硬否决'
    if pos=='偏高': return '不追/回避','估值偏高，新仓风险收益不合格'
    if br in {'突破后2-5日站稳','突破后回踩确认'} and tq>=72 and sector.get('strength')!='弱' and (rr is None or rr>=1.8):
        return '突破后确认','突破后2-5日站稳/回踩确认，避免只认突破当天'
    if tech.get('strict_stage2') and br in {'当日突破','突破次日站稳'} and tq>=85 and score>=80 and sector.get('strength')=='强' and rr is not None and rr>=2.5 and not bp['blockers']:
        return '重点参与','第二阶段、趋势质量、板块、量价和风险收益同时通过；数量可为0'
    near=bp.get('distance_to_pivot') is not None and -0.05<=bp['distance_to_pivot']<=0.01
    if stage in {'第二阶段确认','第二阶段候选'} and tq>=75 and score>=65 and near and sector.get('strength')!='弱' and rr is not None and rr>=2 and not any(x in bp['blockers'] for x in ('估值不可接受','市场门禁关闭','A股特别风险硬门禁')):
        return '小仓试错','接近事先定义枢轴，个股领先且风险收益合格；仅小仓并使用结构止损'
    if stage in {'第二阶段确认','第二阶段候选'} and near and tq>=60:
        return '临近触发','已接近明确枢轴，但尚需真正突破/量价确认；未触发前不买'
    if stage in {'第二阶段确认','第二阶段候选'} and tech.get('pullback_dry') and tq>=65:
        return '缩量回踩观察','强趋势内回踩均线附近且量能收缩，等待止跌/重新转强'
    if stage in {'第二阶段确认','第二阶段候选'} and tq>=45:
        return '普通候选','公司仍处候选趋势，但当前位置未满足低风险买点'
    return '等待趋势修复','估值可以继续研究，但趋势条件不足；便宜不等于买点'


def _position_terms(action: str, bp: dict) -> dict[str,Any]:
    pivot=bp.get('pivot'); stop=bp.get('stop')
    if action=='重点参与': initial='计划仓位20%–25%'
    elif action=='小仓试错': initial='计划仓位5%–10%'
    else: initial='不新增'
    return {"first_buy_zone_low":pivot*0.995 if pivot and action in {'重点参与','小仓试错'} else None,
            "first_buy_zone_high":pivot*1.03 if pivot and action in {'重点参与','小仓试错'} else None,
            "breakout_level":pivot,"initial_position":initial,
            "add_condition":"仅在首次仓位盈利且放量站稳触发位后再加；亏损仓不摊低成本" if action in {'重点参与','小仓试错'} else '不加仓',
            "reduce_condition":"已持仓才适用：跌破结构止损/趋势转第四阶段/估值明显偏高时减仓或退出",
            "stop_loss":stop,"invalidation":"收盘跌破结构止损且不能快速收回；买入触发未满足则不买" if stop else '无法定义'}


def _rolling_validation(histories: dict[str,Any]) -> dict[str,Any]:
    """Small rolling sanity test for score thresholds; not used to tune thresholds to quota."""
    samples=[]
    for code,item in histories.items():
        bars=(item or {}).get('daily') or []
        if len(bars)<280: continue
        # monthly-ish samples to avoid extreme overlap; simple trend proxy independent of current action count.
        closes=[float(x[2]) for x in bars]
        for i in range(220,len(bars)-20,20):
            m50=average(closes[i-49:i+1]);m150=average(closes[i-149:i+1]);m200=average(closes[i-199:i+1]);
            if not (m50 and m150 and m200): continue
            score=sum([closes[i]>m50,closes[i]>m150,closes[i]>m200,m50>m150>m200])
            if score<3: continue
            fwd=closes[i+20]/closes[i]-1
            adverse=min(float(x[4]) for x in bars[i+1:i+21])/closes[i]-1
            samples.append((str(bars[i][0]),fwd,adverse))
    if not samples:return {"sample_count":0,"win_rate":None,"average_return":None,"max_drawdown":None,"max_adverse_excursion":None,"profit_loss_ratio":None}
    wins=[x[1] for x in samples if x[1]>0];losses=[x[1] for x in samples if x[1]<=0]
    pl=(average(wins) or 0)/abs(average(losses) or 1) if losses else None
    by_date={}
    for day,fwd,_ in samples: by_date.setdefault(day,[]).append(fwd)
    equity=peak=1.0; max_dd=0.0
    for day in sorted(by_date):
        equity*=1+(average(by_date[day]) or 0); peak=max(peak,equity); max_dd=min(max_dd,equity/peak-1)
    return {"sample_count":len(samples),"win_rate":sum(x[1]>0 for x in samples)/len(samples),
            "average_return":average([x[1] for x in samples]),"max_drawdown":max_dd,"max_adverse_excursion":min(x[2] for x in samples),"profit_loss_ratio":pl,
            "method":"滚动20交易日样本；同一采样日等权形成验证组合计算最大回撤；仅验证阈值方向，不得为增加通过数量而反向调参"}


def build(data: dict[str,Any]) -> dict[str,Any]:
    valuations=data.get('valuation_current') or {}; histories=data.get('histories') or {}
    companies=[*((data.get('companies') or {}).get('hardware') or []),*((data.get('companies') or {}).get('application') or [])]
    metadata={x['code']:x for x in companies}
    returns12={};returns6={};returns3={}
    for code,item in histories.items():
        bars=(item or {}).get('daily') or []
        for target,n in ((returns12,252),(returns6,126),(returns3,63)):
            v=period_return(bars,min(n,len(bars)-1)) if len(bars)>n else None
            if v is not None: target[code]=v
    rs12,rs6,rs3=percentiles(returns12),percentiles(returns6),percentiles(returns3)
    techs={code:technical((histories.get(code) or {}).get('daily') or [],rs12.get(code),rs6.get(code),rs3.get(code)) for code in valuations}
    # Industry-relative rank uses 12m returns inside the exact sector.
    sec_groups={}
    for code,meta in metadata.items():sec_groups.setdefault(f"{meta.get('scope')}|{meta.get('sector')}",[]).append(code)
    for _,codes in sec_groups.items():
        local=percentiles({c:returns12[c] for c in codes if c in returns12})
        for c in codes: techs[c]['industry_relative_rank']=local.get(c)
    sectors=_sector_metrics(data,techs,metadata); markets=market_gates(data)
    held_codes=set((data.get('user_positions') or {}).keys())
    result={}
    for code,val in valuations.items():
        meta=metadata.get(code) or {}; tech=techs[code]; sk=f"{meta.get('scope')}|{meta.get('sector')}"; sector=sectors.get(sk) or {'strength':'未知','score':0}
        group='hk' if code.endswith('.HK') else 'china'; market=markets[group]
        rules=_ann_risks(data,code,meta); bp=buy_point(val,tech,sector,market,rules); cs=canslim(data,code,meta,val,tech,sector,market,rules)
        action,reason=_action(val,tech,sector,market,bp,rules,code in held_codes)
        vcp_state=(tech.get('vcp') or {}).get('state'); breakout_state=(tech.get('breakout') or {}).get('state')
        setup_quality={"确认突破":95,"形成中":75,"候选形态":60,"未形成":20,"数据不足":0}.get(vcp_state,20)
        setup_quality=max(setup_quality,{"突破后回踩确认":100,"突破后2-5日站稳":95,"突破次日站稳":90,"当日突破":85,"未突破":20,"突破失败跌回":0}.get(breakout_state,20))
        result[code]={"version":RELEASE,"code":code,"name":val.get('name') or meta.get('name'),"scope":meta.get('scope'),"sector":meta.get('sector'),
            "snapshot_date":data.get('snapshot_date'),"reference_price":finite(val.get('price_as_of')) or finite(tech.get('price')),
            "reference_price_date":val.get('price_date') or data.get('snapshot_date'),"action":action,"action_priority":ACTION_PRIORITY[action],
            "home_label":action,"reason":reason,"valuation_position":bp['position'],"valuation_confidence":val.get('confidence_display'),"evidence_state":val.get('evidence_state'),
            "market_gate":market,"sector_strength":sector.get('strength'),"sector_score":sector.get('score'),"sector_metrics":sector,
            "technical":tech,"trend_stage":tech.get('stage'),"trend_stage_priority":STAGE_PRIORITY.get(tech.get('stage'),99),"trend_quality_score":tech.get('trend_quality_score'),
            "buy_point_score":bp['score'],"setup_quality_score":setup_quality,"company_quality":meta.get('quality'),"data_completeness":round((tech.get('data_completeness',0)*0.65)+(cs.get('data_completeness',0)*0.35)),
            "blockers":bp['blockers'],"risk_reward_ratio":bp.get('risk_reward_ratio'),"distance_to_pivot":bp.get('distance_to_pivot'),"can_slim":cs,"a_share_rules":rules,
            **_position_terms(action,bp)}
    return {"schema":"v794-strategy-2","version":RELEASE,"snapshot_date":data.get('snapshot_date'),"market":markets,"sectors":sectors,"companies":result,
            "sort_contract":["action_priority","trend_stage_priority","trend_quality_score(desc)","RS12m(desc)","RS6m(desc)","RS3m(desc)","industry_relative_rank(desc)","distance_to_pivot(abs asc)","setup_quality_score(desc)","sector_score(desc)","company_quality(desc)","code(asc)"],
            "rolling_validation":_rolling_validation(histories),"authority":"策略字段唯一权威源=scripts/strategy_core.py；前端禁止重算"}
