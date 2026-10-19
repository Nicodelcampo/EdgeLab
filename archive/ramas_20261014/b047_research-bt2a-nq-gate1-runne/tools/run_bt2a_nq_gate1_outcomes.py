#!/usr/bin/env python3
"""CLI orchestration entrypoint for BT2A NQ Gate 1 (16-cell) Execution.

Implementation authorized under Token 3 (AUTHORIZE_IMPLEMENT_BT2A_NQ_GATE1_16CELL_V1).
Execution strictly gated behind Token 4 (AUTHORIZE_RUN_BT2A_NQ_GATE1_V1).

Fail-Closed Architecture:
1. Verifies the spec against the FROZEN sha256 pin (not against itself).
2. Verifies the event store manifest and the BT2 V2 result against the spec's
   hash bindings.
3. Positive holdout check on decoded ticks (measured, not attested).
4. Per-contract mode writes atomic per-contract stats; aggregate mode combines
   them. Parallelism lives in the Kaggle LAUNCHER as a thread pool of
   subprocesses per KAGGLE_LAUNCHER_PARALLELISM_POLICY_V1_2026-08-30.md, not
   inside this tool.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.research.bt2_gate1_outcomes import Event
from edgelab.research.bt2a_nq_gate1_nrand_capacity import (
    INSUFFICIENT_HISTORY,
    coarse_phase,
    compute_quintile_edges,
    local_volatility_bin,
    stratum_key,
)
from edgelab.research.bt2a_nq_gate1_outcomes import (
    BARRIERS_TICKS,
    HORIZONS_OBSERVATIONS,
    build_cell_cache,
)
from edgelab.research.bt2a_nq_gate1_runner import (
    MAX_HORIZON_OBSERVATIONS,
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
# The frozen spec pin (Gate 1 spec froze at commit 8b1f334f, backfill c70bdb5d,
# event-store manifest rebound 2026-08-31 under AUTHORIZE_REBIND_BT2A_EVENT_STORE_MANIFEST_V1,
# docs/research/DECISION_NICO_REBIND_EVENT_STORE_MANIFEST_2026-08-31.md).
# Verified against the file, never recomputed-and-self-compared.
FROZEN_SPEC_SHA256 = "b9e75c2533091c3dc8a3a2c8b8b8efde6eb6dfe1313efae48a4b4885366695c3"
HOLDOUT_OPEN_UTC_NS = 1782856800000000000
DEFAULT_SPEC = REPO_ROOT / "specs/bt2a_nq_gate1_v1.draft.json"
CONTRACTS = ["NQ 09-25", "NQ 12-25", "NQ 03-26", "NQ 06-26", "NQ 09-26"]


class _LightTicks:
    """Memory-bounded tick container: only the 3 columns this pipeline uses."""
    __slots__ = ("ts_ns", "price_ticks", "sequence")

    def __init__(self, ts_ns, price_ticks, sequence):
        self.ts_ns = ts_ns
        self.price_ticks = price_ticks
        self.sequence = sequence


def _load_ticks_light(tick_path: Path, contract: str) -> _LightTicks:
    """Read ONLY ts_utc_ns / price_ticks / sequence via pyarrow column selection.

    load_canonical_parquet loads all 6 numeric columns (~1.6 GB for a 34M-row
    contract); the 16-cell evaluation never touches volume/bid/ask. Keeps the
    P0 gate: non-monotonic timestamps raise.
    """
    import pyarrow.parquet as pq

    tbl = pq.read_table(
        tick_path,
        columns=["ts_utc_ns", "price_ticks", "sequence"],
        filters=[("contract", "==", contract)],
    )
    if tbl.num_rows == 0:
        raise RuntimeError(f"empty tick selection for {contract}: {tick_path}")
    ts_ns = tbl.column("ts_utc_ns").to_numpy(zero_copy_only=False).astype(np.int64)
    price_ticks = tbl.column("price_ticks").to_numpy(zero_copy_only=False).astype(np.int64)
    sequence = tbl.column("sequence").to_numpy(zero_copy_only=False).astype(np.int64)
    d = np.diff(ts_ns)
    if len(d) and d.min() < 0:
        raise ValueError("ticks no monótonos (gate P0): auditar/ordenar antes de usar")
    return _LightTicks(ts_ns, price_ticks, sequence)


def _positions_of_source_rows(sequence: np.ndarray, source_rows) -> np.ndarray:
    """Map source_row -> tick position via binary search instead of a Python
    dict with one entry per tick (~2.7 GB at 34M rows, per worker).

    Fail-closed: requires the contract's sequence to be strictly increasing
    (true in the canonical store, where sequence is the source row index —
    P-28). Any violation raises instead of silently mis-mapping.
    """
    seq = np.asarray(sequence, dtype=np.int64)
    if len(seq) and np.any(np.diff(seq) <= 0):
        raise RuntimeError("[FAIL_CLOSED] sequence not strictly increasing; refusing searchsorted map")
    rows = np.asarray(list(source_rows), dtype=np.int64)
    pos = np.searchsorted(seq, rows)
    if np.any(pos >= len(seq)) or np.any(seq[pos] != rows):
        raise RuntimeError("[FAIL_CLOSED] source_row absent from tick sequence")
    return pos


def _build_stratum_pools(sessions, minutes, vol, after, contract, edges):
    """Vectorized stratum pool construction — identical outputs to the original
    per-tick Python loop without its memory cost (measured in the auditor
    sandbox: ~470 MB of Python structures at 3M ticks, extrapolated ~4.4 GB
    per worker at 34M ticks; that footprint is what OOM-restarted the Kaggle
    session twice, at MAX_WORKERS=4 and at MAX_WORKERS=2 alike).

    Bit-identical semantics, verified against the function bodies:
    coarse_phase(m) == m // 240 for normalized minutes, and
    local_volatility_bin(v, edges) == searchsorted(sorted(edges), v, side="left").
    Pools are stored as numpy arrays (no per-int boxing).
    """
    sess_codes, sess_uniques = pd.factorize(sessions, sort=True)
    sess_codes = sess_codes.astype(np.int64)
    phases = (np.asarray(minutes, dtype=np.int64) // 240).astype(np.int64)
    avail = (np.asarray(after) >= MAX_HORIZON_OBSERVATIONS).astype(np.int64)
    vol_arr = np.asarray(vol, dtype=np.float64)
    nan_mask = np.isnan(vol_arr)
    vb = np.full(len(vol_arr), -1, dtype=np.int64)  # -1 == INSUFFICIENT_HISTORY
    if edges is not None:
        edge_arr = np.asarray(sorted(float(e) for e in edges), dtype=np.float64)
        vb[~nan_mask] = np.searchsorted(edge_arr, vol_arr[~nan_mask], side="left")

    key = (((sess_codes * 6 + phases) * 2 + avail) * 6 + (vb + 1))
    order = np.argsort(key, kind="stable")
    sorted_key = key[order]
    uniq, first, counts = np.unique(sorted_key, return_index=True, return_counts=True)

    pools: dict[tuple, np.ndarray] = {}
    for u, f, c in zip(uniq.tolist(), first.tolist(), counts.tolist()):
        uu = int(u)
        vb1 = uu % 6; uu //= 6
        av = uu % 2; uu //= 2
        ph = uu % 6; uu //= 6
        sess = str(sess_uniques[uu])
        v_bin = INSUFFICIENT_HISTORY if vb1 == 0 else int(vb1 - 1)
        pools[stratum_key(contract, sess, int(ph), bool(av), v_bin)] = order[f:f + c]

    key2 = sess_codes * 6 + phases
    order2 = np.argsort(key2, kind="stable")
    s2 = key2[order2]
    uniq2, first2, counts2 = np.unique(s2, return_index=True, return_counts=True)
    by_phase: dict[tuple[str, int], np.ndarray] = {}
    for u, f, c in zip(uniq2.tolist(), first2.tolist(), counts2.tolist()):
        uu = int(u)
        by_phase[(str(sess_uniques[uu // 6]), int(uu % 6))] = order2[f:f + c]
    return pools, by_phase


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


PRE_ANCHOR_VOLATILITY_WINDOW = 500


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


def verify_frozen_inputs(spec_path: Path, event_store_path: Path, bt2_result_path: Path) -> dict:
    """Verify spec against the frozen pin, and inputs against the spec's bindings."""
    verify_input_artifact(spec_path, FROZEN_SPEC_SHA256, "spec")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    deps = spec["dependencies"]
    verify_input_artifact(event_store_path, deps["bt2a_creation_event_store_manifest_sha256"], "event_store_manifest")
    verify_input_artifact(bt2_result_path, deps["bt2_v2_result_file_sha256"], "bt2_v2_result")
    return spec


