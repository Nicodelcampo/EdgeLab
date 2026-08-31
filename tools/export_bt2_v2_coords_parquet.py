# -*- coding: utf-8 -*-
"""Export per-zone BigTrap2 V2 coordinates for one frozen grid cell to Parquet.

`sweep_bigtrap2_nq_tickframes_v2.py` computed the full 51-config grid but only
ever persisted aggregate counts per config -- the per-zone rows lived
transiently in memory and were discarded. BT2A NQ Gate 1's K_BT2 secondary
comparator needs the raw zone coordinates for exactly one already-selected,
already-frozen config (`tick_25_IMB30_VOL10`, cfg_id decision recorded in
specs/bt2a_nq_gate1_v1.draft.json / BT2A_NQ_GATE1_POWER_CLOSURE_2026-08-30.md).

This tool reuses the same fail-closed gates, package verification and session
expansion as the V2 sweep (same frozen spec, same execution token -- this is
the same authorized campaign re-exporting one cell's raw output, not a new
campaign), restricted to that single config, and refuses to write the Parquet
unless the recomputed aggregate (event count, session coverage) matches the
already-frozen V2 result file exactly. A mismatch means the two runs disagree
on the same computation and must not be papered over.
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.bars import build_footprints, build_tick_bars
from edgelab.bridge.indicators.bigtrap2_creation_only import detect_creations_only
from tools.build_event_store_all5_v2 import expand_sessions
from tools.sweep_bigtrap2_nq_tickframes_v2 import (
    HOLDOUT_CUTOFF_UTC_NS,
    _atomic_write_json,
    _load_json_object,
    cme_session_dates,
    cme_session_to_utc_bounds_ns,
    compute_sha256,
    validate_kaggle_runtime,
    verify_git_clean_and_head,
    verify_inputs_fail_closed,
    verify_package_and_effective_registry,
    verify_runtime_execution_gates,
)
from edgelab.bridge.ticks import load_canonical_parquet

TARGET_CFG_ID = "tick_25_IMB30_VOL10"
TARGET_BAR_TYPE = "tick_25"
TARGET_IMBALANCE_RATIO = 3.0
TARGET_MIN_TRAP_VOLUME = 10
TARGET_TICKS_PER_BAR = 25

COORD_COLUMNS = [
    "contract",
    "session_id",
    "bar_time_ns",
    "side",
    "top",
    "bottom",
    "width_ticks",
    "bar_idx",
    "source_row",
    "direction",
]


def zones_for_contract(
    pq_path: Path,
    contract: str,
    min_start_ns: int,
    max_end_ns: int,
    valid_sessions: set[str],
) -> list[dict[str, Any]]:
    effective_end = min(max_end_ns, HOLDOUT_CUTOFF_UTC_NS)
    ticks = load_canonical_parquet(
        path=pq_path,
        contract=contract,
        start_utc_ns=min_start_ns,
        end_utc_ns=effective_end,
        instrument="NQ",
    )
    import numpy as np

    if np.any(ticks.ts_ns >= HOLDOUT_CUTOFF_UTC_NS):
        raise RuntimeError(f"[FAIL_CLOSED] Holdout tick decoded for {contract}")

    bars = build_tick_bars(ticks, TARGET_TICKS_PER_BAR, reiniciar_por_sesion=True)
    footprints = build_footprints(ticks, bars)
    session_ids = cme_session_dates(bars.end_ns)

    # Same convention as tools/build_event_store_all5_v2.py's BigTrap2 block:
    # the creation signal is anchored at the close (last tick) of the bar the
    # zone was created in, identified by ticks.sequence (the CME source_row),
    # not by bar index or timestamp -- Gate 1's loader looks anchors up by
    # source_row against its own independently-loaded tick series.
    n_ticks = len(ticks.ts_ns)
    bar_close_indices = np.concatenate(
        (np.flatnonzero(np.diff(bars.tick_bar_idx)) + 1, [n_ticks])
    ) - 1

    zones = detect_creations_only(
        ticks,
        bars,
        footprints,
        params={
            "imbalance_ratio": TARGET_IMBALANCE_RATIO,
            "min_trap_volume": TARGET_MIN_TRAP_VOLUME,
            "min_export_volume": TARGET_MIN_TRAP_VOLUME,
            "use_wick_filter": False,
        },
    )
    rows: list[dict[str, Any]] = []
    for zone in zones:
        bar_index = zone["bar_idx"]
        if 0 <= bar_index < len(session_ids) and session_ids[bar_index] in valid_sessions:
            if bar_index >= len(bar_close_indices):
                continue
            sig_idx = int(bar_close_indices[bar_index])
            rows.append(
                {
                    "contract": contract,
                    "session_id": session_ids[bar_index],
                    "bar_time_ns": int(zone["bar_time_ns"]),
                    "side": zone["side"],
                    "source_row": int(ticks.sequence[sig_idx]),
                    # Same rule as build_event_store_all5_v2.py's BigTrap2 block:
                    # trapped sellers get pushed, price expected up -> +1.
                    "direction": 1 if zone["kind"] == "trapped_sellers" else -1,
                    "top": float(zone["top"]),
                    "bottom": float(zone["bottom"]),
                    "width_ticks": float(zone["width_ticks"]),
                    "bar_idx": int(bar_index),
                }
            )
    del ticks, bars, footprints, session_ids
    gc.collect()
    return rows


def build_coords_rows(
    session_registry: dict[str, Any],
    verified_paths: dict[str, Path],
) -> list[dict[str, Any]]:
    expanded = expand_sessions(session_registry)
    sessions_by_contract: dict[str, set[str]] = {}
    bounds_by_contract: dict[str, tuple[int, int]] = {}
    for row in expanded:
        contract = row["contract"]
        session_id = row["cme_session_id"]
        sessions_by_contract.setdefault(contract, set()).add(session_id)
        start_ns, end_ns = cme_session_to_utc_bounds_ns(session_id)
        if end_ns > HOLDOUT_CUTOFF_UTC_NS:
            raise RuntimeError("[FAIL_CLOSED] Registered session reaches holdout")
        if contract not in bounds_by_contract:
            bounds_by_contract[contract] = (start_ns, end_ns)
        else:
            cur_start, cur_end = bounds_by_contract[contract]
            bounds_by_contract[contract] = (min(cur_start, start_ns), max(cur_end, end_ns))

    all_rows: list[dict[str, Any]] = []
    for contract in session_registry["selection"]["contracts"]:
        all_rows.extend(
            zones_for_contract(
                pq_path=verified_paths[contract],
                contract=contract,
                min_start_ns=bounds_by_contract[contract][0],
                max_end_ns=bounds_by_contract[contract][1],
                valid_sessions=sessions_by_contract[contract],
            )
        )
    return all_rows


def verify_against_frozen_result(rows: list[dict[str, Any]], frozen_result_path: Path) -> dict[str, Any]:
    """Fail-closed cross-check: this export must reproduce the already-frozen
    V2 aggregate for the same cfg_id exactly, or it does not get written."""
    frozen = _load_json_object(frozen_result_path)
    frozen_row = next(
        (r for r in frozen.get("results", []) if r.get("cfg_id") == TARGET_CFG_ID), None
    )
    if frozen_row is None:
        raise RuntimeError(f"[FAIL_CLOSED] {TARGET_CFG_ID} absent from frozen V2 result")

    total_events = len(rows)
    sessions_with_events = len({r["session_id"] for r in rows})
    if total_events != frozen_row["total_events"]:
        raise RuntimeError(
            "[FAIL_CLOSED] Recomputed event count disagrees with frozen V2 result: "
            f"got {total_events}, frozen {frozen_row['total_events']}"
        )
    if sessions_with_events != frozen_row["sessions_with_events"]:
        raise RuntimeError(
            "[FAIL_CLOSED] Recomputed session coverage disagrees with frozen V2 result: "
            f"got {sessions_with_events}, frozen {frozen_row['sessions_with_events']}"
        )
    return {
        "total_events": total_events,
        "sessions_with_events": sessions_with_events,
        "matches_frozen_v2_result": True,
        "frozen_result_file_sha256": compute_sha256(frozen_result_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--execution-token")
    parser.add_argument("--frozen-result", type=Path, required=True)
    parser.add_argument("--output-parquet", type=Path, required=True)
    args = parser.parse_args(argv)

    import os

    data_dir, output_parquet = validate_kaggle_runtime(args.data_dir, args.output_parquet)
    spec = _load_json_object(args.spec)
    execution_token = args.execution_token or os.environ.get("EDGELAB_AUTHORIZATION_TOKEN")
    verify_runtime_execution_gates(spec, args.expected_commit, execution_token)

    session_registry_path = REPO_ROOT / spec["binding"]["session_registry_path"]
    if compute_sha256(session_registry_path) != spec["binding"]["session_registry_sha256"]:
        raise RuntimeError("[FAIL_CLOSED] Session registry SHA-256 mismatch")
    source_registry_path = REPO_ROOT / spec["binding"]["source_input_registry_path"]
    if compute_sha256(source_registry_path) != spec["binding"]["source_input_registry_sha256"]:
        raise RuntimeError("[FAIL_CLOSED] Source input registry SHA-256 mismatch")

    _, effective_registry, _ = verify_package_and_effective_registry(data_dir, spec)
    verified_paths = verify_inputs_fail_closed(data_dir, effective_registry)
    session_registry = _load_json_object(session_registry_path)

    started = time.time()
    rows = build_coords_rows(session_registry, verified_paths)
    check = verify_against_frozen_result(rows, args.frozen_result)

    df = pd.DataFrame(rows, columns=COORD_COLUMNS)
    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_parquet, index=False)

    manifest = {
        "schema_version": "bt2_v2_coords_export_v1",
        "cfg_id": TARGET_CFG_ID,
        "frozen_commit": args.expected_commit,
        "elapsed_seconds": round(time.time() - started, 1),
        "output_parquet_sha256": compute_sha256(output_parquet),
        "row_count": len(df),
        **check,
        "firewalls": {
            "future_price_path_accessed": False,
            "first_touch_accessed": False,
            "pnl_accessed": False,
            "holdout_touched": False,
        },
    }
    _atomic_write_json(output_parquet.with_suffix(".manifest.json"), manifest)
    verify_git_clean_and_head(args.expected_commit)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
