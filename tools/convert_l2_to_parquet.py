# -*- coding: utf-8 -*-
"""Batch conversion script for CME Level 2 depth CSV files to compressed Parquets.

Usage:
    python tools/convert_l2_to_parquet.py --input-dir "E:\\l2\\6E 09-26" --output-dir "E:\\l2_parquet\\6E_09-26"
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# La raiz del repo tiene que estar en sys.path: el script se invoca desde cualquier cwd
# y sin esto falla con ModuleNotFoundError, que es lo que paso el 2026-08-21.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edgelab.data.l2 import convert_l2_session  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Convert L2 CSV files to Parquet")
    parser.add_argument("--input-dir", type=str, default=r"E:\l2\6E 09-26", help="Input directory with CSV files")
    parser.add_argument("--output-dir", type=str, default=r"E:\l2_parquet\6E_09-26", help="Output directory for Parquet files")
    parser.add_argument("--tick-size", type=float, default=0.00005, help="Instrument tick size")
    args = parser.parse_args()

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(in_dir.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {in_dir}")
        return

    print(f"==================================================")
    print(f"L2/L1 BATCH PARQUET CONVERSION")
    print(f"Found {len(csv_files)} session CSVs in {in_dir}")
    print(f"Target directory: {out_dir}")
    print(f"==================================================\n")

    total_orig_bytes = 0
    total_parq_bytes = 0
    t0 = time.time()

    for i, csv_file in enumerate(csv_files, 1):
        orig_mb = csv_file.stat().st_size / (1024 * 1024)
        total_orig_bytes += csv_file.stat().st_size
        
        print(f"[{i}/{len(csv_files)}] Processing {csv_file.name} ({orig_mb:.1f} MB)... ", end="", flush=True)
        t_file0 = time.time()
        
        p_l2, p_l1 = convert_l2_session(csv_file, out_dir, tick_size=args.tick_size)
        
        l2_mb = p_l2.stat().st_size / (1024 * 1024)
        l1_mb = p_l1.stat().st_size / (1024 * 1024)
        sess_parq_bytes = p_l2.stat().st_size + p_l1.stat().st_size
        total_parq_bytes += sess_parq_bytes
        
        elapsed = time.time() - t_file0
        ratio = (1.0 - (sess_parq_bytes / csv_file.stat().st_size)) * 100
        
        print(f"Done in {elapsed:.1f}s -> L2: {l2_mb:.1f}MB, L1: {l1_mb:.1f}MB (-{ratio:.1f}%)")

    total_time = time.time() - t0
    total_orig_mb = total_orig_bytes / (1024 * 1024)
    total_parq_mb = total_parq_bytes / (1024 * 1024)
    overall_ratio = (1.0 - (total_parq_bytes / total_orig_bytes)) * 100

    print(f"\n==================================================")
    print(f"CONVERSION COMPLETE:")
    print(f"  Total CSV raw size:     {total_orig_mb:.1f} MB")
    print(f"  Total Parquet size:     {total_parq_mb:.1f} MB (-{overall_ratio:.1f}% space saved)")
    print(f"  Total conversion time:  {total_time:.1f} seconds")
    print(f"  Output Parquets in:     {out_dir}")
    print(f"==================================================")


if __name__ == "__main__":
    main()
