#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt,email.utils,html,json,pathlib,re,time,urllib.parse,urllib.request,xml.etree.ElementTree as ET
from snapshot_io import save_snapshot
ROOT=pathlib.Path(__file__).resolve().parents[1];LATEST=ROOT/'docs'/'public_v7'/'data'/'latest-v7.json';HEAD={'User-Agent':'Mozilla/5.0 (compatible; AI-Research-V7/1.0)'}
QUERIES=[('AI网络 / 光互连 / CPO','China optical transceiver FCC BIS export restriction Reuters'),('AI芯片 / ASIC / 端侧算力','China AI chip BIS export control Reuters'),('先进制程 / 设备 / 材料 / 封装','China semiconductor equipment export control BIS Reuters'),('HBM / 存储 / 内存接口','HBM DRAM NAND China restriction price Reuters'),('智算中心运营 / IDC','China data center power regulation Reuters'),('AI安全','China AI cybersecurity regulation Reuters'),('大模型与平台入口','China AI model regulation copyright Reuters')]
WORDS={'sanction':'制裁','export control':'出口管制','ban':'限制/禁令','restriction':'限制','entity list':'实体清单','tariff':'关税','lawsuit':'诉讼','regulation':'监管规则','copyright':'版权风险','investigation':'调查','probe':'调查','recall':'召回','outage':'服务中断'}
OFFICIAL=('fcc.gov','bis.gov','commerce.gov','federalregister.gov','ustr.gov','sec.gov');TRUSTED=('reuters.com','bloomberg.com')
def get(url,timeout=18):
 last=None
 for i in range(3):
  try:
   req=urllib.request.Request(url,headers=HEAD)
   with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()
  except Exception as e:last=e;time.sleep(.6*(i+1))
 raise RuntimeError(repr(last))
def parse(raw):
 root=ET.fromstring(raw);out=[]
 for it in root.findall('.//item')[:20]:
  title=html.unescape(it.findtext('title') or '').strip();link=it.findtext('link') or '';pub=it.findtext('pubDate') or ''
  try:date=email.utils.parsedate_to_datetime(pub).date().isoformat()
  except Exception:date=''
  out.append({'title_raw':title,'url':link,'date':date})
 return out
def source(title,url):
 z=(title+' '+url).lower()
 if 'reuters' in z:return'路透社'
 if 'bloomberg' in z:return'彭博社'
 if 'federal register' in z:return'美国联邦公报'
 if 'fcc' in z:return'美国联邦通信委员会'
 if 'commerce' in z or 'bis' in z:return'美国商务部'
 return'公开新闻源'
def level(title,url):
 z=(title+' '+url).lower()
 if any(d in z for d in OFFICIAL):return'R2'
 if any(d in z for d in TRUSTED) and any(k in z for k in WORDS):return'R1'
 return'R0'
def summary(title):
 z=title.lower();hits=[cn for en,cn in WORDS.items() if en in z];topic='、'.join(dict.fromkeys(hits)) or '潜在政策/经营变化'
 if 'optical' in z or 'transceiver' in z:obj='光模块/光互连'
 elif 'semiconductor' in z or 'chip' in z:obj='半导体/AI芯片'
 elif 'hbm' in z or 'dram' in z or 'nand' in z:obj='存储/HBM'
 elif 'data center' in z:obj='数据中心'
 elif 'copyright' in z:obj='AI内容版权'
 else:obj='相关产业'
 return f'发现与{obj}有关的{topic}信息，需继续核对正式文件和公司实际业务影响。'
def main():
 if not LATEST.exists():raise SystemExit('latest-v7.json missing')
 data=json.loads(LATEST.read_text('utf-8'));today=dt.date.today();events=[];errors={}
 for sector,q in QUERIES:
  url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':q,'hl':'en-US','gl':'US','ceid':'US:en'})
  try:rows=parse(get(url))
  except Exception as e:errors[sector]=repr(e);continue
  for r in rows:
   try:age=(today-dt.date.fromisoformat(r['date'])).days if r['date'] else 999
   except Exception:age=999
   if age>14:continue
   lv=level(r['title_raw'],r['url'])
   if lv=='R0':continue
   events.append({'id':re.sub(r'\W+','-',sector+r['date']+r['title_raw'])[:120],'date':r['date'],'level':lv,'sector':sector,'title':'相关产业出现新的政策/监管风险信息','summary':summary(r['title_raw']),'source':source(r['title_raw'],r['url']),'url':r['url'],'official':lv=='R2','reflected_in_earnings':False,'raw_title_backend_only':r['title_raw']})
 rank={'R3':3,'R2':2,'R1':1,'R0':0};seen=set();unique=[]
 for e in sorted(events,key=lambda x:(rank.get(x['level'],0),x['date']),reverse=True):
  k=(e['sector'],e['date'],e['summary'])
  if k in seen:continue
  seen.add(k);unique.append(e)
 data['risk_events']=unique[:80]
 data['risk_monitor_summary']={'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'events':len(unique),'errors':errors,'rule':'R1可信媒体；R2官方拟议/调查。无正式业务影响时不直接修改EPS。'}
 save_snapshot(data)
 print(json.dumps({'status':'PASS','events':len(unique),'errors':len(errors)},ensure_ascii=False))
if __name__=='__main__':main()
