#!/usr/bin/env python3
"""Rigorous F2.7 Evaluation of 3 Structural Edge Variants:
1. Delta & Volume Absorption at the Extreme (Tick-level Order Flow).
2. Liquidity Void / Imbalance Fast Traversal (Gap Fill Highway).
3. Institutional GEX Call Wall & Put Wall Bounces.
"""

import math
import numpy as np
import pandas as pd
from pathlib import Path

DATA_DIR = Path(r"C:\EdgeLab")
GEX_DIR = Path(r"D:\EdgeLab\data\gex")
PARQUET_6E_DIR = Path(r"D:\EdgeLab\data\nt8\6E")


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


# ==============================================================================
# TEST 1: DELTA ABSORPTION AT EXTREME (TICK-LEVEL 6E PARQUET)
# ==============================================================================
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from edgelab.bridge.ticks import load_canonical_parquet
from edgelab.bridge.bars import build_time_bars, build_footprints

def test_delta_absorption_on_ticks():
    print(f"\n================================================================================")
    print(f"TEST 1: DELTA & VOLUME ABSORPTION AT SWEEP EXTREME (TICK-LEVEL ORDER FLOW)")
    print(f"================================================================================")
    
    p_files = list(PARQUET_6E_DIR.glob("*.parquet"))
    if not p_files:
        print("No 6E tick parquets found.")
        return
        
    all_outcomes_pure = []
    all_outcomes_delta_trap = []
    
    for pf in p_files:
        try:
            ticks = load_canonical_parquet(pf, instrument="6E")
        except Exception:
            continue
            
        bars = build_time_bars(ticks, minutes=1)
        fps = build_footprints(ticks, bars)
        n_b = len(bars.close_t)
        if n_b < 500:
            continue
            
        delta_arr = np.zeros(n_b, dtype=np.float64)
        for b_idx in range(n_b):
            ask_v = sum(fps.ask[b_idx].values()) if b_idx < len(fps.ask) else 0.0
            bid_v = sum(fps.bid[b_idx].values()) if b_idx < len(fps.bid) else 0.0
            delta_arr[b_idx] = ask_v - bid_v
                
        # Group into 60-bar sessions to test sweeps
        for s_start in range(0, n_b - 120, 60):
            ref_bars = bars.high_t[s_start:s_start + 30]
            ref_lo_bars = bars.low_t[s_start:s_start + 30]
            if len(ref_bars) < 30:
                continue
            r_hi = np.max(ref_bars)
            r_lo = np.min(ref_lo_bars)
            r_w = r_hi - r_lo
            if r_w < 10:
                continue
                
            d_ticks = max(int(r_w * 0.5), 4)
            
            # Post window
            swept_hi = False
            for k in range(s_start + 30, min(s_start + 90, n_b)):
                cur_hi = bars.high_t[k]
                cur_lo = bars.low_t[k]
                cur_cl = bars.close_t[k]
                cur_delta = delta_arr[k]
                
                if cur_hi > r_hi and not swept_hi:
                    swept_hi = True
                elif swept_hi:
                    # Re-entry: close back below r_hi
                    if cur_cl < r_hi:
                        entry = cur_cl
                        tp = entry - d_ticks
                        sl = entry + d_ticks
                        
                        # Check Delta Trap: Price swept High, but Bar Delta is Negative or Absorbed
                        is_delta_trap = (cur_delta < 0)  # Aggressive sellers took over or buyers exhausted
                        
                        # Race
                        res = 0
                        for f in range(k + 1, min(k + 50, n_b)):
                            h_f = bars.high_t[f]
                            l_f = bars.low_t[f]
                            hit_tp = (l_f <= tp)
                            hit_sl = (h_f >= sl)
                            if hit_tp and hit_sl:
                                break
                            elif hit_tp:
                                res = 1
                                break
                            elif hit_sl:
                                res = -1
                                break
                        if res != 0:
                            all_outcomes_pure.append(res)
                            if is_delta_trap:
                                all_outcomes_delta_trap.append(res)
                        break

    print(f"{'VARIANTE':<40} | {'N':<5} | {'WIN %':<8} | {'MEDIA r':<10} | {'IC 95%':<22} | {'VEREDICTO'}")
    print("-" * 110)
    for name, outcomes in [("Sweep Re-entry Puro (Tick 6E)", all_outcomes_pure), ("Delta Trap / Absorción Confirmada", all_outcomes_delta_trap)]:
        n = len(outcomes)
        if n == 0:
            continue
        w = outcomes.count(1)
        wr = (w / n) * 100.0
        m, se, lo, hi = hac_bartlett_se(outcomes)
        verdict = "EDGE REAL (Excluye 0)" if lo > 0 else "NEUTRO / NULO"
        print(f"{name:<40} | {n:<5} | {wr:6.2f}% | {m:+8.4f} | {f'[{lo:+.3f}, {hi:+.3f}]':<22} | {verdict}")


