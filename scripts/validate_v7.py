#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime as dt,json,pathlib,time,urllib.parse,urllib.request
from zoneinfo import ZoneInfo
from v7_config import load_config
from snapshot_io import save_snapshot
ROOT=pathlib.Path(__file__).resolve().parents[1]
P=ROOT/'docs'/'public_v7'/'data'/'latest-v7.json'
INTRADAY_DIR=ROOT/'docs'/'public_v7'/'data'/'intraday'
HEAD={'User-Agent':'Mozilla/5.0 (compatible; AI-Research-V7/1.0)','Accept':'application/json,text/plain,*/*'}
CALENDAR_NAMES={'china':'XSHG','hk':'XHKG','korea':'XKRX','us':'XNYS'}

def fail(msg):print('FAIL:',msg);raise SystemExit(1)

def expected_completed_session(group):
 try:
  import exchange_calendars as xcals
  import pandas as pd
  cal=xcals.get_calendar(CALENDAR_NAMES[group])
  now=pd.Timestamp.now(tz=ZoneInfo('UTC'))
  session=cal.date_to_session(pd.Timestamp(now.date()),direction='previous')
  if now<cal.session_close(session):session=cal.previous_session(session)
  return str(session.date())
 except Exception as e:
  fail(f'{group}交易日历不可用: {e!r}')

def _clock(group):
 if group=='us':return ZoneInfo('America/New_York'),dt.time(16,15),'^IXIC'
 if group=='korea':return ZoneInfo('Asia/Seoul'),dt.time(15,40),'^KS11'
 raise ValueError(group)

def _request_json(url,timeout=25):
 last=None
 for i in range(3):
  try:
   req=urllib.request.Request(url,headers=HEAD)
   with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode('utf-8','replace'))
  except Exception as e:last=e;time.sleep(.5*(i+1))
 raise RuntimeError(repr(last))

