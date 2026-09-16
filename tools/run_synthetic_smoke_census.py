"""Reproducible runner for synthetic geometric bands software smoke census.

Validates the revisit episode state machine on a pre-holdout development slice
(NQ 06-26, trade date 2026-06-03) using 10 deterministically placed geometric bands.
NOTE: This is a software sanity and boundary test, NOT structural empirical evidence of HP-007.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.abspath("."))

import numpy as np
import pyarrow.dataset as ds
from collections import Counter

from edgelab.research.void_revisit_episodes import (
    detect_revisit_episodes,
    episode_record,
    RevisitSpec,
)


def run_synthetic_smoke_census() -> dict:
    parquet_path = "data/nt8/NQ_parquet/NQ_06-26_ticks.parquet"
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"Missing required parquet: {parquet_path}")

    dataset = ds.dataset(parquet_path, format="parquet")

    # Session 2026-06-03: 2026-06-02 22:00:00 UTC to 2026-06-03 21:00:00 UTC
    t_start_ns = 1780437600 * 1_000_000_000
    t_end_ns = 1780520400 * 1_000_000_000

    filter_expr = (ds.field("ts_utc_ns") >= t_start_ns) & (ds.field("ts_utc_ns") <= t_end_ns)
    table = dataset.to_table(filter=filter_expr, columns=["ts_utc_ns", "price_ticks", "volume"])
    ts = table["ts_utc_ns"].to_numpy()
    px = table["price_ticks"].to_numpy()
    vol = table["volume"].to_numpy().astype(float)

    n_ticks = len(ts)
    min_px, max_px = int(px.min()), int(px.max())

    spec = RevisitSpec(
        approach_ticks=2,
        rejection_excursion_ticks=8,
        min_away_seconds=60.0,
        min_away_volume=50.0,
        max_episode_seconds=1800.0,
    )

    # 10 deterministically placed geometric bands
    n_bands = 10
    band_width_ticks = 8
    levels = np.linspace(min_px + 50, max_px - 50, n_bands, dtype=int)

    bands_metadata = []
    all_episodes_records = []
    episodes_by_band_and_dir = {}
    time_intervals = []

    for idx, lvl in enumerate(levels, 1):
        band_id = f"BAND_{idx:02d}"
        lower_tick = int(lvl)
        upper_tick = int(lvl + band_width_ticks)
        band_spec = {
            "band_id": band_id,
            "lower_tick": lower_tick,
            "upper_tick": upper_tick,
            "width_ticks": band_width_ticks,
        }
        band_sha256 = hashlib.sha256(json.dumps(band_spec, sort_keys=True).encode()).hexdigest()
        band_spec["band_sha256"] = band_sha256
        bands_metadata.append(band_spec)

        for side in (1, -1):
            dir_label = "LONG" if side == 1 else "SHORT"
            key = f"{band_id}_{dir_label}"
            eps = detect_revisit_episodes(
                ts, px, vol, lower_tick, upper_tick, side=side, spec=spec,
                right_boundary_reason="SESSION_END"
            )
            episodes_by_band_and_dir[key] = len(eps)
            for ep in eps:
                rec = episode_record(ep)
                rec["band_id"] = band_id
                rec["direction"] = dir_label
                all_episodes_records.append(rec)
                t_first = int(ts[rec["first_approach_idx"]])
                term_idx = rec["terminal_idx"] if rec["terminal_idx"] is not None else (n_ticks - 1)
                t_term = int(ts[term_idx])
                time_intervals.append((t_first, t_term, key))

    # Cross-band overlap and concurrency analysis
    total_episodes = len(all_episodes_records)
    # Check simultaneous active intervals
    events = []
    for start_t, end_t, k in time_intervals:
        events.append((start_t, 1))
        events.append((end_t, -1))
    events.sort(key=lambda x: (x[0], -x[1]))

    max_simultaneous = 0
    curr_simultaneous = 0
    for t_ev, delta in events:
        curr_simultaneous += delta
        max_simultaneous = max(max_simultaneous, curr_simultaneous)

    # Overlapping episodes count: episodes that overlap with at least one other band episode
    overlapping_count = 0
    for i in range(len(time_intervals)):
        s_i, e_i, k_i = time_intervals[i]
        has_overlap = False
        for j in range(len(time_intervals)):
            if i == j: continue
            s_j, e_j, k_j = time_intervals[j]
            if max(s_i, s_j) <= min(e_i, e_j):
                has_overlap = True
                break
        if has_overlap:
            overlapping_count += 1

    terminals_counter = Counter(r["terminal"] for r in all_episodes_records)
    stages_counter = Counter(r.get("stage_at_censoring") for r in all_episodes_records if r.get("stage_at_censoring"))

    away_times = [r["elapsed_away_seconds"] for r in all_episodes_records]
    away_vols = [r["volume_away"] for r in all_episodes_records]
    excursions = [r["max_excursion_ticks"] for r in all_episodes_records]

    output_data = {
        "census_type": "SYNTHETIC_GEOMETRIC_BANDS_SOFTWARE_SMOKE_CENSUS",
        "purpose": "Software state machine verification on synthetic geometric bands; NOT empirical HP-007 evidence",
        "dataset": {
            "source_file": parquet_path,
            "contract": "NQ 06-26",
            "session_trade_date": "2026-06-03",
            "ticks_count": n_ticks,
            "price_min_ticks": min_px,
            "price_max_ticks": max_px,
            "spread_ticks": max_px - min_px,
            "holdout_firewall_status": "SEALED_ZERO_READS",
            "max_timestamp_utc": "2026-06-03T21:00:00Z",
        },
        "spec": {
            "approach_ticks": spec.approach_ticks,
            "rejection_excursion_ticks": spec.rejection_excursion_ticks,
            "min_away_seconds": spec.min_away_seconds,
            "min_away_volume": spec.min_away_volume,
            "max_episode_seconds": spec.max_episode_seconds,
            "right_boundary_reason": "SESSION_END",
        },
        "bands": bands_metadata,
        "results": {
            "total_episodes": total_episodes,
            "episodes_by_band_and_direction": episodes_by_band_and_dir,
            "cross_band_dependency": {
                "max_simultaneous_active_episodes": max_simultaneous,
                "episodes_overlapping_other_bands": overlapping_count,
                "episodes_overlapping_pct": round(overlapping_count / max(1, total_episodes) * 100, 2),
                "independent_episodes_warning": "Episodes from different synthetic bands share underlying price action and cannot be treated as statistically independent observations.",
            },
            "terminals_distribution": dict(sorted(terminals_counter.items())),
            "stages_at_censoring_distribution": dict(sorted(stages_counter.items())),
            "metrics": {
                "away_time_seconds": {
                    "median": round(float(np.median(away_times)), 1),
                    "min": round(float(np.min(away_times)), 1),
                    "max": round(float(np.max(away_times)), 1),
                },
                "away_volume_contracts": {
                    "median": round(float(np.median(away_vols)), 1),
                    "min": round(float(np.min(away_vols)), 1),
                    "max": round(float(np.max(away_vols)), 1),
                },
                "max_excursion_ticks": {
                    "median": round(float(np.median(excursions)), 1),
                    "min": int(np.min(excursions)),
                    "max": int(np.max(excursions)),
                },
            },
        },
        "all_episodes": all_episodes_records,
    }

    out_json = "docs/research/SYNTHETIC_GEOMETRIC_BANDS_SMOKE_CENSUS_2026-09-15.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    print(f"Saved machine-readable census JSON: {out_json}")
    return output_data


if __name__ == "__main__":
    res = run_synthetic_smoke_census()
    print("Execution complete. Total episodes:", res["results"]["total_episodes"])
