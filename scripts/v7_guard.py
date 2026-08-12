#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, datetime as dt, email.utils, html, json, pathlib, re, sys, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from snapshot_io import save_snapshot
ROOT=pathlib.Path(__file__).resolve().parents[1]
LATEST=ROOT/'docs'/'public_v7'/'data'/'latest-v7.json'

def save(data):
    save_snapshot(data)

def market(mode):
    import update_market_v7 as m
    for p in (m.DATA,m.INTRADAY):p.mkdir(parents=True,exist_ok=True)
    old=sys.argv;sys.argv=[old[0],'--mode',mode]
    try:m.main()
    finally:sys.argv=old

TENCENT_HEAD={'User-Agent':'Mozilla/5.0','Referer':'https://gu.qq.com/'}
def tencent_text(url,timeout=12,encoding='gbk'):
    last=None
    for i in range(2):
        try:
            req=urllib.request.Request(url,headers=TENCENT_HEAD)
            with urllib.request.urlopen(req,timeout=timeout) as r:return r.read().decode(encoding,errors='replace')
        except Exception as e:last=e;time.sleep(.4*(i+1))
    raise RuntimeError(repr(last))

def tencent_fund_today(rows):
    out={}
    sym2code={r['symbol']:r['code'] for r in rows}
    for start in range(0,len(rows),35):
        group=rows[start:start+35]
        qs=','.join('ff_'+r['symbol'] for r in group)
        try:text=tencent_text('https://qt.gtimg.cn/q='+qs)
        except Exception:continue
        for line in text.splitlines():
            if '="' not in line:continue
            lhs,raw=line.split('="',1);raw=raw.rsplit('"',1)[0];sym=lhs.replace('v_ff_','').strip();a=raw.split('~');code=sym2code.get(sym)
            if not code or len(a)<14:continue
            try:
                main=float(a[3])*10000.0;small=float(a[7])*10000.0;total=float(a[9])*10000.0;date=str(a[13]).strip();
                if len(date)==8:date=f'{date[:4]}-{date[4:6]}-{date[6:]}'
                out[code]={'date':date,'main':main,'small':small,'medium':0.0,'large':0.0,'super':0.0,'main_pct':float(a[4]) if a[4] else 0.0,'small_pct':float(a[8]) if a[8] else 0.0,'close':None,'change_pct':None,'source':'腾讯公开资金流（当日备用）'}
            except Exception:continue
    return out

def merge_today(existing,row):
    arr=list((existing or {}).get('daily') or [])
    arr=[x for x in arr if str(x.get('date') if isinstance(x,dict) else x[0])!=row['date']]
    arr.append(row);arr.sort(key=lambda x:str(x.get('date') if isinstance(x,dict) else x[0]))
    return arr[-100:]

def fund():
    import update_fundflow_v7 as m
    if not LATEST.exists():raise SystemExit('latest-v7.json missing')
    data=json.loads(LATEST.read_text('utf-8'));rows=[x for x in m.load_config()['companies'] if x['code'].endswith(('.SH','.SZ'))];existing=dict(data.get('fund_flows') or {});out={};east_errors={};east_ok=False
    # 先用一家公司做快速探测。接口被整批限流时不再对128家公司重复等待。
    try:
        k,v=m.fetch(rows[0]);out[k]=v;east_ok=True
    except Exception as e:east_errors[rows[0]['code']]=repr(e)
    if east_ok:
        rest=rows[1:]
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            fs={pool.submit(m.fetch,x):x for x in rest}
            for f,x in fs.items():
                try:k,v=f.result();out[k]=v
                except Exception as e:east_errors[x['code']]=repr(e)
    # 腾讯当日资金作为独立备用；即便东方财富可用，也用于补空洞。
    tq=tencent_fund_today(rows)
    for x in rows:
        code=x['code']
        if code in out:continue
        if code in tq:
            arr=merge_today(existing.get(code),tq[code]);out[code]={'daily':arr,'last_date':tq[code]['date'],'source':'腾讯公开资金流（当日备用）','identity_note':'按订单大小划分，只作为大单/小单代理，不代表真实机构或散户身份'}
        elif code in existing:
            # 只保留为缓存，不计入“当前覆盖”。
            out[code]=existing[code]
    active_date=data.get('snapshot_date');current=sum(1 for code,x in out.items() if str(x.get('last_date') or ((x.get('daily') or [{}])[-1].get('date') if isinstance((x.get('daily') or [{}])[-1],dict) else ''))==str(active_date))
    hist5=sum(1 for x in out.values() if len(x.get('daily') or [])>=5)
    status='正常' if current>=int(len(rows)*.90) else '部分可用' if current>=int(len(rows)*.50) else '数据不足'
    data['fund_flows']=out;data['fund_flow_summary']={'coverage_current':current,'coverage_total_cache':len(out),'history_5d':hist5,'total_a_share':len(rows),'status':status,'primary_source':'东方财富公开资金流','fallback_source':'腾讯公开资金流（当日）','note':'大单/小单是订单规模代理。当前数据不足时不参与5/10日买点评分。'}
    err={k:v for k,v in (data.get('errors') or {}).items() if not k.startswith('fund:')};err.update({'fund:'+k:v for k,v in east_errors.items()});data['errors']=err;save(data)
    print(json.dumps({'status':'PASS','fund_status':status,'current':current,'cache':len(out),'history5':hist5,'total':len(rows),'eastmoney_ok':east_ok,'tencent_today':len(tq)},ensure_ascii=False))

