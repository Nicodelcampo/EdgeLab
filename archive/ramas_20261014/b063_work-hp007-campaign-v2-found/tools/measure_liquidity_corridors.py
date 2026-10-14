#!/usr/bin/env python3
"""Portable HP-007 causal measurement runner.

Input is JSONL, one record per signal, with a nested ``ticks`` array. This is
intentionally an exchange format: local/Kaggle adapters must build the records
from certified point-in-time data. The runner never scans repository datasets
and cannot silently open the holdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from edgelab.research.liquidity_corridors import (
    CorridorDefinition, CorridorSignal, TradeTick, resolve_first_passage,
    select_non_overlapping,
)


def canonical_sha256(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-jsonl", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--output-json", required=True)
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    required = {"campaign_id", "definition", "target_ticks", "stop_ticks", "horizon_ns",
                "cooldown_ns", "friction_ticks_round_turn", "n_eff_declared"}
    missing = sorted(required - manifest.keys())
    if missing:
        raise SystemExit(f"manifest missing keys: {missing}")
    definition = CorridorDefinition(**manifest["definition"])

    rows = [json.loads(line) for line in Path(args.input_jsonl).read_text(encoding="utf-8").splitlines() if line.strip()]
    signals = [CorridorSignal(**row["signal"]) for row in rows]
    qualified_ids = {
        s.event_id for s in signals if definition.qualifies(
            forward_density=s.forward_density, backstop_density=s.backstop_density,
            width_ticks=s.width_ticks)
    }
    selected = select_non_overlapping((s for s in signals if s.event_id in qualified_ids),
                                      cooldown_ns=int(manifest["cooldown_ns"]))
    row_by_id = {row["signal"]["event_id"]: row for row in rows}
    outcomes = []
    for signal in selected:
        ts = [TradeTick(**tick) for tick in row_by_id[signal.event_id]["ticks"]]
        outcomes.append(asdict(resolve_first_passage(
            signal, ts, target_ticks=int(manifest["target_ticks"]),
            stop_ticks=int(manifest["stop_ticks"]), horizon_ns=int(manifest["horizon_ns"]),
            friction_ticks_round_turn=float(manifest["friction_ticks_round_turn"]))))

    result = {
        "status": "EXPLORATORY_MEASUREMENT_ONLY",
        "campaign_id": manifest["campaign_id"],
        "manifest_sha256": canonical_sha256(manifest),
        "input_sha256": hashlib.sha256(Path(args.input_jsonl).read_bytes()).hexdigest(),
        "n_eff_declared": manifest["n_eff_declared"],
        "n_input": len(rows),
        "n_qualified": len(qualified_ids),
        "n_non_overlapping": len(selected),
        "outcomes": outcomes,
    }
    Path(args.output_json).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
