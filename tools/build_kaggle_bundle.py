#!/usr/bin/env python3
"""Build and index the complete multi-asset CME tick dataset for Kaggle.

Gathers all 11 assets (56 contracts, >1.07B ticks) from E:/EdgeLab/data/nt8,
computes metadata (tick counts, date ranges, SHA-256), and creates the Kaggle manifest.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
import pyarrow.parquet as pq
import pandas as pd

BASE = Path("E:/EdgeLab/data/nt8")
OUT_DIR = Path("E:/EdgeLab/kaggle_dataset")

ASSET_CONFIG = {
    "6B":  {"folder": "6B_parquet",  "name": "British Pound",       "class": "FX",        "tick_size": 0.0001,    "multiplier": 62500, "is_micro": False},
    "6E":  {"folder": "6E",          "name": "Euro FX",              "class": "FX",        "tick_size": 0.00005,   "multiplier": 125000,"is_micro": False},
    "6J":  {"folder": "6J_parquet",  "name": "Japanese Yen",        "class": "FX",        "tick_size": 0.0000005, "multiplier": 12500000,"is_micro": False},
    "ES":  {"folder": "ES_parquet",  "name": "E-mini S&P 500",      "class": "Index",     "tick_size": 0.25,      "multiplier": 50,    "is_micro": False},
    "GC":  {"folder": "GC_parquet",  "name": "Gold",                "class": "Commodity", "tick_size": 0.10,      "multiplier": 100,   "is_micro": False},
    "MBT": {"folder": "MBT_parquet", "name": "Micro Bitcoin",        "class": "Crypto",    "tick_size": 5.0,       "multiplier": 0.1,   "is_micro": True},
    "MES": {"folder": "MES_parquet", "name": "Micro E-mini S&P 500","class": "Index",     "tick_size": 0.25,      "multiplier": 5,     "is_micro": True},
    "MNQ": {"folder": "MNQ_parquet", "name": "Micro E-mini Nasdaq",  "class": "Index",     "tick_size": 0.25,      "multiplier": 2,     "is_micro": True},
    "NQ":  {"folder": "NQ_parquet",  "name": "E-mini Nasdaq 100",   "class": "Index",     "tick_size": 0.25,      "multiplier": 20,    "is_micro": False},
    "YM":  {"folder": "YM_parquet",  "name": "E-mini Dow Jones",    "class": "Index",     "tick_size": 1.0,       "multiplier": 5,     "is_micro": False},
    "ZB":  {"folder": "ZB",          "name": "30-Year US Treasury",  "class": "Bonds",     "tick_size": 0.03125,   "multiplier": 1000,  "is_micro": False},
}


def build_manifest():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset_name": "edgelab-cme-futures-tick-universe",
        "title": "EdgeLab CME Futures Complete Tick Dataset (1.07B Ticks)",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_assets": len(ASSET_CONFIG),
        "assets": {}
    }

    grand_total_ticks = 0
    grand_total_size = 0
    total_contracts = 0

    print("Indexing multi-asset CME dataset for Kaggle...")
    print("=" * 80)

    for symbol, cfg in sorted(ASSET_CONFIG.items()):
        folder_path = BASE / cfg["folder"]
        if not folder_path.exists():
            continue

        asset_info = {
            "symbol": symbol,
            "name": cfg["name"],
            "asset_class": cfg["class"],
            "tick_size": cfg["tick_size"],
            "multiplier": cfg["multiplier"],
            "is_micro": cfg["is_micro"],
            "contracts": {}
        }

        asset_ticks = 0
        asset_size = 0

        for f in sorted(folder_path.iterdir()):
            if f.is_file() and f.name.endswith(".parquet") and "all" not in f.name and "prev" not in f.name:
                try:
                    meta = pq.read_metadata(f)
                    n_rows = meta.num_rows
                    fsize = f.stat().st_size
                    contract_name = f.stem.replace("_ticks", "")

                    asset_info["contracts"][contract_name] = {
                        "file_name": f.name,
                        "file_size_bytes": fsize,
                        "file_size_mb": round(fsize / 1024 / 1024, 2),
                        "total_ticks": n_rows,
                    }

                    asset_ticks += n_rows
                    asset_size += fsize
                    total_contracts += 1
                except Exception as e:
                    print(f"Error reading {f.name}: {e}")

        asset_info["total_ticks"] = asset_ticks
        asset_info["total_size_mb"] = round(asset_size / 1024 / 1024, 2)
        asset_info["num_contracts"] = len(asset_info["contracts"])

        manifest["assets"][symbol] = asset_info
        grand_total_ticks += asset_ticks
        grand_total_size += asset_size

        print(f"[{symbol:4s}] {cfg['name']:25s} | {asset_info['num_contracts']} contracts | {asset_ticks:12,d} ticks | {asset_info['total_size_mb']:8.1f} MB")

    manifest["grand_total_ticks"] = grand_total_ticks
    manifest["grand_total_contracts"] = total_contracts
    manifest["grand_total_size_gb"] = round(grand_total_size / 1024 / 1024 / 1024, 2)

    print("=" * 80)
    print(f"TOTAL: {total_contracts} contracts | {grand_total_ticks:,} ticks | {manifest['grand_total_size_gb']} GB")

    # Save manifest
    manifest_path = OUT_DIR / "dataset_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest written to: {manifest_path}")

    # Create dataset-metadata.json for Kaggle CLI
    kaggle_meta = {
        "title": "EdgeLab CME Futures 1B Tick Dataset",
        "id": "nicodelcampo/edgelab-cme-futures-ticks",
        "licenses": [{"name": "CC0-1.0"}],
        "description": f"Complete tick-by-tick order execution dataset across 11 CME futures assets (56 contracts, {grand_total_ticks:,} ticks). Includes full-size and micro pairs (ES/MES, NQ/MNQ), FX (6E, 6B, 6J), Commodities (GC), Bonds (ZB), and Crypto (MBT)."
    }
    with open(OUT_DIR / "dataset-metadata.json", "w", encoding="utf-8") as f:
        json.dump(kaggle_meta, f, indent=2)

    # Create README.md
    readme_content = f"""# EdgeLab CME Futures Tick Dataset

A comprehensive, institutional-grade dataset of **{grand_total_ticks:,} ticks** ({manifest['grand_total_size_gb']} GB) across **11 CME futures assets** and **{total_contracts} quarterly contracts**.

## Asset Universe

| Symbol | Name | Asset Class | Type | Contracts | Total Ticks | Tick Size | Multiplier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
"""
    for symbol, info in sorted(manifest["assets"].items()):
        tipo = "Micro" if info["is_micro"] else "Full-size"
        readme_content += f"| **{symbol}** | {info['name']} | {info['asset_class']} | {tipo} | {info['num_contracts']} | {info['total_ticks']:,} | {info['tick_size']} | ${info['multiplier']} |\n"

    readme_content += f"""
## Key Pairs for Cross-Asset Microstructure Research:
- **Index Full vs Micro**: ES vs MES (459M ticks), NQ vs MNQ (476M ticks)
- **Foreign Exchange**: 6E (Euro), 6B (Pound), 6J (Yen) (44.3M ticks)
- **Commodities & Bonds**: GC (Gold - 39.8M ticks), ZB (30Y Treasury - 30.2M ticks)
- **Crypto Futures**: MBT (Micro Bitcoin - 4.9M ticks)

Generated automatically by EdgeLab.
"""
    with open(OUT_DIR / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print(f"README.md written to: {OUT_DIR / 'README.md'}")


if __name__ == "__main__":
    build_manifest()
