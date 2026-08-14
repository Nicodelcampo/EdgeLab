# -*- coding: utf-8 -*-
"""Exhaustive Massive Multiverse Surface Sweep for Kaggle.

Evaluates 100+ continuous window durations (5 min to 300 min) across the entire 24-hour cycle,
all stop/target ratios, and Fade vs Breakout modes across YM, NQ, ES, GC, 6E.
Features auto-dataset discovery across all /kaggle/input/ subdirectories and multi-core parallelism.
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import time
from pathlib import Path
import numpy as np
import pandas as pd


def load_dataset_auto(dataset_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Auto-discovers parquet and csv files anywhere under dataset_dir."""
    d = Path(dataset_dir)
    print(f"Searching for datasets in {d}...")
    
    files = list(d.rglob("*.parquet"))
    if not files:
        files = list(d.rglob("*.csv"))
        
    data = {}
    for p in files:
        if "events" in p.name.lower() or "census" in p.name.lower():
            continue
            
        asset_name = p.stem.split("_")[0].upper()
        if asset_name in ["6E", "ES", "NQ", "YM", "GC"] or len(asset_name) <= 4:
            print(f"Loading {p.name} as [{asset_name}]...")
            if p.suffix == ".parquet":
                df = pd.read_parquet(p)
            else:
                df = pd.read_csv(p)
                
            df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
            df.dropna(subset=["Time", "Open", "High", "Low", "Close"], inplace=True)
            df.sort_values(by="Time", inplace=True)
            df.drop_duplicates(subset=["Time"], inplace=True)
            
            df["date"] = df["Time"].dt.date
            df["min_of_day"] = df["Time"].dt.hour * 60 + df["Time"].dt.minute
            data[asset_name] = df
            print(f"  -> [{asset_name}]: {len(df):,} bars | {df['date'].nunique()} trading days ({df['Time'].min().date()} to {df['Time'].max().date()})")
            
    return data


