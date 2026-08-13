import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import chromium from "@sparticuz/chromium";
import puppeteer from "puppeteer-core";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const publicRoot = path.join(root, "docs", "public_v7");
const resultsRoot = path.join(root, "test-results", "browser-v793");
fs.mkdirSync(resultsRoot, { recursive: true });
const fontBytes = fs.readFileSync(path.join(root, "node_modules", "@fontsource", "noto-sans-sc", "files", "noto-sans-sc-chinese-simplified-400-normal.woff2"));
const fontCss = `@font-face{font-family:'V793 Noto Sans SC';font-style:normal;font-weight:100 900;src:url(data:font/woff2;base64,${fontBytes.toString("base64")}) format('woff2')}html,body,button,input,select,textarea{font-family:'V793 Noto Sans SC','Microsoft YaHei',sans-serif!important}`;

const mime = { ".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8" };
const server = http.createServer((request, response) => {
  const urlPath = decodeURIComponent((request.url || "/").split("?", 1)[0]);
  const requested = path.resolve(publicRoot, "." + (urlPath === "/" ? "/index.html" : urlPath));
  if (!requested.startsWith(publicRoot + path.sep) || !fs.existsSync(requested) || !fs.statSync(requested).isFile()) {
    response.writeHead(404).end("not found");
    return;
  }
  response.writeHead(200, { "content-type": mime[path.extname(requested)] || "application/octet-stream", "cache-control": "no-store" });
  fs.createReadStream(requested).pipe(response);
});

await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const address = server.address();
const baseUrl = `http://127.0.0.1:${address.port}`;
const executablePath = await chromium.executablePath();
const browser = await puppeteer.launch({ executablePath, headless: true, args: chromium.args });

const reports = [];
let failed = false;
function check(value, message) {
  if (!value) throw new Error(message);
}

