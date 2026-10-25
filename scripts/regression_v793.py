#!/usr/bin/env python3
"""Full release regression for V7.9.4 (filename retained for workflow compatibility)."""
from __future__ import annotations
import hashlib,json,pathlib,re

ROOT=pathlib.Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'docs'/'public_v7'; LATEST=PUBLIC/'data'/'latest-v7.json'; LIVE=PUBLIC/'data'/'live-markets.json'; HTML=PUBLIC/'index.html'; INDEX=PUBLIC/'index.json'
WORKFLOW=ROOT/'.github'/'workflows'/'v7-unified-refresh.yml'; FRONT=ROOT/'frontend'/'V7_9_统一前端.js'; FACT=ROOT/'docs'/'audit'/'V7.9.4_事实证据缺口.json'
ACTIONS=('重点参与','小仓试错','临近触发','突破后确认','缩量回踩观察','普通候选','等待趋势修复','不追/回避','已持仓继续持有','已持仓减仓或退出')
STAGES=('第二阶段确认','第二阶段候选','第一阶段','第三阶段','第四阶段','数据不足')

def fail(x):raise SystemExit(x)
def companies(d):return [*((d.get('companies') or {}).get('hardware') or []),*((d.get('companies') or {}).get('application') or [])]

def main():
 d=json.loads(LATEST.read_text('utf-8')); cs=companies(d); codes={x['code'] for x in cs}; q=d.get('quotes') or {}; v=d.get('valuation_current') or {}; s=d.get('strategy_current') or {}
 if d.get('version')!='V7.9.4' or d.get('frontend_release')!='V7.9.4':fail('snapshot release not V7.9.4')
 if (len(cs),len(codes),sum(x.get('scope')=='hardware' for x in cs),sum(x.get('scope')=='application' for x in cs))!=(142,142,83,59):fail('pool is not 142/83/59 unique')
 if set(q)!=codes or set(v)!=codes or set(s)!=codes:fail('quote/valuation/strategy pools differ')
 if d.get('snapshot_date')!=d.get('embedded_snapshot'):fail('embedded snapshot date differs')
 six=__import__('collections').Counter(x.get('forward_scenario_status') for x in v.values())
 if six.get('research',0)!=24 or six.get('unavailable',0)!=118:fail(f'24/118 split broken: {dict(six)}')
 if sum(x.get('twelve_public') is not False for x in v.values())!=0:fail('public 12m targets not zero')
 if sum(bool(x.get('formal_closed')) for x in v.values())!=0:fail('formal evidence closure not zero')
 if any(x.get('forward_public_horizon_months')!=6 for x in v.values()):fail('forward public horizon not 6m')
 held=set((d.get('user_positions') or {}).keys())
 for c in cs:
  code=c['code']; vv=v[code]; ss=s[code]; qq=q[code]
  if ss.get('action') not in ACTIONS:fail(f'{code}: invalid action')
  if ss.get('trend_stage') not in STAGES:fail(f'{code}: invalid stage')
  if ss.get('action','').startswith('已持仓') and code not in held:fail(f'{code}: unheld stock has holding action')
  for k in ('trend_quality_score','buy_point_score','data_completeness'):
   if not isinstance(ss.get(k),(int,float)):fail(f'{code}: missing score {k}')
  if not isinstance(ss.get('blockers'),list):fail(f'{code}: blockers is not list')
  if ss.get('reference_price')!=qq.get('price') or ss.get('reference_price_date')!=qq.get('date'):fail(f'{code}: strategy price basis differs from close quote')
  if c.get('price')!=qq.get('price') or c.get('price_date')!=qq.get('date'):fail(f'{code}: display card price differs from quote')
  if c.get('six') != (vv.get('forward_scenario') or '暂不估算'):fail(f'{code}: card six-month display stale')
  if vv.get('forward_scenario_status')=='research':
   calc=vv.get('forward_scenario_calculation') or {}
   if calc.get('route')!='current_research_range_roll_forward_by_ntm_eps_and_pe':fail(f'{code}: six-month route not same-source')
  if any(k in vv for k in ('action','trend_stage','buy_point_score','trend_quality_score')):fail(f'{code}: valuation contains strategy fields')
 if (d.get('strategy_meta') or {}).get('separated_from_valuation') is not True:fail('strategy not separated from valuation')
 contract=(d.get('strategy_meta') or {}).get('sort_contract') or []
 expected=['action_priority','trend_stage_priority','trend_quality_score(desc)','RS12m(desc)','RS6m(desc)','RS3m(desc)','industry_relative_rank(desc)','distance_to_pivot(abs asc)','setup_quality_score(desc)','sector_score(desc)','company_quality(desc)','code(asc)']
 if contract!=expected:fail(f'canonical sort contract differs: {contract}')
 roll=(d.get('strategy_meta') or {}).get('rolling_validation') or {}
 for k in ('sample_count','win_rate','average_return','max_drawdown','profit_loss_ratio'):
  if k not in roll:fail(f'rolling validation missing {k}')
 live=json.loads(LIVE.read_text('utf-8'))
 if live.get('schema')!='v794-live-markets-2' or live.get('release')!='V7.9.4' or live.get('market_count')!=4:fail('live schema/release/market count wrong')
 if live.get('separate_from_valuation') is not True or live.get('separate_intraday_price_from_close_strategy') is not True:fail('intraday/valuation/strategy separation flag missing')
 req=('phase','exchange_timezone','exchange_local_time','beijing_time','source','quote_type','fresh','stale','freshness_reason','sample_date','file_generated_at')
 for group in ('china','hk','us','korea'):
  m=(live.get('markets') or {}).get(group) or {}
  if any(k not in m for k in req):fail(f'{group}: freshness/timezone fields incomplete')
  rows=m.get('items') or []
  if not rows or any(not isinstance(x.get('price'),(int,float)) or not isinstance(x.get('change_pct'),(int,float)) for x in rows):fail(f'{group}: live rows incomplete')
  if m.get('fresh')==m.get('stale'):fail(f'{group}: fresh/stale flags contradictory')
 wf=WORKFLOW.read_text('utf-8')
 if "cron: '5,15,25,35,45,55 13-21 * * 1-5'" not in wf:fail('US continuous sampling cron missing')
 for token in ('WORKFLOW_SCHEDULE','WORKFLOW_RUN_STARTED_AT','python scripts/update_live_markets.py','python scripts/rebuild_strategy.py','python scripts/validate_strategy.py'):
  if token not in wf:fail(f'workflow missing {token}')
 if 'python scripts/更新研究系统.py' in wf:fail('workflow still calls deprecated all-in-one engine')
 front=FRONT.read_text('utf-8')
 for token in ('__V794_AUTHORITY__','legacyFrontendCalculatorsDisabled:true','行情已过期','v794CanonicalCompare','trend_quality_score','buy_point_score'):
  if token not in front:fail(f'frontend missing authority/UX token {token}')
 if 'Math.min(score, 49)' in front or 'Math.min(score,49)' in front:fail('49 score cap remains')
 if re.search(r'\bfunction\s+v74CanSlimAssessment\s*\([^)]*\)\s*\{(?:(?!return\s+.*can_slim).){300,}',front,re.S):fail('frontend CAN SLIM appears to recompute')
 fact=json.loads(FACT.read_text('utf-8'))
 if fact.get('formal_closed')!=0 or fact.get('hk_companies')!=14:fail('factual-gap audit invariant broken')
 if (fact.get('summary') or {}).get('港股币种',{}).get('unresolved')!=14:fail('HK currency gaps were falsely closed')
 html=HTML.read_text('utf-8')
 if 'V7.9.4' not in html:fail('built HTML is not V7.9.4')
 if any(t in html for t in ('__V79_CSS__','__V79_SNAPSHOT_JSON__','__V79_APP_JS__')):fail('build token unresolved')
 idx=json.loads(INDEX.read_text('utf-8'))
 if idx.get('snapshot_sha256')!=hashlib.sha256(LATEST.read_bytes()).hexdigest():fail('public index snapshot hash differs')
 print(json.dumps({'status':'PASS','release':'V7.9.4','companies':142,'hardware':83,'application':59,'six_month_research':24,'six_month_unavailable':118,'public_12m':0,'formal_closed':0,'actions':(d.get('strategy_meta') or {}).get('action_counts'),'live_markets':4},ensure_ascii=False))

if __name__=='__main__':main()