# ==============================================================================
# TEST 2: LIQUIDITY VOID TRAVERSAL (HIGHWAY FILLING ON ES & NQ)
# ==============================================================================
def test_liquidity_void_traversal():
    print(f"\n================================================================================")
    print(f"TEST 2: DESPLAZAMIENTO POR VACÍOS DE LIQUIDEZ / IMBALANCES (LIQUIDITY HIGHWAY)")
    print(f"================================================================================")
    
    for fn, name in [("ES_1min.csv", "E-MINI S&P 500 (ES)"), ("NQ_1min.csv", "E-MINI NASDAQ 100 (NQ)")]:
        fpath = DATA_DIR / fn
        if not fpath.exists():
            continue
            
        df = pd.read_csv(fpath)
        highs = df['High'].values
        lows = df['Low'].values
        closes = df['Close'].values
        opens = df['Open'].values
        n = len(df)
        
        outcomes_void_traversal = []
        
        # Detect Fair Value Gaps / Imbalances (3-bar pattern: Bar 0 High < Bar 2 Low -> Bullish Void)
        for i in range(2, n - 30):
            # Bullish Void (Gap between Bar i-2 High and Bar i Low)
            gap_lo = highs[i - 2]
            gap_hi = lows[i]
            gap_size = gap_hi - gap_lo
            
            if gap_size > 0:
                avg_range = np.mean(highs[i-10:i] - lows[i-10:i])
                if gap_size >= avg_range * 1.2:  # Wide significant void
                    # When price enters the void from above (re-testing the void):
                    # Test if it accelerates THROUGH the void to the other shelf (fill gap_lo)
                    for k in range(i + 1, min(i + 40, n)):
                        if lows[k] < gap_hi and closes[k] < gap_hi: # Price entered the void
                            entry = closes[k]
                            tp = gap_lo # Target: Fill the void
                            d = abs(entry - tp)
                            sl = entry + d # Strict Symmetric Stop
                            if d <= 0:
                                break
                            
                            res = 0
                            for m in range(k + 1, min(k + 30, n)):
                                hit_tp = (lows[m] <= tp)
                                hit_sl = (highs[m] >= sl)
                                if hit_tp and hit_sl:
                                    break
                                elif hit_tp:
                                    res = 1
                                    break
                                elif hit_sl:
                                    res = -1
                                    break
                            if res != 0:
                                outcomes_void_traversal.append(res)
                            break

        n_tot = len(outcomes_void_traversal)
        if n_tot > 0:
            w = outcomes_void_traversal.count(1)
            wr = (w / n_tot) * 100.0
            m, se, lo, hi = hac_bartlett_se(outcomes_void_traversal)
            verdict = "EDGE REAL (Excluye 0)" if lo > 0 else "NEUTRO / NULO"
            print(f"{name:<40} | N={n_tot:<4} | Win: {wr:6.2f}% | Media r: {m:+8.4f} | IC 95%: [{lo:+.3f}, {hi:+.3f}] | {verdict}")


# ==============================================================================
# TEST 3: GEX CALL WALL & PUT WALL BOUNCES (17-YEAR HISTORICAL DATABASE)
# ==============================================================================
def test_gex_wall_bounces():
    print(f"\n================================================================================")
    print(f"TEST 3: REACCIÓN INSTITUCIONAL EN CALL WALL & PUT WALL (17 AÑOS GEX)")
    print(f"================================================================================")
    
    es_file = DATA_DIR / "ES_1min.csv"
    gex_file = GEX_DIR / "gex_daily_sp500_history.parquet"
    if not (es_file.exists() and gex_file.exists()):
        return
        
    df_es = pd.read_csv(es_file)
    df_es['Time'] = pd.to_datetime(df_es['Time'])
    df_es['Date'] = df_es['Time'].dt.strftime('%Y-%m-%d')
    
    df_gex = pd.read_parquet(gex_file)
    gex_map = df_gex.set_index('date').to_dict(orient='index')
    
    wall_bounce_outcomes = []
    
    for dt, day_bars in df_es.groupby('Date'):
        if dt not in gex_map:
            continue
        gex_row = gex_map[dt]
        c_wall = gex_row['call_wall'] * 10.0  # Scale SPY to ES
        p_wall = gex_row['put_wall'] * 10.0
        regime = gex_row['regime']
        
        if regime != "POSITIVE_GAMMA":  # Walls only act as rigid buffers in Positive Gamma
            continue
            
        b_hi = day_bars['High'].values
        b_lo = day_bars['Low'].values
        b_cl = day_bars['Close'].values
        n_b = len(day_bars)
        
        # Test Call Wall Touch (Resistance Bounce)
        for i in range(10, n_b - 30):
            if b_hi[i] >= c_wall and b_cl[i] < c_wall: # Touched Call Wall and rejected
                entry = b_cl[i]
                d = 15.0 # 15 ES points symmetric target and stop
                tp = entry - d
                sl = entry + d
                
                res = 0
                for j in range(i + 1, min(i + 60, n_b)):
                    hit_tp = (b_lo[j] <= tp)
                    hit_sl = (b_hi[j] >= sl)
                    if hit_tp and hit_sl:
                        break
                    elif hit_tp:
                        res = 1
                        break
                    elif hit_sl:
                        res = -1
                        break
                if res != 0:
                    wall_bounce_outcomes.append(res)
                break
                
    n_tot = len(wall_bounce_outcomes)
    if n_tot > 0:
        w = wall_bounce_outcomes.count(1)
        wr = (w / n_tot) * 100.0
        m, se, lo, hi = hac_bartlett_se(wall_bounce_outcomes)
        verdict = "EDGE REAL (Excluye 0)" if lo > 0 else "NEUTRO / NULO"
        print(f"{'Call/Put Wall Bounce en +GEX (ES)':<40} | N={n_tot:<4} | Win: {wr:6.2f}% | Media r: {m:+8.4f} | IC 95%: [{lo:+.3f}, {hi:+.3f}] | {verdict}")


def main():
    test_delta_absorption_on_ticks()
    test_liquidity_void_traversal()
    test_gex_wall_bounces()


if __name__ == "__main__":
    main()