def eval_single_slice(args):
    """Worker function for single duration & start time evaluation."""
    (start_m, dur, day_sessions, asset_name, point_val, cost_pts, stop_ratios, target_ratios) = args
    h = start_m // 60
    m = start_m % 60
    t_str = f"{h:02d}:{m:02d}"
    end_m = start_m + dur
    
    # Filter sessions with valid range
    valid = []
    for (d_bars_min, d_highs, d_lows) in day_sessions:
        # Window mask
        mask_win = (d_bars_min >= start_m) & (d_bars_min <= end_m)
        if mask_win.sum() < max(3, dur // 5):
            continue
            
        w_high = d_highs[mask_win].max()
        w_low = d_lows[mask_win].min()
        r_pts = w_high - w_low
        if r_pts <= 0:
            continue
            
        mask_post = (d_bars_min > end_m)
        if mask_post.sum() < 10:
            continue
            
        valid.append((w_high, w_low, r_pts, d_highs[mask_post], d_lows[mask_post]))
        
    if len(valid) < 25:
        return []
        
    records = []
    for s_rat in stop_ratios:
        for t_rat in target_ratios:
            for mode in ["FADE", "BREAKOUT"]:
                wins = 0
                losses = 0
                net_pts = 0.0
                gross_win = 0.0
                gross_loss = 0.0
                
                for (w_high, w_low, r_pts, highs, lows) in valid:
                    stop_pts = r_pts * s_rat
                    target_pts = r_pts * t_rat
                    
                    trade_open = False
                    trade_side = 0 # 1 = Long, -1 = Short
                    tp_p = 0.0
                    sl_p = 0.0
                    resolved = False
                    pnl = 0.0
                    
                    for bh, bl in zip(highs, lows):
                        if not trade_open:
                            hh = bh >= w_high
                            hl = bl <= w_low
                            if hh and hl:
                                break
                            elif hh:
                                trade_open = True
                                trade_side = -1 if mode == "FADE" else 1
                                tp_p = w_high - target_pts if mode == "FADE" else w_high + target_pts
                                sl_p = w_high + stop_pts if mode == "FADE" else w_high - stop_pts
                            elif hl:
                                trade_open = True
                                trade_side = 1 if mode == "FADE" else -1
                                tp_p = w_low + target_pts if mode == "FADE" else w_low - target_pts
                                sl_p = w_low - stop_pts if mode == "FADE" else w_low + stop_pts
                        else:
                            if trade_side == -1: # Short
                                if bh >= sl_p and bl <= tp_p:
                                    pnl = -(stop_pts + cost_pts)
                                    resolved = True
                                    break
                                elif bl <= tp_p:
                                    pnl = target_pts - cost_pts
                                    resolved = True
                                    break
                                elif bh >= sl_p:
                                    pnl = -(stop_pts + cost_pts)
                                    resolved = True
                                    break
                            elif trade_side == 1: # Long
                                if bl <= sl_p and bh >= tp_p:
                                    pnl = -(stop_pts + cost_pts)
                                    resolved = True
                                    break
                                elif bh >= tp_p:
                                    pnl = target_pts - cost_pts
                                    resolved = True
                                    break
                                elif bl <= sl_p:
                                    pnl = -(stop_pts + cost_pts)
                                    resolved = True
                                    break
                                    
                    if resolved:
                        if pnl > 0:
                            wins += 1
                            gross_win += pnl
                        else:
                            losses += 1
                            gross_loss += abs(pnl)
                        net_pts += pnl
                        
                n_trades = wins + losses
                if n_trades >= 30:
                    wr = wins / n_trades
                    pf = gross_win / gross_loss if gross_loss > 0 else 99.0
                    ev_usd = (net_pts / n_trades) * point_val
                    tot_pnl = net_pts * point_val
                    
                    records.append({
                        "asset": asset_name,
                        "start_time": t_str,
                        "start_min": start_m,
                        "duration_min": dur,
                        "stop_ratio": s_rat,
                        "target_ratio": t_rat,
                        "mode": mode,
                        "n_trades": n_trades,
                        "win_rate": wr,
                        "profit_factor": pf,
                        "ev_usd": ev_usd,
                        "total_pnl_usd": tot_pnl,
                    })
    return records


def sweep_asset_parallel(
    df: pd.DataFrame,
    asset_name: str,
    point_val: float,
    cost_pts: float,
    start_step_min: int = 5,
    durations: list[int] = None,
    stop_ratios: list[float] = [0.3, 0.5, 0.7, 1.0],
    target_ratios: list[float] = [0.5, 1.0, 1.5, 2.0],
) -> pd.DataFrame:
    if durations is None:
        # Generate 100 continuous durations from 5 min to 302 min (step = 3 min)
        durations = list(range(5, 305, 3))
        
    # Pre-extract numpy arrays per date
    day_sessions = []
    for d, g in df.groupby("date"):
        day_sessions.append((g["min_of_day"].values, g["High"].values, g["Low"].values))
        
    start_times = list(range(0, 24 * 60, start_step_min))
    total_slices = len(start_times) * len(durations)
    total_evals = total_slices * len(stop_ratios) * len(target_ratios) * 2
    
    print(f"\n==================================================")
    print(f"ASSET: {asset_name} | {len(day_sessions)} Trading Days")
    print(f"Durations tested: {len(durations)} (from {min(durations)}m to {max(durations)}m)")
    print(f"Start times tested: {len(start_times)} (every {start_step_min}m over 24h)")
    print(f"Total Combinatorial Evaluations: {total_evals:,}")
    print(f"==================================================")
    
    task_args = [
        (s, dur, day_sessions, asset_name, point_val, cost_pts, stop_ratios, target_ratios)
        for s in start_times
        for dur in durations
    ]
    
    t0 = time.time()
    n_cpus = max(1, mp.cpu_count())
    print(f"Executing parallel sweep on {n_cpus} CPU workers...")
    
    with mp.Pool(processes=n_cpus) as pool:
        results_nested = pool.map(eval_single_slice, task_args, chunksize=100)
        
    all_records = [rec for sublist in results_nested for rec in sublist]
    res_df = pd.DataFrame(all_records)
    
    elapsed = time.time() - t0
    print(f"Done for {asset_name} in {elapsed:.1f}s | Found {len(res_df):,} profitable parameter sets.")
    return res_df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="/kaggle/input", help="Directory with datasets")
    parser.add_argument("--output-csv", default="multiverse_full_results.csv", help="Output CSV path")
    parser.add_argument("--start-step", type=int, default=5, help="Step in minutes for 24h start times")
    args = parser.parse_args()
    
    data = load_dataset_auto(args.data_dir)
    if not data:
        print("ERROR: No datasets found in data-dir! Checking fallback paths...")
        for alt_path in ["/kaggle/input/edgelab-m1-dataset", "C:\\EdgeLab\\m1_parquets", "C:\\EdgeLab", "."]:
            if Path(alt_path).exists():
                data = load_dataset_auto(alt_path)
                if data:
                    break
                    
    if not data:
        print("FATAL: Could not locate dataset parquets. Please check dataset attachment.")
        return
        
    point_vals = {"YM": 5.0, "ES": 50.0, "NQ": 20.0, "GC": 100.0, "6E": 125000.0}
    costs = {"YM": 3.0, "ES": 0.5, "NQ": 1.0, "GC": 0.4, "6E": 0.00010}
    
    all_dfs = []
    for asset, df in data.items():
        pval = point_vals.get(asset, 5.0)
        cpts = costs.get(asset, 1.0)
        res = sweep_asset_parallel(df, asset_name=asset, point_val=pval, cost_pts=cpts, start_step_min=args.start_step)
        all_dfs.append(res)
        
    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        final_df.to_csv(args.output_csv, index=False)
        print(f"\n==================================================")
        print(f"MASSIVE MULTIVERSE COMPLETE! Results saved to {args.output_csv}")
        print(f"Total Parameter Sets Evaluated: {len(final_df):,}")
        print(f"==================================================")
        
        for asset in data.keys():
            print(f"\n--- TOP 5 ROBUST CONFIGURATIONS: {asset} ---")
            sub = final_df[final_df["asset"] == asset].sort_values(by="profit_factor", ascending=False).head(5)
            if not sub.empty:
                print(sub[["start_time", "duration_min", "mode", "stop_ratio", "target_ratio", "win_rate", "profit_factor", "ev_usd", "total_pnl_usd"]].to_string())


if __name__ == "__main__":
    main()
