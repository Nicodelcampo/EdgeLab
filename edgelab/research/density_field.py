"""Pure discrete density field computation and causal corridor detection for EdgeLab HP-007.

This module provides a pure, deterministic, viewport-invariant calculation of
microstructural density fields D(p, t) over integer price ticks.

Mandatory invariants:
1. No dependency on canvas, viewport, zoom, pan, or auto-scaling.
2. Causal availability: a zone contributes at t iff available_ts <= t.
3. Stable zone ordering: identical inputs -> identical output and deterministic SHA-256 hash.
4. Calculations strictly in integer price ticks.
5. As-of touch count and lifecycle state reconstruction.
6. Rolling causal median V_ref(t) using up to 500 past available zones.
7. Baseline mode FIELD_RAW_STATIC: zone weight = 1.0, no maturation, no decay, no wear.
8. Target-free: no targets, stops, R:R, win rates, traversals, or P&L.
"""
from __future__ import annotations

import collections
import hashlib
import json
import math
from typing import Any

import numpy as np

# Firewall del holdout (2026-07-01 -> 2026-12-31 CT). Ninguna zona disponible en o despues de este
# instante puede entrar a un campo, ni se puede evaluar el campo en ese instante. Antes vivia solo
# en `corridor_engine.js`; el campo canonico tiene que llevarlo consigo, en Python y en JS.
HOLDOUT_NS = 1_782_856_800_000_000_000


def to_nanoseconds(t: Any) -> int:
    """Converts a timestamp or epoch representation into integer nanoseconds."""
    if t is None:
        return 0
    if hasattr(t, "value"):  # pd.Timestamp or similar
        return int(t.value)
    if isinstance(t, (int, np.integer)):
        val = int(t)
    elif isinstance(t, (float, np.floating)):
        val = int(round(t))
    elif isinstance(t, str):
        try:
            return int(t)
        except ValueError:
            import pandas as pd
            return int(pd.Timestamp(t).value)
    else:
        import pandas as pd
        return int(pd.Timestamp(t).value)

    # Heuristic scale detection for epoch timestamps
    if val < 100_000_000_000:
        # Seconds (< year 5138 in seconds)
        return val * 1_000_000_000
    elif val < 100_000_000_000_000:
        # Milliseconds
        return val * 1_000_000
    elif val < 100_000_000_000_000_000:
        # Microseconds
        return val * 1_000
    else:
        # Nanoseconds
        return val


def price_to_tick(price: float, tick_size: float) -> int:
    """Converts floating point price to discrete integer tick count."""
    return int(round(round(price / tick_size, 6)))


def tick_to_price(tick: int, tick_size: float) -> float:
    """Converts discrete integer tick count back to floating point price."""
    return round(tick * tick_size, 6)


def compute_causal_v_ref(
    zones: list[dict],
    t_ref_ns: int,
    max_window: int = 500,
    cold_start_default: float = 100.0,
) -> tuple[float, str]:
    """Computes rolling causal median volume over past available zones <= t_ref.

    Invariants:
    - Strictly causal: only zones with available_ts <= t_ref_ns contribute.
    - Shuffled-input invariant: explicitly sorted by (available_ts, tiebreaker_id).
    - Window bounded: takes the last min(max_window, N) sorted causal zones.

    Returns (v_ref, v_ref_source).
    """
    causal_items: list[tuple[int, str, float]] = []
    for z in zones:
        z_avail = extract_zone_available_ns(z)
        avail_ns = z_avail[0]
        if avail_ns <= t_ref_ns:
            vol = zone_volume(z, 0.0)
            if vol > 0.0:
                zid = str(z.get("id", z.get("zone_id", "")))
                causal_items.append((avail_ns, zid, vol))

    if not causal_items:
        return cold_start_default, "COLD_START_DEFAULT"

    # Explicit sort by available_ts_ns, then tiebreaker zone_id (invariant to input order)
    causal_items.sort(key=lambda x: (x[0], x[1]))

    # Take the last min(max_window, len(causal_items))
    window_items = causal_items[-max_window:]
    window_vols = [item[2] for item in window_items]
    med = float(np.median(window_vols))
    return max(1.0, med), f"CAUSAL_ROLLING_MEDIAN_N_{len(window_vols)}"


