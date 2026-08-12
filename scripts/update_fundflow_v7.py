#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures,json,pathlib,time,urllib.parse,urllib.request
from v7_config import load_config
from snapshot_io import save_snapshot
ROOT=pathlib.Path(__file__).resolve().parents[1];LATEST=ROOT/'docs'/'public_v7'/'data'/'latest-v7.json';HEAD={'User-Agent':'Mozilla/5.0','Referer':'https://data.eastmoney.com/'}
def get(url,timeout=18):
 last=None
 for i in range(3):
  try:
   req=urllib.request.Request(url,headers=HEAD)
   with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode('utf-8',errors='replace'))
  except Exception as e:last=e;time.sleep(.5*(i+1))
 raise RuntimeError(repr(last))
def fetch(row):
 code=row['code'].split('.')[0];market=1 if row['code'].endswith('.SH') else 0;params={'lmt':'0','klt':'101','secid':f'{market}.{code}','fields1':'f1,f2,f3,f7','fields2':'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65','ut':'b2884a393a59ad64002292a3e90d46a5','_':str(int(time.time()*1000))};j=get('https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?'+urllib.parse.urlencode(params));src=((j.get('data') or {}).get('klines') or []);out=[]
 for line in src:
  a=str(line).split(',')
  if len(a)<13:continue
  try:out.append({'date':a[0],'main':float(a[1]),'small':float(a[2]),'medium':float(a[3]),'large':float(a[4]),'super':float(a[5]),'main_pct':float(a[6]),'small_pct':float(a[7]),'medium_pct':float(a[8]),'large_pct':float(a[9]),'super_pct':float(a[10]),'close':float(a[11]),'change_pct':float(a[12])/100})
  except Exception:pass
 if not out:raise RuntimeError('empty fund flow')
 return row['code'],{'daily':out[-100:],'last_date':out[-1]['date'],'source':'东方财富公开资金流','identity_note':'按订单大小划分，只作为大单/小单代理，不代表真实机构或散户身份'}
def main():
 if not LATEST.exists():raise SystemExit('latest-v7.json missing')
 data=json.loads(LATEST.read_text('utf-8'));rows=[x for x in load_config()['companies'] if x['code'].endswith(('.SH','.SZ'))];out={};errors={}
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
  fs={pool.submit(fetch,x):x for x in rows}
  for f,x in fs.items():
   try:k,v=f.result();out[k]=v
   except Exception as e:errors[x['code']]=repr(e)
 data['fund_flows']=out
 data['fund_flow_summary']={'coverage':len(out),'total_a_share':len(rows),'source':'东方财富公开资金流','note':'大单/小单只是订单规模代理'}
 data.setdefault('errors',{}).update({'fund:'+k:v for k,v in errors.items()})
 save_snapshot(data)
 if len(out)<max(1,int(len(rows)*.70)):raise SystemExit(f'fund flow coverage too low {len(out)}/{len(rows)}')
 print(json.dumps({'status':'PASS','coverage':len(out),'total_a_share':len(rows),'errors':len(errors)},ensure_ascii=False))
if __name__=='__main__':main()
