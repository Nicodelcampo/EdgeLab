#!/usr/bin/env python3
"""Kaggle entrypoint: T2 N_RAND stratum capacity check for BT2A NQ Gate 1.

Target-free: reads creation-only coordinates (K_ABS events) and raw
pre-holdout ticks strictly to compute pre-anchor session/volatility
statistics (coarse_phase, availability, local_volatility_bin) and stratum
capacity, per the D6 definitions ratified by Nico (corrigendum: 4-hour
blocks, commit cb84424 on research/bt2a-nq-gate1-power-closure-20260830).
No outcome, no future price path, no first-passage, no P&L anywhere in this
script -- only creation-time coordinates and ticks strictly before each
anchor.
"""
from __future__ import annotations

import glob
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
FULL_COMMIT = "23a5ee41f3f168a75860df1fe66faaeb9e21a900" # will be replaced before commit
TEMP_REPO_DIR = Path("/tmp/EdgeLab")
OUTPUT_DIR = Path("/kaggle/working/edgelab-output")
WORKING_DIR = Path("/kaggle/working")

CONTRACTS = ["NQ 03-26", "NQ 06-26", "NQ 09-25", "NQ 09-26", "NQ 12-25"]
PRE_ANCHOR_VOLATILITY_WINDOW = 500
MAX_HORIZON_OBSERVATIONS = 250


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=True, **kw)


def find_dataset_dir(name_fragment: str) -> Path:
    search_roots = [Path("/kaggle/input"), Path("/kaggle/input/datasets"), Path(".")]
    print(f"Searching for dataset matching '{name_fragment}' in {[str(r) for r in search_roots if r.is_dir()]}", flush=True)
    for root in search_roots:
        if root.is_dir():
            hits = [p for p in root.rglob("*") if p.is_dir() and name_fragment in p.name]
            if hits:
                hits.sort(key=lambda p: len(p.parts))
                print(f"-> found '{name_fragment}' at: {hits[0]}", flush=True)
                return hits[0]
    for root in search_roots:
        if root.is_dir():
            candidate = root / name_fragment
            if candidate.is_dir():
                print(f"-> found '{name_fragment}' at: {candidate}", flush=True)
                return candidate
    raise SystemExit(f"no dataset directory matching '{name_fragment}' found under /kaggle/input")


def contract_to_glob_stub(contract: str) -> str:
    return contract.split(" ")[1]


def find_tick_file(ticks_dir: Path, contract: str) -> Path:
    stub = contract_to_glob_stub(contract)
    hits = [p for p in ticks_dir.rglob("*") if p.is_file() and stub in p.name and p.suffix in (".parquet", ".pq")]
    if not hits:
        raise SystemExit(f"no tick parquet found for {contract} (stub={stub}) under {ticks_dir}")
    if len(hits) > 1:
        print(f"multiple tick files for {contract}: {hits}, selecting shortest path")
        hits.sort(key=lambda p: len(str(p)))
    return hits[0]


def find_coord_file(coords_dir: Path, contract: str) -> Path:
    stub = contract_to_glob_stub(contract)
    hits = [p for p in coords_dir.rglob("*.parquet") if stub in p.name and "manifest" not in p.name]
    if not hits:
        raise SystemExit(f"expected coordinate parquet for {contract} (stub={stub}) in {coords_dir}")
    if len(hits) > 1:
        print(f"multiple coord files for {contract}: {hits}, selecting shortest path")
        hits.sort(key=lambda p: len(str(p)))
    return hits[0]


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
        med = s.rolling(window=500, min_periods=500).median().shift(1)
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


def main() -> None:
    t_start = datetime.now(timezone.utc)
    print(f"=== BT2A NQ N_RAND CAPACITY CHECK T2 ===", flush=True)
    print(f"Started at: {t_start.isoformat()}", flush=True)

    # 1. Clone EdgeLab to /tmp/EdgeLab
    if TEMP_REPO_DIR.exists():
        shutil.rmtree(TEMP_REPO_DIR)
    run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(TEMP_REPO_DIR)])
    run(["git", "fetch", "origin", FULL_COMMIT, "--depth", "200"], cwd=TEMP_REPO_DIR)
    run(["git", "checkout", "--detach", FULL_COMMIT], cwd=TEMP_REPO_DIR)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TEMP_REPO_DIR, text=True).strip()
    print("repo_commit=", actual, flush=True)
    if actual != FULL_COMMIT:
        raise SystemExit(f"checked-out commit differs: {actual} != {FULL_COMMIT}")

    sys.path.insert(0, str(TEMP_REPO_DIR))
    from edgelab.research.bt2a_nq_gate1_nrand_capacity import (
        INSUFFICIENT_HISTORY,
        availability_flag,
        capacity_report,
        coarse_phase,
        compute_quintile_edges,
        local_volatility_bin,
        stratum_key,
    )
    from edgelab.bridge.ticks import load_canonical_parquet

    # 2. Locate datasets
    coords_dir = find_dataset_dir("coordinates")
    ticks_dir = find_dataset_dir("edgelab-ticks-nq-preholdout")
    print("coords_dir=", coords_dir, flush=True)
    print("ticks_dir=", ticks_dir, flush=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_event_vol_by_contract: dict[str, list[float]] = {c: [] for c in CONTRACTS}
    per_contract_frames = {}
    cached_ticks_data: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}

    print("\n=== STEP 1: LOAD COORDINATES AND PRE-ANCHOR TICKS ===", flush=True)
    for contract in CONTRACTS:
        coord_path = find_coord_file(coords_dir, contract)
        print(f"Loading coordinates for {contract} from {coord_path}", flush=True)
        coords = pd.read_parquet(coord_path)
        coords = coords[coords["contract"] == contract].reset_index(drop=True)

        tick_path = find_tick_file(ticks_dir, contract)
        print(f"Loading ticks for {contract} from {tick_path}", flush=True)
        ticks = load_canonical_parquet(tick_path, contract=contract, instrument="NQ")

        sessions = cme_session_dates(ticks.ts_ns)
        minutes = chicago_minutes_since_1700(ticks.ts_ns)
        vol = rolling_median_abs_delta_pre_anchor(ticks.price_ticks, sessions)
        after = rows_after_in_session(sessions)
        cached_ticks_data[contract] = (sessions, minutes, vol, after)

        row_by_source_row = {int(r): i for i, r in enumerate(ticks.sequence)}
        anchor_positions = []
        for source_row in coords["source_row"].to_numpy():
            pos = row_by_source_row.get(int(source_row))
            if pos is None:
                raise SystemExit(f"coordinate source_row {source_row} not found in tick sequence for {contract}")
            anchor_positions.append(pos)
        anchor_positions = np.asarray(anchor_positions, dtype=np.int64)

        coords["session_from_ticks"] = sessions[anchor_positions]
        mismatched = (coords["session_from_ticks"].to_numpy() != coords["cme_session_id"].to_numpy()).sum()
        if mismatched:
            raise SystemExit(f"{mismatched} events in {contract} have session mismatch between coordinates and ticks")

        coords["chicago_minutes_since_1700"] = minutes[anchor_positions]
        coords["rows_after_in_session"] = after[anchor_positions]
        coords["local_vol_raw"] = vol[anchor_positions]
        coords["coarse_phase"] = [coarse_phase(int(m)) for m in coords["chicago_minutes_since_1700"]]
        coords["available"] = [availability_flag(int(r)) for r in coords["rows_after_in_session"]]

        all_event_vol_by_contract[contract] = coords.loc[
            coords["local_vol_raw"].notna(), "local_vol_raw"
        ].tolist()
        per_contract_frames[contract] = coords

        print(f"{contract}: {len(coords)} events, "
              f"{coords['local_vol_raw'].isna().sum()} insufficient-history, "
              f"{(~coords['available']).sum()} unavailable", flush=True)

    print("\n=== STEP 2: COMPUTE QUINTILE EDGES PER CONTRACT ===", flush=True)
    quintile_edges_by_contract = {
        c: compute_quintile_edges(vals) if vals else None
        for c, vals in all_event_vol_by_contract.items()
    }
    for c, edges in quintile_edges_by_contract.items():
        print(f"{c}: quintile_edges={edges}", flush=True)

    print("\n=== STEP 3: ASSIGN STRATA KEYS TO K_ABS EVENTS (DEMAND) ===", flush=True)
    demand_keys: list[tuple] = []
    for contract, coords in per_contract_frames.items():
        edges = quintile_edges_by_contract[contract]
        for _, row in coords.iterrows():
            if pd.isna(row["local_vol_raw"]):
                vol_bin = INSUFFICIENT_HISTORY
            else:
                vol_bin = local_volatility_bin(float(row["local_vol_raw"]), edges)
            key = stratum_key(
                contract, str(row["cme_session_id"]), int(row["coarse_phase"]),
                bool(row["available"]), vol_bin,
            )
            demand_keys.append(key)

    print(f"Total K_ABS events classified: {len(demand_keys)}", flush=True)

    print("\n=== STEP 4: COMPUTE CANDIDATE POOL SIZES ACROSS ALL TICKS ===", flush=True)
    pool_sizes: dict[tuple, int] = {}
    for contract in CONTRACTS:
        print(f"Building candidate pool for {contract}...", flush=True)
        sessions, minutes, vol, after = cached_ticks_data[contract]
        edges = quintile_edges_by_contract[contract]

        phases = np.array([coarse_phase(int(m)) for m in minutes], dtype=np.int32)
        available = after >= MAX_HORIZON_OBSERVATIONS
        vol_bins = np.empty(len(vol), dtype=object)
        nan_mask = np.isnan(vol)
        vol_bins[nan_mask] = INSUFFICIENT_HISTORY
        if edges is not None:
            valid_indices = np.flatnonzero(~nan_mask)
            bin_indices = np.searchsorted(edges, vol[valid_indices], side="left")
            for idx, b in zip(valid_indices, bin_indices):
                vol_bins[idx] = int(b)

        df = pd.DataFrame({
            "sess": sessions,
            "ph": phases,
            "av": available,
            "vb": vol_bins
        })
        counts = df.groupby(["sess", "ph", "av", "vb"], observed=False).size()
        for (sess, ph, av, vb), count in counts.items():
            key = stratum_key(contract, str(sess), int(ph), bool(av), vb)
            pool_sizes[key] = pool_sizes.get(key, 0) + int(count)

    print(f"Total unique candidate strata in pool: {len(pool_sizes)}", flush=True)

    print("\n=== STEP 5: RUN CAPACITY REPORT ===", flush=True)
    report = capacity_report(demand_keys, pool_sizes)
    t_end = datetime.now(timezone.utc)
    duration_sec = (t_end - t_start).total_seconds()

    report["contracts"] = CONTRACTS
    report["n_events_total"] = len(demand_keys)
    report["quintile_edges_by_contract"] = quintile_edges_by_contract
    report["frozen_commit"] = FULL_COMMIT
    report["coarse_phase_hours"] = 4
    report["max_horizon_observations"] = MAX_HORIZON_OBSERVATIONS
    report["pre_anchor_volatility_window"] = PRE_ANCHOR_VOLATILITY_WINDOW
    report["execution_metadata"] = {
        "started_utc": t_start.isoformat(),
        "ended_utc": t_end.isoformat(),
        "duration_seconds": round(duration_sec, 2),
        "target_free": True,
        "outcomes_accessed": False,
        "future_prices_accessed": False,
        "pnl_accessed": False,
        "holdout_touched": False,
    }

    print(f"\n================ SUMMARY REPORT ================", flush=True)
    print(json.dumps(
        {k: v for k, v in report.items() if k != "strata"},
        indent=2, default=str,
    ), flush=True)

    report_json_str = json.dumps(report, indent=2, sort_keys=True, default=str) + "\n"
    out_file_1 = OUTPUT_DIR / "bt2a_nq_gate1_nrand_capacity_report.json"
    out_file_2 = WORKING_DIR / "bt2a_nq_gate1_nrand_capacity_report.json"
    out_file_1.write_text(report_json_str, encoding="utf-8")
    out_file_2.write_text(report_json_str, encoding="utf-8")
    print(f"\nReport written to {out_file_1} and {out_file_2}", flush=True)

    print(f"\n================ FULL JSON REPORT ================", flush=True)
    print(report_json_str, flush=True)
    print(f"================ END FULL JSON ================", flush=True)


if __name__ == "__main__":
    main()
