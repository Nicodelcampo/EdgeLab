"""BigTrap2Absorption v1.1.1 — absorcion = flujo alto con desplazamiento bajo.

Percentil causal sobre las ultimas `AbsorptionLookback` cubetas completas.
Filtro de filas contiguas (`MinStackedRows`) y fraccion de volumen (`MinTrapFrac`).
Fills anclados al primer tick posterior (causal).
"""
from __future__ import annotations

import math
from datetime import datetime, timezone as _tz
import numpy as np

from ..common import floor_div, ns_to_ms, plain, tz_of

NAME = "BigTrap2Absorption"

DEFAULTS = dict(
    TapeWindowTicks=25,
    ScoreMode="AbsDirectional",
    AbsorptionPct=90.0,
    AbsorptionLookback=500,
    MinHistoryBuckets=200,
    RequireFlowSideMatch=True,
    ImbalanceMode="Diagonal",
    TrapVolumeSource="AggressiveSide",
    TicksPerRow=1,
    ImbalanceRatio=3.0,
    MinStackedRows=2,
    MinTrapFrac=0.20,
    MinDeltaFilter=0.0,
    MinTrapVolume=0.0,
    MinExportVolume=1.0,
    UseWickFilter=True,
    WickZonePct=30.0,
    InvalidationMode="CloseThrough",
    MaxAgeBars=2000,
    MaxTouches=0,
    DrawZoneBand=True,
)

PARAM_SPEC = dict(
    TapeWindowTicks=dict(type="int", min=2, max=1000),
    ScoreMode=dict(type="enum", choices=["AbsDirectional", "AbsMagnitude"]),
    AbsorptionPct=dict(type="float", min=0.0, max=100.0, step=0.5),
    AbsorptionLookback=dict(type="int", min=10, max=5000),
    MinHistoryBuckets=dict(type="int", min=1, max=2000),
    RequireFlowSideMatch=dict(type="bool"),
    ImbalanceMode=dict(type="enum", choices=["Diagonal", "SameLevel"]),
    TrapVolumeSource=dict(type="enum", choices=["AggressiveSide", "TotalLevel"]),
    TicksPerRow=dict(type="int", min=1, max=20),
    ImbalanceRatio=dict(type="float", min=1.0, max=20.0, step=0.1),
    MinStackedRows=dict(type="int", min=1, max=20),
    MinTrapFrac=dict(type="float", min=0.0, max=1.0, step=0.05),
    MinDeltaFilter=dict(type="float", min=0.0, max=10000.0),
    MinTrapVolume=dict(type="float", min=0.0, max=10000.0),
    MinExportVolume=dict(type="float", min=1.0, max=10000.0),
    UseWickFilter=dict(type="bool"),
    WickZonePct=dict(type="float", min=0.0, max=50.0, step=1.0),
    InvalidationMode=dict(type="enum", choices=["CloseThrough", "FirstTouch", "None"]),
    MaxAgeBars=dict(type="int", min=0, max=20000),
    MaxTouches=dict(type="int", min=0, max=100),
    DrawZoneBand=dict(type="bool"),
)

def _percentile(arr, q):
    if len(arr) == 0:
        return float("nan")
    if len(arr) == 1:
        return float(arr[0])
    tmp = sorted(arr)
    n = len(tmp)
    qq = max(0.0, min(100.0, float(q)))
    pos = (qq / 100.0) * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi or hi >= n:
        return float(tmp[min(lo, n - 1)])
    return float(tmp[lo] + (tmp[hi] - tmp[lo]) * (pos - lo))