HEAD={'User-Agent':'Mozilla/5.0 (compatible; AI-Research-V7/1.0)'}
RISK_QUERIES=[
('AI网络 / 光互连 / CPO','China optical transceiver FCC BIS ban restriction Reuters',('optical','transceiver','photonics','cpo')),
('AI芯片 / ASIC / 端侧算力','China AI chip BIS export control restriction Reuters',('ai chip','gpu','accelerator','asic','semiconductor chip')),
('先进制程 / 设备 / 材料 / 封装','China semiconductor equipment export control restriction Reuters',('semiconductor equipment','chipmaking equipment','etch','deposition','lithography')),
('HBM / 存储 / 内存接口','HBM DRAM NAND China restriction ban Reuters',('hbm','dram','nand','memory chip')),
('智算中心运营 / IDC','China data center power regulation restriction Reuters',('data center','datacenter','colocation')),
('AI安全','China AI cybersecurity regulation investigation Reuters',('cybersecurity','cyber security')),
('大模型与平台入口','China AI model regulation copyright investigation Reuters',('ai model','generative ai','large language model','copyright'))
]
RISK_WORDS={'sanction':'制裁','export control':'出口管制','ban':'限制/禁令','restriction':'限制','entity list':'实体清单','tariff':'关税','lawsuit':'诉讼','regulation':'监管规则','copyright':'版权风险','investigation':'调查','probe':'调查','recall':'召回','outage':'服务中断'}
VERIFIED_RISK={'id':'20260804-cpo-us-risk','date':'2026-08-04','level':'R1','sector':'AI网络 / 光互连 / CPO','title':'美国正在研究限制部分中国数据中心设备','summary':'路透社报道美国正在研究针对部分中国数据中心设备、包括新型光模块的限制方案；目前仍处于方案阶段，规则可能修改或取消。','source':'路透社','url':'https://www.reuters.com/world/trump-administration-drafting-ban-chinese-data-center-devices-sources-say-2026-08-04/','official':False,'reflected_in_earnings':False}

def http(url,timeout=18):
    last=None
    for i in range(3):
        try:
            req=urllib.request.Request(url,headers=HEAD)
            with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()
        except Exception as e:last=e;time.sleep(.6*(i+1))
    raise RuntimeError(repr(last))

def rss(raw):
    root=ET.fromstring(raw);out=[]
    for it in root.findall('.//item')[:25]:
        title=html.unescape(it.findtext('title') or '').strip();link=it.findtext('link') or '';publisher=(it.findtext('source') or '').strip();pub=it.findtext('pubDate') or ''
        try:date=email.utils.parsedate_to_datetime(pub).date().isoformat()
        except Exception:date=''
        out.append({'title_raw':title,'url':link,'publisher':publisher,'date':date})
    return out

def risk_source(z):
    q=z.lower()
    if 'reuters' in q:return '路透社'
    if 'bloomberg' in q:return '彭博社'
    if 'federal register' in q:return '美国联邦公报'
    if 'fcc' in q:return '美国联邦通信委员会'
    if 'commerce' in q or 'bis' in q:return '美国商务部'
    return '公开新闻源'

