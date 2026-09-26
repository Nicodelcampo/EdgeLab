#!/usr/bin/env python3
"""F2.7-Grade Strict Symmetric Stress Test & Variant Optimization for GEX Re-entry (ES, NQ, YM)."""

import math
import numpy as np
import pandas as pd
from pathlib import Path

DATA_DIR = Path(r"C:\EdgeLab")
GEX_DIR = Path(r"D:\EdgeLab\data\gex")


def hac_bartlett_se(series: list[float], max_lag: int | None = None) -> tuple[float, float, float, float]:
    """Computes sample mean, HAC Bartlett standard error, and 95% CI."""
    n = len(series)
    if n < 2:
        return 0.0, 0.0, 0.0, 0.0
    x = np.asarray(series, dtype=np.float64)
    mean = float(np.mean(x))
    dm = x - mean
    gamma0 = float(np.dot(dm, dm) / n)
    if max_lag is None:
        max_lag = int(math.ceil(math.sqrt(n)))
    v = gamma0
    for lag in range(1, max_lag + 1):
        w = 1.0 - (lag / (max_lag + 1.0))
        gamma_l = float(np.dot(dm[lag:], dm[:-lag]) / n)
        v += 2.0 * w * gamma_l
    v = max(v, 0.0)
    se = math.sqrt(v / n)
    return mean, se, mean - 1.96 * se, mean + 1.96 * se


