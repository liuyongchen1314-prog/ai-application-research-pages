#!/usr/bin/env python3
from __future__ import annotations
import copy,datetime as dt,hashlib,json,pathlib,sys
import pytest
from collections import Counter

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import valuation_core
from market_clock import assess,phase,expected_completed_session
from strategy_core import ACTIONS,STAGES,ACTION_PRIORITY,STAGE_PRIORITY

LATEST=ROOT/'docs'/'public_v7'/'data'/'latest-v7.json'
FACT=ROOT/'docs'/'audit'/'V7.9.4_事实证据缺口.json'
FRONT=ROOT/'frontend'/'V7_9_统一前端.js'
WORKFLOW=ROOT/'.github'/'workflows'/'v7-unified-refresh.yml'

def h(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def companies(d):return [*((d.get('companies') or {}).get('hardware') or []),*((d.get('companies') or {}).get('application') or [])]
def check(v,msg):
    if not v: raise AssertionError(msg)

@pytest.fixture(scope='module')
def data():
    return json.load(open(LATEST,encoding='utf-8'))

def test_fields_counts(data):
    cs=companies(data); codes={x['code'] for x in cs}
    check(len(cs)==142 and len(codes)==142,'142 unique')
    check(sum(x.get('scope')=='hardware' for x in cs)==83,'83 hardware')
    check(sum(x.get('scope')=='application' for x in cs)==59,'59 application')
    check(set(data['quotes'])==set(data['valuation_current'])==set(data['strategy_current'])==codes,'single company pool')
    v=data['valuation_current']; split=Counter(x.get('forward_scenario_status') for x in v.values())
    check(split['research']==24 and split['unavailable']==118,f'24/118 {split}')
    check(sum(x.get('twelve_public') is not False for x in v.values())==0,'0 public 12m')
    check(sum(bool(x.get('formal_closed')) for x in v.values())==0,'0 formal closure')

def test_valuation_zero_drift_and_no_price_feedback():
    data,config=valuation_core.load_inputs()
    a=valuation_core.rebuild(copy.deepcopy(data),copy.deepcopy(config)); b=valuation_core.rebuild(copy.deepcopy(data),copy.deepcopy(config))
    check(h(a)==h(b),'same input valuation drift')
    changed=copy.deepcopy(data)
    for q in (changed.get('quotes') or {}).values():
        if isinstance(q.get('price'),(int,float)): q['price']=q['price']*1.37+3.21
    c=valuation_core.rebuild(changed,copy.deepcopy(config))
    fair=('current_low','current_high','six_low','six_high','twelve_low','twelve_high','pe_base_current','pe_base_six','pe_base_twelve','eps_anchor_current','eps_anchor_six','eps_anchor_twelve')
    for code in a:
        for k in fair: check(a[code].get(k)==c[code].get(k),f'{code} market price fed back into fair value {k}')
    check(all((x.get('institution_check') or {}).get('role') in (None,'仅交叉验证，不反推合理价') for x in a.values()),'institution target role')

def test_trend_action_sort_scores(data):
    held=set((data.get('user_positions') or {}).keys()); strat=data['strategy_current']
    for code,s in strat.items():
        check(s['action'] in ACTIONS,f'{code} action')
        check(s['trend_stage'] in STAGES,f'{code} stage')
        check(s['action_priority']==ACTION_PRIORITY[s['action']],f'{code} action priority')
        check(s['trend_stage_priority']==STAGE_PRIORITY[s['trend_stage']],f'{code} stage priority')
        check(0<=s['trend_quality_score']<=100 and 0<=s['buy_point_score']<=100 and 0<=s['data_completeness']<=100,f'{code} scores')
        check(isinstance(s.get('blockers'),list),f'{code} blockers')
        if s['action'].startswith('已持仓'):check(code in held,f'{code} holding action without position')
        if s['action']=='不追/回避' and s['buy_point_score']>=60: check(bool(s.get('reason')) and bool(s.get('blockers') or s.get('market_gate',{}).get('hard_veto')),f'{code} high buy score avoid unexplained')
        tech=s.get('technical') or {}
        check(tech.get('stage')==s['trend_stage'],'stage result conflict')
        check(tech.get('trend_quality_score')==s['trend_quality_score'],'trend score result conflict')
        expected_comp=round((tech.get('data_completeness',0)*0.65)+((s.get('can_slim') or {}).get('data_completeness',0)*0.35))
        check(expected_comp==s['data_completeness'],'completeness composition conflict')
    expected=['action_priority','trend_stage_priority','trend_quality_score(desc)','RS12m(desc)','RS6m(desc)','RS3m(desc)','industry_relative_rank(desc)','distance_to_pivot(abs asc)','setup_quality_score(desc)','sector_score(desc)','company_quality(desc)','code(asc)']
    check(data['strategy_meta']['sort_contract']==expected,'canonical sort')
    roll=data['strategy_meta']['rolling_validation']
    check(roll.get('sample_count',0)>500,'rolling sample too small')
    check(all(k in roll for k in ('win_rate','average_return','max_drawdown','profit_loss_ratio')),'rolling metrics incomplete')
    check('not used to tune' in str(roll).lower() or '不' in str(roll),'validation must document no pass-count tuning')

def test_canslim_evidence(data):
    for code,s in data['strategy_current'].items():
        cs=s.get('can_slim') or {}; items=cs.get('items') or []
        check([x.get('letter') for x in items]==list('CANSLIM'),f'{code} CANSLIM letters')
        for item in items:
            check(item.get('state') in {'pass','partial','fail','unknown','na'},f'{code} {item.get("letter")} state')
            check(bool(item.get('evidence')),f'{code} {item.get("letter")} evidence missing')
            if item.get('letter')=='I' and item.get('state')=='pass': check('分析师' not in item.get('evidence',''),f'{code} analyst coverage passed I')
            if item.get('letter')=='N' and item.get('state')=='pass': check('关键词' not in item.get('evidence','') or '不作为' in item.get('evidence',''),f'{code} keyword passed N')
            if item.get('state')=='unknown': check(any(x in item.get('evidence','') for x in ('缺','未取得','尚未取得','未齐全','未知','无法','不适用')),f'{code} unknown without missing-data evidence')
        check('不参与合理估值' in cs.get('book_original',''),f'{code} CANSLIM valuation boundary')
        check('涨跌停' in cs.get('a_share_localization','') and 'T+1' in cs.get('a_share_localization',''),f'{code} A-share localization')
    check(sum(s.get('can_slim',{}).get('verdict')=='通过' for s in data['strategy_current'].values())==0,'weak evidence created fake CANSLIM pass')

def test_market_clock():
    UTC=dt.timezone.utc
    cn_open=dt.datetime(2026,8,13,2,0,tzinfo=UTC)
    us_open=dt.datetime(2026,8,13,15,0,tzinfo=UTC)
    weekend=dt.datetime(2026,8,15,15,0,tzinfo=UTC)
    check(phase('china',cn_open)['phase']=='盘中','China phase')
    check(phase('us',us_open)['phase']=='盘中','US phase')
    check(phase('us',weekend)['phase']=='休市','US weekend')
    fresh=assess('us',sample_at=us_open-dt.timedelta(minutes=5),sample_date='2026-08-13',realtime=True,file_generated_at=us_open-dt.timedelta(minutes=2),now=us_open)
    check(fresh['fresh'] and not fresh['stale'],'US current sample should be fresh')
    stale=assess('us',sample_at=us_open-dt.timedelta(hours=20),sample_date='2026-08-12',realtime=False,file_generated_at=us_open-dt.timedelta(minutes=2),now=us_open)
    check(stale['stale'] and '盘中' in stale['reason'],'US previous close during open must be stale')
    cn_after=dt.datetime(2026,8,13,9,0,tzinfo=UTC)
    check(expected_completed_session('china',cn_after)=='2026-08-13','China completed session')

def test_market_json_and_coverage(data):
    live=json.load(open(ROOT/'docs'/'public_v7'/'data'/'live-markets.json',encoding='utf-8'))
    check(live['schema']=='v794-live-markets-2' and live['market_count']==4,'live schema')
    for g in ('china','hk','us','korea'):
        m=live['markets'][g]
        for k in ('phase','exchange_timezone','exchange_local_time','beijing_time','source','quote_type','sample_date','file_generated_at','fresh','stale','freshness_reason'):check(k in m,f'{g} {k}')
        check(m['fresh'] != m['stale'],f'{g} fresh stale')
    check(len(data['quotes'])==142,'142 quote coverage')
    # stale package rows are acceptable only when they are explicitly labelled stale.
    for g,m in live['markets'].items():
        exp=m.get('expected_completed_session'); sd=m.get('sample_date')
        if exp and sd!=exp and m.get('phase') in {'盘后','休市','盘前'}:check(m.get('stale') is True,f'{g} old session falsely fresh')

def test_hardware_application_same_contract(data):
    h=[c['code'] for c in companies(data) if c['scope']=='hardware']; a=[c['code'] for c in companies(data) if c['scope']=='application']
    skey=set(data['strategy_current'][h[0]])
    check(all(set(data['strategy_current'][x])==skey for x in h+a),'hardware/application strategy fields differ')
    for code in h+a:
        s=data['strategy_current'][code]
        check(set((s.get('technical') or {}).keys())==set((data['strategy_current'][h[0]].get('technical') or {}).keys()),f'{code} technical contract differs')

def test_factual_gaps_and_crosscheck(data):
    fact=json.load(open(FACT,encoding='utf-8'))
    check(fact['formal_closed']==0 and fact['hk_companies']==14,'factual closure facts')
    check(fact['summary']['港股币种']['unresolved']==14,'HK currency falsely closed')
    for code,v in data['valuation_current'].items():
        ic=v.get('institution_check') or {}
        if ic.get('overlap') is False:
            check(v.get('formal_closed') is False,f'{code} institution mismatch still formal')
            check(v.get('audit_status') not in {'正式闭环','通过'},f'{code} institution mismatch not flagged')

def test_source_authority():
    front=FRONT.read_text('utf-8'); wf=WORKFLOW.read_text('utf-8')
    check('__V794_AUTHORITY__' in front and 'legacyFrontendCalculatorsDisabled:true' in front,'frontend authority marker')
    check('Math.min(score,49)' not in front.replace(' ',''),'49 cap')
    check('python scripts/更新研究系统.py' not in wf,'legacy all-in-one active')
    legacy=(ROOT/'scripts'/'更新研究系统.py').read_text('utf-8')
    check('deprecated' in legacy.lower() or '停用' in legacy,'legacy does not fail fast')
    check("5,15,25,35,45,55 13-21" in wf,'US 10m backend sampling missing')

def main():
    data=json.load(open(LATEST,encoding='utf-8'))
    tests=[
      ('1_fields_counts',lambda:test_fields_counts(data)),
      ('2_valuation_zero_drift',test_valuation_zero_drift_and_no_price_feedback),
      ('3_trend_action_sort_scores',lambda:test_trend_action_sort_scores(data)),
      ('4_canslim_evidence',lambda:test_canslim_evidence(data)),
      ('5_market_clock',test_market_clock),
      ('6_market_json_quote_coverage',lambda:test_market_json_and_coverage(data)),
      ('7_hardware_application_same_contract',lambda:test_hardware_application_same_contract(data)),
      ('8_factual_gaps_crosscheck',lambda:test_factual_gaps_and_crosscheck(data)),
      ('9_source_authority',test_source_authority),
    ]
    out=[]
    for name,fn in tests:
        fn(); out.append({'test':name,'status':'PASS'})
    print(json.dumps({'status':'PASS','tests':out},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
