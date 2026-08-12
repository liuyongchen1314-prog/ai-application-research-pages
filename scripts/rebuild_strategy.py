#!/usr/bin/env python3
from __future__ import annotations

import collections
import datetime as dt
import json
import pathlib

from snapshot_io import load_snapshot, save_snapshot
from strategy_core import ACTIONS, build


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "public_v7" / "data" / "strategy-v79.json"
HISTORY = ROOT / "config" / "strategy_history"


def main() -> None:
    data = load_snapshot()
    strategy = build(data)
    companies = strategy["companies"]
    if len(companies) != 142 or set(companies) != set(data.get("valuation_current") or {}):
        raise SystemExit("strategy and valuation company pools differ")
    counts = dict(collections.Counter(row["action"] for row in companies.values()))
    strategy["generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    strategy["action_counts"] = counts
    data["strategy_current"] = companies
    data["strategy_meta"] = {
        "schema": strategy["schema"],
        "version": "V7.9.3",
        "generated_at": strategy["generated_at"],
        "snapshot_date": strategy["snapshot_date"],
        "action_counts": counts,
        "valuation_source": "valuation_current",
        "separated_from_valuation": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(strategy, ensure_ascii=False, indent=2), "utf-8")
    HISTORY.mkdir(parents=True, exist_ok=True)
    (HISTORY / f"{strategy['snapshot_date']}.json").write_text(
        json.dumps(strategy, ensure_ascii=False, separators=(",", ":")), "utf-8"
    )
    save_snapshot(data)
    print(json.dumps({"status": "PASS", "companies": 142, "actions": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
