# -*- coding: utf-8 -*-
"""BigTrap2 Creation-Only Detector (Target-Free, Canonical Parity, Zero-Lifecycle).

Strictly extracts trapped buyer/seller absorption zones on the bar of creation
using the exact canonical formulas from BigTrap2 v2.2 (row_price > close for buyers,
row_price < close for sellers).

Guaranteed to NEVER call update_zones, NEVER inspect future bars, NEVER compute touches,
NEVER evaluate invalidation/expiration, and NEVER access price paths beyond the current bar index.
"""
from __future__ import annotations

from typing import Any
import numpy as np

from ..common import floor_div, ns_to_ms

DEFAULTS = dict(
    ticks_per_row=1,
    imbalance_mode="Diagonal",
    trap_volume_source="AggressiveSide",
    imbalance_ratio=3.0,
    use_wick_filter=False,
    wick_zone_pct=30.0,
    min_delta_filter=0.0,
    min_trap_volume=10.0,
    min_export_volume=10.0,
)


def detect_creations_only(
    ticks: Any,
    bars: Any,
    footprints: Any,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Extract creation zones across bars with exact canonical parity and zero lifecycle."""
    p = {**DEFAULTS, **(params or {})}
    tick_size = float(ticks.tick_size)
    row_ticks = max(1, int(p["ticks_per_row"]))
    min_vol = float(p["min_trap_volume"])
    imb_ratio = float(p["imbalance_ratio"])
    use_wick = bool(p["use_wick_filter"])
    wick_pct = float(p["wick_zone_pct"])
    min_delta = float(p["min_delta_filter"])
    imb_mode = str(p["imbalance_mode"])
    trap_vol_src = str(p["trap_volume_source"])

    n_bars = len(bars.close_t)
    created_zones: list[dict[str, Any]] = []

    # Bar 0 is discarded (potentially partial footprint, standard BigTrap2 protocol)
    for b in range(1, n_bars):
        if b >= len(footprints.ask):
            break
        ask_map = footprints.ask[b]
        bid_map = footprints.bid[b]
        if not ask_map and not bid_map:
            continue

        # Aggregate footprint into price rows
        row_ask: dict[int, float] = {}
        row_bid: dict[int, float] = {}
        for tk, v in ask_map.items():
            r = floor_div(tk, row_ticks)
            row_ask[r] = row_ask.get(r, 0.0) + float(v)
        for tk, v in bid_map.items():
            r = floor_div(tk, row_ticks)
            row_bid[r] = row_bid.get(r, 0.0) + float(v)

        row_keys = sorted(set(row_ask) | set(row_bid))
        if not row_keys:
            continue

        close = float(bars.close_t[b]) * tick_size
        hi = float(bars.high_t[b]) * tick_size
        lo = float(bars.low_t[b]) * tick_size
        rng = hi - lo
        wick_hi_floor = hi - rng * (wick_pct / 100.0)
        wick_lo_ceil = lo + rng * (wick_pct / 100.0)

        poc_vol = -1.0
        buy = dict(vol=0.0, wsum=0.0, mx=0.0, lo=None, hi=None, n=0)
        sell = dict(vol=0.0, wsum=0.0, mx=0.0, lo=None, hi=None, n=0)

        for r in row_keys:
            a = row_ask.get(r, 0.0)
            bv = row_bid.get(r, 0.0)
            total = a + bv
            if total > poc_vol:
                poc_vol = total
            if abs(a - bv) < min_delta:
                continue

            if imb_mode == "Diagonal":
                buy_ratio = a / max(row_bid.get(r - 1, 0.0), 1.0)
                sell_ratio = bv / max(row_ask.get(r + 1, 0.0), 1.0)
            else:
                buy_ratio = a / max(bv, 1.0)
                sell_ratio = bv / max(a, 1.0)

            row_price = (r * row_ticks + (row_ticks - 1) / 2.0) * tick_size
            contrib_buy = a if trap_vol_src == "AggressiveSide" else total
            contrib_sell = bv if trap_vol_src == "AggressiveSide" else total

            # Canonical Trapped Buyers: buyer aggression ending strictly ABOVE bar close
            if (a >= 1 and buy_ratio >= imb_ratio and row_price > close
                    and (not use_wick or (rng > 0 and row_price >= wick_hi_floor))):
                buy["vol"] += contrib_buy
                buy["wsum"] += row_price * contrib_buy
                buy["n"] += 1
                buy["lo"] = r if buy["lo"] is None else min(buy["lo"], r)
                buy["hi"] = r if buy["hi"] is None else max(buy["hi"], r)
                buy["mx"] = max(buy["mx"], buy_ratio)

            # Canonical Trapped Sellers: seller aggression ending strictly BELOW bar close
            if (bv >= 1 and sell_ratio >= imb_ratio and row_price < close
                    and (not use_wick or (rng > 0 and row_price <= wick_lo_ceil))):
                sell["vol"] += contrib_sell
                sell["wsum"] += row_price * contrib_sell
                sell["n"] += 1
                sell["lo"] = r if sell["lo"] is None else min(sell["lo"], r)
                sell["hi"] = r if sell["hi"] is None else max(sell["hi"], r)
                sell["mx"] = max(sell["mx"], sell_ratio)

        t_ns = int(bars.end_ns[b])

        # Emit Trapped Buyers (Bull)
        if buy["n"] > 0 and buy["vol"] >= min_vol:
            lo_row = buy["lo"] or 0
            hi_row = buy["hi"] or 0
            lo_tick = lo_row * row_ticks
            hi_tick = (hi_row + 1) * row_ticks - 1
            z_lo = lo_tick * tick_size - tick_size / 2.0
            z_hi = hi_tick * tick_size + tick_size / 2.0
            centroid = buy["wsum"] / buy["vol"]
            created_zones.append({
                "bar_idx": b,
                "bar_time_ns": t_ns,
                "kind": "trapped_buyers",
                "side": "B",
                "vol": float(buy["vol"]),
                "centroid": float(centroid),
                "top": float(z_hi),
                "bottom": float(z_lo),
                "width_ticks": int(round((z_hi - z_lo) / tick_size)),
                "max_ratio": float(buy["mx"]),
                "n_rows": int(buy["n"]),
            })

        # Emit Trapped Sellers (Bear)
        if sell["n"] > 0 and sell["vol"] >= min_vol:
            lo_row = sell["lo"] or 0
            hi_row = sell["hi"] or 0
            lo_tick = lo_row * row_ticks
            hi_tick = (hi_row + 1) * row_ticks - 1
            z_lo = lo_tick * tick_size - tick_size / 2.0
            z_hi = hi_tick * tick_size + tick_size / 2.0
            centroid = sell["wsum"] / sell["vol"]
            created_zones.append({
                "bar_idx": b,
                "bar_time_ns": t_ns,
                "kind": "trapped_sellers",
                "side": "S",
                "vol": float(sell["vol"]),
                "centroid": float(centroid),
                "top": float(z_hi),
                "bottom": float(z_lo),
                "width_ticks": int(round((z_hi - z_lo) / tick_size)),
                "max_ratio": float(sell["mx"]),
                "n_rows": int(sell["n"]),
            })

    return created_zones
