"""HFTZonesNQ -> causal liquidity-density integration.

Target-free by construction: this module never reads future returns, trades,
P&L, MAE/MFE, targets, stops, or holdout data. A HFT zone becomes available
only when the detector has completed it (end_ts), never at its origin.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Iterable

import numpy as np

from edgelab.research.density_field import compute_field, detect_density_intervals, price_to_tick, to_nanoseconds

HFT_PARITY_STATUS = "PROVISIONAL_NEAR_EXACT_BLOCKED_BY_SHARED_INPUT_V2_EXPORT"

HFT_VISUAL_CONFIGS: tuple[dict[str, Any], ...] = (
    {"id": "HFT_RAW_GAUSS_1", "model": "FIELD_RAW_STATIC", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.0},
    {"id": "HFT_RAW_GAUSS_2", "model": "FIELD_RAW_STATIC", "kernel": "KERNEL_GAUSS", "sigma_ticks": 2.0},
    {"id": "HFT_RAW_GAUSS_4", "model": "FIELD_RAW_STATIC", "kernel": "KERNEL_GAUSS", "sigma_ticks": 4.0},
    {"id": "HFT_RAW_BOX", "model": "FIELD_RAW_STATIC", "kernel": "KERNEL_BOX", "sigma_ticks": 1.0},
    {"id": "HFT_VOL025_GAUSS_2", "model": "FIELD_TRANS", "kernel": "KERNEL_GAUSS", "sigma_ticks": 2.0, "vol_transform": "TRANS_POWER_025"},
    {"id": "HFT_LOGVOL_GAUSS_2", "model": "FIELD_TRANS", "kernel": "KERNEL_GAUSS", "sigma_ticks": 2.0, "vol_transform": "TRANS_LOG"},
)


def _first(row: dict, *keys: str) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def normalize_hft_zone(row: dict, *, strict: bool = True) -> dict:
    """Map V1/V2 HFT zone exports to the density-field contract."""
    lo = _first(row, "lo", "bottom", "price_low")
    hi = _first(row, "hi", "top", "price_high")
    end = _first(row, "end_ts_ns", "available_ts_ns", "end_ns", "end_ms")
    start = _first(row, "start_ts_ns", "origin_ts_ns", "start_ns", "start_ms")
    if lo is None or hi is None or end is None:
        raise ValueError("HFT zone requires lo/hi and detector completion timestamp")
    if strict and start is None:
        raise ValueError("HFT zone requires origin timestamp")

    end_key = next(k for k in ("end_ts_ns", "available_ts_ns", "end_ns", "end_ms") if row.get(k) not in (None, ""))
    start_key = next((k for k in ("start_ts_ns", "origin_ts_ns", "start_ns", "start_ms") if row.get(k) not in (None, "")), None)
    available_ns = int(end) * 1_000_000 if end_key == "end_ms" else to_nanoseconds(int(end))
    origin_ns = (int(start) * 1_000_000 if start_key == "start_ms" else to_nanoseconds(int(start))) if start is not None else available_ns
    if available_ns < origin_ns:
        raise ValueError("HFT completion precedes origin")

    seq = _first(row, "zone_seq", "id")
    session_id = str(_first(row, "session_id", "session") or "LEGACY_SESSION_UNKNOWN")
    contract = str(_first(row, "contract", "instrument") or "NQ_UNKNOWN")
    direction = int(_first(row, "dir", "direction") or 0)
    zid = f"{contract}:{session_id}:{seq if seq is not None else origin_ns}:{direction}"
    return {
        "id": zid, "source": "HFTZonesNQPureV4",
        "lo": float(min(float(lo), float(hi))), "hi": float(max(float(lo), float(hi))),
        "origin_ts": origin_ns, "available_ts": available_ns,
        "available_ts_source": "V2_END_NS" if end_key != "end_ms" else "V1_END_MS_DERIVED",
        "vol": float(_first(row, "vol", "volume") or 1.0), "direction": direction,
        "session_id": session_id, "contract": contract,
        "zone_seq": int(seq) if seq is not None else None,
        "parity_status": HFT_PARITY_STATUS,
    }


def normalize_hft_zones(rows: Iterable[dict], *, strict: bool = True) -> list[dict]:
    zones = [normalize_hft_zone(dict(r), strict=strict) for r in rows]
    zones.sort(key=lambda z: (z["available_ts"], z["origin_ts"], z["id"]))
    return zones


def causal_domain(price_ticks: Iterable[int], timestamps_ns: Iterable[int], t_ref_ns: int, zones: Iterable[dict], tick_size: float, margin_ticks: int = 20) -> tuple[int, int]:
    past_prices = [int(p) for p, ts in zip(price_ticks, timestamps_ns) if int(ts) <= int(t_ref_ns)]
    zone_ticks: list[int] = []
    for z in zones:
        if int(z["available_ts"]) <= int(t_ref_ns):
            zone_ticks.extend((price_to_tick(float(z["lo"]), tick_size), price_to_tick(float(z["hi"]), tick_size)))
    values = past_prices + zone_ticks
    if not values:
        raise ValueError("No causally available prices or zones at t_ref")
    return min(values) - margin_ticks, max(values) + margin_ticks


def _quantile_intervals(field: dict, tick_size: float, low_q: float = 0.25, high_q: float = 0.80) -> dict:
    d = np.asarray(field["density"], dtype=float)
    positive = d[d > 0]
    if positive.size == 0:
        return {"low_density_intervals": [], "high_density_regions": [], "low_threshold": 0.0, "high_threshold": 0.0}
    low, high = float(np.quantile(positive, low_q)), float(np.quantile(positive, high_q))
    result = detect_density_intervals(field["density"], field["price_ticks"], tick_size, low_thresh=low, high_thresh=high)
    result.update({"low_threshold": low, "high_threshold": high})
    return result


def evaluate_visual_configurations(zones: list[dict], t_refs: list[int], tick_size: float, domains: dict[int, tuple[int, int]]) -> dict:
    """Rank configs by target-free visual quality, never by outcomes."""
    rows: list[dict] = []
    for cfg in HFT_VISUAL_CONFIGS:
        fields = []
        for t_ref in sorted(t_refs):
            pmin, pmax = domains[t_ref]
            field = compute_field(zones, t_ref, tick_size, pmin, pmax, cfg)
            d = np.asarray(field["density"], dtype=float)
            positive_fraction = float(np.mean(d > 0))
            cv = float(np.std(d) / np.mean(d)) if float(np.mean(d)) > 0 else 0.0
            intervals = _quantile_intervals(field, tick_size)
            fields.append({"field": field, "positive_fraction": positive_fraction, "cv": cv, "n_high": len(intervals["high_density_regions"]), "n_low": len(intervals["low_density_intervals"])})
        coverage = float(np.median([f["positive_fraction"] for f in fields]))
        dynamic = float(np.median([f["cv"] for f in fields]))
        fragmentation = float(np.median([f["n_high"] + f["n_low"] for f in fields]))
        score = 0.40 * math.exp(-((coverage - 0.25) / 0.20) ** 2) + 0.35 * min(1.0, dynamic / 1.25) + 0.25 * math.exp(-((fragmentation - 12.0) / 12.0) ** 2)
        rows.append({"configuration_id": cfg["id"], "target_free_visual_score": round(score, 8), "median_positive_fraction": round(coverage, 8), "median_cv": round(dynamic, 8), "median_interval_count": fragmentation, "field_hashes": [f["field"]["field_hash"] for f in fields]})
    rows.sort(key=lambda r: (-r["target_free_visual_score"], r["configuration_id"]))
    payload = {"status": "TARGET_FREE_VISUAL_RANKING_ONLY", "parity_status": HFT_PARITY_STATUS, "recommended_for_owner_review": rows[0]["configuration_id"] if rows else None, "configurations": rows, "prohibitions": ["NO_OUTCOMES", "NO_PNL", "NO_HOLDOUT", "NO_EDGE_CLAIM"]}
    payload["sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload
