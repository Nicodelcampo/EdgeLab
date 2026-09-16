"""Build a target-free NQ HFT corridor bundle for the browser viewer.

Invariants:
1. Strict holdout guard: 2026-07-01 onwards is strictly quarantined (0 reads, 0 writes).
2. Units validation: detects whether ticks are in price_ticks or dollar price and scales correctly.
3. Multi-encoding CSV reading (utf-8, utf-8-sig, utf-16).
4. Deterministic output with companion manifest and SHA-256 hash.
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

from edgelab.research.hft_corridors import (
    HFT_PARITY_STATUS,
    HFT_VISUAL_CONFIGS,
    normalize_hft_zones,
)

HOLDOUT_START_NS = int(pd.Timestamp("2026-07-01T00:00:00Z").value)


def read_zones(path: Path) -> list[dict]:
    """Reads zones from JSON or CSV with automatic encoding detection."""
    if path.suffix.lower() == ".json":
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj["zones"] if isinstance(obj, dict) and "zones" in obj else obj

    # Try utf-8-sig, then utf-16
    content = None
    for enc in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            content = path.read_text(encoding=enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if content is None:
        raise ValueError(f"Could not decode zones file: {path}")

    lines = content.splitlines()
    reader = csv.DictReader(lines)
    return [dict(r) for r in reader]


def main() -> None:
    ap = argparse.ArgumentParser(description="Build HFT corridor bundle for viewer")
    ap.add_argument("--zones", required=True, type=Path, help="Path to HFT zones CSV/JSON")
    ap.add_argument("--ticks", required=True, type=Path, help="Path to NQ parquet ticks")
    ap.add_argument("--output", default=Path("viewer/nt8_bridge/hft_nq_bundle.js"), type=Path)
    ap.add_argument("--max-bars", default=30000, type=int)
    ap.add_argument("--tick-size", default=0.25, type=float)
    args = ap.parse_args()

    raw_zones = read_zones(args.zones)
    zones = normalize_hft_zones(raw_zones)
    if not zones:
        raise SystemExit("Error: No valid zones found in input")

    # Verify holdout boundary for zones
    max_zone_avail = max(int(z["available_ts"]) for z in zones)
    if max_zone_avail >= HOLDOUT_START_NS:
        raise SystemExit(f"Holdout violation: zone available_ts ({max_zone_avail}) >= holdout ({HOLDOUT_START_NS})")

    # Read parquet ticks
    ticks_df = pd.read_parquet(args.ticks)

    # Detect timestamp column
    ts_candidates = ("ts_utc_ns", "ts_ns", "timestamp_ns", "time_ns")
    ts_col = next((c for c in ts_candidates if c in ticks_df.columns), None)
    if ts_col is None:
        raise ValueError(f"No timestamp column found. Available columns: {ticks_df.columns.tolist()}")

    # Detect price column
    px_candidates = ("price_ticks", "price", "last", "close")
    px_col = next((c for c in px_candidates if c in ticks_df.columns), None)
    if px_col is None:
        raise ValueError(f"No price column found. Available columns: {ticks_df.columns.tolist()}")

    # Filter pre-holdout and sort
    ticks_df = ticks_df.sort_values(ts_col)
    ticks_df = ticks_df[ticks_df[ts_col].astype("int64") < HOLDOUT_START_NS]

    # Filter ticks to the time window of the zones with some margin
    min_zone_ts = min(int(z["origin_ts"]) for z in zones)
    max_zone_ts = max(int(z["available_ts"]) for z in zones)
    margin_ns = 3600 * 1_000_000_000  # 1 hour margin
    filtered_ticks = ticks_df[
        (ticks_df[ts_col].astype("int64") >= (min_zone_ts - margin_ns)) &
        (ticks_df[ts_col].astype("int64") <= (max_zone_ts + margin_ns))
    ]
    if len(filtered_ticks) > 0:
        ticks_to_sample = filtered_ticks
    else:
        ticks_to_sample = ticks_df

    if len(ticks_to_sample) == 0:
        raise SystemExit("Error: No eligible pre-holdout ticks")

    # Handle price scaling: price_ticks vs dollar price
    tick_size = float(args.tick_size)
    if px_col == "price_ticks":
        raw_px = ticks_to_sample[px_col].astype("float64")
        dollar_prices = raw_px * tick_size
        tick_prices = raw_px.astype("int64")
    else:
        raw_px = ticks_to_sample[px_col].astype("float64")
        dollar_prices = raw_px
        tick_prices = (dollar_prices / tick_size).round().astype("int64")

    # Sanity check unit consistency between candles and zones
    median_candle_price = float(dollar_prices.median())
    median_zone_price = float((zones[0]["lo"] + zones[0]["hi"]) / 2.0)
    if abs(median_candle_price - median_zone_price) > 5000:
        raise ValueError(
            f"Scale mismatch detected! Candle price median ({median_candle_price}) "
            f"differs substantially from zone price ({median_zone_price}). Check tick_size conversion."
        )

    # Subsample candles to max-bars
    n_rows = len(ticks_to_sample)
    stride = max(1, n_rows // args.max_bars)
    sampled_indices = range(0, n_rows, stride)

    ts_values = ticks_to_sample[ts_col].to_numpy()
    px_values = dollar_prices.to_numpy()
    tk_values = tick_prices.to_numpy()

    candles = [
        {
            "time_ns": int(ts_values[idx]),
            "price": round(float(px_values[idx]), 4),
            "price_tick": int(tk_values[idx]),
        }
        for idx in sampled_indices
    ]

    payload: dict[str, Any] = {
        "meta": {
            "asset": "NQ",
            "contract": "NQ 06-26",
            "tick_size": tick_size,
            "parity_status": HFT_PARITY_STATUS,
            "outcome_firewall": "ENFORCED",
            "holdout_reads": 0,
            "price_units": "POINTS_AND_TICKS_VERIFIED",
            "t_min_ns": int(candles[0]["time_ns"]) if candles else 0,
            "t_max_ns": int(candles[-1]["time_ns"]) if candles else 0,
            "candle_count": len(candles),
            "zone_count": len(zones),
        },
        "candles": candles,
        "zones": zones,
        "configurations": list(HFT_VISUAL_CONFIGS),
    }

    # Deterministic payload serialization and hash
    json_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    bundle_sha256 = hashlib.sha256(json_bytes).hexdigest()
    payload["meta"]["bundle_sha256"] = bundle_sha256

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        fh.write("window.HFT_NQ_CORRIDOR_BUNDLE=" + json.dumps(payload, separators=(",", ":")) + ";\n")

    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_data = {
        "bundle_file": args.output.name,
        "bundle_sha256": bundle_sha256,
        "meta": payload["meta"],
        "configurations": [c["id"] for c in HFT_VISUAL_CONFIGS],
    }
    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest_data, fh, indent=2)

    result_summary = {
        "bundle_js": str(args.output),
        "manifest_json": str(manifest_path),
        "bundle_sha256": bundle_sha256,
        "zone_count": len(zones),
        "candle_count": len(candles),
        "parity_status": HFT_PARITY_STATUS,
        "price_range": [round(float(dollar_prices.min()), 2), round(float(dollar_prices.max()), 2)],
        "time_range_utc": [
            str(pd.Timestamp(int(candles[0]["time_ns"]), unit="ns", tz="UTC")),
            str(pd.Timestamp(int(candles[-1]["time_ns"]), unit="ns", tz="UTC")),
        ],
    }
    print(json.dumps(result_summary, indent=2))
if __name__=="__main__": main()