def zone_volume(z: dict, default: float) -> float:
    """Volumen de una zona. Un volumen NULO equivale a un volumen AUSENTE (usa `default`).

    Antes la lectura directa del campo reventaba con TypeError cuando la clave existía con valor null, y el
    puerto JS lo habría tratado en silencio como 0 o NaN (un NaN contamina el campo entero). Lo encontró la
    paridad sobre bundles reales: hay zonas con `vol: null`. Ambas implementaciones aplican esta regla.
    """
    v = z.get("vol")
    if v is None:
        v = z.get("volume")
    if v is None:
        return float(default)
    return float(v)


def extract_zone_available_source(z: dict) -> str:
    """Extracts explicit availability provenance source.

    Possible sources:
    - V2_END_NS: HFT zone with nanosecond completion timestamp
    - V1_END_MS_DERIVED: HFT zone derived from millisecond completion timestamp
    - SIG_TS_CONFIRMED: BigTrap2 / BT2A zone confirmed at signal timestamp
    - LEGACY_CREATED_MS_FALLBACK: BigTrap2 / legacy fallback on creation timestamp
    - EXPLICIT_AVAILABLE_TS: Explicit available_ts field present
    - LEGACY_FALLBACK: Unspecified legacy fallback
    """
    if "available_ts_source" in z and z["available_ts_source"]:
        return str(z["available_ts_source"])

    src = str(z.get("source", "")).lower()
    if "hft" in src:
        if "end_ms" in z or "created_ms" in z or ("end_ts_ns" not in z and "available_ts_ns" not in z and "end_ns" not in z):
            return "V1_END_MS_DERIVED"
        return "V2_END_NS"

    if "bigtrap" in src or "bt2a" in src:
        if "sig_ts" in z or "sig_ts_confirmed" in z or "available_ts" in z:
            return "SIG_TS_CONFIRMED"
        return "LEGACY_CREATED_MS_FALLBACK"

    avail_ns, is_fallback = extract_zone_available_ns(z)
    if is_fallback:
        return "LEGACY_FALLBACK"
    return "EXPLICIT_AVAILABLE_TS"


def extract_zone_available_ns(z: dict) -> tuple[int, bool]:
    """Extracts available_ts in nanoseconds.

    Returns (available_ns, is_legacy_fallback).
    """
    for key in ("available_ns", "available_ts", "availableTime"):
        if key in z and z[key] is not None:
            return to_nanoseconds(z[key]), False

    # Legacy fallback: origin_ts, created_ms, sig_ts, t0, time
    for key in ("origin_ts", "created_ms", "sig_ts", "t0", "time"):
        if key in z and z[key] is not None:
            return to_nanoseconds(z[key]), True

    return 0, True


def extract_zone_ended_ns(z: dict) -> int | None:
    """Extracts ended_ts in nanoseconds if present."""
    for key in ("ended_ns", "ended_ts", "ended_ms", "t1"):
        if key in z and z[key] is not None:
            return to_nanoseconds(z[key])
    return None


def reconstruct_zone_touches_asof(z: dict, t_ref_ns: int) -> tuple[int, bool]:
    """Reconstructs touch count strictly as-of t_ref.

    Returns (touches_asof, is_legacy_fallback).
    """
    if "touch_events" in z and isinstance(z["touch_events"], list):
        count = 0
        for ev in z["touch_events"]:
            ev_ts = ev.get("touch_ts", ev.get("ts", ev)) if isinstance(ev, dict) else ev
            if to_nanoseconds(ev_ts) <= t_ref_ns:
                count += 1
        return count, False

    # Legacy touch count fallback
    final_touches = int(z.get("touches", 0))
    return final_touches, True


def reconstruct_zone_state_asof(z: dict, t_ref_ns: int) -> tuple[str, bool]:
    """Reconstructs lifecycle state strictly as-of t_ref.

    Returns (state_asof, is_legacy_fallback).
    """
    if "state_events" in z and isinstance(z["state_events"], list):
        latest_state = "ACTIVE"
        latest_ts = -1
        for ev in z["state_events"]:
            if isinstance(ev, dict):
                ev_ts = to_nanoseconds(ev.get("event_ts", ev.get("ts", 0)))
                if ev_ts <= t_ref_ns and ev_ts > latest_ts:
                    latest_ts = ev_ts
                    latest_state = str(ev.get("state", "ACTIVE"))
        return latest_state, False

    ended_ns = extract_zone_ended_ns(z)
    if ended_ns is not None and ended_ns <= t_ref_ns:
        return "ENDED", True
    return str(z.get("state", "ACTIVE")), True


