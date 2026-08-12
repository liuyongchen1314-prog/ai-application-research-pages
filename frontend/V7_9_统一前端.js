/* AI研究系统 V7.9 统一前端源码：以V7.6完整交互为母版，估值与操作策略使用独立数据层。 */

const D=window.__V7_DATA__;
const BUILD={version:'V7.9.3',builtAt:'2026-08-12T18:30:00+08:00'};

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
 'AI网络 / 光互连 / CPO':{doing:'解决大规模集