def risk_level(z):
    q=z.lower();official=any(x in q for x in ('fcc.gov','bis.gov','commerce.gov','federalregister.gov','ustr.gov','sec.gov')) or any(x in q for x in ('federal register','federal communications commission','bureau of industry and security'))
    trusted=('reuters' in q or 'bloomberg' in q)
    if official:return 'R2'
    if trusted and any(k in q for k in RISK_WORDS):return 'R1'
    return 'R0'

def cn_summary(sector,z):
    q=z.lower();hits=[cn for en,cn in RISK_WORDS.items() if en in q];topic='、'.join(dict.fromkeys(hits)) or '潜在政策/经营变化'
    obj='相关产业'
    if 'optical' in q or 'transceiver' in q:obj='光模块/光互连'
    elif 'semiconductor' in q or 'chip' in q:obj='半导体/AI芯片'
    elif 'hbm' in q or 'dram' in q or 'nand' in q:obj='存储/HBM'
    elif 'data center' in q:obj='数据中心'
    elif 'copyright' in q:obj='AI内容版权'
    return f'发现与{obj}有关的{topic}信息，需继续核对正式文件和公司实际业务影响。'

def risk():
    data=json.loads(LATEST.read_text('utf-8'));today=dt.date.today();events=[VERIFIED_RISK.copy()];errors={}
    for sector,q,required in RISK_QUERIES:
        url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':q,'hl':'en-US','gl':'US','ceid':'US:en'})
        try:rows=rss(http(url))
        except Exception as e:errors[sector]=repr(e);continue
        for r in rows:
            try:age=(today-dt.date.fromisoformat(r['date'])).days if r['date'] else 999
            except Exception:age=999
            if age>14:continue
            title=(r.get('title_raw') or '').lower();
            if not any(k in title for k in required):continue
            z=' '.join((r['title_raw'],r['url'],r.get('publisher','')));lv=risk_level(z)
            if lv=='R0':continue
            events.append({'id':re.sub(r'\W+','-',sector+r['date']+r['title_raw'])[:120],'date':r['date'],'level':lv,'sector':sector,'title':'相关产业出现新的政策/监管风险信息','summary':cn_summary(sector,z),'source':risk_source(z),'url':r['url'],'official':lv=='R2','reflected_in_earnings':False,'raw_title_backend_only':r['title_raw']})
    rank={'R2':2,'R1':1};seen=set();uniq=[]
    for e in sorted(events,key=lambda x:(rank.get(x['level'],0),x['date']),reverse=True):
        k=e.get('id') or (e['sector'],e['date'],e['source'],e['summary'])
        if k in seen:continue
        seen.add(k);uniq.append(e)
    data['risk_events']=uniq[:80];data['risk_monitor_summary']={'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'events':len(uniq),'errors':errors,'rule':'一级=可信媒体待确认；二级=官方拟议/调查。每个板块必须命中自身业务对象关键词；低相关结果直接丢弃。无正式业务影响时不直接修改EPS。'};save(data)
    print(json.dumps({'status':'PASS','events':len(uniq),'errors':len(errors),'verified_seed':any(x.get('id')==VERIFIED_RISK['id'] for x in uniq)},ensure_ascii=False))

def validate(mode):
    import validate_v7 as v
    old=sys.argv;sys.argv=[old[0],'--mode',mode]
    try:v.main()
    finally:sys.argv=old
    d=json.loads(LATEST.read_text('utf-8'));cov=d.get('coverage') or {}
    if mode in ('all','asia') and int(cov.get('intraday') or 0)<int(142*.95):raise SystemExit(f'分时覆盖低于95% {cov.get("intraday")}/142')
    print(json.dumps({'status':'STRICT_PASS','mode':mode,'intraday':cov.get('intraday'),'fund_flow_status':(d.get('fund_flow_summary') or {}).get('status'),'fund_current':(d.get('fund_flow_summary') or {}).get('coverage_current')},ensure_ascii=False))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('task',choices=['market','fund','risk','validate']);ap.add_argument('--mode',choices=['all','us','asia'],default='all');a=ap.parse_args()
    {'market':lambda:market(a.mode),'fund':fund,'risk':risk,'validate':lambda:validate(a.mode)}[a.task]()
if __name__=='__main__':main()
