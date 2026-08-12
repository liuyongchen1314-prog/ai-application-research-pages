#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import tempfile
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "docs" / "public_v7" / "data" / "refresh-log.json"
LATEST = ROOT / "docs" / "public_v7" / "data" / "latest-v7.json"


def atomic_write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        try:
            os.unlink(temp)
        except FileNotFoundError:
            pass


def main() -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(PATH.read_text("utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"version": "V7.9.3", "runs": []}
    now = dt.datetime.now(dt.timezone.utc)
    run = {
        "mode": os.getenv("REFRESH_MODE", "unknown"),
        "status": os.getenv("JOB_STATUS", "unknown"),
        "finished_at_utc": now.isoformat(),
        "finished_at_beijing": now.astimezone(ZoneInfo("Asia/Shanghai")).isoformat(),
    }
    data["version"] = "V7.9.3"
    data["runs"] = ([run] + list(data.get("runs") or []))[:120]
    data["last_success"] = next((row for row in data["runs"] if row.get("status") == "success"), None)
    atomic_write(PATH, json.dumps(data, ensure_ascii=False, indent=2))
    if LATEST.exists():
        latest = json.loads(LATEST.read_text("utf-8"))
        latest["refresh_summary"] = {
            "version": "V7.9.3",
            "last_success": data["last_success"],
            "recent_runs": data["runs"][:12],
            "expected_daily_runs": 8,
        }
        raw = json.dumps(latest, ensure_ascii=False, separators=(",", ":"))
        atomic_write(LATEST, raw)
    print(json.dumps(run, ensure_ascii=False))


if __name__ == "__main__":
    main()
