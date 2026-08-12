#!/usr/bin/env python3
from __future__ import annotations

import json
from valuation_core import LATEST, RELEASE, load_inputs, rebuild


def main() -> None:
    data = json.loads(LATEST.read_text("utf-8"))
    values = data.get("valuation_current") or {}
    errors: list[str] = []
    if len(values) != 142:
        errors.append(f"coverage={len(values)}/142")
    for legacy in ("valuation_v71", "valuation_v72", "valuation_v73"):
        if legacy in data:
            errors.append(f"legacy key loaded: {legacy}")
    companies = [
        *((data.get("companies") or {}).get("hardware") or []),
        *((data.get("companies") or {}).get("application") or []),
    ]
    if len(companies) != 142:
        errors.append(f"company_pool={len(companies)}/142")
    if sum(row.get("scope") == "hardware" for row in companies) != 83:
        errors.append("hardware pool is not 83")
    if sum(row.get("scope") == "application" for row in companies) != 59:
        errors.append("application pool is not 59")
    required = (
        "current", "year_end", "next_year_start", "twelve", "status",
        "valuation_gate", "version", "current_low", "current_high",
        "primary_model", "cross_check_model", "evidence_state",
        "calculation_route", "confidence_display", "forward_public_horizon_months",
        "forward_scenario_status", "forward_scenario_date", "forward_scenario_note",
    )
    for code, row in values.items():
        missing = [key for key in required if not row.get(key)]
        if missing:
            errors.append(f"{code}: missing {','.join(missing)}")
        if row.get("version") != RELEASE:
            errors.append(f"{code}: wrong version")
        if not row.get("primary_model") or not row.get("cross_check_model"):
            errors.append(f"{code}: missing primary/cross model")
        if row.get("valuation_basis") not in ("正式模型复算", "低置信度数值研究区间"):
            errors.append(f"{code}: missing valuation basis")
        if row.get("twelve_public") is not False:
            errors.append(f"{code}: twelve-month target is still public")
        forward_status = row.get("forward_scenario_status")
        if forward_status not in ("formal", "research", "unavailable"):
            errors.append(f"{code}: invalid forward scenario status")
        if row.get("forward_public_horizon_months") != 6:
            errors.append(f"{code}: public forward horizon is not six months")
        if forward_status == "unavailable" and row.get("forward_scenario") is not None:
            errors.append(f"{code}: unavailable forward scenario still exposes a number")
        if forward_status in ("formal", "research") and not row.get("forward_scenario"):
            errors.append(f"{code}: displayable forward scenario has no range")
        if forward_status in ("formal", "research") and not isinstance(row.get("forward_scenario_calculation"), dict):
            errors.append(f"{code}: displayable forward scenario has no calculation audit")
        if forward_status == "research" and (
            row.get("revision_gate") != "通过" or row.get("realization_gate") != "通过"
        ):
            errors.append(f"{code}: research scenario bypasses forecast or realization gate")
        if forward_status == "research":
            calc = row.get("forward_scenario_calculation") or {}
            if calc.get("route") != "current_research_range_roll_forward_by_ntm_eps_and_pe":
                errors.append(f"{code}: research scenario reused a stale absolute range")
            expected_low = row.get("current_low", 0) * (1 + (calc.get("value_low_change_pct") or 0))
            expected_high = row.get("current_high", 0) * (1 + (calc.get("value_high_change_pct") or 0))
            if abs(expected_low - row.get("six_low", 0)) > 1e-6 or abs(expected_high - row.get("six_high", 0)) > 1e-6:
                errors.append(f"{code}: research scenario does not reconcile to its current range")
        if not isinstance(row.get("current_low"), (int, float)) or not isinstance(row.get("current_high"), (int, float)):
            errors.append(f"{code}: non-numeric current range")
        elif row.get("current_low", 0) <= 0 or row.get("current_low", 0) >= row.get("current_high", 0):
            errors.append(f"{code}: inverted current range")
        if any(key in row for key in ("action_level", "action_reason", "action_trigger", "action_model")):
            errors.append(f"{code}: trading action leaked into valuation object")
        if row.get("formal_closed"):
            if row.get("evidence_state") != "正式闭环":
                errors.append(f"{code}: formal flag without formal evidence")
            if row.get("model_kind") == "enterprise_value":
                bridge = row.get("ev_bridge") or {}
                ev_required = ("metric_value", "multiple", "cash", "debt", "minority_interest", "diluted_shares", "currency")
                if any(bridge.get(key) in (None, "") for key in ev_required):
                    errors.append(f"{code}: incomplete EV-to-equity bridge")
        dates = [row.get("report_date"), row.get("forecast_date"), row.get("capture_date")]
        if dates[0] and dates[1] and dates[0] == dates[1]:
            errors.append(f"{code}: report date reused as forecast date")
    if errors:
        raise SystemExit("\n".join(errors[:50]))
    input_data, input_config = load_inputs()
    repeated = rebuild(input_data, input_config)
    if repeated != values:
        drifted = [code for code in values if repeated.get(code) != values.get(code)]
        raise SystemExit(f"valuation rebuild is not idempotent: {len(drifted)} records drift")
    print(json.dumps({
        "status": "PASS",
        "release": RELEASE,
        "companies": len(values),
        "hardware": 83,
        "application": 59,
        "numeric_ranges": sum(bool(r.get("current_low") and r.get("current_high")) for r in values.values()),
        "formal_closed": sum(bool(r.get("formal_closed")) for r in values.values()),
        "public_six_month_scenarios": sum(r.get("forward_scenario_status") in ("formal", "research") for r in values.values()),
        "public_twelve_month_targets": sum(r.get("twelve_public") is not False for r in values.values()),
        "legacy_keys": 0,
        "public_horizon_months": 6,
        "valuation_trading_separated": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