def load_k_abs_coords(event_store_path: Path) -> pd.DataFrame:
    manifest = json.loads(event_store_path.read_text(encoding="utf-8"))
    parquet_path = event_store_path.parent / manifest.get("parquet_file", "bt2a_nq_creation_events.parquet")
    if not parquet_path.is_file():
        raise FileNotFoundError(f"creation event parquet not found next to manifest: {parquet_path}")
    df = pd.read_parquet(parquet_path)
    if df.empty:
        raise RuntimeError("K_ABS creation coordinates parquet is empty")
    return df


def load_k_bt2_coords(bt2_coords_path: Path, contract: str) -> pd.DataFrame:
    """Load the staged BT2 comparator coordinates parquet for one contract.

    The V2 sweep RESULT json only carries summary rows; the creation
    coordinates artifact is staged physically (the spec declares this staging
    as a separate pending step). Fail-closed: missing file, wrong schema or
    zero rows for the contract all raise.
    """
    if not bt2_coords_path.is_file():
        raise FileNotFoundError(f"BT2 comparator coordinates not staged: {bt2_coords_path}")
    df = pd.read_parquet(bt2_coords_path)
    required = {"contract", "source_row", "direction"}
    if not required.issubset(set(df.columns)):
        raise RuntimeError(f"BT2 coordinates schema mismatch: need {sorted(required)}, got {sorted(df.columns)}")
    out = df[df["contract"] == contract]
    if out.empty:
        raise RuntimeError(f"BT2 comparator coordinates staged but empty for {contract}")
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
    import time as _time
    _t0 = _time.monotonic()
    print(f"[{contract}] Loading ticks from {tick_path}...", flush=True)
    ticks = _load_ticks_light(tick_path, contract)
    print(f"[{contract}] {len(ticks.ts_ns):,} ticks loaded ({_time.monotonic() - _t0:.1f}s)", flush=True)

    # Positive holdout check: measured, not attested.
    if np.any(ticks.ts_ns >= HOLDOUT_OPEN_UTC_NS):
        raise RuntimeError(f"[FAIL_CLOSED] Holdout tick decoded for {contract}")

    # 1. Precompute pre-anchor features once per contract (speed lever 2)
    sessions = cme_session_dates(ticks.ts_ns)
    minutes = chicago_minutes_since_1700(ticks.ts_ns)
    vol = rolling_median_abs_delta_pre_anchor(ticks.price_ticks, sessions)
    after = rows_after_in_session(sessions)

    # 2. Map coordinates to tick positions (binary search, not a per-tick dict)
    k_abs_c = k_abs_coords[k_abs_coords["contract"] == contract].reset_index(drop=True)
    if k_abs_c.empty:
        raise RuntimeError(f"no K_ABS coordinates for {contract}")
    k_abs_positions = _positions_of_source_rows(ticks.sequence, k_abs_c["source_row"])

    contract_event_vol = vol[k_abs_positions]
    valid_vols = contract_event_vol[~np.isnan(contract_event_vol)].tolist()
    edges = compute_quintile_edges(valid_vols) if valid_vols else None

    # 3. Stratify K_ABS demand and build pools
    strata_demand: dict[tuple, list[int]] = {}
    k_abs_events: list[Event] = []
    events_by_session_phase: dict[tuple[str, int], list[Event]] = {}
    direction_by_pos: dict[int, int] = {}

    for i, row in k_abs_c.iterrows():
        pos = int(k_abs_positions[i])
        sess = str(sessions[pos])
        ph = coarse_phase(int(minutes[pos]))
        av = bool(after[pos] >= MAX_HORIZON_OBSERVATIONS)
        v_raw = vol[pos]
        v_bin = INSUFFICIENT_HISTORY if np.isnan(v_raw) else local_volatility_bin(float(v_raw), edges)
        s_key = stratum_key(contract, sess, ph, av, v_bin)

        strata_demand.setdefault(s_key, []).append(pos)
        direction = int(row["direction"])
        direction_by_pos[pos] = direction

        ev = Event(
            key=str(row.get("event_key", f"{contract}_{sess}_{pos}")),
            arm="K_ABS",
            contract=contract,
            session=sess,
            direction=direction,
            signal_idx=pos,
            signal_ts_ns=int(ticks.ts_ns[pos]),
            signal_source_row=int(ticks.sequence[pos]),
            fill_idx=pos,
        )
        k_abs_events.append(ev)
        events_by_session_phase.setdefault((sess, ph), []).append(ev)

    # 4. Build candidate pools for N_RAND (per stratum) and shuffle (per session-phase),
    #    vectorized: the per-tick Python loop version is what OOM-killed Kaggle twice.
    candidate_pools, candidate_indices_by_session_phase = _build_stratum_pools(
        sessions, minutes, vol, after, contract, edges,
    )
    print(f"[{contract}] stratum pools built, {len(candidate_pools)} strata ({_time.monotonic() - _t0:.1f}s)", flush=True)

    # 5. Sample N_RAND: pairs (own_anchor, sampled_anchor), own excluded per draw;
    #    the anchor inherits the direction of the K_ABS event it replaces.
    nrand_pairs = sample_nrand_strata_indices(strata_demand, candidate_pools, seed=seed + 101)
    n_rand_events: list[Event] = []
    for own_pos, sampled_pos in nrand_pairs:
        sess = str(sessions[sampled_pos])
        n_rand_events.append(Event(
            key=f"NRAND_{contract}_{sess}_{sampled_pos}",
            arm="N_RAND",
            contract=contract,
            session=sess,
            direction=direction_by_pos[own_pos],
            signal_idx=sampled_pos,
            signal_ts_ns=int(ticks.ts_ns[sampled_pos]),
            signal_source_row=int(ticks.sequence[sampled_pos]),
            fill_idx=sampled_pos,
        ))

    # 6. K_ABS_SHUFFLE: permute anchor positions within (session, coarse_phase),
    #    preserving event count and direction.
    shuffle_events: list[Event] = []
    for (sess, ph), ev_list in events_by_session_phase.items():
        pool_sp = candidate_indices_by_session_phase.get((sess, ph), [])
        permuted_pos = permute_kabs_shuffle_indices(
            {ph: ev_list}, {ph: pool_sp}, seed=seed + 202 + ph
        )
        for ev_orig, p_pos in zip(ev_list, permuted_pos):
            shuffle_events.append(Event(
                key=f"SHUF_{ev_orig.key}",
                arm="K_ABS_SHUFFLE",
                contract=contract,
                session=sess,
                direction=ev_orig.direction,
                signal_idx=p_pos,
                signal_ts_ns=int(ticks.ts_ns[p_pos]),
                signal_source_row=int(ticks.sequence[p_pos]),
                fill_idx=p_pos,
            ))

    # 7. K_BT2 events from the staged coordinates artifact
    k_bt2_events: list[Event] = []
    k_bt2_positions = _positions_of_source_rows(ticks.sequence, k_bt2_coords["source_row"])
    for k, (_, row) in enumerate(k_bt2_coords.iterrows()):
        pos = int(k_bt2_positions[k])
        sess = str(sessions[pos])
        k_bt2_events.append(Event(
            key=f"BT2_{contract}_{sess}_{pos}",
            arm="K_BT2",
            contract=contract,
            session=sess,
            direction=int(row["direction"]),
            signal_idx=pos,
            signal_ts_ns=int(ticks.ts_ns[pos]),
            signal_source_row=int(row["source_row"]),
            fill_idx=pos,
        ))

    arms_events: dict[str, dict[str, list[Event]]] = {
        "K_ABS": {}, "N_RAND": {}, "K_BT2": {}, "K_ABS_SHUFFLE": {},
    }
    for ev in k_abs_events:
        arms_events["K_ABS"].setdefault(ev.session, []).append(ev)
    for ev in n_rand_events:
        arms_events["N_RAND"].setdefault(ev.session, []).append(ev)
    for ev in k_bt2_events:
        arms_events["K_BT2"].setdefault(ev.session, []).append(ev)
    for ev in shuffle_events:
        arms_events["K_ABS_SHUFFLE"].setdefault(ev.session, []).append(ev)

    # 8. Evaluate 16 cells. Exclusions are aggregated by (arm, cell, reason) with a
    #    capped sample: a full per-event-cell exclusion list over 152K events x 16
    #    cells would be a multi-GB JSON — counts + samples carry the same evidence.
    EXCLUSION_SAMPLE_CAP = 2000
    stats: list[SessionCellArmStat] = []
    exclusions: list[dict[str, Any]] = []
    exclusion_counts: dict[str, int] = {}
    unique_sessions = sorted(set(sessions))

    print(
        f"[{contract}] events ready: K_ABS={len(k_abs_events)} N_RAND={len(n_rand_events)} "
        f"K_BT2={len(k_bt2_events)} SHUFFLE={len(shuffle_events)}; starting 16-cell evaluation "
        f"({_time.monotonic() - _t0:.1f}s)", flush=True,
    )
    for horizon in HORIZONS_OBSERVATIONS:
        _th = _time.monotonic()
        cache = build_cell_cache(ticks.ts_ns, ticks.price_ticks, sessions, horizon_observations=horizon)
        print(f"[{contract}] horizon={horizon} cache built ({_time.monotonic() - _th:.1f}s)", flush=True)
        for barrier in BARRIERS_TICKS:
            for arm_name, session_map in arms_events.items():
                for sess in unique_sessions:
                    ev_list = session_map.get(sess, [])
                    if ev_list:
                        stat, excl = evaluate_session_cell_arm(
                            ev_list, ticks.price_ticks, cache,
                            contract=contract, session=sess, arm=arm_name,
                            barrier_ticks=barrier, horizon_observations=horizon,
                        )
                        stats.append(stat)
                        for e in excl:
                            ck = f"{arm_name}|{stat.cell_id}|{e['reason']}"
                            exclusion_counts[ck] = exclusion_counts.get(ck, 0) + 1
                            if len(exclusions) < EXCLUSION_SAMPLE_CAP:
                                exclusions.append(e)
            print(
                f"[{contract}] cell barrier={barrier} horizon={horizon} done, "
                f"{len(stats)} session-arm-cell rows so far ({_time.monotonic() - _t0:.1f}s)",
                flush=True,
            )

    contract_summary = {
        "contract": contract,
        "n_ticks": len(ticks.price_ticks),
        "n_sessions": len(unique_sessions),
        "n_k_abs_events": len(k_abs_events),
        "n_n_rand_events": len(n_rand_events),
        "n_k_bt2_events": len(k_bt2_events),
        "n_k_abs_shuffle_events": len(shuffle_events),
        "quintile_edges": edges,
        "exclusion_counts": exclusion_counts,
        "exclusion_sample_size": len(exclusions),
    }
    return stats, exclusions, contract_summary


