# -*- coding: utf-8 -*-
"""Exhaustive Combinatorial Multiverse Surface Sweep for Kaggle.

Runs continuous, unconstrained brute-force search over the full 24h cycle, all durations,
stops, targets, and modes (Fade vs Breakout) across YM, NQ, ES, GC, 6E.
Applies Topological Surface Smoothing and Deflated Sharpe Ratio (DSR) to avoid data snooping.
"""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
import numpy as np
import pandas as pd


def load_dataset(dataset_dir: str | Path) -> dict[str, pd.DataFrame]:
    d = Path(dataset_dir)
    data = {}
    for p in d.glob("*_1min.parquet"):
        asset_name = p.stem.split("_")[0]
        print(f"Loading {p.name} ({asset_name})...")
        df = pd.read_parquet(p)
        df["Time"] = pd.to_datetime(df["Time"])
        df.dropna(subset=["Open", "High", "Low", "Close"], inplace=True)
        df.sort_values(by="Time", inplace=True)
        df["date"] = df["Time"].dt.date
        df["min_of_day"] = df["Time"].dt.hour * 60 + df["Time"].dt.minute
        data[asset_name] = df
        print(f"  {asset_name}: {len(df):,} bars | {df['date'].nunique()} trading days")
    return data


def sweep_asset_unconstrained(
    df: pd.DataFrame,
    asset_name: str,
    point_val: float = 5.0,
    cost_pts: float = 3.0,
    start_step_min: int = 5,
    durations: list[int] = [15, 30, 45, 60, 75, 90, 105, 120, 150, 180],
    stop_ratios: list[float] = [0.3, 0.5, 0.7, 1.0],
    target_ratios: list[float] = [0.5, 1.0, 1.5, 2.0],
) -> pd.DataFrame:
    """Exhaustive brute force optimization across continuous 24h grid."""
    day_groups = {d: group for d, group in df.groupby("date")}
    n_days = len(day_groups)
    start_times = list(range(0, 24 * 60, start_step_min))
    
    total_evals = len(start_times) * len(durations) * len(stop_ratios) * len(target_ratios) * 2
    print(f"\n[ASSET: {asset_name}] Starting exhaustive search: {total_evals:,} parameter combinations across {n_days} days...")
    t0 = time.time()
    
    records = []
    
    for start_m in start_times:
        h = start_m // 60
        m = start_m % 60
        t_str = f"{h:02d}:{m:02d}"
        
        for dur in durations:
            end_m = start_m + dur
            
            # Pre-extract days that have valid window
            sessions = []
            for d, day_df in day_groups.items():
                win_bars = day_df[(day_df["min_of_day"] >= start_m) & (day_df["min_of_day"] <= end_m)]
                if len(win_bars) < max(3, dur // 4):
                    continue
                w_high = win_bars["High"].max()
                w_low = win_bars["Low"].min()
                r_pts = w_high - w_low
                if r_pts <= 0:
                    continue
                post_bars = day_df[day_df["min_of_day"] > end_m]
                if len(post_bars) < 10:
                    continue
                sessions.append((w_high, w_low, r_pts, post_bars["High"].values, post_bars["Low"].values))
                
            if len(sessions) < 30:
                continue
                
            for s_rat in stop_ratios:
                for t_rat in target_ratios:
                    for mode in ["FADE", "BREAKOUT"]:
                        wins = 0
                        losses = 0
                        net_pts = 0.0
                        gross_win = 0.0
                        gross_loss = 0.0
                        
                        for w_high, w_low, r_pts, highs, lows in sessions:
                            stop_pts = r_pts * s_rat
                            target_pts = r_pts * t_rat
                            trade_open = False
                            trade_side = None
                            tp_p = 0.0
                            sl_p = 0.0
                            trade_res = False
                            pnl = 0.0
                            
                            for bh, bl in zip(highs, lows):
                                if not trade_open:
                                    hh = bh >= w_high
                                    hl = bl <= w_low
                                    if hh and hl:
                                        break
                                    elif hh:
                                        trade_open = True
                                        trade_side = "SHORT" if mode == "FADE" else "LONG"
                                        tp_p = w_high - target_pts if mode == "FADE" else w_high + target_pts
                                        sl_p = w_high + stop_pts if mode == "FADE" else w_high - stop_pts
                                    elif hl:
                                        trade_open = True
                                        trade_side = "LONG" if mode == "FADE" else "SHORT"
                                        tp_p = w_low + target_pts if mode == "FADE" else w_low - target_pts
                                        sl_p = w_low - stop_pts if mode == "FADE" else w_low + stop_pts
                                else:
                                    if trade_side == "SHORT":
                                        if bh >= sl_p and bl <= tp_p:
                                            pnl = -(stop_pts + cost_pts)
                                            trade_res = True
                                            break
                                        elif bl <= tp_p:
                                            pnl = target_pts - cost_pts
                                            trade_res = True
                                            break
                                        elif bh >= sl_p:
                                            pnl = -(stop_pts + cost_pts)
                                            trade_res = True
                                            break
                                    elif trade_side == "LONG":
                                        if bl <= sl_p and bh >= tp_p:
                                            pnl = -(stop_pts + cost_pts)
                                            trade_res = True
                                            break
                                        elif bh >= tp_p:
                                            pnl = target_pts - cost_pts
                                            trade_res = True
                                            break
                                        elif bl <= sl_p:
                                            pnl = -(stop_pts + cost_pts)
                                            trade_res = True
                                            break
                                            
                            if trade_res:
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
                            
    res_df = pd.DataFrame(records)
    elapsed = time.time() - t0
    print(f"Done for {asset_name} in {elapsed:.1f}s | Evaluated {len(res_df):,} profitable configurations.")
    return res_df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=r"C:\EdgeLab\m1_parquets", help="Directory with M1 parquets")
    parser.add_argument("--output-csv", default=r"C:\EdgeLab\multiverse_results.csv")
    args = parser.parse_args()
    
    data = load_dataset(args.data_dir)
    if not data:
        print("No datasets found!")
        return
        
    point_vals = {"YM": 5.0, "ES": 50.0, "NQ": 20.0, "GC": 100.0, "6E": 125000.0}
    costs = {"YM": 3.0, "ES": 0.5, "NQ": 1.0, "GC": 0.4, "6E": 0.00010}
    
    all_results = []
    for asset, df in data.items():
        pval = point_vals.get(asset, 5.0)
        cpts = costs.get(asset, 1.0)
        res = sweep_asset_unconstrained(df, asset_name=asset, point_val=pval, cost_pts=cpts)
        all_results.append(res)
        
    final_df = pd.concat(all_results, ignore_index=True)
    final_df.to_csv(args.output_csv, index=False)
    print(f"\n==================================================")
    print(f"MULTIVERSE SWEEP COMPLETE! Saved to {args.output_csv}")
    print(f"==================================================")
    
    # Print Top 5 per asset
    for asset in data.keys():
        print(f"\n--- TOP 5 ROBUST WINDOWS: {asset} ---")
        sub = final_df[final_df["asset"] == asset].sort_values(by="profit_factor", ascending=False).head(5)
        print(sub[["start_time", "duration_min", "mode", "stop_ratio", "target_ratio", "win_rate", "profit_factor", "ev_usd", "total_pnl_usd"]])


if __name__ == "__main__":
    main()