for (const profile of [
  { name: "desktop", viewport: { width: 1680, height: 1100, deviceScaleFactor: 1 } },
  { name: "mobile", viewport: { width: 390, height: 844, deviceScaleFactor: 1 } },
]) {
  const page = await browser.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.setViewport(profile.viewport);
  await page.setRequestInterception(true);
  page.on("request", (request) => {
    const url = request.url();
    if (/qt\.gtimg\.cn|web\.ifzq\.gtimg\.cn/.test(url)) request.abort("blockedbyclient");
    else request.continue();
  });
  const report = { profile: profile.name };
  try {
    await page.goto(baseUrl + "/index.html", { waitUntil: "networkidle0", timeout: 60000 });
    await page.addStyleTag({ content: fontCss });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForFunction(() => window.__V79_RUNTIME__?.release === "V7.9.4", { timeout: 30000 });
    const initial = await page.evaluate(() => ({
      title: document.title,
      bodyWidth: document.body.scrollWidth,
      viewportWidth: document.documentElement.clientWidth,
      markets: [...document.querySelectorAll("[data-live-market]")].map((node) => node.textContent),
      refreshText: document.querySelector("#v74RefreshNow")?.textContent,
      release: window.__V79_RUNTIME__.release,
      schedulerActive: window.__V79_RUNTIME__.state().schedulerActive,
      authority: window.__V794_AUTHORITY__,
      liveMarkets: window.__V79_RUNTIME__.state().liveMarkets,
      liveFingerprint: JSON.stringify(Object.values(window.__V79_RUNTIME__.state().liveMarkets?.markets || {}).map(m => [m.market, m.sampled_at, m.sample_date, m.last, m.source])),
      strategyDate: window.__V7_DATA__.snapshot_date,
    }));
    check(initial.title.includes("V7.9.4"), "title is not V7.9.4");
    check(initial.markets.length === 4 && initial.markets.every((text) => text.includes("%")), "four-market rise/fall cards are incomplete");
    check(initial.refreshText === "手动刷新全部数据", "manual refresh button has the wrong contract");
    check(initial.schedulerActive, "ten-minute browser scheduler is inactive");
    check(initial.authority?.frontendRole === 'display-and-sort-only' && initial.authority?.legacyFrontendCalculatorsDisabled === true, 'frontend authority contract is missing');
    check(initial.liveMarkets?.market_count === 4 && initial.liveMarkets?.separate_intraday_price_from_close_strategy === true, 'intraday/close-strategy separation missing');
    check(initial.bodyWidth <= initial.viewportWidth + 2, `body overflow ${initial.bodyWidth}/${initial.viewportWidth}`);
    const marketAudit = await page.evaluate(() => [...document.querySelectorAll('[data-live-market]')].map((node) => ({
      group: node.dataset.liveMarket, phase: node.dataset.marketPhase, freshness: node.dataset.marketFreshness, sampleDate: node.dataset.marketSampleDate, text: node.textContent || ''
    })));
    check(marketAudit.length === 4, 'market audit cards != 4');
    for (const m of marketAudit) {
      check(Boolean(m.phase) && Boolean(m.sampleDate), `${m.group} missing phase/sample date`);
      check(/来源/.test(m.text) && /实际采样/.test(m.text) && /文件生成/.test(m.text) && /数据年龄/.test(m.text), `${m.group} freshness evidence not rendered`);
      if (m.freshness === 'stale') check(/行情已过期/.test(m.text), `${m.group} stale data is shown as success`);
    }

    await page.click("#v74RefreshNow");
    await page.waitForFunction(() => {
      const button = document.querySelector("#v74RefreshNow");
      const message = document.querySelector("#v74RefreshMessage")?.textContent || "";
      return !button?.disabled && /(取得新行情|检查完成，当前行情未变化|行情已过期|在线数据暂不可用，继续显示最近一次有效快照|上次自动检查失败)/.test(message);
    }, { timeout: 45000 });
    report.manualRefresh = await page.$eval("#v74RefreshMessage", (node) => node.textContent);
    const refreshState = await page.evaluate(() => ({
      fingerprint: JSON.stringify(Object.values(window.__V79_RUNTIME__.state().liveMarkets?.markets || {}).map(m => [m.market, m.sampled_at, m.sample_date, m.last, m.source])),
      message: document.querySelector("#v74RefreshMessage")?.textContent || "",
    }));
    if (/取得新行情/.test(refreshState.message)) check(refreshState.fingerprint !== initial.liveFingerprint, "manual refresh claimed new market data but market fingerprint did not change");
    const strategyAfterRefresh = await page.evaluate(() => Object.keys(window.__V7_DATA__?.strategy_current || {}).length);
    check(strategyAfterRefresh === 142, `manual refresh destroyed close-strategy snapshot: ${strategyAfterRefresh}/142`);
    const marketsAfterRefresh = await page.$$eval("[data-live-market]", (nodes) => nodes.map((node) => node.textContent));
    check(marketsAfterRefresh.length === 4 && marketsAfterRefresh.every((text) => text.includes("%")), "manual refresh fallback damaged four-market cards");

    await page.click('[data-scope="full"]');
    await page.click('[data-tab="strategy"]');
    await new Promise((resolve) => setTimeout(resolve, 750));
    const strategyDiag = await page.evaluate(() => ({count: document.querySelectorAll('.strategy-company').length, text: document.querySelector('#strategyContent')?.textContent?.slice(0,600) || '', htmlLength: document.querySelector('#strategyContent')?.innerHTML?.length || 0}));
    check(strategyDiag.count > 0, `strategy render failed: count=${strategyDiag.count} html=${strategyDiag.htmlLength} text=${strategyDiag.text} pageErrors=${pageErrors.join(' | ')}`);
    const actions = await page.$$eval("[data-strategy-action]", (nodes) => [...new Set(nodes.map((node) => node.dataset.strategyAction).filter((value) => value && value !== "all"))]);
    const expectedActions=['重点参与','小仓试错','临近触发','突破后确认','缩量回踩观察','普通候选','等待趋势修复','不追/回避','已持仓继续持有','已持仓减仓或退出'];
    check(expectedActions.every((x)=>actions.includes(x)), `strategy action filters incomplete: ${actions.join(',')}`);
    const invalidHoldingActions=await page.evaluate(()=>Object.entries(window.__V7_DATA__.strategy_current||{}).filter(([code,s])=>String(s.action||'').startsWith('已持仓') && !window.__V7_DATA__.user_positions?.[code]));
    check(invalidHoldingActions.length===0, `unheld stocks have holding actions: ${invalidHoldingActions.map(x=>x[0]).join(',')}`);
    for (const action of actions) {
      await page.evaluate((value) => document.querySelector(`[data-strategy-action="${CSS.escape(value)}"]`)?.click(), action);
      await new Promise((resolve) => setTimeout(resolve, 30));
      const count = await page.$$eval(".strategy-company", (nodes) => nodes.length);
      const expected = await page.evaluate((value) => window.__V7_DATA__.strategy_meta.action_counts[value] || 0, action);
      check(count === expected, `${action} filter shows ${count}, expected ${expected}`);
    }
    const scoreAudit=await page.evaluate(()=>Object.values(window.__V7_DATA__.strategy_current||{}).map(s=>({a:s.action,t:s.trend_stage,ts:s.trend_quality_score,bs:s.buy_point_score,dc:s.data_completeness,blockers:s.blockers||[]})));
    check(scoreAudit.length===142,'strategy rows != 142');
    check(scoreAudit.every(x=>Number.isFinite(+x.ts)&&Number.isFinite(+x.bs)&&Number.isFinite(+x.dc)), 'trend/buy/completeness scores missing');
    check(new Set(scoreAudit.map(x=>x.bs)).size>5, 'buy-point scores are still collapsed');
    const sortContract=await page.evaluate(()=>window.__V7_DATA__.strategy_meta.sort_contract);
    check(Array.isArray(sortContract)&&sortContract[0]==='action_priority'&&sortContract.at(-1)==='code(asc)','canonical sort contract missing');
    const zeroZone = await page.evaluate(() => /第一买入区\s*0(?:\.0+)?\s*[-–—]\s*0(?:\.0+)?/.test(document.querySelector("#panel-strategy")?.textContent || ""));
    check(!zeroZone, "strategy page still renders a 0-0 buy zone");

    await page.click('[data-scope="hardware"]');
    await page.click('[data-tab="kline"]');
    await page.waitForSelector("#v7KlineSortKey");
    const klineSortOptions = await page.$$eval("#v7KlineSortKey option", nodes => nodes.map(n => n.value));
    check(['canonical','action','trend','buy','rs'].every(x => klineSortOptions.includes(x)), `K-line sort options incomplete: ${klineSortOptions.join(',')}`);
    await page.select("#v7KlineSortKey", "trend");
    await page.waitForSelector("#klineList .company-item");
    await page.click("#klineList .company-item");
    await page.waitForFunction(() => {
      const box=document.querySelector('#chartCanvas');
      return (document.querySelector('#chartName')?.textContent || '') !== '选择公司' && box && box.getBoundingClientRect().height > 150;
    }, { timeout: 20000 });
    const klineAudit = await page.evaluate(() => ({
      name: document.querySelector('#chartName')?.textContent || '',
      sort: document.querySelector('#v7KlineSortKey')?.value,
      height: document.querySelector('#chartCanvas')?.getBoundingClientRect().height || 0,
    }));
    check(klineAudit.sort === 'trend' && klineAudit.height > 150, 'K-line sorting/rendering interaction failed');

    await page.click('[data-tab="valuation"]');
    await page.waitForSelector("#panel-valuation table");
    const valuation = await page.evaluate(() => ({
      columns: document.querySelectorAll("#panel-valuation thead th").length,
      heading: document.querySelector("#panel-valuation thead")?.textContent || "",
      text: document.querySelector("#panel-valuation tbody")?.textContent || "",
      tableWidth: document.querySelector("#panel-valuation table")?.scrollWidth || 0,
      bodyWidth: document.body.scrollWidth,
      viewportWidth: document.documentElement.clientWidth,
      sixMonthScenarios: Object.values(window.__V7_VALUATION__ || {}).filter((row) => ["formal", "research"].includes(row.forward_scenario_status)).length,
      twelveMonthTargets: Object.values(window.__V7_VALUATION__ || {}).filter((row) => row.twelve_public !== false).length,
    }));
    check(valuation.columns === 9, `valuation table has ${valuation.columns} columns, expected 9`);
    check(valuation.heading.includes("当前研究区间 / 6个月情景"), "valuation table does not use the six-month scenario contract");
    check(!/(未来12个月|明年2月|年底)/.test(valuation.text), "valuation table still exposes old long-horizon targets");
    check(valuation.sixMonthScenarios > 0 && valuation.sixMonthScenarios < 142, "six-month scenarios are not gated company by company");
    check(valuation.twelveMonthTargets === 0, "twelve-month targets remain public");
    check(valuation.bodyWidth <= valuation.viewportWidth + 2, "valuation table leaks horizontal overflow to the body");
    await page.click("#valuationBody [data-detail]");
    await page.waitForSelector("#modal.open .v7-detail-model");
    const detailValuation = await page.$eval("#modalBody .v7-detail-model", (node) => node.textContent);
    check(detailValuation.includes("6个月"), "company detail does not show the six-month scenario decision");
    check(!detailValuation.includes("12个月目标价"), "company detail still presents a twelve-month target price");
    await page.click("#detailBack");
    report.initial = initial;
    report.valuation = valuation;
    report.pageErrors = pageErrors;
    check(pageErrors.length === 0, `page errors: ${pageErrors.join(" | ")}`);
    await page.screenshot({ path: path.join(resultsRoot, `${profile.name}.png`), fullPage: true });
    report.status = "PASS";
  } catch (error) {
    failed = true;
    report.status = "FAIL";
    report.error = error.stack || String(error);
    await page.screenshot({ path: path.join(resultsRoot, `${profile.name}-failure.png`), fullPage: true }).catch(() => {});
  } finally {
    reports.push(report);
    await page.close();
  }
}

