#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,json,re
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads(gzip.decompress(base64.b64decode((ROOT/'config/公司估值配置.b64').read_text().strip())).decode('utf-8'))
DATA=ROOT/'data/最新研究数据.json'; PAGE=ROOT/'index.html'

def fail(x): raise SystemExit(x)

class Visible(HTMLParser):
    def __init__(self): super().__init__(); self.skip=0; self.parts=[]
    def handle_starttag(self,t,a):
        if t in {'script','style'}: self.skip+=1
    def handle_endtag(self,t):
        if t in {'script','style'} and self.skip: self.skip-=1
    def handle_data(self,d):
        if not self.skip:self.parts.append(d)

def main():
    c=CFG.get('公司') or []
    if len(c)!=142 or len({x['代码'] for x in c})!=142: fail('估值配置不是142家唯一公司')
    if any(not isinstance(x.get('下限'),(int,float)) or not isinstance(x.get('上限'),(int,float)) or x['下限']>=x['上限'] for x in c): fail('存在空白或异常估值区间')
    sc={k:sum(x['估值状态']==k for x in c) for k in {'已审计估值区间','条件估值区间','低置信度研究区间'}}
    if sc!={'已审计估值区间':65,'条件估值区间':1,'低置信度研究区间':76}: fail('65/1/76估值状态发生漂移: '+repr(sc))
    if not DATA.exists() or not PAGE.exists(): fail('发布数据或网页尚未生成')
    d=json.loads(DATA.read_text(encoding='utf-8')); rows=d.get('公司') or []
    if len(rows)!=142 or d.get('估值覆盖')!=142: fail('最终数据未达到142/142估值覆盖')
    if any(r.get('合理下限') is None or r.get('合理上限') is None or not r.get('合理估值范围') for r in rows): fail('最终页面数据仍有空白估值范围')
    if any(r.get('行动')=='可买候选' and r.get('估值状态')!='已审计估值区间' for r in rows): fail('低置信度或条件估值越过交易门')
    if any(r.get('估值状态')=='低置信度研究区间' and r.get('行动')!='暂不参与' for r in rows): fail('低置信度公司未保持暂不参与')
    text=PAGE.read_text(encoding='utf-8')
    v=Visible();v.feed(text);visible=' '.join(v.parts)
    if '冻结' in visible: fail('可见网页仍出现“冻结”')
    bad=re.findall(r'[A-Za-z]{5,}',visible)
    if bad: fail('可见网页仍有长串英文: '+','.join(sorted(set(bad))[:10]))
    for word in ['合理估值范围','暂不参与','波动收缩','失效条件','人工智能全产业链']:
        if word not in visible: fail('网页缺少中文关键字段: '+word)
    if d.get('分时覆盖',0)<135: fail('分时覆盖低于95%')
    print(json.dumps({'状态':'通过','公司':142,'估值覆盖':142,'估值状态':sc,'分时覆盖':d['分时覆盖'],'数据日期':d['数据日期'],'行动统计':d.get('行动统计')},ensure_ascii=False))
if __name__=='__main__': main()
