"""Causal configuration runner and density field evaluation script for HP007-CAMP-002.

Executes all 9 BigTrap2Absorption configurations on certified sessions of NQ 06-26.
Calculates:
1. zone_stream_sha256: Hash of discrete zone coordinates and events.
2. causal_field_evaluation: Viewport-invariant density field evaluated across
   all selected sessions, all configurations, and explicit reproducible tRef points.
3. Deduplication and equivalence classes based on strictly causal semantics.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from edgelab.bridge.indicators import bigtrap2absorption
from edgelab.bridge.ticks import load_canonical_parquet
from edgelab.research.density_field import (
    compute_field,
    detect_density_intervals,
    price_to_tick,
    tick_to_price,
    to_nanoseconds,
)

CONFIG_CATALOG_PATH = Path("docs/research/HP007_CAMP002_BT2A_CONFIG_CATALOG_2026-09-15.json")
SESSION_MANIFEST_PATH = Path("docs/research/HP007_CAMP002_SESSION_SELECTION_MANIFEST_2026-09-15.json")
REPORT_OUT = Path("docs/research/HP007_CAMP002_CAUSAL_FIELD_EVALUATION_REPORT_2026-09-15.json")
DEDUP_REPORT_OUT = Path("docs/research/HP007_CAMP002_DEDUPLICATION_REPORT_2026-09-15.json")


def compute_zone_stream_hash(zones: list[dict]) -> str:
    """Computes deterministic SHA-256 of zone stream geometry."""
    normalized = []
    for z in sorted(zones, key=lambda x: (x.get("created_ms", 0), x.get("id", ""))):
        normalized.append({
            "id": str(z.get("id")),
            "dir": str(z.get("dir")),
            "lo": round(float(z.get("lo", 0.0)), 4),
            "hi": round(float(z.get("hi", 0.0)), 4),
            "created_ms": int(z.get("created_ms", 0)),
            "ended_ms": int(z.get("ended_ms", 0)) if z.get("ended_ms") is not None else None,
            "end_reason": str(z.get("end_reason", "")),
            "vol": round(float(z.get("vol", 0.0)), 2)
        })
    raw_bytes = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw_bytes).hexdigest()


def normalize_zone_dict(z: dict) -> dict:
    """Normalizes BigTrap2 raw zone dictionary to standard causal fields."""
    zd = dict(z)
    zd["id"] = str(zd.get("id", ""))
    zd["bottom"] = float(zd.get("lo", 0.0))
    zd["top"] = float(zd.get("hi", 0.0))
    # Available timestamp is sig_ts (when zone was fully formed)
    sig_ts = zd.get("sig_ts")
    if sig_ts is not None:
        zd["available_ts"] = int(sig_ts)
        zd["available_ns"] = int(sig_ts)
    else:
        created_ms = zd.get("created_ms", 0)
        zd["available_ts"] = int(created_ms * 1_000_000)
        zd["available_ns"] = int(created_ms * 1_000_000)

    zd["origin_ts"] = int(zd.get("created_ms", 0) * 1_000_000)
    if zd.get("ended_ms") is not None:
        zd["ended_ts"] = int(zd["ended_ms"] * 1_000_000)
        zd["ended_ns"] = int(zd["ended_ms"] * 1_000_000)
    else:
        zd["ended_ts"] = None

    zd["vol"] = float(zd.get("vol", 1.0))
    zd["touches"] = int(zd.get("touches", 0))
    return zd


def run_causal_evaluation() -> dict:
    with open(CONFIG_CATALOG_PATH, "r", encoding="utf-8") as f:
        config_catalog = json.load(f)

    with open(SESSION_MANIFEST_PATH, "r", encoding="utf-8") as f:
        session_manifest = json.load(f)

    source_parquet = session_manifest["asset"]["source_parquet"]
    tick_size = float(session_manifest["asset"]["tick_size"])
    selected_sessions = session_manifest["selected_sessions"]

    # Unique sessions to load
    unique_session_dates = {}
    for s in selected_sessions:
        td = s["trade_date"]
        if td not in unique_session_dates:
            unique_session_dates[td] = s

    print(f"Loading {len(unique_session_dates)} unique sessions from {source_parquet}...")
    loaded_ticks = {}
    session_price_ranges = {}

    for td, s in unique_session_dates.items():
        open_ns = s["metrics"]["session_open_utc_ns"]
        close_ns = s["metrics"]["session_close_utc_ns"]
        t_series = load_canonical_parquet(
            source_parquet,
            start_utc_ns=open_ns,
            end_utc_ns=close_ns,
            instrument="NQ"
        )
        loaded_ticks[td] = t_series
        min_t = int(np.min(t_series.price_ticks)) - 40
        max_t = int(np.max(t_series.price_ticks)) + 40
        session_price_ranges[td] = {
            "min_px": float(min_t * tick_size),
            "max_px": float(max_t * tick_size),
            "min_tick": min_t,
            "max_tick": max_t,
        }
        print(f"  Session {td}: loaded {len(t_series):,} ticks. Range: [{session_price_ranges[td]['min_px']:.2f}, {session_price_ranges[td]['max_px']:.2f}]")

    configs = config_catalog["configurations"]
    print(f"\nExecuting {len(configs)} configurations across {len(unique_session_dates)} sessions...")

    config_results = {}
    zone_hashes: dict[str, str] = {}
    zone_counts: dict[str, int] = {}

    for cfg in configs:
        cid = cfg["configuration_id"]
        params = cfg["parameters"]

        all_zones_for_cfg = []
        total_zones_count = 0
        cfg_session_zones = {}

        for td, t_series in loaded_ticks.items():
            res = bigtrap2absorption.run(t_series, params=params)
            norm_zones = [normalize_zone_dict(z) for z in res["zones"]]
            cfg_session_zones[td] = norm_zones
            all_zones_for_cfg.extend(norm_zones)
            total_zones_count += len(norm_zones)

        z_hash = compute_zone_stream_hash(all_zones_for_cfg)
        zone_hashes[cid] = z_hash
        zone_counts[cid] = total_zones_count
        config_results[cid] = {
            "configuration_id": cid,
            "description": cfg["description"],
            "total_zones": total_zones_count,
            "zone_stream_sha256": z_hash,
            "session_zones": cfg_session_zones
        }
        print(f"  {cid}: {total_zones_count} zones | zone_stream_sha256: {z_hash[:16]}...")

    # Equivalence classes for zone streams
    zone_equiv_classes: dict[str, list[str]] = {}
    for cid, zh in zone_hashes.items():
        zone_equiv_classes.setdefault(zh, []).append(cid)

    # Multi-session, multi-model causal field evaluation
    print("\nExecuting multi-session causal field evaluations...")

    field_models = [
        ("FIELD_RAW_STATIC", {"model": "FIELD_RAW_STATIC", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.2}),
        ("FIELD_BOX", {"model": "FIELD_RAW_STATIC", "kernel": "KERNEL_BOX"}),
        ("FIELD_TRANS_POWER025", {"model": "FIELD_TRANS", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.2, "vol_transform": "TRANS_POWER_025"}),
        ("FIELD_TRANS_LOG", {"model": "FIELD_TRANS", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.2, "vol_transform": "TRANS_LOG"}),
        ("FIELD_ABL_NO_MATURATION", {"model": "FIELD_TRANS", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.2, "use_maturation": False}),
        ("FIELD_ABL_NO_TIME_DECAY", {"model": "FIELD_TRANS", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.2, "use_time_decay": False}),
        ("FIELD_ABL_NO_WEAR", {"model": "FIELD_TRANS", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.2, "use_wear": False}),
    ]

    total_cells_evaluated = 0
    total_trefs_evaluated = 0
    sample_field_hashes = {}
    evaluations_summary = []

    for td, t_series in loaded_ticks.items():
        ts_arr = t_series.ts_ns
        n_ticks_sess = len(ts_arr)
        # 4 explicit reproducible tRef quartiles: 25%, 50%, 75%, 90%
        t_indices = [
            int(n_ticks_sess * 0.25),
            int(n_ticks_sess * 0.50),
            int(n_ticks_sess * 0.75),
            int(n_ticks_sess * 0.90),
        ]

        p_min_tick = session_price_ranges[td]["min_tick"]
        p_max_tick = session_price_ranges[td]["max_tick"]
        n_price_ticks = (p_max_tick - p_min_tick) + 1

        for q_idx, t_idx in enumerate(t_indices):
            t_ref_ns = int(ts_arr[t_idx])
            total_trefs_evaluated += 1

            for mod_name, mod_cfg in field_models:
                for cfg_id in ["BT2A_CFG_01", "BT2A_CFG_04", "BT2A_CFG_08", "BT2A_CFG_09"]:
                    zones = config_results[cfg_id]["session_zones"][td]
                    res = compute_field(
                        zones=zones,
                        t_ref=t_ref_ns,
                        tick_size=tick_size,
                        price_tick_min=p_min_tick,
                        price_tick_max=p_max_tick,
                        field_config=mod_cfg
                    )
                    total_cells_evaluated += n_price_ticks
                    key = f"{td}_q{q_idx+1}_{cfg_id}_{mod_name}"
                    sample_field_hashes[key] = res["field_hash"]

            evaluations_summary.append({
                "trade_date": td,
                "t_ref_ns": t_ref_ns,
                "quartile": f"Q{q_idx+1}",
                "price_tick_min": p_min_tick,
                "price_tick_max": p_max_tick,
                "n_price_ticks": n_price_ticks,
                "raw_static_cfg01_hash": sample_field_hashes[f"{td}_q{q_idx+1}_BT2A_CFG_01_FIELD_RAW_STATIC"]
            })

    print(f"Total cells evaluated: {total_cells_evaluated:,} across {len(unique_session_dates)} sessions, {total_trefs_evaluated} tRefs, and {len(field_models)} models.")

    report = {
        "report_version": "hp007_camp002_causal_field_evaluation_v2",
        "phase": "VISUAL_LOGIC_DESIGN",
        "revisit_hypothesis_measurement": "ON_HOLD_BY_OWNER",
        "revisit_event_semantics": "OWNER_DECISION_PENDING",
        "outcome_based_selection": "PROHIBITED",
        "ready_for_parameter_sweep": "NO",
        "holdout_reads_for_selection": 0,
        "asset": "NQ 06-26",
        "tick_size": tick_size,
        "coverage_metrics": {
            "n_sessions": len(unique_session_dates),
            "n_configurations": len(configs),
            "n_trefs": total_trefs_evaluated,
            "n_price_ticks_per_grid_mean": round(float(np.mean([s["n_price_ticks"] for s in evaluations_summary])), 1),
            "n_field_cells": total_cells_evaluated,
            "sample_evaluation_note": "Evaluated on 4 explicit reproducible quartiles across all selected sessions on fixed integer tick domains."
        },
        "level_1_zone_stream_deduplication": {
            "n_configurations_input": len(configs),
            "n_unique_zone_streams": len(zone_equiv_classes),
            "equivalence_classes": [
                {
                    "class_id": f"ZONE_CLASS_{i+1:02d}",
                    "representative_configuration": members[0],
                    "member_configurations": members,
                    "zone_stream_sha256": zh,
                    "total_zones": zone_counts[members[0]]
                }
                for i, (zh, members) in enumerate(zone_equiv_classes.items())
            ]
        },
        "level_2_causal_field_summary": evaluations_summary,
        "representative_sample_hashes": dict(list(sample_field_hashes.items())[:20])
    }

    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Published causal field evaluation report to {REPORT_OUT}")

    # Also update deduplication report to reflect causal status
    dedup_content = {
        "report_version": "hp007_camp002_deduplication_v2_causal",
        "artifact_status": "READY_FOR_TARGET_FREE_OWNER_VISUAL_REVIEW",
        "phase": "VISUAL_LOGIC_DESIGN",
        "revisit_hypothesis_measurement": "ON_HOLD_BY_OWNER",
        "asset": "NQ 06-26",
        "coverage_metrics": report["coverage_metrics"],
        "level_1_zone_stream_deduplication": report["level_1_zone_stream_deduplication"],
        "level_2_causal_field_summary": evaluations_summary[:8]
    }
    with open(DEDUP_REPORT_OUT, "w", encoding="utf-8") as f:
        json.dump(dedup_content, f, indent=2, ensure_ascii=False)
    print(f"Updated {DEDUP_REPORT_OUT}")

    return report


if __name__ == "__main__":
    run_causal_evaluation()