def run(ticks, bars, footprints=None, params=None, chart_tz="UTC"):
    p = dict(DEFAULTS)
    if params:
        p.update(params)

    tape_window = max(2, int(p["TapeWindowTicks"]))
    score_mode = str(p["ScoreMode"])
    abs_pct = float(p["AbsorptionPct"])
    abs_lookback = max(10, int(p["AbsorptionLookback"]))
    min_history = max(1, int(p["MinHistoryBuckets"]))
    require_flow_side = bool(p["RequireFlowSideMatch"])
    imbalance_mode = str(p["ImbalanceMode"])
    trap_vol_src = str(p["TrapVolumeSource"])
    ticks_per_row = max(1, int(p["TicksPerRow"]))
    imbalance_ratio = float(p["ImbalanceRatio"])
    min_stacked_rows = max(1, int(p["MinStackedRows"]))
    min_trap_frac = float(p["MinTrapFrac"])
    min_delta = float(p["MinDeltaFilter"])
    min_trap_vol = float(p["MinTrapVolume"])
    min_export_vol = float(p["MinExportVolume"])
    use_wick = bool(p["UseWickFilter"])
    wick_pct = float(p["WickZonePct"])
    invalidation = str(p["InvalidationMode"])
    max_age_bars = int(p["MaxAgeBars"])
    max_touches = int(p["MaxTouches"])

    tick_size = float(ticks.tick_size)
    n_ticks = len(ticks.ts_ns)

    # Process ticks in buckets of tape_window
    abs_ring = []
    zones = []
    events = []
    
    # Tick loop
    n_buckets = n_ticks // tape_window
    
    for b_idx in range(1, n_buckets): # skip first bucket like NT8
        k_start = b_idx * tape_window
        k_end = min(n_ticks, (b_idx + 1) * tape_window)
        if k_end - k_start < tape_window:
            break

        slice_px = ticks.price_ticks[k_start:k_end]
        slice_vol = ticks.volume[k_start:k_end]
        slice_bid = ticks.bid_ticks[k_start:k_end]
        slice_ask = ticks.ask_ticks[k_start:k_end]
        slice_ts = ticks.ts_ns[k_start:k_end]

        o_tick = int(slice_px[0])
        c_tick = int(slice_px[-1])
        mx_tick = int(np.max(slice_px))
        mn_tick = int(np.min(slice_px))
        bar_vol = float(np.sum(slice_vol))

        # Classify side
        ask_map = {}
        bid_map = {}
        signed_flow = 0.0

        for i in range(len(slice_px)):
            px = slice_px[i]
            v = slice_vol[i]
            a_q = slice_ask[i]
            b_q = slice_bid[i]
            
            side = 0
            if a_q > 0 and b_q > 0 and a_q >= b_q:
                if px >= a_q:
                    side = 1
                elif px <= b_q:
                    side = -1
            if side == 0:
                if i > 0:
                    side = 1 if slice_px[i] > slice_px[i-1] else (-1 if slice_px[i] < slice_px[i-1] else 1)
                else:
                    side = 1
            
            m = ask_map if side > 0 else bid_map
            m[px] = m.get(px, 0.0) + v
            signed_flow += (v if side > 0 else -v)

        d_ticks = float(c_tick - o_tick)
        if score_mode == "AbsDirectional":
            sgn = 1.0 if signed_flow > 0 else (-1.0 if signed_flow < 0 else 0.0)
            denom = 1.0 + max(0.0, sgn * d_ticks)
        else:
            denom = 1.0 + abs(d_ticks)
        
        a_score = abs(signed_flow) / denom

        if abs_pct <= 0.0:
            a_pass = True
            a_thr = 0.0
        elif len(abs_ring) >= min_history:
            a_thr = _percentile(abs_ring, abs_pct)
            a_pass = (a_score >= a_thr)
        else:
            a_thr = float("nan")
            a_pass = False

        # Build rows
        row_ask = {}
        row_bid = {}
        for tick, v in ask_map.items():
            r = floor_div(tick, ticks_per_row)
            row_ask[r] = row_ask.get(r, 0.0) + v
        for tick, v in bid_map.items():
            r = floor_div(tick, ticks_per_row)
            row_bid[r] = row_bid.get(r, 0.0) + v

        row_keys = sorted(set(row_ask.keys()) | set(row_bid.keys()))
        close_px_val = c_tick * tick_size
        close_half_tick = 2 * c_tick
        hi_px = mx_tick * tick_size
        lo_px = mn_tick * tick_size
        rng = hi_px - lo_px
        wick_hi_floor = hi_px - rng * (wick_pct / 100.0)
        wick_lo_ceil = lo_px + rng * (wick_pct / 100.0)

        # Runs
        buy_runs = []
        sell_runs = []
        b_act = False; b_prev = -999999; b_cur = None
        s_act = False; s_prev = -999999; s_cur = None

        for r in row_keys:
            a = row_ask.get(r, 0.0)
            b = row_bid.get(r, 0.0)
            total = a + b
            skip = abs(a - b) < min_delta

            buy_ratio = 0.0
            sell_ratio = 0.0
            if not skip:
                if imbalance_mode == "Diagonal":
                    bDn = row_bid.get(r - 1, 0.0)
                    aUp = row_ask.get(r + 1, 0.0)
                    buy_ratio = a / max(bDn, 1.0)
                    sell_ratio = b / max(aUp, 1.0)
                else:
                    buy_ratio = a / max(b, 1.0)
                    sell_ratio = b / max(a, 1.0)

            row_price = (r * ticks_per_row + (ticks_per_row - 1) / 2.0) * tick_size
            row_half = 2 * r * ticks_per_row + (ticks_per_row - 1)
            contrib_buy = a if trap_vol_src == "AggressiveSide" else total
            contrib_sell = b if trap_vol_src == "AggressiveSide" else total

            buyQ = (not skip and a >= 1 and buy_ratio >= imbalance_ratio and row_half > close_half_tick
                    and (not use_wick or (rng > 0 and row_price >= wick_hi_floor)))
            sellQ = (not skip and b >= 1 and sell_ratio >= imbalance_ratio and row_half < close_half_tick
                     and (not use_wick or (rng > 0 and row_price <= wick_lo_ceil)))

            if buyQ:
                if b_act and r == b_prev + 1:
                    b_cur["hi"] = r
                    b_cur["vol"] += contrib_buy
                    b_cur["wsum"] += row_price * contrib_buy
                    b_cur["nrows"] += 1
                else:
                    if b_act: buy_runs.append(b_cur)
                    b_cur = dict(lo=r, hi=r, vol=contrib_buy, wsum=row_price*contrib_buy, nrows=1)
                    b_act = True
                b_prev = r
            elif b_act:
                buy_runs.append(b_cur)
                b_act = False

            if sellQ:
                if s_act and r == s_prev + 1:
                    s_cur["hi"] = r
                    s_cur["vol"] += contrib_sell
                    s_cur["wsum"] += row_price * contrib_sell
                    s_cur["nrows"] += 1
                else:
                    if s_act: sell_runs.append(s_cur)
                    s_cur = dict(lo=r, hi=r, vol=contrib_sell, wsum=row_price*contrib_sell, nrows=1)
                    s_act = True
                s_prev = r
            elif s_act:
                sell_runs.append(s_cur)
                s_act = False

        if b_act: buy_runs.append(b_cur)
        if s_act: sell_runs.append(s_cur)

        # Check side qualifications
        flow_side = 1 if signed_flow > 0 else (-1 if signed_flow < 0 else 0)

        for is_bull, runs, side_match in [(True, buy_runs, flow_side == 1), (False, sell_runs, flow_side == -1)]:
            if not a_pass:
                continue
            if require_flow_side and not side_match:
                continue
            
            # Find best run >= min_stacked_rows
            best_run = None
            for run_cand in runs:
                if run_cand["nrows"] >= min_stacked_rows:
                    if best_run is None or run_cand["vol"] > best_run["vol"]:
                        best_run = run_cand
            
            if best_run is None:
                continue
            if best_run["vol"] < min_trap_vol:
                continue
            if (best_run["vol"] / max(bar_vol, 1.0)) < min_trap_frac:
                continue

            lo_t = best_run["lo"] * ticks_per_row
            hi_t = (best_run["hi"] + 1) * ticks_per_row - 1
            z_lo = lo_t * tick_size - tick_size / 2.0
            z_hi = hi_t * tick_size + tick_size / 2.0
            
            # Fill tick: 1st tick of NEXT bucket
            fill_k = k_end
            if fill_k < n_ticks:
                fill_px = float(ticks.price_ticks[fill_k]) * tick_size
                fill_ts = int(ticks.ts_ns[fill_k])
            else:
                fill_px = close_px_val
                fill_ts = int(slice_ts[-1])

            zones.append({
                "zone_id": f"{b_idx}_{'B' if is_bull else 'S'}",
                "bar": b_idx,
                "ts_ns": fill_ts,
                "time_sec": fill_ts // 1_000_000_000,
                "side": "trapped_buyers" if is_bull else "trapped_sellers",
                "dir": "short" if is_bull else "long",
                "lo": z_lo,
                "hi": z_hi,
                "vol": best_run["vol"],
                "fill_px": fill_px,
                "a_score": a_score,
                "a_thr": a_thr
            })

        # Push to ring
        if len(abs_ring) < abs_lookback:
            abs_ring.append(a_score)
        else:
            abs_ring.pop(0)
            abs_ring.append(a_score)

    return dict(
        indicator=NAME,
        params=p,
        zones=zones,
        n_zones=len(zones)
    )