def compute_field(
    zones: list[dict],
    t_ref: int | float | Any,
    tick_size: float,
    price_tick_min: int,
    price_tick_max: int,
    field_config: dict | None = None,
) -> dict:
    """Pure, deterministic discrete density field calculation.

    Inputs:
    - zones: list of zone dictionaries (not modified).
    - t_ref: evaluation timestamp as-of.
    - tick_size: instrument tick size (e.g. 0.25 for NQ).
    - price_tick_min: minimum integer price tick (inclusive).
    - price_tick_max: maximum integer price tick (inclusive).
    - field_config: configuration dict for model, kernel, and ablations.

    Returns dictionary with:
    - price_ticks: list of integer price ticks.
    - density: list of float density values.
    - active_zone_ids: sorted list of zone IDs active at t_ref.
    - diagnostics: calculation diagnostics including fallbacks, v_ref, and hashes.
    - field_hash: SHA-256 hash of the output field.
    """
    if price_tick_max < price_tick_min:
        raise ValueError(f"price_tick_max ({price_tick_max}) must be >= price_tick_min ({price_tick_min})")

    cfg = field_config or {}
    model_name = cfg.get("model", "FIELD_RAW_STATIC")
    kernel_type = cfg.get("kernel", "KERNEL_GAUSS")
    sigma_ticks = float(cfg.get("sigma_ticks", 1.2))
    ended_policy = cfg.get("ended_zone_policy", "exclude_ended")  # "exclude_ended" | "penalize_ended" | "include_all"

    t_ref_ns = to_nanoseconds(t_ref)
    holdout_guard = bool(cfg.get("holdout_guard", True))
    if holdout_guard and t_ref_ns >= HOLDOUT_NS:
        raise ValueError(f"t_ref {t_ref_ns} is at or after the sealed holdout boundary {HOLDOUT_NS}")

    # Filter and sort causally available zones
    active_zones: list[dict] = []
    active_zone_ids: list[str] = []
    legacy_availability_fallbacks = 0
    legacy_touch_fallbacks = 0

    for z in zones:
        z_avail_ns, is_avail_fallback = extract_zone_available_ns(z)
        if holdout_guard and z_avail_ns >= HOLDOUT_NS:
            raise ValueError(f"zone {z.get('id', z.get('zone_id', '?'))} is available at or after the sealed holdout boundary")
        if is_avail_fallback:
            legacy_availability_fallbacks += 1

        # Causal gate: available_ts <= t_ref
        if z_avail_ns > t_ref_ns:
            continue

        # Session & roll boundary isolation (B3)
        if "session_id" in cfg and cfg["session_id"] is not None:
            z_sess = z.get("session_id")
            if z_sess is not None and str(z_sess) != str(cfg["session_id"]):
                continue

        if "contract" in cfg and cfg["contract"] is not None:
            z_contract = z.get("contract")
            if z_contract is not None and str(z_contract) != str(cfg["contract"]):
                continue

        ended_ns = extract_zone_ended_ns(z)
        is_ended = (ended_ns is not None and ended_ns <= t_ref_ns)

        if is_ended and ended_policy == "exclude_ended":
            continue

        active_zones.append(z)

    # Sort zones stably by (available_ns, origin_ts, zone_id, lo, hi)
    def zone_sort_key(z: dict) -> tuple:
        avail_ns, _ = extract_zone_available_ns(z)
        zid = str(z.get("id", z.get("zone_id", "")))
        lo = float(z.get("lo", z.get("bottom", 0.0)))
        hi = float(z.get("hi", z.get("top", 0.0)))
        return (avail_ns, zid, lo, hi)

    active_zones.sort(key=zone_sort_key)
    for z in active_zones:
        zid = str(z.get("id", z.get("zone_id", "")))
        active_zone_ids.append(zid)

    # Causal V_ref calculation
    v_ref, v_ref_source = compute_causal_v_ref(
        zones=zones,
        t_ref_ns=t_ref_ns,
        max_window=int(cfg.get("v_ref_window", 500)),
        cold_start_default=float(cfg.get("cold_start_v_ref", 100.0)),
    )

    n_ticks = (price_tick_max - price_tick_min) + 1
    density_array = np.zeros(n_ticks, dtype=np.float64)

    # Compute contribution of each active zone
    for z in active_zones:
        z_avail_ns, _ = extract_zone_available_ns(z)
        ended_ns = extract_zone_ended_ns(z)
        is_ended = (ended_ns is not None and ended_ns <= t_ref_ns)

        # Price bounds in integer ticks
        z_lo_px = float(z.get("lo", z.get("bottom", 0.0)))
        z_hi_px = float(z.get("hi", z.get("top", 0.0)))
        lo_tick = price_to_tick(z_lo_px, tick_size)
        hi_tick = price_to_tick(z_hi_px, tick_size)
        if lo_tick > hi_tick:
            lo_tick, hi_tick = hi_tick, lo_tick

        # Base weight calculation
        if model_name == "FIELD_RAW_STATIC":
            w_zone = 1.0
        else:
            # Volume transform
            z_vol = zone_volume(z, 1.0)
            vol_trans = cfg.get("vol_transform", "TRANS_POWER_025")
            ratio = max(1.0, z_vol) / max(1.0, v_ref)
            if vol_trans == "TRANS_COUNT":
                w_vol = 1.0
            elif vol_trans == "TRANS_LOG":
                w_vol = math.log2(1.0 + ratio)
            elif vol_trans == "TRANS_WINSORIZED":
                w_vol = min(ratio, 3.0) ** 0.25
            else:
                w_vol = ratio ** 0.25

            # Maturation
            if cfg.get("use_maturation", False):
                age_s = max(0.0, (t_ref_ns - z_avail_ns) / 1e9)
                f_mat = 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, (age_s - 1800.0) / 600.0))))
            else:
                f_mat = 1.0

            # Time decay
            if cfg.get("use_time_decay", False):
                age_s = max(0.0, (t_ref_ns - z_avail_ns) / 1e9)
                decay_age = max(0.0, age_s - 14400.0)
                f_decay = math.exp(-math.log(2.0) * decay_age / 43200.0)
            else:
                f_decay = 1.0

            # Wear by touches as-of
            if cfg.get("use_wear", False):
                touches_asof, is_touch_fb = reconstruct_zone_touches_asof(z, t_ref_ns)
                if is_touch_fb:
                    legacy_touch_fallbacks += 1
                # (1 + a·toques)^-b. Por defecto a=0.5, b=0.60 (HP-007); ajustable para calibrar el tamaño de corredores.
                f_wear = (1.0 + float(cfg.get("wear_alpha", 0.5)) * touches_asof) ** -float(cfg.get("wear_exp", 0.60))
            else:
                f_wear = 1.0

            # Invalidation / ended penalty
            if is_ended and ended_policy == "penalize_ended":
                penalty = float(cfg.get("invalidation_penalty", 0.35))
            else:
                penalty = 1.0

            w_zone = w_vol * f_mat * f_decay * f_wear * penalty

        if w_zone <= 0.0:
            continue

        # Spatial kernel calculation across price grid
        if kernel_type == "KERNEL_BOX":
            k_lo = max(price_tick_min, lo_tick)
            k_hi = min(price_tick_max, hi_tick)
            if k_lo <= k_hi:
                i_lo = k_lo - price_tick_min
                i_hi = k_hi - price_tick_min
                density_array[i_lo : i_hi + 1] += w_zone
        elif kernel_type.startswith("KERNEL_GAUSS"):
            sigma = max(0.1, sigma_ticks)
            cutoff_ticks = int(math.ceil(3.0 * sigma))
            k_lo = max(price_tick_min, lo_tick - cutoff_ticks)
            k_hi = min(price_tick_max, hi_tick + cutoff_ticks)
            if k_lo <= k_hi:
                for k in range(k_lo, k_hi + 1):
                    if k < lo_tick:
                        d_ticks = lo_tick - k
                    elif k > hi_tick:
                        d_ticks = k - hi_tick
                    else:
                        d_ticks = 0.0

                    if d_ticks <= 3.0 * sigma:
                        k_val = 1.0 if d_ticks == 0.0 else math.exp(-(d_ticks ** 2) / (2.0 * (sigma ** 2)))
                        density_array[k - price_tick_min] += w_zone * k_val

    # Optional saturation transform (e.g. F(p) = 1 - exp(-D))
    if cfg.get("saturation", False):
        density_array = 1.0 - np.exp(-np.maximum(0.0, density_array))

    # Round to 8 decimal places for exact reproducibility
    rounded_density = [round(float(v), 8) for v in density_array]
    price_ticks = list(range(price_tick_min, price_tick_max + 1))

    # Compute deterministic SHA-256 field hash
    canonical_payload = {
        "price_tick_min": price_tick_min,
        "price_tick_max": price_tick_max,
        "tick_size": tick_size,
        "active_zone_ids": active_zone_ids,
        "density": rounded_density,
        "model": model_name,
        "kernel": kernel_type,
    }
    raw_bytes = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    field_hash = hashlib.sha256(raw_bytes).hexdigest()

    diagnostics = {
        "model": model_name,
        "kernel": kernel_type,
        "sigma_ticks": sigma_ticks,
        "v_ref": v_ref,
        "v_ref_source": v_ref_source,
        "n_active_zones": len(active_zones),
        "total_zones_evaluated": len(zones),
        "legacy_availability_fallbacks": legacy_availability_fallbacks,
        "legacy_touch_fallbacks": legacy_touch_fallbacks,
        "available_ts_sources": dict(collections.Counter(extract_zone_available_source(z) for z in active_zones)),
        "causal_status": "LEGACY_NON_CAUSAL" if legacy_availability_fallbacks > 0 else "PASS_CAUSAL",
        "price_tick_min": price_tick_min,
        "price_tick_max": price_tick_max,
        "n_ticks": n_ticks,
        "field_mean": round(float(np.mean(density_array)), 6),
        "field_max": round(float(np.max(density_array)), 6),
        "field_hash": field_hash,
    }

    return {
        "price_ticks": price_ticks,
        "density": rounded_density,
        "active_zone_ids": active_zone_ids,
        "diagnostics": diagnostics,
        "field_hash": field_hash,
    }


