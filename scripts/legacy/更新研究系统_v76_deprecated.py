#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, datetime as dt, gzip, base64, json, math, pathlib, statistics, time, urllib.parse, urllib.request, csv
from zoneinfo import ZoneInfo

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; HIST=DATA/'历史'; INTRA=DATA/'分时'
CONFIG_B64=(ROOT/'config'/'公司估值配置.b64').read_text(encoding='ascii').strip()
CFG=json.loads(gzip.decompress(base64.b64decode(CONFIG_B64)).decode('utf-8'))
COMPANIES=CFG['公司']
HEAD={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/144 Safari/537.36','Referer':'https://gu.qq.com/'}

def symbol(code:str)->str:
    a,b=code.split('.')
    return ('sh'+a if b=='SH' else 'sz'+a if b=='SZ' else 'hk'+a.zfill(5))

def request(url,timeout=25):
    last=None
    for i in range(4):
        try:
            req=urllib.request.Request(url,headers=HEAD)
            with urllib.request.urlopen(req,timeout=timeout) as r:
                return r.read().decode('utf-8','replace')
        except Exception as e:
            last=e; time.sleep(.7*(i+1))
    raise RuntimeError(repr(last))

def qfq_history(code,count=700):
    s=symbol(code)
    url='https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?'+urllib.parse.urlencode({'param':f'{s},day,,,{count},qfq'})
    j=json.loads(request(url)); node=(j.get('data') or {}).get(s) or {}; src=node.get('qfqday') or node.get('day') or []
    out=[]
    for x in src:
        if len(x)<6: continue
        try: out.append([str(x[0]),float(x[1]),float(x[2]),float(x[3]),float(x[4]),float(x[5])])
        except Exception: pass
    if not out: raise RuntimeError('日线为空')
    return out

def completed_bars(bars):
    now=dt.datetime.now(ZoneInfo('Asia/Shanghai'))
    today=now.date().isoformat()
    if now.time()<dt.time(16,30) and bars and bars[-1][0]>=today:
        bars=[x for x in bars if x[0]<today]
    if not bars: raise RuntimeError('没有已完成交易日日线')
    return bars

def five_day_intraday(code,snapshot):
    s=symbol(code)
    url=f'https://web.ifzq.gtimg.cn/appstock/app/day/query?code={urllib.parse.quote(s)}'
    j=json.loads(request(url,18)); node=(j.get('data') or {}).get(s) or {}; root=node.get('data') or {}
    days=root if isinstance(root,list) else (root.get('data') or [] if isinstance(root,dict) else [])
    if isinstance(days,dict): days=days.get('data') or []
    out=[]
    for day in days:
        if not isinstance(day,dict): continue
        d=str(day.get('date') or '')
        dkey=''.join(ch for ch in d if ch.isdigit())
        skey=''.join(ch for ch in snapshot if ch.isdigit())
        if dkey!=skey: continue
        rows=day.get('data') or []
        if isinstance(rows,dict): rows=rows.get('data') or []
        if isinstance(rows,str): rows=rows.replace('\n','|').split('|')
        for line in rows:
            p=str(line).split(' ')
            if len(p)>=3:
                try: out.append([d,p[0],float(p[1]),float(p[2])])
                except Exception: pass
    if not out: raise RuntimeError('目标交易日分时为空')
    return out

def avg(a): return sum(a)/len(a) if a else None

def sma(a,n,off=0):
    e=len(a)-off
    return avg(a[e-n:e]) if e>=n else None

def period_return(b,n):
    return b[-1][2]/b[-n-1][2]-1 if len(b)>n and b[-n-1][2] else None

def rank_pct(vals):
    a=sorted((v,k) for k,v in vals.items() if isinstance(v,(int,float)) and math.isfinite(v)); n=len(a)
    return {k:100*(i/(n-1) if n>1 else 1) for i,(v,k) in enumerate(a)}

def valuation_position(p,lo,hi):
    if p<lo*.85:return '明显低估'
    if p<lo:return '合理偏低'
    if p<=hi:return '合理区间'
    if p<=hi*1.15:return '偏高观察'
    return '明显偏高'

def analyze(bars,rs):
    if len(bars)<220:return {'阶段':'历史不足','通过':0,'严格':False,'收缩':'暂不判断','突破':None,'止损':None}
    cl=[x[2] for x in bars]; hi=[x[3] for x in bars]; lo=[x[4] for x in bars]; vo=[x[5] for x in bars]; p=cl[-1]
    m50,m150,m200,m200o=sma(cl,50),sma(cl,150),sma(cl,200),sma(cl,200,20)
    n=min(252,len(bars)); h52=max(hi[-n:]); l52=min(lo[-n:])
    checks=[p>m150 and p>m200,m150>m200,m200o is not None and m200>m200o,m50>m150 and m50>m200,p>m50,p>=l52*1.30,p>=h52*.75,(rs or 0)>=70]
    passed=sum(checks); strict=all(checks)
    stage='第二阶段确认' if strict else ('第二阶段候选' if passed>=6 and p>m200 else ('弱势阶段' if p<m200 and m200o is not None and m200<m200o else '整理过渡'))
    blocks=[]
    for a,b in [(-65,-45),(-45,-25),(-25,-5)]:
        mid=statistics.median(cl[a:b]); blocks.append(((max(hi[a:b])-min(lo[a:b]))/mid if mid else 99,avg(vo[a:b])))
    r=[x[0] for x in blocks]; vv=[x[1] for x in blocks]
    contract=r[0]>r[1]*1.05 and r[1]>r[2]*1.05; dry=vv[2]<vv[0]*.85
    pivot=max(hi[-21:-1]); av20=avg(vo[-21:-1]); br=p>pivot and vo[-1]>=av20*1.25; near=p>=h52*.85
    shape='确认突破' if contract and dry and br else ('形成中' if contract and dry and near else ('候选' if contract or (r[2]<r[0]*.75 and near) else '未形成'))
    stop=max(min(lo[-15:]),pivot*.93)
    return {'阶段':stage,'通过':passed,'严格':strict,'收缩':shape,'突破':pivot,'止损':stop}

def fmt(v):
    if v is None:return '—'
    return f'{v:.0f}' if abs(v)>=100 else (f'{v:.1f}' if abs(v)>=10 else f'{v:.2f}')

def build():
    if len(COMPANIES)!=142 or len({x['代码'] for x in COMPANIES})!=142: raise SystemExit('公司池不是142家唯一公司')
    histories={}; errors={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        fut={pool.submit(qfq_history,x['代码']):x for x in COMPANIES}
        for f,x in fut.items():
            try: histories[x['代码']]=completed_bars(f.result())
            except Exception as e: errors[x['代码']]=repr(e)
    if len(histories)!=142: raise SystemExit(f'日线覆盖不足 {len(histories)}/142: '+json.dumps(errors,ensure_ascii=False))
    dates={v[-1][0] for v in histories.values()}
    if len(dates)!=1: raise SystemExit('142家公司日线日期不一致: '+repr(sorted(dates)))
    snapshot=next(iter(dates))
    rets={}
    for x in COMPANIES:
        b=histories[x['代码']]
        if len(b)>=220:
            back=min(252,len(b)-1); rets[x['代码']]=b[-1][2]/b[-1-back][2]-1
    ranks=rank_pct(rets)
    sec20={}; groups={}
    for x in COMPANIES: groups.setdefault((x['范围'],x['板块']),[]).append(x['代码'])
    for k,codes in groups.items():
        vals=[period_return(histories[c],20) for c in codes]; vals=[v for v in vals if v is not None]
        sec20[k]=statistics.median(vals) if vals else None
    secr=rank_pct(sec20); rows=[]
    for x in COMPANIES:
        code=x['代码']; b=histories[code]; p=b[-1][2]; prev=b[-2][2] if len(b)>1 else p; tech=analyze(b,ranks.get(code)); sr=secr.get((x['范围'],x['板块']))
        sec_strength='未知' if sr is None else ('强' if sr>=70 else ('中' if sr>=35 else '弱'))
        pos=valuation_position(p,x['下限'],x['上限']); acceptable=pos in {'明显低估','合理偏低','合理区间'}
        if x['估值状态']=='低置信度研究区间': action='暂不参与'; reason='已有数值研究区间，但关键估值证据仍需继续交叉核验'
        elif x['估值状态']=='条件估值区间': action='条件观察'; reason='估值为条件区间，暂不进入正式买入候选'
        elif not acceptable: action='观察'; reason='当前价格相对合理估值区间偏高'
        elif not tech['严格']: action='观察'; reason='估值可接受，但尚未满足完整第二阶段趋势条件'
        elif tech['收缩']=='确认突破' and sec_strength!='弱': action='可买候选'; reason='估值可接受、第二阶段确认、波动收缩后突破，且板块不弱'
        elif tech['收缩'] in {'形成中','候选'} and sec_strength!='弱': action='等待触发'; reason='估值和趋势通过，但买点尚未完全确认'
        else: action='观察'; reason='趋势较强，但波动收缩或板块条件不足'
        if action in {'可买候选','等待触发'}:
            entry=f"{fmt(tech['突破'])}–{fmt(tech['突破']*1.05)}" if tech['收缩']=='确认突破' else f"等待有效突破 {fmt(tech['突破'])}"
            invalid=f"跌破 {fmt(tech['止损'])} 重新评估；不向下摊低成本"
        else: entry=invalid='—'
        rows.append({'代码':code,'公司':x['公司'],'范围':x['范围'],'板块':x['板块'],'数据日期':snapshot,'最新价':p,'涨跌幅':p/prev-1 if prev else None,'合理下限':x['下限'],'合理上限':x['上限'],'合理估值范围':f"{fmt(x['下限'])}–{fmt(x['上限'])}",'估值状态':x['估值状态'],'置信度':x['置信度'],'估值位置':pos,'趋势阶段':tech['阶段'],'趋势条件':tech['通过'],'相对强弱':ranks.get(code),'波动收缩':tech['收缩'],'板块强弱':sec_strength,'行动':action,'入场条件':entry,'失效条件':invalid,'原因':reason})
    INTRA.mkdir(parents=True,exist_ok=True); intra_ok=0; intra_err={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        fut={pool.submit(five_day_intraday,x['代码'],snapshot):x for x in COMPANIES}
        for f,x in fut.items():
            try:
                z=f.result(); (INTRA/(x['代码'].replace('.','_')+'.json')).write_text(json.dumps({'代码':x['代码'],'日期':snapshot,'分时':z},ensure_ascii=False,separators=(',',':')),encoding='utf-8'); intra_ok+=1
            except Exception as e: intra_err[x['代码']]=repr(e)
    if intra_ok<135: raise SystemExit(f'分时覆盖低于95% {intra_ok}/142')
    out={'版本':'公开完整发布版','数据日期':snapshot,'生成时间':dt.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'公司数量':142,'估值覆盖':142,'分时覆盖':intra_ok,'估值状态统计':dict(__import__('collections').Counter(r['估值状态'] for r in rows)),'行动统计':dict(__import__('collections').Counter(r['行动'] for r in rows)),'公司':rows,'说明':'所有公司均显示数值合理估值范围；低置信度区间不代表正式估值通过，技术信号不能反向抬高合理价值。'}
    return out,histories

def page(out):
    rows=json.dumps(out['公司'],ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    stats=json.dumps(out['行动统计'],ensure_ascii=False)
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>人工智能全产业链研究系统</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f4f7fa;color:#172431;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}}header{{background:#173d5c;color:white;padding:16px}}.w{{max-width:1580px;margin:auto;padding:0 12px}}h1{{font-size:23px;margin:0}}.sub{{font-size:13px;opacity:.88;margin-top:5px}}.cards{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:12px 0}}.c{{background:white;border:1px solid #dae2e8;border-radius:10px;padding:10px}}.c b{{display:block;font-size:20px}}.c span{{font-size:12px;color:#667686}}.note{{line-height:1.65;font-size:13px}}.tools{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}}.tools input,.tools select{{padding:9px;border:1px solid #d6dfe6;border-radius:8px;background:white;min-width:170px}}.box{{background:white;border:1px solid #dae2e8;border-radius:10px;overflow:auto}}table{{border-collapse:collapse;width:100%;min-width:1500px}}th,td{{padding:8px;border-bottom:1px solid #edf1f4;text-align:left;vertical-align:top;font-size:12px}}th{{background:#eaf0f5;position:sticky;top:0}}.n{{font-weight:800;font-size:14px}}.muted{{color:#6d7d8c}}.tag{{display:inline-block;padding:3px 7px;border-radius:999px;background:#edf2f6}}.buy{{background:#e7f5ee;color:#176c52}}.wait{{background:#fff3d9;color:#8a5c0c}}.off{{background:#f0f1f3;color:#6b7280}}.risk{{background:#fff0f0;color:#a52e35}}.range{{font-weight:800;color:#8a5c0c;white-space:nowrap}}.foot{{font-size:12px;color:#667686;line-height:1.65;margin:12px 0 28px}}
@media(max-width:720px){{header{{padding:13px 4px}}h1{{font-size:19px}}.cards{{grid-template-columns:repeat(2,1fr)}}.tools>*{{flex:1;min-width:0!important}}.box{{border:0;background:transparent;overflow:visible}}table,tbody,tr,td{{display:block;width:100%}}table{{min-width:0}}thead{{display:none}}tr{{background:white;border:1px solid #dae2e8;border-radius:10px;margin:9px 0;padding:5px}}td{{display:grid;grid-template-columns:42% 58%;border-bottom:1px solid #f0f3f5;padding:7px}}td:before{{content:attr(data-label);color:#71808e;font-size:11px;padding-right:7px}}td:first-child{{grid-template-columns:1fr}}td:first-child:before{{display:none}}}}
</style></head><body><header><div class="w"><h1>人工智能全产业链 · 估值与交易研究系统</h1><div class="sub">数据日期 {out['数据日期']} · 142家公司全部显示合理估值范围 · 收盘后自动更新</div></div></header><main class="w"><div id="cards" class="cards"></div><div class="c note"><b>阅读规则：</b>合理估值范围与交易入场条件是两件事。低置信度研究区间仍给出数字，但关键证据未完全闭环时标记“暂不参与”；技术走势只能决定什么时候参与，不能反向抬高公司的合理价值。</div><div class="tools"><input id="q" placeholder="搜索公司、代码、板块"><select id="scope"><option value="">全部产业链</option><option>人工智能硬件</option><option>人工智能应用</option></select><select id="act"><option value="">全部行动</option><option>可买候选</option><option>等待触发</option><option>观察</option><option>条件观察</option><option>暂不参与</option></select></div><div class="box"><table><thead><tr><th>公司</th><th>最新价</th><th>合理估值范围</th><th>估值状态</th><th>估值位置</th><th>趋势阶段</th><th>趋势条件</th><th>相对强弱</th><th>波动收缩</th><th>板块强弱</th><th>行动</th><th>入场条件</th><th>失效条件</th><th>原因</th></tr></thead><tbody id="tb"></tbody></table></div><div class="foot">区间来自前期估值审计链；低置信度公司后续继续用公司公告、东方财富、同花顺和机构研报交叉修正。任何区间和交易状态都不是收益承诺。每笔交易先定义风险，只在盈利后考虑加仓，不向亏损仓位摊低成本。</div></main><script>
const R={rows},A={stats};const $=s=>document.querySelector(s);function e(v){{return String(v??'').replace(/[&<>"']/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[m]))}}function n(v){{return typeof v==='number'?v.toLocaleString('zh-CN',{{maximumFractionDigits:2}}):'—'}}function p(v){{return typeof v==='number'?`${{v>=0?'+':''}}${{(v*100).toFixed(1)}}%`:'—'}}function tag(t){{let c=t==='可买候选'?'buy':t==='等待触发'?'wait':t==='暂不参与'?'off':(t==='偏高观察'||t==='明显偏高')?'risk':'';return `<span class="tag ${{c}}">${{e(t)}}</span>`}}function card(){{let x=[['公司总数',142],['估值区间覆盖',142],['可买候选',A.可买候选||0],['等待触发',A.等待触发||0],['暂不参与',A.暂不参与||0]];$('#cards').innerHTML=x.map(z=>`<div class="c"><span>${{z[0]}}</span><b>${{z[1]}}</b></div>`).join('')}}function filtered(){{let q=$('#q').value.trim().toLowerCase(),s=$('#scope').value,a=$('#act').value;return R.filter(r=>(!q||(`${{r.公司}} ${{r.代码}} ${{r.板块}}`).toLowerCase().includes(q))&&(!s||r.范围===s)&&(!a||r.行动===a))}}function render(){{let x=filtered();$('#tb').innerHTML=x.map(r=>`<tr><td data-label="公司"><div class="n">${{e(r.公司)}}</div><div class="muted">${{e(r.代码.split('.')[0])}} · ${{e(r.板块)}}</div></td><td data-label="最新价"><b>${{n(r.最新价)}}</b><div>${{p(r.涨跌幅)}}</div></td><td data-label="合理估值范围" class="range">${{e(r.合理估值范围)}}</td><td data-label="估值状态">${{tag(r.估值状态)}}<div class="muted">置信度：${{e(r.置信度)}}</div></td><td data-label="估值位置">${{tag(r.估值位置)}}</td><td data-label="趋势阶段">${{tag(r.趋势阶段)}}</td><td data-label="趋势条件">${{r.趋势条件||0}}/8</td><td data-label="相对强弱">${{typeof r.相对强弱==='number'?r.相对强弱.toFixed(0):'—'}}</td><td data-label="波动收缩">${{tag(r.波动收缩)}}</td><td data-label="板块强弱">${{tag(r.板块强弱)}}</td><td data-label="行动">${{tag(r.行动)}}</td><td data-label="入场条件">${{e(r.入场条件)}}</td><td data-label="失效条件">${{e(r.失效条件)}}</td><td data-label="原因">${{e(r.原因)}}</td></tr>`).join('');document.body.dataset.ready=String(x.length);document.body.dataset.total='142'}}card();render();['q','scope','act'].forEach(i=>$(`#${{i}}`).addEventListener(i==='q'?'input':'change',render));
</script></body></html>'''

def write(out,histories):
    DATA.mkdir(parents=True,exist_ok=True); HIST.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(out,ensure_ascii=False,separators=(',',':'))
    (DATA/'最新研究数据.json').write_text(raw,encoding='utf-8')
    (HIST/f"{out['数据日期']}.json").write_text(raw,encoding='utf-8')
    with (DATA/'交易总表.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['代码','公司','范围','板块','数据日期','最新价','涨跌幅','合理下限','合理上限','合理估值范围','估值状态','置信度','估值位置','趋势阶段','趋势条件','相对强弱','波动收缩','板块强弱','行动','入场条件','失效条件','原因']
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows({k:r.get(k) for k in fields} for r in out['公司'])
    (ROOT/'index.html').write_text(page(out),encoding='utf-8')
    (DATA/'日线.json').write_text(json.dumps({k:v for k,v in histories.items()},ensure_ascii=False,separators=(',',':')),encoding='utf-8')

def main():
    out,histories=build(); write(out,histories)
    print(json.dumps({'状态':'通过','数据日期':out['数据日期'],'公司':142,'估值覆盖':142,'分时覆盖':out['分时覆盖'],'行动统计':out['行动统计']},ensure_ascii=False))
if __name__=='__main__': main()
