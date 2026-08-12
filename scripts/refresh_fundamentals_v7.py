#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt,hashlib,json,pathlib,time,urllib.parse,urllib.request
from v7_config import load_config
from snapshot_io import save_snapshot
ROOT=pathlib.Path(__file__).resolve().parents[1];LATEST=ROOT/'docs'/'public_v7'/'data'/'latest-v7.json';URL='https://datacenter-web.eastmoney.com/api/data/v1/get';HEAD={'User-Agent':'Mozilla/5.0','Referer':'https://data.eastmoney.com/'}
def req(params,timeout=30):
 last=None
 for i in range(3):
  try:
   r=urllib.request.Request(URL+'?'+urllib.parse.urlencode(params),headers=HEAD)
   with urllib.request.urlopen(r,timeout=timeout) as f:return json.loads(f.read().decode('utf-8',errors='replace'))
  except Exception as e:last=e;time.sleep(.7*(i+1))
 raise RuntimeError(repr(last))
def fetch_all(report,columns,extra=None):
 p={'reportName':report,'columns':columns,'pageNumber':'1','pageSize':'500'};p.update(extra or {});j=req(p);res=j.get('result') or {};rows=list(res.get('data') or []);pages=int(res.get('pages') or 1)
 for n in range(2,pages+1):p['pageNumber']=str(n);rows.extend((req(p).get('result') or {}).get('data') or [])
 return rows
def f(v):
 try:return float(v)
 except Exception:return None
def quarter_ends(today):
 out=[]
 for y in range(today.year,today.year-2,-1):
  for m,d in ((12,31),(9,30),(6,30),(3,31)):
   q=dt.date(y,m,d)
   if q<=today:out.append(q)
 return sorted(out,reverse=True)[:6]
def sig(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def requires_revaluation(old,new):
 old=old or {};old_report=old.get('latest_report') or {};new_report=new.get('latest_report') or {}
 if new_report.get('report_date') and new_report.get('report_date')!=old_report.get('report_date'):return True
 old_cons=old.get('consensus') or {};new_cons=new.get('consensus') or {}
 for key in ('eps1','eps2','eps3'):
  try:
   before=float(old_cons.get(key));after=float(new_cons.get(key))
  except (TypeError,ValueError):
   if old_cons.get(key) is None and new_cons.get(key) is not None:return True
   continue
  if before and abs(after/before-1)>.05:return True
 for key in ('diluted_shares','cash','debt','minority_interest'):
  before=f(old_report.get(key));after=f(new_report.get(key))
  if before is None and after is not None:return True
  if before and after is not None and abs(after/before-1)>.02:return True
 for key in ('corporate_action_hash','business_structure_hash','accounting_policy_hash'):
  if new.get(key) and new.get(key)!=old.get(key):return True
 return False
def main():
 if not LATEST.exists():raise SystemExit('latest-v7.json missing')
 data=json.loads(LATEST.read_text('utf-8'));cfg=load_config();a={r['code'].split('.')[0]:r['code'] for r in cfg['companies'] if r['code'].endswith(('.SH','.SZ'))};reports={};today=dt.date.today()
 for q in quarter_ends(today):
  rows=fetch_all('RPT_LICO_FN_CPD','ALL',{'sortColumns':'UPDATE_DATE,SECURITY_CODE','sortTypes':'-1,-1','filter':f"(REPORTDATE='{q.isoformat()}')"})
  for x in rows:
   n=str(x.get('SECURITY_CODE') or '')
   if n not in a or n in reports:continue
   reports[n]={'report_date':str(x.get('REPORTDATE') or '')[:10],'notice_date':str(x.get('NOTICE_DATE') or x.get('UPDATE_DATE') or '')[:10],'eps':f(x.get('BASIC_EPS')),'revenue':f(x.get('TOTAL_OPERATE_INCOME')),'revenue_yoy':f(x.get('YSTZ')),'net_profit':f(x.get('PARENT_NETPROFIT')),'net_profit_yoy':f(x.get('SJLTZ')),'deduct_net_profit':f(x.get('DEDUCT_PARENT_NETPROFIT') or x.get('KCFJCXSYJLR')),'deduct_net_profit_yoy':f(x.get('DEDUCT_PARENT_NETPROFIT_YOY') or x.get('KCFJCXSYJLR_TZ')),'roe':f(x.get('WEIGHTAVG_ROE')),'ocf_per_share':f(x.get('MGJYXJJE')),'gross_margin':f(x.get('XSMLL')),'source':'东方财富公开财务数据'}
  if len(reports)>=len(a):break
 cons={};rows=fetch_all('RPT_WEB_RESPREDICT','SECUCODE,SECURITY_CODE,RATING_ORG_NUM,RATING_BUY_NUM,RATING_ADD_NUM,RATING_NEUTRAL_NUM,RATING_REDUCE_NUM,RATING_SALE_NUM,YEAR1,EPS1,YEAR2,EPS2,YEAR3,EPS3,DEC_AIMPRICEMAX,DEC_AIMPRICEMIN',{'sortTypes':'-1','sortColumns':'RATING_ORG_NUM'})
 for x in rows:
  n=str(x.get('SECURITY_CODE') or '')
  if n not in a:continue
  cons[n]={'forecast_date':data.get('snapshot_date'),'year1':x.get('YEAR1'),'eps1':f(x.get('EPS1')),'year2':x.get('YEAR2'),'eps2':f(x.get('EPS2')),'year3':x.get('YEAR3'),'eps3':f(x.get('EPS3')),'target_min':f(x.get('DEC_AIMPRICEMIN')),'target_max':f(x.get('DEC_AIMPRICEMAX')),'analyst_count':int(f(x.get('RATING_ORG_NUM')) or 0),'source':'东方财富公开一致预期'}
 old=data.get('company_financials') or {};out={};changed=[]
 for row in cfg['companies']:
  code=row['code'];n=code.split('.')[0];ann=(data.get('announcements') or {}).get(code) or [];event=[x for x in ann if any(k in str(x.get('title') or '') for k in ('年度报告','半年度报告','季度报告','业绩预告','业绩快报'))]
  old_record=old.get(code) or {};new_report=reports.get(n) if code.endswith(('.SH','.SZ')) else None;new_consensus=cons.get(n) if code.endswith(('.SH','.SZ')) else None
  rec={'updated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'capture_date':dt.date.today().isoformat(),'latest_report':new_report or old_record.get('latest_report'),'consensus':new_consensus or old_record.get('consensus'),'financial_event':event[:5] or old_record.get('financial_event') or [],'corporate_action_hash':old_record.get('corporate_action_hash'),'business_structure_hash':old_record.get('business_structure_hash'),'accounting_policy_hash':old_record.get('accounting_policy_hash'),'source_scope':'A股使用结构化更新；其他市场只在取得正式披露时更新，禁止跨市场套用一致预期'};core={k:rec[k] for k in ('latest_report','consensus','financial_event','corporate_action_hash','business_structure_hash','accounting_policy_hash')};rec['content_hash']=sig(core);old_hash=old_record.get('content_hash');meaningful=requires_revaluation(old_record,rec);rec['event_refresh_status']='changed' if meaningful else 'metadata_only' if old_hash and old_hash!=rec['content_hash'] else 'initial' if not old_hash else 'unchanged'
  if meaningful:changed.append(code)
  out[code]=rec
 data['company_financials']=out
 data['fundamental_refresh_summary']={'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'a_share_report_coverage':len(reports),'a_share_consensus_coverage':len(cons),'changed_companies':changed,'method':'事件驱动：财报/业绩预告/一致预期发生变化才进入重新估值队列'}
 data['revaluation_queue']=changed
 save_snapshot(data)
 print(json.dumps({'status':'PASS','reports':len(reports),'consensus':len(cons),'changed':len(changed),'total':len(cfg['companies'])},ensure_ascii=False))
if __name__=='__main__':main()
