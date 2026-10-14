# -*- coding: utf-8 -*-
"""Micro-Tick & Fast-Bar Sweep for BigTrap2 on NQ (Target-Free Bubble Mapping).

Evaluates BigTrap2 absorption bubbles across multiple tick bar resolutions:
- Tick Bars: 10t, 25t, 50t, 100t, 120t, 240t
- Time Bars: 1m
- Grid: Imbalance Ratios (2.5, 3.0, 3.5, 4.0), MinTrapVolume (10, 20, 50, 100)

Target-free execution strictly measuring bubble frequencies, sizes, and directional balance.
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
from edgelab.bridge.bars import build_time_bars, build_tick_bars, build_footprints
from edgelab.bridge.indicators.bigtrap2 import run as run_bigtrap2, DEFAULTS as BT2_DEFAULTS


def cme_session_dates(ts_ns: np.ndarray) -> np.ndarray:
    sec = ts_ns // 1_000_000_000
    dt = pd.to_datetime(sec, unit="s", utc=True).tz_convert("America/Chicago")
    is_after_17 = dt.hour >= 17
    trade_dt = dt + pd.to_timedelta(np.where(is_after_17, 1, 0), unit="D")
    return trade_dt.strftime("%Y%m%d").to_numpy()


def run_bigtrap2_for_contract(
    pq_path: Path,
    contract: str,
    valid_sessions: set[str],
    bar_series_types: dict[str, Any],
    grid_configs: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Run BigTrap2 grid on a single NQ contract across tick resolutions."""
    print(f"\n[{contract}] Loading ticks: {pq_path.name}...")
    ticks = load_canonical_parquet(pq_path, contract=contract, instrument="NQ")
    
    contract_events: dict[str, list[dict[str, Any]]] = {cfg["cfg_id"]: [] for cfg in grid_configs}

    for b_type, b_info in bar_series_types.items():
        type_configs = [c for c in grid_configs if c["bar_type"] == b_type]
        if not type_configs:
            continue
            
        print(f"[{contract}] Building {b_type} bars & footprints...")
        if b_info["kind"] == "time":
            bars = build_time_bars(ticks, b_info["param"])
        else:
            bars = build_tick_bars(ticks, b_info["param"], reiniciar_por_sesion=True)
            
        fps = build_footprints(ticks, bars)
        ses_ids = cme_session_dates(bars.end_ns)
        
        # Filter bars belonging to valid pre-holdout sessions
        valid_bar_mask = np.isin(ses_ids, list(valid_sessions))
        if not np.any(valid_bar_mask):
            continue

        print(f"[{contract}] [{b_type}] Running {len(type_configs)} BigTrap2 configs on {len(bars.close_t)} bars...")

        for cfg in type_configs:
            cfg_id = cfg["cfg_id"]
            imb = cfg["imbalance_ratio"]
            min_vol = cfg["min_trap_volume"]

            # Run BigTrap2 kernel
            cfg_params = {
                "imbalance_ratio": imb,
                "min_trap_volume": min_vol,
                "min_export_volume": min_vol,
                "use_wick_filter": False,
            }
            res = run_bigtrap2(ticks, bars, fps, params=cfg_params)

            # Record creation zones / bubbles
            for z in res.get("zones", []):
                b_idx = z["created_bar"]
                if 0 <= b_idx < len(ses_ids) and ses_ids[b_idx] in valid_sessions:
                    contract_events[cfg_id].append({
                        "contract": contract,
                        "session_id": ses_ids[b_idx],
                        "bar_time_ns": int(bars.end_ns[b_idx]),
                        "side": "B" if z["kind"] == "trapped_buyers" else "S",
                        "top": float(z["top"]),
                        "bottom": float(z["bottom"]),
                        "width_ticks": int(round((z["top"] - z["bottom"]) / ticks.tick_size)) + 1,
                        "bar_idx": int(b_idx),
                    })

        del bars, fps, ses_ids, valid_bar_mask
        gc.collect()

    del ticks
    gc.collect()
    return contract_events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(r"E:\EdgeLab\data\nt8\NQ_parquet"))
    parser.add_argument("--session-registry", type=Path, default=Path(r"specs/bt2a_gate1_nq_all5_sessions_2026-08-27.json"))
    parser.add_argument("--output-json", type=Path, default=Path(r"docs/research/bigtrap2_nq_tickframes_sweep_result.json"))
    args = parser.parse_args()

    sess_reg = json.loads(args.session_registry.read_text(encoding="utf-8"))
    contracts = sess_reg["selection"]["contracts"]
    
    from tools.build_event_store_all5_v2 import expand_sessions
    expanded = expand_sessions(sess_reg)
    sessions_by_contract: dict[str, set[str]] = {}
    for row in expanded:
        sessions_by_contract.setdefault(row["contract"], set()).add(row["cme_session_id"])
    total_valid_sessions = sum(len(v) for v in sessions_by_contract.values())

    print(f"=== BigTrap2 Micro-Tick & Fast-Bar Sweep on NQ ===")
    print(f"Contracts: {contracts}")
    print(f"Total CME Sessions: {total_valid_sessions}")

    bar_series_types = {
        "tick_10": {"kind": "tick", "param": 10},
        "tick_25": {"kind": "tick", "param": 25},
        "tick_50": {"kind": "tick", "param": 50},
        "tick_100": {"kind": "tick", "param": 100},
        "tick_120": {"kind": "tick", "param": 120},
        "tick_240": {"kind": "tick", "param": 240},
        "time_1m": {"kind": "time", "param": 1},
    }

    grid_configs = []
    for b_type in bar_series_types.keys():
        for imb in [2.5, 3.0, 3.5, 4.0]:
            for m_vol in [10, 20, 50, 100]:
                cid = f"{b_type}_IMB{int(imb*10)}_VOL{m_vol}"
                grid_configs.append({
                    "cfg_id": cid,
                    "bar_type": b_type,
                    "imbalance_ratio": imb,
                    "min_trap_volume": m_vol,
                })

    print(f"Total Configurations to Test: {len(grid_configs)}")

    all_events: dict[str, list[dict[str, Any]]] = {cfg["cfg_id"]: [] for cfg in grid_configs}
    start_all = time.time()

    for contract in contracts:
        pq_path = args.data_dir / f"{contract.replace(' ', '_')}_ticks.parquet"
        if not pq_path.exists():
            print(f"Warning: {pq_path} does not exist, skipping.")
            continue
            
        c_events = run_bigtrap2_for_contract(
            pq_path=pq_path,
            contract=contract,
            valid_sessions=sessions_by_contract.get(contract, set()),
            bar_series_types=bar_series_types,
            grid_configs=grid_configs,
        )
        for cfg_id, ev_list in c_events.items():
            all_events[cfg_id].extend(ev_list)

    elapsed_all = time.time() - start_all
    print(f"\n[Sweep Complete] Finished all {len(grid_configs)} configs in {elapsed_all:.1f}s.")

    # Summarize results
    results = []
    for cfg in grid_configs:
        cid = cfg["cfg_id"]
        evts = all_events[cid]
        n_ev = len(evts)
        ses_with_ev = len(set(e["session_id"] for e in evts))
        n_buy = sum(1 for e in evts if e["side"] == "B")
        n_sell = sum(1 for e in evts if e["side"] == "S")
        widths = [e["width_ticks"] for e in evts] if evts else [0]
        
        results.append({
            "cfg_id": cid,
            "bar_type": cfg["bar_type"],
            "imbalance_ratio": cfg["imbalance_ratio"],
            "min_trap_volume": cfg["min_trap_volume"],
            "total_events": n_ev,
            "sessions_with_events": ses_with_ev,
            "coverage_pct": round(ses_with_ev / total_valid_sessions * 100.0, 2) if total_valid_sessions else 0.0,
            "buy_events": n_buy,
            "sell_events": n_sell,
            "buy_ratio": round(n_buy / n_ev, 3) if n_ev else 0.0,
            "events_per_session": round(n_ev / total_valid_sessions, 2) if total_valid_sessions else 0.0,
            "mean_width_ticks": round(float(np.mean(widths)), 1),
            "median_width_ticks": round(float(np.median(widths)), 1),
            "p95_width_ticks": round(float(np.percentile(widths, 95)), 1) if evts else 0.0,
        })

    results.sort(key=lambda x: x["total_events"], reverse=True)

    summary_doc = {
        "schema_version": "bigtrap2_nq_tickframes_sweep_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "total_configs": len(grid_configs),
        "total_cme_sessions": total_valid_sessions,
        "elapsed_seconds": round(elapsed_all, 1),
        "results": results,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary_doc, indent=2), encoding="utf-8")
    print(f"\nResults saved to: {args.output_json}")

    print("\n--- TOP 10 CONFIGURATIONS BY EVENT DENSITY ---")
    for r in results[:10]:
        print(f"[{r['cfg_id']:<26}] Evts: {r['total_events']:<6} | Cov: {r['coverage_pct']:>5.1f}% | Ev/Ses: {r['events_per_session']:>5.1f} | Buy/Sell: {r['buy_events']}/{r['sell_events']}")


if __name__ == "__main__":
    main()
