#!/usr/bin/env python3
"""Downloads canonical historical options chains and computes daily GEX history (SPY / QQQ)."""

import os
import sys
import urllib.request
import numpy as np
import pandas as pd
from pathlib import Path

DATA_DIR = Path(r"E:\options_data")
OUTPUT_DIR = Path(r"D:\EdgeLab\data\gex")

URLS = {
    "SPY": "https://github.com/lambdaclass/options_backtester/releases/download/data-v1/SPY_options.parquet",
    "QQQ": "https://github.com/lambdaclass/options_backtester/releases/download/data-v1/QQQ_options.parquet",
}


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 100_000_000:
        print(f"File already exists: {dest} ({dest.stat().st_size / (1024*1024):.1f} MB)")
        return
        
    print(f"Downloading {url} -> {dest} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as out_file:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 1024 * 4  # 4MB chunks
        
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = downloaded / total * 100
                print(f"\rDownloaded {downloaded / (1024*1024):.1f} / {total / (1024*1024):.1f} MB ({pct:.1f}%)", end="", flush=True)
    print("\nDownload complete.")


def inspect_and_process_gex(symbol: str, parquet_path: Path) -> pd.DataFrame:
    print(f"\n--- Processing GEX History for {symbol} ---")
    df = pd.read_parquet(parquet_path)
    print(f"Loaded {len(df):,} rows. Columns: {list(df.columns)}")
    print(df.head(3))
    
    # Identify key columns (date, strike, type, open_interest, gamma/delta, underlying_price)
    date_col = next((c for c in df.columns if "date" in c.lower() or "quote_date" in c.lower() or "time" in c.lower()), None)
    strike_col = next((c for c in df.columns if "strike" in c.lower()), None)
    type_col = next((c for c in df.columns if "type" in c.lower() or "call_put" in c.lower() or "cp" in c.lower()), None)
    oi_col = next((c for c in df.columns if "open_interest" in c.lower() or "oi" in c.lower()), None)
    gamma_col = next((c for c in df.columns if "gamma" in c.lower()), None)
    
    print(f"Mapped columns -> Date: {date_col}, Strike: {strike_col}, Type: {type_col}, OI: {oi_col}, Gamma: {gamma_col}")
    return df


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Download SPY Options
    spy_path = DATA_DIR / "SPY_options.parquet"
    download_file(URLS["SPY"], spy_path)
    
    # 2. Inspect SPY
    inspect_and_process_gex("SPY", spy_path)


if __name__ == "__main__":
    main()
