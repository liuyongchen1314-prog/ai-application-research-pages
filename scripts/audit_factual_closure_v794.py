#!/usr/bin/env python3
"""V7.9.4 factual-evidence gap audit.

This audit deliberately separates "the program can calculate" from "the facts
needed for a formal valuation are evidenced".  It never upgrades a record.
"""
from __future__ import annotations
import datetime as dt
import json
import pathlib
from collections import Counter
from typing import Any

ROOT=pathlib.Path(__file__).resolve().parents[1]
PUB=ROOT/'docs'/'public_v7'/'data'
LATEST=PUB/'latest-v7.json'
EVIDENCE=PUB/'evidence-audit-v79.json'
MODEL=ROOT/'config'/'valuation_model.json'
OUT_JSON=ROOT/'docs'/'audit'/'V7.9.4_事实证据缺口.json'
OUT_MD=ROOT/'docs'/'audit'/'V7.9.4_事实证据缺口.md'

CHECKS=(
 ('港股币种','14家港股公司元数据币种、估值币种与期限证据'),
 ('法定财报','公司公告/法定披露的正式证据'),
 ('净现金净债务','净现金或净债务原始值及日期'),
 ('少数股东权益','少数股东权益/NCI原始值及日期'),
 ('完全摊薄股本','完全摊薄股本与股本日期'),
 ('ADR转换','ADR/普通股转换比率（仅适用时）'),
 ('EV到每股价值桥','EV→股权价值→完全摊薄每股价值逐项桥'),
 ('拆股除权增发','拆股、除权、配股、增发等公司行动证据'),
 ('扣非净利润','最近法定报告扣非净利润/可比经营利润'),
 ('机构预测日期年度','机构预测真实发布日期与适用年度'),
)

def _companies(data:dict[str,Any])->list[dict[str,Any]]:
    return [*((data.get('companies') or {}).get('hardware') or []),*((data.get('companies') or {}).get('application') or [])]

def _bool(v:Any)->bool:return v is True

