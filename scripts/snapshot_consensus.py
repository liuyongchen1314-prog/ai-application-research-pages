#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import pathlib
from snapshot_io import save_snapshot

ROOT = pathlib.Path(__file__).resolve().parents[1]
LATEST = ROOT / "docs" / "public_v7" / "data" / "latest-v7.json"


def main() -> None:
    data = json.loads(LATEST.read_text("utf-8"))
    financials = data.get("company_financials") or {}
    snapshot = {
        code: row.get("consensus")
        for code, row in financials.items()
        if isinstance(row, dict) and isinstance(row.get("consensus"), dict)
    }
    day = str(data.get("snapshot_date") or dt.date.today())
    target = ROOT / "config" / "consensus_snapshots" / f"{day}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"date": day, "coverage": len(snapshot), "consensus": snapshot}, ensure_ascii=False, indent=2), "utf-8")
    data["consensus_history"] = {"latest_date": day, "latest_file": target.name, "coverage": len(snapshot)}
    save_snapshot(data)
    print(json.dumps({"status": "PASS", "date": day, "coverage": len(snapshot)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
