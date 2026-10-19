"""Build a target-free NQ HFT corridor bundle.

The builder fails before decoding parquet data unless every row group proves,
through physical statistics, that it ends before the canonical holdout boundary.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pandas as pd
import pyarrow.parquet as pq

from edgelab.research.hft_corridors import HFT_PARITY_STATUS, HFT_VISUAL_CONFIGS, normalize_hft_zones

HOLDOUT_START_NS = 1_782_856_800_000_000_000  # 2026-06-30T22:00:00Z


def read_zones(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj["zones"] if isinstance(obj, dict) and "zones" in obj else obj
    content = None
    for encoding in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            content = path.read_text(encoding=encoding)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if content is None:
        raise ValueError(f"Could not decode zones file: {path}")
    return [dict(row) for row in csv.DictReader(content.splitlines())]


def parquet_preflight(path: Path) -> tuple[pq.ParquetFile, str, str]:
    """Prove physical pre-holdout custody before any row is decoded."""
    parquet = pq.ParquetFile(path)
    names = parquet.schema_arrow.names
    ts_col = next((name for name in ("ts_utc_ns", "ts_ns", "timestamp_ns", "time_ns") if name in names), None)
    px_col = next((name for name in ("price_ticks", "price", "last", "close") if name in names), None)
    if ts_col is None:
        raise ValueError(f"No timestamp column found. Available columns: {names}")
    if px_col is None:
        raise ValueError(f"No price column found. Available columns: {names}")
    ts_index = names.index(ts_col)
    for row_group_index in range(parquet.metadata.num_row_groups):
        column = parquet.metadata.row_group(row_group_index).column(ts_index)
        stats = column.statistics
        if stats is None or not stats.has_min_max or stats.max is None:
            raise ValueError(f"Row group {row_group_index} lacks timestamp min/max; zero-holdout-read proof unavailable")
        if int(stats.max) >= HOLDOUT_START_NS:
            raise ValueError(
                f"Holdout gate failed before decode: row group {row_group_index} "
                f"max({ts_col})={int(stats.max)} >= {HOLDOUT_START_NS}"
            )
    return parquet, ts_col, px_col


def main() -> None:
    parser = argparse.ArgumentParser(description="Build HFT corridor bundle for viewer")
    parser.add_argument("--zones", required=True, type=Path)
    parser.add_argument("--ticks", required=True, type=Path)
    parser.add_argument("--zone-mode", choices=("V2", "V1_LEGACY"), default="V2")
    parser.add_argument("--output", default=Path("viewer/nt8_bridge/hft_nq_bundle.js"), type=Path)
    parser.add_argument("--max-bars", default=30000, type=int)
    parser.add_argument("--tick-size", default=0.25, type=float)
    args = parser.parse_args()

    raw_zones = read_zones(args.zones)
    zones = normalize_hft_zones(raw_zones, mode=args.zone_mode)
    if not zones:
        raise SystemExit("No valid zones found in input")
    if max(int(zone["available_ts"]) for zone in zones) >= HOLDOUT_START_NS:
        raise SystemExit("Holdout violation in zone availability")
    contracts = sorted({zone["contract"] for zone in zones})
    if len(contracts) != 1:
        raise SystemExit(f"Bundle requires exactly one contract, found: {contracts}")

    _, ts_col, px_col = parquet_preflight(args.ticks)
    # Safe only after every row group passed the physical gate above.
    table = pq.read_table(args.ticks, columns=[ts_col, px_col])
    ticks = table.to_pandas()
    if ticks.empty:
        raise SystemExit("No eligible pre-holdout ticks")
    ticks = ticks.sort_values(ts_col, kind="mergesort")
    if int(ticks[ts_col].max()) >= HOLDOUT_START_NS:
        raise RuntimeError("Parquet statistics disagreed with decoded timestamps")

    min_zone_ts = min(int(zone["origin_ts"]) for zone in zones)
    max_zone_ts = max(int(zone["available_ts"]) for zone in zones)
    margin_ns = 3_600_000_000_000
    selected = ticks[(ticks[ts_col].astype("int64") >= min_zone_ts - margin_ns) & (ticks[ts_col].astype("int64") <= max_zone_ts + margin_ns)]
    if selected.empty:
        raise SystemExit("No ticks overlap the causal zone window")

    tick_size = float(args.tick_size)
    if px_col == "price_ticks":
        raw_price = selected[px_col].astype("float64")
        prices = raw_price * tick_size
        price_ticks = raw_price.astype("int64")
    else:
        prices = selected[px_col].astype("float64")
        price_ticks = (prices / tick_size).round().astype("int64")

    zone_midpoints = [(zone["lo"] + zone["hi"]) / 2.0 for zone in zones]
    if abs(float(prices.median()) - float(pd.Series(zone_midpoints).median())) > 5000:
        raise ValueError("Scale mismatch between tick prices and zone prices")

    stride = max(1, len(selected) // args.max_bars)
    indices = range(0, len(selected), stride)
    ts_values = selected[ts_col].to_numpy()
    price_values = prices.to_numpy()
    tick_values = price_ticks.to_numpy()
    candles = [
        {"time_ns": int(ts_values[index]), "price": round(float(price_values[index]), 4), "price_tick": int(tick_values[index])}
        for index in indices
    ]

    payload: dict[str, Any] = {
        "meta": {
            "asset": "NQ",
            "contract": contracts[0],
            "tick_size": tick_size,
            "zone_mode": args.zone_mode,
            "parity_status": HFT_PARITY_STATUS if args.zone_mode == "V2" else "LEGACY_DIAGNOSTIC_NOT_CERTIFIED",
            "outcome_firewall": "ENFORCED",
            "holdout_boundary_ns": HOLDOUT_START_NS,
            "holdout_rows_decoded": 0,
            "t_min_ns": int(candles[0]["time_ns"]),
            "t_max_ns": int(candles[-1]["time_ns"]),
            "candle_count": len(candles),
            "zone_count": len(zones),
        },
        "candles": candles,
        "zones": zones,
        "configurations": list(HFT_VISUAL_CONFIGS),
    }
    canonical = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    bundle_sha256 = hashlib.sha256(canonical).hexdigest()
    payload["meta"]["bundle_sha256"] = bundle_sha256

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("window.HFT_NQ_CORRIDOR_BUNDLE=" + json.dumps(payload, separators=(",", ":")) + ";\n", encoding="utf-8")
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest = {"bundle_file": args.output.name, "bundle_sha256": bundle_sha256, "meta": payload["meta"], "configurations": [cfg["id"] for cfg in HFT_VISUAL_CONFIGS]}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"bundle_js": str(args.output), "manifest_json": str(manifest_path), "bundle_sha256": bundle_sha256, "zone_count": len(zones), "candle_count": len(candles), "parity_status": payload["meta"]["parity_status"]}, indent=2))


if __name__ == "__main__":
    main()