def main()->None:
    data=json.loads(LATEST.read_text('utf-8'))
    ea=json.loads(EVIDENCE.read_text('utf-8'))
    model=json.loads(MODEL.read_text('utf-8'))
    companies=_companies(data); valuation=data.get('valuation_current') or {}; financials=data.get('company_financials') or {}
    erows={r['code']:r for r in ea.get('rows') or []}; mrows={r['code']:r for r in model.get('records') or []}
    if len(companies)!=142 or len(valuation)!=142 or len(erows)!=142 or len(mrows)!=142:
        raise SystemExit('事实审计输入不是142家公司同源集合')
    results=[]
    hk_codes=[c['code'] for c in companies if c.get('market')=='港股']
    for c in companies:
        code=c['code']; v=valuation[code]; e=erows[code]; m=mrows[code]; f=financials.get(code) or {}; report=f.get('latest_report') or {}; consensus=f.get('consensus') or {}
        market=c.get('market'); applicable_adr=bool(m.get('adr_conversion_ratio') or v.get('adr_conversion_ratio'))
        currency_meta=bool(c.get('currency'))
        currency_value=bool(v.get('currency'))
        currency_evidence=_bool(e.get('currency_horizon_checked'))
        official=_bool(e.get('official_disclosure'))
        deduct=report.get('deduct_net_profit')
        corp_hash=f.get('corporate_action_hash')
        # The current schema exposes only the existence of an aggregate EV/equity/share bridge.
        # It does not expose the underlying cash/debt/NCI/diluted-share facts separately.
        bridge=_bool(e.get('ev_equity_share_bridge'))
        forecast_date=consensus.get('forecast_date') or v.get('forecast_date')
        years=[consensus.get(k) for k in ('year1','year2','year3') if consensus.get(k) is not None]
        row={
          'code':code,'name':c.get('name'),'scope':c.get('scope'),'market':market,
          'formal_closed':bool(v.get('formal_closed')),'evidence_state':v.get('evidence_state'),
          'checks':{
            '港股币种': {'applicable':market=='港股','passed': (market!='港股') or (currency_meta and currency_value and currency_evidence),
                       'evidence':{'company_currency':c.get('currency'),'valuation_currency':v.get('currency'),'currency_horizon_checked':currency_evidence}},
            '法定财报': {'applicable':True,'passed':official,'evidence':{'official_disclosure':official,'report_date':report.get('report_date') or v.get('report_date'),'report_source':report.get('source')}},
            '净现金净债务': {'applicable':True,'passed':False,'evidence':{'aggregate_ev_bridge':bridge,'raw_net_cash_or_debt_exposed':False},'reason':'当前公开模型未单列可审计的净现金/净债务原始值与日期'},
            '少数股东权益': {'applicable':True,'passed':False,'evidence':{'aggregate_ev_bridge':bridge,'raw_nci_exposed':False},'reason':'当前公开模型未单列可审计的少数股东权益原始值与日期'},
            '完全摊薄股本': {'applicable':True,'passed':False,'evidence':{'aggregate_ev_bridge':bridge,'raw_fully_diluted_shares_exposed':False},'reason':'当前公开模型未单列完全摊薄股本及股本日期'},
            'ADR转换': {'applicable':applicable_adr,'passed':not applicable_adr,'evidence':{'conversion_ratio':m.get('adr_conversion_ratio') or v.get('adr_conversion_ratio')},'reason':'无公开ADR转换字段；非ADR公司记为不适用'},
            'EV到每股价值桥': {'applicable':True,'passed':bridge,'evidence':{'ev_equity_share_bridge':bridge},'reason':'布尔桥接核验不等于现金/债务/NCI/摊薄股本逐项事实闭环'},
            '拆股除权增发': {'applicable':True,'passed':bool(corp_hash),'evidence':{'corporate_action_hash':corp_hash},'reason':'有公司行动哈希才证明该轮抓取已形成可追踪输入；仍需原公告闭环'},
            '扣非净利润': {'applicable':True,'passed':deduct is not None,'evidence':{'deduct_net_profit':deduct,'deduct_net_profit_yoy':report.get('deduct_net_profit_yoy'),'report_date':report.get('report_date')}},
            '机构预测日期年度': {'applicable':True,'passed':bool(forecast_date and years),'evidence':{'forecast_date':forecast_date,'forecast_years':years,'source':consensus.get('source') or (v.get('institution_check') or {}).get('source')}},
          }
        }
        row['unresolved']=[k for k,x in row['checks'].items() if x.get('applicable') and not x.get('passed')]
        results.append(row)
    summary={}
    for name,_ in CHECKS:
        applicable=sum(1 for r in results if r['checks'][name]['applicable'])
        passed=sum(1 for r in results if r['checks'][name]['applicable'] and r['checks'][name]['passed'])
        summary[name]={'passed':passed,'applicable':applicable,'unresolved':applicable-passed}
    payload={
      'schema':'v794-factual-gap-audit-1','generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
      'companies':142,'hardware':sum(c.get('scope')=='hardware' for c in companies),'application':sum(c.get('scope')=='application' for c in companies),
      'hk_companies':len(hk_codes),'hk_codes':hk_codes,'formal_closed':sum(bool(v.get('formal_closed')) for v in valuation.values()),
      'evidence_audit_coverage':ea.get('coverage'),'summary':summary,'rows':results,
      'conclusion':'程序一致性不等于事实闭环。存在任一事实缺口的公司不得升级为正式估值；本审计只暴露缺口，不反推或修改合理价值。'
    }
    OUT_JSON.parent.mkdir(parents=True,exist_ok=True); OUT_JSON.write_text(json.dumps(payload,ensure_ascii=False,indent=2),'utf-8')
    lines=['# V7.9.4 事实证据缺口审计','',f'- 公司：142（硬件 {payload["hardware"]} / 应用 {payload["application"]}）',f'- 港股：{len(hk_codes)}',f'- 正式证据完全闭环：{payload["formal_closed"]}/142','- 原则：程序算得通 ≠ 事实证据闭环；本文件不会升级估值。','', '| 项目 | 通过/适用 | 未闭环 | 说明 |','|---|---:|---:|---|']
    desc=dict(CHECKS)
    for name,_ in CHECKS:
        s=summary[name]; lines.append(f'| {name} | {s["passed"]}/{s["applicable"]} | {s["unresolved"]} | {desc[name]} |')
    lines += ['','## 港股币种特别说明','', '14 家港股公司在公司元数据中标为 HKD；但只有当估值记录自身币种字段与 `currency_horizon_checked` 证据同时存在时才视为闭环。当前不能用“元数据写了 HKD”替代正式证据。','', '## 仍需人工/一级证据完成的工作','', '- 港股币种与估值期限逐家核对；法定财报原文；净现金/净债务；少数股东权益；完全摊薄股本；ADR（适用时）转换。','- EV→股权价值→每股价值逐项桥；拆股/除权/配股/增发；扣非净利润；机构预测真实发布日期与适用年度。','- 未闭环项目只能保留“研究区间/暂不估算/待补证”语义，不得包装成正式目标价。']
    OUT_MD.write_text('\n'.join(lines)+'\n','utf-8')
    print(json.dumps({'status':'PASS','formal_closed':payload['formal_closed'],'hk':len(hk_codes),'summary':summary},ensure_ascii=False))

if __name__=='__main__':main()
