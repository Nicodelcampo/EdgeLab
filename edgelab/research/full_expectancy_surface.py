#!/usr/bin/env python3
"""Full 2D Expectancy Surface Analysis across all Target and Stop Distances.

For any pair of (d_TP, d_SL):
- Gambler's Ruin / Brownian Benchmark Win Rate: p_0 = d_SL / (d_TP + d_SL)
- Excess Probability: Delta_p = p - p_0
- Mathematical Expectation in R-multiples: E[R] = p * (d_TP / d_SL) - (1 - p)
- Profit Factor: PF = (p * d_TP) / ((1 - p) * d_SL)
"""

import math
import numpy as np
import pandas as pd
from pathlib import Path

DATA_DIR = Path(r"C:\EdgeLab")
GEX_DIR = Path(r"D:\EdgeLab\data\gex")


def evaluate_full_surface(m1_file: Path, gex_file: Path, asset_name: str):
    print(f"\n=========================================================================================")
    print(f"FULL 2D EXPECTANCY SURFACE & PnL MATRIX: {asset_name}")
    print(f"=========================================================================================")
    
    df_m1 = pd.read_csv(m1_file)
    df_m1['Time'] = pd.to_datetime(df_m1['Time'])
    df_m1['Date'] = df_m1['Time'].dt.strftime('%Y-%m-%d')
    df_m1['HourMin'] = df_m1['Time'].dt.strftime('%H:%M')
    
    df_gex = pd.read_parquet(gex_file)
    gex_map = df_gex.set_index('date').to_dict(orient='index')
    
    # Grid of Target and Stop Multipliers (relative to Range Width)
    tp_mults = [0.25, 0.50, 0.75, 1.00, 1.50]
    sl_mults = [0.25, 0.50, 0.75, 1.00, 1.50]
    
    # Collect all sweep re-entry trades
    trades = []
    unique_dates = df_m1['Date'].unique()
    
    for dt in unique_dates:
        if dt not in gex_map:
            continue
        regime = gex_map[dt]['regime']
        
        day_bars = df_m1[df_m1['Date'] == dt].sort_values('Time').reset_index(drop=True)
        if len(day_bars) < 200:
            continue
            
        range_bars = day_bars[(day_bars['HourMin'] >= '08:12') & (day_bars['HourMin'] <= '09:12')]
        if len(range_bars) < 15:
            continue
            
        r_hi = range_bars['High'].max()
        r_lo = range_bars['Low'].min()
        r_w = r_hi - r_lo
        if r_w <= 0:
            continue
            
        post_bars = day_bars[day_bars['HourMin'] > '09:12'].reset_index(drop=True)
        
        swept_hi, swept_lo, taken = False, False, False
        for i in range(len(post_bars)):
            if taken:
                break
            b_hi = post_bars.loc[i, 'High']
            b_lo = post_bars.loc[i, 'Low']
            b_cl = post_bars.loc[i, 'Close']
            
            # Short re-entry
            if b_hi > r_hi and not swept_hi:
                swept_hi = True
            elif swept_hi and not taken and b_cl < r_hi:
                taken = True
                trades.append({
                    "type": "SHORT",
                    "entry": b_cl,
                    "range_w": r_w,
                    "regime": regime,
                    "future_highs": post_bars.loc[i+1:, 'High'].values,
                    "future_lows": post_bars.loc[i+1:, 'Low'].values,
                })
                
            # Long re-entry
            elif b_lo < r_lo and not swept_lo:
                swept_lo = True
            elif swept_lo and not taken and b_cl > r_lo:
                taken = True
                trades.append({
                    "type": "LONG",
                    "entry": b_cl,
                    "range_w": r_w,
                    "regime": regime,
                    "future_highs": post_bars.loc[i+1:, 'High'].values,
                    "future_lows": post_bars.loc[i+1:, 'Low'].values,
                })

    print(f"Total Sweep Re-entry Trades Identified: {len(trades)}")
    
    # Evaluate every (TP, SL) cell in the grid
    for regime_filter in ["ALL_DAYS", "POSITIVE_GAMMA"]:
        print(f"\n--- REGIME: {regime_filter} ---")
        print(f"{'TP_Mult':<8} | {'SL_Mult':<8} | {'N':<5} | {'Real Win%':<10} | {'Null Win%':<10} | {'Delta Win%':<11} | {'E[R]':<9} | {'Profit Factor':<13} | {'VEREDICTO'}")
        print("-" * 115)
        
        for tp_m in tp_mults:
            for sl_m in sl_mults:
                # Null benchmark win rate under pure random walk
                p_0 = sl_m / (tp_m + sl_m)
                
                wins = 0
                losses = 0
                
                for t in trades:
                    if regime_filter == "POSITIVE_GAMMA" and t["regime"] != "POSITIVE_GAMMA":
                        continue
                        
                    entry = t["entry"]
                    rw = t["range_w"]
                    d_tp = rw * tp_m
                    d_sl = rw * sl_m
                    
                    f_hi = t["future_highs"]
                    f_lo = t["future_lows"]
                    
                    if t["type"] == "SHORT":
                        target = entry - d_tp
                        stop = entry + d_sl
                        for h, l in zip(f_hi, f_lo):
                            hit_tp = (l <= target)
                            hit_sl = (h >= stop)
                            if hit_tp and hit_sl:
                                break # Ambiguous
                            elif hit_tp:
                                wins += 1
                                break
                            elif hit_sl:
                                losses += 1
                                break
                    else: # LONG
                        target = entry + d_tp
                        stop = entry - d_sl
                        for h, l in zip(f_hi, f_lo):
                            hit_tp = (h >= target)
                            hit_sl = (l <= stop)
                            if hit_tp and hit_sl:
                                break
                            elif hit_tp:
                                wins += 1
                                break
                            elif hit_sl:
                                losses += 1
                                break
                                
                total = wins + losses
                if total < 10:
                    continue
                    
                real_win = wins / total
                delta_win = (real_win - p_0) * 100.0
                e_r = real_win * (tp_m / sl_m) - (1.0 - real_win)
                pf = (real_win * tp_m) / max((1.0 - real_win) * sl_m, 1e-6)
                
                if e_r > 0.05 and delta_win > 2.0:
                    verdict = "EDGE POSITIVO (+EV)"
                elif e_r < -0.05:
                    verdict = "-EV (Pérdida)"
                else:
                    verdict = "NEUTRO / AZAR"
                    
                print(f"{tp_m:<8.2f} | {sl_m:<8.2f} | {total:<5} | {real_win*100:8.2f}% | {p_0*100:8.2f}% | {delta_win:+9.2f}% | {e_r:+8.4f}R | {pf:11.2f}x | {verdict}")


def main():
    es_file = DATA_DIR / "ES_1min.csv"
    nq_file = DATA_DIR / "NQ_1min.csv"
    gex_sp500 = GEX_DIR / "gex_daily_sp500_history.parquet"
    gex_nasdaq = GEX_DIR / "gex_daily_nasdaq_history.parquet"
    
    if es_file.exists() and gex_sp500.exists():
        evaluate_full_surface(es_file, gex_sp500, "E-MINI S&P 500 (ES)")
        
    if nq_file.exists() and gex_nasdaq.exists():
        evaluate_full_surface(nq_file, gex_nasdaq, "E-MINI NASDAQ 100 (NQ)")


if __name__ == "__main__":
    main()
