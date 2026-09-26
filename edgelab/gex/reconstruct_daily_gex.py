#!/usr/bin/env python3
"""High-performance GEX Daily History Reconstructor (SPY / QQQ -> S&P 500 / Nasdaq)."""

import time
import numpy as np
import pandas as pd
from pathlib import Path

OPTIONS_DIR = Path(r"E:\options_data")
OUTPUT_DIR = Path(r"D:\EdgeLab\data\gex")


def compute_daily_gex_series(parquet_file: Path, symbol: str) -> pd.DataFrame:
    print(f"\n=======================================================")
    print(f"Reconstructing Daily GEX History for {symbol} ({parquet_file.name})")
    print(f"=======================================================")
    
    t0 = time.perf_counter()
    # Read only needed columns for speed and memory efficiency
    cols = ['date', 'strike', 'type', 'open_interest', 'gamma', 'last', 'bid', 'ask']
    df = pd.read_parquet(parquet_file, columns=cols)
    
    df['date'] = pd.to_datetime(df['date'])
    df['open_interest'] = df['open_interest'].fillna(0).astype(np.float64)
    df['gamma'] = df['gamma'].fillna(0).astype(np.float64)
    df['type'] = df['type'].str.upper()
    
    # Filter valid options
    valid = df[(df['open_interest'] > 0) & (df['gamma'] > 0)].copy()
    print(f"Loaded {len(df):,} total rows -> {len(valid):,} active options across {df['date'].nunique()} trading days.")
    
    # Estimate spot price per day (median of strikes with delta near 0.5 or mid-quote of ATM options)
    # Using approx spot from options mid-quote
    mid = (valid['bid'] + valid['ask']) / 2.0
    valid['mid'] = mid.fillna(valid['last'])
    
    # Calculate Dollar GEX per contract: OI * Gamma * Spot * 100 (for 1% move standard convention)
    # Dollar GEX = OI * Gamma * Spot^2 * 0.01 * 100
    # Calls: Positive Gamma Exposure for Dealer
    # Puts: Negative Gamma Exposure for Dealer
    is_call = valid['type'].isin(['C', 'CALL'])
    valid['gex_dollar'] = np.where(
        is_call,
        valid['open_interest'] * valid['gamma'] * 100.0,
        -valid['open_interest'] * valid['gamma'] * 100.0
    )
    
    daily_records = []
    
    for dt, group in valid.groupby('date'):
        # Aggregate by strike
        by_strike = group.groupby('strike')['gex_dollar'].sum()
        calls_by_strike = group[group['type'].isin(['C', 'CALL'])].groupby('strike')['open_interest'].sum()
        puts_by_strike = group[group['type'].isin(['P', 'PUT'])].groupby('strike')['open_interest'].sum()
        
        total_net_gex = float(by_strike.sum())
        regime = "POSITIVE_GAMMA" if total_net_gex > 0 else "NEGATIVE_GAMMA"
        
        # Call Wall = Strike with highest positive call open interest / gamma
        call_wall = float(calls_by_strike.idxmax()) if len(calls_by_strike) > 0 else np.nan
        # Put Wall = Strike with highest put open interest / gamma
        put_wall = float(puts_by_strike.idxmax()) if len(puts_by_strike) > 0 else np.nan
        # Max Net GEX Strike
        abs_wall = float(by_strike.abs().idxmax()) if len(by_strike) > 0 else np.nan
        
        # Estimate Zero Gamma / Flip Level (strike where cumulative GEX crosses 0)
        sorted_strikes = by_strike.sort_index()
        cum_gex = sorted_strikes.cumsum()
        crossings = np.where(np.diff(np.sign(cum_gex)))[0]
        if len(crossings) > 0:
            gamma_flip = float(sorted_strikes.index[crossings[0]])
        else:
            gamma_flip = float(abs_wall)
            
        daily_records.append({
            "date": dt.strftime("%Y-%m-%d"),
            "symbol": symbol,
            "total_net_gex": total_net_gex,
            "regime": regime,
            "call_wall": call_wall,
            "put_wall": put_wall,
            "gamma_flip": gamma_flip,
            "abs_gex_wall": abs_wall,
            "total_contracts": int(group['open_interest'].sum()),
            "n_strikes": int(len(by_strike))
        })
        
    res_df = pd.DataFrame(daily_records)
    res_df = res_df.sort_values('date').reset_index(drop=True)
    
    t1 = time.perf_counter()
    print(f"Processed {len(res_df)} daily GEX records in {t1 - t0:.2f}s.")
    return res_df


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. SPY / S&P 500
    spy_path = OPTIONS_DIR / "SPY_options.parquet"
    if spy_path.exists():
        spy_gex = compute_daily_gex_series(spy_path, "SPY")
        out_spy = OUTPUT_DIR / "gex_daily_sp500_history.parquet"
        spy_gex.to_parquet(out_spy, index=False)
        print(f"Saved: {out_spy} ({len(spy_gex)} days)")
        print(spy_gex.tail(5))
        
    # 2. QQQ / Nasdaq 100
    qqq_path = OPTIONS_DIR / "QQQ_options.parquet"
    if qqq_path.exists():
        qqq_gex = compute_daily_gex_series(qqq_path, "QQQ")
        out_qqq = OUTPUT_DIR / "gex_daily_nasdaq_history.parquet"
        qqq_gex.to_parquet(out_qqq, index=False)
        print(f"Saved: {out_qqq} ({len(qqq_gex)} days)")
        print(qqq_gex.tail(5))


if __name__ == "__main__":
    main()