def detect_density_intervals(
    density: list[float],
    price_ticks: list[int],
    tick_size: float,
    low_thresh: float = 0.32,
    high_thresh: float = 0.70,
    min_low_ticks: int = 7,
    min_high_ticks: int = 2,
) -> dict:
    """Detects low-density intervals and high-density regions across the complete domain.

    Calculated strictly over the entire fixed price grid, independent of the viewport.
    Returns:
    {
        "low_density_intervals": list[dict],
        "high_density_regions": list[dict]
    }
    """
    n = len(density)
    if n == 0 or len(price_ticks) != n:
        return {"low_density_intervals": [], "high_density_regions": []}

    low_intervals = []
    in_low = False
    low_start = 0

    for i in range(n):
        if density[i] <= low_thresh:
            if not in_low:
                in_low = True
                low_start = i
        else:
            if in_low:
                span = i - low_start
                if span >= min_low_ticks:
                    avg_d = float(np.mean(density[low_start:i]))
                    low_intervals.append({
                        "tick_start": price_ticks[low_start],
                        "tick_end": price_ticks[i - 1],
                        "price_min": tick_to_price(price_ticks[low_start], tick_size),
                        "price_max": tick_to_price(price_ticks[i - 1], tick_size),
                        "tick_count": span,
                        "avg_density": round(avg_d, 6),
                    })
                in_low = False

    if in_low:
        span = n - low_start
        if span >= min_low_ticks:
            avg_d = float(np.mean(density[low_start:n]))
            low_intervals.append({
                "tick_start": price_ticks[low_start],
                "tick_end": price_ticks[n - 1],
                "price_min": tick_to_price(price_ticks[low_start], tick_size),
                "price_max": tick_to_price(price_ticks[n - 1], tick_size),
                "tick_count": span,
                "avg_density": round(avg_d, 6),
            })

    high_regions = []
    in_high = False
    high_start = 0

    for i in range(n):
        if density[i] >= high_thresh:
            if not in_high:
                in_high = True
                high_start = i
        else:
            if in_high:
                span = i - high_start
                if span >= min_high_ticks:
                    max_d = float(np.max(density[high_start:i]))
                    high_regions.append({
                        "tick_start": price_ticks[high_start],
                        "tick_end": price_ticks[i - 1],
                        "price_min": tick_to_price(price_ticks[high_start], tick_size),
                        "price_max": tick_to_price(price_ticks[i - 1], tick_size),
                        "tick_count": span,
                        "max_density": round(max_d, 6),
                    })
                in_high = False

    if in_high:
        span = n - high_start
        if span >= min_high_ticks:
            max_d = float(np.max(density[high_start:n]))
            high_regions.append({
                "tick_start": price_ticks[high_start],
                "tick_end": price_ticks[n - 1],
                "price_min": tick_to_price(price_ticks[high_start], tick_size),
                "price_max": tick_to_price(price_ticks[n - 1], tick_size),
                "tick_count": span,
                "max_density": round(max_d, 6),
            })

    return {
        "low_density_intervals": low_intervals,
        "high_density_regions": high_regions,
    }