def run_single_contract(
    *, spec_path: Path, event_store_path: Path, bt2_result_path: Path,
    bt2_coords_path: Path, data_dir: Path, contract: str, stats_out: Path,
    authorization_token: str, seed: int,
) -> dict[str, Any]:
    """Per-contract mode: the unit of work the Kaggle launcher parallelizes
    as subprocesses (KAGGLE_LAUNCHER_PARALLELISM_POLICY_V1)."""
    if authorization_token != EXECUTION_TOKEN:
        raise PermissionError(f"[FAIL_CLOSED] Invalid execution token")
    verify_frozen_inputs(spec_path, event_store_path, bt2_result_path)
    k_abs_df = load_k_abs_coords(event_store_path)
    k_bt2_df = load_k_bt2_coords(bt2_coords_path, contract)

    stub = contract.split(" ")[1]
    hits = [p for p in data_dir.rglob("*") if p.is_file() and stub in p.name and p.suffix in (".parquet", ".pq")]
    if not hits:
        raise FileNotFoundError(f"Missing tick parquet for {contract} in {data_dir}")
    tick_file = sorted(hits, key=lambda p: len(str(p)))[0]

    stats, exclusions, summary = run_contract_pipeline(
        contract, tick_file, k_abs_df, k_bt2_df, seed=seed,
    )
    payload = {
        "schema_version": "bt2a_nq_gate1_contract_stats_v1",
        "contract": contract,
        "seed": seed,
        "stats": [asdict(s) for s in stats],
        "exclusions": exclusions,
        "contract_summary": summary,
        "spec_sha256": sha256_file(spec_path),
        "event_store_manifest_sha256": sha256_file(event_store_path),
        "bt2_v2_result_sha256": sha256_file(bt2_result_path),
        "bt2_coords_sha256": sha256_file(bt2_coords_path),
    }
    atomic_write_json(stats_out, payload)
    print(f"[{contract}] stats written to {stats_out} ({len(stats)} stats rows)", flush=True)
    return payload


