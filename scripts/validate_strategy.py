#!/usr/bin/env python3
from __future__ import annotations
import collections, json
from snapshot_io import load_snapshot
from strategy_core import ACTIONS, STAGES

def main():
    data=load_snapshot(); vals=data.get('valuation_current') or {}; rows=data.get('strategy_current') or {}; errors=[]
    if len(rows)!=142 or set(rows)!=set(vals): errors.append('strategy coverage/source mismatch')
    counts=collections.Counter(); stages=collections.Counter()
    required=('action','reason','valuation_position','sector_strength','market_gate','trend_stage','trend_quality_score','buy_point_score','data_completeness','blockers','can_slim','a_share_rules','invalidation')
    for code,row in rows.items():
        missing=[k for k in required if k not in row or row.get(k) is None]
        if missing: errors.append(f"{code}: missing {','.join(missing)}")
        action=row.get('action'); counts[action]+=1; stages[row.get('trend_stage')]+=1
        if action not in ACTIONS: errors.append(f'{code}: unknown action {action}')
        if row.get('trend_stage') not in STAGES: errors.append(f"{code}: unknown stage {row.get('trend_stage')}")
        val=vals.get(code) or {}
        if row.get('valuation_confidence')!=val.get('confidence_display'): errors.append(f'{code}: confidence drift')
        if row.get('reference_price')!=val.get('price_as_of'): errors.append(f'{code}: reference price drift')
        if row.get('reference_price_date')!=val.get('price_date'): errors.append(f'{code}: reference date drift')
        if any(k in val for k in ('action','action_level','action_reason','initial_position','trend_quality_score','buy_point_score')): errors.append(f'{code}: valuation object contains strategy fields')
        if row.get('action') in {'已持仓继续持有','已持仓减仓或退出'} and code not in (data.get('user_positions') or {}): errors.append(f'{code}: unheld company displays holding action')
        tq=row.get('trend_quality_score'); bp=row.get('buy_point_score')
        if not (isinstance(tq,(int,float)) and 0<=tq<=100): errors.append(f'{code}: trend score invalid')
        if not (isinstance(bp,(int,float)) and 0<=bp<=100): errors.append(f'{code}: buy score invalid')
        cs=row.get('can_slim') or {}
        if len(cs.get('items') or [])!=7: errors.append(f'{code}: CAN SLIM does not have 7 evidence items')
        i=next((x for x in cs.get('items') or [] if x.get('letter')=='I'),{})
        if '分析师覆盖' in str(i.get('evidence')) and i.get('state')=='pass': errors.append(f'{code}: analyst coverage improperly passes I')
        if row.get('market_gate',{}).get('hard_veto') and action in {'重点参与','小仓试错','临近触发','突破后确认'}: errors.append(f'{code}: hard market gate leaked into aggressive action')
    # Zero in aggressive categories is valid; no quota test is allowed.
    if errors: raise SystemExit('\n'.join(errors[:80]))
    print(json.dumps({'status':'PASS','companies':142,'actions':dict(counts),'stages':dict(stages),'quota_forcing':False,'separated':True},ensure_ascii=False))
if __name__=='__main__': main()
