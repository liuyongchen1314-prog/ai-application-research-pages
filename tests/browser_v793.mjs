import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
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
    await page.waitForFunction(() => window.__V79_RUNTIME__?.release === "V7.9.3", { timeout: 30000 });
    const initial = await page.evaluate(() => ({
      title: document.title,
      bodyWidth: document.body.scrollWidth,
      viewportWidth: document.documentElement.clientWidth,
      markets: [...document.querySelectorAll("[data-live-market]")].map((node) => node.textContent),
      refreshText: document.querySelector("#v74RefreshNow")?.textContent,
      release: window.__V79_RUNTIME__.release,
      schedulerActive: window.__V79_RUNTIME__.state().schedulerActive,
    }));
    check(initial.title.includes("V7.9.3"), "title is not V7.9.3");
    check(initial.markets.length === 4 && initial.markets.every((text) => text.includes("%")), "four-market rise/fall cards are incomplete");
    check(initial.refreshText === "手动刷新全部数据", "manual refresh button has the wrong contract");
    check(initial.schedulerActive, "ten-minute browser scheduler is inactive");
    check(initial.bodyWidth <= initial.viewportWidth + 2, `body overflow ${initial.bodyWidth}/${initial.viewportWidth}`);

    await page.click("#v74RefreshNow");
    await page.waitForFunction(() => {
      const button = document.querySelector("#v74RefreshNow");
      const message = document.querySelector("#v74RefreshMessage")?.textContent || "";
      return !button?.disabled && /(取得新数据|检查完成，当前已是最新|在线数据暂不可用，继续显示最近一次有效快照|上次自动检查失败)/.test(message);
    }, { timeout: 45000 });
    report.manualRefresh = await page.$eval("#v74RefreshMessage", (node) => node.textContent);
    const marketsAfterRefresh = await page.$$eval("[data-live-market]", (nodes) => nodes.map((node) => node.textContent));
    check(marketsAfterRefresh.length === 4 && marketsAfterRefresh.every((text) => text.includes("%")), "manual refresh fallback damaged four-market cards");

    await page.click('[data-scope="full"]');
    await page.click('[data-tab="strategy"]');
    await page.waitForSelector(".strategy-company");
    const actions = await page.$$eval("[data-strategy-action]", (nodes) => [...new Set(nodes.map((node) => node.dataset.strategyAction).filter((value) => value && value !== "all"))]);
    check(actions.length >= 6, "strategy action filters are incomplete");
    for (const action of actions) {
      await page.evaluate((value) => document.querySelector(`[data-strategy-action="${CSS.escape(value)}"]`)?.click(), action);
      await new Promise((resolve) => setTimeout(resolve, 30));
      const count = await page.$$eval(".strategy-company", (nodes) => nodes.length);
      const expected = await page.evaluate((value) => window.__V7_DATA__.strategy_meta.action_counts[value] || 0, action);
      check(count === expected, `${action} filter shows ${count}, expected ${expected}`);
    }
    const zeroZone = await page.evaluate(() => /第一买入区\s*0(?:\.0+)?\s*[-–—]\s*0(?:\.0+)?/.test(document.querySelector("#panel-strategy")?.textContent || ""));
    check(!zeroZone, "strategy page still renders a 0-0 buy zone");

    await page.click('[data-scope="hardware"]');
    await page.click('[data-tab="valuation"]');
    await page.waitForSelector("#panel-valuation table");
    const valuation = await page.evaluate(() => ({
      columns: document.querySelectorAll("#panel-valuation thead th").length,
      tableWidth: document.querySelector("#panel-valuation table")?.scrollWidth || 0,
      bodyWidth: document.body.scrollWidth,
      viewportWidth: document.documentElement.clientWidth,
    }));
    check(valuation.columns === 9, `valuation table has ${valuation.columns} columns, expected 9`);
    check(valuation.bodyWidth <= valuation.viewportWidth + 2, "valuation table leaks horizontal overflow to the body");
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

await browser.close();
await new Promise((resolve) => server.close(resolve));
fs.writeFileSync(path.join(resultsRoot, "report.json"), JSON.stringify(reports, null, 2));
console.log(JSON.stringify(reports, null, 2));
if (failed) process.exit(1);