{
  const page = await browser.newPage();
  const pageErrors=[];
  page.on("pageerror", error => pageErrors.push(error.message));
  await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
  await page.setRequestInterception(true);
  page.on("request", request => {
    const url=request.url();
    if (/^https?:/.test(url)) request.abort("blockedbyclient");
    else request.continue();
  });
  const report={profile:"local-file"};
  try {
    const localUrl=pathToFileURL(path.join(publicRoot,"index.html")).href;
    await page.goto(localUrl,{waitUntil:"load",timeout:60000});
    await page.waitForFunction(() => window.__V79_RUNTIME__?.release === "V7.9.4", {timeout:30000});
    const local=await page.evaluate(() => ({
      release: window.__V79_RUNTIME__?.release,
      strategyCount: Object.keys(window.__V7_DATA__?.strategy_current || {}).length,
      markets: document.querySelectorAll('[data-live-market]').length,
      bodyWidth: document.body.scrollWidth,
      viewportWidth: document.documentElement.clientWidth,
      authority: window.__V794_AUTHORITY__?.frontendRole,
    }));
    check(local.release==='V7.9.4','local file is not V7.9.4');
    check(local.strategyCount===142,'local file does not contain 142 strategy rows');
    check(local.markets===4,'local file does not render four market cards');
    check(local.authority==='display-and-sort-only','local file lost authority contract');
    check(local.bodyWidth<=local.viewportWidth+2,'local file has body overflow');
    check(pageErrors.length===0,`local file page errors: ${pageErrors.join(' | ')}`);
    report.local=local; report.pageErrors=pageErrors; report.status='PASS';
    await page.screenshot({path:path.join(resultsRoot,'local-file.png'),fullPage:true});
  } catch(error) {
    failed=true; report.status='FAIL'; report.error=error.stack||String(error);
    await page.screenshot({path:path.join(resultsRoot,'local-file-failure.png'),fullPage:true}).catch(()=>{});
  } finally { reports.push(report); await page.close(); }
}

await browser.close();
await new Promise((resolve) => server.close(resolve));
fs.writeFileSync(path.join(resultsRoot, "report.json"), JSON.stringify(reports, null, 2));
console.log(JSON.stringify(reports, null, 2));
if (failed) process.exit(1);
