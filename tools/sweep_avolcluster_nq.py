# -*- coding: utf-8 -*-
"""Target-Free Sweep and Calibration Runner for aVolClusterPOI on NQ.

Maps parameter sensitivity across the 234 CME sessions of NQ (5 contracts:
NQ 09-25, NQ 12-25, NQ 03-26, NQ 06-26, NQ 09-26) to find the optimal
structural configuration for NQ without opening outcomes.

Evaluates:
- Event density per session (target: 2-6 zones/session)
- Session coverage (target: >= 80% of sessions)
- Cluster width distribution in ticks (target: 4-16 ticks / 1-4 pts)
- OFF_PRICE vs AT_PRICE ratio

Memory-safe: processes sequentially with explicit garbage collection and
persistent SessionProfile across contracts.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import load_canonical_parquet
from edgelab.bridge.bars import build_time_bars, build_footprints
from edgelab.bridge.indicators.avolclusterpoi import (
    RESEARCH_DEFAULTS,
    SessionProfile,
    detect_block,
)


def cme_session_dates(ts_ns: np.ndarray) -> np.ndarray:
    sec = ts_ns // 1_000_000_000
    dt = pd.to_datetime(sec, unit="s", utc=True).tz_convert("America/Chicago")
    is_after_17 = dt.hour >= 17
    trade_dt = dt + pd.to_timedelta(np.where(is_after_17, 1, 0), unit="D")
    return trade_dt.strftime("%Y%m%d").to_numpy()


def run_avol_for_contract(
    pq_path: Path,
    contract: str,
    valid_sessions: set[str],
    grid_configs: list[dict[str, Any]],
    profiles: dict[str, SessionProfile],
) -> dict[str, list[dict[str, Any]]]:
    """Run multiple aVolClusterPOI configs on a single contract using persistent profiles."""
    print(f"\n[{contract}] Loading ticks: {pq_path.name}...")
    ticks = load_canonical_parquet(pq_path, contract=contract, instrument="NQ")
    
    print(f"[{contract}] Building 1-minute time bars...")
    bars1m = build_time_bars(ticks, 1)
    
    print(f"[{contract}] Building 1-minute footprints...")
    fps1m = build_footprints(ticks, bars1m)
    
    # We no longer need full tick arrays in RAM during block processing
    del ticks
    gc.collect()

    ses_ids = cme_session_dates(bars1m.end_ns)
    # Sort unique sessions chronologically
    unique_sessions = [s for s in sorted(np.unique(ses_ids)) if s in valid_sessions]
    print(f"[{contract}] Processing {len(unique_sessions)} valid sessions across {len(grid_configs)} configs...")

    contract_events: dict[str, list[dict[str, Any]]] = {cfg["cfg_id"]: [] for cfg in grid_configs}

    # Group bar indices by session once
    session_bar_indices = {s: np.flatnonzero(ses_ids == s) for s in unique_sessions}

    for cfg in grid_configs:
        cfg_id = cfg["cfg_id"]
        w_bars = cfg["window_bars"]
        prof = profiles[cfg_id]
        
        for s_id in unique_sessions:
            b_idx = session_bar_indices[s_id]
            if len(b_idx) < w_bars:
                prof.commit()
                continue
                
            s_start_ns = bars1m.start_ns[b_idx[0]]
            n_blocks = len(b_idx) // w_bars
            
            for blk in range(n_blocks):
                blk_b = b_idx[blk * w_bars : (blk + 1) * w_bars]
                cells: dict[int, float] = {}
                for b in blk_b:
                    for p, v in fps1m.total[b].items():
                        cells[int(p)] = cells.get(int(p), 0.0) + float(v)
                        
                min_from_open = (bars1m.end_ns[blk_b[-1]] - s_start_ns) // (60 * 1_000_000_000)
                bucket = min(int(min_from_open // 30), 45)
                
                out = detect_block(
                    cells,
                    prof.history_scores(bucket),
                    close_tick=int(bars1m.close_t[blk_b[-1]]),
                    params=cfg,
                )
                prof.add_block(bucket, out["best_score"])
                
                for z in out.get("zones", []):
                    width_t = int(z["upper_tick"] - z["lower_tick"] + 1)
                    contract_events[cfg_id].append({
                        "contract": contract,
                        "session_id": s_id,
                        "bar_time_ns": int(bars1m.end_ns[blk_b[-1]]),
                        "kind": z.get("kind", "OFF_PRICE"),
                        "direction": z.get("direction", 0),
                        "lower_tick": int(z["lower_tick"]),
                        "upper_tick": int(z["upper_tick"]),
                        "width_ticks": width_t,
                        "score": float(z["score"]),
                        "threshold": float(z["threshold"]) if z.get("threshold") else None,
                    })
            
            # Commit session to history at end of every CME session
            prof.commit()

    del bars1m, fps1m, session_bar_indices
    gc.collect()
    return contract_events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(r"E:\EdgeLab\data\nt8\NQ_parquet"))
    parser.add_argument("--session-registry", type=Path, default=Path(r"specs/bt2a_gate1_nq_all5_sessions_2026-08-27.json"))
    parser.add_argument("--output-json", type=Path, default=Path(r"docs/research/avolcluster_nq_sweep_result.json"))
    args = parser.parse_args()

    sess_reg = json.loads(args.session_registry.read_text(encoding="utf-8"))
    contracts = sess_reg["selection"]["contracts"]
    
    # Expand sessions
    from tools.build_event_store_all5_v2 import expand_sessions
    expanded = expand_sessions(sess_reg)
    sessions_by_contract: dict[str, set[str]] = {}
    for row in expanded:
        sessions_by_contract.setdefault(row["contract"], set()).add(row["cme_session_id"])
    total_valid_sessions = sum(len(v) for v in sessions_by_contract.values())

    print(f"=== aVolClusterPOI Target-Free Sweep on NQ ===")
    print(f"Contracts: {contracts}")
    print(f"Total Valid CME Sessions: {total_valid_sessions}")

    # Build Grid Configurations for NQ
    grid_configs = []
    
    window_bars_opts = [5, 10, 15]
    median_mult_opts = [1.5, 2.0, 2.5]
    min_cluster_opts = [4, 8, 12]
    pct_opts = [95.0, 97.5, 98.0]

    for wb in window_bars_opts:
        for mm in median_mult_opts:
            for mc in min_cluster_opts:
                for pct in pct_opts:
                    cid = f"CFG_W{wb}_M{int(mm*10)}_C{mc}_P{int(pct*10)}"
                    grid_configs.append({
                        "cfg_id": cid,
                        "window_bars": wb,
                        "median_multiplier": mm,
                        "max_gap_ticks": 1,
                        "min_cluster_ticks": mc,
                        "time_bucket_minutes": 30,
                        "lookback_sessions": 20,
                        "detection_percentile": pct,
                        "min_samples_per_bucket": 15,
                        "one_cluster_per_block": True,
                    })

    print(f"Total candidate configurations in grid: {len(grid_configs)}")

    # Initialize persistent session profiles for each configuration across all 5 contracts
    profiles = {cfg["cfg_id"]: SessionProfile(lookback_sessions=cfg["lookback_sessions"]) for cfg in grid_configs}
    all_results: dict[str, list[dict[str, Any]]] = {cfg["cfg_id"]: [] for cfg in grid_configs}

    t0 = time.time()
    for contract in contracts:
        pq_name = f"{contract.replace(' ', '_')}_ticks.parquet"
        pq_path = args.data_dir / pq_name
        if not pq_path.is_file():
            print(f"WARNING: Missing parquet {pq_path}, skipping...")
            continue
            
        v_sess = sessions_by_contract.get(contract, set())
        c_events = run_avol_for_contract(pq_path, contract, v_sess, grid_configs, profiles)
        
        for cid, evts in c_events.items():
            all_results[cid].extend(evts)
            
        gc.collect()

    elapsed = time.time() - t0
    print(f"\nProcessing complete in {elapsed/60:.1f} minutes. Compiling structural census...")

    # Analyze & Rank Configurations
    summary_table = []
    for cfg in grid_configs:
        cid = cfg["cfg_id"]
        evts = all_results[cid]
        off_evts = [e for e in evts if e["kind"] == "OFF_PRICE"]
        at_evts = [e for e in evts if e["kind"] == "AT_PRICE"]
        
        sessions_with_off = len(set(e["session_id"] for e in off_evts))
        coverage_pct = (sessions_with_off / total_valid_sessions * 100.0) if total_valid_sessions > 0 else 0.0
        
        dens_per_session = len(off_evts) / total_valid_sessions if total_valid_sessions > 0 else 0.0
        widths = [e["width_ticks"] for e in off_evts]
        
        mean_width = float(np.mean(widths)) if widths else 0.0
        p95_width = float(np.percentile(widths, 95)) if widths else 0.0
        
        # Scoring fitness: ideal density ~ 2-6 zones/session, coverage >= 80%, mean width in [6, 16] ticks
        density_score = max(0.0, 1.0 - min(abs(dens_per_session - 3.5) / 3.5, 1.0))
        coverage_score = min(coverage_pct / 80.0, 1.0)
        width_score = 1.0 if 4.0 <= mean_width <= 16.0 else max(0.0, 1.0 - abs(mean_width - 10.0) / 10.0)
        
        composite_score = round(0.4 * coverage_score + 0.3 * density_score + 0.3 * width_score, 4)
        
        summary_table.append({
            "cfg_id": cid,
            "params": {
                "window_bars": cfg["window_bars"],
                "median_multiplier": cfg["median_multiplier"],
                "min_cluster_ticks": cfg["min_cluster_ticks"],
                "detection_percentile": cfg["detection_percentile"],
            },
            "total_off_price": len(off_evts),
            "total_at_price": len(at_evts),
            "off_to_at_ratio": round(len(off_evts) / max(1, len(at_evts)), 2) if at_evts else 0.0,
            "sessions_with_events": sessions_with_off,
            "session_coverage_pct": round(coverage_pct, 1),
            "zones_per_session_mean": round(dens_per_session, 2),
            "width_ticks_mean": round(mean_width, 1),
            "width_ticks_p95": round(p95_width, 1),
            "fitness_score": composite_score,
        })

    summary_table.sort(key=lambda x: x["fitness_score"], reverse=True)

    out_payload = {
        "schema": "avolcluster_nq_sweep_v1",
        "instrument": "NQ",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "total_sessions": total_valid_sessions,
        "elapsed_seconds": round(elapsed, 1),
        "top_5_configurations": summary_table[:5],
        "all_configurations": summary_table,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out_payload, indent=2), encoding="utf-8")
    
    print(f"\n{'='*75}")
    print(f"SWEEP COMPLETE — Results written to: {args.output_json}")
    print(f"{'='*75}")
    print(f"{'Rank':<5} {'Config ID':<25} {'Total OFF':<10} {'Zones/Sess':<12} {'Coverage':<10} {'Mean Width':<12} {'Fitness':<8}")
    print(f"{'-'*75}")
    for i, row in enumerate(summary_table[:10], 1):
        print(f"{i:<5} {row['cfg_id']:<25} {row['total_off_price']:<10} {row['zones_per_session_mean']:<12} {row['session_coverage_pct']}%{'':<3} {row['width_ticks_mean']}t{'':<6} {row['fitness_score']:<8}")
    print(f"{'='*75}")


if __name__ == "__main__":
    main()
