# -*- coding: utf-8 -*-
"""Multiverse Surface Sweep Optimization Engine for Intraday Range Sweeps.

Runs high-performance vectorised parameter sweep over all possible 24h time windows,
durations, stop/target ratios, and Fade vs Breakout modes.
Generates 2D / 3D heatmap surfaces to find persistent and robust trading windows.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path
import numpy as np
import pandas as pd


def load_m1_data(csv_or_parquet: str | Path) -> pd.DataFrame:
    path = Path(csv_or_parquet)
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
        
    df["Time"] = pd.to_datetime(df["Time"])
    df.dropna(subset=["Open", "High", "Low", "Close"], inplace=True)
    df.sort_values(by="Time", inplace=True)
    
    # Pre-extract temporal features
    df["date"] = df["Time"].dt.date
    df["minute_of_day"] = df["Time"].dt.hour * 60 + df["Time"].dt.minute
    return df


def sweep_time_windows(
    df: pd.DataFrame,
    start_step_min: int = 15,
    durations_min: list[int] = [30, 45, 60, 90, 120],
    point_value_usd: float = 5.0,
    cost_pts: float = 3.0,
    stop_ratio: float = 0.5,
    target_ratio: float = 1.0,
    mode: str = "FADE", # "FADE" or "BREAKOUT"
) -> pd.DataFrame:
    """Run combinatorial sweep across 24h start times and durations."""
    # Group by calendar date
    dates = df["date"].unique()
    n_days = len(dates)
    
    results = []
    start_times = list(range(0, 24 * 60, start_step_min))
    
    print(f"Running Multiverse Surface Sweep across {n_days} trading days...")
    print(f"Start times: {len(start_times)} points | Durations: {durations_min} | Mode: {mode}")
    t0 = time.time()
    
    # Group bars by date into fast array lookups
    day_groups = {d: group for d, group in df.groupby("date")}
    
    for start_m in start_times:
        h = start_m // 60
        m = start_m % 60
        time_str = f"{h:02d}:{m:02d}"
        
        for dur in durations_min:
            end_m = start_m + dur
            
            wins = 0
            losses = 0
            total_net_pts = 0.0
            gross_win_pts = 0.0
            gross_loss_pts = 0.0
            valid_sessions = 0
            
            for d, day_df in day_groups.items():
                # Extract window bars
                win_bars = day_df[(day_df["minute_of_day"] >= start_m) & (day_df["minute_of_day"] <= end_m)]
                if len(win_bars) < max(3, dur // 3):
                    continue
                    
                w_high = win_bars["High"].max()
                w_low = win_bars["Low"].min()
                range_pts = w_high - w_low
                if range_pts <= 0:
                    continue
                    
                post_bars = day_df[day_df["minute_of_day"] > end_m]
                if len(post_bars) < 10:
                    continue
                    
                valid_sessions += 1
                stop_pts = range_pts * stop_ratio
                target_pts = range_pts * target_ratio
                
                # Evaluate first sweep and trade evolution
                trade_open = False
                trade_side = None
                entry_price = 0.0
                tp_price = 0.0
                sl_price = 0.0
                trade_resolved = False
                trade_pnl = 0.0
                
                highs = post_bars["High"].values
                lows = post_bars["Low"].values
                
                for bar_h, bar_l in zip(highs, lows):
                    if not trade_open:
                        hit_h = bar_h >= w_high
                        hit_l = bar_l <= w_low
                        if hit_h and hit_l:
                            break # Same bar both, skip ambiguous
                        elif hit_h:
                            trade_open = True
                            if mode == "FADE": # Sell high expecting pullback to low
                                trade_side = "SHORT"
                                entry_price = w_high
                                tp_price = w_high - target_pts
                                sl_price = w_high + stop_pts
                            else: # Breakout Buy
                                trade_side = "LONG"
                                entry_price = w_high
                                tp_price = w_high + target_pts
                                sl_price = w_high - stop_pts
                        elif hit_l:
                            trade_open = True
                            if mode == "FADE": # Buy low expecting rally to high
                                trade_side = "LONG"
                                entry_price = w_low
                                tp_price = w_low + target_pts
                                sl_price = w_low - stop_pts
                            else: # Breakout Sell
                                trade_side = "SHORT"
                                entry_price = w_low
                                tp_price = w_low - target_pts
                                sl_price = w_low + stop_pts
                    else:
                        # Trade is open, check TP / SL
                        if trade_side == "SHORT":
                            hit_sl = bar_h >= sl_price
                            hit_tp = bar_l <= tp_price
                            if hit_sl and hit_tp:
                                trade_pnl = -(stop_pts + cost_pts)
                                trade_resolved = True
                                break
                            elif hit_tp:
                                trade_pnl = target_pts - cost_pts
                                trade_resolved = True
                                break
                            elif hit_sl:
                                trade_pnl = -(stop_pts + cost_pts)
                                trade_resolved = True
                                break
                        elif trade_side == "LONG":
                            hit_sl = bar_l <= sl_price
                            hit_tp = bar_h >= tp_price
                            if hit_sl and hit_tp:
                                trade_pnl = -(stop_pts + cost_pts)
                                trade_resolved = True
                                break
                            elif hit_tp:
                                trade_pnl = target_pts - cost_pts
                                trade_resolved = True
                                break
                            elif hit_sl:
                                trade_pnl = -(stop_pts + cost_pts)
                                trade_resolved = True
                                break
                
                if trade_resolved:
                    if trade_pnl > 0:
                        wins += 1
                        gross_win_pts += trade_pnl
                    else:
                        losses += 1
                        gross_loss_pts += abs(trade_pnl)
                    total_net_pts += trade_pnl
                    
            n_trades = wins + losses
            if n_trades >= 30:
                win_rate = wins / n_trades
                pf = gross_win_pts / gross_loss_pts if gross_loss_pts > 0 else 99.0
                ev_trade_usd = (total_net_pts / n_trades) * point_value_usd
                total_pnl_usd = total_net_pts * point_value_usd
                
                results.append({
                    "start_time": time_str,
                    "start_minute": start_m,
                    "duration_min": dur,
                    "mode": mode,
                    "n_trades": n_trades,
                    "win_rate": win_rate,
                    "profit_factor": pf,
                    "ev_trade_usd": ev_trade_usd,
                    "total_pnl_usd": total_pnl_usd,
                })
                
    res_df = pd.DataFrame(results)
    elapsed = time.time() - t0
    print(f"Sweep completed in {elapsed:.1f}s | Evaluated {len(res_df)} viable window configurations.\n")
    return res_df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=r"C:\EdgeLab\YM_1min.csv")
    parser.add_argument("--point-val", type=float, default=5.0)
    parser.add_argument("--cost-pts", type=float, default=3.0)
    args = parser.parse_args()
    
    df = load_m1_data(args.data)
    
    # 1. Sweep FADE mode (reversion)
    res_fade = sweep_time_windows(df, point_value_usd=args.point_val, cost_pts=args.cost_pts, mode="FADE")
    # 2. Sweep BREAKOUT mode (momentum)
    res_break = sweep_time_windows(df, point_value_usd=args.point_val, cost_pts=args.cost_pts, mode="BREAKOUT")
    
    print("=" * 85)
    print("TOP 10 VENTANAS ÓPTIMAS — MODO FADE / REVERSIÓN (Doble Barrido):")
    print("=" * 85)
    top_fade = res_fade.sort_values(by="profit_factor", ascending=False).head(10)
    print(f"{'Hora Inicio':<14} {'Duración':<12} {'Trades':<10} {'Win Rate':<12} {'Profit Factor':<15} {'EV / Trade':<14} {'Total PnL':<14}")
    print("-" * 85)
    for _, r in top_fade.iterrows():
        print(f"{r['start_time']:<14} {r['duration_min']:<4} min      {r['n_trades']:<10} {r['win_rate']*100:<10.1f}% {r['profit_factor']:<15.2f} ${r['ev_trade_usd']:<12.2f} ${r['total_pnl_usd']:<12.0f}")

    print("\n" + "=" * 85)
    print("TOP 10 VENTANAS ÓPTIMAS — MODO BREAKOUT / CONTINUACIÓN:")
    print("=" * 85)
    top_break = res_break.sort_values(by="profit_factor", ascending=False).head(10)
    print(f"{'Hora Inicio':<14} {'Duración':<12} {'Trades':<10} {'Win Rate':<12} {'Profit Factor':<15} {'EV / Trade':<14} {'Total PnL':<14}")
    print("-" * 85)
    for _, r in top_break.iterrows():
        print(f"{r['start_time']:<14} {r['duration_min']:<4} min      {r['n_trades']:<10} {r['win_rate']*100:<10.1f}% {r['profit_factor']:<15.2f} ${r['ev_trade_usd']:<12.2f} ${r['total_pnl_usd']:<12.0f}")


if __name__ == "__main__":
    main()
