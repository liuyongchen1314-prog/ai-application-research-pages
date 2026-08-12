#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "docs" / "public_v7"
LATEST = PUBLIC / "data" / "latest-v7.json"
INDEX = PUBLIC / "index.json"


def main() -> None:
    raw = LATEST.read_bytes()
    data = json.loads(raw)
    index = {
        "schema": "v7-public-index-3",
        "data_schema": "v7-public-market-1",
        "release": "V7.9.1",
        "latest": "data/latest-v7.json",
        "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
        "snapshot_date": data.get("snapshot_date"),
        "generated_at_cn": data.get("generated_at_cn"),
        "coverage": data.get("coverage"),
        "intraday": data.get("intraday"),
        "market_freshness": data.get("market_freshness"),
        "privacy": "仅公开市场与基础信息",
    }
    temp = INDEX.with_suffix(".json.tmp")
    temp.write_text(json.dumps(index, ensure_ascii=False, indent=2), "utf-8")
    temp.replace(INDEX)
    print(json.dumps({"status": "PASS", "release": "V7.9.1", "snapshot_sha256": index["snapshot_sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