def _completed_yahoo(item):
 tz,finalize,_=_clock(item['group']);now=dt.datetime.now(dt.timezone.utc).astimezone(tz)
 ticker=urllib.parse.quote(item['ticker'],safe='')
 j=_request_json(f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=15d&interval=1d&events=history')
 chart=((j.get('chart') or {}).get('result') or [None])[0]
 if not chart:raise RuntimeError((j.get('chart') or {}).get('error'))
 ts=chart.get('timestamp') or [];cl=((((chart.get('indicators') or {}).get('quote') or [{}])[0]).get('close') or [])
 pts=[]
 for stamp,close in zip(ts,cl):
  if close is None:continue
  local_date=dt.datetime.fromtimestamp(stamp,dt.timezone.utc).astimezone(tz).date()
  if now.time()<finalize and local_date>=now.date():continue
  pts.append((local_date,float(close)))
 if len(pts)<2:raise RuntimeError('完整交易日数据不足')
 a,b=pts[-2],pts[-1]
 return {'ticker':item['ticker'],'name':item['name'],'group':item['group'],'date':b[0].isoformat(),'close':b[1],'change_pct':b[1]/a[1]-1,'source':'海外公开行情','session_complete':True}

def _save(d):
 save_snapshot(d)

def _repair_partial(d,cfg,group):
 tz,finalize,benchmark=_clock(group);now=dt.datetime.now(dt.timezone.utc).astimezone(tz);fr=(d.get('market_freshness') or {}).get(group) or {};date=str(fr.get('date') or '')
 if not (now.time()<finalize and date>=now.date().isoformat()):return False
 wanted=[x for x in cfg.get('external_market',[]) if x.get('group')==group]
 items=[]
 for x in wanted:items.append(_completed_yahoo(x))
 b=next((x for x in items if x.get('ticker')==benchmark),None)
 if not b:fail(f'{group}完整交易日基准缺失')
 bad=[x.get('ticker') for x in items if x.get('date')!=b['date']]
 if bad:fail(f'{group}完整交易日成分日期不一致: {bad}')
 d.setdefault('market_context',{})[group]={'items':items,'status':'正常'}
 d.setdefault('market_freshness',{})[group]={'fresh':True,'date':b['date'],'reason':'','count':len(items)}
 d.setdefault('errors',{});d['errors']={k:v for k,v in d['errors'].items() if not k.startswith(group+':')}
 _save(d);print(f'REPAIRED {group}: 使用上一完整交易日 {b["date"]}')
 return True

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['all','us','asia'],default='all');a=ap.parse_args();cfg=load_config();rows=cfg['companies'];total=len(rows)
 if total!=142:fail(f'公司总数 {total} != 142')
 if sum(x['scope']=='hardware' for x in rows)!=83 or sum(x['scope']=='application' for x in rows)!=59:fail('83/59分类不一致')
 if not P.exists():fail('latest-v7.json不存在')
 d=json.loads(P.read_text('utf-8'))
 if d.get('schema')!='v7-public-market-1':fail(f'正式数据协议不匹配: {d.get("schema")}')
 if str(d.get('embedded_snapshot') or '')!=str(d.get('snapshot_date') or ''):fail('内置基线日期仍停在旧快照')
 companies=[*((d.get('companies') or {}).get('hardware') or []),*((d.get('companies') or {}).get('application') or [])]
 quotes=d.get('quotes') or {};valuations=d.get('valuation_current') or {};strategies=d.get('strategy_current') or {}
 for company in companies:
  code=company.get('code');quote=quotes.get(code) or {};valuation=valuations.get(code) or {};strategy=strategies.get(code) or {}
  if not quote.get('date'):fail(f'{code} 报价缺少标准交易日字段')
  if quote.get('session_complete') is not True:fail(f'{code} 报价不是正式收盘口径')
  if company.get('price')!=quote.get('price'):fail(f'{code} 公司卡片价格与唯一报价不一致')
  if company.get('price_date')!=quote.get('date'):fail(f'{code} 公司卡片日期与唯一报价不一致')
  if company.get('valuation_status')!=valuation.get('status'):fail(f'{code} 公司卡片估值状态与唯一估值对象不一致')
  if strategy and strategy.get('reference_price')!=quote.get('price'):fail(f'{code} 策略参考价与唯一报价不一致')
  if 'V7.6当前合理区间' in str(company.get('one_liner') or ''):fail(f'{code} 一句话仍含V7.6旧估值')
  if '等待当前估值模型更新' in json.dumps(company.get('signal') or {},ensure_ascii=False):fail(f'{code} 信号仍含旧等待提示')
  if '估值日2026-08-07' in json.dumps(company.get('details') or [],ensure_ascii=False):fail(f'{code} 生产详情仍显示8月7日旧估值日')
 fund=d.get('fund_flow_summary') or {};actual_fund=sum(str((x or {}).get('last_date') or '')==str(d.get('snapshot_date') or '') for x in (d.get('fund_flows') or {}).values())
 if int(fund.get('coverage_current') or 0)!=actual_fund:fail('资金流当前覆盖把旧日期缓存计入当日')
 if a.mode in ('all','asia'):_repair_partial(d,cfg,'korea')
 if a.mode in ('all','us'):_repair_partial(d,cfg,'us')
 d=json.loads(P.read_text('utf-8'));cov=d.get('coverage') or {};fr=d.get('market_freshness') or {}
 if a.mode in ('all','asia'):
  if +cov.get('histories',0)!=total or +cov.get('quotes',0)!=total:fail('142家公司行情/K线覆盖不完整')
  if +cov.get('benchmarks',0)<4:fail('宽基指数覆盖不足')
  manifest=d.get('intraday') or {};available=manifest.get('available_codes') or []
  entity_codes=sorted(p.stem.replace('_','.',1) for p in INTRADAY_DIR.glob('*.json'))
  if manifest.get('schema')!='v7-intraday-manifest-1':fail('分时实体清单协议缺失')
  if len(available)!=len(set(available)):fail('分时实体清单含重复代码')
  if sorted(available)!=entity_codes:fail(f'分时清单与实体文件不一致: 清单{len(available)}，实体{len(entity_codes)}')
  if +manifest.get('success',0)!=len(entity_codes) or +cov.get('intraday',0)!=len(entity_codes):fail('分时覆盖数字与实体数量不一致')
  if len(entity_codes)<int(total*.95):fail(f'分时覆盖低于95%: {len(entity_codes)}/{total}')
  for k in ('china','hk','korea'):
   if not (fr.get(k) or {}).get('fresh'):fail(f'{k}市场数据未通过新鲜度门禁: {fr.get(k)}')
   expected=expected_completed_session(k);actual=str((fr.get(k) or {}).get('date') or '')
   if actual!=expected:fail(f'{k}完整交易日不一致: 当前{actual}, 应为{expected}')
  kr=dt.datetime.now(dt.timezone.utc).astimezone(ZoneInfo('Asia/Seoul'));krd=str((fr.get('korea') or {}).get('date') or '')
  if kr.time()<dt.time(15,40) and krd>=kr.date().isoformat():fail(f'韩国数据包含尚未收盘的当日盘中K线: {krd}')
 if a.mode in ('all','us'):
  if not (fr.get('us') or {}).get('fresh'):fail(f'美国市场数据未通过新鲜度门禁: {fr.get("us")}')
  us=(d.get('market_context') or {}).get('us') or {}
  if not us.get('items'):fail('美国当前数据为空；禁止用旧缓存冒充')
  expected=expected_completed_session('us')
  if str(