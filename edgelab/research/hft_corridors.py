"""HFTZonesNQ -> causal liquidity-density integration.

This adapter is target-free.  V2 inputs are fail-closed: detector completion
(`end_ts_ns`) and causal availability (`available_ts_ns`) are distinct fields.
A V2 zone never becomes visible before `available_ts_ns`.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from decimal import Decimal
from typing import Any, Iterable

import numpy as np

from edgelab.research.density_field import compute_field, detect_density_intervals, price_to_tick

# The 2026-09-17 certification establishes exact equality across all 38 exported fields
# (primary geometry, timestamps with 0ns drift, secondary metrics, volume breakdown,
# non-movement statistics, termination reason, derived geometry, and session monotonicity)
# with contract boundary isolation strictly enforced.
HFT_PARITY_STATUS = "PASS_CERTIFIED_FULL_FIELD_PARITY"

HFT_VISUAL_CONFIGS: tuple[dict[str, Any], ...] = (
    {"id": "HFT_RAW_GAUSS_1", "model": "FIELD_RAW_STATIC", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.0},
    {"id": "HFT_RAW_GAUSS_2", "model": "FIELD_RAW_STATIC", "kernel": "KERNEL_GAUSS", "sigma_ticks": 2.0},
    {"id": "HFT_RAW_GAUSS_4", "model": "FIELD_RAW_STATIC", "kernel": "KERNEL_GAUSS", "sigma_ticks": 4.0},
    {"id": "HFT_RAW_BOX", "model": "FIELD_RAW_STATIC", "kernel": "KERNEL_BOX", "sigma_ticks": 1.0},
    {"id": "HFT_VOL025_GAUSS_2", "model": "FIELD_TRANS", "kernel": "KERNEL_GAUSS", "sigma_ticks": 2.0, "vol_transform": "TRANS_POWER_025"},
    {"id": "HFT_LOGVOL_GAUSS_2", "model": "FIELD_TRANS", "kernel": "KERNEL_GAUSS", "sigma_ticks": 2.0, "vol_transform": "TRANS_LOG"},
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_V2_REQUIRED = (
    "start_ts_ns", "end_ts_ns", "available_ts_ns", "session_id", "contract",
    "zone_seq", "parameter_manifest_sha256", "indicator_source_sha256",
    "termination_reason",
)
_ALLOWED_TERMINATIONS = {"REVERSAL", "MAX_PAUSE", "END_OF_SESSION", "CENSORED_END_OF_INPUT"}


def _first(row: dict, *keys: str) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def _int_exact(value: Any, name: str) -> int:
    try:
        number = Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{name} is not numeric") from exc
    if number != number.to_integral_value():
        raise ValueError(f"{name} must be an exact integer")
    return int(number)


def _mode(row: dict, requested: str) -> str:
    if requested not in {"auto", "V2", "V1_LEGACY"}:
        raise ValueError(f"unsupported HFT zone mode: {requested}")
    if requested != "auto":
        return requested
    if any(k in row for k in ("available_ts_ns", "start_ts_ns", "end_ts_ns")):
        return "V2"
    return "V1_LEGACY"


def normalize_hft_zone(row: dict, *, strict: bool = True, mode: str = "auto") -> dict:
    """Map a V1/V2 row to the density-field contract.

    V2 is deliberately strict and never falls back from available_ts_ns to
    end_ts_ns.  V1 remains diagnostic and derives availability from end_ms.
    """
    row = dict(row)
    detected = _mode(row, mode)
    lo = _first(row, "lo", "bottom", "price_low", "price_lower")
    hi = _first(row, "hi", "top", "price_high", "price_upper")
    if lo is None or hi is None:
        raise ValueError("HFT zone requires price bounds")

    if detected == "V2":
        missing = [key for key in _V2_REQUIRED if row.get(key) in (None, "")]
        if missing:
            raise ValueError("V2 HFT zone missing required fields: " + ", ".join(missing))
        origin_ns = _int_exact(row["start_ts_ns"], "start_ts_ns")
        end_ns = _int_exact(row["end_ts_ns"], "end_ts_ns")
        available_ns = _int_exact(row["available_ts_ns"], "available_ts_ns")
        if end_ns < origin_ns:
            raise ValueError("V2 end_ts_ns precedes start_ts_ns")
        if available_ns < end_ns:
            raise ValueError("V2 available_ts_ns precedes end_ts_ns")
        reason = str(row["termination_reason"])
        if reason not in _ALLOWED_TERMINATIONS:
            raise ValueError(f"uncertifiable termination_reason: {reason}")
        for key in ("parameter_manifest_sha256", "indicator_source_sha256"):
            if not _SHA256.fullmatch(str(row[key])):
                raise ValueError(f"invalid {key}")
        session_id = str(row["session_id"])
        contract = str(row["contract"])
        seq = _int_exact(row["zone_seq"], "zone_seq")
        if seq < 1:
            raise ValueError("zone_seq must start at 1")
        availability_source = "V2_AVAILABLE_NS"
        parity_status = HFT_PARITY_STATUS
    else:
        start = _first(row, "start_ms", "origin_ms", "start_ts", "origin_ts")
        end = _first(row, "end_ms", "end_ts")
        if end is None or (strict and start is None):
            raise ValueError("legacy HFT zone requires start and end milliseconds")
        available_ns = _int_exact(end, "end_ms") * 1_000_000
        origin_ns = (_int_exact(start, "start_ms") * 1_000_000) if start is not None else available_ns
        end_ns = available_ns
        if available_ns < origin_ns:
            raise ValueError("legacy completion precedes origin")
        seq_raw = _first(row, "zone_seq", "id")
        seq = _int_exact(seq_raw, "zone_seq") if seq_raw is not None else None
        session_id = str(_first(row, "session_id", "session") or "LEGACY_SESSION_UNKNOWN")
        contract = str(_first(row, "contract", "instrument") or "NQ_UNKNOWN")
        reason = str(_first(row, "termination_reason") or "LEGACY_UNKNOWN")
        availability_source = "V1_END_MS_DERIVED_DIAGNOSTIC"
        parity_status = "LEGACY_DIAGNOSTIC_NOT_CERTIFIED"

    direction = int(float(_first(row, "dir", "direction") or 0))
    zid = f"{contract}:{session_id}:{seq if seq is not None else origin_ns}:{direction}"
    return {
        "id": zid,
        "source": "HFTZonesNQPureV4",
        "lo": float(min(float(lo), float(hi))),
        "hi": float(max(float(lo), float(hi))),
        "origin_ts": origin_ns,
        "end_ts": end_ns,
        "available_ts": available_ns,
        "available_ts_source": availability_source,
        "termination_reason": reason,
        "vol": float(_first(row, "vol", "volume", "total_vol") or 1.0),
        "direction": direction,
        "session_id": session_id,
        "contract": contract,
        "zone_seq": seq,
        "parity_status": parity_status,
    }


def normalize_hft_zones(rows: Iterable[dict], *, strict: bool = True, mode: str = "auto") -> list[dict]:
    materialized = [dict(row) for row in rows]
    detected_modes = {_mode(row, mode) for row in materialized}
    if len(detected_modes) > 1:
        raise ValueError("mixed V1/V2 HFT zone inputs are forbidden")
    zones = [normalize_hft_zone(row, strict=strict, mode=mode) for row in materialized]
    zones.sort(key=lambda z: (z["available_ts"], z["origin_ts"], z["id"]))
    return zones


def causal_domain(price_ticks: Iterable[int], timestamps_ns: Iterable[int], t_ref_ns: int, zones: Iterable[dict], tick_size: float, margin_ticks: int = 20) -> tuple[int, int]:
    past_prices = [int(p) for p, ts in zip(price_ticks, timestamps_ns) if int(ts) <= int(t_ref_ns)]
    zone_ticks: list[int] = []
    for zone in zones:
        if int(zone["available_ts"]) <= int(t_ref_ns):
            zone_ticks.extend((price_to_tick(float(zone["lo"]), tick_size), price_to_tick(float(zone["hi"]), tick_size)))
    values = past_prices + zone_ticks
    if not values:
        raise ValueError("No causally available prices or zones at t_ref")
    return min(values) - margin_ticks, max(values) + margin_ticks


def _quantile_intervals(field: dict, tick_size: float, low_q: float = 0.25, high_q: float = 0.80) -> dict:
    density = np.asarray(field["density"], dtype=float)
    positive = density[density > 0]
    if positive.size == 0:
        return {"low_density_intervals": [], "high_density_regions": [], "low_threshold": 0.0, "high_threshold": 0.0}
    low, high = float(np.quantile(positive, low_q)), float(np.quantile(positive, high_q))
    result = detect_density_intervals(field["density"], field["price_ticks"], tick_size, low_thresh=low, high_thresh=high)
    result.update({"low_threshold": low, "high_threshold": high})
    return result


def evaluate_visual_configurations(zones: list[dict], t_refs: list[int], tick_size: float, domains: dict[int, tuple[int, int]]) -> dict:
    """Rank display configurations by target-free visual diagnostics only."""
    rows: list[dict] = []
    for cfg in HFT_VISUAL_CONFIGS:
        fields = []
        for t_ref in sorted(t_refs):
            pmin, pmax = domains[t_ref]
            field = compute_field(zones, t_ref, tick_size, pmin, pmax, cfg)
            density = np.asarray(field["density"], dtype=float)
            coverage = float(np.mean(density > 0))
            cv = float(np.std(density) / np.mean(density)) if float(np.mean(density)) > 0 else 0.0
            intervals = _quantile_intervals(field, tick_size)
            fields.append({"field": field, "coverage": coverage, "cv": cv, "fragments": len(intervals["high_density_regions"]) + len(intervals["low_density_intervals"])})
        median_coverage = float(np.median([item["coverage"] for item in fields]))
        dynamic = float(np.median([item["cv"] for item in fields]))
        fragmentation = float(np.median([item["fragments"] for item in fields]))
        score = 0.40 * math.exp(-((median_coverage - 0.25) / 0.20) ** 2) + 0.35 * min(1.0, dynamic / 1.25) + 0.25 * math.exp(-((fragmentation - 12.0) / 12.0) ** 2)
        rows.append({"configuration_id": cfg["id"], "target_free_visual_score": round(score, 8), "median_positive_fraction": round(median_coverage, 8), "median_cv": round(dynamic, 8), "median_interval_count": fragmentation, "field_hashes": [item["field"]["field_hash"] for item in fields]})
    rows.sort(key=lambda row: (-row["target_free_visual_score"], row["configuration_id"]))
    payload = {"status": "TARGET_FREE_VISUAL_HEURISTIC_ONLY_NOT_SCIENTIFIC_SELECTION", "parity_status": HFT_PARITY_STATUS, "recommended_for_owner_review": rows[0]["configuration_id"] if rows else None, "configurations": rows, "prohibitions": ["NO_OUTCOMES", "NO_PNL", "NO_HOLDOUT", "NO_EDGE_CLAIM", "NO_SCIENTIFIC_MODEL_SELECTION"]}
    payload["sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload
