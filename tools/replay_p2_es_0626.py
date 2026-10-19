# -*- coding: utf-8 -*-
"""P2 Parity Replay for ES 06-26 aVolClusterPOI v0.5."""

from datetime import datetime, timedelta
import math
import csv
from pathlib import Path
import sys

import numpy as np
import pandas as pd

REPO_PATH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_PATH))

from edgelab.bridge.ticks import load_canonical_parquet
from edgelab.bridge.bars import build_time_bars, build_footprints, p1a_gate, session_ids
from edgelab.bridge.indicators.avolclusterpoi import (
    SessionProfile,
    detect_block,
    RESEARCH_DEFAULTS,
    NS,
)

TZ = "America/Chicago"
ORACLE_TZ = "America/Argentina/Buenos_Aires"

PARQUET_FILE = Path(r"E:\EdgeLab\data\nt8\ES_parquet\ES_06-26_ticks.parquet")
ORACLE_CSV = REPO_PATH / "data" / "nt8_oracles" / "avolcluster_v05_ES_0626.csv"

def art_to_chicago(dt: datetime) -> datetime:
    ts = pd.Timestamp(dt)
    if ts.tz is None:
        ts = ts.tz_localize(ORACLE_TZ)
    return ts.tz_convert(TZ).to_pydatetime().replace(tzinfo=None)

def parse_oracle(csv_path: Path):
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    header_i = next((i for i, line in enumerate(lines) if "event_type" in line and "lower_tick" in line), None)
    zones = []
    for row in csv.DictReader(lines[header_i:], delimiter=","):
        if row.get("event_type") != "ZONE_CREATED":
            continue
        dt_raw = row["bar_close_time"].strip()
        dt = datetime.fromisoformat(dt_raw)
        dt_ct = art_to_chicago(dt)
        dir_val = 1 if row["direction"] == "LONG" else (-1 if row["direction"] == "SHORT" else 0)
        zones.append({
            "event_seq": int(row["event_seq"]),
            "zone_id": int(row["zone_id"]),
            "time_art": dt,
            "time_ct": dt_ct,
            "lower_tick": int(row["lower_tick"]),
            "upper_tick": int(row["upper_tick"]),
            "direction": dir_val,
            "reason": row.get("reason", "OFF_PRICE"),
        })
    return zones

def run_p2():
    print(f"Loading parquet: {PARQUET_FILE}...")
    ticks = load_canonical_parquet(PARQUET_FILE, instrument="ES")
    print(f"Loaded {len(ticks.ts_utc_ns):,} ticks. Building 1-min bars...")
    
    bars = build_time_bars(ticks, minutes=1)
    print(f"Built {len(bars.close_t):,} bars. Building footprints...")
    fps = build_footprints(ticks, bars)
    
    p1a = p1a_gate(bars, fps)
    print(f"P1A Gate status: {p1a}")
    
    sess_ids = session_ids(bars.close_time_ns, tz=TZ)
    unique_sessions = np.unique(sess_ids)
    print(f"Total sessions in parquet: {len(unique_sessions)}")
    
    oracle_zones = parse_oracle(ORACLE_CSV)
    print(f"Total ZONE_CREATED in NT8 oracle: {len(oracle_zones)}")
    
    # Run Python kernel
    py_zones = []
    profile = SessionProfile(
        window_bars=RESEARCH_DEFAULTS["window_bars"],
        time_bucket_minutes=RESEARCH_DEFAULTS["time_bucket_minutes"],
        lookback_sessions=RESEARCH_DEFAULTS["lookback_sessions"],
        min_samples_per_bucket=RESEARCH_DEFAULTS["min_samples_per_bucket"],
        detection_percentile=RESEARCH_DEFAULTS["detection_percentile"],
        median_multiplier=RESEARCH_DEFAULTS["median_multiplier"],
        max_gap_ticks=RESEARCH_DEFAULTS["max_gap_ticks"],
        min_cluster_ticks=RESEARCH_DEFAULTS["min_cluster_ticks"],
    )
    
    n_bars = len(bars.close_t)
    wb = RESEARCH_DEFAULTS["window_bars"]
    
    for s_id in unique_sessions:
        s_mask = np.where(sess_ids == s_id)[0]
        if len(s_mask) == 0:
            continue
        s_begin_ns = bars.close_time_ns[s_mask[0]] - 60 * NS
        profile.on_session_begin(s_begin_ns)
        
        n_blocks = len(s_mask) // wb
        for b_idx in range(n_blocks):
            block_indices = s_mask[b_idx * wb : (b_idx + 1) * wb]
            block_fp = [fps.raw[i] for i in block_indices]
            block_end_ns = bars.close_time_ns[block_indices[-1]]
            bar_close_tick = bars.close_t[block_indices[-1]]
            
            res = detect_block(block_fp, block_end_ns, bar_close_tick, s_begin_ns, profile)
            if res and res.get("kind") == "OFF_PRICE":
                close_dt = pd.Timestamp(block_end_ns, unit="ns", tz="UTC").tz_convert(TZ).to_pydatetime().replace(tzinfo=None)
                py_zones.append({
                    "time_ct": close_dt,
                    "lower_tick": res["lower_tick"],
                    "upper_tick": res["upper_tick"],
                    "direction": res["direction"],
                })
        profile.on_session_end()
        
    print(f"Total Python OFF_PRICE zones emitted: {len(py_zones)}")
    
    # Match against oracle in the active comparison window
    # Compare between 2026-04-12 and 2026-06-08
    py_df = pd.DataFrame(py_zones)
    or_df = pd.DataFrame(oracle_zones)
    
    print("\n--- Bipartite Matching (Python vs Oracle) ---")
    matched = 0
    unmatched_oracle = []
    unmatched_py = set(range(len(py_zones)))
    
    for idx_or, o in enumerate(oracle_zones):
        t_or = o["time_ct"]
        lo_or = o["lower_tick"]
        hi_or = o["upper_tick"]
        
        found = False
        for idx_py, p in enumerate(py_zones):
            if idx_py not in unmatched_py:
                continue
            dt_sec = abs((p["time_ct"] - t_or).total_seconds())
            if dt_sec <= 60 and p["lower_tick"] == lo_or and p["upper_tick"] == hi_or:
                matched += 1
                unmatched_py.remove(idx_py)
                found = True
                break
        if not found:
            unmatched_oracle.append(o)
            
    print(f"MATCHED: {matched} / {len(oracle_zones)} ({matched / len(oracle_zones) * 100:.1f}%)")
    print(f"Unmatched in Oracle: {len(unmatched_oracle)}")
    print(f"Unmatched in Python: {len(unmatched_py)}")
    
    if unmatched_oracle:
        print("\nFirst 5 unmatched Oracle zones:")
        for u in unmatched_oracle[:5]:
            print("  Oracle:", u["time_ct"], f"[{u['lower_tick']}, {u['upper_tick']}]", "dir:", u["direction"])
            
    if unmatched_py:
        print("\nFirst 5 unmatched Python zones:")
        for u_idx in list(unmatched_py)[:5]:
            p = py_zones[u_idx]
            print("  Python:", p["time_ct"], f"[{p['lower_tick']}, {p['upper_tick']}]", "dir:", p["direction"])

if __name__ == "__main__":
    run_p2()
