#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, datetime as dt, json, os, pathlib, statistics, tempfile, time, urllib.parse, urllib.request
from zoneinfo import ZoneInfo
from v7_config import load_config
from snapshot_io import save_snapshot
ROOT=pathlib.Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'docs'/'public_v7'; DATA=PUBLIC/'data'; INTRADAY=DATA/'intraday'
HEAD={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/144 Safari/537.36','Referer':'https://gu.qq.com/','Accept':'application/json,text/plain,*/*'}
BENCH={'CSI300':{'symbol':'sh000300','name':'沪深300'},'CHINEXT':{'symbol':'sz399006','name':'创业板指'},'STAR50':{'symbol':'sh000688','name':'科创50'},'HSI':{'symbol':'hkHSI','name':'恒生指数'},'HSTECH':{'symbol':'hkHSTECH','name':'恒生科技指数'}}
DATA_SCHEMA='v7-public-market-1'
INDEX_SCHEMA='v7-public-index-3'
INTRADAY_SCHEMA='v7-intraday-manifest-1'

def normalize_quote_date(value):
    raw=''.join(ch for ch in str(value or '') if ch.isdigit())
    if len(raw)>=8:return f'{raw[:4]}-{raw[4:6]}-{raw[6:8]}'
    return None

def request(url,timeout=25,encoding='utf-8'):
    last=None
    for i in range(4):
        try:
            req=urllib.request.Request(url,headers=HEAD)
            with urllib.request.urlopen(req,timeout=timeout) as r:return r.read().decode(encoding,errors='replace')
        except Exception as e:last=e;time.sleep(.7*(i+1))
    raise RuntimeError(f'{url}: {last!r}')

def qfq_history(symbol,count=700):
    url='https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?'+urllib.parse.urlencode({'param':f'{symbol},day,,,{count},qfq'})
    j=json.loads(request(url));node=(j.get('data') or {}).get(symbol) or {};src=node.get('qfqday') or node.get('day') or [];out=[]
    for x in src:
        if len(x)<6:continue
        try:out.append([str(x[0]),float(x[1]),float(x[2]),float(x[3]),float(x[4]),float(x[5])])
        except Exception:pass
    if not out:raise RuntimeError(f'empty history {symbol}')
    return out

def fetch_history(row):
    bars=qfq_history(row['symbol'],700);return row['code'],{'daily':bars,'provider':'腾讯公开行情','symbol':row['symbol'],'last_date':bars[-1][0],'count':len(bars)}

def fetch_benchmark(k,cfg):
    bars=qfq_history(cfg['symbol'],700);return k,{'name':cfg['name'],'symbol':cfg['symbol'],'daily':bars,'last_date':bars[-1][0],'provider':'腾讯公开行情'}

def parse_intraday(j,symbol,kind):
    node=(j.get('data') or {}).get(symbol) or {};root=node.get('data') or {};out=[]
    if kind=='minute':
        d=str(root.get('date') or '') if isinstance(root,dict) else '';rows=(root.get('data') or []) if isinstance(root,dict) else []
        for line in rows:
            p=str(line).split(' ')
            if len(p)>=3:
                try:out.append([d,p[0],float(p[1]),float(p[2])])
                except Exception:pass
    else:
        days=root if isinstance(root,list) else (root.get('data') or [] if isinstance(root,dict) else [])
        if isinstance(days,dict):days=days.get('data') or []
        for day in days:
            if not isinstance(day,dict):continue
            d=str(day.get('date') or '');rows=day.get('data') or []
            if isinstance(rows,dict):rows=rows.get('data') or []
            for line in rows:
                p=str(line).split(' ')
                if len(p)>=3:
                    try:out.append([d,p[0],float(p[1]),float(p[2])])
                    except Exception:pass
    return out

def fetch_intraday(row):
    s=row['symbol'];m=json.loads(request(f'https://web.ifzq.gtimg.cn/appstock/app/minute/query?code={urllib.parse.quote(s)}',18));f=json.loads(request(f'https://web.ifzq.gtimg.cn/appstock/app/day/query?code={urllib.parse.quote(s)}',18));mn=parse_intraday(m,s,'minute');five=parse_intraday(f,s,'five')
    if not mn and not five:raise RuntimeError('empty intraday')
    return row['code'],{'code':row['code'],'symbol':s,'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'minute':mn,'five_day':five}

def fetch_quotes(rows):
    out={};sym2code={x['symbol']:x['code'] for x in rows}
    for start in range(0,len(rows),45):
        group=rows[start:start+45];text=request('https://qt.gtimg.cn/q='+','.join(x['symbol'] for x in group),20,'gbk')
        for line in text.splitlines():
            if '="' not in line:continue
            lhs,raw=line.split('="',1);raw=raw.rsplit('"',1)[0];sym=lhs.replace('v_','').strip();a=raw.split('~');code=sym2code.get(sym)
            if not code or len(a)<6:continue
            try:
                p=float(a[3]);pre=float(a[4]);stamp=a[30] if len(a)>30 else '';out[code]={'name':a[1],'price':p,'prev_close':pre,'open':float(a[5]),'change_pct':p/pre-1 if pre else None,'source':'腾讯公开行情','timestamp':stamp,'date':normalize_quote_date(stamp),'session_complete':False}
            except Exception:pass
    return out

def _market_clock(group):
    if group=='us':return ZoneInfo('America/New_York'),dt.time(16,15)
    if group=='korea':return ZoneInfo('Asia/Seoul'),dt.time(15,40)
    return dt.timezone.utc,dt.time(23,59)

def yahoo(item):
    t=urllib.parse.quote(item['ticker'],safe='');j=json.loads(request(f'https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=15d&interval=1d&events=history',25));chart=((j.get('chart') or {}).get('result') or [None])[0]
    if not chart:raise RuntimeError((j.get('chart') or {}).get('error'))
    ts=chart.get('timestamp') or [];cl=((((chart.get('indicators') or {}).get('quote') or [{}])[0]).get('close') or [])
    tz,finalize=_market_clock(item['group']);now_local=dt.datetime.now(dt.timezone.utc).astimezone(tz)
    pts=[]
    for stamp,close in zip(ts,cl):
        if close is None:continue
        local_date=dt.datetime.fromtimestamp(stamp,dt.timezone.utc).astimezone(tz).date()
        if item['group'] in ('us','korea') and now_local.time()<finalize and local_date>=now_local.date():continue
        pts.append((stamp,float(close),local_date))
    if len(pts)<2:raise RuntimeError('insufficient completed points')
    a,b=pts[-2],pts[-1]
    return {'ticker':item['ticker'],'name':item['name'],'group':item['group'],'date':b[2].isoformat(),'close':b[1],'change_pct':b[1]/a[1]-1,'source':'海外公开行情','session_complete':True}

def freshness(items,group,benchmark):
    rows=[x for x in items if x.get('group')==group];b=next((x for x in rows if x.get('ticker')==benchmark),None)
    if not b:return {'fresh':False,'date':None,'reason':'基准数据缺失'}
    date=b['date'];bad=[x.get('ticker') for x in rows if x.get('date')!=date]
    return {'fresh':not bad,'date':date,'reason':'' if not bad else '部分成分日期不一致','count':len(rows)}

def period_return(b,n):return b[-1][2]/b[-n-1][2]-1 if len(b)>n and b[-n-1][2] else None

def sector_stats(rows,h):
    groups={}
    for x in rows:groups.setdefault((x['scope'],x['sector']),[]).append(x)
    out={}
    for (scope,sec),items in groups.items():
        one=[];five=[];twenty=[];ma20=[];ma50=[]
        for x in items:
            b=(h.get(x['code']) or {}).get('daily') or []
            if len(b)>=2:one.append(b[-1][2]/b[-2][2]-1)
            five.append(period_return(b,5));twenty.append(period_return(b,20))
            if len(b)>=20:ma20.append(b[-1][2]>=sum(y[2] for y in b[-20:])/20)
            if len(b)>=50:ma50.append(b[-1][2]>=sum(y[2] for y in b[-50:])/50)
        clean=lambda a:[v for v in a if v is not None]
        out[f'{scope}|{sec}']={'count':len(items),'median_1d':statistics.median(clean(one)) if clean(one) else None,'median_5d':statistics.median(clean(five)) if clean(five) else None,'median_20d':statistics.median(clean(twenty)) if clean(twenty) else None,'breadth':sum(v>0 for v in clean(one))/len(clean(one)) if clean(one) else None,'ma20_breadth':sum(ma20)/len(ma20) if ma20 else None,'ma50_breadth':sum(ma50)/len(ma50) if ma50 else None}
    return out

def scope_stats(rows,h,scope):
    one=[];five=[];twenty=[]
    for x in rows:
        if x['scope']!=scope:continue
        bars=(h.get(x['code']) or {}).get('daily') or []
        if len(bars)>=2:one.append(bars[-1][2]/bars[-2][2]-1)
        if (v:=period_return(bars,5)) is not None:five.append(v)
        if (v:=period_return(bars,20)) is not None:twenty.append(v)
    return {'count':len(one),'median_1d':statistics.median(one) if one else None,'median_5d':statistics.median(five) if five else None,'median_20d':statistics.median(twenty) if twenty else None,'breadth':sum(v>0 for v in one)/len(one) if one else None}

def load_latest():
    p=DATA/'latest-v7.json'
    if not p.exists():return {}
    try:return json.loads(p.read_text('utf-8'))
    except Exception:return {}

def atomic_write_text(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            f.write(text);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        try:os.unlink(tmp)
        except FileNotFoundError:pass

def public_index(data):
    return {'schema':INDEX_SCHEMA,'data_schema':DATA_SCHEMA,'release':'V7.9.3','latest':'data/latest-v7.json','snapshot_date':data.get('snapshot_date'),'generated_at_cn':data.get('generated_at_cn'),'coverage':data.get('coverage'),'intraday':data.get('intraday'),'market_freshness':data.get('market_freshness'),'privacy':'仅公开市场与基础信息'}

def write(data):
    DATA.mkdir(parents=True,exist_ok=True);INTRADAY.mkdir(parents=True,exist_ok=True)
    save_snapshot(data)

def update_us(cfg,data):
    wanted=[x for x in cfg['external_market'] if x['group']=='us'];items=[];errors={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        fs={pool.submit(yahoo,x):x for x in wanted}
        for f,x in fs.items():
            try:items.append(f.result())
            except Exception as e:errors[x['ticker']]=repr(e)
    fr=freshness(items,'us','^IXIC');data.setdefault('stale_cache',{})['us']=(data.get('market_context') or {}).get('us',{}).get('items',[]) if errors or not fr['fresh'] else []
    data.setdefault('market_context',{})['us']={'items':items,'status':'正常' if fr['fresh'] else '数据不足'};data.setdefault('market_freshness',{})['us']=fr
    if errors:data.setdefault('errors',{}).update({'us:'+k:v for k,v in errors.items()})

def update_asia(cfg,data):
    rows=cfg['companies'];hist={};errs={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        fs={pool.submit(fetch_history,x):x for x in rows}
        for f,x in fs.items():
            try:k,v=f.result();hist[k]=v
            except Exception as e:errs[x['code']]=repr(e)
    if len(hist)!=len(rows):raise SystemExit(f'K线覆盖不完整 {len(hist)}/{len(rows)}')
    quotes=fetch_quotes(rows)
    if len(quotes)!=len(rows):raise SystemExit(f'报价覆盖不完整 {len(quotes)}/{len(rows)}')
    benchmarks={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        fs={pool.submit(fetch_benchmark,k,v):(k,v) for k,v in BENCH.items()}
        for f,(k,v) in fs.items():
            try:kk,x=f.result();benchmarks[kk]=x
            except Exception as e:errs['benchmark:'+k]=repr(e)
    if len(benchmarks)<4:raise SystemExit('宽基基准覆盖不足 '+json.dumps(errs,ensure_ascii=False))
    intraday_payloads={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        fs={pool.submit(fetch_intraday,x):x for x in rows}
        for f,x in fs.items():
            try:k,v=f.result();intraday_payloads[k]=v
            except Exception as e:errs['intraday:'+x['code']]=repr(e)
    ok=len(intraday_payloads)
    minimum=(len(rows)*95+99)//100
    if ok<minimum:raise SystemExit(f'分时实体覆盖低于95% {ok}/{len(rows)}；拒绝发布')
    expected_files=set()
    for code,payload in intraday_payloads.items():
        p=INTRADAY/(code.replace('.','_')+'.json');expected_files.add(p.name)
        atomic_write_text(p,json.dumps(payload,ensure_ascii=False,separators=(',',':')))
    for p in INTRADAY.glob('*.json'):
        if p.name not in expected_files:p.unlink()
    ext=[];ext_errors={};wanted=[x for x in cfg['external_market'] if x['group']=='korea']
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        fs={pool.submit(yahoo,x):x for x in wanted}
        for f,x in fs.items():
            try:ext.append(f.result())
            except Exception as e:ext_errors[x['ticker']]=repr(e)
    kr=freshness(ext,'korea','^KS11');data.setdefault('stale_cache',{})['korea']=(data.get('market_context') or {}).get('korea',{}).get('items',[]) if ext_errors or not kr['fresh'] else []
    snapshot=max(x['last_date'] for x in hist.values());a_codes=[x['code'] for x in rows if not x['code'].endswith('.HK')];hk_codes=[x['code'] for x in rows if x['code'].endswith('.HK')]
    a_date=benchmarks.get('CSI300',{}).get('last_date');hk_date=benchmarks.get('HSI',{}).get('last_date');a_ok=sum(hist[x]['last_date']==a_date for x in a_codes);hk_ok=sum(hist[x]['last_date']==hk_date for x in hk_codes)
    # 批量实时报价可能在收盘集合竞价前停止更新（港股尤其明显）。正式日K已完成时，
    # 统一使用同源日K收盘作为发布价，避免“15:47报价”冒充港股正式收盘。
    for row in rows:
        code=row['code'];bars=(hist.get(code) or {}).get('daily') or [];quote=quotes.get(code)
        if not quote or len(bars)<2:continue
        expected=hk_date if code.endswith('.HK') else a_date
        if str(bars[-1][0])!=str(expected):continue
        close=float(bars[-1][2]);previous=float(bars[-2][2])
        quote.update({'price':close,'prev_close':previous,'change_pct':close/previous-1 if previous else None,'date':str(expected),'timestamp':str(expected),'source':'腾讯前复权日K正式收盘','session_complete':True})
    available=sorted(intraday_payloads)
    data.update({'schema':DATA_SCHEMA,'snapshot_date':snapshot,'quotes':quotes,'histories':hist,'benchmarks':benchmarks,'sector_stats':sector_stats(rows,hist),'intraday':{'schema':INTRADAY_SCHEMA,'base':'data/intraday/','success':ok,'total':len(rows),'available_codes':available,'status':'complete' if ok==len(rows) else 'partial'}})
    data.setdefault('market_context',{})['china']={'snapshot_date':a_date,'hardware':scope_stats(rows,hist,'hardware'),'application':scope_stats(rows,hist,'application')};data['market_context']['hk']={'snapshot_date':hk_date};data['market_context']['korea']={'items':ext,'status':'正常' if kr['fresh'] else '数据不足'}
    data.setdefault('market_freshness',{}).update({'china':{'fresh':a_ok==len(a_codes),'date':a_date,'coverage':f'{a_ok}/{len(a_codes)}'},'hk':{'fresh':hk_ok==len(hk_codes),'date':hk_date,'coverage':f'{hk_ok}/{len(hk_codes)}'},'korea':kr})
    retained={k:v for k,v in (data.get('errors') or {}).items() if not (k.startswith('intraday:') or k.startswith('korea:') or k.startswith('benchmark:') or k in {x['code'] for x in rows})}
    retained.update(errs);retained.update({'korea:'+k:v for k,v in ext_errors.items()});data['errors']=retained;data['coverage']={'histories':len(hist),'quotes':len(quotes),'intraday':ok,'total':len(rows),'hardware':sum(x['scope']=='hardware' for x in rows),'application':sum(x['scope']=='application' for x in rows),'benchmarks':len(benchmarks)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['all','us','asia'],default='all');args=ap.parse_args();cfg=load_config();data=load_latest();data.setdefault('schema',DATA_SCHEMA);data.setdefault('market_context',{});data.setdefault('market_freshness',{});data.setdefault('errors',{})
    if args.mode in ('all','asia'):update_asia(cfg,data)
    if args.mode in ('all','us'):update_us(cfg,data)
    data.setdefault('snapshot_date',data.get('embedded_snapshot'))
    data['generated_at_cn']=dt.datetime.now(dt.timezone.utc).astimezone(ZoneInfo('Asia/Shanghai')).isoformat();write(data);print(json.dumps({'status':'PASS','mode':args.mode,'snapshot':data.get('snapshot_date'),'coverage':data.get('coverage'),'freshness':data.get('market_freshness')},ensure_ascii=False))
if __name__=='__main__':main()
