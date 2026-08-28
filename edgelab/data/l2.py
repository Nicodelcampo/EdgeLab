# -*- coding: utf-8 -*-
"""L2 Book Depth and L1 Quotes Parser and Feature Extractor for EdgeLab.

Parses unified CME Market-By-Price feed events:
- L2 rows (10 levels of book): L2;side;timestamp;microsecond;operation;level;;price;size
- L1 rows (Top of book quotes): L1;side;timestamp;microsecond;price;size
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


def parse_l2_raw_csv(csv_path: str | Path, tick_size: float = 0.00005) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse raw CSV into (df_l2_depth, df_l1_quotes)."""
    csv_path = Path(csv_path)
    df_raw = pd.read_csv(csv_path, sep=";", header=None, names=list(range(9)), low_memory=False)
    
    # 1. L2 Depth Book updates
    m_l2 = df_raw[0] == "L2"
    df_l2 = df_raw[m_l2][[1, 2, 3, 4, 5, 7, 8]].copy()
    df_l2.columns = ["side", "ts_str", "usec", "operation", "level", "price", "size"]
    df_l2["side"] = df_l2["side"].astype(np.int8)
    df_l2["operation"] = df_l2["operation"].astype(np.int8)
    df_l2["level"] = df_l2["level"].astype(np.int8)
    df_l2["price"] = df_l2["price"].astype(np.float64)
    df_l2["size"] = df_l2["size"].astype(np.int32)
    
    dt2 = pd.to_datetime(df_l2["ts_str"].astype(str), format="%Y%m%d%H%M%S", errors="coerce")
    df_l2["ts_us"] = (dt2.astype("int64") // 1000) + df_l2["usec"]
    df_l2["price_tick"] = np.round(df_l2["price"] / tick_size).astype(np.int32)
    df_l2.drop(columns=["ts_str", "usec"], inplace=True)
    
    # 2. L1 Quotes / Top of Book
    m_l1 = df_raw[0] == "L1"
    df_l1 = df_raw[m_l1][[1, 2, 3, 4, 5]].copy()
    df_l1.columns = ["side", "ts_str", "usec", "price", "size"]
    df_l1["side"] = df_l1["side"].astype(np.int8)
    df_l1["price"] = df_l1["price"].astype(np.float64)
    df_l1["size"] = df_l1["size"].astype(np.int32)
    
    dt1 = pd.to_datetime(df_l1["ts_str"].astype(str), format="%Y%m%d%H%M%S", errors="coerce")
    df_l1["ts_us"] = (dt1.astype("int64") // 1000) + df_l1["usec"]
    df_l1["price_tick"] = np.round(df_l1["price"] / tick_size).astype(np.int32)
    df_l1.drop(columns=["ts_str", "usec"], inplace=True)
    
    return df_l2, df_l1


def convert_l2_session(csv_path: str | Path, out_dir: str | Path, tick_size: float = 0.00005) -> tuple[Path, Path]:
    """Convert an L2 raw CSV into compressed L2 and L1 Parquet files."""
    csv_path = Path(csv_path)
    out_dir = Path(out_dir)
    session_name = csv_path.stem
    
    dir_l2 = out_dir / "l2_depth"
    dir_l1 = out_dir / "l1_quotes"
    dir_l2.mkdir(parents=True, exist_ok=True)
    dir_l1.mkdir(parents=True, exist_ok=True)
    
    df_l2, df_l1 = parse_l2_raw_csv(csv_path, tick_size=tick_size)
    
    p_l2 = dir_l2 / f"{session_name}.parquet"
    p_l1 = dir_l1 / f"{session_name}.parquet"
    
    t_l2 = pa.Table.from_pandas(df_l2, preserve_index=False)
    pq.write_table(t_l2, p_l2, compression="zstd", compression_level=7)
    
    t_l1 = pa.Table.from_pandas(df_l1, preserve_index=False)
    pq.write_table(t_l1, p_l1, compression="zstd", compression_level=7)
    
    return p_l2, p_l1
