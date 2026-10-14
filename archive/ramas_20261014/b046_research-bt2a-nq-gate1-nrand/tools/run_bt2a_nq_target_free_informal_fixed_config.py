#!/usr/bin/env python3
"""Kaggle-only: informal fixed-config creation-only partitions for the 3 NQ
contracts never run under the formal target-free selection campaign.

Context: the formal campaign (tools/run_bt2a_nq_target_free_selection.py)
early-stopped at 2/5 contracts (NQ 09-25, NQ 12-25) by explicit decision
(docs/research/DECISION_NQ_SELECTION_EARLY_STOP_2026-08-29.md). Nico chose
the informal path over resuming the full 104-config campaign: generate
creation-only coordinates for ONLY the already-adopted config_id
bt2a_nq_7e84981882b0b380 across the 3 missing contracts, instead of
repeating all 104 configs. This script reuses
tools.run_bt2a_nq_target_free_selection's proven per-contract computation
path unchanged (same event schema, same coordinate/checkpoint file layout,
same firewall discipline) restricted to that single config.

Target-free: no outcomes, no lifecycle, no first passage, no MFE/MAE, no
PnL, no holdout access. Same as the formal campaign it borrows from.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edgelab.research.all5_runtime.bigtrap2absorption import run as run_bt2a
from edgelab.research.all5_runtime.ticks import load_canonical_parquet
from tools.build_event_store_all5_v2 import expand_sessions
from tools.run_bt2a_nq_target_free_selection import (
    COORDINATE_COLUMNS,
    HOLDOUT_NS,
    _checkpoint_path,
    _coordinate_path,
    _contract_filename,
    _resume_valid,
    atomic_write_json,
    canonical_sha256,
    creation_event_key,
    expand_configs,
    load_json,
    preflight,
    require_execution,
    sha256_file,
    verify_package_and_effective_registry,
)
from tools.sweep_bigtrap2_nq_tickframes_v2 import (
    cme_session_dates,
    cme_session_to_utc_bounds_ns,
    verify_git_clean_and_head,
)

FIXED_CONFIG_ID = "bt2a_nq_7e84981882b0b380"
MISSING_CONTRACTS = ("NQ 03-26", "NQ 06-26", "NQ 09-26")


def run_contract_fixed_config(
    spec_path: Path, data_dir: Path, output_dir: Path, expected_commit: str,
    token: str | None, contract: str, resume: bool,
) -> dict[str, Any]:
    if contract not in MISSING_CONTRACTS:
        raise RuntimeError(
            f"this informal runner only covers the 3 missing contracts "
            f"{MISSING_CONTRACTS}, not {contract!r} -- use the formal "
            f"campaign for NQ 09-25/NQ 12-25"
        )
    readiness = preflight(spec_path, data_dir, output_dir, expected_commit)
    if readiness["status"] != "PASS_READY_FOR_FREEZE_OR_EXECUTION":
        raise RuntimeError("ABSTAIN_BT2A_NQ_PREFLIGHT_NOT_READY")
    spec = load_json(spec_path)
    require_execution(spec, expected_commit, token)
    if contract not in spec["universe"]["contracts"]:
        raise RuntimeError(f"unknown contract partition: {contract}")

    all_configs = expand_configs(spec)
    configs = [c for c in all_configs if c["config_id"] == FIXED_CONFIG_ID]
    if len(configs) != 1:
        raise RuntimeError(
            f"FIXED_CONFIG_ID {FIXED_CONFIG_ID} must resolve to exactly one "
            f"config in the frozen grid, found {len(configs)}"
        )

    _, effective, provenance = verify_package_and_effective_registry(data_dir, spec)
    registry = load_json(ROOT / spec["binding"]["session_registry_path"])
    session_rows = [row for row in expand_sessions(registry) if row["contract"] == contract]
    valid_sessions = {row["cme_session_id"] for row in session_rows}
    if not valid_sessions:
        raise RuntimeError("empty contract session partition")
    first_warmup = registry["initial_warmup_session"][contract]
    start_ns = cme_session_to_utc_bounds_ns(first_warmup)[0]
    end_ns = max(cme_session_to_utc_bounds_ns(row["cme_session_id"])[1] for row in session_rows)
    if end_ns > HOLDOUT_NS:
        raise RuntimeError("registered partition reaches holdout")
    entry = effective["contracts"][contract]
    parquet = data_dir / entry["parquet_file"]
    ticks = load_canonical_parquet(
        parquet, contract=contract, instrument="NQ", start_utc_ns=start_ns, end_utc_ns=end_ns
    )
    if len(ticks) == 0 or np.any(np.asarray(ticks.ts_ns, dtype=np.int64) >= HOLDOUT_NS):
        raise RuntimeError("empty partition or holdout tick decoded")
    labels = cme_session_dates(np.asarray(ticks.ts_ns, dtype=np.int64))
    spec_sha = sha256_file(spec_path)
    completed = skipped = 0
    for config in configs:
        coordinate = _coordinate_path(output_dir, config, contract)
        checkpoint = _checkpoint_path(output_dir, config, contract)
        if resume and _resume_valid(checkpoint, coordinate, spec_sha, config):
            skipped += 1
            continue
        result = run_bt2a(ticks, params=config["params"])
        rows = []
        for zone in result.get("zones", []):
            index = int(zone["sig_idx"])
            if index < 0 or index >= len(ticks.ts_ns):
                raise RuntimeError("BT2A creation index outside decoded partition")
            session = str(labels[index])
            if session not in valid_sessions:
                continue
            direction = 1 if str(zone["dir"]) == "long" else -1
            event_time = int(ticks.ts_ns[index])
            source_row = int(ticks.sequence[index])
            rows.append({
                "config_id": config["config_id"],
                "contract": contract,
                "cme_session_id": session,
                "event_time_ns": event_time,
                "source_row": source_row,
                "direction": direction,
                "signal_price_ticks": int(ticks.price_ticks[index]),
                "a_score": float(zone["a_score"]),
                "a_threshold": float(zone["a_thr"]),
                "event_key": creation_event_key(contract, session, direction, event_time, source_row),
            })
        frame = pd.DataFrame(rows, columns=COORDINATE_COLUMNS)
        if len(frame):
            frame = frame.sort_values(
                ["cme_session_id", "event_time_ns", "source_row", "direction", "event_key"], kind="stable"
            )
            if frame["event_key"].duplicated().any():
                raise RuntimeError("duplicate creation event identity")
        coordinate.parent.mkdir(parents=True, exist_ok=True)
        temp = coordinate.with_suffix(".parquet.tmp")
        frame.to_parquet(temp, index=False, compression="zstd")
        os.replace(temp, coordinate)
        body = {
            "schema_version": "bt2a_nq_target_free_partition_v1",
            "status": "COMPLETE_TARGET_FREE_PARTITION",
            "informal_fixed_config": True,
            "config_id": config["config_id"],
            "contract": contract,
            "spec_file_sha256": spec_sha,
            "params_sha256": canonical_sha256(config["params"]),
            "coordinate_file": coordinate.relative_to(output_dir).as_posix(),
            "coordinate_file_sha256": sha256_file(coordinate),
            "coordinate_file_bytes": coordinate.stat().st_size,
            "n_events": len(frame),
            "n_sessions_with_events": int(frame["cme_session_id"].nunique()) if len(frame) else 0,
            "event_set_sha256": canonical_sha256(frame["event_key"].tolist()),
            "package_provenance": provenance,
            "firewall": {
                "target_free": True, "lifecycle_accessed": False, "future_price_path_accessed": False,
                "first_touch_accessed": False, "first_passage_accessed": False,
                "mfe_mae_accessed": False, "pnl_accessed": False, "holdout_touched": False,
            },
        }
        body["payload_sha256"] = canonical_sha256(body)
        atomic_write_json(checkpoint, body)
        completed += 1
    verify_git_clean_and_head(expected_commit)
    status = {
        "status": "COMPLETE_INFORMAL_FIXED_CONFIG_CONTRACT_PARTITION",
        "informal_fixed_config": True,
        "config_id": FIXED_CONFIG_ID,
        "contract": contract,
        "configs_completed": completed,
        "configs_resumed": skipped,
        "total_configs": len(configs),
        "outcomes_accessed": False,
        "holdout_touched": False,
    }
    atomic_write_json(output_dir / f"contract_status_{_contract_filename(contract)}.json", status)
    return status


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", type=Path, required=True)
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--expected-commit", required=True)
    p.add_argument("--execution-token")
    p.add_argument("--contract", required=True, choices=list(MISSING_CONTRACTS))
    p.add_argument("--resume", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    token = args.execution_token or os.environ.get("EDGELAB_AUTHORIZATION_TOKEN")
    result = run_contract_fixed_config(
        args.spec, args.data_dir, args.output_dir, args.expected_commit,
        token, args.contract, args.resume,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if str(result["status"]).startswith("COMPLETE") else 3


if __name__ == "__main__":
    raise SystemExit(main())
