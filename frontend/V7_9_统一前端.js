/* AI研究系统 V7.9.4 统一前端：前端仅展示/排序；估值与策略字段禁止二次计算。 */

const D=window.__V7_DATA__;
const BUILD={version:'V7.9.4',builtAt:new Date().toISOString()};

/* V7.9：保留V7.6完整能力，并由统一运行层提供唯一前端入口。 */
let chooseMagicPeriod, dbGet, dbPut, deriveAttribution, drawCurrentChart, evaluateWeekLine, fetchFirst, gateState, loadCache, loadCompanyOnline, mergeLive, openDetailKline, refreshAllData, refreshPublicHardware, renderCurrent, renderDetail, renderIntraday, renderKline, renderMarketContext, renderSector, renderSepa, renderValuation, saveCache, selectChart, selectedWeekLine, updateStatus;
let scope='hardware',tab='valuation',signalFilter='all',chart=null,chartCode=null,period='day',detailIndex=0,detailCodes=[],selectedChainNode=null;
let liveMeta={source:'内置发布快照',snapshot:D.embedded_snapshot||latestPriceDate(),generated:D.generated_at};
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const num=v=>v==null||Number.isNaN(+v)?'—':(+v).toLocaleString('zh-CN',{maximumFractionDigits:2});
const pct=v=>v==null||Number.isNaN(+v)?'—':`${v>=0?'+':''}${(+v*100).toFixed(2)}%`;
const classFor=v=>v>0?'up':v<0?'down':'neutral';
const uniq=a=>[...new Set((a||[]).filter(Boolean))];
const NORMAL_TABS=[['valuation','估值总表'],['strategy','操作策略'],['sector','板块强弱＋个股'],['sepa','SEPA阶段'],['kline','K线'],['daily','每日涨跌归因'],['chain','产业链地图'],['operations','我的操作检查']];
const FULL_TABS=[['chain-overview','产业链总览'],['strategy','操作策略'],['chain-roadmap','技术与需求路线'],['chain-flow','上下游传导'],['chain-clock','投资时钟'],['chain-companies','公司与板块'],['chain-learn','学习中心']];
const CHAIN_STAGES=[
 {id:'resource',name:'上上游：能源、材料与基础条件',desc:'决定AI基础设施能否落地的物理约束。',sectors:['液冷 / 电源 / AI电力系统','其他AI硬件基础设施']},
 {id:'semi',name:'上游：半导体、存储与核心芯片',desc:'先进制程、设备材料、HBM和ASIC决定单位算力成本与交付。',sectors:['先进制程 / 设备 / 材料 / 封装','HBM / 存储 / 内存接口','AI芯片 / ASIC / 端侧算力']},
 {id:'infra',name:'中游：服务器、网络、IDC与智算中心',desc:'把芯片组成可持续运行的算力，并运营机房、电力和网络容量。',sectors:['AI服务器 / 算力基础设施','智算中心运营 / IDC','AI服务器PCB / 覆铜板','高速铜缆 / 连接器','AI网络 / 交换芯片 / 设备','AI网络 / 光互连 / CPO']},
 {id:'operate',name:'运行层：可观测性、AIOps与智能诊断',desc:'监测应用、模型、GPU、日志、调用链和故障，把物理算力变成稳定服务。',sectors:['AI可观测性 / AIOps / 智能运维']},
 {id:'platform',name:'平台层：模型、云与Agent工具链',desc:'把算力转化为模型能力、开发接口和工作流。',sectors:['大模型与平台入口','AI Agent／企业智能体','AI数据与知识服务']},
 {id:'apps',name:'下游：软件与行业应用',desc:'把模型能力转成可验证收入、付费和现金流。',sectors:['AI办公与生产力工具','企业软件／ERP／SaaS','AI营销与广告','AI内容生成','AI游戏','AI教育','AI医疗','AI金融','AI安全','工业与垂直行业应用']},
 {id:'physical',name:'终端与物理AI',desc:'AI从屏幕走向设备、机器人和消费终端。',sectors:['物理AI核心硬件','消费端AI应用']}
];
const NODE_LIBRARY={
 '智算中心运营 / IDC':{doing:'建设并运营机房、电力、网络和高功率容量，为云与AI客户提供可持续算力环境。',bottleneck:'供电指标、建设周期、上架率、资本开支、负债与电力成本。',driver:'云厂和企业AI算力部署、高功率机柜需求。',leading:'新增预订MW、在运营容量、上架率、调整后EBITDA、净债务/EBITDA。',clock:'预订先行、投产随后、利用率和现金回报最终验证；不能只看在建容量。'},
 'AI可观测性 / AIOps / 智能运维':{doing:'监测指标、日志、调用链、模型、Agent和基础设施，发现故障并辅助根因诊断与自动修复。',bottleneck:'数据接入、产品标准化、续费、跨客户复制和AI诊断可靠性。',driver:'AI系统复杂度、GPU成本、停机损失和合规要求上升。',leading:'ARR/软件收入、付费客户、续费率、毛利率、销售效率、现金流和故障自动化覆盖。',clock:'PoC不等于收入；当产品收入、续费和经营现金流同步改善时，才从主题观察转向经营验证。'},

 '液冷 / 电源 / AI电力系统':{doing:'解决高功率机柜的供电、散热和稳定运行。',bottleneck:'高压直流、液冷可靠性、数据中心并网周期。',driver:'机柜功率密度上升与AI集群扩容。',leading:'云厂资本开支、液冷渗透率、单柜功率、在手订单。',clock:'订单和产能同步上修、板块宽度扩散时研究；只靠主题脉冲时不追。'},
 '其他AI硬件基础设施':{doing:'承接数据中心建设中尚未单列的机房与配套环节。',bottleneck:'项目周期长、回款和资本开支效率。',driver:'数据中心新建与改造。',leading:'项目招标、开工率、应收账款和现金流。',clock:'先验证订单与现金流，避免只看概念。'},
 '先进制程 / 设备 / 材料 / 封装':{doing:'提供AI芯片制造、先进封装和关键材料。',bottleneck:'设备国产化、良率、先进封装产能与验证周期。',driver:'GPU/ASIC扩产和国产替代。',leading:'设备招标、验证进度、产能利用率、先进封装扩产。',clock:'订单先行、收入确认随后；设备材料通常早于晶圆产量反映景气。'},
 'HBM / 存储 / 内存接口':{doing:'为训练和推理提供高带宽存储与高速接口。',bottleneck:'HBM良率、堆叠封装、产能和供货认证。',driver:'模型参数和推理并发提升。',leading:'HBM价格、库存、产能扩张、主流厂商指引。',clock:'价格与订单共同上行时更强；价格上涨但终端需求弱需防库存周期反转。'},
 'AI芯片 / ASIC / 端侧算力':{doing:'提供训练、推理和端侧计算核心。',bottleneck:'先进制程、软件生态、客户验证与量产。',driver:'云厂自研芯片、国产替代和端侧模型。',leading:'流片、量产、客户导入、软件生态和毛利率。',clock:'量产和收入确认比发布会更重要。'},
 'AI服务器 / 算力基础设施':{doing:'把芯片、存储、网络和电源组成可交付算力。',bottleneck:'关键器件供给、交付节奏和客户集中度。',driver:'云厂和运营商资本开支。',leading:'服务器出货、ODM指引、订单、库存与应收。',clock:'出货加速且库存健康时研究龙头；订单增长但现金流恶化要降级。'},
 'AI服务器PCB / 覆铜板':{doing:'承载高速信号和高功率连接。',bottleneck:'高层数、高频高速材料、良率和认证。',driver:'服务器代际升级与交换机速率提升。',leading:'高阶板占比、扩产、稼动率、ASP和毛利率。',clock:'产品结构升级比单纯产能扩张更关键。'},
 '高速铜缆 / 连接器':{doing:'在短距离高速互连中连接服务器和交换机。',bottleneck:'高速损耗、散热、可靠性和客户认证。',driver:'机柜内高速连接和scale-up网络。',leading:'800G/1.6T认证、订单、连接器价值量。',clock:'铜与光并非简单替代，按距离和架构看份额。'},
 'AI网络 / 交换芯片 / 设备':{doing:'负责集群内部数据交换和网络调度。',bottleneck:'交换芯片、软件栈和大规模网络稳定性。',driver:'集群规模扩大和训练效率要求。',leading:'端口速率、交换机出货、网络资本开支。',clock:'网络通常在GPU交付后仍有补配需求，观察订单持续性。'},
 'AI网络 / 光互连 / CPO':{doing:'解决大规模集群的高速、低功耗远距离互连。',bottleneck:'光芯片、DSP、良率、客户认证和1.6T放量。',driver:'800G向1.6T升级、集群规模和带宽需求。',leading:'云厂指引、1.6T出货、ASP、份额、良率。',clock:'龙头率先创新高且板块宽度扩散更可靠；只靠单股拉升不算行业确认。'},
 '大模型与平台入口':{doing:'提供基础模型、云平台和用户入口。',bottleneck:'推理成本、模型能力、分发和合规。',driver:'开发者调用、企业采用和消费者入口。',leading:'Token调用、云收入、活跃用户、单位推理成本。',clock:'收入和毛利改善确认后，才从“期权”转为可估值业务。'},
 'AI Agent／企业智能体':{doing:'把模型接入企业流程，自动完成多步骤任务。',bottleneck:'可靠性、权限、数据接入和责任边界。',driver:'企业降本增效与工作流自动化。',leading:'付费客户、部署周期、续费率、单客收入。',clock:'PoC多但收入少时只观察；复制速度和续费提高后再上调。'},
 'AI数据与知识服务':{doing:'提供训练、检索、知识库和数据治理。',bottleneck:'数据质量、版权、隐私和更新成本。',driver:'RAG、Agent和企业知识管理。',leading:'合同负债、项目标准化程度、毛利率。',clock:'从项目制走向标准化订阅才有估值提升。'},
 'AI办公与生产力工具':{doing:'提升写作、会议、表格和协作效率。',bottleneck:'付费意愿、留存和与原产品的增量区分。',driver:'个人和企业席位升级。',leading:'AI付费率、ARPU、活跃和续费。',clock:'用户增长不等于收入，优先看付费和留存。'},
 '企业软件／ERP／SaaS':{doing:'把AI嵌入企业核心业务系统。',bottleneck:'数据迁移、交付周期和客户预算。',driver:'企业数字化升级与降本。',leading:'ARR、续费率、合同负债、经营现金流。',clock:'现金流和续费率比一次性订单更重要。'},
 'AI营销与广告':{doing:'优化素材生成、投放和转化。',bottleneck:'归因准确性、平台政策和同质化。',driver:'广告主ROI提升。',leading:'广告收入、转化率、客户留存、流量成本。',clock:'毛利改善与客户留存同时出现才算商业化。'},
 'AI内容生成':{doing:'生成文字、图片、视频和音频。',bottleneck:'版权、内容质量、推理成本和平台分发。',driver:'内容生产效率与用户需求。',leading:'付费用户、生成量、成本、版权支出。',clock:'先看单位经济性，避免只看下载量。'},
 'AI游戏':{doing:'用于研发提效、NPC和内容生成。',bottleneck:'产品周期、用户体验和监管。',driver:'研发降本与新玩法。',leading:'流水、研发费用率、上线节奏和留存。',clock:'AI叙事必须落到产品和流水。'},
 'AI教育':{doing:'个性化学习、题库和教学辅助。',bottleneck:'获客成本、合规和效果验证。',driver:'学习效率与教育数字化。',leading:'付费转化、续费、获客成本和政策。',clock:'政策与现金流门必须同时通过。'},
 'AI医疗':{doing:'辅助诊断、科研、药物和医院流程。',bottleneck:'审批、临床验证、数据合规和支付方。',driver:'医疗效率与新药研发。',leading:'注册证、医院覆盖、订单和回款。',clock:'临床/审批证据优先于模型演示。'},
 'AI金融':{doing:'用于投研、风控、客服和交易基础设施。',bottleneck:'合规、数据安全和错误责任。',driver:'金融机构降本与风险控制。',leading:'机构客户、合同负债、合规进展。',clock:'项目可复制与回款质量是关键。'},
 'AI安全':{doing:'保护模型、数据、身份和企业网络。',bottleneck:'攻击变化快、预算归属和产品验证。',driver:'AI扩大攻击面和合规要求。',leading:'ARR、净留存、合同负债和安全事件。',clock:'安全需求刚性，但仍需确认收入兑现。'},
 '工业与垂直行业应用':{doing:'将AI用于制造、能源、交通等具体流程。',bottleneck:'行业数据、交付周期和定制化。',driver:'提质、降本和少人化。',leading:'标杆客户复制、项目毛利、回款。',clock:'从单项目复制到行业产品化时价值提升。'},
 '物理AI核心硬件':{doing:'为机器人和智能设备提供执行、感知和控制硬件。',bottleneck:'量产、可靠性、成本和供应链。',driver:'机器人、智能车和自动化设备。',leading:'定点、量产、出货、BOM价值量。',clock:'样机不等于订单，量产与现金流确认后再提高权重。'},
 '消费端AI应用':{doing:'通过手机、穿戴和个人应用触达用户。',bottleneck:'入口、留存、付费和隐私。',driver:'终端换机与个人效率需求。',leading:'DAU、留存、付费率、渠道成本。',clock:'爆款下载后要看30/90日留存和付费。'}
};
function allCompanies(){return [...D.companies.hardware,...D.companies.application]}
function totalCompanies(){return allCompanies().length}
function list(){return scope==='full'?allCompanies():D.companies[scope]}
function latestPriceDate(){return allCompanies().map(c=>c.price_date).filter(Boolean).sort().at(-1)||D.embedded_snapshot||'未知'}
function priceDateCoverage(ds){return allCompanies().filter(c=>String(c.price_date||'')===String(ds||'')).length}
function dateAgeDays(ds){if(!ds)return 999;const d=new Date(ds+'T00:00:00+08:00');return Math.floor((Date.now()-d.getTime())/86400000)}
function isStale(ds){return dateAgeDays(ds)>3}
function filtered(){const q=($('#search')?.value||'').trim().toLowerCase(),sec=$('#sectorFilter')?.value||'';return list().filter(c=>(!q||[c.name,c.code,c.sector,c.subsector].join(' ').toLowerCase().includes(q))&&(!sec||c.sector===sec))}
function median(a){a=a.filter(x=>x!=null&&!Number.isNaN(+x)).map(Number).sort((x,y)=>x-y);if(!a.length)return null;const m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2}
function rangeNumbers(s){return (String(s||'').match(/\d+(?:\.\d+)?/g)||[]).map(Number)}
function rangeStatus(c){const n=rangeNumbers(c.current);if(n.length<2||c.price==null)return c.valuation_status||'区间待核验';const [lo,hi]=n;const mid=(lo+hi)/2,p=+c.price;if(p<lo)return`低于当前区间 ${((lo-p)/lo*100).toFixed(1)}%`;if(p>hi)return`高于当前区间 ${((p-hi)/hi*100).toFixed(1)}%`;if(Math.abs(p-mid)/mid<.08)return'位于当前区间中枢附近';return p<mid?'位于当前区间下半部':'位于当前区间上半部'}
function history(code){return (D.histories[code]?.daily||[]).filter(r=>Array.isArray(r)&&r.length>=6)}
function retN(rows,n){return rows.length>n?rows.at(-1)[2]/rows.at(-1-n)[2]-1:null}
function avg(a){a=a.filter(x=>x!=null&&!Number.isNaN(+x));return a.length?a.reduce((x,y)=>x+(+y),0)/a.length:null}
function moving(rows,n,key=2){return rows.length>=n?avg(rows.slice(-n).map(x=>x[key])):null}
function calcCompanyTech(c){const r=history(c.code),last=r.at(-1),close=last?.[2],vol=last?.[5],ma20=moving(r,20),ma50=moving(r,50),ma150=moving(r,150),ma200=moving(r,200),v20=moving(r.slice(0,-1),20,5),high20=r.length?Math.max(...r.slice(-20).map(x=>x[3])):null;return{rows:r,last,close,vol,ma20,ma50,ma150,ma200,v20,volRatio:v20&&vol?vol/v20:null,r5:retN(r,5),r20:retN(r,20),nearHigh:high20&&close?close/high20-1:null}}
function calcSectorStats(items){const groups={};items.forEach(c=>(groups[c.sector]??=[]).push(c));return Object.entries(groups).map(([sector,rows])=>{const ts=rows.map(calcCompanyTech),r1=rows.map(c=>c.change),r5=ts.map(x=>x.r5),vol=ts.map(x=>x.volRatio),ma20Breadth=ts.filter(x=>x.ma20&&x.close>=x.ma20).length/(ts.filter(x=>x.ma20).length||1),ma50Breadth=ts.filter(x=>x.ma50&&x.close>=x.ma50).length/(ts.filter(x=>x.ma50).length||1),highBreadth=ts.filter(x=>x.nearHigh!=null&&x.nearHigh>=-.05).length/(ts.filter(x=>x.nearHigh!=null).length||1),leaders=[...rows].sort((a,b)=>(calcCompanyTech(b).r5??-99)-(calcCompanyTech(a).r5??-99)).slice(0,3);return{sector,count:rows.length,median1:median(r1),median5:median(r5),breadth:r1.filter(x=>x>0).length/(r1.filter(x=>x!=null).length||1),volumeRatio:median(vol),ma20Breadth,ma50Breadth,highBreadth,leaders,positive:rows.filter(x=>x.signal?.direction==='positive').length,risk:rows.filter(x=>x.signal?.direction==='risk').length}}).sort((a,b)=>(b.median5??-99)-(a.median5??-99))}
function renderTabs(){const tabs=scope==='full'?FULL_TABS:NORMAL_TABS;$('#subtabs').innerHTML=tabs.map(([id,label])=>`<button class="main-tab ${tab===id?'active':''}" data-tab="${id}">${label}</button>`).join('');$$('.main-tab').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;renderTabs();renderCurrent()})}
function populateSector(){const s=uniq(list().map(c=>c.sector)).sort();$('#sectorFilter').innerHTML='<option value="">全部细分板块</option>'+s.map(x=>`<option>${esc(x)}</option>`).join('')}
function setScope(s){scope=s;tab=s==='full'?'chain-overview':'valuation';selectedChainNode=null;$$('.scope-btn').forEach(b=>b.classList.toggle('active',b.dataset.scope===s));populateSector();renderTabs();renderCurrent()}
function init(){registerCustomIndicators();$$('.scope-btn').forEach(b=>b.onclick=()=>setScope(b.dataset.scope));$('#search').oninput=renderCurrent;$('#sectorFilter').onchange=renderCurrent;$('#refreshBtn').onclick=()=>refreshAllData({manual:true}).catch(()=>{});$('#deepRefreshBtn').onclick=()=>refreshAllHistories({manual:true});$$('.period-btn').forEach(b=>b.onclick=e=>setPeriod(e.currentTarget.dataset.period));$$('.filter-btn').forEach(b=>b.onclick=e=>{signalFilter=e.currentTarget.dataset.filter;$$('.filter-btn').forEach(x=>x.classList.toggle('active',x===e.currentTarget));renderAttribution()});['ma5','ma10','ma20','ma50','ma150','ma200','toggleBoll','toggleVcp','weekLineVisible','toggleVol','toggleMacd','toggleRsi','toggleKdj','toggleDmi'].forEach(id=>$('#'+id).onchange=drawCurrentChart);$('#weekMaSelect').onchange=drawCurrentChart;$('#weekMaSelect').onkeydown=e=>{if(!['ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();const opts=[...e.currentTarget.options],step=e.key==='ArrowDown'?1:-1,next=Math.max(0,Math.min(opts.length-1,e.currentTarget.selectedIndex+step));e.currentTarget.selectedIndex=next;e.currentTarget.dispatchEvent(new Event('change',{bubbles:true}))};$('#detailPrev').onclick=()=>moveDetail(-1);$('#detailNext').onclick=()=>moveDetail(1);$('#detailKline').onclick=openDetailKline;$('#detailBack').onclick=closeDetail;$('#modal').onclick=e=>{if(e.target.id==='modal')closeDetail()};$('#opEvaluate').onclick=e=>{e.preventDefault();evaluateOperation()};$('#opSave').onclick=e=>{e.preventDefault();saveOperation()};$('#opCompany').onchange=fillOperationCompany;loadCache();populateSector();renderTabs();syncIndicatorControls();renderCurrent();updateStatus();setTimeout(()=>refreshAllData({silent:true}).catch(()=>{}),350);window.__V7_LEGACY_TIMERS__=[];window.addEventListener('online',()=>refreshAllData({silent:true}).catch(()=>{}));document.addEventListener('visibilitychange',()=>{if(!document.hidden){refreshAllData({silent:true}).catch(()=>{});checkDailyDeepRefresh()}});setTimeout(checkDailyDeepRefresh,1200)}
function renderCurrentBase(){['valuation','strategy','sector','sepa','kline','daily','chain','operations'].forEach(id=>$('#panel-'+id)?.classList.remove('active'));$('#commonControls').classList.toggle('hidden',scope==='full'&&!['chain-companies','strategy'].includes(tab));if(scope==='full'&&tab==='strategy'){$('#panel-strategy').classList.add('active');renderStrategy();return}if(scope==='full'){$('#panel-chain').classList.add('active');renderFullChain();return}const p=tab==='chain'?'chain':tab;$('#panel-'+p)?.classList.add('active');if(tab==='valuation')renderValuation();else if(tab==='strategy')renderStrategy();else if(tab==='sector')renderSector();else if(tab==='sepa')renderSepa();else if(tab==='kline')renderKline();else if(tab==='daily')renderAttribution();else if(tab==='chain')renderIndustryMap();else if(tab==='operations')renderOperations();}

function strategyFor(c){return D.strategy_current?.[typeof c==='string'?c:c?.code]||{}}
function strategyNumber(v,digits=2){return v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v))?Number(v).toLocaleString('zh-CN',{maximumFractionDigits:digits}):'—'}
function strategyRange(s){
  if(s.first_buy_zone_low!==null&&s.first_buy_zone_low!==undefined&&s.first_buy_zone_high!==null&&s.first_buy_zone_high!==undefined&&Number.isFinite(Number(s.first_buy_zone_low))&&Number.isFinite(Number(s.first_buy_zone_high)))return `${strategyNumber(s.first_buy_zone_low)}–${strategyNumber(s.first_buy_zone_high)}`;
  if(s.action==='已持仓继续持有')return '持仓管理｜不新增';
  if(s.action==='已持仓减仓或退出')return '减仓/退出管理｜不新增';
  if(s.action==='不追/回避')return '回避｜不设买入区';
  return '触发条件未满足｜当前不买';
}
let strategyActionFilter='all';
function strategyRows(){return filtered().map(c=>({c,s:strategyFor(c)})).filter(x=>x.s.action&&(strategyActionFilter==='all'||x.s.action===strategyActionFilter))}
function renderStrategy(){
  const root=$('#strategyContent');if(!root)return;
  const actions=['重点参与','小仓试错','临近触发','突破后确认','缩量回踩观察','普通候选','等待趋势修复','不追/回避','已持仓继续持有','已持仓减仓或退出'];
  const allRows=filtered().map(c=>({c,s:strategyFor(c)})).filter(x=>x.s.action),rows=strategyRows();
  const counts=Object.fromEntries(actions.map(a=>[a,allRows.filter(x=>x.s.action===a).length]));
  const markets=['A股','港股','美股','韩国'];
  const marketOf=c=>/\.SH$|\.SZ$|\.BJ$/.test(c.code)?'A股':/\.HK$/.test(c.code)?'港股':/\.KS$|\.KQ$/.test(c.code)?'韩国':'美股';
  const cmp=(a,b)=>v794CanonicalCompare(a.c,b.c);
  const marketBlocks=markets.map(m=>{
    const marketRows=rows.filter(x=>marketOf(x.c)===m);if(!marketRows.length)return'';
    const sectors=uniq(marketRows.map(x=>x.c.sector)).sort((a,b)=>{
      const ar=marketRows.filter(x=>x.c.sector===a),br=marketRows.filter(x=>x.c.sector===b);
      return Math.max(...br.map(x=>+x.s.sector_score||0))-Math.max(...ar.map(x=>+x.s.sector_score||0));
    });
    return `<section class="strategy-market"><div class="strategy-market-title"><h2>${m}</h2><span>${marketRows.length}家公司</span></div>${sectors.map(sec=>{const secRows=marketRows.filter(x=>x.c.sector===sec).sort(cmp);return `<div class="strategy-sector"><div class="strategy-sector-title"><h3>${esc(sec)}</h3><span>${secRows.length}家</span></div><div class="strategy-company-grid">${secRows.map(({c,s})=>`<article class="strategy-company action-${esc(s.action)}"><div class="strategy-company-head"><button class="company-link" data-strategy-detail="${esc(c.code)}">${esc(c.name)}</button><span class="strategy-action">${esc(s.action)}</span></div><div class="strategy-price"><b>${strategyNumber(c.price)}</b><span>${esc(c.code)}｜盘中价 ${esc(c.price_date||'—')}｜策略基准 ${esc(s.reference_price_date||s.snapshot_date||'—')}</span></div><div class="strategy-levels"><div><span>当前买点</span><b>${strategyNumber(s.buy_point_score,0)}分</b></div><div><span>趋势质量</span><b>${strategyNumber(s.trend_quality_score,0)}分｜${esc(s.trend_stage||'数据不足')}</b></div><div><span>第一买入区</span><b>${strategyRange(s)}</b></div><div><span>突破位</span><b>${strategyNumber(s.breakout_level)}</b></div><div><span>首次仓位</span><b>${esc(s.initial_position||'—')}</b></div><div><span>止损位</span><b>${strategyNumber(s.stop_loss)}</b></div></div><p>${esc(s.reason||'等待证据更新')}</p><p class="small muted">阻断：${esc((s.blockers||[]).join('；')||'无硬阻断')}｜数据完整度 ${strategyNumber(s.data_completeness,0)}｜12/6/3月RS ${strategyNumber(s.technical?.relative_strength_12m,0)}/${strategyNumber(s.technical?.relative_strength_6m,0)}/${strategyNumber(s.technical?.relative_strength_3m,0)}</p><details><summary>加仓、减仓与失效条件</summary><dl><dt>加仓</dt><dd>${esc(s.add_condition||'—')}</dd><dt>减仓</dt><dd>${esc(s.reduce_condition||'—')}</dd><dt>失效</dt><dd>${esc(s.invalidation||'—')}</dd><dt>风险收益比</dt><dd>${Number.isFinite(+s.risk_reward_ratio)?(+s.risk_reward_ratio).toFixed(2):'当前不可计算'}</dd></dl></details></article>`).join('')}</div></div>`}).join('')}</section>`;
  }).join('');
  const order=(D.strategy_meta?.sort_contract||[]).join(' → ');
  root.innerHTML=`<div class="card strategy-overview"><div><span class="v74-eyebrow">市场门禁 → 板块 → 公司 → 买点</span><h2>独立操作策略</h2><p>策略只使用后台唯一结果。盘中价格可先变化，但行动、趋势和止损仍明确标注其正式收盘基准日；未满足事先触发条件就不买。</p><p class="small muted">默认排序：${esc(order||'行动优先级 → 趋势阶段 → 趋势质量 → RS → 枢轴距离 → 形态质量 → 公司质量 → 代码')}</p></div><div class="strategy-counts">${actions.map(a=>`<button class="strategy-count ${strategyActionFilter===a?'active':''}" data-strategy-action="${esc(a)}"><b>${counts[a]||0}</b>${a}</button>`).join('')}</div></div><div class="card strategy-filter"><b>行动筛选</b><button class="chip-btn ${strategyActionFilter==='all'?'active':''}" data-strategy-action="all">全部 ${allRows.length}</button>${actions.map(a=>`<button class="chip-btn ${strategyActionFilter===a?'active':''}" data-strategy-action="${esc(a)}">${esc(a)} ${counts[a]||0}</button>`).join('')}<span class="small muted">当前显示 ${rows.length} 家</span></div>${marketBlocks||'<div class="card empty">当前筛选下没有公司</div>'}`;
  root.querySelectorAll('[data-strategy-action]').forEach(b=>b.onclick=()=>{strategyActionFilter=b.dataset.strategyAction;renderStrategy()});
  root.querySelectorAll('[data-strategy-detail]').forEach(b=>b.onclick=()=>openDetail(b.dataset.strategyDetail,rows.map(x=>x.c.code)));
}
function getCompany(code){return allCompanies().find(c=>c.code===code)}

function selectChartBase(code){chartCode=code;$$('#klineList .company-item').forEach(b=>b.classList.toggle('active',b.dataset.code===code));drawCurrentChart();loadCompanyOnline(code,{silent:true}).then(()=>{if(chartCode===code)drawCurrentChart()})}
function toBars(rows){return rows.map(r=>({timestamp:Date.parse(r[0]+'T00:00:00+08:00'),open:+r[1],close:+r[2],high:+r[3],low:+r[4],volume:+r[5],turnover:+(r[6]||0)}))}
function isoWeekKey(ds){const [y,m,d]=ds.split('-').map(Number),dt=new Date(Date.UTC(y,m-1,d)),day=dt.getUTCDay()||7;dt.setUTCDate(dt.getUTCDate()+4-day);const year=dt.getUTCFullYear(),yearStart=new Date(Date.UTC(year,0,1)),week=Math.ceil((((dt-yearStart)/86400000)+1)/7);return `${year}-W${String(week).padStart(2,'0')}`}
function weekly(rows){const g=[];let key=null,w=null;rows.forEach(r=>{const k=isoWeekKey(r[0]);if(k!==key){if(w)g.push(w);key=k;w=[r[0],r[1],r[2],r[3],r[4],r[5],r[6]||0]}else{w[2]=r[2];w[3]=Math.max(w[3],r[3]);w[4]=Math.min(w[4],r[4]);w[5]+=r[5];w[6]+=(r[6]||0)}});if(w)g.push(w);return g}
function registerCustomIndicators(){try{if(!klinecharts.getSupportedIndicators().includes('MAGIC'))klinecharts.registerIndicator({name:'MAGIC',shortName:'神奇支撑线',series:'price',calcParams:[10],precision:2,shouldOhlc:true,figures:[{key:'magic',title:'Magic: ',type:'line'}],calc:(data,ind)=>{const n=Math.max(1,Math.round(ind.calcParams[0]||10));let sum=0;return data.map((x,i)=>{sum+=x.close;const out={};if(i>=n-1){out.magic=sum/n;sum-=data[i-(n-1)].close}return out})}});if(!klinecharts.getSupportedIndicators().includes('VCPMARK'))klinecharts.registerIndicator({name:'VCPMARK',shortName:'VCP枢轴',series:'price',calcParams:[0,20],precision:2,figures:[{key:'pivot',title:'VCP Pivot: ',type:'line'}],calc:(data,ind)=>{const p=+ind.calcParams[0]||0,n=Math.max(1,Math.round(ind.calcParams[1]||20));return data.map((x,i)=>i>=data.length-n&&p?{pivot:p}:{})}})}catch(e){console.warn('custom indicator register',e)}}
 
 

function detectVcp(rows){if(rows.length<60)return{state:'数据不足',reason:'至少需要60根日K',pivot:null};const x=rows.slice(-90),range=n=>{const z=x.slice(-n),hi=Math.max(...z.map(r=>r[3])),lo=Math.min(...z.map(r=>r[4]));return(hi-lo)/hi},r40=range(40),r20=range(20),r10=range(10),r5=range(5),v5=avg(x.slice(-5).map(r=>r[5])),v20=avg(x.slice(-20).map(r=>r[5])),pivot=Math.max(...x.slice(-20,-1).map(r=>r[3])),last=x.at(-1),contract=r40>r20&&r20>r10&&r10>=r5*.85,volDry=v5<v20*.82,confirmed=last[2]>pivot&&last[5]>v20*1.2;if(confirmed)return{state:'突破确认',reason:'价格越过近20日枢轴且量能放大',pivot,ranges:[r40,r20,r10,r5],volRatio:v5/v20};if(contract&&volDry)return{state:'候选形态',reason:'波动逐级收缩且量能收敛，尚未突破枢轴',pivot,ranges:[r40,r20,r10,r5],volRatio:v5/v20};if(contract)return{state:'形成中',reason:'波动收缩存在，但量能尚未充分收敛',pivot,ranges:[r40,r20,r10,r5],volRatio:v5/v20};return{state:'未形成',reason:'最近窗口未满足逐级收缩',pivot,ranges:[r40,r20,r10,r5],volRatio:v5/v20}}
function selectedMa(){return period==='day'?[5,10,20,50,150,200].filter(n=>$('#ma'+n).checked):[]}
function syncIndicatorControls(){const week=period==='week',priceMode=period==='day'||week;$('#dayIndicatorControls').classList.toggle('hidden',!priceMode||week);$('#weekIndicatorControls').classList.toggle('hidden',!week);$('#subIndicatorControls').classList.toggle('hidden',period==='minute'||period==='five')}
function destroyChart(){if(chart){try{klinecharts.dispose('chartCanvas')}catch(e){}chart=null}$('#chartCanvas').classList.remove('hidden');$('#intradayBox').classList.add('hidden')}
function renderOhlcAt(rows,index){if(!rows?.length){$('#ohlc').textContent='无K线';return}index=Math.max(0,Math.min(rows.length-1,Number.isFinite(+index)?+index:rows.length-1));const r=rows[index],prev=index>0?+rows[index-1][2]:null,open=+r[1],close=+r[2],high=+r[3],low=+r[4],vol=+r[5],chg=prev!=null?close-prev:null,cp=prev?close/prev-1:null,amp=prev?(high-low)/prev:null,cls=cp==null?'flat':cp>0?'up':cp<0?'down':'flat';$('#ohlc').innerHTML=`<span>日期 ${esc(r[0])}</span><span>开 ${num(open)}</span><span>高 ${num(high)}</span><span>低 ${num(low)}</span><span>收 ${num(close)}</span><span class="${cls}">涨跌 ${chg==null?'—':`${chg>=0?'+':''}${num(chg)}`}</span><span class="${cls}">涨跌幅 ${cp==null?'—':pct(cp)}</span><span>振幅 ${amp==null?'—':pct(amp)}</span><span>量 ${num(vol)}</span>`}
function bindCrosshairOhlc(rows){const box=$('#chartCanvas');if(!chart||!box)return;const update=e=>{let index=Number.isFinite(e?.dataIndex)?e.dataIndex:-1;if(index<0&&e?.kLineData?.timestamp){const ts=+e.kLineData.timestamp;index=rows.findIndex(r=>Date.parse(r[0]+'T00:00:00+08:00')===ts)}if(index>=0)renderOhlcAt(rows,index)};try{chart.subscribeAction?.('onCrosshairChange',update)}catch(e){console.warn('crosshair action bind failed',e)}box.onmousemove=ev=>{try{const rect=box.getBoundingClientRect(),point=chart.convertFromPixel({x:ev.clientX-rect.left,y:Math.max(1,ev.clientY-rect.top)},{paneId:'candle_pane'}),index=Math.round(point?.dataIndex);if(Number.isFinite(index))renderOhlcAt(rows,index)}catch(e){}};box.onmouseleave=()=>renderOhlcAt(rows,rows.length-1)}

function renderChartAnalysis(c,raw,weekLine=null,vcp=detectVcp(raw)){const t=calcCompanyTech(c),week=weekLine||(period==='week'?selectedWeekLine(raw):null);$('#chartAnalysis').innerHTML=`<div class="analysis-box"><b>VCP状态：${esc(vcp.state)}</b><div>${esc(vcp.reason)}</div><div class="small muted">${vcp.ranges?vcp.ranges.map(x=>(x*100).toFixed(1)+'%').join(' → '):'—'}｜量能 ${vcp.volRatio?`${vcp.volRatio.toFixed(2)}x`:'—'}</div></div><div class="analysis-box"><b>周线支撑：${week?`${week.period}周线（${week.mode==='system'?'系统选择':'手动选择'}）`:'切换周K后显示'}</b><div>${week?`触线 ${week.touches}｜守住 ${week.holds}｜有效跌破 ${week.breaches}｜当前距离 ${week.distance==null?'—':pct(week.distance)}`:'7—25周可选；系统模式采用稳定性、触线、跌破、斜率和距离评分'}</div><div class="small muted">本功能为A股本地化辅助规则，不是《100倍超级强势股》的固定公式；系统设置换线滞后门槛，避免事后拟合。</div></div><div class="analysis-box"><b>趋势检查</b><div>5日 ${pct(t.r5)}｜20日 ${pct(t.r20)}｜量比 ${t.volRatio?t.volRatio.toFixed(2)+'x':'—'}</div><div class="small muted">任何阶段或技术线都只是概率判断，需基本面、板块和风险门共同确认。</div></div>`;if(week&&$('#weekLineHint'))$('#weekLineHint').textContent=`${week.mode==='system'?'系统选择':'手动'} ${week.period}周｜评分 ${Number.isFinite(week.score)?week.score.toFixed(1):'—'}｜方向键↑↓切换`}
function setPeriod(p){period=p;$$('.period-btn').forEach(b=>b.classList.toggle('active',b.dataset.period===p));syncIndicatorControls();drawCurrentChart()}
function minutePoints(code,which){const h=D.histories[code]||{},source=h.intraday||h.minute||h.minutes||null;if(!source)return[];let arr=[];if(source&&typeof source==='object'&&!Array.isArray(source)&&(Array.isArray(source.minute)||Array.isArray(source.five_day))){arr=which==='minute'?(source.minute||[]):(source.five_day||[])}else if(Array.isArray(source))arr=source;else if(typeof source==='object'){const keys=Object.keys(source).sort();const use=which==='minute'?keys.slice(-1):keys.slice(-5);use.forEach(k=>arr.push(...(source[k]||[]).map(x=>Array.isArray(x)?[k,...x]:{date:k,...x})))}return arr.map((x,i)=>{if(Array.isArray(x)){if(x.length>=4&&typeof x[0]==='string'&&(x[0].includes('-')||/^\d{8}$/.test(x[0])))return{time:x[1],price:+x[2],volume:+(x[3]||0),date:x[0]};return{time:x[0],price:+x[1],volume:+(x[2]||0),date:''}}return{time:x.time||x.timestamp||i,price:+(x.price??x.close),volume:+(x.volume||0),date:x.date||''}}).filter(x=>Number.isFinite(x.price))}

function deriveAttributionBase(c,sectorStats){const t=calcCompanyTech(c),ss=sectorStats.find(x=>x.sector===c.sector),pos=[...(c.signal?.positive||[])],risk=[...(c.signal?.risk||[])],neutral=[...(c.signal?.neutral||[])],dr=c.daily_reason||{};(dr.direct_evidence||[]).forEach(x=>pos.push('正式披露：'+(x.title||'')));if(dr.conclusion)neutral.push('公开GitHub归因：'+dr.conclusion);if(t.volRatio>=1.5)pos.push(`成交量为20日均量${t.volRatio.toFixed(2)}倍`);else if(t.volRatio&&t.volRatio<.7)neutral.push(`成交量仅为20日均量${t.volRatio.toFixed(2)}倍`);if(ss&&c.change!=null&&ss.median1!=null){const rel=c.change-ss.median1;(rel>.015?pos:risk).push(`${rel>0?'跑赢':'跑输'}板块中位${Math.abs(rel*100).toFixed(2)}个百分点`)}if(t.r5!=null&&ss?.median5!=null){const rel=t.r5-ss.median5;(rel>.03?pos:rel<-.03?risk:neutral).push(`5日相对板块${rel>=0?'+':''}${(rel*100).toFixed(2)}个百分点`)}if(t.ma20&&t.close<t.ma20)risk.push('收盘价位于MA20下方');if(t.ma50&&t.close>=t.ma50)pos.push('收盘价位于MA50上方');const sourceState=(D.events?.[c.code]||D.announcements?.[c.code])?'已有正式披露增量':'本地快照未提供当日正式公告增量';neutral.push(sourceState);const direction=pos.length>risk.length?'positive':risk.length>pos.length?'risk':'neutral';return{direction,positive:uniq(pos).slice(0,9),risk:uniq(risk).slice(0,9),neutral:uniq(neutral).slice(0,6),failed:c.sepa?.failed||[]}}

function renderAttribution(){renderMarketContext();const stats=calcSectorStats(filtered()),rows=filtered().map(c=>({c,s:deriveAttribution(c,stats)})).filter(x=>signalFilter==='all'||x.s.direction===signalFilter);$('#dailyCards').innerHTML=rows.map(({c,s})=>`<div class="card signal-card ${s.direction}"><div class="signal-head"><div><span class="signal-company">${esc(c.name)}</span> <span class="code">${c.code}</span><div class="small muted">${esc(c.sector)}</div></div><div><b class="${classFor(c.change)}">${pct(c.change)}</b>｜<b>${esc(c.price_date)}</b>${isStale(c.price_date)?'<span class="stale-pill">数据已过期</span>':''}</div></div><div><span class="signal-label positive">积极信号：</span>${s.positive.map(x=>`<span class="badge positive">${esc(x)}</span>`).join('')||'无明确积极信号'}</div><div><span class="signal-label risk">消极信号：</span>${s.risk.map(x=>`<span class="badge risk">${esc(x)}</span>`).join('')||'无明确消极信号'}</div><div><span class="signal-label neutral">待确认：</span>${s.neutral.map(x=>`<span class="badge neutral">${esc(x)}</span>`).join('')||'—'}</div><div class="gate"><span class="signal-label">核心门禁：</span>${s.failed.map(x=>`<div>• ${esc(x)}</div>`).join('')||'未发现明确阻断，仍需基本面与估值复核'}</div></div>`).join('')}
function companiesForSector(sector){return allCompanies().filter(c=>c.sector===sector)}
function nodeCard(sector){const rows=companiesForSector(sector).filter(c=>scope==='full'||c.scope===scope),lib=NODE_LIBRARY[sector]||{};if(!rows.length)return'';const stat=calcSectorStats(rows)[0]||{},id='node_'+sector.replace(/[^\w\u4e00-\u9fa5]+/g,'_');return`<div class="chain-node-wrap" data-wrap="${esc(sector)}"><button class="chain-node" data-node="${esc(sector)}"><h3>${esc(sector)}</h3><p>${esc(lib.doing||'该环节的公司与产业信息。')}</p><div><b>${rows.length}家公司</b>｜5日中位 <span class="${classFor(stat.median5)}">${pct(stat.median5)}</span></div><div class="small muted">点击后在本节点下方展开公司、产业逻辑和领先指标</div></button><div class="node-inline-detail" id="${id}"></div></div>`}
function renderIndustryMap(){const sectors=uniq(filtered().map(c=>c.sector));$('#chainContent').innerHTML=`<div class="card"><h2>${scope==='hardware'?'AI硬件':'AI应用'}产业链地图</h2><p class="muted">点击节点展开公司；点击公司进入完整详情。该地图只显示当前板块，不再把硬件与应用混在一起。</p><div class="chain-grid">${sectors.map(nodeCard).join('')}</div><div id="nodeDetail"></div></div>`;bindChainNodes()}
function bindChainNodes(){$$('#chainContent [data-node]').forEach(b=>b.onclick=()=>{const sector=b.dataset.node,wrap=b.closest('.chain-node-wrap'),was=wrap.classList.contains('open');$$('#chainContent .chain-node-wrap.open').forEach(x=>x.classList.remove('open'));if(!was){wrap.classList.add('open');selectedChainNode=sector;renderNodeDetail(sector,wrap.querySelector('.node-inline-detail'));requestAnimationFrame(()=>wrap.scrollIntoView({behavior:'smooth',block:'nearest'}))}else selectedChainNode=null});$$('#chainContent .company-link').forEach(b=>b.onclick=()=>openDetail(b.dataset.code,companiesForSector(getCompany(b.dataset.code).sector).map(x=>x.code)))}
function renderNodeDetail(sector,target){const rows=companiesForSector(sector).filter(c=>scope==='full'||c.scope===scope),lib=NODE_LIBRARY[sector]||{},el=target||$('#nodeDetail')||$('#chainContent');el.innerHTML=`<div class="card" style="margin:0"><div class="section-title"><h2>${esc(sector)}</h2><span class="badge neutral">${rows.length}家公司</span></div><div class="grid"><div class="metric"><b>做什么</b><span>${esc(lib.doing||'待补充')}</span></div><div class="metric"><b>当前瓶颈</b><span>${esc(lib.bottleneck||'待补充')}</span></div><div class="metric"><b>需求驱动</b><span>${esc(lib.driver||'待补充')}</span></div><div class="metric"><b>领先指标</b><span>${esc(lib.leading||'待补充')}</span></div><div class="metric"><b>研究/投资时钟</b><span>${esc(lib.clock||'待补充')}</span></div></div><div class="company-links">${rows.map(c=>`<button class="company-link" data-code="${c.code}">${esc(c.name)}｜${pct(c.change)}｜${esc(c.sepa_stage||'')}</button>`).join('')}</div></div>`;el.querySelectorAll('.company-link').forEach(b=>b.onclick=()=>openDetail(b.dataset.code,rows.map(x=>x.code)))}
function renderFullChain(){if(tab==='chain-overview')renderChainOverview();else if(tab==='chain-roadmap')renderRoadmap();else if(tab==='chain-flow')renderFlow();else if(tab==='chain-clock')renderClock();else if(tab==='chain-companies')renderChainCompanies();else renderLearning()}
function renderChainOverview(){$('#chainContent').innerHTML=`<div class="card"><h2>AI全产业链知识体系</h2><p>从物理资源、半导体制造、算力基础设施，到模型平台、软件应用和物理AI。每个节点都回答“做什么、瓶颈、需求、领先指标、何时研究”。</p>${CHAIN_STAGES.map(st=>`<div class="chain-stage"><h2>${esc(st.name)}</h2><p>${esc(st.desc)}</p><div class="chain-grid">${st.sectors.map(nodeCard).join('')}</div></div>`).join('')}<div id="nodeDetail"></div></div>`;bindChainNodes();if(selectedChainNode)renderNodeDetail(selectedChainNode)}
function renderRoadmap(){$('#chainContent').innerHTML=`<div class="card"><h2>技术与需求路线</h2><div class="grid"><div class="metric"><b>未来1年：交付验证</b><span>重点看1.6T光模块、HBM供给、ASIC量产、液冷渗透和服务器出货。判断标准是订单、出货、毛利和现金流，而不是发布会。</span></div><div class="metric"><b>未来3年：推理成本下降</b><span>模型调用成本下降后，Agent和企业软件从PoC走向规模部署。关注ARR、续费率、合同负债和单位经济性。</span></div><div class="metric"><b>未来5年：物理AI扩散</b><span>机器人、智能设备和终端AI扩大需求，但量产、可靠性、渠道与BOM价值量必须验证。</span></div></div><h3>判断产业阶段的顺序</h3><div class="flow"><div class="flow-step"><b>云厂资本开支</b><p>预算与订单先变化</p></div><div class="flow-step"><b>芯片/存储/网络</b><p>交付、价格和产能</p></div><div class="flow-step"><b>服务器/电力/液冷</b><p>集群真正落地</p></div><div class="flow-step"><b>模型调用成本</b><p>应用可承受成本</p></div><div class="flow-step"><b>应用收入与留存</b><p>商业化最终验证</p></div></div></div>`}
function renderFlow(){$('#chainContent').innerHTML=`<div class="card"><h2>上下游传导与AI数据中心全生命周期</h2><div class="flow"><div class="flow-step"><b>资源与建设</b><p>电力、土地、制冷、设备和机柜决定可用容量。</p></div><div class="flow-step"><b>算力与网络</b><p>芯片、服务器、存储、交换和光互连组成集群。</p></div><div class="flow-step"><b>IDC运营</b><p>预订、投产、上架率、利用率和EBITDA验证物理资产回报。</p></div><div class="flow-step"><b>可观测性/AIOps</b><p>监控应用、模型、GPU、日志和调用链，降低故障与云成本。</p></div><div class="flow-step"><b>模型与应用</b><p>推理成本下降和稳定性提升后，商业化向下游扩散。</p></div></div><div class="warn"><b>分类边界：</b>博睿数据、新炬网络、亚信科技属于软件运行层；奥飞数据、万国数据属于物理IDC。它们共享“AI数据中心全生命周期”主题，但估值模型不能混用。</div></div>`}
function renderClock(){$('#chainContent').innerHTML=`<div class="card"><h2>条件式投资时钟</h2><div class="grid"><div class="metric"><b>阶段A：预算先行</b><span>云厂资本开支和订单上修，但出货未确认。优先研究设备、材料、关键零部件；仓位需小，防止预期落空。</span></div><div class="metric"><b>阶段B：交付扩散</b><span>服务器、网络、存储、电力同步走强，板块上涨宽度扩大。优先龙头和供给瓶颈环节。</span></div><div class="metric"><b>阶段C：盈利兑现</b><span>收入、扣非利润、现金流和指引同步上修。可以从纯预期转向业绩持有。</span></div><div class="metric"><b>阶段D：应用接棒</b><span>推理成本下降，应用ARR、续费、付费率和合同负债改善。研究平台、Agent和软件。</span></div><div class="metric"><b>阶段E：拥挤与顶部</b><span>好消息不涨、龙头破位、板块宽度收缩、盈利预测不再上修。优先减风险，而不是找理由。</span></div></div><p class="footer-note">系统不会输出“某日期必买某公司”。只有触发条件、证据等级和失效条件。</p></div>`}
function renderChainCompanies(){const rows=filtered(),groups=CHAIN_STAGES.map(st=>({st,rows:rows.filter(c=>st.sectors.includes(c.sector))})).filter(x=>x.rows.length);$('#chainContent').innerHTML=`<div class="card"><h2>公司与板块</h2>${groups.map(({st,rows})=>`<div class="chain-stage"><h3>${esc(st.name)}</h3><div class="company-links">${rows.map(c=>`<button class="company-link" data-code="${c.code}">${esc(c.name)}｜${esc(c.sector)}｜${pct(c.change)}</button>`).join('')}</div></div>`).join('')}</div>`;$$('#chainContent .company-link').forEach(b=>b.onclick=()=>openDetail(b.dataset.code,rows.map(x=>x.code)))}
function renderLearning(){$('#chainContent').innerHTML=`<div class="card"><h2>学习中心</h2><div class="grid"><div class="metric"><b>第一步：画链条</b><span>先说清楚产品从资源到应用如何传导，禁止只背公司名单。</span></div><div class="metric"><b>第二步：找瓶颈</b><span>价值通常集中在短期无法快速扩产、认证周期长、良率难提升的环节。</span></div><div class="metric"><b>第三步：找领先指标</b><span>订单、价格、产能、库存、出货、ARR、续费和现金流，哪个先于收入变化。</span></div><div class="metric"><b>第四步：看市场验证</b><span>龙头是否先走强、板块宽度是否扩散、好消息是否被价格确认。</span></div><div class="metric"><b>第五步：写失效条件</b><span>交易前写清楚什么事实出现时承认判断错误。</span></div></div><h3>核心术语</h3><p><b>SEPA：</b>趋势、基本面、催化剂、买入时机、卖出时机五类证据共同收敛。</p><p><b>VCP：</b>波动和供给逐级收缩的候选形态；必须区分候选、形成中和突破确认。</p><p><b>Magic Line：</b>本系统的A股本地化周线辅助规则，不是米勒维尼书中的固定指标。</p><p><b>利润质量：</b>归母利润不直接等于可估值利润，需拆分非经常项目、现金流、资本化和稀释。</p></div>`}
function richDetail(x){const title=esc(x.title||x.chapter||'研究章节');let body='';if(x.body||x.content)body+=`<p>${esc(x.body||x.content)}</p>`;if(Array.isArray(x.items))body+=`<ul>${x.items.map(i=>`<li>${esc(i)}</li>`).join('')}</ul>`;if(Array.isArray(x.subsections))body+=x.subsections.map(s=>`<h4>${esc(s.name)}</h4><ul>${(s.items||[]).map(i=>`<li>${esc(i)}</li>`).join('')}</ul>`).join('');return`<div class="detail-section"><h4>${title}</h4>${body||'<p class="muted">本章数据结构存在，但当前底稿未提供可显示正文。</p>'}</div>`}
function sourceLinks(c){const src=c.sources||[];return src.length?src.map((s,i)=>{const u=typeof s==='string'?s:(s.url||s.link||''),name=typeof s==='string'?`证据入口 ${i+1}`:(s.title||s.name||`证据入口 ${i+1}`);return u?`<a href="${esc(u)}" target="_blank" rel="noopener">${esc(name)}</a>`:`<div>${esc(name)}</div>`}).join(''):'<span class="muted">当前底稿没有结构化来源链接。</span>'}
function openDetail(code,codes=null){detailCodes=(codes&&codes.length?codes:filtered().map(x=>x.code)).filter(x=>getCompany(x));detailIndex=Math.max(0,detailCodes.indexOf(code));renderDetail();$('#modal').classList.add('open')}
function moveDetail(n){if(!detailCodes.length)return;detailIndex=(detailIndex+n+detailCodes.length)%detailCodes.length;renderDetail()}
function closeDetail(){$('#modal').classList.remove('open')}
function currentDetail(){return getCompany(detailCodes[detailIndex])}
function openDetailKlineBase(){const c=currentDetail();if(!c)return;closeDetail();scope=c.scope;tab='kline';$$('.scope-btn').forEach(b=>b.classList.toggle('active',b.dataset.scope===scope));populateSector();renderTabs();renderCurrent();selectChart(c.code)}
function renderDetailBase(){const c=currentDetail();if(!c)return;$('#modalTitle').textContent=`${c.name}｜${c.code}`;const details=(c.details||[]).map(richDetail).join(''),audit=c.institution_audit||{},tech=calcCompanyTech(c),lf=c.live_financials||{},liveAnn=(lf.announcements||[]).slice(0,8),liveCard=liveAnn.length?`<div class="card source-list"><h3>云端每日正式披露与基础信息更新</h3><p class="small muted">生成时间：${esc(lf.generated_at||lf.update_time||'')}｜公开源仅做证据入口，仍需打开公告原文。</p>${liveAnn.map(x=>`<p><b>${esc(x.title||x.name||'公告')}</b><br><span class="small muted">${esc(x.date||x.notice_date||'')} ${esc(x.source||'')}</span></p>`).join('')}</div>`:'';$('#modalBody').innerHTML=`<div class="detail-hero"><h3>${esc(c.one_liner||c.subsector||'')}</h3><div class="grid"><div class="metric">最新价<b>${num(c.price)} <span class="${classFor(c.change)}">${pct(c.change)}</span></b><span>${esc(c.price_date)}${isStale(c.price_date)?'<span class="stale-pill">过期</span>':''}</span></div><div class="metric">公司质量<b>${num(c.quality)}</b><span>${esc(c.tier)}</span></div><div class="metric">趋势阶段<b>${esc(strategyFor(c).trend_stage||"数据不足")}</b><span>${esc(strategyFor(c).action||"等待趋势修复")}</span></div><div class="metric">产业链位置<b>${esc(c.sector)}</b><span>${esc(c.market)}｜${esc(c.currency)}</span></div></div></div><div class="card"><h3>估值概览</h3><div class="grid"><div class="metric">当前区间<b>${esc(c.current)}</b></div><div class="metric">6个月<b>${esc(c.six)}</b></div><div class="metric">12个月公开目标<b>不公开</b></div><div class="metric">价格状态<b>${esc(rangeStatus(c))}</b></div></div><p><b>模型：</b>${esc(c.valuation_model)}</p><p><b>置信度：</b>${esc(c.valuation_confidence)}｜${esc(c.valuation_status)}</p></div><div class="detail-grid"><div class="detail-section"><h4>护城河</h4><p>${esc(c.moat)}</p></div><div class="detail-section"><h4>最大风险</h4><p>${esc(c.risk)}</p></div><div class="detail-section"><h4>最强反证</h4><p>${esc(c.counter)}</p></div><div class="detail-section"><h4>财务事实与利润质量</h4><p>${esc(c.financial)}</p></div><div class="detail-section"><h4>技术与量价</h4><p>5日 ${pct(tech.r5)}｜20日 ${pct(tech.r20)}｜量比 ${tech.volRatio?tech.volRatio.toFixed(2)+'x':'—'}</p><p>MA20 ${num(tech.ma20)}｜MA50 ${num(tech.ma50)}｜MA150 ${num(tech.ma150)}｜MA200 ${num(tech.ma200)}</p></div><div class="detail-section"><h4>机构交叉审计</h4><p>${esc(typeof audit==='string'?audit:[audit.status,audit.model,audit.difference_reason].filter(Boolean).join('｜'))||'当前没有可显示的结构化机构审计。'}</p></div></div><div class="card"><h3>门禁、行动与失效</h3><p><b>积极：</b>${(c.sepa?.positive||[]).map(x=>`<span class="badge positive">${esc(x)}</span>`).join('')||'—'}</p><p><b>风险：</b>${(c.sepa?.risk||[]).map(x=>`<span class="badge risk">${esc(x)}</span>`).join('')||'—'}</p><p><b>未通过：</b>${(c.sepa?.failed||[]).map(x=>`<span class="badge neutral">${esc(x)}</span>`).join('')||'—'}</p><p><b>当前行动：</b>${esc(c.action)}</p></div>${liveCard}<div class="card"><h3>完整研究章节</h3><div class="detail-grid">${details}</div></div><div class="card source-list"><h3>来源与证据入口</h3>${sourceLinks(c)}<p class="small muted">事实、模型推算、反证和未知项应分开；无法核验的预测不自动补全。</p></div>`}
function fillOperationCompany(){const c=getCompany($('#opCompany').value);if(!c)return;$('#opEntry').value=c.price??'';const h=history(c.code),low=h.length?Math.min(...h.slice(-10).map(r=>r[4])):'';$('#opStop').value=low?low.toFixed(2):'';evaluateOperation()}
function renderOperations(){const rows=filtered(),old=$('#opCompany').value;$('#opCompany').innerHTML=rows.map(c=>`<option value="${c.code}">${esc(c.name)}｜${c.code}</option>`).join('');if(old&&rows.some(c=>c.code===old))$('#opCompany').value=old;fillOperationCompany()}

function evaluateOperation(){const c=getCompany($('#opCompany').value)||filtered()[0];if(!c){$('#operationResult').innerHTML='<div class="error">没有可检查的公司</div>';return}const cap=+$('#opCapital').value,rp=+$('#opRiskPct').value,entry=+$('#opEntry').value,stop=+$('#opStop').value,per=entry-stop,riskAmt=cap*rp/100,shares=per>0?Math.floor(riskAmt/per):0,value=shares*entry,gates=gateState(c),fails=gates.filter(g=>g.state==='fail').length,unknown=gates.filter(g=>g.state==='unknown').length,reason=$('#opReason').value.trim();const psychology=[];if(!reason)psychology.push('没有写唯一核心逻辑，容易在下跌后临时找理由');if(per<=0)psychology.push('失效价必须低于计划买入价');if(rp>1)psychology.push('单笔风险超过1%，需确认是否属于情绪性放大仓位');if(rangeStatus(c).startsWith('高于'))psychology.push('价格已高于当前区间，不能用“长期看好”替代风险收益比');$('#operationResult').innerHTML=`<div class="card"><h3>${esc(c.name)}｜操作检查结果</h3><div class="grid"><div class="metric">理论风险金额<b>${num(riskAmt)}</b></div><div class="metric">每股风险<b>${per>0?num(per):'无效'}</b></div><div class="metric">理论股数<b>${shares||'—'}</b><span class="small">未考虑A股100股/港股每手股数，实际下单需调整。</span></div><div class="metric">理论仓位金额<b>${shares?num(value):'—'}</b></div></div>${gates.map(g=>`<div class="gate-row"><b>${g.name}</b><span class="${g.state}">${g.state==='pass'?'通过':g.state==='fail'?'未通过':'待确认'}</span><span>${esc(g.detail)}</span></div>`).join('')}<div class="${fails?'error':unknown?'warn':'success'}" style="margin-top:12px"><b>结论：</b>${fails?`有${fails}道门未通过，当前不应把“想买”写成“可以买”。`:unknown?`没有明确阻断，但有${unknown}项数据待确认。`:'五道门均通过，仍不代表必然盈利。'}</div>${psychology.length?`<div class="warn" style="margin-top:10px"><b>心理与纪律提醒：</b><ul>${psychology.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:''}</div>`;window.__V620_OPERATION__={code:c.code,capital:cap,riskPct:rp,entry,stop,riskAmt,shares,gates,reason,createdAt:new Date().toISOString()}}
function saveOperation(){evaluateOperation();try{const key='v7_operation_checks',arr=JSON.parse(localStorage.getItem(key)||'[]');arr.push(window.__V620_OPERATION__);localStorage.setItem(key,JSON.stringify(arr.slice(-100)));alert('已保存到浏览器本地记录。')}catch(e){alert('保存失败：浏览器本地存储不可用。')}}

function cachePayload(j){return{snapshot_date:j.snapshot_date||j.embedded_snapshot,generated_at:j.generated_at,quotes:j.quotes,sectors:j.sectors,market_context:j.market_context||j.market,events:j.events,announcements:j.announcements,intraday:j.intraday}}


function saveCurrentSummary(){const quotes={},company_financials={},daily_reasons={};allCompanies().forEach(c=>{quotes[c.code]={price:c.price,change_pct:c.change,date:c.price_date,timestamp:c.price_date};if(c.live_financials)company_financials[c.code]=c.live_financials;if(c.daily_reason)daily_reasons[c.code]=c.daily_reason});saveCache({schema:'v622-browser-summary-1',snapshot_date:latestPriceDate(),generated_at_cn:new Date().toISOString(),quotes,market_panel:D.market_context||{},announcements:D.announcements||{},announcement_summary:D.announcement_summary||{},company_financials,daily_reasons,coverage:{companies:allCompanies().length}})}
async function fetchOne(url,timeout=6500){const ctl=new AbortController(),tm=setTimeout(()=>ctl.abort(),timeout);try{const r=await fetch(url+(url.includes('?')?'&':'?')+'t='+Date.now(),{cache:'no-store',signal:ctl.signal,mode:'cors'});if(!r.ok)throw new Error(`HTTP ${r.status}`);return await r.json()}finally{clearTimeout(tm)}}
async function refreshOnlineLegacy(){return null}
function mergeLiveBase(j){
  if(j.histories)Object.entries(j.histories).forEach(([code,h])=>{const old=D.histories[code]||{};D.histories[code]={...old,...h,daily:h.daily||old.daily||[]}});
  if(j.company){const c=getCompany(j.company.code);if(c)Object.assign(c,j.company)}
  if(j.intraday&&j.code){D.histories[j.code]??={};D.histories[j.code].intraday=j.intraday}
  if(j.valuation_current){D.valuation_current=j.valuation_current;window.__V7_VALUATION__=D.valuation_current}
  if(j.strategy_current)D.strategy_current=j.strategy_current;
  if(j.valuation_meta)D.valuation_meta=j.valuation_meta;
  if(j.strategy_meta)D.strategy_meta=j.strategy_meta;
  if(j.market_freshness)D.market_freshness=j.market_freshness;
  if(j.live_markets)D.live_markets=j.live_markets;
  if(j.refresh_summary)D.refresh_summary=j.refresh_summary;
  if(j.coverage)D.coverage=j.coverage;
  const q=j.quotes||{};
  allCompanies().forEach(c=>{const x=q[c.code],h=j.histories?.[c.code]?.daily;if(x){c.price=x.price??x.close??c.price;c.change=x.change_pct??x.change??c.change;c.price_date=normalizeFeedDate(x.timestamp||x.date||j.snapshot_date||c.price_date)}else if(h?.length){const a=h.at(-1),b=h.at(-2);c.price=a[2];c.change=b?a[2]/b[2]-1:c.change;c.price_date=a[0]}c.valuation_status=rangeStatus(c)});
  if(j.company_meta)Object.entries(j.company_meta).forEach(([code,m])=>{const c=getCompany(code);if(c){c.name=m.name||c.name;c.market=m.market||c.market;c.sector=m.sector||c.sector}});
  if(j.market_panel||j.market_context||j.market)D.market_context=j.market_panel||j.market_context||j.market;
  if(j.events)D.events=j.events;if(j.announcements)D.announcements=j.announcements;if(j.announcement_summary)D.announcement_summary=j.announcement_summary;
  if(j.company_financials)Object.entries(j.company_financials).forEach(([code,x])=>{const c=getCompany(code);if(c)c.live_financials=x});
  if(j.daily_reasons)Object.entries(j.daily_reasons).forEach(([code,x])=>{const c=getCompany(code);if(c)c.daily_reason=x});
  if(j.sector_stats)D.remote_sector_stats=j.sector_stats;
  D.sectors.hardware=calcSectorStats(D.companies.hardware);D.sectors.application=calcSectorStats(D.companies.application)
}


function normalizeFeedDate(v){const x=String(v||'');const m=x.match(/(20\d{2})[-\/]?(\d{2})[-\/]?(\d{2})/);return m?`${m[1]}-${m[2]}-${m[3]}`:x.slice(0,10)}
function compareDate(a,b){return String(a||'').localeCompare(String(b||''))}


function batchQuoteJsonp(symbols,timeout=5000){return new Promise((resolve,reject)=>{const script=document.createElement('script'),timer=setTimeout(()=>{cleanup();reject(new Error('腾讯批量报价超时'))},timeout),cleanup=()=>{clearTimeout(timer);script.remove()};script.charset='gbk';script.src='https://qt.gtimg.cn/q='+symbols.join(',')+'&_='+Date.now();script.onload=()=>{const out={};for(const sym of symbols){const raw=window['v_'+sym];if(typeof raw!=='string')continue;const a=raw.split('~');if(a.length<6)continue;const p=Number(a[3]),pre=Number(a[4]);out[sym]={name:a[1],price:p,prev_close:pre,open:Number(a[5]),change_pct:pre?p/pre-1:null,timestamp:a[30]||'',source:'tencent-live'}}cleanup();resolve(out)};script.onerror=()=>{cleanup();reject(new Error('腾讯批量报价加载失败'))};document.head.appendChild(script)})}
async function refreshBenchmarkDates(){try{const q=await batchQuoteJsonp(['sh000001','hkHSI'],5000),dates=Object.values(q).map(x=>normalizeFeedDate(x.timestamp)).filter(Boolean).sort();if(!dates.length)throw new Error('基准行情日期为空');liveMeta.expected_market_date=dates.at(-1);liveMeta.benchmark_dates={A股:normalizeFeedDate(q.sh000001?.timestamp),港股:normalizeFeedDate(q.hkHSI?.timestamp)};return liveMeta.benchmark_dates}catch(e){liveMeta.benchmark_error=String(e);return null}}
async function refreshRealtimeQuotes({silent=false}={}){const rows=allCompanies(),groups=[];for(let i=0;i<rows.length;i+=45)groups.push(rows.slice(i,i+45));let updated=0;const errs=[];for(const g of groups){const syms=g.map(c=>D.histories[c.code]?.symbol).filter(Boolean);try{const q=await batchQuoteJsonp(syms);for(const c of g){const x=q[D.histories[c.code]?.symbol];if(!x)continue;c.price=x.price;c.change=x.change_pct;c.price_date=normalizeFeedDate(x.timestamp)||c.price_date;c.valuation_status=rangeStatus(c);updated++}}catch(e){errs.push(String(e))}}if(updated){D.sectors.hardware=calcSectorStats(D.companies.hardware);D.sectors.application=calcSectorStats(D.companies.application);liveMeta.realtime_count=updated;liveMeta.realtime_updated=new Date().toISOString();liveMeta.source=liveMeta.source.includes('GitHub')?liveMeta.source:`腾讯${totalCompanies()}家公司实时行情`;saveCurrentSummary();if(!silent){renderCurrent();updateStatus()}}return{updated,errors:errs}}
function v793CompletedItem(symbol,name,record){const rows=record?.daily||[];if(rows.length<2)return null;const current=rows.at(-1),previous=rows.at(-2),price=+current[2],prior=+previous[2];return{symbol,name,price,previous_close:prior,change_pct:prior?price/prior-1:null,date:String(current[0]),sample_at:null,as_of:String(current[0])+' 收盘',source:'正式收盘快照',quote_type:'正式收盘',realtime:false}}
function v793FormalLiveFallback(){const b=D.benchmarks||{},context=D.market_context||{},mk=(items)=>({status:'completed_session_fallback',phase:'未知',exchange_timezone:'未知',exchange_local_time:null,beijing_time:new Date().toISOString(),source:'内置正式收盘快照',quote_type:'正式收盘',fresh:false,stale:true,freshness_reason:'仅有内置快照，联网后才能核验交易日与新鲜度',data_age_minutes:null,sample_at:null,sample_date:items[0]?.date||null,file_generated_at:D.generated_at_cn||D.generated_at||null,items}),pick=(group)=>(context[group]?.items||[]).slice(0,3).map(x=>({symbol:x.ticker,name:x.name||x.ticker,price:x.close,previous_close:null,change_pct:x.change_pct,date:x.date,sample_at:null,as_of:String(x.date||'')+' 收盘',source:'正式收盘快照',quote_type:'正式收盘',realtime:false}));const china=[v793CompletedItem('sh000300','沪深300',b.CSI300),v793CompletedItem('sz399006','创业板指',b.CHINEXT),v793CompletedItem('sh000688','科创50',b.STAR50)].filter(Boolean),hk=[v793CompletedItem('hkHSI','恒生指数',b.HSI),v793CompletedItem('hkHSTECH','恒生科技',b.HSTECH)].filter(Boolean),us=pick('us'),korea=pick('korea');return{schema:'v794-live-markets-2',release:'V7.9.4',generated_at:D.generated_at_cn||D.generated_at||new Date().toISOString(),formal_snapshot_date:D.snapshot_date||D.embedded_snapshot,separate_from_valuation:true,separate_intraday_price_from_close_strategy:true,market_count:4,markets:{china:mk(china),hk:mk(hk),us:mk(us),korea:mk(korea)}}}
function v793ValidateLiveMarkets(payload){if(!payload||payload.schema!=='v794-live-markets-2'||payload.release!=='V7.9.4'||+payload.market_count!==4)throw new Error('四市场即时行情协议不匹配');for(const group of ['china','hk','us','korea']){const market=payload.markets?.[group],items=market?.items;if(!Array.isArray(items)||!items.length||items.some(x=>!Number.isFinite(+x.price)||!Number.isFinite(+x.change_pct)))throw new Error(`${group}即时行情不完整`);if(typeof market.stale!=='boolean'||typeof market.fresh!=='boolean'||!market.phase)throw new Error(`${group}缺少阶段/新鲜度字段`)}if(payload.separate_from_valuation!==true||payload.separate_intraday_price_from_close_strategy!==true)throw new Error('即时行情未声明与估值/收盘策略隔离');return payload}
function v794TencentIso(raw){const x=String(raw||'').replace(/\D/g,'');if(x.length<14)return null;return `${x.slice(0,4)}-${x.slice(4,6)}-${x.slice(6,8)}T${x.slice(8,10)}:${x.slice(10,12)}:${x.slice(12,14)}+08:00`}
function v793MergeDirectMarkets(payload,quotes){for(const group of ['china','hk']){const market=payload.markets?.[group]||{},items=market.items||[];let updated=0;items.forEach(item=>{const x=quotes[item.symbol];if(!x)return;const sampleAt=v794TencentIso(x.timestamp);Object.assign(item,{price:x.price,previous_close:x.prev_close,change_pct:x.change_pct,date:normalizeFeedDate(x.timestamp)||item.date,sample_at:sampleAt,as_of:sampleAt||x.timestamp||item.as_of,source:'腾讯即时行情',quote_type:'浏览器即时行情',realtime:true});updated++});if(updated){market.status='realtime';market.source='腾讯即时行情';market.quote_type='浏览器即时行情';market.sample_at=items.map(x=>x.sample_at).filter(Boolean).sort().at(-1)||market.sample_at;market.sample_date=items.map(x=>x.date).filter(Boolean).sort().at(-1)||market.sample_date;if(market.phase==='盘中'&&market.sample_at){const age=(Date.now()-new Date(market.sample_at).getTime())/60000;market.data_age_minutes=Math.max(0,age);market.fresh=age<=20;market.stale=!market.fresh;market.freshness_reason=market.fresh?'浏览器直连行情在20分钟新鲜度阈值内':'浏览器直连行情已超过20分钟';}}}return payload}
async function refreshLiveMarkets(){let payload=null,endpointError='';try{const result=await fetchFirst(['data/live-markets.json','https://liuyongchen1314-prog.github.io/ai-application-research-pages/data/live-markets.json'],6500);payload=v793ValidateLiveMarkets(result.data)}catch(error){endpointError=String(error?.message||error);payload=v793FormalLiveFallback()}let directCount=0;try{const symbols=['sh000300','sz399006','sh000688','hkHSI','hkHSTECH'],quotes=await batchQuoteJsonp(symbols,5500);directCount=Object.keys(quotes).length;v793MergeDirectMarkets(payload,quotes)}catch(error){payload.browser_direct_error=String(error?.message||error)}payload.browser_refreshed_at=new Date().toISOString();if(endpointError)payload.endpoint_error=endpointError;D.live_markets=v793ValidateLiveMarkets(payload);liveMeta.live_market_updated=payload.browser_refreshed_at;const staleGroups=Object.entries(payload.markets||{}).filter(([,m])=>m.stale).map(([g])=>g);return{success:true,marketCount:4,directCount,staleGroups,payload}}
function v793MarketCards(){const payload=D.live_markets||v793FormalLiveFallback(),labels={china:'A股',hk:'港股',us:'美股',korea:'韩股'};return ['china','hk','us','korea'].map(group=>{const market=payload.markets?.[group]||{},items=(market.items||[]).slice(0,3),stale=!!market.stale,tone=stale?'行情已过期':`${market.phase||'未知'} · ${market.status==='realtime'?'即时':'正式收盘'}`,age=Number.isFinite(+market.data_age_minutes)?`${(+market.data_age_minutes).toFixed(0)}分钟`:'—',sample=market.sample_at||market.sample_date||items[0]?.as_of||'—',file=market.file_generated_at_beijing||market.file_generated_at||payload.generated_at_beijing||payload.generated_at||'—';return `<article class="v793-market-card" data-live-market="${group}" data-market-freshness="${stale?'stale':'fresh'}" data-market-phase="${esc(market.phase||'未知')}" data-market-sample-date="${esc(market.sample_date||items[0]?.date||'')}"><div class="v793-market-head"><b>${labels[group]}</b><span>${esc(tone)}</span></div>${items.map(x=>`<div class="v793-market-row"><span>${esc(x.name||x.symbol)}</span><strong class="${classFor(x.change_pct)}">${pct(x.change_pct)}</strong><small>${num(x.price)}</small></div>`).join('')}<div class="v793-market-time"><b>${stale?'行情已过期':'新鲜度正常'}</b>｜来源 ${esc(market.source||items[0]?.source||'未知')}｜类型 ${esc(market.quote_type||items[0]?.quote_type||'未知')}<br>交易所当地 ${esc(String(market.exchange_local_time||'—').replace('T',' ').slice(0,19))}｜北京时间 ${esc(String(market.beijing_time||'—').replace('T',' ').slice(0,19))}<br>实际采样 ${esc(String(sample).replace('T',' ').slice(0,25))}｜文件生成 ${esc(String(file).replace('T',' ').slice(0,25))}｜数据年龄 ${age}<br>${esc(market.freshness_reason||'')}</div></article>`}).join('')}
function jsonpVar(url,varName,timeout=8000){return new Promise((resolve,reject)=>{const script=document.createElement('script'),timer=setTimeout(()=>{cleanup();reject(new Error('JSONP超时'))},timeout),cleanup=()=>{clearTimeout(timer);script.remove();try{delete window[varName]}catch(e){}};script.src=url+(url.includes('?')?'&':'?')+'_var='+encodeURIComponent(varName)+'&_='+Date.now();script.onload=()=>{const v=window[varName];cleanup();v?resolve(v):reject(new Error('JSONP无数据'))};script.onerror=()=>{cleanup();reject(new Error('JSONP加载失败'))};document.head.appendChild(script)})}
function parseDirectHistory(j,symbol){const n=(j.data||{})[symbol]||{},src=n.qfqday||n.day||[];return src.map(x=>[String(x[0]),+x[1],+x[2],+x[3],+x[4],+x[5]]).filter(x=>Number.isFinite(x[2]))}
function parseDirectIntraday(j,symbol,kind){const node=((j.data||{})[symbol]||{}),root=node.data||{},out=[];if(kind==='minute'){const obj=Array.isArray(root)?{}:root,d=String(obj.date||'');(obj.data||[]).forEach(line=>{const p=String(line).split(' ');if(p.length>=3)out.push([d,p[0],+p[1],+p[2]])})}else{const days=Array.isArray(root)?root:(Array.isArray(root.data)?root.data:[]);days.forEach(day=>{const d=String(day.date||'');(day.data||[]).forEach(line=>{const p=String(line).split(' ');if(p.length>=3)out.push([d,p[0],+p[1],+p[2]])})})}return out}
function openCacheDb(){return new Promise((resolve,reject)=>{if(!window.indexedDB)return reject(new Error('IndexedDB不可用'));const q=indexedDB.open('AIResearchCache_V79',1);q.onupgradeneeded=()=>{const db=q.result;if(!db.objectStoreNames.contains('company'))db.createObjectStore('company')};q.onsuccess=()=>resolve(q.result);q.onerror=()=>reject(q.error)})}
async function dbPutBase(key,value){try{const db=await openCacheDb();await new Promise((resolve,reject)=>{const tx=db.transaction('company','readwrite');tx.objectStore('company').put(value,key);tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error)});db.close()}catch(e){console.warn('idb put',e)}}
async function dbGetBase(key){try{const db=await openCacheDb(),v=await new Promise((resolve,reject)=>{const tx=db.transaction('company','readonly'),q=tx.objectStore('company').get(key);q.onsuccess=()=>resolve(q.result);q.onerror=()=>reject(q.error)});db.close();return v}catch(e){return null}}
async function fetchDirectHistory(code){const h=D.histories[code]||{},symbol=h.symbol;if(!symbol)throw new Error('缺少行情symbol');const v='v7_h_'+Date.now()+'_'+Math.random().toString(36).slice(2),j=await jsonpVar('https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param='+encodeURIComponent(symbol+',day,,,700,qfq'),v,9000),daily=parseDirectHistory(j,symbol);if(!daily.length)throw new Error('日K为空');return{daily,last_date:daily.at(-1)[0],count:daily.length,provider:'tencent-direct',symbol}}
async function fetchDirectIntraday(code){const h=D.histories[code]||{},symbol=h.symbol;if(!symbol)throw new Error('缺少行情symbol');const a='v7_m_'+Date.now()+'_'+Math.random().toString(36).slice(2),b='v7_f_'+Date.now()+'_'+Math.random().toString(36).slice(2),[jm,jf]=await Promise.allSettled([jsonpVar('https://web.ifzq.gtimg.cn/appstock/app/minute/query?code='+encodeURIComponent(symbol),a,7000),jsonpVar('https://web.ifzq.gtimg.cn/appstock/app/day/query?code='+encodeURIComponent(symbol),b,7000)]),out={};if(jm.status==='fulfilled')out.minute=parseDirectIntraday(jm.value,symbol,'minute');if(jf.status==='fulfilled')out.five_day=parseDirectIntraday(jf.value,symbol,'five');if(!out.minute?.length&&!out.five_day?.length)throw new Error('真实分时为空');out.synthetic=false;return out}
async function loadCompanyOnlineBase(code,{silent=false}={}){try{const [h,i]=await Promise.allSettled([fetchDirectHistory(code),fetchDirectIntraday(code)]);if(h.status==='fulfilled')D.histories[code]={...(D.histories[code]||{}),...h.value};if(i.status==='fulfilled')D.histories[code].intraday=i.value;const cache={history:D.histories[code],saved_at:new Date().toISOString()};await dbPut(code,cache);return cache}catch(e){const c=await dbGet(code);if(c?.history){D.histories[code]={...(D.histories[code]||{}),...c.history};return c}if(!silent)console.warn('company direct failed',code,e);return null}}
async function refreshAllHistories({manual=false}={}){const btn=$('#deepRefreshBtn');if(btn)btn.disabled=true;const rows=allCompanies(),total=rows.length;let done=0,ok=0,failed=0,index=1;liveMeta.deep_progress=`通道预检…`;updateStatus();try{const first=await fetchDirectHistory(rows[0].code);D.histories[rows[0].code]={...(D.histories[rows[0].code]||{}),...first};await dbPut(rows[0].code,{history:D.histories[rows[0].code],saved_at:new Date().toISOString()});done=1;ok=1}catch(e){liveMeta.deep_progress=`通道不可用，保留缓存：${e.message||e}`;if(btn)btn.disabled=false;updateStatus();return{ok:0,failed:0,total,aborted:true,error:String(e)}}async function worker(){while(true){const i=index++;if(i>=total)return;const c=rows[i];try{const h=await fetchDirectHistory(c.code);D.histories[c.code]={...(D.histories[c.code]||{}),...h};await dbPut(c.code,{history:D.histories[c.code],saved_at:new Date().toISOString()});ok++}catch(e){failed++;const cached=await dbGet(c.code);if(cached?.history)D.histories[c.code]={...(D.histories[c.code]||{}),...cached.history}}done++;liveMeta.deep_progress=`${done}/${total}，成功${ok}，失败${failed}`;if(manual||done%8===0)updateStatus()}}await Promise.all(Array.from({length:8},worker));const cn=chinaNow();try{localStorage.setItem('v7_last_deep_date',cn.date)}catch(e){}if(btn)btn.disabled=false;liveMeta.deep_progress=`完成${ok}/${total}，失败${failed}`;D.sectors.hardware=calcSectorStats(D.companies.hardware);D.sectors.application=calcSectorStats(D.companies.application);renderCurrent();updateStatus();return{ok,failed,total,aborted:false}}
function chinaNow(){const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).formatToParts(new Date()).reduce((o,x)=>(o[x.type]=x.value,o),{});return{date:`${parts.year}-${parts.month}-${parts.day}`,hour:+parts.hour,minute:+parts.minute,weekday:new Date(`${parts.year}-${parts.month}-${parts.day}T00:00:00+08:00`).getDay()}}
function checkDailyDeepRefresh(){const n=chinaNow();if(n.weekday===0||n.weekday===6)return;let last='';try{last=localStorage.getItem('v7_last_deep_date')||''}catch(e){}if((n.hour>16||(n.hour===16&&n.minute>=30))&&last!==n.date)refreshAllHistories({manual:false})}
async function refreshOnline({silent=false}={}){return refreshPublicHardware({silent})}





/* AI研究系统 V7.9 统一运行层：统一估值、独立策略、刷新控制、趋势灯、CAN SLIM本土化 */
(function () {
  "use strict";
  window.__V7_VALUATION__ = window.__V7_DATA__?.valuation_current || {};
  window.__V7_META__ = { version: "V7.9.4", builtAt: BUILD.builtAt };
  const V74_VALUATION_PENDING = "估值数据暂不可用";
  const V7_CACHE = {
    temp: new Map(),
    fund: new Map(),
    av: new Map(),
    profile: new Map(),
    chip: new Map(),
    sector: new Map(),
    sectorRs: new Map(),
    rrg: new Map(),
    risk: new Map(),
    buy: new Map(),
  };

  const V7_TECH_ABBR = new Set([
    "EPS",
    "RSI",
    "BOLL",
    "MA",
    "MACD",
    "KDJ",
    "DMI",
    "ADX",
    "PE",
    "PEG",
    "PS",
    "PB",
    "CPO",
    "HBM",
    "PCB",
    "VCP",
  ]);
  const V7_REPL = [
    [/Anchored VWAP/gi, "锚定均价"],
    [/Volume Profile/gi, "价格成交分布"],
    [/RRG/gi, "板块轮动图"],
    [/SEPA\/门禁/gi, "阶段/门禁"],
    [/SEPA阶段/gi, "趋势阶段"],
    [/\bSEPA\b/gi, "趋势阶段法"],
    [/AIOps/gi, "智能运维"],
    [/\bAgent\b/gi, "智能体"],
    [/\bSaaS\b/gi, "订阅软件"],
    [/\bERP\b/gi, "企业资源管理"],
    [/\bARR\b/gi, "年度经常性收入"],
    [/\bARPU\b/gi, "单用户平均收入"],
    [/\bSOTP\b/gi, "分部估值"],
    [/\bFCF\b/gi, "自由现金流"],
    [/EV\/EBITDA/gi, "企业价值/息税折旧摊销前利润"],
    [/\bEBITDA\b/gi, "息税折旧摊销前利润"],
    [/EV\/Sales/gi, "企业价值/收入"],
    [/EV\/GP/gi, "企业价值/毛利润"],
    [/Forward PE/gi, "远期市盈率"],
    [/Forward/gi, "远期"],
    [/Rule of 40/gi, "40法则"],
    [/ODM/gi, "代工"],
    [/CAPEX/gi, "资本开支"],
    [/ROIC/gi, "投入资本回报率"],
    [/\bPEG\b/gi, "市盈率增速匹配"],
    [/\bPE\b/gi, "市盈率"],
    [/\bPS\b/gi, "市销率"],
    [/\bPB\b/gi, "市净率"],
    [/\bROE\b/gi, "净资产收益率"],
    [/News/gi, "新闻"],
    [/Magic Line/gi, "神奇支撑线"],
    [/Market Profile/gi, "市场成交分布"],
    [/Risk-adjusted Fair Value/gi, "风险调整合理价值"],
    [/Base Fair Value/gi, "基础合理价值"],
    [/(20\d{2})E/g, "$1年预测"],
  ];
  function v7Zh(v) {
    let s = String(v ?? "");
    V7_REPL.forEach(([a, b]) => (s = s.replace(a, b)));
    return s;
  }
  function v7TranslateTree(x, seen = new WeakSet()) {
    if (!x || typeof x !== "object" || seen.has(x)) return;
    seen.add(x);
    if (Array.isArray(x)) {
      x.forEach((v, i) => {
        if (typeof v === "string") x[i] = v7Zh(v);
        else v7TranslateTree(v, seen);
      });
      return;
    }
    Object.keys(x).forEach((k) => {
      const v = x[k];
      if (
        typeof v === "string" &&
        !["code", "symbol", "ticker", "url", "link"].includes(k)
      )
        x[k] = v7Zh(v);
      else v7TranslateTree(v, seen);
    });
  }
  v7TranslateTree(D);
  D.version = "V7.9.4";
  D.v7 = D.v7 || {};
  D.v7.valuation = window.__V7_VALUATION__;
  D.fund_flows = D.fund_flows || {};
  D.benchmarks = D.benchmarks || {};
  D.risk_events = D.risk_events || [];
  Object.entries(D.company_financials || {}).forEach(([code, x]) => {
    const c = getCompany(code);
    if (c) c.live_financials = x;
  });
  if (!D.risk_events.some((x) => x.id === "20260804-cpo-us-risk"))
    D.risk_events.push({
      id: "20260804-cpo-us-risk",
      date: "2026-08-04",
      level: "R1",
      sector: "AI网络 / 光互连 / CPO",
      title: "美国正在研究限制部分中国数据中心设备",
      summary:
        "路透社报道美国正在研究针对部分中国数据中心设备、包括新型光模块的限制方案；目前仍处于方案阶段，规则可能修改或取消。",
      source: "路透社",
      url: "https://www.reuters.com/world/trump-administration-drafting-ban-chinese-data-center-devices-sources-say-2026-08-04/",
      official: false,
      reflected_in_earnings: false,
    });

  function v7RangeMid(s) {
    const a = rangeNumbers(s);
    return a.length >= 2 ? (a[0] + a[1]) / 2 : null;
  }
  function v79ForwardScenario(v) {
    const status = String(v?.forward_scenario_status || "unavailable");
    const available = ["formal", "research"].includes(status) && !!v?.forward_scenario;
    return {
      available,
      label: status === "formal" ? "6个月正式情景" : "6个月研究情景",
      range: available ? v.forward_scenario : "暂不估算",
      date: v?.forward_scenario_date || "",
      note: v?.forward_scenario_note || "前瞻盈利或模型证据未闭环",
    };
  }
  function v7ValStatus(c) {
    const v = window.__V7_VALUATION__?.[c.code];
    if (!v || v.blocked) return "估值输入未闭环";
    if (!Number.isFinite(+c.price)) return "无法判断";
    const p = +c.price,
      lo = +v.current_low,
      hi = +v.current_high,
      blo = +v.buy_low,
      bhi = +v.buy_high;
    if (p < blo) return "低于安全边际区";
    if (p <= bhi) return "进入安全边际买入区";
    if (p < lo) return "低于内在价值但安全垫不足";
    if (p <= hi) return "内在价值区内但无安全边际";
    if (p <= hi * 1.15) return "高于内在价值上限";
    return "明显高于内在价值";
  }
  function v74ModelStatus(c) {
    const v = window.__V7_VALUATION__?.[c.code];
    if (!v || !Number.isFinite(+c.price)) return "无法判断";
    const p = +c.price,
      lo = +v.current_low,
      hi = +v.current_high,
      buyLow = +v.buy_low;
    if (p < buyLow) return "明显低估";
    if (p < lo) return "合理偏低";
    if (p <= hi) return "合理区间";
    if (p <= hi * 1.15) return "偏高观察";
    return "明显偏高";
  }
  function v7ApplyValuation() {
    const m = window.__V7_VALUATION__ || {};
    allCompanies().forEach((c) => {
      const x = m[c.code];
      if (!x) return;
      c.current = x.current;
      c.six = x.six;
      c.year_end = x.year_end;
      c.next_year_start = x.next_year_start;
      c.twelve = x.twelve;
      c.valuation_model = v7Zh(x.model_note);
      c.valuation_confidence = x.confidence;
      c.v7_model_family = x.model_family;
      c.v7_eps_2026 = x.eps_2026;
      c.v7_eps_2027 = x.eps_2027;
      c.v7_eps_2028 = x.eps_2028;
      c.v7_buy_zone = x.buy_zone;
      c.v7_blocked = !!x.blocked;
      c.calibration_grade = x.calibration_grade || "C";
      x.status = v74ModelStatus(c);
      x.valuation_judgement = x.status;
      x.valuation_gate = ["明显低估", "合理偏低", "合理区间"].includes(
        x.status,
      )
        ? "通过"
        : x.status === "偏高观察"
          ? "观察"
          : "不通过";
      c.valuation_status = x.status;
      const liveAction = v73Action(c),
        oneLineCore = String(c.one_liner || "")
          .replace(/；当前操作为“[^”]*”。?$/, "")
          .replace(/；当前行动：[^。]*。?$/, "");
      c.action = liveAction;
      if (oneLineCore) c.one_liner = `${oneLineCore}；最新价${num(c.price)}，V7.9.4当前合理区间${x.current || V74_VALUATION_PENDING}，估值状态为“${x.status}”；当前行动为“${liveAction}”。`;
      (c.details || []).forEach((d) => {
        const t = String(d.title || d.chapter || "");
        if (
          (c.scope === "hardware" && t.startsWith("10.")) ||
          (c.scope === "application" && t.startsWith("11."))
        ) {
          const tx = x.blocked
            ? `旧区间已停用。缺少：${(x.missing_inputs || []).join("、")}。`
            : (() => { const f=v79ForwardScenario(x); return `估值日${x.valuation_as_of || x.price_date || "待更新"}。当前研究区间${x.current || V74_VALUATION_PENDING}；${f.label}${f.range}${f.date ? `（截至${f.date}）` : ""}；安全边际区${x.buy_zone || V74_VALUATION_PENDING}。六个月情景不是股价预测，未来12个月目标已取消公开展示。`; })();
          if ("body" in d) d.body = tx;
          else d.content = tx;
        }
        if (t.startsWith("11.") && Array.isArray(d.items)) {
          d.items = d.items.filter(
            (z) => !String(z).includes("当前参考区间上限"),
          );
          d.items.unshift(
            x.blocked
              ? "估值输入未闭环前，旧区间不得作为买点"
              : `价格必须进入安全边际买入区 ${x.buy_zone}`,
          );
        }
      });
    });
  }
  v7ApplyValuation();

  const V7_HELP = {
    fund: "看大单、小单谁更主动。这里只是按订单大小分类，不等于真实机构或散户身份。连续多日与股价同向时更有参考价值。",
    chip: "估算市场主要持仓成本集中在哪里。上方成本密集可能形成压力，下方密集可能形成支撑；它不是交易所真实账户成本。",
    avwap:
      "从一个关键日期开始计算成交量加权平均成本。股价在其上方，说明该锚点后的交易资金整体偏盈利。",
    profile:
      "看“哪些价格成交最多”，不是看哪一天成交最多。密集区常形成支撑/压力，成交真空区更容易被快速穿过。",
    rrg: "看板块相对大盘正在变强还是变弱。改善→领先通常比领先→减弱更值得继续观察，但不能单独作为买入理由。",
    temp: "交易温度只回答“当前位置热不热”，不回答公司贵不贵。低温但长期趋势已经破坏，不会被当成好买点。",
    buy: "先过趋势、基本面、板块、估值、市场五道资格门，再综合买点结构、量价、资金、支撑和风险收益比。分数高也不代表必涨。",
    risk: "可信突发风险会降低估值置信度并触发情景分析；只有正式规则真正影响业务后，才会修改收入、EPS或合理区间。",
    magic:
      "系统只在5—30周里选择历史证据足够的支撑线。没有可靠周期时宁可不画；这是一项本地化辅助规则，不是书中固定公式。",
  };
  function v7Help(k) {
    const el = document.querySelector("#v7HelpText");
    if (el)
      el.textContent =
        V7_HELP[k] || "把鼠标放到指标名称或问号上，这里会显示简单说明。";
  }
  function v7Q(k) {
    return `<button type="button" class="v7-help" data-help="${k}" aria-label="说明">?</button>`;
  }

  function v7Ma(rows, n, idx = 2) {
    if (rows.length < n) return null;
    let s = 0;
    for (const r of rows.slice(-n)) s += +r[idx] || 0;
    return s / n;
  }
  function v7Std(a) {
    const m = avg(a),
      sd = Math.sqrt(avg(a.map((x) => (x - m) ** 2)) || 0);
    return { m, sd };
  }
  function v7Slope(rows, n) {
    if (rows.length < n + 10) return null;
    const now = v7Ma(rows, n),
      old = avg(rows.slice(-n - 10, -10).map((x) => +x[2]));
    return now && old ? now / old - 1 : null;
  }
  function v7BenchmarkKey(c) {
    if (String(c.market).includes("科创")) return "STAR50";
    if (String(c.market).includes("创业")) return "CHINEXT";
    if (String(c.market).includes("港") || String(c.code).endsWith(".HK"))
      return /科技|AI|互联网|软件|芯片|机器人|云|智能/.test(c.sector)
        ? "HSTECH"
        : "HSI";
    return "CSI300";
  }
  function v7BenchmarkRows(c) {
    const key = v7BenchmarkKey(c),
      b = D.benchmarks?.[key];
    return (b?.daily || b || []).filter(
      (r) => Array.isArray(r) && r.length >= 3,
    );
  }
  function v7Relative(c, n = 20) {
    const cr = history(c.code),
      br = v7BenchmarkRows(c);
    if (cr.length <= n || br.length <= n) return null;
    const ca = cr.at(-1)[2] / cr.at(-1 - n)[2] - 1,
      ba = br.at(-1)[2] / br.at(-1 - n)[2] - 1;
    return ca - ba;
  }
  function v7SectorRows(c) {
    return D.companies[c.scope].filter((x) => x.sector === c.sector);
  }
  function _v7SectorMetrics(c) {
    const rows = v7SectorRows(c),
      r5 = rows.map((x) => calcCompanyTech(x).r5).filter(Number.isFinite),
      r20 = rows.map((x) => calcCompanyTech(x).r20).filter(Number.isFinite);
    const t = rows.map(calcCompanyTech),
      valid20 = t.filter((x) => x.ma20),
      valid50 = t.filter((x) => x.ma50);
    return {
      count: rows.length,
      median5: median(r5),
      median20: median(r20),
      breadth:
        rows.filter((x) => (x.change ?? 0) > 0).length / (rows.length || 1),
      ma20:
        valid20.filter((x) => x.close >= x.ma20).length / (valid20.length || 1),
      ma50:
        valid50.filter((x) => x.close >= x.ma50).length / (valid50.length || 1),
    };
  }
  function _v7SectorRs(c, n = 20) {
    const ss = v7SectorRows(c),
      rs = ss
        .map((x) => {
          const h = history(x.code);
          return h.length > n ? h.at(-1)[2] / h.at(-1 - n)[2] - 1 : null;
        })
        .filter(Number.isFinite);
    const br = v7BenchmarkRows(c);
    if (!rs.length || br.length <= n) return null;
    return median(rs) - (br.at(-1)[2] / br.at(-1 - n)[2] - 1);
  }
  function _v7Rrg(c) {
    const rs20 = v7SectorRs(c, 20),
      rs5 = v7SectorRs(c, 5);
    if (rs20 == null || rs5 == null)
      return { state: "数据不足", rs20: null, momentum: null };
    const mom = rs5 - rs20;
    if (rs20 >= 0 && mom >= 0) return { state: "领先", rs20, momentum: mom };
    if (rs20 >= 0 && mom < 0) return { state: "减弱", rs20, momentum: mom };
    if (rs20 < 0 && mom < 0) return { state: "落后", rs20, momentum: mom };
    return { state: "改善", rs20, momentum: mom };
  }

  function _v7Temperature(c) {
    const r = history(c.code);
    if (r.length < 60)
      return { score: null, label: "数据不足", detail: "数据不足" };
    const close = +r.at(-1)[2],
      ma20 = v7Ma(r, 20),
      ma50 = v7Ma(r, 50),
      ma150 = v7Ma(r, 150),
      ma200 = v7Ma(r, 200);
    const ret20 = retN(r, 20) || 0,
      ret60 = retN(r, 60) || 0,
      hi20 = Math.max(...r.slice(-20).map((x) => +x[3])),
      hi60 = Math.max(...r.slice(-60).map((x) => +x[3]));
    const dd20 = close / hi20 - 1,
      dd60 = close / hi60 - 1;
    const rs14 = [];
    for (let i = Math.max(1, r.length - 14); i < r.length; i++)
      rs14.push(+r[i][2] - +r[i - 1][2]);
    const gains = rs14.filter((x) => x > 0).reduce((a, b) => a + b, 0),
      loss = -rs14.filter((x) => x < 0).reduce((a, b) => a + b, 0);
    const rsi = loss ? 100 - 100 / (1 + gains / loss) : gains ? 100 : 50;
    let score = 50;
    const dist20 = ma20 ? close / ma20 - 1 : 0,
      dist50 = ma50 ? close / ma50 - 1 : 0;
    score += Math.max(-18, Math.min(18, dist20 * 120));
    score += Math.max(-10, Math.min(10, dist50 * 70));
    score += Math.max(-14, Math.min(12, ret20 * 55));
    score += Math.max(-9, Math.min(9, ret60 * 22));
    score += Math.max(-10, Math.min(10, (rsi - 50) * 0.35));
    const rel = v7Relative(c, 20);
    if (rel != null) score += Math.max(-8, Math.min(8, rel * 45));
    const longBroken =
      (ma200 &&
        close < ma200 &&
        v7Slope(r, 200) != null &&
        v7Slope(r, 200) < 0) ||
      (ma150 &&
        close < ma150 &&
        v7Slope(r, 150) != null &&
        v7Slope(r, 150) < 0);
    score = Math.max(0, Math.min(100, Math.round(score)));
    // “超跌”必须有极端证据，不因为从高位回撤就自动贴标签；顶层龙头从过热回归正常时通常只标偏冷。
    const oversoldConfirmed =
      score < 20 &&
      ((rsi < 35 && dd20 < -0.15) ||
        (dist20 < -0.12 && dd20 < -0.2 && ret20 < -0.15));
    if (score < 20 && !oversoldConfirmed) score = 20;
    let label =
      score < 20
        ? "超跌"
        : score < 40
          ? "偏冷"
          : score < 60
            ? "正常"
            : score < 80
              ? "偏热"
              : "过热";
    if (longBroken && score < 40) label = "低温但趋势受损";
    return {
      score,
      label,
      rsi,
      dd20,
      dd60,
      dist20,
      dist50,
      longBroken,
      oversoldConfirmed,
      detail: `RSI ${rsi.toFixed(0)}｜20日回撤 ${pct(dd20)}｜距MA20 ${pct(dist20)}`,
    };
  }

  function _v7FundFlow(c) {
    const src = D.fund_flows?.[c.code];
    const arr = Array.isArray(src) ? src : src?.daily || [];
    if (!arr?.length)
      return {
        state: "数据不足",
        score: null,
        rows: [],
        confidence: "数据不足",
      };
    const rows = arr
      .slice(-20)
      .map((x) =>
        Array.isArray(x)
          ? {
              date: x[0],
              main: +x[1] || 0,
              small: +x[2] || 0,
              medium: +x[3] || 0,
              large: +x[4] || 0,
              super: +x[5] || 0,
              main_pct: +x[6] || 0,
              small_pct: +x[7] || 0,
            }
          : x,
      );
    const lastDate = String(rows.at(-1)?.date || "");
    if (c.price_date && lastDate && lastDate < String(c.price_date))
      return {
        state: "数据不足",
        score: null,
        rows,
        m5: null,
        m10: null,
        s5: null,
        confidence: "资金数据已过期",
      };
    const s = (n) => rows.slice(-n).reduce((a, x) => a + (+x.main || 0), 0),
      small = (n) => rows.slice(-n).reduce((a, x) => a + (+x.small || 0), 0);
    const m5 = s(Math.min(5, rows.length)),
      m10 = s(Math.min(10, rows.length)),
      s5 = small(Math.min(5, rows.length));
    if (rows.length < 3) {
      const last = rows.at(-1),
        today =
          (+last.main || 0) > 0
            ? "当日偏流入"
            : (+last.main || 0) < 0
              ? "当日偏流出"
              : "当日中性";
      return {
        state: today,
        score: null,
        rows,
        m5,
        m10,
        s5,
        confidence: "仅当日数据",
      };
    }
    let score = 50;
    if (m5 > 0) score += 20;
    else score -= 20;
    if (m10 > 0) score += 15;
    else score -= 15;
    if (m5 > 0 && s5 < 0) score += 10;
    score = Math.max(0, Math.min(100, score));
    return {
      state: score >= 65 ? "偏强" : score <= 35 ? "偏弱" : "中性",
      score,
      rows,
      m5,
      m10,
      s5,
      confidence: rows.length >= 10 ? "较完整" : "样本偏少",
    };
  }
  function v7FmtMoney(v) {
    if (!Number.isFinite(+v)) return "—";
    const n = +v,
      a = Math.abs(n);
    if (a >= 1e8) return `${(n / 1e8).toFixed(2)}亿`;
    if (a >= 1e4) return `${(n / 1e4).toFixed(0)}万`;
    return n.toFixed(0);
  }

  const V7_MEM_STATE = {
    avwapMode: {},
    avwapDate: {},
    magicSystem: {},
    magicManual: {},
  };
  function v7AnchorMode(c) {
    let v = "";
    try {
      v = localStorage.getItem("v7_avwap_mode_" + c.code) || "";
    } catch (e) {}
    return v || V7_MEM_STATE.avwapMode[c.code] || "auto";
  }
  function v7ManualAnchor(c) {
    let v = "";
    try {
      v = localStorage.getItem("v7_avwap_date_" + c.code) || "";
    } catch (e) {}
    return v || V7_MEM_STATE.avwapDate[c.code] || "";
  }
  function v7SetAnchorMode(c, v) {
    V7_MEM_STATE.avwapMode[c.code] = v;
    try {
      localStorage.setItem("v7_avwap_mode_" + c.code, v);
    } catch (e) {}
  }
  function v7SetAnchorDate(c, v) {
    V7_MEM_STATE.avwapDate[c.code] = v;
    try {
      localStorage.setItem("v7_avwap_date_" + c.code, v);
    } catch (e) {}
  }
  function v7BreakoutIndex(r) {
    let last = null;
    for (let i = Math.max(25, r.length - 120); i < r.length; i++) {
      const prev = r.slice(Math.max(0, i - 20), i),
        pivot = Math.max(...prev.map((x) => +x[3] || 0)),
        av = avg(prev.map((x) => +x[5] || 0));
      if (+r[i][2] > pivot * 1.005 && (+r[i][5] || 0) >= av * 1.12) last = i;
    }
    return last;
  }
  function v7AnchorIndex(c, r, mode) {
    const start = Math.max(0, r.length - 180);
    if (mode === "manual") {
      const d = v7ManualAnchor(c);
      if (d) {
        const i = r.findIndex((x) => String(x[0]) >= d);
        if (i >= 0) return { i, kind: "手动日期" };
      }
    }
    if (mode === "report") {
      const d = c.live_financials?.latest_report?.report_date;
      if (d) {
        const i = r.findIndex((x) => String(x[0]) >= d);
        if (i >= 0) return { i, kind: "财报日" };
      }
    }
    if (mode === "breakout") {
      const i = v7BreakoutIndex(r);
      if (i != null) return { i, kind: "突破日" };
    }
    if (mode === "low") {
      const z = r.slice(-120),
        j = z.reduce((best, x, i, a) => (+x[4] < +a[best][4] ? i : best), 0);
      return { i: r.length - z.length + j, kind: "阶段低点" };
    }
    if (mode === "auto") {
      const bi = v7BreakoutIndex(r);
      if (bi != null && bi >= r.length - 70)
        return { i: bi, kind: "自动·突破日" };
      const d = c.live_financials?.latest_report?.report_date;
      if (d) {
        const i = r.findIndex((x) => String(x[0]) >= d);
        if (i >= Math.max(0, r.length - 120)) return { i, kind: "自动·财报日" };
      }
      const z = r.slice(-120),
        j = z.reduce((best, x, i, a) => (+x[4] < +a[best][4] ? i : best), 0);
      return { i: r.length - z.length + j, kind: "自动·阶段低点" };
    }
    return v7AnchorIndex(c, r, "low");
  }
  function _v7Avwap(c) {
    const r = history(c.code);
    if (r.length < 20) return null;
    const mode = v7AnchorMode(c),
      a = v7AnchorIndex(c, r, mode),
      z = r.slice(Math.max(0, a.i));
    let pv = 0,
      v = 0;
    z.forEach((x) => {
      const typ = (+x[2] + +x[3] + +x[4]) / 3,
        vol = +x[5] || 0;
      pv += typ * vol;
      v += vol;
    });
    return v ? { value: pv / v, anchor: z[0]?.[0], kind: a.kind, mode } : null;
  }
  function _v7Profile(c) {
    const intr = D.histories?.[c.code]?.intraday;
    let pts = [];
    try {
      pts = minutePoints(c.code, "five") || [];
    } catch (e) {}
    if (pts.length >= 200) {
      const clean = pts.filter(
        (x) => Number.isFinite(+x.price) && Number.isFinite(+x.volume),
      );
      if (clean.length >= 200) {
        const lo = Math.min(...clean.map((x) => +x.price)),
          hi = Math.max(...clean.map((x) => +x.price));
        if (hi > lo) {
          const bins = 30,
            vols = Array(bins).fill(0),
            step = (hi - lo) / bins;
          clean.forEach((x) => {
            const i = Math.max(
              0,
              Math.min(
                bins - 1,
                Math.floor(((+x.price - lo) / (hi - lo)) * bins),
              ),
            );
            vols[i] += Math.max(0, +x.volume || 0);
          });
          const k = vols.indexOf(Math.max(...vols)),
            poc = lo + (k + 0.5) * step,
            total = vols.reduce((a, b) => a + b, 0);
          let ids = [...vols.keys()].sort((a, b) => vols[b] - vols[a]),
            sum = 0,
            sel = [];
          for (const i of ids) {
            sel.push(i);
            sum += vols[i];
            if (sum >= total * 0.7) break;
          }
          return {
            poc,
            vaLow: lo + Math.min(...sel) * step,
            vaHigh: lo + (Math.max(...sel) + 1) * step,
            approx: false,
            source: "五日分钟数据",
          };
        }
      }
    }
    const r = history(c.code);
    if (r.length < 30) return null;
    const z = r.slice(-60),
      lo = Math.min(...z.map((x) => +x[4])),
      hi = Math.max(...z.map((x) => +x[3]));
    if (!(hi > lo)) return null;
    const bins = 24,
      vols = Array(bins).fill(0);
    z.forEach((x) => {
      const px = (+x[2] + +x[3] + +x[4]) / 3,
        i = Math.max(
          0,
          Math.min(bins - 1, Math.floor(((px - lo) / (hi - lo)) * bins)),
        );
      vols[i] += +x[5] || 0;
    });
    const k = vols.indexOf(Math.max(...vols)),
      step = (hi - lo) / bins,
      poc = lo + (k + 0.5) * step,
      total = vols.reduce((a, b) => a + b, 0);
    let ids = [...vols.keys()].sort((a, b) => vols[b] - vols[a]),
      sum = 0,
      sel = [];
    for (const i of ids) {
      sel.push(i);
      sum += vols[i];
      if (sum >= total * 0.7) break;
    }
    return {
      poc,
      vaLow: lo + Math.min(...sel) * step,
      vaHigh: lo + (Math.max(...sel) + 1) * step,
      approx: true,
      source: "日K近似",
    };
  }
  function _v7Chip(c) {
    const p = v7Profile(c);
    if (!p) return null;
    const close = +history(c.code).at(-1)[2];
    return {
      avg: p.poc,
      low70: p.vaLow,
      high70: p.vaHigh,
      profit: close > p.poc ? "偏高" : "偏低",
      approx: p.approx,
    };
  }

  function _v7Risk(c) {
    const ev = (D.risk_events || []).filter(
      (x) =>
        (!x.code && !x.sector) || x.code === c.code || x.sector === c.sector,
    );
    if (!ev.length) return { level: "R0", label: "无新增重大事件", events: [] };
    const rank = { R0: 0, R1: 1, R2: 2, R3: 3 },
      top = [...ev].sort(
        (a, b) =>
          (rank[b.level] || 0) - (rank[a.level] || 0) ||
          String(b.date).localeCompare(String(a.date)),
      )[0];
    return {
      level: top.level || "R0",
      label:
        top.level === "R1"
          ? "可信报道待确认"
          : top.level === "R2"
            ? "官方拟议规则"
            : top.level === "R3"
              ? "正式规则已生效"
              : "无新增重大事件",
      events: ev,
      top,
    };
  }

  function v7FundamentalGate(c) {
    const s=strategyFor(c), items=s.can_slim?.items||[], ca=items.filter(x=>['C','A'].includes(x.letter));
    if(!ca.length)return{name:'基本面',state:'unknown',detail:'后台CAN SLIM C/A数据不足'};
    const map={pass:'pass',fail:'fail',partial:'unknown',unknown:'unknown',not_applicable:'unknown'}, state=ca.some(x=>x.state==='fail')?'fail':ca.every(x=>x.state==='pass')?'pass':'unknown';
    return{name:'基本面',state:map[state]||state,detail:ca.map(x=>`${x.letter}:${x.evidence}`).join('｜')};
  }
  function v7TrendGate(c) {
    const s=strategyFor(c), stage=s.trend_stage||'数据不足', score=s.trend_quality_score;
    return{name:'趋势',state:stage==='第二阶段确认'?'pass':stage==='第四阶段'?'fail':stage==='数据不足'?'unknown':'unknown',detail:`后台唯一阶段 ${stage}｜趋势质量 ${strategyNumber(score,0)}分`};
  }
  function v7VolumeGate(c) {
    const s=strategyFor(c), br=s.technical?.breakout?.state||'数据不足', vcp=s.technical?.vcp?.state||'数据不足', vr=s.technical?.volume_ratio;
    const good=['当日突破','突破次日站稳','突破后2-5日站稳','突破后回踩确认'].includes(br)||['确认突破','形成中'].includes(vcp), bad=br==='突破失败跌回';
    return{name:'量价',state:good?'pass':bad?'fail':'unknown',detail:`后台突破=${br}｜VCP=${vcp}｜量比=${strategyNumber(vr,2)}`};
  }
  function v7SectorGate(c) {
    const s=strategyFor(c), strength=s.sector_strength||'未知', score=s.sector_score;
    return{name:'板块',state:strength==='强'?'pass':strength==='弱'?'fail':'unknown',detail:`后台板块强弱=${strength}｜综合分=${strategyNumber(score,0)}`};
  }
  function v7ValGate(c) {
    const v = window.__V7_VALUATION__?.[c.code],
      state =
        v?.valuation_gate === "通过"
          ? "pass"
          : v?.valuation_gate === "不通过"
            ? "fail"
            : "unknown";
    return {
      name: "估值",
      state,
      detail: `${v?.status || "数据不足"}｜${v?.confidence || "C"}级`,
    };
  }
  function v7MarketItem(group, ticker) {
    return (D.market_context?.[group]?.items || []).find(
      (x) => x.ticker === ticker,
    );
  }
  function v7OverseasRefs(c) {
    const s = String(c.sector || "");
    if (/HBM|存储|芯片|先进制程|设备|材料|封装/.test(s))
      return [
        ["us", "^SOX"],
        ["us", "SMH"],
        ["korea", "^KS11"],
      ];
    if (/AI安全/.test(s)) return [["us", "CIBR"]];
    if (/软件|应用|智能体|办公|教育|医疗|金融|可观测|运维|大模型|平台/.test(s))
      return [
        ["us", "IGV"],
        ["us", "CLOU"],
      ];
    if (/CPO|光互连|服务器|IDC|网络|连接器|PCB/.test(s))
      return [
        ["us", "^IXIC"],
        ["us", "SMH"],
      ];
    return [["us", "^IXIC"]];
  }
  function v7MarketGate(c) {
    const m=strategyFor(c).market_gate||{};
    return{name:'市场',state:m.hard_veto?'fail':m.state==='绿'?'pass':'unknown',detail:`后台市场灯=${m.state||'未知'}｜${esc(m.reason||'无说明')}｜${strategyNumber(m.score,0)}分`};
  }
  function v7GateState(c) {
    return [v7TrendGate(c),v7VolumeGate(c),v7FundamentalGate(c),v7SectorGate(c),v7ValGate(c)];
  }
  gateState = function (c) { return [v7MarketGate(c), ...v7GateState(c)]; };
  /* [LEGACY_DISABLED_V794] 原前端买点打分器已停用；分数/阻断/行动只读 strategy_core.py 输出。 */
  function _v7BuyPoint(c) {
    const s=strategyFor(c),tech=s.technical||{},blockers=s.blockers||[],score=Number.isFinite(+s.buy_point_score)?+s.buy_point_score:0;
    const zone=[s.first_buy_zone_low??null,s.first_buy_zone_high??null], market=v7MarketGate(c), gates=v7GateState(c);
    const type=s.action||'等待趋势修复', rr=Number.isFinite(+s.risk_reward_ratio)?+s.risk_reward_ratio:null;
    return {type,score,temp:v7Temperature(c),fund:v7FundFlow(c),av:v7Avwap(c),prof:v7Profile(c),chip:v7Chip(c),rrg:v7Rrg(c),risk:v7Risk(c),
      vcp:{state:tech.vcp?.state||'数据不足',reason:`后台VCP：${tech.vcp?.state||'数据不足'}`,pivot:tech.pivot||null},gates,market,zone,invalid:s.stop_loss??null,rr,
      supportEvidence:[],action:blockers.length?`阻断：${blockers.join('；')}`:(s.reason||'后台未列硬阻断'),backendAuthority:true};
  }
  function v7ClearCaches() {
    Object.values(V7_CACHE).forEach((x) => x.clear());
  }
  
  function v7Temperature(c) {
    if (V7_CACHE.temp.has(c.code)) return V7_CACHE.temp.get(c.code);
    const x = _v7Temperature(c);
    V7_CACHE.temp.set(c.code, x);
    return x;
  }
  
  function v7FundFlow(c) {
    if (V7_CACHE.fund.has(c.code)) return V7_CACHE.fund.get(c.code);
    const x = _v7FundFlow(c);
    V7_CACHE.fund.set(c.code, x);
    return x;
  }
  
  function v7Avwap(c) {
    if (V7_CACHE.av.has(c.code)) return V7_CACHE.av.get(c.code);
    const x = _v7Avwap(c);
    V7_CACHE.av.set(c.code, x);
    return x;
  }
  
  function v7Profile(c) {
    if (V7_CACHE.profile.has(c.code)) return V7_CACHE.profile.get(c.code);
    const x = _v7Profile(c);
    V7_CACHE.profile.set(c.code, x);
    return x;
  }
  
  function v7Chip(c) {
    if (V7_CACHE.chip.has(c.code)) return V7_CACHE.chip.get(c.code);
    const x = _v7Chip(c);
    V7_CACHE.chip.set(c.code, x);
    return x;
  }
  
  function v7SectorMetrics(c) {
    const k = c.scope + "|" + c.sector;
    if (V7_CACHE.sector.has(k)) return V7_CACHE.sector.get(k);
    const x = _v7SectorMetrics(c);
    V7_CACHE.sector.set(k, x);
    return x;
  }
  
  function v7SectorRs(c, n = 20) {
    const k = c.scope + "|" + c.sector + "|" + v7BenchmarkKey(c) + "|" + n;
    if (V7_CACHE.sectorRs.has(k)) return V7_CACHE.sectorRs.get(k);
    const x = _v7SectorRs(c, n);
    V7_CACHE.sectorRs.set(k, x);
    return x;
  }
  
  function v7Rrg(c) {
    const k = c.scope + "|" + c.sector + "|" + v7BenchmarkKey(c);
    if (V7_CACHE.rrg.has(k)) return V7_CACHE.rrg.get(k);
    const x = _v7Rrg(c);
    V7_CACHE.rrg.set(k, x);
    return x;
  }
  
  function v7Risk(c) {
    if (V7_CACHE.risk.has(c.code)) return V7_CACHE.risk.get(c.code);
    const x = _v7Risk(c);
    V7_CACHE.risk.set(c.code, x);
    return x;
  }
  
  function v7BuyPoint(c) {
    if (V7_CACHE.buy.has(c.code)) return V7_CACHE.buy.get(c.code);
    const x = _v7BuyPoint(c);
    V7_CACHE.buy.set(c.code, x);
    return x;
  }

  function v7GateHtml(x) {
    const cls =
        x.state === "pass"
          ? "v7-pass"
          : x.state === "fail"
            ? "v7-fail"
            : "v7-unk",
      sym = x.state === "pass" ? "✓" : x.state === "fail" ? "✕" : "?";
    return `<span class="v7-gate ${cls}" title="${esc(x.detail)}">${esc(x.name)} ${sym}</span>`;
  }
  function v7TempHtml(c) {
    const t = v7Temperature(c);
    return t.score == null
      ? '<span class="v7-temp muted">温度：数据不足</span>'
      : `<span class="v7-temp" data-help="temp">温度${t.score} · ${esc(t.label)}</span>`;
  }
  function v7Action(c) { return strategyFor(c).action || '等待趋势修复'; }

  function v794CanonicalCompare(A,B){
    const a=strategyFor(A),b=strategyFor(B),n=(v,d=0)=>Number.isFinite(+v)?+v:d,abs=(v)=>Number.isFinite(+v)?Math.abs(+v):999;
    const asc=[n(a.action_priority,99)-n(b.action_priority,99),n(a.trend_stage_priority,99)-n(b.trend_stage_priority,99),n(b.trend_quality_score)-n(a.trend_quality_score),n(b.technical?.relative_strength_12m)-n(a.technical?.relative_strength_12m),n(b.technical?.relative_strength_6m)-n(a.technical?.relative_strength_6m),n(b.technical?.relative_strength_3m)-n(a.technical?.relative_strength_3m),n(b.technical?.industry_relative_rank)-n(a.technical?.industry_relative_rank),abs(a.distance_to_pivot)-abs(b.distance_to_pivot),n(b.setup_quality_score)-n(a.setup_quality_score),n(b.sector_score)-n(a.sector_score),n(b.company_quality??B.quality)-n(a.company_quality??A.quality)];
    return asc.find(x=>Math.abs(x)>1e-12)||String(A.code).localeCompare(String(B.code));
  }
  let v7SortKey = "canonical", v7SortDir = "desc";
  function v7SortRows(rows) {
    if(v7SortKey==='canonical')return [...rows].sort(v794CanonicalCompare);
    const dir=v7SortDir==='asc'?1:-1,n=(v,d=-Infinity)=>Number.isFinite(+v)?+v:d;
    return rows.map((x,i)=>({x,i})).sort((a,b)=>{const A=a.x,B=b.x,sa=strategyFor(A),sb=strategyFor(B);let av,bv;
      if(v7SortKey==='trend'){av=n(sa.trend_quality_score);bv=n(sb.trend_quality_score)}
      else if(v7SortKey==='buy'){av=n(sa.buy_point_score);bv=n(sb.buy_point_score)}
      else if(v7SortKey==='rs'){av=n(sa.technical?.relative_strength_12m);bv=n(sb.technical?.relative_strength_12m)}
      else if(v7SortKey==='action'){av=-n(sa.action_priority,99);bv=-n(sb.action_priority,99)}
      else if(v7SortKey==='stage'){av=-n(sa.trend_stage_priority,99);bv=-n(sb.trend_stage_priority,99)}
      else if(v7SortKey==='quality'){av=n(A.quality);bv=n(B.quality)}
      else if(v7SortKey==='valuation'){const f=x=>{const z=window.__V7_VALUATION__?.[x.code]?.status||'';return z==='明显低估'?5:z==='合理偏低'?4:z==='合理区间'?3:z.includes('偏高')?2:1};av=f(A);bv=f(B)}
      else if(v7SortKey==='change'){av=n(A.change);bv=n(B.change)}
      else {av=n(calcCompanyTech(A).r5);bv=n(calcCompanyTech(B).r5)}
      const d=(av-bv)*dir;return Math.abs(d)>1e-12?d:a.i-b.i;
    }).map(x=>x.x);
  }
  function v7SectorHtml(s, c0) {
    const rows = v7SectorRows(c0),
      leaders = [...rows]
        .sort(
          (a, b) =>
            (calcCompanyTech(b).r5 ?? -99) - (calcCompanyTech(a).r5 ?? -99),
        )
        .slice(0, 3),
      rs = v7SectorRs(c0, 20),
      r = v7Rrg(c0);
    return `<div class="card sector-card v7-sector"><div class="section-title"><div><h3>${esc(c0.sector)}</h3><p class="small muted">${rows.length}家公司｜领头羊：${leaders.map((x) => esc(x.name)).join("、")}</p></div><button class="detail-btn v7-expand-sector" data-sector="${esc(c0.sector)}">展开全部公司</button></div><div class="v7-sector-grid"><div><span>当日中位</span><b class="${classFor(s.median1)}">${pct(s.median1)}</b></div><div><span>5日中位</span><b class="${classFor(s.median5)}">${pct(s.median5)}</b></div><div><span>相对大盘20日</span><b class="${classFor(rs)}">${rs == null ? "数据不足" : pct(rs)}</b></div><div><span>板块轮动 ${v7Q("rrg")}</span><b>${esc(r.state)}</b></div><div><span>上涨宽度</span><b>${(s.breadth * 100).toFixed(0)}%</b></div><div><span>站上MA20</span><b>${(s.ma20 * 100).toFixed(0)}%</b></div></div><div class="v7-sector-all hidden" data-sector-list="${esc(c0.sector)}">${[
      ...rows,
    ]
      .sort(
        (a, b) =>
          (calcCompanyTech(b).r5 ?? -99) - (calcCompanyTech(a).r5 ?? -99),
      )
      .map(
        (x, i) =>
          `<button class="v7-mini-company" data-detail="${esc(x.code)}"><span>${i + 1}. ${esc(x.name)}</span><b class="${classFor(calcCompanyTech(x).r5)}">${pct(calcCompanyTech(x).r5)}</b></button>`,
      )
      .join("")}</div></div>`;
  }
  renderSector = function () {
    const rows = filtered(),
      stats = calcSectorStats(rows);
    $("#sectorCards").innerHTML = stats
      .map((s) => {
        const c0 = rows.find((x) => x.sector === s.sector);
        return c0 ? v7SectorHtml(s, c0) : "";
      })
      .join("");
    document.querySelectorAll(".v7-expand-sector").forEach(
      (b) =>
        (b.onclick = () => {
          const el = document.querySelector(
            `[data-sector-list="${CSS.escape(b.dataset.sector)}"]`,
          );
          if (!el) return;
          el.classList.toggle("hidden");
          b.textContent = el.classList.contains("hidden")
            ? "展开全部公司"
            : "收起公司";
        }),
    );
    document.querySelectorAll(".v7-mini-company").forEach(
      (b) =>
        (b.onclick = () =>
          openDetail(
            b.dataset.detail,
            filtered().map((x) => x.code),
          )),
    );
    document
      .querySelectorAll(".v7-help")
      .forEach((x) => (x.onmouseenter = () => v7Help(x.dataset.help)));
  };

  // 神奇支撑线：5-30周，系统只选通过稳定性验证的周期。

  function v7WeekKey(d) {
    const x = new Date(String(d) + "T00:00:00Z");
    if (Number.isNaN(+x)) return String(d).slice(0, 7);
    const day = (x.getUTCDay() + 6) % 7;
    x.setUTCDate(x.getUTCDate() - day + 3);
    const y = x.getUTCFullYear(),
      jan4 = new Date(Date.UTC(y, 0, 4)),
      jday = (jan4.getUTCDay() + 6) % 7,
      week =
        1 +
        Math.round((x - new Date(Date.UTC(y, 0, 4 - jday + 3))) / 604800000);
    return `${y}-W${String(week).padStart(2, "0")}`;
  }
  function v7FundSeriesForRows(c, rows, per) {
    const src = D.fund_flows?.[c.code],
      arr = Array.isArray(src) ? src : src?.daily || [];
    if (!arr?.length) return [];
    const norm = arr.map((x) =>
      Array.isArray(x)
        ? { date: x[0], main: +x[1] || 0, small: +x[2] || 0 }
        : x,
    );
    if (per === "week") {
      const agg = {};
      norm.forEach((x) => {
        const k = v7WeekKey(x.date);
        agg[k] ??= { main: 0, small: 0 };
        agg[k].main += +x.main || 0;
        agg[k].small += +x.small || 0;
      });
      return rows.map((x) => agg[v7WeekKey(x[0])] || {});
    }
    const map = Object.fromEntries(norm.map((x) => [String(x.date), x]));
    return rows.map((x) => {
      const y = map[String(x[0])];
      return y ? { main: +y.main || 0, small: +y.small || 0 } : {};
    });
  }
  function v7RegisterFundIndicator() {
    try {
      if (!klinecharts.getSupportedIndicators().includes("FUNDV7"))
        klinecharts.registerIndicator({
          name: "FUNDV7",
          shortName: "订单规模资金",
          series: "normal",
          precision: 0,
          figures: [
            { key: "main", title: "大单净额: ", type: "line" },
            { key: "small", title: "小单净额: ", type: "line" },
          ],
          calc: (data) =>
            data.map((_, i) => window.__V7_FUND_SERIES__?.[i] || {}),
        });
    } catch (e) {
      console.warn("资金指标注册失败", e);
    }
  }
  v7RegisterFundIndicator();

  evaluateWeekLine = function (w, n) {
    const need = Math.max(78, n * 3);
    if (w.length < n)
      return {
        period: n,
        drawable: false,
        available: false,
        reason: "数据不足",
        score: -999,
        touches: 0,
        holds: 0,
        breaches: 0,
        distance: null,
        slope: null,
      };
    const mas = [];
    for (let i = 0; i < w.length; i++)
      mas[i] =
        i >= n - 1 ? avg(w.slice(i - n + 1, i + 1).map((x) => +x[2])) : null;
    let touches = 0,
      holds = 0,
      breaches = 0;
    const from = Math.max(n - 1, w.length - 78);
    for (let i = from; i < w.length; i++) {
      const ma = mas[i];
      if (!ma) continue;
      const low = +w[i][4],
        high = +w[i][3],
        close = +w[i][2];
      if (low <= ma * 1.025 && high >= ma * 0.975) {
        touches++;
        if (
          close >= ma * 0.985 ||
          (i + 1 < w.length && +w[i + 1][2] >= (mas[i + 1] || ma) * 0.985)
        )
          holds++;
      }
      if (
        i > from &&
        close < ma * 0.97 &&
        +w[i - 1][2] < (mas[i - 1] || ma) * 0.97
      )
        breaches++;
    }
    const last = mas.at(-1),
      old = mas[Math.max(n - 1, mas.length - 9)],
      slope = last && old ? last / old - 1 : null,
      distance = last ? +w.at(-1)[2] / last - 1 : null;
    const score =
      holds * 10 +
      touches * 2 -
      breaches * 22 +
      (slope == null ? 0 : Math.max(-20, Math.min(16, slope * 150))) -
      (distance == null ? 20 : Math.min(25, Math.abs(distance) * 100));
    const available =
      w.length >= need &&
      touches >= 3 &&
      holds >= 2 &&
      breaches <= 1 &&
      slope > -0.035 &&
      distance != null &&
      Math.abs(distance) < 0.18;
    return {
      period: n,
      drawable: true,
      available,
      reason: available
        ? "历史证据通过"
        : `证据不足：${w.length}周、触线${touches}、守住${holds}、跌破${breaches}`,
      score,
      touches,
      holds,
      breaches,
      distance,
      slope,
      line: last,
    };
  };
  chooseMagicPeriod = function (w, code = chartCode) {
    const candidates = [];
    for (let n = 5; n <= 30; n++) candidates.push(evaluateWeekLine(w, n));
    const valid = candidates
      .filter((x) => x.available)
      .sort((a, b) => b.score - a.score);
    if (!valid.length)
      return {
        period: null,
        drawable: false,
        available: false,
        reason: "暂无可靠神奇支撑线",
        score: null,
        touches: 0,
        holds: 0,
        breaches: 0,
        distance: null,
        slope: null,
        line: null,
        mode: "system",
        candidates,
      };
    let best = valid[0],
      oldN = V7_MEM_STATE.magicSystem[code] || 0;
    try {
      oldN = +(localStorage.getItem("v7_magic_system_" + code) || oldN || 0);
    } catch (e) {}
    const old = valid.find((x) => x.period === oldN);
    if (old && best.period !== old.period && best.score < old.score + 10)
      best = old;
    V7_MEM_STATE.magicSystem[code] = best.period;
    try {
      localStorage.setItem("v7_magic_system_" + code, String(best.period));
    } catch (e) {}
    return { ...best, mode: "system", candidates };
  };
  selectedWeekLine = function (raw) {
    const w = weekly(raw),
      value = $("#weekMaSelect")?.value || "system";
    if (value === "system") return chooseMagicPeriod(w, chartCode);
    const x = evaluateWeekLine(w, +value);
    V7_MEM_STATE.magicManual[chartCode] = +value;
    try {
      localStorage.setItem("v7_magic_manual_" + chartCode, String(value));
    } catch (e) {}
    return { ...x, mode: "manual", candidates: [] };
  };

  /* [LEGACY_DISABLED_V794] 趋势灯只读后台趋势阶段/趋势质量。 */
  function v74TrendSignal(c) {
    const s=strategyFor(c),score=Number.isFinite(+s.trend_quality_score)?+s.trend_quality_score:null,stage=s.trend_stage||'数据不足';
    const tone=stage==='第二阶段确认'?'strong':stage==='第二阶段候选'?'good':stage==='第一阶段'?'neutral':stage==='第三阶段'?'weak':stage==='第四阶段'?'bad':'unknown';
    return{score,label:stage,tone,note:`后台唯一趋势结果｜数据完整度 ${strategyNumber(s.data_completeness,0)}｜阻断 ${(s.blockers||[]).join('；')||'无硬阻断'}`,relative:s.technical?.relative_strength_12m??null,s20:null,s50:null};
  }
  function v74RenderTrendLight(c) {
    const title = document.querySelector("#panel-kline .chart-title");
    if (!title) return;
    let light = document.querySelector("#v74TrendLight");
    if (!light) {
      light = document.createElement("div");
      light.id = "v74TrendLight";
      title.querySelector("div")?.appendChild(light);
    }
    const result = v74TrendSignal(c);
    light.className = `v74-trend-light tone-${result.tone}`;
    light.innerHTML = `<span>趋势</span><b>${esc(result.label)}</b><em>${result.score == null ? "—" : result.score + "分"}</em><small>${esc(result.note)}</small>`;
  }
  function v7RenderAnalysis(c, raw, weekLine = null, vcp = detectVcp(raw)) {
    const b = v7BuyPoint(c),
      t = b.temp,
      f = b.fund,
      a = b.av,
      p = b.prof,
      ch = b.chip,
      risk = b.risk;
    $("#chartAnalysis").innerHTML =
      `<div class="v7-buy-card"><div class="v7-buy-head"><div><span class="v7-kicker">当前买点 ${v7Q("buy")}</span><h3>${esc(b.type)} <em>${b.score}/100</em></h3></div><span class="v7-temp-pill" data-help="temp">${t.score == null ? "温度：数据不足" : `温度${t.score} · ${esc(t.label)}`}</span></div><div class="v7-gates">${b.gates.map(v7GateHtml).join("")}${v7GateHtml(b.market)}</div><div class="v7-buy-grid"><div><span>参考买区</span><b>${num(b.zone[0])}–${num(b.zone[1])}</b></div><div><span>结构失效</span><b>${b.invalid ? num(b.invalid) : "无法判断"}</b></div><div><span>风险收益比</span><b>${b.rr != null && b.rr > 0 ? b.rr.toFixed(1) + ":1" : "无法判断"}</b></div><div><span>支撑共振</span><b>${b.supportEvidence.length ? `${b.supportEvidence.length}项` : "数据不足"}</b></div></div><p class="v7-action">${esc(b.action)}</p>${risk.level !== "R0" ? `<div class="v7-risk" data-help="risk"><b>⚠ ${risk.level === "R1" ? "一级事件风险" : risk.level === "R2" ? "二级事件风险" : "三级事件风险"}</b><span>${esc(risk.top?.summary || "无法判断")}</span></div>` : ""}</div><div class="v7-tools"><div class="v7-tool"><b>资金行为 ${v7Q("fund")}</b><span>${f.state}${f.score != null ? `｜5日主力 ${v7FmtMoney(f.m5)}` : ""}</span></div><div class="v7-tool"><b>筹码成本估算 ${v7Q("chip")}</b><span>${ch ? `核心成本约 ${num(ch.avg)}｜70%区 ${num(ch.low70)}–${num(ch.high70)}` : "数据不足"}</span></div><div class="v7-tool"><b>锚定均价 ${v7Q("avwap")}</b><span>${a ? `${num(a.value)}｜${esc(a.kind)} ${a.anchor}` : "数据不足"}</span><div class="v7-anchor-ctrl"><select id="v7AvwapMode"><option value="auto">自动锚点</option><option value="report">财报日</option><option value="breakout">突破日</option><option value="low">阶段低点</option><option value="manual">手动日期</option></select><input id="v7AvwapDate" type="date" class="hidden"></div></div><div class="v7-tool"><b>价格成交分布 ${v7Q("profile")}</b><span>${p ? `最大成交区 ${num(p.poc)}｜${p.approx ? "日K近似" : "五日分钟"}` : "数据不足"}</span></div><div class="v7-tool"><b>板块轮动 ${v7Q("rrg")}</b><span>${esc(b.rrg.state)}${b.rrg.rs20 != null ? `｜20日相对大盘 ${pct(b.rrg.rs20)}` : ""}</span></div><div class="v7-tool"><b>VCP</b><span>${esc(vcp.state)}｜${esc(vcp.reason)}</span></div></div><div id="v7HelpBox" class="v7-help-box"><b>当前功能说明</b><span id="v7HelpText">把鼠标放到指标名称旁的问号上，这里会显示简单说明。</span></div>${period === "week" ? `<div class="v7-week-note"><b>神奇支撑线 ${v7Q("magic")}</b><span>${weekLine?.available ? `${weekLine.period}周｜触线${weekLine.touches}｜守住${weekLine.holds}｜跌破${weekLine.breaches}` : weekLine?.mode === "manual" && weekLine?.drawable ? `${weekLine.period}周手动查看｜${esc(weekLine.reason)}` : "暂无可靠神奇支撑线"}</span></div>` : ""}`;
    const ms = document.querySelector("#v7AvwapMode"),
      md = document.querySelector("#v7AvwapDate");
    if (ms) {
      ms.value = v7AnchorMode(c);
      if (md) {
        md.value = v7ManualAnchor(c);
        md.classList.toggle("hidden", ms.value !== "manual");
      }
      ms.onchange = () => {
        v7SetAnchorMode(c, ms.value);
        if (md) md.classList.toggle("hidden", ms.value !== "manual");
        v7ClearCaches();
        drawCurrentChart();
      };
      if (md)
        md.onchange = () => {
          v7SetAnchorDate(c, md.value);
          v7SetAnchorMode(c, "manual");
          v7ClearCaches();
          drawCurrentChart();
        };
    }
    document.querySelectorAll(".v7-help,[data-help]").forEach((x) => {
      x.onmouseenter = () => v7Help(x.dataset.help);
    });
  }
  renderChartAnalysis = v7RenderAnalysis;

  drawCurrentChart = function () {
    if (!chartCode) return;
    const c = getCompany(chartCode),
      raw = history(chartCode);
    $("#chartName").textContent = `${c.name}｜${c.code}`;
    v74RenderTrendLight(c);
    renderOhlcAt(raw, raw.length - 1);
    if (period === "minute" || period === "five") {
      destroyChart();
      renderIntraday(period);
      v7RenderAnalysis(c, raw, null, detectVcp(raw));
      return;
    }
    destroyChart();
    const rows = period === "week" ? weekly(raw) : raw;
    if (!rows.length) {
      $("#indicatorNote").textContent = "数据不足";
      $("#indicatorNote").classList.remove("hidden");
      return;
    }
    $("#indicatorNote").classList.add("hidden");
    chart = klinecharts.init("chartCanvas", {
      locale: "zh-CN",
      timezone: "Asia/Shanghai",
    });
    chart.setDataLoader({ getBars: ({ callback }) => callback(toBars(rows)) });
    chart.setSymbol({
      ticker: c.code,
      name: c.name,
      pricePrecision: 2,
      volumePrecision: 0,
    });
    chart.setPeriod({ span: 1, type: period === "week" ? "week" : "day" });
    chart.setStyles({
      candle: { tooltip: { showRule: "always", showType: "standard" } },
      indicator: { tooltip: { showRule: "always" } },
      separator: {
        size: 2,
        fill: true,
        activeBackgroundColor: "rgba(53,89,255,.08)",
      },
    });
    let weekLine = null;
    if (period === "day") {
      const ma = selectedMa();
      if (ma.length)
        chart.createIndicator(
          { name: "MA", calcParams: ma, paneId: "candle_pane" },
          true,
        );
      if ($("#toggleBoll").checked)
        chart.createIndicator(
          { name: "BOLL", calcParams: [20, 2], paneId: "candle_pane" },
          true,
        );
    } else {
      weekLine = selectedWeekLine(raw);
      const canDraw =
        weekLine.mode === "system" ? weekLine.available : weekLine.drawable;
      if ($("#weekLineVisible").checked && canDraw && weekLine.period)
        chart.createIndicator(
          {
            name: "MAGIC",
            calcParams: [weekLine.period],
            paneId: "candle_pane",
          },
          true,
        );
    }
    const vcp = detectVcp(raw);
    if (
      period === "day" &&
      $("#toggleVcp").checked &&
      vcp.pivot &&
      vcp.state !== "未形成"
    )
      chart.createIndicator(
        { name: "VCPMARK", calcParams: [vcp.pivot, 20], paneId: "candle_pane" },
        true,
      );
    const panes = [];
    if ($("#toggleVol").checked) {
      chart.createIndicator(
        { name: "VOL", calcParams: [5, 10, 20], paneId: "vol_pane" },
        false,
      );
      panes.push(["vol_pane", 128]);
    }
    if ($("#toggleFundV7")?.checked) {
      window.__V7_FUND_SERIES__ = v7FundSeriesForRows(c, rows, period);
      if (
        window.__V7_FUND_SERIES__.some(
          (x) => Number.isFinite(x.main) || Number.isFinite(x.small),
        )
      ) {
        chart.createIndicator(
          { name: "FUNDV7", paneId: "fund_v7_pane" },
          false,
        );
        panes.push(["fund_v7_pane", 120]);
      }
    }
    if ($("#toggleMacd").checked) {
      chart.createIndicator(
        { name: "MACD", calcParams: [12, 26, 9], paneId: "macd_pane" },
        false,
      );
      panes.push(["macd_pane", 145]);
    }
    if ($("#toggleRsi").checked) {
      chart.createIndicator(
        { name: "RSI", calcParams: [6, 12, 24], paneId: "rsi_pane" },
        false,
      );
      panes.push(["rsi_pane", 138]);
    }
    if ($("#toggleKdj").checked) {
      chart.createIndicator(
        { name: "KDJ", calcParams: [9, 3, 3], paneId: "kdj_pane" },
        false,
      );
      panes.push(["kdj_pane", 138]);
    }
    if ($("#toggleDmi").checked) {
      chart.createIndicator(
        { name: "DMI", calcParams: [14, 6], paneId: "dmi_pane" },
        false,
      );
      panes.push(["dmi_pane", 138]);
    }
    try {
      chart.setPaneOptions({
        id: "candle_pane",
        height: Math.max(380, 780 - panes.reduce((a, x) => a + x[1], 0)),
      });
      panes.forEach(([id, h]) => chart.setPaneOptions({ id, height: h }));
    } catch (e) {}
    chart.setBarSpace(period === "week" ? 10 : 7);
    chart.scrollToRealTime();
    renderOhlcAt(rows, rows.length - 1);
    bindCrosshairOhlc(rows);
    v7RenderAnalysis(c, raw, weekLine, vcp);
    window.__V7_CHART_STATE__ = {
      code: c.code,
      period,
      bars: rows.length,
      weekSelection: weekLine
        ? {
            mode: weekLine.mode,
            period: weekLine.period,
            available: weekLine.available,
            drawable: weekLine.drawable,
            score: weekLine.score,
          }
        : null,
      indicators: chart
        .getIndicators()
        .map((x) => ({
          name: x.name,
          paneId: x.paneId,
          calcParams: x.calcParams,
        })),
    };
  };

  function v7Incremental(pts) {
    let lastByDay = {};
    return pts.map((x) => {
      const d = x.date || "",
        raw = +x.volume || 0,
        last = lastByDay[d];
      let inc = last == null ? raw : raw - last;
      if (!Number.isFinite(inc) || inc < 0) inc = 0;
      lastByDay[d] = raw;
      return { ...x, volume_raw: raw, volume: inc };
    });
  }
  function v7PrevClose(c, day) {
    const r = history(c.code);
    if (!r.length) return null;
    const idx = r.findIndex((x) => x[0] === day);
    if (idx > 0) return +r[idx - 1][2];
    if (idx === 0) return +r[0][1];
    return +r.at(-2)?.[2] || +r.at(-1)[1];
  }
  renderIntraday = function (which) {
    const c = getCompany(chartCode),
      raw = v7Incremental(minutePoints(chartCode, which)),
      box = $("#intradayBox");
    $("#chartCanvas").classList.add("hidden");
    box.classList.remove("hidden");
    if (!raw.length) {
      box.innerHTML = `<div class="v7-empty"><b>${which === "minute" ? "当日分时" : "五日分时"}：数据不足</b><span>没有真实分钟数据，不生成伪分时。</span></div>`;
      window.__V7_INTRADAY_STATE__ = {
        code: c.code,
        period: which,
        bars: 0,
        real: false,
      };
      return;
    }
    const W = 1180,
      H = 610,
      L = 66,
      R = 68,
      T = 38,
      VH = 120,
      B = 32,
      priceBottom = H - VH - B,
      days = [...new Set(raw.map((x) => x.date || ""))],
      prev = v7PrevClose(c, days.at(-1));
    const prices = raw.map((x) => x.price),
      min0 = Math.min(...prices),
      max0 = Math.max(...prices);
    let lo = min0,
      hi = max0;
    if (which === "minute" && prev) {
      const d = Math.max(
        Math.abs(max0 / prev - 1),
        Math.abs(min0 / prev - 1),
        0.008,
      );
      lo = prev * (1 - d * 1.12);
      hi = prev * (1 + d * 1.12);
    } else {
      const d = Math.max((max0 - min0) * 0.12, ((max0 + min0) / 2) * 0.006);
      lo = min0 - d;
      hi = max0 + d;
    }
    const sx = (i) => L + (i / Math.max(1, raw.length - 1)) * (W - L - R),
      sy = (p) =>
        T + ((hi - p) / Math.max(0.000001, hi - lo)) * (priceBottom - T),
      vmax = Math.max(1, ...raw.map((x) => x.volume)),
      sv = (v) => H - B - (v / vmax) * (VH - 18);
    const path = raw
      .map(
        (x, i) =>
          `${i ? "L" : "M"}${sx(i).toFixed(1)},${sy(x.price).toFixed(1)}`,
      )
      .join(" ");
    let grid = "";
    for (let i = 0; i <= 4; i++) {
      const p = hi - ((hi - lo) * i) / 4,
        y = sy(p);
      grid += `<line x1="${L}" y1="${y}" x2="${W - R}" y2="${y}" class="iv-grid"/><text x="${L - 8}" y="${y + 4}" text-anchor="end">${p.toFixed(2)}</text>`;
      if (prev)
        grid += `<text x="${W - R + 8}" y="${y + 4}" text-anchor="start">${((p / prev - 1) * 100).toFixed(1)}%</text>`;
    }
    let sep = "",
      last = "";
    raw.forEach((x, i) => {
      if (x.date && x.date !== last) {
        if (i > 0)
          sep += `<line x1="${sx(i)}" y1="${T}" x2="${sx(i)}" y2="${H - B}" class="iv-day"/>`;
        sep += `<text x="${sx(i) + 5}" y="${H - 8}" class="iv-date">${x.date.slice(5)}</text>`;
        last = x.date;
      }
    });
    const bars = raw
      .map(
        (x, i) =>
          `<rect x="${Math.max(L, sx(i) - 1)}" y="${sv(x.volume)}" width="2" height="${H - B - sv(x.volume)}" class="iv-vol"/>`,
      )
      .join("");
    const prevLine = prev
      ? `<line x1="${L}" y1="${sy(prev)}" x2="${W - R}" y2="${sy(prev)}" class="iv-prev"/><text x="${W - R - 6}" y="${sy(prev) - 6}" text-anchor="end" class="iv-prev-label">昨收 ${prev.toFixed(2)}</text>`
      : "";
    const fsum = v7FundFlow(c),
      fbadge =
        fsum.score != null
          ? `<div class="v7-intraday-fund">当日/历史资金：${esc(fsum.state)}｜5日大单 ${v7FmtMoney(fsum.m5)}</div>`
          : `<div class="v7-intraday-fund muted">资金行为：数据不足</div>`;
    box.innerHTML = `<div class="v7-intraday-wrap">${fbadge}<svg id="v7IntradaySvg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${grid}${sep}${prevLine}<path d="${path}" class="iv-line"/>${bars}<line id="ivX" class="iv-cross hidden"/><line id="ivY" class="iv-cross hidden"/><rect id="ivDot" class="iv-dot hidden" width="6" height="6" rx="3"/><rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent" class="iv-hit"/></svg><div id="ivTip" class="iv-tip hidden"></div></div>`;
    const svg = $("#v7IntradaySvg"),
      tip = $("#ivTip"),
      xline = $("#ivX"),
      yline = $("#ivY"),
      dot = $("#ivDot");
    function move(ev) {
      const rect = svg.getBoundingClientRect(),
        px = ((ev.clientX - rect.left) / rect.width) * W,
        idx = Math.max(
          0,
          Math.min(
            raw.length - 1,
            Math.round(((px - L) / (W - L - R)) * (raw.length - 1)),
          ),
        ),
        x = raw[idx],
        xx = sx(idx),
        yy = sy(x.price),
        pc = v7PrevClose(c, x.date) || prev,
        chg = pc ? x.price - pc : null,
        cp = pc ? x.price / pc - 1 : null;
      xline.setAttribute("x1", xx);
      xline.setAttribute("x2", xx);
      xline.setAttribute("y1", T);
      xline.setAttribute("y2", H - B);
      yline.setAttribute("x1", L);
      yline.setAttribute("x2", W - R);
      yline.setAttribute("y1", yy);
      yline.setAttribute("y2", yy);
      dot.setAttribute("x", xx - 3);
      dot.setAttribute("y", yy - 3);
      [xline, yline, dot, tip].forEach((e) => e.classList.remove("hidden"));
      tip.innerHTML = `<b>${esc(x.date || "")} ${esc(x.time || "")}</b><span>价格 ${num(x.price)}</span><span>涨跌 ${chg == null ? "—" : `${chg >= 0 ? "+" : ""}${chg.toFixed(2)}`}</span><span>涨幅 ${cp == null ? "—" : pct(cp)}</span><span>分钟成交量 ${num(x.volume)}</span>`;
      tip.style.left =
        Math.min(rect.width - 190, Math.max(8, ev.clientX - rect.left + 12)) +
        "px";
      tip.style.top = Math.max(8, ev.clientY - rect.top - 70) + "px";
      window.__V7_INTRADAY_HOVER__ = {
        index: idx,
        date: x.date,
        time: x.time,
        price: x.price,
        volume: x.volume,
        change: chg,
        change_pct: cp,
      };
    }
    svg.addEventListener("pointermove", move);
    svg.addEventListener("pointerleave", () =>
      [xline, yline, dot, tip].forEach((e) => e.classList.add("hidden")),
    );
    window.__V7_INTRADAY_STATE__ = {
      code: c.code,
      period: which,
      bars: raw.length,
      real: true,
      incrementalVolume: true,
      days: days.length,
      prevClose: prev,
      yRange: [lo, hi],
    };
  };

  renderKline = function () {
    const rows = v7SortRows(filtered());
    $("#klineList").innerHTML = rows
      .map(
        (c) =>
          `<button class="company-item ${c.code === chartCode ? "active" : ""}" data-code="${c.code}"><b>${esc(c.name)}</b><div class="code">${c.code}｜${esc(c.sector)}</div><span class="${classFor(c.change)}">${pct(c.change)}</span></button>`,
      )
      .join("");
    $$("#klineList .company-item").forEach(
      (b) => (b.onclick = () => selectChart(b.dataset.code)),
    );
    if (!chartCode || !rows.some((c) => c.code === chartCode))
      chartCode = rows[0]?.code || null;
    if (chartCode) drawCurrentChart();
    else {
      $("#chartName").textContent = "没有符合筛选的公司";
      destroyChart();
    }
  };
  function v7ScrollSelected() {
    document
      .querySelector("#klineList .company-item.active")
      ?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
  const v7SelectChart = selectChartBase;
  selectChart = function (code) {
    v7SelectChart(code);
    requestAnimationFrame(v7ScrollSelected);
  };
  const v7LoadCompanyOnline = loadCompanyOnlineBase;
  loadCompanyOnline = async function (code, opts = {}) {
    const got = await v7LoadCompanyOnline(code, opts);
    const cur = D.histories?.[code]?.intraday;
    if ((cur?.minute || []).length || (cur?.five_day || []).length) return got;
    const file = code.replace(/\./g, "_") + ".json",
      urls = [
        `https://liuyongchen1314-prog.github.io/ai-application-research-pages/data/intraday/${file}`,
      ];
    for (const u of urls) {
      try {
        const j = await fetchOne(u, 5500);
        if (j?.minute?.length || j?.five_day?.length) {
          D.histories[code] ??= {};
          D.histories[code].intraday = j;
          return { history: D.histories[code], source: "公开分时缓存" };
        }
      } catch (e) {}
    }
    return got;
  };

  let v7DetailReturn = null;
  const v7OldOpenDetailKline = openDetailKlineBase;
  openDetailKline = function () {
    const c = currentDetail();
    if (!c) return;
    const box = document.querySelector("#modal .modal-box");
    v7DetailReturn = { code: c.code, scroll: box?.scrollTop || 0 };
    v7OldOpenDetailKline();
  };
  function v7ReturnDetail() {
    const c = getCompany(v7DetailReturn?.code || chartCode);
    if (!c) return;
    openDetail(c.code, [c.code]);
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        const box = document.querySelector("#modal .modal-box");
        if (box) box.scrollTop = v7DetailReturn?.scroll || 0;
      }),
    );
  }

  function v74MarketDate(group) {
    return D.market_freshness?.[group]?.date || "数据不足";
  }
  function v74RefreshState() {
    try {
      return JSON.parse(localStorage.getItem("v76_refresh_state") || "{}");
    } catch (e) {
      return {};
    }
  }
  const V76_RELEASE = "V7.9.4",
    V76_DATA_SCHEMA = "v7-public-market-1",
    V76_CACHE_SCHEMA = "v7-browser-summary-2",
    V76_KLINE_SCHEMA = "v7-kline-cache-2",
    V76_DB_NAME = "AIResearchCache_V79";
  let v76RefreshPromise = null,
    v76SchedulerTimer = null,
    v76LastScheduledRefresh = 0;
  function v74SaveRefreshState(value) {
    try {
      localStorage.setItem("v76_refresh_state", JSON.stringify(value));
    } catch (e) {}
  }
  function v74RenderRefreshCard() {
    const card = $("#v74RefreshCard"); if(!card)return;
    const state=v74RefreshState(),enabled=state.auto!==false,last=state.lastSuccess||D.refresh_summary?.last_success?.finished_at_beijing,next=enabled?new Date(Date.now()+10*60*1000):null;
    const market=[["A股","china"],["港股","hk"],["韩国","korea"],["美股","us"]],formalDates=market.map(([name,key])=>`${name}${v74MarketDate(key)}`).join("｜"),backend=D.refresh_summary?.last_success||{},plan=D.refresh_summary?.schedule_plan||[],live=D.live_markets||v793FormalLiveFallback();
    const stale=Object.entries(live.markets||{}).filter(([,m])=>m.stale).map(([g])=>({china:'A股',hk:'港股',us:'美股',korea:'韩国'}[g]||g));
    const planned=backend.scheduled_cron?`计划规则 ${backend.scheduled_cron}`:'手动/推送触发，无计划时点';
    const actualStart=backend.actual_started_at_beijing||'—',actualFinish=backend.finished_at_beijing||'—';
    card.innerHTML=`<div class="v74-refresh-main"><div><span class="v74-eyebrow">数据控制中心</span><h2>四市场即时行情＋正式研究快照</h2><p>页面打开立即检查，之后每10分钟检查；美股常规时段后台计划每10分钟采样。GitHub Actions计划规则与实际启动/完成时间分开显示，绝不把cron当成完成时间。盘中价格只用于观察，行动策略仍使用标明日期的正式收盘快照。</p></div><div class="v74-refresh-actions"><button id="v74RefreshNow" class="v74-refresh-now">手动刷新全部数据</button><label class="v74-auto"><input id="v74AutoRefresh" type="checkbox" ${enabled?'checked':''}><span>自动检查</span></label></div></div><div class="v793-market-grid">${v793MarketCards()}</div><div class="v793-refresh-meta"><span>正式交易日｜${esc(formalDates)}</span><span>后台计划｜${esc(planned)}</span><span>实际启动｜${esc(String(actualStart).replace('T',' ').slice(0,19))}</span><span>实际完成｜${esc(String(actualFinish).replace('T',' ').slice(0,19))}</span><span>本页最近检查｜${last?esc(String(last).replace('T',' ').slice(0,19)):'尚未检查'}</span><span>下次浏览器检查｜${next?next.toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'}):'已关闭'}</span></div><div id="v74RefreshMessage" class="v74-refresh-message">${stale.length?`行情已过期：${esc(stale.join('、'))}｜继续显示最近有效数据，但不标记刷新成功`:state.lastError?`上次自动检查失败：${esc(state.lastError)}`:state.lastMessage?esc(state.lastMessage):D.valuation_meta?.single_source?'142家公司正在使用同一版估值结果':'当前为内置快照，页面已启动立即检查'}</div>`;
    $("#v74RefreshNow").onclick=async()=>{const button=$("#v74RefreshNow"),message=$("#v74RefreshMessage");button.disabled=true;button.textContent="正在检查…";try{const result=await refreshAllData({silent:true,reason:'manual'});if(!result?.success)throw new Error('没有任何数据源成功');const current=v74RefreshState();current.lastMessage=result.staleGroups?.length?`行情已过期：${result.staleGroups.join('、')}｜没有把过期行情标为刷新成功`:`${result.changed?'取得新数据':'检查完成，当前已是最新'}｜行情截至 ${latestPriceDate()}｜估值 ${D.valuation_meta?.version||'V7.9.4'}`;v74SaveRefreshState(current);message.textContent=current.lastMessage}catch(error){const current=v74RefreshState();current.lastError=String(error?.message||error);current.lastErrorAt=new Date().toISOString();v74SaveRefreshState(current);message.textContent='在线数据暂不可用，继续显示最近一次有效快照'}finally{button.disabled=false;button.textContent='手动刷新全部数据';v74RenderRefreshCard()}};
    $("#v74AutoRefresh").onchange=event=>{const current=v74RefreshState();current.auto=event.target.checked;v74SaveRefreshState(current);v74SetupAutoRefresh();v74RenderRefreshCard()};
  }
  let v74AutoTimer = null;
  function v76StopLegacyTimers() {
    [...(window.__V7_LEGACY_TIMERS__ || []), v74AutoTimer, v76SchedulerTimer]
      .filter(Boolean)
      .forEach((timer) => clearInterval(timer));
    window.__V7_LEGACY_TIMERS__ = [];
    v74AutoTimer = null;
    v76SchedulerTimer = null;
  }
  async function v76SchedulerTick() {
    if (v74RefreshState().auto === false) return;
    const now = Date.now();
    if (now - v76LastScheduledRefresh >= 10 * 60 * 1000) {
      v76LastScheduledRefresh = now;
      try {
        await refreshAllData({ silent: true, reason: "scheduler" });
      } catch (e) {
        const state=v74RefreshState();
        state.lastError=String(e?.message||e);
        state.lastErrorAt=new Date().toISOString();
        v74SaveRefreshState(state);
      }
      v74RenderRefreshCard();
    }
    checkDailyDeepRefresh();
  }
  function v74SetupAutoRefresh() {
    v76StopLegacyTimers();
    if (v74RefreshState().auto === false) return;
    v76SchedulerTimer = setInterval(v76SchedulerTick, 60 * 1000);
    v74AutoTimer = v76SchedulerTimer;
    void v76SchedulerTick();
  }
  function v74InjectRefreshCard() {
    if ($("#v74RefreshCard")) return;
    const card = document.createElement("section");
    card.id = "v74RefreshCard";
    card.className = "v74-refresh-card";
    document.querySelector("main")?.prepend(card);
    const old = $("#refreshBtn");
    if (old) old.classList.add("hidden");
    v74RenderRefreshCard();
    v74SetupAutoRefresh();
  }

  function v74CanSlimItem(letter, name, state, evidence, counter) {
    return { letter, name, state, evidence, counter };
  }
  /* [LEGACY_DISABLED_V794] CAN SLIM 前端关键词/分析师代理实现已停用。 */
  function v74CanSlimAssessment(c) {
    const cs=strategyFor(c).can_slim;
    if(cs&&Array.isArray(cs.items)&&cs.items.length===7)return strategyFor(c).can_slim;
    return{verdict:'数据不足',items:['C','A','N','S','L','I','M'].map(letter=>v74CanSlimItem(letter,letter,'unknown','后台证据未生成','不得由前端补猜')),pass_count:0,fail_count:0,data_completeness:0};
  }
  function v74CanSlimRows() {
    let rows =
      scope === "hardware"
        ? D.companies.hardware || []
        : scope === "application"
          ? D.companies.application || []
          : allCompanies();
    if (v74SoftwareOnly)
      rows = rows.filter((c) => /软件|智能体|办公|营销|内容|教育|医疗|金融科技|可观测|运维|大模型|平台/.test(c.sector));
    return rows;
  }
  function v74RenderCanSlim() {
    const panel = $("#panel-canslim");
    if (!panel) return;
    const rows = v74CanSlimRows(),
      assessments = rows.map((c) => ({ c, a: v74CanSlimAssessment(c) })),
      counts = {
        通过: assessments.filter((x) => x.a.verdict === "通过").length,
        部分通过: assessments.filter((x) => x.a.verdict === "部分通过").length,
        不通过: assessments.filter((x) => x.a.verdict === "不通过").length,
      };
    panel.innerHTML = `<div class="card v74-book-rule"><div><span class="v74-eyebrow">《笑傲股市》A股化</span><h2>CAN SLIM成长股筛选</h2><p>书中原意、A股本土化和当前反证分开显示。该模块只筛公司质量、市场和时机，不参与抬高合理价。</p></div><div class="v74-canslim-counts"><b>通过 ${counts["通过"]}</b><b>部分通过 ${counts["部分通过"]}</b><b>不通过 ${counts["不通过"]}</b></div></div><div class="card v74-local-rules"><b>A股修正</b><span>季度增长优先看累计扣非与现金流；加入涨跌停、T+1、ST、减持、解禁和再融资；机构持仓只作滞后证据；止损采用结构失效位＋仓位风险预算。</span>${scope === "application" ? `<label><input id="v74SoftwareOnly" type="checkbox" ${v74SoftwareOnly ? "checked" : ""}> 只看AI软件子集</label>` : ""}</div><div class="card"><div class="table-wrap"><table class="v74-canslim-table"><thead><tr><th>公司</th><th>结论</th><th>C/A/N/S/L/I/M通过情况</th><th>最关键反证</th><th>详情</th></tr></thead><tbody>${assessments
      .map(({ c, a }) => `<tr><td><span class="company">${esc(c.name)}</span><div class="code">${esc(c.code)}｜${esc(c.sector)}</div></td><td><span class="v74-verdict verdict-${a.verdict}">${a.verdict}</span></td><td><div class="v74-rule-grid">${a.items.map((x) => `<span class="rule-${x.state}" title="${esc(x.evidence)}"><b>${esc(x.letter)}</b> ${x.state === "pass" ? "通过" : x.state === "partial" ? "部分" : x.state === "not_applicable" ? "不适用" : "未过"}</span>`).join("")}</div></td><td>${esc(a.items.find((x) => x.state === "fail")?.counter || a.items.find((x) => x.state === "partial")?.counter || "暂无硬反证")}</td><td><button class="detail-btn" data-canslim-detail="${esc(c.code)}">查看</button></td></tr>`)
      .join("")}</tbody></table></div></div>`;
    if ($("#v74SoftwareOnly"))
      $("#v74SoftwareOnly").onchange = (event) => {
        v74SoftwareOnly = event.target.checked;
        v74RenderCanSlim();
      };
    panel.querySelectorAll("[data-canslim-detail]").forEach(
      (button) =>
        (button.onclick = () =>
          openDetail(
            button.dataset.canslimDetail,
            rows.map((x) => x.code),
          )),
    );
  }
  const v76BaseRenderCurrent = renderCurrentBase;
  renderCurrent = function () {
    if (tab === "canslim") {
      document.querySelectorAll(".panel").forEach((panel) => panel.classList.remove("active"));
      $("#commonControls")?.classList.add("hidden");
      $("#panel-canslim")?.classList.add("active");
      v74RenderCanSlim();
      return;
    }
    $("#panel-canslim")?.classList.remove("active");
    v76BaseRenderCurrent();
  };
  function v74InjectCanSlimPanel() {
    if (!NORMAL_TABS.some((x) => x[0] === "canslim"))
      NORMAL_TABS.splice(3, 0, ["canslim", "笑傲股市选股"]);
    if (!FULL_TABS.some((x) => x[0] === "canslim"))
      FULL_TABS.push(["canslim", "笑傲股市选股"]);
    if (!$("#panel-canslim")) {
      const panel = document.createElement("section");
      panel.id = "panel-canslim";
      panel.className = "panel";
      document.querySelector("main")?.appendChild(panel);
    }
    renderTabs();
  }

  function v7InjectUi() {
    document.title = "AI研究系统 V7.9.4";
    const h = document.querySelector("header .title");
    if (h) h.textContent = "AI研究系统 V7.9.4";
    const sub = document.querySelector("header .subtitle");
    if (sub)
      sub.textContent = "产业链 · 独立估值 · 相对强弱 · 风险监控 · 买点判断";
    try {
      NORMAL_TABS.forEach((x) => {
        if (x[0] === "sepa") x[1] = "趋势阶段";
      });
    } catch (e) {}
    const gateTh = document.querySelector(
      "#panel-valuation thead th:nth-child(9)",
    );
    if (gateTh) gateTh.textContent = "阶段/门禁";
    const week = $("#weekMaSelect");
    if (week) {
      week.innerHTML =
        '<option value="system">系统选择</option>' +
        Array.from({ length: 26 }, (_, i) => i + 5)
          .map((n) => `<option value="${n}">${n}周线</option>`)
          .join("");
    }
    const subCtl = $("#subIndicatorControls");
    if (subCtl && !$("#toggleFundV7")) {
      const lab = document.createElement("label");
      lab.innerHTML = '<input id="toggleFundV7" type="checkbox">资金';
      subCtl.appendChild(lab);
      $("#toggleFundV7").onchange = drawCurrentChart;
    }
    const panel = $("#panel-valuation .card");
    if (panel && !$("#v7SortBar")) {
      const bar = document.createElement("div");
      bar.id = "v7SortBar";
      bar.className = "v7-sortbar";
      bar.innerHTML = `<b>排序</b><select id="v7SortKey"><option value="canonical">系统默认顺序</option><option value="action">行动优先级</option><option value="stage">趋势阶段</option><option value="trend">趋势分</option><option value="buy">买点分</option><option value="rs">12个月RS</option><option value="quality">公司质量</option><option value="valuation">估值吸引力</option><option value="change">当日涨跌</option><option value="r5">5日强度</option></select><button id="v7SortDir" class="chip-btn">降序 ↓</button><span class="small muted">估值按板块商业模式独立计算</span>`;
      panel.prepend(bar);
      $("#v7SortKey").value = v7SortKey;
      $("#v7SortKey").onchange = (e) => {
        v7SortKey = e.target.value;
        renderValuation();
      };
      $("#v7SortDir").onclick = () => {
        v7SortDir = v7SortDir === "desc" ? "asc" : "desc";
        $("#v7SortDir").textContent =
          v7SortDir === "desc" ? "降序 ↓" : "升序 ↑";
        renderValuation();
      };
    }
    const klinePanel = $("#panel-kline");
    if (klinePanel && !$("#v7KlineSortBar")) {
      const kb=document.createElement("div");kb.id="v7KlineSortBar";kb.className="v7-sortbar";
      kb.innerHTML=`<b>K线排序</b><select id="v7KlineSortKey"><option value="canonical">系统默认顺序</option><option value="action">行动优先级</option><option value="trend">趋势分</option><option value="buy">买点分</option><option value="rs">12个月RS</option></select><span class="small muted">分数来自后台唯一策略引擎，前端不重算</span>`;
      klinePanel.prepend(kb);$("#v7KlineSortKey").value=v7SortKey;$("#v7KlineSortKey").onchange=e=>{v7SortKey=e.target.value;if($("#v7SortKey"))$("#v7SortKey").value=v7SortKey;renderKline()};
    }
    const chartTitle = document.querySelector("#panel-kline .chart-title");
    if (chartTitle && !$("#v7ReturnDetail")) {
      const b = document.createElement("button");
      b.id = "v7ReturnDetail";
      b.className = "v7-return";
      b.textContent = "← 返回公司详情";
      b.onclick = v7ReturnDetail;
      chartTitle.prepend(b);
    }
    document.addEventListener("keydown", (e) => {
      const a = document.activeElement,
        tag = a?.tagName?.toLowerCase();
      if (["input", "select", "textarea"].includes(tag)) return;
      if (tab !== "kline" || !["ArrowUp", "ArrowDown"].includes(e.key)) return;
      const rows = filtered();
      if (!rows.length) return;
      let i = Math.max(
        0,
        rows.findIndex((x) => x.code === chartCode),
      );
      i = Math.max(
        0,
        Math.min(rows.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)),
      );
      if (rows[i]?.code !== chartCode) {
        e.preventDefault();
        selectChart(rows[i].code);
      }
    });
    const observer = new MutationObserver(() => {
      document.querySelectorAll(".v7-help").forEach((x) => {
        if (!x.dataset.bound) {
          x.dataset.bound = "1";
          x.onmouseenter = () => v7Help(x.dataset.help);
        }
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
    v74InjectRefreshCard();
    v74InjectCanSlimPanel();
  }

  // 市场背景渲染：保留基础实现，再由唯一的最终实现负责中文清洗。
  function renderMarketContextBase() {
    const m = D.market_context || D.market || null;
    if (!m) {
      $("#marketContext").innerHTML =
        '<h3>市场上下文</h3><div class="muted">未取得结构化市场数据。</div>';
      return;
    }
    const china = m.china || {};
    const chinaRows = [
      ["AI硬件", china.hardware],
      ["AI应用", china.application],
    ].filter((x) => x[1]);
    const itemRows = (items) =>
      (items || [])
        .map(
          (x) =>
            `<div class="market-row"><span><b>${esc(x.name || x.ticker)}</b><small class="muted"> ${esc(x.date || "")}</small></span><span class="${classFor(x.change_pct)}">${pct(x.change_pct)}｜${num(x.close)}</span></div>`,
        )
        .join("");
    $("#marketContext").innerHTML = `<div class="section-title"><h3>市场上下文</h3><span class="badge neutral">中国 ${esc(m.snapshot_date || D.embedded_snapshot)}｜美股前一交易日｜韩国当日</span></div><div class="market-grid"><div class="market-card"><h4>中国AI板块</h4>${chinaRows.map(([name, x]) => `<div class="market-row"><span><b>${name}</b></span><span>1日 <b class="${classFor(x.median_1d)}">${pct(x.median_1d)}</b>｜5日 ${pct(x.median_5d)}｜宽度 ${pct(x.breadth)}</span></div>`).join("")}</div><div class="market-card"><h4>美国市场</h4>${itemRows(m.us?.items || []) || '<div class="muted">未取得</div>'}</div><div class="market-card"><h4>韩国市场</h4>${itemRows(m.korea?.items || []) || '<div class="muted">未取得</div>'}</div></div>`;
  }
  renderMarketContext = function () {
    renderMarketContextBase();
    const box = $("#marketContext");
    if (!box) return;
    box.querySelectorAll("pre").forEach((x) => x.remove());
    box.innerHTML = box.innerHTML
      .replace(/Yahoo chart API/g, "公开行情源")
      .replace(/ETF/g, "指数基金");
  };
  const v76BaseDeriveAttribution = deriveAttributionBase;
  deriveAttribution = function (c, stats) {
    const result = v76BaseDeriveAttribution(c, stats),
      valuation = window.__V7_VALUATION__?.[c.code],
      clean = (rows) =>
        (rows || []).filter(
          (text) => !/估值模型更新|估值待补|旧估值/.test(String(text)),
        );
    result.positive = clean(result.positive);
    result.risk = clean(result.risk);
    result.neutral = clean(result.neutral);
    result.failed = clean(result.failed);
    if (valuation) {
      const text = `当前估值：${valuation.status}（${valuation.current}）`;
      if (valuation.valuation_gate === "不通过") result.failed.push(text);
      else if (valuation.valuation_gate === "通过") result.positive.push(text);
      else result.neutral.push(text);
    }
    return result;
  };

  // 在线优先：主地址成功即使用；只有主地址失败才请求镜像，避免重复下载大快照。
  D.public_data = D.public_data || {};
  D.public_data.unified_market_urls = [
    "data/latest-v7.json",
    "https://liuyongchen1314-prog.github.io/ai-application-research-pages/data/latest-v7.json",
    "https://liuyongchen1314-prog.github.io/ai-application-research-pages/mirror/latest-v7.json",
    ...(D.public_data.unified_market_urls || []),
  ].filter((x, i, a) => x && a.indexOf(x) === i);
  function v76ValidatePayload(d) {
    if (!d || typeof d !== "object") throw new Error("正式数据为空");
    if (d.schema !== V76_DATA_SCHEMA)
      throw new Error(`正式数据协议不匹配：${d.schema || "缺失"}`);
    const total = totalCompanies(),
      cov = d.coverage || {};
    if (+cov.total !== total || +cov.histories !== total || +cov.quotes !== total)
      throw new Error(`正式数据覆盖不完整：${JSON.stringify(cov)}`);
    if (d.valuation_current && Object.keys(d.valuation_current).length !== total)
      throw new Error("正式估值覆盖不完整");
    if (!d.strategy_current || Object.keys(d.strategy_current).length !== total)
      throw new Error("正式策略覆盖不完整");
    for (const key of ["china", "hk", "korea", "us"]) {
      const fresh = d.market_freshness?.[key];
      if (!fresh?.fresh || !fresh?.date)
        throw new Error(`${key}市场没有通过完整交易日门禁`);
    }
    const quoteRows = Object.values(d.quotes || {});
    if (quoteRows.length !== total || quoteRows.some((x) => !x?.date || x.session_complete !== true))
      throw new Error("正式报价缺少标准交易日或收盘完成标记");
    for (const company of allCompanies()) {
      const quote=d.quotes?.[company.code], expected=company.code.endsWith(".HK")?d.market_freshness.hk.date:d.market_freshness.china.date;
      if (quote?.date!==expected) throw new Error(`${company.code}报价日期${quote?.date||"缺失"}与市场完整交易日${expected}不一致`);
    }
    const manifest = d.intraday || {},
      available = manifest.available_codes;
    if (Array.isArray(available)) {
      const unique = new Set(available);
      if (
        unique.size !== available.length ||
        +manifest.success !== unique.size ||
        +cov.intraday !== unique.size
      )
        throw new Error("分时覆盖数字与实体清单不一致");
    }
    return d;
  }
  fetchFirst = async function (urls, timeout = 7000) {
    const errors = [];
    for (const url of urls || []) {
      try {
        return { url, data: await fetchOne(url, timeout) };
      } catch (error) {
        errors.push(`${url}: ${error?.message || error}`);
      }
    }
    throw new Error(errors.join(" | ") || "在线数据暂不可用");
  };
  refreshPublicHardware = async function ({ silent = false } = {}) {
    try {
      const result = await fetchFirst(D.public_data.unified_market_urls || []),
        market = v76ValidatePayload(result.data),
        coverage = market.coverage || {};
      mergeLive(market);
      liveMeta.github_coverage = `${coverage.quotes}/${coverage.total}`;
      liveMeta.snapshot = market.snapshot_date || latestPriceDate();
      liveMeta.source = "正式统一数据";
      liveMeta.github_diag = [
        `market ${market.snapshot_date || "—"} ${coverage.quotes}/${coverage.total}`,
        `history ${coverage.histories}/${coverage.total}`,
        `intraday ${coverage.intraday || 0}/${coverage.total}`,
      ];
      liveMeta.github_error = "";
      saveCache(market);
      if (!silent) {
        renderCurrent();
        updateStatus();
      }
      return { success: true, source: result.url, coverage };
    } catch (error) {
      liveMeta.github_error = error?.message || String(error);
      if (!silent) console.warn("正式数据刷新失败", error);
      throw error;
    }
  };
  updateStatus = function () {
    const total = totalCompanies(),
      ds = latestPriceDate(),
      stale = isStale(ds);
    $("#feedStatus").textContent =
      `${liveMeta.source || "内置发布快照"}｜行情截至 ${ds}｜覆盖 ${priceDateCoverage(ds)}/${total}｜程序 ${V76_RELEASE}${stale ? "｜缓存数据" : ""}`;
    $("#feedStatus").classList.toggle("stale", stale);
    $("#feedStatus").classList.toggle("ok", !stale);
    $("#dataBoundary").textContent =
      `当前显示截至 ${ds}；共 ${total} 家（硬件/基础设施 ${D.companies.hardware.length}，应用 ${D.companies.application.length}）。A股 ${v74MarketDate("china")}｜港股 ${v74MarketDate("hk")}｜韩国 ${v74MarketDate("korea")}｜美股 ${v74MarketDate("us")}。${stale ? "当前为缓存数据。" : ""}`;
  };
  function v76OpenDb() {
    return new Promise((resolve, reject) => {
      if (!window.indexedDB) return reject(new Error("IndexedDB不可用"));
      const request = indexedDB.open(V76_DB_NAME, 1);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains("company")) db.createObjectStore("company");
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
  openCacheDb = v76OpenDb;
  const v76BaseDbPut = dbPutBase,
    v76BaseDbGet = dbGetBase;
  dbPut = function (key, value) {
    return v76BaseDbPut(key, {
      schema: V76_KLINE_SCHEMA,
      release: V76_RELEASE,
      payload: value,
    });
  };
  dbGet = async function (key) {
    const row = await v76BaseDbGet(key);
    if (row?.schema !== V76_KLINE_SCHEMA || row?.release !== V76_RELEASE) return null;
    return row.payload || (row.history ? { history: row.history, saved_at: row.saved_at } : null);
  };
  function v76SaveHistories(histories, snapshotDate) {
    if (!histories || typeof histories !== "object") return Promise.resolve();
    return v76OpenDb()
      .then(
        (db) =>
          new Promise((resolve, reject) => {
            const tx = db.transaction("company", "readwrite"),
              store = tx.objectStore("company");
            Object.entries(histories).forEach(([code, history]) =>
              store.put(
                {
                  schema: V76_KLINE_SCHEMA,
                  release: V76_RELEASE,
                  snapshot_date: snapshotDate || "",
                  history,
                },
                code,
              ),
            );
            tx.oncomplete = () => {
              db.close();
              resolve();
            };
            tx.onerror = () => {
              db.close();
              reject(tx.error);
            };
          }),
      )
      .catch((error) => console.warn("K线缓存写入失败", error));
  }
  function v76LoadHistories() {
    return v76OpenDb().then(
      (db) =>
        new Promise((resolve, reject) => {
          const tx = db.transaction("company", "readonly"),
            request = tx.objectStore("company").openCursor(),
            histories = {};
          request.onsuccess = () => {
            const cursor = request.result;
            if (cursor) {
              const row = cursor.value;
              if (
                row?.schema === V76_KLINE_SCHEMA &&
                row?.release === V76_RELEASE &&
                row?.history?.daily &&
                !String(cursor.key).startsWith("__")
              )
                histories[String(cursor.key)] = row.history;
              cursor.continue();
              return;
            }
            db.close();
            resolve(histories);
          };
          request.onerror = () => {
            db.close();
            reject(request.error);
          };
        }),
    );
  }
  saveCache = function (j) {
    try {
      const slim = {
        schema: V76_CACHE_SCHEMA,
        release: V76_RELEASE,
        snapshot_date: j.snapshot_date || latestPriceDate(),
        generated_at_cn:
          j.generated_at_cn || j.generated_at || new Date().toISOString(),
        quotes: j.quotes || {},
        market_freshness: j.market_freshness || D.market_freshness || {},
        valuation_meta: j.valuation_meta || D.valuation_meta || {},
        refresh_summary: j.refresh_summary || D.refresh_summary || {},
        coverage: j.coverage || {},
      };
      localStorage.setItem("v76_summary_cache", JSON.stringify(slim));
      v76SaveHistories(j.histories || {}, slim.snapshot_date);
    } catch (e) {
      console.warn("V7缓存不可用", e);
    }
  };
  loadCache = function () {
    try {
      const j = JSON.parse(localStorage.getItem("v76_summary_cache") || "null");
      if (
        j &&
        j.schema === V76_CACHE_SCHEMA &&
        j.release === V76_RELEASE &&
        /^V7\.9(?:\.\d+)?$/.test(String(j.valuation_meta?.version || "")) &&
        String(j.snapshot_date || "") >= String(D.embedded_snapshot || "")
      ) {
        mergeLive(j);
        liveMeta = {
          source: "浏览器最近有效缓存",
          snapshot: j.snapshot_date,
          generated: j.generated_at_cn || j.generated_at,
        };
      }
      v76LoadHistories()
        .then((histories) => {
          if (!Object.keys(histories || {}).length) return;
          mergeLive({ histories });
          v7ClearCaches();
          renderCurrent();
          updateStatus();
        })
        .catch(() => {});
    } catch (e) {
      console.warn("V7.9.4缓存不可用", e);
    }
  };
  refreshAllData = async function (o = {}) {
    if (v76RefreshPromise) return v76RefreshPromise;
    v76RefreshPromise = (async () => {
      const before={snapshot:D.snapshot_date||D.embedded_snapshot,generated:D.generated_at_cn||D.generated_at,prices:allCompanies().map(c=>`${c.code}:${c.price}:${c.price_date}`).join('|')};
      const results = await Promise.allSettled([
        refreshPublicHardware({ silent: true }),
        refreshRealtimeQuotes({ silent: true }),
        refreshBenchmarkDates(),
        refreshLiveMarkets(),
      ]);
      const selected = chartCode || filtered()[0]?.code;
      let company = null;
      if (selected) company = await loadCompanyOnline(selected, { silent: true });
      const publicOk = results[0].status === "fulfilled" && results[0].value?.success,
        quoteCount = results[1].status === "fulfilled" ? +results[1].value?.updated || 0 : 0,
        companyOk = !!company?.history,
        liveOk = results[3].status === "fulfilled" && results[3].value?.marketCount === 4,
        staleGroups = results[3].status === "fulfilled" ? (results[3].value?.staleGroups || []) : ["四市场状态未知"],
        success = (!!publicOk || quoteCount === totalCompanies()) && liveOk;
      if (!success) throw new Error(`完整刷新失败：正式快照${publicOk?'成功':'失败'}，公司实时行情${quoteCount}/${totalCompanies()}，四市场${liveOk?'4/4':'未完成'}；单家公司更新不计作全量成功`);
      v7ApplyValuation();
      v7ClearCaches();
      populateSector();
      renderCurrent();
      updateStatus();
      const current = v74RefreshState();
      current.lastSuccess = new Date().toISOString();
      current.lastSource = publicOk ? "正式统一数据" : quoteCount > 0 ? "实时行情" : "公司行情";
      current.lastError = "";
      current.lastErrorAt = "";
      v74SaveRefreshState(current);
      v74RenderRefreshCard();
      if (!o.silent)
        $("#feedStatus").textContent =
          `${staleGroups.length?"行情已过期":"刷新完成"}｜行情截至 ${latestPriceDate()}｜覆盖 ${priceDateCoverage(latestPriceDate())}/${totalCompanies()}｜程序 ${V76_RELEASE}`;
      const afterPrices=allCompanies().map(c=>`${c.code}:${c.price}:${c.price_date}`).join('|');
      const changed=before.snapshot!==(D.snapshot_date||D.embedded_snapshot)||before.generated!==(D.generated_at_cn||D.generated_at)||before.prices!==afterPrices;
      return { success: true, changed, publicOk: !!publicOk, quoteCount, companyOk, liveOk, marketCount:4, staleGroups, results };
    })();
    try {
      return await v76RefreshPromise;
    } finally {
      v76RefreshPromise = null;
    }
  };
  window.__V7__ = {
    v7Temperature,
    v7BuyPoint,
    v7FundFlow,
    v7Profile,
    v7Chip,
    v7Avwap,
    v7Rrg,
    v7Relative,
    v7SectorRs,
    v7Risk,
    v7GateState,
    v7MarketGate,
    v7FundamentalGate,
    v7TrendGate,
    v7VolumeGate,
    v7SectorGate,
    v7ValGate,
    v7Zh,
    v7AnchorMode,
    v7Avwap,
    v7FundSeriesForRows,
  };

  let v73ActionFilter = "all",
    v73StageFilter = "all";
  
  
  
  function v73Action(c) {
    return strategyFor(c).action || "等待趋势修复";
  }
  function v73Reason(c) {
    return strategyFor(c).reason || "等待趋势、估值和风险条件共同确认";
  }
  function v73Rows() {
    return v7SortRows(filtered()).filter(
      (c) =>
        (v73ActionFilter === "all" || v73Action(c) === v73ActionFilter) &&
        (v73StageFilter === "all" ||
          String(strategyFor(c).trend_stage || '')===v73StageFilter),
    );
  }
  function v73Filters(id) {
    return `<div id="${id}" class="v73-filter"><b>筛选</b>${["all","重点参与","小仓试错","临近触发","突破后确认","缩量回踩观察","普通候选","等待趋势修复","不追/回避","已持仓继续持有","已持仓减仓或退出"].map((x) => `<button class="chip-btn ${v73ActionFilter === x ? "active" : ""}" data-v73-action="${x}">${x === "all" ? "全部" : x}</button>`).join("")}<span class="split"></span>${["all","第二阶段确认","第二阶段候选","第一阶段","第三阶段","第四阶段","数据不足"].map((x) => `<button class="chip-btn ${v73StageFilter === x ? "active" : ""}" data-v73-stage="${x}">${x === "all" ? "全部阶段" : x}</button>`).join("")}</div>`;
  }
  function v73BindFilters(root) {
    root.querySelectorAll("[data-v73-action]").forEach(
      (b) =>
        (b.onclick = () => {
          v73ActionFilter = b.dataset.v73Action;
          renderValuation();
          renderSepa();
        }),
    );
    root.querySelectorAll("[data-v73-stage]").forEach(
      (b) =>
        (b.onclick = () => {
          v73StageFilter = b.dataset.v73Stage;
          renderValuation();
          renderSepa();
        }),
    );
  }
  renderValuation = function () {
    const rows = v73Rows(),
      scopeRows =
        scope === "hardware"
          ? D.companies.hardware || []
          : scope === "application"
            ? D.companies.application || []
            : [
                ...(D.companies.hardware || []),
                ...(D.companies.application || []),
              ],
      counts = Object.fromEntries(
        ["重点参与","小仓试错","临近触发","突破后确认","缩量回踩观察","普通候选","等待趋势修复","不追/回避","已持仓继续持有","已持仓减仓或退出"].map((k) => [
          k,
          scopeRows.filter((c) => v73Action(c) === k).length,
        ]),
      ),
      reasonable = scopeRows.filter((c) =>
        ["明显低估", "合理偏低", "合理区间"].includes(
          window.__V7_VALUATION__?.[c.code]?.status,
        ),
      ).length;
    const sum = $("#valuationSummary");
    if (sum)
      sum.innerHTML = `<div class="metric"><span>合理或更低</span><b>${reasonable} / ${scopeRows.length}</b></div><div class="metric good"><span>重点参与 / 小仓试错</span><b>${counts["重点参与"]} / ${counts["小仓试错"]}</b></div><div class="metric"><span>临近触发 / 突破确认</span><b>${counts["临近触发"]} / ${counts["突破后确认"]}</b></div><div class="metric warn"><span>等待修复 / 不追回避</span><b>${counts["等待趋势修复"]} / ${counts["不追/回避"]}</b></div>`;
    const body = $("#valuationBody");
    if (!body) return;
    const card = body.closest(".card");
    let bar = $("#v73ValFilters");
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "v73ValFilters";
      card.prepend(bar);
    }
    bar.innerHTML = v73Filters("v73ValFiltersInner");
    v73BindFilters(bar);
    const head = body.closest("table").querySelector("thead tr");
    head.innerHTML =
      "<th>公司 / 最新价</th><th>板块 / 质量</th><th>当前研究区间 / 6个月情景</th><th>估值位置 / 证据</th><th>盈利预期</th><th>趋势</th><th>行动</th><th>最关键原因</th><th>详情</th>";
    body.innerHTML = rows
      .map((c) => {
        const v = window.__V7_VALUATION__?.[c.code] || {},
          a = v73Action(c),
          trend = v74TrendSignal(c);
        const s=strategyFor(c), f=v79ForwardScenario(v);
        return `<tr><td><span class="company">${esc(c.name)}</span><div class="v74-live-price">${num(c.price)} <span class="${classFor(c.change)}">${pct(c.change)}</span></div><div class="code">${esc(c.code)}｜${esc(c.price_date || latestPriceDate())}</div></td><td>${esc(c.sector)}<div class="small muted">质量 ${num(c.quality)}｜${esc(c.tier||'—')}</div></td><td class="range"><b>当前 ${esc(v.current || V74_VALUATION_PENDING)}</b><div class="v74-calendar-price">${esc(f.label)} ${esc(f.range)}${f.available && f.date ? `｜截至 ${esc(f.date)}` : ""}</div></td><td><b>${esc(v.status || V74_VALUATION_PENDING)}</b><div class="small muted">${esc(v.confidence || "D")}级｜${esc(v.evidence_state || v.audit_status || "待复核")}</div></td><td>${esc(v.revision_gate || "数据不足")}<div class="small muted">财报 ${esc(v.realization_gate || "数据不足")}</div></td><td><span class="v74-mini-trend tone-${trend.tone}"><b>${esc(trend.label)}</b><em>${trend.score == null ? "—" : trend.score + "分"}</em></span><div class="small muted">${esc(s.trend_stage || "数据不足")}</div></td><td><span class="v73-action a-${a}">${esc(a)}</span></td><td>${esc(s.reason || v73Reason(c))}</td><td><button class="detail-btn" data-detail="${esc(c.code)}">查看</button></td></tr>`;
      })
      .join("");
    body.querySelectorAll("[data-detail]").forEach(
      (b) =>
        (b.onclick = () =>
          openDetail(
            b.dataset.detail,
            rows.map((x) => x.code),
          )),
    );
  };
  renderSepa = function () {
    const rows = v73Rows(),
      panel = $("#panel-sepa .card");
    let bar = $("#v73SepaFilters");
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "v73SepaFilters";
      panel.prepend(bar);
    }
    bar.innerHTML = v73Filters("v73SepaFiltersInner");
    v73BindFilters(bar);
    $("#sepaBody").innerHTML = rows
      .map(
        (c) =>
          `<tr><td><button class="detail-btn" data-code="${c.code}"><span class="company">${esc(c.name)}</span></button><div class="code">${c.code}</div></td><td><b>${esc(strategyFor(c).trend_stage||"数据不足")}</b><div class="small muted">趋势质量 ${strategyNumber(strategyFor(c).trend_quality_score,0)}分</div></td><td>${(c.sepa?.positive || []).map((x) => `<span class="badge positive">${esc(x)}</span>`).join("") || "—"}</td><td>${(c.sepa?.risk || []).map((x) => `<span class="badge risk">${esc(x)}</span>`).join("") || "—"}</td><td>${(c.sepa?.failed || []).map((x) => `<div>• ${esc(x)}</div>`).join("")}</td><td><span class="v73-action a-${v73Action(c)}">${v73Action(c)}</span><div class="small muted">${esc(v73Reason(c))}</div></td></tr>`,
      )
      .join("");
    $$("#sepaBody .detail-btn").forEach(
      (b) =>
        (b.onclick = () =>
          openDetail(
            b.dataset.code,
            rows.map((x) => x.code),
          )),
    );
  };
  function v73Header() {
    document.title = "AI研究系统 V7.9.4";
    const h = document.querySelector("header .title");
    if (h) h.textContent = "AI研究系统 V7.9.4";
    const s = $("#v7SortBar .small.muted");
    if (s) s.textContent = "142家公司均有数值估值范围；证据不足时扩大区间并明确降级";
    document.querySelectorAll("#v72Methods").forEach((n) => n.remove());
  }
  // V7.9 唯一集成层：详情、在线合并和启动逻辑各只注册一次。
  const v76BaseRenderDetail = renderDetailBase;
  renderDetail = function () {
    v76BaseRenderDetail();
    const c = currentDetail(),
      v = window.__V7_VALUATION__?.[c?.code],
      body = $("#modalBody");
    if (!c || !v || !body) return;
    body.querySelectorAll(".v7-detail-model").forEach((n) => n.remove());
    [...body.children].forEach((node) => {
      if (node.querySelector("h3")?.textContent.trim() === "估值概览") node.remove();
    });
    const d = v.data_inputs || {},
      card = document.createElement("div");
    card.className = "card v7-detail-model";
    const trend = v74TrendSignal(c),
      institution = v.institution_check,
      compactNumber = (value, digits = 2) => {
        const n = Number(value);
        if (!Number.isFinite(n)) return "—";
        return n.toFixed(Math.abs(n) < 1 ? Math.max(3, digits) : digits).replace(/\.?0+$/, "");
      },
      eps26 = d.consensus_2026_eps ?? v.eps_2026,
      eps27 = d.consensus_2027_eps ?? v.eps_2027,
      profitYoy = d.deduct_net_profit_yoy ?? d.net_profit_yoy,
      analystCount = d.analyst_count ?? institution?.analyst_count,
      strategy=strategyFor(c),
      formal=!!v.formal_closed,
      forward=v79ForwardScenario(v);
    card.innerHTML = `<div class="v74-detail-heading"><h3>估值证据与独立行动</h3><span>估值模型 V7.9.4</span></div><div class="v7-detail-model-grid"><div><span>当前研究区间</span><b>${esc(v.current || V74_VALUATION_PENDING)}</b></div><div><span>安全边际区</span><b>${esc(v.buy_zone || "—")}</b></div><div><span>${esc(forward.label)}</span><b>${esc(forward.range)}</b></div><div><span>证据状态</span><b>${esc(v.evidence_state||v.audit_status||"待复核")}</b></div></div><div class="v74-detail-pills"><span>置信度 ${esc(v.confidence || "—")}</span><span>${formal?"正式闭环":"研究区间"}</span><span>行情日 ${esc(v.price_date||c.price_date||"—")}</span></div><p><b>估值位置：</b>${esc(v.status || V74_VALUATION_PENDING)}｜<b>独立行动：</b>${esc(strategy.action||"等待趋势修复")}｜<b>趋势：</b>${esc(trend.label)} ${trend.score == null ? "" : trend.score + "分"}</p><p><b>行动原因：</b>${esc(strategy.reason||"等待趋势、量价和风险条件共同确认")}</p><p><b>六个月情景说明：</b>${esc(forward.note)}${forward.available && forward.date ? `｜截至 ${esc(forward.date)}` : ""}。这是盈利与估值假设下的合理价值测算，不是未来股价预测；未来12个月目标已取消公开展示。</p><p><b>主模型：</b>${esc(v.primary_model || "—")}｜<b>交叉验证：</b>${esc(v.cross_check_model || "—")}｜<b>依据：</b>${esc(v.valuation_basis || v.model_note || "—")}</p><p><b>关键数据：</b>2026年预测EPS ${compactNumber(eps26)}｜2027年预测EPS ${compactNumber(eps27)}｜最新扣非/归母利润同比 ${compactNumber(profitYoy, 1)}%｜覆盖机构 ${Number.isFinite(+analystCount) ? Math.round(+analystCount) : "—"}家</p><p><b>机构交叉：</b>${institution ? `${esc(institution.range)}｜${institution.overlap ? "与模型有重叠" : "与模型差异较大，需复核"}` : "暂无结构化目标带"}。机构只作交叉验证，不反推合理价。</p><p class="small muted">行情变化只更新估值位置；只有财报、盈利预期、股本、公司行动或业务结构等估值输入改变，才重算合理价值。完整模型和版本变化记录在后台审计文件中。</p>`;
    body.prepend(card);
  };

  const v76BaseMergeLive = mergeLiveBase;
  mergeLive = function (j) {
    const verified = (D.risk_events || []).filter(
      (x) => x.id === "20260804-cpo-us-risk",
    );
    v76BaseMergeLive(j);
    if (j.benchmarks)
      D.benchmarks = { ...(D.benchmarks || {}), ...j.benchmarks };
    if (j.fund_flows)
      D.fund_flows = { ...(D.fund_flows || {}), ...j.fund_flows };
    if (Array.isArray(j.risk_events)) {
      D.risk_events = [...j.risk_events];
      verified.forEach((x) => {
        if (!D.risk_events.some((y) => y.id === x.id)) D.risk_events.push(x);
      });
    }
    if (j.market_freshness) D.market_freshness = j.market_freshness;
    if (j.live_markets) D.live_markets = j.live_markets;
    if (j.consensus_history) D.consensus_history = j.consensus_history;
    if (j.company_financials) {
      D.company_financials = j.company_financials;
      Object.entries(j.company_financials).forEach(([code, value]) => {
        const company = getCompany(code);
        if (company) company.live_financials = value;
      });
    }
    if (j.valuation_current) {
      D.valuation_current = j.valuation_current;
      window.__V7_VALUATION__ = j.valuation_current;
      D.v7.valuation = j.valuation_current;
    }
    if (j.strategy_current) D.strategy_current = j.strategy_current;
    if (j.strategy_meta) D.strategy_meta = j.strategy_meta;
    if (j.valuation_meta) D.valuation_meta = j.valuation_meta;
    if (j.refresh_summary) D.refresh_summary = j.refresh_summary;
    if (j.fund_flow_summary) D.fund_flow_summary = j.fund_flow_summary;
    if (j.quotes) D.quotes = j.quotes;
    if (j.generated_at_cn) D.generated_at_cn = j.generated_at_cn;
    if (j.generated_at) D.generated_at = j.generated_at;
    if (j.snapshot_date) D.snapshot_date = j.snapshot_date;
    if (j.embedded_snapshot) D.embedded_snapshot = j.embedded_snapshot;
    v7ApplyValuation();
  };

  document.addEventListener("DOMContentLoaded", () => {
    init();
    v7InjectUi();
    v7ApplyValuation();
    v73Header();
    v74RenderRefreshCard();
    if (tab === "valuation") renderValuation();
    if (tab === "kline" && chartCode) drawCurrentChart();
    window.__V794_AUTHORITY__={valuation:'scripts/valuation_core.py',strategy:'scripts/strategy_core.py',marketClock:'scripts/market_clock.py',publish:'scripts/build_public_site.py',frontendRole:'display-and-sort-only',legacyFrontendCalculatorsDisabled:true};
    window.__V79_RUNTIME__ = {
      release: V76_RELEASE,
      dataSchema: V76_DATA_SCHEMA,
      dbName: V76_DB_NAME,
      refresh: (options = {}) => refreshAllData(options),
      state: () => ({
        schedulerActive: !!v76SchedulerTimer,
        refreshLocked: !!v76RefreshPromise,
        legacyTimers: (window.__V7_LEGACY_TIMERS__ || []).filter(Boolean).length,
        latestPriceDate: latestPriceDate(),
        latestCoverage: priceDateCoverage(latestPriceDate()),
        marketFreshness: D.market_freshness,
        liveMarkets: D.live_markets,
      }),
    };
    window.__V76_RUNTIME__ = window.__V79_RUNTIME__;
  });

  Object.assign(window.__V7__, {
    v7ValStatus,
    v7ValGate,
    v7ApplyValuation,
    v74TrendSignal,
    v74CanSlimAssessment,
    v73Action,
    v73Reason,
    v7ValGate,
  });
})();
