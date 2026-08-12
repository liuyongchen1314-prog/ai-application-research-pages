#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib

from valuation_core import CONFIG, LATEST, RELEASE, ROOT, load_inputs, rebuild
from snapshot_io import save_snapshot


def write_json(path: pathlib.Path, value: object, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2 if pretty else None, separators=None if pretty else (",", ":")), "utf-8")


def scrub_legacy_valuation(value: object) -> None:
    """Remove every executable legacy valuation branch, including company-level copies."""
    if isinstance(value, dict):
        for legacy in ("valuation_v71", "valuation_v72", "valuation_v73"):
            value.pop(legacy, None)
        for child in value.values():
            scrub_legacy_valuation(child)
    elif isinstance(value, list):
        for child in value:
            scrub_legacy_valuation(child)


def main() -> None:
    data, config = load_inputs()
    previous = data.get("valuation_current") or {}
    valuation = rebuild(data, config)
    if len(valuation) != 142:
        raise SystemExit(f"valuation coverage failed: {len(valuation)}/142")
    scrub_legacy_valuation(data)
    data["version"] = RELEASE
    data["frontend_release"] = RELEASE
    data["valuation_current"] = valuation
    data["valuation_meta"] = {
        "version": RELEASE,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "companies": len(valuation),
        "single_source": True,
        "public_targets": ["current_research_range", "six_month_value_scenario"],
        "internal_audit_targets": ["2026-12-31", "2027-02-28", "12_month"],
        "public_six_month_scenarios": sum(
            row.get("forward_scenario_status") in ("formal", "research") for row in valuation.values()
        ),
        "public_twelve_month_targets": 0,
        "queued_companies": data.get("revaluation_queue") or [],
        "numeric_research_ranges": sum(
            bool(row.get("current_low") and row.get("current_high")) for row in valuation.values()
        ),
        "formal_closed": sum(bool(row.get("formal_closed")) for row in valuation.values()),
        "evidence_distribution": {
            state: sum(row.get("evidence_state") == state for row in valuation.values())
            for state in ("正式闭环", "部分闭环", "条件成立", "证据较弱")
        },
        "separation_rule": "估值对象不保存交易行动；操作策略由独立策略对象生成",
    }
    data["revaluation_queue"] = []
    save_snapshot(data)
    config["version"] = RELEASE
    config["valuation_date"] = data.get("snapshot_date") or data.get("embedded_snapshot")
    if isinstance(config.get("rules"), dict):
        config["rules"]["version"] = RELEASE
    config["records"] = list(valuation.values())
    write_json(CONFIG, config, pretty=True)
    changed = {code: record for code, record in valuation.items() if previous.get(code) != record}
    deleted = sorted(set(previous) - set(valuation))
    history_name = None
    if changed or deleted:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
        history = ROOT / "config" / "valuation_history" / f"{stamp}.delta.json"
        history_name = history.name
        write_json(
            history,
            {
                "schema": "v79-valuation-delta-1",
                "meta": data["valuation_meta"],
                "previous_sha256": hashlib.sha256(json.dumps(previous, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                "current_sha256": hashlib.sha256(json.dumps(valuation, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                "changed": changed,
                "deleted": deleted,
            },
            pretty=True,
        )
    print(json.dumps({"status": "PASS", "release": RELEASE, "valuation_model": RELEASE, "companies": len(valuation), "changed": len(changed), "history": history_name}, ensure_ascii=False))


if __name__ == "__main__":
    main()
