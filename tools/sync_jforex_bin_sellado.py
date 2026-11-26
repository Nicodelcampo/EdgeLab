#!/usr/bin/env python3
"""Merge JForex4 E:\\dukascopy_HOLDOUT_SELLADO\\<INST>\\ticks\\2026-11-16..*.bin into C:\\EdgeLab\\sellado."""
import glob
import sys
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, r"E:\EdgeLab-fundedsync\tools")
from dukascopy_descarga import leer_jforex_bin  # noqa: E402

SELLADO = Path(r"C:\EdgeLab\sellado")
JF_HOL = Path(r"E:\dukascopy_HOLDOUT_SELLADO")
SCHEMA = pa.schema([
    ("time_utc_ns", pa.int64()),
    ("bid", pa.float64()),
    ("ask", pa.float64()),
    ("bid_vol", pa.float64()),
    ("ask_vol", pa.float64()),
])

for sym in ("USATECHIDXUSD", "USA500IDXUSD", "XAUUSD"):
    tdir = JF_HOL / sym / "ticks"
    bins = sorted(p for p in tdir.glob("2026-11-*.bin") if p.stem >= "2026-11-16")
    if not bins:
        print(f"[SKIP] No .bin >= 2026-11-16 found in {tdir}")
        continue
    dest = SELLADO / f"{sym}_ticks.parquet"
    old = pd.read_parquet(dest)
    n_old = len(old)
    parts = [old] + [leer_jforex_bin(b) for b in bins]
    df = pd.concat(parts, ignore_index=True)
    df["time_utc_ns"] = df["time_utc_ns"].astype("int64")
    for c in ("bid", "ask", "bid_vol", "ask_vol"):
        df[c] = df[c].astype("float64")
    df = df.drop_duplicates(subset=["time_utc_ns"]).sort_values("time_utc_ns", kind="stable").reset_index(drop=True)
    mx = pd.Timestamp(int(df["time_utc_ns"].max()), unit="ns", tz="UTC")
    tmp = dest.with_suffix(".tmp")
    pq.write_table(pa.Table.from_pandas(df[SCHEMA.names], schema=SCHEMA, preserve_index=False), tmp, compression="zstd")
    tmp.replace(dest)
    print(f"[OK] {sym}: {len(bins)} bin files merged | {n_old:,} -> {len(df):,} rows | max_utc={mx}")