def run_aggregate(
    *, spec_path: Path, stats_dir: Path, output_dir: Path,
    authorization_token: str, replications: int, seed: int,
    input_hashes: Dict[str, str],
) -> dict[str, Any]:
    """Aggregate the per-contract stats into the 16-cell Holm family and decision."""
    if authorization_token != EXECUTION_TOKEN:
        raise PermissionError(f"[FAIL_CLOSED] Invalid execution token")
    verify_input_artifact(spec_path, FROZEN_SPEC_SHA256, "spec")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    t_start = datetime.now(timezone.utc)
    all_stats: list[SessionCellArmStat] = []
    all_exclusions: list[dict[str, Any]] = []
    contract_summaries: list[dict[str, Any]] = []
    for contract in CONTRACTS:
        stats_path = stats_dir / f"bt2a_nq_gate1_stats_{contract.replace(' ', '_')}.json"
        if not stats_path.is_file():
            raise FileNotFoundError(f"[FAIL_CLOSED] missing per-contract stats: {stats_path}")
        payload = json.loads(stats_path.read_text(encoding="utf-8"))
        if payload.get("spec_sha256") != FROZEN_SPEC_SHA256:
            raise RuntimeError(f"[FAIL_CLOSED] stats for {contract} were computed against a different spec")
        for row in payload["stats"]:
            all_stats.append(SessionCellArmStat(**row))
        all_exclusions.extend(payload["exclusions"])  # capped samples, not the full list
        contract_summaries.append(payload["contract_summary"])

    family_results = aggregate_full_family_contrasts(all_stats, replications=replications, seed=seed)

    # Coverage: sessions eligible in BOTH arms of the primary contrast, per cell;
    # take the minimum across cells (fail-closed: the worst cell governs).
    primary_cells = family_results["primary_contrast"]["cells"]
    eligible_both = [int(c["n_sessions_eligible_both_arms"]) for c in primary_cells.values()]
    eff_available = min(eligible_both) if eligible_both else 0
    eff_required = int(spec["power_design"]["effective_sessions_required"])

    decision = decide_gate1_outcome(
        family_results["primary_contrast"],
        effective_sessions_available=eff_available,
        effective_sessions_required=eff_required,
    )

    t_end = datetime.now(timezone.utc)
    output_report = {
        "schema_version": "bt2a_nq_gate1_result_v1",
        "status": "GATE1_EXECUTION_COMPLETED",
        "decision": decision["decision"],
        "decision_details": decision,
        "primary_family_holm": family_results["primary_contrast"],
        "secondary_contrasts": family_results["secondary_contrasts"],
        "coverage": {
            "sessions_total_preholdout": 234,
            "effective_sessions_available_min_over_cells": eff_available,
            "effective_sessions_required": eff_required,
            "sufficient_power": eff_available >= eff_required,
        },
        "contract_summaries": contract_summaries,
        "n_exclusions_total": sum(
            sum(cs.get("exclusion_counts", {}).values()) for cs in contract_summaries
        ),
        "n_exclusions_sampled": len(all_exclusions),
        "execution_metadata": {
            "execution_token": authorization_token,
            "started_utc": t_start.isoformat(),
            "ended_utc": t_end.isoformat(),
            "duration_seconds": round((t_end - t_start).total_seconds(), 2),
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
        "result_payload_sha256": canonical_sha256(output_report),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **input_hashes,
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
    parser.add_argument("--bt2-coords", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--stats-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--contract", type=str)
    parser.add_argument("--aggregate", action="store_true")
    parser.add_argument("--authorization", type=str, required=True)
    parser.add_argument("--replications", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260831)
    args = parser.parse_args(argv)

    try:
        if args.aggregate:
            if args.stats_dir is None or args.output_dir is None:
                raise SystemExit("--aggregate requires --stats-dir and --output-dir")
            res = run_aggregate(
                spec_path=args.spec, stats_dir=args.stats_dir, output_dir=args.output_dir,
                authorization_token=args.authorization,
                replications=args.replications, seed=args.seed,
                input_hashes={},
            )
            print(f"\n=== GATE 1 OUTCOME DECISION ===")
            print(f"Decision: {res['decision']}")
            print(f"Reason:   {res['decision_details']['reason']}")
            return 0
        if not args.contract:
            raise SystemExit("per-contract mode requires --contract (or use --aggregate)")
        if args.bt2_coords is None or args.data_dir is None or args.stats_dir is None:
            raise SystemExit("per-contract mode requires --bt2-coords, --data-dir and --stats-dir")
        stats_out = args.stats_dir / f"bt2a_nq_gate1_stats_{args.contract.replace(' ', '_')}.json"
        run_single_contract(
            spec_path=args.spec, event_store_path=args.event_store,
            bt2_result_path=args.bt2_result, bt2_coords_path=args.bt2_coords,
            data_dir=args.data_dir, contract=args.contract, stats_out=stats_out,
            authorization_token=args.authorization, seed=args.seed,
        )
        return 0
    except Exception as e:
        print(f"\n[FATAL ERROR] Pipeline aborted: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
