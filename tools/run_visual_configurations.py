"""Target-free configuration runner and deduplication script for HP007-CAMP-002.

Executes all 9 BigTrap2Absorption configurations on certified sessions of NQ 06-26.
Calculates:
1. zone_stream_sha256: Hash of discrete zone coordinates and events.
2. field_stream_sha256: Hash of discretized intensity field tensors across kernels and ablations.
3. Deduplication report: Collapsing redundant configurations and models into equivalence classes.
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

CONFIG_CATALOG_PATH = Path("docs/research/HP007_CAMP002_BT2A_CONFIG_CATALOG_2026-09-15.json")
SESSION_MANIFEST_PATH = Path("docs/research/HP007_CAMP002_SESSION_SELECTION_MANIFEST_2026-09-15.json")
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


def calculate_field_intensity(
    p: float,
    t_ns: int,
    active_zones: list[dict],
    kernel_type: str,
    sigma_ticks: float,
    vol_trans: str,
    v_ref: float,
    ablation: str,
    tick_size: float
) -> float:
    """Calculates aggregate field intensity F(p, t) in [0, 1) strictly as-of."""
    if not active_zones:
        return 0.0

    exponent_sum = 0.0
    for z in active_zones:
        # Distance to zone in ticks
        z_lo = z["lo"]
        z_hi = z["hi"]
        if p < z_lo:
            d_ticks = (z_lo - p) / tick_size
        elif p > z_hi:
            d_ticks = (p - z_hi) / tick_size
        else:
            d_ticks = 0.0

        # Spatial kernel K(d)
        if kernel_type == "KERNEL_BOX":
            k_val = 1.0 if d_ticks == 0.0 else 0.0
        elif kernel_type.startswith("KERNEL_GAUSS"):
            sigma = max(0.1, sigma_ticks)
            if d_ticks > 3.0 * sigma:
                k_val = 0.0
            else:
                k_val = math.exp(-(d_ticks ** 2) / (2.0 * (sigma ** 2)))
        else:
            k_val = 0.0

        if k_val <= 0.0:
            continue

        # Volume weight w_vol
        z_vol = max(1.0, float(z.get("vol", 1.0)))
        ratio = z_vol / max(1.0, v_ref)
        if vol_trans == "TRANS_COUNT":
            w_vol = 1.0
        elif vol_trans == "TRANS_POWER_025":
            w_vol = ratio ** 0.25
        elif vol_trans == "TRANS_POWER_050":
            w_vol = ratio ** 0.50
        elif vol_trans == "TRANS_LOG":
            w_vol = math.log2(1.0 + ratio)
        elif vol_trans == "TRANS_WINSORIZED":
            w_vol = min(ratio, 3.0) ** 0.25
        else:
            w_vol = 1.0

        # Age in seconds
        z_created_ns = z.get("sig_ts") or (z.get("created_ms", 0) * 1_000_000)
        age_s = max(0.0, (t_ns - z_created_ns) / 1_000_000_000.0)

        # Maturation factor
        if ablation == "NO_MATURATION":
            f_mat = 1.0
        else:
            # Sigmoidal maturation ramping over 30 mins (1800s)
            f_mat = 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, (age_s - 1800.0) / 600.0))))

        # Time decay factor
        if ablation == "NO_TIME_DECAY":
            f_decay = 1.0
        else:
            # Slow exponential decay with half-life of 12 hours after 4h grace period
            decay_age = max(0.0, age_s - 14400.0)
            f_decay = math.exp(-math.log(2.0) * decay_age / 43200.0)

        # Wear attenuation by touches
        if ablation == "NO_WEAR":
            f_wear = 1.0
        else:
            touches = max(0, int(z.get("touches", 0)))
            f_wear = (1.0 + 0.5 * touches) ** -0.6

        w_zone = w_vol * f_mat * f_decay * f_wear
        exponent_sum += w_zone * k_val

    # F(p, t) = 1 - exp(-sum)
    f_val = 1.0 - math.exp(-max(0.0, exponent_sum))
    return round(f_val, 6)


def run_all_configurations() -> dict:
    with open(CONFIG_CATALOG_PATH, "r", encoding="utf-8") as f:
        config_catalog = json.load(f)

    with open(SESSION_MANIFEST_PATH, "r", encoding="utf-8") as f:
        session_manifest = json.load(f)

    source_parquet = session_manifest["asset"]["source_parquet"]
    tick_size = float(session_manifest["asset"]["tick_size"])
    selected_sessions = session_manifest["selected_sessions"]

    # Use unique sessions to avoid redundant tick loads
    unique_session_dates = {}
    for s in selected_sessions:
        td = s["trade_date"]
        if td not in unique_session_dates:
            unique_session_dates[td] = s

    print(f"Loading {len(unique_session_dates)} unique sessions from {source_parquet}...")
    loaded_ticks = {}
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
        print(f"  Session {td}: loaded {len(t_series):,} ticks.")

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
            cfg_session_zones[td] = res["zones"]
            all_zones_for_cfg.extend(res["zones"])
            total_zones_count += res["n_zones"]

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

    # Now evaluate field models on representative baseline (BT2A_CFG_01) on SESS_02 (Median session)
    print("\nEvaluating field models and kernels on median session...")
    median_td = "2026-04-01"
    med_ticks = loaded_ticks[median_td]
    med_zones = config_results["BT2A_CFG_01"]["session_zones"][median_td]

    # Compute rolling median volume as v_ref
    all_vols = [z.get("vol", 1.0) for z in med_zones]
    v_ref = float(np.median(all_vols)) if all_vols else 100.0

    field_models = [
        ("FIELD_BOX", "KERNEL_BOX", 0.0, "TRANS_POWER_025", "FULL"),
        ("FIELD_GAUSS_NARROW", "KERNEL_GAUSS_NARROW", 0.75, "TRANS_POWER_025", "FULL"),
        ("FIELD_GAUSS_BASE", "KERNEL_GAUSS_BASE", 1.20, "TRANS_POWER_025", "FULL"),
        ("FIELD_GAUSS_BROAD", "KERNEL_GAUSS_BROAD", 3.00, "TRANS_POWER_025", "FULL"),
        ("FIELD_TRANS_COUNT", "KERNEL_GAUSS_BASE", 1.20, "TRANS_COUNT", "FULL"),
        ("FIELD_TRANS_POWER050", "KERNEL_GAUSS_BASE", 1.20, "TRANS_POWER_050", "FULL"),
        ("FIELD_TRANS_LOG", "KERNEL_GAUSS_BASE", 1.20, "TRANS_LOG", "FULL"),
        ("FIELD_TRANS_WINSORIZED", "KERNEL_GAUSS_BASE", 1.20, "TRANS_WINSORIZED", "FULL"),
        ("FIELD_ABL_NO_MATURATION", "KERNEL_GAUSS_BASE", 1.20, "TRANS_POWER_025", "NO_MATURATION"),
        ("FIELD_ABL_NO_TIME_DECAY", "KERNEL_GAUSS_BASE", 1.20, "TRANS_POWER_025", "NO_TIME_DECAY"),
        ("FIELD_ABL_NO_WEAR", "KERNEL_GAUSS_BASE", 1.20, "TRANS_POWER_025", "NO_WEAR")
    ]

    # Sample grid evaluation: 50 time steps across the session, 30 price levels per time step
    eval_indices = np.linspace(1000, len(med_ticks) - 1000, 50, dtype=int)
    field_vectors: dict[str, np.ndarray] = {}
    field_hashes: dict[str, str] = {}

    for mod_id, k_type, sig, v_tr, abl in field_models:
        vals = []
        for idx in eval_indices:
            t_ns = int(med_ticks.ts_ns[idx])
            p_center = med_ticks.price(idx)
            # 30 price levels around price center
            p_grid = [p_center + (i * tick_size) for i in range(-15, 15)]

            # Filter zones strictly active as-of at t_ns
            active = []
            for z in med_zones:
                z_start = z.get("sig_ts") or (z.get("created_ms", 0) * 1_000_000)
                z_end = (z.get("ended_ms") * 1_000_000) if z.get("ended_ms") else float("inf")
                if z_start <= t_ns < z_end:
                    active.append(z)

            for p in p_grid:
                f_val = calculate_field_intensity(
                    p, t_ns, active, k_type, sig, v_tr, v_ref, abl, tick_size
                )
                vals.append(f_val)

        arr = np.array(vals, dtype=np.float64)
        field_vectors[mod_id] = arr
        f_hash = hashlib.sha256(arr.tobytes()).hexdigest()
        field_hashes[mod_id] = f_hash
        print(f"  Field model {mod_id:24s}: mean={arr.mean():.4f}, max={arr.max():.4f}, sha256={f_hash[:16]}...")

    # Pairwise correlations among field models
    model_ids = [m[0] for m in field_models]
    corr_matrix = {}
    for m1 in model_ids:
        corr_matrix[m1] = {}
        for m2 in model_ids:
            v1 = field_vectors[m1]
            v2 = field_vectors[m2]
            if np.std(v1) > 1e-6 and np.std(v2) > 1e-6:
                r = float(np.corrcoef(v1, v2)[0, 1])
            else:
                r = 1.0 if np.allclose(v1, v2) else 0.0
            corr_matrix[m1][m2] = round(r, 4)

    # Compile report
    report = {
        "report_version": "hp007_camp002_deduplication_v1",
        "phase": "VISUAL_LOGIC_DESIGN",
        "revisit_hypothesis_measurement": "ON_HOLD_BY_OWNER",
        "asset": "NQ 06-26",
        "sessions_evaluated": list(unique_session_dates.keys()),
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
        "level_2_field_stream_deduplication": {
            "n_field_models_evaluated": len(field_models),
            "n_unique_field_hashes": len(set(field_hashes.values())),
            "field_models_summary": [
                {
                    "model_id": m[0],
                    "kernel": m[1],
                    "sigma_ticks": m[2],
                    "volume_transformation": m[3],
                    "ablation": m[4],
                    "mean_field_intensity": round(float(field_vectors[m[0]].mean()), 4),
                    "max_field_intensity": round(float(field_vectors[m[0]].max()), 4),
                    "field_stream_sha256": field_hashes[m[0]]
                }
                for m in field_models
            ],
            "correlation_matrix": corr_matrix
        },
        "conclusion": {
            "geometric_redundancy_found": len(zone_equiv_classes) < len(configs),
            "field_redundancy_found": len(set(field_hashes.values())) < len(field_models),
            "recommended_representative_visual_package": [
                c["representative_configuration"] for c in [
                    {"representative_configuration": members[0]} for members in zone_equiv_classes.values()
                ]
            ]
        }
    }

    # Hash of this script
    script_path = Path("tools/run_visual_configurations.py")
    if script_path.exists():
        report["runner_script_sha256"] = hashlib.sha256(script_path.read_bytes()).hexdigest()

    DEDUP_REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(DEDUP_REPORT_OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nDeduplication report saved to: {DEDUP_REPORT_OUT}")
    print(f"Level 1 (Zone streams): {len(configs)} configs -> {len(zone_equiv_classes)} unique classes.")
    print(f"Level 2 (Field streams): {len(field_models)} models -> {len(set(field_hashes.values()))} unique classes.")

    return report


if __name__ == "__main__":
    run_all_configurations()
