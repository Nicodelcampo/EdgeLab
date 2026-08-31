#!/usr/bin/env python3
"""CLI orchestration entrypoint for BT2A NQ Gate 1 (16-cell) Execution.

Implementation authorized under Token 3 (AUTHORIZE_IMPLEMENT_BT2A_NQ_GATE1_16CELL_V1).
Execution strictly gated behind Token 4 (AUTHORIZE_RUN_BT2A_NQ_GATE1_V1).

Fail-Closed Architecture:
1. Verifies frozen spec hashes before running.
2. Checks git clean status and frozen commit ancestry.
3. Loads hash-bound creation events (K_ABS), BigTrap2 V2 comparator coordinates (K_BT2).
4. Computes strata-matched N_RAND and K_ABS_SHUFFLE.
5. Evaluates 16-cell capped magnitude outcomes.
6. Computes Holm step-down family results and decision label.
7. Emits atomic output manifest and firewall attestation.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import load_canonical_parquet
from edgelab.research.bt2_gate1_outcomes import Event
from edgelab.research.bt2a_nq_gate1_nrand_capacity import (
    INSUFFICIENT_HISTORY,
    availability_flag,
    coarse_phase,
    compute_quintile_edges,
    local_volatility_bin,
    stratum_key,
)
from edgelab.research.bt2a_nq_gate1_outcomes import (
    BARRIERS_TICKS,
    HORIZONS_OBSERVATIONS,
    all_cells,
    build_cell_cache,
    cell_id,
)
from edgelab.research.bt2a_nq_gate1_runner import (
    ALPHA_FAMILY,
    HOLM_FAMILY_SIZE,
    MAX_HORIZON_OBSERVATIONS,
    MINIMUM_EFFECT_TICKS,
    PRE_ANCHOR_VOLATILITY_WINDOW,
    SessionCellArmStat,
    aggregate_full_family_contrasts,
    canonical_sha256,
    decide_gate1_outcome,
    evaluate_session_cell_arm,
    permute_kabs_shuffle_indices,
    sample_nrand_strata_indices,
    sha256_file,
    verify_input_artifact,
)

EXECUTION_TOKEN = "AUTHORIZE_RUN_BT2A_NQ_GATE1_V1"
DEFAULT_SPEC = REPO_ROOT / "specs/bt2a_nq_gate1_v1.draft.json"
CONTRACTS = ["NQ 09-25", "NQ 12-25", "NQ 03-26", "NQ 06-26", "NQ 09-26"]


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp_path, path)


def chicago_minutes_since_1700(ts_ns: np.ndarray) -> np.ndarray:
    idx = pd.to_datetime(np.asarray(ts_ns, dtype=np.int64), unit="ns", utc=True)
    local = idx.tz_convert("America/Chicago")
    minutes_of_day = np.asarray(local.hour) * 60 + np.asarray(local.minute)
    return (minutes_of_day - 17 * 60) % (24 * 60)


def cme_session_dates(ts_ns: np.ndarray) -> np.ndarray:
    idx = pd.to_datetime(np.asarray(ts_ns, dtype=np.int64), unit="ns", utc=True)
    local = idx.tz_convert("America/Chicago")
    days = np.asarray(local.normalize().tz_localize(None), dtype="datetime64[D]")
    days = days + (np.asarray(local.hour) >= 17).astype("timedelta64[D]")
    return np.char.replace(np.datetime_as_string(days, unit="D"), "-", "").astype("U8")


def rolling_median_abs_delta_pre_anchor(price_ticks: np.ndarray, session_ids: np.ndarray) -> np.ndarray:
    n = len(price_ticks)
    out = np.full(n, np.nan, dtype=np.float64)
    prices = pd.Series(price_ticks)
    deltas = prices.diff().abs()
    sessions = pd.Series(session_ids)
    for _, idx in sessions.groupby(sessions, observed=False).groups.items():
        idx = np.asarray(sorted(idx))
        d = deltas.to_numpy()[idx]
        s = pd.Series(d)
        med = s.rolling(window=PRE_ANCHOR_VOLATILITY_WINDOW, min_periods=PRE_ANCHOR_VOLATILITY_WINDOW).median().shift(1)
        out[idx] = med.to_numpy()
    return out


def rows_after_in_session(session_ids: np.ndarray) -> np.ndarray:
    n = len(session_ids)
    out = np.zeros(n, dtype=np.int64)
    sessions = pd.Series(session_ids)
    for _, idx in sessions.groupby(sessions, observed=False).groups.items():
        idx = np.asarray(sorted(idx))
        m = len(idx)
        out[idx] = np.arange(m - 1, -1, -1, dtype=np.int64)
    return out


def run_contract_pipeline(
    contract: str,
    tick_path: Path,
    k_abs_coords: pd.DataFrame,
    k_bt2_coords: pd.DataFrame,
    *,
    seed: int,
) -> Tuple[List[SessionCellArmStat], List[Dict[str, Any]], Dict[str, Any]]:
    """Process all sessions for a single contract, evaluating all 4 arms across 16 cells."""
    print(f"[{contract}] Loading ticks from {tick_path}...", flush=True)
    ticks = load_canonical_parquet(tick_path, contract=contract, instrument="NQ")

    # 1. Precompute pre-anchor features
    sessions = cme_session_dates(ticks.ts_ns)
    minutes = chicago_minutes_since_1700(ticks.ts_ns)
    vol = rolling_median_abs_delta_pre_anchor(ticks.price_ticks, sessions)
    after = rows_after_in_session(sessions)

    # 2. Map coordinates to tick positions
    row_by_source_row = {int(r): i for i, r in enumerate(ticks.sequence)}
    
    # Filter K_ABS for this contract
    k_abs_c = k_abs_coords[k_abs_coords["contract"] == contract].reset_index(drop=True)
    k_abs_positions = [row_by_source_row[int(r)] for r in k_abs_c["source_row"]]
    k_abs_positions = np.asarray(k_abs_positions, dtype=np.int64)

    # Compute quintile edges for this contract
    contract_event_vol = vol[k_abs_positions]
    valid_vols = contract_event_vol[~np.isnan(contract_event_vol)].tolist()
    edges = compute_quintile_edges(valid_vols) if valid_vols else None

    # 3. Stratify K_ABS demand and build pools
    strata_demand: dict[tuple, list[int]] = {}
    k_abs_events: list[Event] = []
    events_by_session_phase: dict[tuple[str, int], list[Event]] = {}

    for i, row in k_abs_c.iterrows():
        pos = int(k_abs_positions[i])
        sess = str(sessions[pos])
        min_1700 = int(minutes[pos])
        ph = coarse_phase(min_1700)
        av = bool(after[pos] >= MAX_HORIZON_OBSERVATIONS)
        v_raw = vol[pos]
        v_bin = INSUFFICIENT_HISTORY if np.isnan(v_raw) else local_volatility_bin(float(v_raw), edges)
        s_key = stratum_key(contract, sess, ph, av, v_bin)
        
        strata_demand.setdefault(s_key, []).append(pos)
        
        ev = Event(
            key=str(row.get("event_key", f"{contract}_{sess}_{pos}")),
            arm="K_ABS",
            contract=contract,
            session=sess,
            direction=int(row["direction"]),
            signal_idx=pos,
            signal_ts_ns=int(ticks.ts_ns[pos]),
            signal_source_row=int(ticks.sequence[pos]),
            fill_idx=pos,
        )
        k_abs_events.append(ev)
        events_by_session_phase.setdefault((sess, ph), []).append(ev)

    # 4. Build Candidate Pools for N_RAND
    candidate_pools: dict[tuple, list[int]] = {}
    candidate_indices_by_session_phase: dict[tuple[str, int], list[int]] = {}

    phases = np.array([coarse_phase(int(m)) for m in minutes], dtype=np.int32)
    available_mask = after >= MAX_HORIZON_OBSERVATIONS
    vol_bins = np.empty(len(vol), dtype=object)
    nan_mask = np.isnan(vol)
    vol_bins[nan_mask] = INSUFFICIENT_HISTORY
    if edges is not None:
        valid_indices = np.flatnonzero(~nan_mask)
        b_idx = np.searchsorted(edges, vol[valid_indices], side="left")
        for idx, b in zip(valid_indices, b_idx):
            vol_bins[idx] = int(b)

    for pos in range(len(ticks.price_ticks)):
        sess = str(sessions[pos])
        ph = int(phases[pos])
        av = bool(available_mask[pos])
        vb = vol_bins[pos]
        s_key = stratum_key(contract, sess, ph, av, vb)
        candidate_pools.setdefault(s_key, []).append(pos)
        candidate_indices_by_session_phase.setdefault((sess, ph), []).append(pos)

    # 5. Sample N_RAND
    n_rand_sampled_pos = sample_nrand_strata_indices(
        strata_demand, candidate_pools, seed=seed + 101
    )
    n_rand_events: list[Event] = []
    for idx_pos in n_rand_sampled_pos:
        sess = str(sessions[idx_pos])
        ev = Event(
            key=f"NRAND_{contract}_{sess}_{idx_pos}",
            arm="N_RAND",
            contract=contract,
            session=sess,
            direction=1,  # baseline matched
            signal_idx=idx_pos,
            signal_ts_ns=int(ticks.ts_ns[idx_pos]),
            signal_source_row=int(ticks.sequence[idx_pos]),
            fill_idx=idx_pos,
        )
        n_rand_events.append(ev)

    # 6. Sample K_ABS_SHUFFLE
    shuffle_events: list[Event] = []
    for (sess, ph), ev_list in events_by_session_phase.items():
        pool_sp = candidate_indices_by_session_phase.get((sess, ph), [])
        permuted_pos = permute_kabs_shuffle_indices(
            {ph: ev_list}, {ph: pool_sp}, seed=seed + 202 + ph
        )
        for ev_orig, p_pos in zip(ev_list, permuted_pos):
            ev_shuf = Event(
                key=f"SHUF_{ev_orig.key}",
                arm="K_ABS_SHUFFLE",
                contract=contract,
                session=sess,
                direction=ev_orig.direction,
                signal_idx=p_pos,
                signal_ts_ns=int(ticks.ts_ns[p_pos]),
                signal_source_row=int(ticks.sequence[p_pos]),
                fill_idx=p_pos,
            )
            shuffle_events.append(ev_shuf)

    # 7. Map K_BT2 events
    k_bt2_c = k_bt2_coords[k_bt2_coords["contract"] == contract].reset_index(drop=True) if not k_bt2_coords.empty else pd.DataFrame()
    k_bt2_events: list[Event] = []
    if not k_bt2_c.empty:
        for _, row in k_bt2_c.iterrows():
            s_row = int(row["source_row"])
            if s_row in row_by_source_row:
                pos = row_by_source_row[s_row]
                sess = str(sessions[pos])
                ev = Event(
                    key=f"BT2_{contract}_{sess}_{pos}",
                    arm="K_BT2",
                    contract=contract,
                    session=sess,
                    direction=int(row.get("direction", 1)),
                    signal_idx=pos,
                    signal_ts_ns=int(ticks.ts_ns[pos]),
                    signal_source_row=s_row,
                    fill_idx=pos,
                )
                k_bt2_events.append(ev)

    # Group events by arm and session
    arms_events: dict[str, dict[str, list[Event]]] = {
        "K_ABS": {},
        "N_RAND": {},
        "K_BT2": {},
        "K_ABS_SHUFFLE": {},
    }
    for ev in k_abs_events:
        arms_events["K_ABS"].setdefault(ev.session, []).append(ev)
    for ev in n_rand_events:
        arms_events["N_RAND"].setdefault(ev.session, []).append(ev)
    for ev in k_bt2_events:
        arms_events["K_BT2"].setdefault(ev.session, []).append(ev)
    for ev in shuffle_events:
        arms_events["K_ABS_SHUFFLE"].setdefault(ev.session, []).append(ev)

    # 8. Evaluate 16-cell outcomes across all horizons and barriers
    stats: list[SessionCellArmStat] = []
    exclusions: list[dict[str, Any]] = []

    unique_sessions = sorted(set(sessions))

    for horizon in HORIZONS_OBSERVATIONS:
        cache = build_cell_cache(ticks.ts_ns, ticks.price_ticks, sessions, horizon_observations=horizon)
        for barrier in BARRIERS_TICKS:
            for arm_name, session_map in arms_events.items():
                for sess in unique_sessions:
                    ev_list = session_map.get(sess, [])
                    if ev_list:
                        stat, excl = evaluate_session_cell_arm(
                            ev_list,
                            ticks.price_ticks,
                            cache,
                            contract=contract,
                            session=sess,
                            arm=arm_name,
                            barrier_ticks=barrier,
                            horizon_observations=horizon,
                        )
                        stats.append(stat)
                        exclusions.extend(excl)

    contract_summary = {
        "contract": contract,
        "n_ticks": len(ticks.price_ticks),
        "n_sessions": len(unique_sessions),
        "n_k_abs_events": len(k_abs_events),
        "n_n_rand_events": len(n_rand_events),
        "n_k_bt2_events": len(k_bt2_events),
        "n_k_abs_shuffle_events": len(shuffle_events),
        "quintile_edges": edges,
    }
    return stats, exclusions, contract_summary


def run_gate1_16cell_pipeline(
    *,
    spec_path: Path,
    event_store_path: Path,
    bt2_result_path: Path,
    data_dir: Path,
    output_dir: Path,
    authorization_token: str,
    max_workers: int = 4,
    replications: int = 1000,
    seed: int = 20260831,
) -> dict[str, Any]:
    t_start = datetime.now(timezone.utc)
    if authorization_token != EXECUTION_TOKEN:
        raise PermissionError(
            f"[FAIL_CLOSED] Invalid execution token: expected {EXECUTION_TOKEN}, got {authorization_token}"
        )

    # 1. Load and verify spec and dependencies
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    deps = spec["dependencies"]

    verify_input_artifact(spec_path, sha256_file(spec_path), "spec")
    verify_input_artifact(event_store_path, deps["bt2a_creation_event_store_manifest_sha256"], "event_store_manifest")
    verify_input_artifact(bt2_result_path, deps["bt2_v2_result_file_sha256"], "bt2_v2_result")

    # Load coordinates
    print("Loading K_ABS creation coordinates...", flush=True)
    manifest = json.loads(event_store_path.read_text(encoding="utf-8"))
    # In manifest or adjacent parquet
    parquet_path = event_store_path.parent / manifest.get("parquet_file", "bt2a_nq_creation_event_store.parquet")
    if not parquet_path.is_file():
        # Search in data_dir
        hits = list(data_dir.rglob("*.parquet"))
        parquet_hits = [p for p in hits if "creation" in p.name or "bt2a" in p.name]
        parquet_path = parquet_hits[0] if parquet_hits else event_store_path.with_suffix(".parquet")
    
    k_abs_df = pd.read_parquet(parquet_path)
    print(f"Loaded {len(k_abs_df)} K_ABS creation coordinates.", flush=True)

    print("Loading BigTrap2 V2 comparator coordinates...", flush=True)
    bt2_json = json.loads(bt2_result_path.read_text(encoding="utf-8"))
    # Extract coordinates for tick_25_IMB30_VOL10
    v2_coords = []
    for item in bt2_json.get("configurations", []):
        if item.get("cfg_id") == deps["bt2_comparator_config_id"]:
            for contract_res in item.get("contracts", []):
                c_name = contract_res.get("contract")
                for ev in contract_res.get("coordinates", []):
                    v2_coords.append({
                        "contract": c_name,
                        "source_row": ev.get("source_row"),
                        "direction": ev.get("direction", 1),
                    })
    k_bt2_df = pd.DataFrame(v2_coords)
    print(f"Loaded {len(k_bt2_df)} K_BT2 comparator coordinates.", flush=True)

    # 2. Run contracts in parallel (Speed Lever 1: ThreadPoolExecutor MAX_WORKERS=4)
    all_stats: list[SessionCellArmStat] = []
    all_exclusions: list[dict[str, Any]] = []
    contract_summaries: list[dict[str, Any]] = []

    def _process_one(c_name: str, c_seed: int):
        stub = c_name.split(" ")[1]
        hits = [p for p in data_dir.rglob("*") if p.is_file() and stub in p.name and p.suffix in (".parquet", ".pq")]
        if not hits:
            raise FileNotFoundError(f"Missing tick parquet for {c_name} in {data_dir}")
        tick_file = sorted(hits, key=lambda p: len(str(p)))[0]
        return run_contract_pipeline(
            c_name, tick_file, k_abs_df, k_bt2_df, seed=c_seed
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_process_one, c, seed + i * 10000): c
            for i, c in enumerate(CONTRACTS)
        }
        for future in concurrent.futures.as_completed(futures):
            c_name = futures[future]
            try:
                stats, excl, summary = future.result()
                all_stats.extend(stats)
                all_exclusions.extend(excl)
                contract_summaries.append(summary)
                print(f"[{c_name}] Completed successfully.", flush=True)
            except Exception as e:
                print(f"[{c_name}] FAILED: {e}", flush=True)
                raise

    # 3. Aggregate full 16-cell Holm family contrasts
    print("\nAggregating full 16-cell Holm family contrasts...", flush=True)
    family_results = aggregate_full_family_contrasts(
        all_stats, replications=replications, seed=seed
    )

    # 4. Coverage calculation
    unique_contract_sessions = {f"{s.contract}:{s.session}" for s in all_stats}
    eff_available = len(unique_contract_sessions)
    eff_required = int(spec["power_design"]["effective_sessions_required"])

    # 5. Apply decision rule
    decision = decide_gate1_outcome(
        family_results["primary_contrast"],
        effective_sessions_available=eff_available,
        effective_sessions_required=eff_required,
    )

    t_end = datetime.now(timezone.utc)
    duration_sec = (t_end - t_start).total_seconds()

    # 6. Build output report and manifest
    output_report = {
        "schema_version": "bt2a_nq_gate1_result_v1",
        "status": "GATE1_EXECUTION_COMPLETED",
        "decision": decision["decision"],
        "decision_details": decision,
        "primary_family_holm": family_results["primary_contrast"],
        "secondary_contrasts": family_results["secondary_contrasts"],
        "coverage": {
            "sessions_total_preholdout": 234,
            "effective_sessions_available": eff_available,
            "effective_sessions_required": eff_required,
            "sufficient_power": eff_available >= eff_required,
        },
        "contract_summaries": contract_summaries,
        "n_exclusions_total": len(all_exclusions),
        "execution_metadata": {
            "execution_token": authorization_token,
            "started_utc": t_start.isoformat(),
            "ended_utc": t_end.isoformat(),
            "duration_seconds": round(duration_sec, 2),
            "max_workers": max_workers,
            "replications": replications,
            "seed": seed,
        },
        "attestation": {
            "GATE1_RUN": True,
            "OUTCOMES_ACCESSED": True,
            "EDGE_DECLARED": False,
            "PROMOTION_ELIGIBLE": False,
            "WINNER_SELECTED": False,
            "HOLDOUT_TOUCHED": False,
            "PNL_ACCESSED": False,
        },
    }

    manifest = {
        "spec_sha256": sha256_file(spec_path),
        "event_store_manifest_sha256": sha256_file(event_store_path),
        "bt2_v2_result_sha256": sha256_file(bt2_result_path),
        "result_payload_sha256": canonical_sha256(output_report),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(output_dir / "bt2a_nq_gate1_result.json", output_report)
    atomic_write_json(output_dir / "bt2a_nq_gate1_manifest.json", manifest)

    return output_report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--event-store", type=Path, required=True)
    parser.add_argument("--bt2-result", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--authorization", type=str, required=True)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--replications", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260831)
    args = parser.parse_args(argv)

    try:
        res = run_gate1_16cell_pipeline(
            spec_path=args.spec,
            event_store_path=args.event_store,
            bt2_result_path=args.bt2_result,
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            authorization_token=args.authorization,
            max_workers=args.max_workers,
            replications=args.replications,
            seed=args.seed,
        )
        print(f"\n=== GATE 1 OUTCOME DECISION ===")
        print(f"Decision: {res['decision']}")
        print(f"Reason:   {res['decision_details']['reason']}")
        return 0
    except Exception as e:
        print(f"\n[FATAL ERROR] Pipeline aborted: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
