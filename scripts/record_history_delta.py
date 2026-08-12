#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
LATEST = ROOT / "docs" / "public_v7" / "data" / "latest-v7.json"
HISTORY = ROOT / "docs" / "public_v7" / "data" / "history"
MANIFEST = HISTORY / "manifest.json"
MAP_SECTIONS = {"quotes", "valuation_current", "company_financials", "fund_flows"}


def read_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def stable(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value) -> str:
    return hashlib.sha256(stable(value).encode("utf-8")).hexdigest()


def write_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), "utf-8")
    temp.replace(path)


def histories_index(histories: dict) -> dict:
    result = {}
    for code, record in histories.items():
        daily = record.get("daily") or [] if isinstance(record, dict) else []
        result[code] = {
            "count": len(daily),
            "last_date": daily[-1][0] if daily else None,
            "sha256": digest(record),
        }
    return result


def component_hashes(data: dict) -> dict:
    result = {"globals": {}, "maps": {}, "companies": {}, "histories": histories_index(data.get("histories") or {})}
    for key, value in data.items():
        if key == "histories":
            continue
        if key in MAP_SECTIONS and isinstance(value, dict):
            result["maps"][key] = {code: digest(row) for code, row in value.items()}
        elif key == "companies" and isinstance(value, dict):
            result["companies"] = {
                scope: {row["code"]: digest(row) for row in rows}
                for scope, rows in value.items() if isinstance(rows, list)
            }
        else:
            result["globals"][key] = digest(value)
    return result


def initialize(source: pathlib.Path) -> None:
    data = read_json(source)
    date = str(data.get("snapshot_date") or data.get("embedded_snapshot") or dt.date.today())
    core = {key: value for key, value in data.items() if key not in {"histories", "fund_flows", "companies"}}
    core["companies_index"] = {
        scope: [
            {"code": row.get("code"), "name": row.get("name"), "sector": row.get("sector")}
            for row in rows
        ]
        for scope, rows in (data.get("companies") or {}).items() if isinstance(rows, list)
    }
    core["fund_flows_index"] = {
        code: {"sha256": digest(row), "records": len(row) if isinstance(row, list) else None}
        for code, row in (data.get("fund_flows") or {}).items()
    }
    core["histories_index"] = histories_index(data.get("histories") or {})
    baseline_name = f"baseline-{date}.core.json"
    baseline_path = HISTORY / baseline_name
    write_json(baseline_path, core)
    manifest = {
        "schema": "v75-incremental-history-1",
        "baseline": baseline_name,
        "baseline_sha256": hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
        "baseline_date": date,
        "deltas": [],
        "component_hashes": component_hashes(data),
        "latest_snapshot_sha256": hashlib.sha256(LATEST.read_bytes()).hexdigest() if LATEST.exists() else None,
        "policy": "基线不复制两年K线；后续仅记录变化字段和K线追加行。历史回滚以压缩包版本为主，本目录用于跨日审计。",
    }
    write_json(MANIFEST, manifest)
    print(json.dumps({"status": "PASS", "mode": "initialize", "baseline": baseline_name, "core_bytes": baseline_path.stat().st_size}, ensure_ascii=False))


def record() -> None:
    if not MANIFEST.exists():
        initialize(LATEST)
        return
    data = read_json(LATEST)
    manifest = read_json(MANIFEST)
    previous = manifest.get("component_hashes") or {}
    current = component_hashes(data)
    delta = {"schema": "v75-history-delta-1", "snapshot_date": data.get("snapshot_date"), "globals": {}, "maps": {}, "companies": {}, "histories": {}}

    for key, value in data.items():
        if key in MAP_SECTIONS or key in {"companies", "histories"}:
            continue
        if current["globals"].get(key) != (previous.get("globals") or {}).get(key):
            delta["globals"][key] = value

    for section in MAP_SECTIONS:
        rows = data.get(section) or {}
        old_hashes = (previous.get("maps") or {}).get(section) or {}
        changed = {code: row for code, row in rows.items() if current["maps"].get(section, {}).get(code) != old_hashes.get(code)}
        deleted = sorted(set(old_hashes) - set(rows))
        if changed or deleted:
            delta["maps"][section] = {"changed": changed, "deleted": deleted}

    for scope, rows in (data.get("companies") or {}).items():
        if not isinstance(rows, list):
            continue
        old_hashes = (previous.get("companies") or {}).get(scope) or {}
        changed = {row["code"]: row for row in rows if current["companies"].get(scope, {}).get(row["code"]) != old_hashes.get(row["code"])}
        deleted = sorted(set(old_hashes) - {row["code"] for row in rows})
        if changed or deleted:
            delta["companies"][scope] = {"changed": changed, "deleted": deleted, "order": [row["code"] for row in rows]}

    old_histories = previous.get("histories") or {}
    for code, record_value in (data.get("histories") or {}).items():
        now = current["histories"][code]
        old = old_histories.get(code)
        if old and now["sha256"] == old.get("sha256"):
            continue
        daily = record_value.get("daily") or [] if isinstance(record_value, dict) else []
        old_count = int((old or {}).get("count") or 0)
        if old and len(daily) >= old_count and old_count > 0:
            delta["histories"][code] = {"mode": "append", "rows": daily[old_count:], "meta": {key: value for key, value in record_value.items() if key != "daily"}}
        else:
            delta["histories"][code] = {"mode": "replace", "record": record_value}

    changed_count = sum(bool(delta[key]) for key in ("globals", "maps", "companies", "histories"))
    if changed_count:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d-%H%M%S")
        name = f"{stamp}.delta.json"
        write_json(HISTORY / name, delta)
        manifest.setdefault("deltas", []).append(name)
    manifest["component_hashes"] = current
    manifest["latest_snapshot_sha256"] = hashlib.sha256(LATEST.read_bytes()).hexdigest()
    write_json(MANIFEST, manifest)
    print(json.dumps({"status": "PASS", "mode": "delta", "changed_sections": changed_count, "deltas": len(manifest.get("deltas") or [])}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initialize-from", type=pathlib.Path)
    args = parser.parse_args()
    if args.initialize_from:
        initialize(args.initialize_from)
    else:
        record()


if __name__ == "__main__":
    main()
