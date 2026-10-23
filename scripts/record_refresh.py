#!/usr/bin/env python3
"""Record actual workflow timing separately from the scheduled cadence."""
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
VERSION = "V7.9.4"
US_CONTINUOUS_CRON = "5,15,25,35,45,55 13-21 * * 1-5"
PLAN = [
    {"cron": "50 22 * * 1-5", "purpose": "美股上一完整交易日"},
    {"cron": "35 1 * * 1-5", "purpose": "亚洲早盘即时行情"},
    {"cron": "40 3 * * 1-5", "purpose": "亚洲午间即时行情"},
    {"cron": "10 5 * * 1-5", "purpose": "亚洲午后即时行情"},
    {"cron": "20 7 * * 1-5", "purpose": "A股尾盘/港股盘中"},
    {"cron": "35 8 * * 1-5", "purpose": "亚洲收盘"},
    {"cron": "10 10 * * 1-5", "purpose": "财务/一致预期/估值"},
    {"cron": "10 14 * * 1-5", "purpose": "晚间公告补偿与审计"},
    {"cron": US_CONTINUOUS_CRON, "purpose": "美股常规时段每10分钟轻量采样"},
]


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


def iso(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(raw).astimezone(dt.timezone.utc).isoformat()
    except ValueError:
        return None


def main() -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(PATH.read_text("utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"version": VERSION, "runs": []}
    now = dt.datetime.now(dt.timezone.utc)
    started = iso(os.getenv("WORKFLOW_ACTUAL_STARTED_AT"))
    run = {
        "mode": os.getenv("REFRESH_MODE", "unknown"),
        "status": os.getenv("JOB_STATUS", "unknown"),
        "event": os.getenv("WORKFLOW_EVENT", "unknown"),
        "scheduled_cron": os.getenv("WORKFLOW_SCHEDULE") or None,
        "planned_schedule_is_not_actual_time": True,
        "actual_started_at_utc": started,
        "actual_started_at_beijing": dt.datetime.fromisoformat(started).astimezone(ZoneInfo("Asia/Shanghai")).isoformat() if started else None,
        "finished_at_utc": now.isoformat(),
        "finished_at_beijing": now.astimezone(ZoneInfo("Asia/Shanghai")).isoformat(),
        "run_id": os.getenv("WORKFLOW_RUN_ID") or None,
        "run_attempt": os.getenv("WORKFLOW_RUN_ATTEMPT") or None,
    }
    data["version"] = VERSION
    data["schedule_plan"] = PLAN
    data["runs"] = ([run] + list(data.get("runs") or []))[:240]
    data["last_success"] = next((row for row in data["runs"] if row.get("status") == "success"), None)
    atomic_write(PATH, json.dumps(data, ensure_ascii=False, indent=2))
    if LATEST.exists():
        latest = json.loads(LATEST.read_text("utf-8"))
        latest["refresh_summary"] = {
            "version": VERSION,
            "last_success": data["last_success"],
            "recent_runs": data["runs"][:20],
            "schedule_plan": PLAN,
            "us_live_cadence": "美股常规时段计划每10分钟一次；GitHub Actions可能延迟，实际完成时间单独记录",
            "schedule_time_is_not_completion_time": True,
        }
        raw = json.dumps(latest, ensure_ascii=False, separators=(",", ":"))
        atomic_write(LATEST, raw)
    print(json.dumps(run, ensure_ascii=False))


if __name__ == "__main__":
    main()
