#!/usr/bin/env python3
"""Build the GitHub Pages mirror from the same V7.9 snapshot and frontend sources."""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
PUBLIC = ROOT / "docs" / "public_v7"
SNAPSHOT = PUBLIC / "data" / "latest-v7.json"
OUTPUT = PUBLIC / "index.html"


def main() -> None:
    data = json.loads(SNAPSHOT.read_text("utf-8"))
    valuation = data.get("valuation_current") or {}
    strategy = data.get("strategy_current") or {}
    companies = [
        *(data.get("companies", {}).get("hardware") or []),
        *(data.get("companies", {}).get("application") or []),
    ]
    codes = {row.get("code") for row in companies}
    if (len(companies), sum(row.get("scope") == "hardware" for row in companies), sum(row.get("scope") == "application" for row in companies)) != (142, 83, 59):
        raise SystemExit("公司池不是142/83/59")
    if set(valuation) != codes or set(strategy) != codes:
        raise SystemExit("估值或策略未覆盖唯一公司池")
    if any(not isinstance(v.get("current_low"), (int, float)) or not isinstance(v.get("current_high"), (int, float)) for v in valuation.values()):
        raise SystemExit("存在非数值合理估值范围")

    template = (FRONTEND / "V7_9_页面模板.html").read_text("utf-8")
    app = (FRONTEND / "V7_9_统一前端.js").read_text("utf-8")
    style = (FRONTEND / "V7_9_统一样式.css").read_text("utf-8")
    compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    values = {
        "__V79_CSS__": style,
        "__V79_SNAPSHOT_JSON__": compact,
        "__V79_APP_JS__": app,
    }
    for token in values:
        if template.count(token) != 1:
            raise SystemExit(f"模板占位符异常: {token}")
    html = template
    for token, value in values.items():
        html = html.replace(token, value)
    temp = OUTPUT.with_suffix(".html.tmp")
    temp.write_text(html, "utf-8")
    temp.replace(OUTPUT)
    print(json.dumps({"status": "PASS", "release": "V7.9.3", "html_sha256": hashlib.sha256(html.encode()).hexdigest(), "html_bytes": len(html.encode())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
