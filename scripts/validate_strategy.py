#!/usr/bin/env python3
from __future__ import annotations

import collections
import json

from snapshot_io import load_snapshot
from strategy_core import ACTIONS


def main() -> None:
    data = load_snapshot()
    valuations = data.get("valuation_current") or {}
    strategies = data.get("strategy_current") or {}
    errors = []
    if len(strategies) != 142 or set(strategies) != set(valuations):
        errors.append("strategy coverage/source mismatch")
    counts = collections.Counter()
    required = (
        "action", "home_label", "reason", "valuation_position", "sector_strength",
        "initial_position", "add_condition", "reduce_condition", "invalidation",
    )
    for code, row in strategies.items():
        missing = [key for key in required if row.get(key) in (None, "")]
        if missing:
            errors.append(f"{code}: missing {','.join(missing)}")
        action = row.get("action")
        counts[action] += 1
        if action not in ACTIONS:
            errors.append(f"{code}: unknown action {action}")
        valuation = valuations.get(code) or {}
        if row.get("valuation_confidence") != valuation.get("confidence_display"):
            errors.append(f"{code}: strategy copied a different confidence")
        if any(key in valuation for key in ("action", "action_level", "action_reason", "initial_position")):
            errors.append(f"{code}: valuation object contains trading fields")
    if counts["暂不参与"] > 5:
        errors.append(f"too many do-not-participate actions: {counts['暂不参与']}")
    if len([action for action, count in counts.items() if count]) < 4:
        errors.append(f"action distribution is not decisive enough: {dict(counts)}")
    if errors:
        raise SystemExit("\n".join(errors[:50]))
    print(json.dumps({"status": "PASS", "companies": 142, "actions": dict(counts), "separated": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