def evaluate_asset_variants(m1_file: Path, gex_file: Path, asset_name: str, point_scale: float = 1.0) -> dict:
    print(f"\n================================================================================")
    print(f"STRICT SYMMETRIC STRESS TEST & VARIANTS: {asset_name}")
    print(f"================================================================================")
    
    df_m1 = pd.read_csv(m1_file)
    df_m1['Time'] = pd.to_datetime(df_m1['Time'])
    df_m1['Date'] = df_m1['Time'].dt.strftime('%Y-%m-%d')
    df_m1['HourMin'] = df_m1['Time'].dt.strftime('%H:%M')
    
    df_gex = pd.read_parquet(gex_file)
    gex_map = df_gex.set_index('date').to_dict(orient='index')
    
    # Store results for all variants
    variants = {
        "V0_Symmetric_Baseline": [],           # Pure re-entry, exact symmetric TP=SL=d (E[r]=0 under null)
        "V1_Symmetric_Plus_GEX": [],           # Pure re-entry + Positive Gamma only
        "V2_Symmetric_Minus_GEX": [],          # Pure re-entry + Negative Gamma only
        "V3_GEX_Plus_Rejection_Wick": [],      # +GEX + Re-entry bar has >= 25% rejection wick
        "V4_GEX_Plus_Wall_Alignment": [],      # +GEX + Sweep occurs near Call/Put Wall
        "V5_High_Conviction_All_Filters": [],  # +GEX + Wall + Rejection Wick
    }
    
    unique_dates = df_m1['Date'].unique()
    
    for dt in unique_dates:
        if dt not in gex_map:
            continue
            
        gex_info = gex_map[dt]
        regime = gex_info['regime']
        call_wall = gex_info['call_wall'] * point_scale
        put_wall = gex_info['put_wall'] * point_scale
        
        day_bars = df_m1[df_m1['Date'] == dt].sort_values('Time').reset_index(drop=True)
        if len(day_bars) < 200:
            continue
            
        # Morning reference range (08:12 to 09:12 ART)
        range_bars = day_bars[(day_bars['HourMin'] >= '08:12') & (day_bars['HourMin'] <= '09:12')]
        if len(range_bars) < 15:
            continue
            
        range_hi = range_bars['High'].max()
        range_lo = range_bars['Low'].min()
        range_width = range_hi - range_lo
        
        if range_width <= 0:
            continue
            
        # STRICT SYMMETRIC DISTANCE: d = 0.5 * range_width (for BOTH TP and SL)
        d = range_width * 0.5
        
        post_bars = day_bars[day_bars['HourMin'] > '09:12'].reset_index(drop=True)
        
        sweep_high = False
        sweep_low = False
        trade_taken = False
        
        for i in range(len(post_bars)):
            if trade_taken:
                break
                
            b_op = post_bars.loc[i, 'Open']
            b_hi = post_bars.loc[i, 'High']
            b_lo = post_bars.loc[i, 'Low']
            b_cl = post_bars.loc[i, 'Close']
            bar_range = max(b_hi - b_lo, 1e-4)
            
            # Case 1: Upper Sweep & Re-entry (Short)
            if b_hi > range_hi and not sweep_high:
                sweep_high = True
                peak_hi = b_hi
            elif sweep_high and not trade_taken:
                peak_hi = max(peak_hi, b_hi)
                if b_cl < range_hi:
                    trade_taken = True
                    entry_p = b_cl
                    # STRICT SYMMETRIC RACE: TP = entry - d, SL = entry + d
                    tp = entry_p - d
                    sl = entry_p + d
                    
                    # Rejection wick calculation (Upper wick = High - max(Open, Close))
                    upper_wick = b_hi - max(b_op, b_cl)
                    wick_frac = upper_wick / bar_range
                    
                    # Wall proximity check (Peak within 25 pts of Call Wall)
                    wall_near = abs(peak_hi - call_wall) <= 25.0 if not np.isnan(call_wall) else False
                    
                    # Run race
                    outcome = 0
                    for j in range(i + 1, len(post_bars)):
                        sub_hi = post_bars.loc[j, 'High']
                        sub_lo = post_bars.loc[j, 'Low']
                        hit_tp = (sub_lo <= tp)
                        hit_sl = (sub_hi >= sl)
                        if hit_tp and hit_sl:
                            outcome = 0 # Ambiguous
                            break
                        elif hit_tp:
                            outcome = 1 # Win Reversal
                            break
                        elif hit_sl:
                            outcome = -1 # Loss Continuation
                            break
                            
                    if outcome != 0:
                        variants["V0_Symmetric_Baseline"].append(outcome)
                        if regime == "POSITIVE_GAMMA":
                            variants["V1_Symmetric_Plus_GEX"].append(outcome)
                            if wick_frac >= 0.25:
                                variants["V3_GEX_Plus_Rejection_Wick"].append(outcome)
                            if wall_near:
                                variants["V4_GEX_Plus_Wall_Alignment"].append(outcome)
                            if wick_frac >= 0.25 and wall_near:
                                variants["V5_High_Conviction_All_Filters"].append(outcome)
                        else:
                            variants["V2_Symmetric_Minus_GEX"].append(outcome)
                            
            # Case 2: Lower Sweep & Re-entry (Long)
            if b_lo < range_lo and not sweep_low:
                sweep_low = True
                peak_lo = b_lo
            elif sweep_low and not trade_taken:
                peak_lo = min(peak_lo, b_lo)
                if b_cl > range_lo:
                    trade_taken = True
                    entry_p = b_cl
                    # STRICT SYMMETRIC RACE: TP = entry + d, SL = entry - d
                    tp = entry_p + d
                    sl = entry_p - d
                    
                    # Rejection wick calculation (Lower wick = min(Open, Close) - Low)
                    lower_wick = min(b_op, b_cl) - b_lo
                    wick_frac = lower_wick / bar_range
                    
                    # Wall proximity check (Peak within 25 pts of Put Wall)
                    wall_near = abs(peak_lo - put_wall) <= 25.0 if not np.isnan(put_wall) else False
                    
                    # Run race
                    outcome = 0
                    for j in range(i + 1, len(post_bars)):
                        sub_hi = post_bars.loc[j, 'High']
                        sub_lo = post_bars.loc[j, 'Low']
                        hit_tp = (sub_hi >= tp)
                        hit_sl = (sub_lo <= sl)
                        if hit_tp and hit_sl:
                            outcome = 0
                            break
                        elif hit_tp:
                            outcome = 1
                            break
                        elif hit_sl:
                            outcome = -1
                            break
                            
                    if outcome != 0:
                        variants["V0_Symmetric_Baseline"].append(outcome)
                        if regime == "POSITIVE_GAMMA":
                            variants["V1_Symmetric_Plus_GEX"].append(outcome)
                            if wick_frac >= 0.25:
                                variants["V3_GEX_Plus_Rejection_Wick"].append(outcome)
                            if wall_near:
                                variants["V4_GEX_Plus_Wall_Alignment"].append(outcome)
                            if wick_frac >= 0.25 and wall_near:
                                variants["V5_High_Conviction_All_Filters"].append(outcome)
                        else:
                            variants["V2_Symmetric_Minus_GEX"].append(outcome)

    print(f"{'VARIANTE':<35} | {'N':<5} | {'WIN %':<8} | {'MEDIA r':<10} | {'IC 95%':<22} | {'VEREDICTO'}")
    print("-" * 105)
    
    summary = {}
    for name, outcomes in variants.items():
        n = len(outcomes)
        if n == 0:
            print(f"{name:<35} | {0:<5} | {'N/A':<8} | {'N/A':<10} | {'N/A':<22} | INSUFICIENTE")
            continue
        wins = outcomes.count(1)
        losses = outcomes.count(-1)
        win_rate = (wins / n) * 100.0
        mean, se, ci_lo, ci_hi = hac_bartlett_se(outcomes)
        
        ci_str = f"[{ci_lo:+.3f}, {ci_hi:+.3f}]"
        if ci_lo > 0:
            verdict = "EDGE REAL (Excluye 0)"
        elif ci_hi < 0:
            verdict = "FADE (Continua)"
        else:
            verdict = "NEUTRO / NULO (Cruza 0)"
            
        print(f"{name:<35} | {n:<5} | {win_rate:6.2f}% | {mean:+8.4f} | {ci_str:<22} | {verdict}")
        summary[name] = {"n": n, "win_rate": win_rate, "mean": mean, "ci_lo": ci_lo, "ci_hi": ci_hi, "verdict": verdict}
        
    return summary


def main():
    es_file = DATA_DIR / "ES_1min.csv"
    nq_file = DATA_DIR / "NQ_1min.csv"
    gex_sp500 = GEX_DIR / "gex_daily_sp500_history.parquet"
    gex_nasdaq = GEX_DIR / "gex_daily_nasdaq_history.parquet"
    
    if es_file.exists() and gex_sp500.exists():
        # SPY to ES scale is ~10x
        evaluate_asset_variants(es_file, gex_sp500, "E-MINI S&P 500 (ES)", point_scale=10.0)
        
    if nq_file.exists() and gex_nasdaq.exists():
        # QQQ to NQ scale is ~40x
        evaluate_asset_variants(nq_file, gex_nasdaq, "E-MINI NASDAQ 100 (NQ)", point_scale=40.0)


if __name__ == "__main__":
    main()
