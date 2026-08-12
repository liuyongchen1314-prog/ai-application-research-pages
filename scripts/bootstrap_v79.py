#!/usr/bin/env python3
"""Create the V7.9 working snapshot from immutable V7.6 and 2026-08-11 production baselines.

This is a one-time migration, not a valuation approval step.  It imports newer
market data and numeric research ranges while explicitly downgrading every old
audit label pending the new company-by-company evidence review.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import pathlib
import shutil
from typing import Any


ENGINE = pathlib.Path(__file__).resolve().parents[1]
BACKEND = ENGINE.parents[0]
REBUILD = BACKEND / "10_V7.9全量重建"
PUBLIC_BASE = REBUILD / "外部生产基线_2026-08-11" / "公开仓库"
V76_CONFIG = REBUILD / "V7_6_估值配置基线_只读.json"
V76_SNAPSHOT = REBUILD / "V7_6_生产快照基线_只读.json"
CONFIG = ENGINE / "config" / "valuation_model.json"
LATEST = ENGINE / "docs" / "public_v7" / "data" / "latest-v7.json"
INTRADAY = LATEST.parent / "intraday"


def read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text("utf-8"))


def write_json(path: pathlib.Path, value: Any, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
        ),
        "utf-8",
    )


def fmt(value: float) -> str:
    if abs(value) >= 100:
        return str(int(round(value)))
    if abs(value) >= 10:
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{value:.2f}".rstrip("0").rstrip(".")


def range_text(low: float, high: float) -> str:
    return f"{fmt(low)}–{fmt(high)}"


def evidence_profile(old_label: str) -> dict[str, Any]:
    if old_label == "已审计估值区间":
        return {
            "audit_stage": "P1候选复算待二次对账",
            "evidence_state": "部分闭环",
            "confidence": "C+",
            "confidence_display": "中低",
            "formal_closed": False,
        }
    if old_label == "条件估值区间":
        return {
            "audit_stage": "P0部分闭环",
            "evidence_state": "条件成立",
            "confidence": "C",
            "confidence_display": "较低",
            "formal_closed": False,
        }
    return {
        "audit_stage": "P0缺口待补",
        "evidence_state": "证据较弱",
        "confidence": "D",
        "confidence_display": "低",
        "formal_closed": False,
    }


def migrate_record(old: dict[str, Any], public: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(old)
    low = float(public["合理下限"])
    high = float(public["合理上限"])
    profile = evidence_profile(str(public.get("估值状态") or ""))
    out.update(profile)
    out.update(
        {
            "version": "V7.9",
            "price_as_of": public.get("最新价"),
            "price_date": public.get("数据日期"),
            "current_low": low,
            "current_high": high,
            "current": range_text(low, high),
            "blocked": False,
            "audit_status": profile["audit_stage"],
            "model_audit_status": profile["audit_stage"],
            "valuation_basis": "新一轮研究区间；正式闭环待逐家交叉验证",
            "range_origin": "2026-08-11过渡生产区间，仅作V7.9重建起点",
            "legacy_v76_range_rejected": True,
            "legacy_public_label": public.get("估值状态"),
            "evidence_sources": [
                {
                    "source": "V7.6历史估值配置",
                    "role": "只作模型结构与差异对照，不作价格锚",
                    "as_of": "2026-08-07",
                },
                {
                    "source": "公开生产过渡数据",
                    "role": "数值研究区间起点，不等于正式审计结论",
                    "as_of": public.get("数据日期"),
                },
                {
                    "source": "公司公告/东方财富/同花顺/券商研报",
                    "role": "V7.9逐家补证目标",
                    "as_of": None,
                },
            ],
            "report_date": (out.get("data_inputs") or {}).get("report_date"),
            "forecast_date": (out.get("institution_check") or {}).get("forecast_date"),
            "capture_date": "2026-08-12",
            "price_feedback_policy": "行情只改变估值位置与行动，不改变合理价值",
        }
    )
    # Six/twelve-month scenario fields may remain useful for display, but are
    # explicitly non-formal until their forecast anchors are revalidated.
    out["forward_ranges_formal"] = False
    return out


def main() -> None:
    config = read_json(V76_CONFIG)
    snapshot = read_json(V76_SNAPSHOT)
    public = read_json(PUBLIC_BASE / "data" / "最新研究数据.json")
    histories = read_json(PUBLIC_BASE / "data" / "日线.json")
    public_rows = {row["代码"]: row for row in public["公司"]}
    if len(public_rows) != 142 or len(config.get("records") or []) != 142:
        raise SystemExit("V7.9 migration requires 142 unique public rows and 142 V7.6 records")
    if set(public_rows) != {row["code"] for row in config["records"]}:
        raise SystemExit("public and V7.6 company pools differ")

    records = [migrate_record(row, public_rows[row["code"]]) for row in config["records"]]
    valuation = {row["code"]: copy.deepcopy(row) for row in records}
    quotes = {
        code: {
            "name": row["公司"],
            "price": row["最新价"],
            "change_pct": row.get("涨跌幅"),
            "date": row["数据日期"],
            "timestamp": row["数据日期"],
            "source": "公开生产基线/腾讯公开行情",
        }
        for code, row in public_rows.items()
    }
    rebuilt_histories = {
        code: {
            "daily": bars,
            "provider": "公开生产基线/腾讯前复权日线",
            "symbol": ((snapshot.get("histories") or {}).get(code) or {}).get("symbol"),
            "last_date": bars[-1][0] if bars else None,
            "count": len(bars),
        }
        for code, bars in histories.items()
    }
    if len(rebuilt_histories) != 142 or len(quotes) != 142:
        raise SystemExit("2026-08-11 market baseline is not 142/142")

    INTRADAY.mkdir(parents=True, exist_ok=True)
    for path in INTRADAY.glob("*.json"):
        path.unlink()
    copied = 0
    for source in (PUBLIC_BASE / "data" / "分时").glob("*.json"):
        item = read_json(source)
        rows = item.get("分时") or []
        payload = {
            "code": item.get("代码"),
            "symbol": None,
            "generated_at": public.get("生成时间"),
            "minute": rows,
            "five_day": rows,
            "source": "公开生产基线/腾讯五日分时兼容结果",
            "synthetic": False,
        }
        write_json(INTRADAY / source.name, payload)
        copied += 1
    if copied != 142:
        raise SystemExit(f"intraday baseline is {copied}/142")

    snapshot.update(
        {
            "version": "V7.9",
            "frontend_release": "V7.9",
            "schema": "v79-unified-research-1",
            "snapshot_date": public["数据日期"],
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "generated_at_cn": public.get("生成时间"),
            "quotes": quotes,
            "histories": rebuilt_histories,
            "valuation_current": valuation,
            "intraday": {
                "schema": "v79-intraday-manifest-1",
                "base": "data/intraday/",
                "success": 142,
                "total": 142,
                "available_codes": sorted(public_rows),
                "status": "complete",
            },
            "coverage": {
                **(snapshot.get("coverage") or {}),
                "histories": 142,
                "quotes": 142,
                "intraday": 142,
                "total": 142,
                "hardware": 83,
                "application": 59,
            },
            "valuation_meta": {
                "version": "V7.9",
                "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "companies": 142,
                "single_source": True,
                "formal_closed": 0,
                "partial_evidence": sum(r["evidence_state"] == "部分闭环" for r in records),
                "conditional_evidence": sum(r["evidence_state"] == "条件成立" for r in records),
                "weak_evidence": sum(r["evidence_state"] == "证据较弱" for r in records),
                "note": "142家均保留数值研究区间；旧65/1/76标签已降级，不能视为正式结论。",
            },
        }
    )
    config.update(
        {
            "version": "V7.9",
            "valuation_date": public["数据日期"],
            "schema": "v79-valuation-config-1",
            "records": records,
            "rules": {
                "version": "V7.9",
                "total": 142,
                "hardware": 83,
                "application": 59,
                "formal_closed": 0,
                "numeric_research_ranges": 142,
                "price_feedback": "review_only",
                "institution_target_role": "cross_check_only",
                "legacy_v76_price_anchor": "forbidden",
                "valuation_and_trading_separated": True,
            },
        }
    )
    write_json(CONFIG, config, pretty=True)
    write_json(LATEST, snapshot)
    summary = {
        "schema": "v79-bootstrap-summary-1",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "version": "V7.9",
        "companies": 142,
        "hardware": 83,
        "application": 59,
        "numeric_ranges": 142,
        "formal_closed": 0,
        "evidence_distribution": {
            "部分闭环": sum(r["evidence_state"] == "部分闭环" for r in records),
            "条件成立": sum(r["evidence_state"] == "条件成立" for r in records),
            "证据较弱": sum(r["evidence_state"] == "证据较弱" for r in records),
        },
        "market_snapshot": public["数据日期"],
        "histories": 142,
        "intraday": 142,
        "warning": "本迁移只建立诚实的新底座，不把旧标签升级为正式估值闭环。",
    }
    write_json(REBUILD / "V7_9_第1步_新底座迁移结果.json", summary, pretty=True)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
