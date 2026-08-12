#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures,json,pathlib,time,urllib.parse,urllib.request
from v7_config import load_config
from snapshot_io import save_snapshot
ROOT=pathlib.Path(__file__).resolve().parents[1];LATEST=ROOT/'docs'/'public_v7'/'data'/'latest-v7.json';HEAD={'User-Agent':'Mozilla/5.0','Referer':'https://data.eastmoney.com/notices/'}
POS=('中标','订单','签订','获批','回购','增持','预增','扭亏','增长','分红','战略合作','重大合同','上修','超预期');RISK=('减持','预亏','亏损','下降','下修','处罚','立案','调查','诉讼','仲裁','终止','风险提示','质押','退市','监管','问询函','冻结','违约')
def get(url,timeout=20):
 last=None
 for i in range(3):
  try:
   req=urllib.request.Request(url,headers=HEAD)
   with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode('utf-8',errors='replace'))
  except Exception as e:last=e;time.sleep(.5*(i+1))
 raise RuntimeError(repr(last))
def classify(t):
 if any(k in t for k in RISK):return'risk'
 if any(k in t for k in POS):return'positive'
 return'neutral'
def fetch(code,date):
 n=code.split('.')[0];p={'sr':'-1','page_size':'100','page_index':'1','ann_type':'A','client_source':'web','f_node':'0','s_node':'0','stock_list':n,'begin_time':date,'end_time':date};j=get('https://np-anotice-stock.eastmoney.com/api/security/ann?'+urllib.parse.urlencode(p));out=[]
 for x in ((j.get('data') or {}).get('list') or []):
  t=str(x.get('title') or '').strip()
  if not t:continue
  ac=str(x.get('art_code') or '');out.append({'date':str(x.get('notice_date') or x.get('display_time') or '')[:10],'title':t,'signal':classify(t),'source':'交易所正式披露索引','url':f'https://data.eastmoney.com/notices/detail/{n}/{ac}.html' if ac else ''})
 return code,out
def main():
 if not LATEST.exists():raise SystemExit('latest-v7.json missing')
 d=json.loads(LATEST.read_text('utf-8'));date=d.get('snapshot_date');codes=[x['code'] for x in load_config()['companies'] if x['code'].endswith(('.SH','.SZ'))];out={};errors={}
 with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
  fs={pool.submit(fetch,c,date):c for c in codes}
  for f,c in fs.items():
   try:k,v=f.result();
   except Exception as e:errors[c]=repr(e);continue
   if v:out[k]=v
 d['announcements']=out
 d['announcement_summary']={'snapshot_date':date,'a_share_checked':len(codes),'companies_with_disclosure':len(out),'disclosure_count':sum(map(len,out.values())),'failed':len(errors),'note':'标题分类只用于筛选，正式结论必须核对公告原文'}
 d.setdefault('errors',{}).update({'announcement:'+k:v for k,v in errors.items()})
 save_snapshot(d)
 print(json.dumps({'status':'PASS',**d['announcement_summary']},ensure_ascii=False))
if __name__=='__main__':main()
