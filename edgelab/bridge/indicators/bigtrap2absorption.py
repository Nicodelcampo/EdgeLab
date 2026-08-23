"""BigTrap2Absorption v1.1.1 — kernel canónico de absorción sobre flujo y desplazamiento.

Definición:
    dPx  = (close - open) en ticks
    A    = |flujo| / (1 + |dPx|)             [ScoreMode = AbsMagnitude (Headline)]
    A    = |flujo| / (1 + max(0, sgn*dPx))   [ScoreMode = AbsDirectional (Trial 2)]

El umbral se calcula mediante percentil causal rodante sobre las últimas `AbsorptionLookback` cubetas.
Cortes de sesión CME mediante session_ids de bars.py (marcan cubetas residuales, fuera del historial).
Fills anclados al primer tick de la cubeta siguiente.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone as _tz
import numpy as np

from ..common import floor_div, ns_to_ms, plain, tz_of
from ..bars import session_ids

NAME = "BigTrap2Absorption"

# HEADLINE CONGELADO (2026-08-22 20:55 ART)
DEFAULTS = dict(
    TapeWindowTicks=25,
    ScoreMode="AbsMagnitude",
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
    ScoreMode=dict(type="enum", choices=["AbsMagnitude", "AbsDirectional"]),
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

def run(ticks, bars=None, footprints=None, params=None, chart_tz="UTC"):
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
    s_ids = session_ids(ticks.ts_ns)

    abs_ring = []
    zones = []
    events = []
    active_zones = []
    pending_fills = []

    cur_block = []
    cur_session = None
    bar_seq = 0
    seq_counter = 0

    def log_event(t_ns, ev_type, payload):
        nonlocal seq_counter
        # Formato pipe: seq|iso|type|payload
        dt_str = datetime.fromtimestamp(t_ns / 1_000_000_000.0, tz=_tz.utc).strftime("%Y-%m-%dT%H:%M:%S.%f0")
        line = f"{seq_counter}|{dt_str}|{ev_type}|{payload}"
        events.append(line)
        seq_counter += 1

    def update_active_zones(bar_idx, t_ns, close_px, hi_px, lo_px):
        for z in list(active_zones):
            if max_age_bars > 0 and (bar_idx - z["created_bar"]) > max_age_bars:
                z.update(state="EXPIRED", ended_ms=ns_to_ms(t_ns), end_reason="max_age")
                log_event(t_ns, "ZONE_EXPIRED", f"zone_id={z['id']};bar={bar_idx};reason=max_age")
                active_zones.remove(z)
                continue
            touched = (hi_px >= z["lo"] and lo_px <= z["hi"])
            if touched:
                z["touches"] += 1
                log_event(t_ns, "ZONE_TOUCHED", f"zone_id={z['id']};bar={bar_idx};touches={z['touches']}")
            adverse_close = (close_px > z["hi"] if z["is_bull"] else close_px < z["lo"])
            reason = None
            if invalidation == "FirstTouch" and touched:
                reason = "first_touch"
            elif invalidation == "CloseThrough" and adverse_close:
                reason = "close_through" if touched else "close_through_gap"
            if reason is None and max_touches > 0 and z["touches"] >= max_touches:
                reason = "max_touches"
            if reason is not None:
                z.update(state="INVALIDATED", ended_ms=ns_to_ms(t_ns), end_reason=reason)
                log_event(t_ns, "ZONE_INVALIDATED", f"zone_id={z['id']};reason={reason};bar={bar_idx}")
                active_zones.remove(z)

    def flush_block(blk, residual, sess_id):
        nonlocal bar_seq
        if len(blk) == 0:
            return

        bar_seq += 1
        b_idx = bar_seq

        blk_px = ticks.price_ticks[blk]
        blk_vol = ticks.volume[blk]
        blk_bid = ticks.bid_ticks[blk]
        blk_ask = ticks.ask_ticks[blk]
        blk_ts = ticks.ts_ns[blk]

        o_tick = int(blk_px[0])
        c_tick = int(blk_px[-1])
        mx_tick = int(np.max(blk_px))
        mn_tick = int(np.min(blk_px))
        bar_vol = float(np.sum(blk_vol))

        close_px = c_tick * tick_size
        hi_px = mx_tick * tick_size
        lo_px = mn_tick * tick_size

        t_start_iso = datetime.fromtimestamp(blk_ts[0] / 1e9, tz=_tz.utc).strftime("%Y-%m-%dT%H:%M:%S.%f0")
        t_end_iso = datetime.fromtimestamp(blk_ts[-1] / 1e9, tz=_tz.utc).strftime("%Y-%m-%dT%H:%M:%S.%f0")
        trade_date = str(sess_id)

        update_active_zones(b_idx, blk_ts[-1], close_px, hi_px, lo_px)

        log_event(blk_ts[-1], "BARRA_PROCESADA", f"bar={b_idx};largo={len(blk)};residual={residual};tape_window={tape_window};td={trade_date}")

        ask_map = {}
        bid_map = {}
        signed_flow = 0.0
        n_quote = 0
        n_rule = 0

        for k in range(len(blk)):
            p = blk_px[k]
            v = blk_vol[k]
            aq = blk_ask[k]
            bq = blk_bid[k]

            side = 0
            by_quote = False
            if aq > 0 and bq > 0 and aq >= bq:
                if p >= aq:
                    side = 1
                    by_quote = True
                elif p <= bq:
                    side = -1
                    by_quote = True
            if side == 0:
                if k > 0:
                    if p > blk_px[k - 1]:
                        side = 1
                    elif p < blk_px[k - 1]:
                        side = -1
                    else:
                        side = 1
                else:
                    side = 1
            if by_quote:
                n_quote += 1
            else:
                n_rule += 1

            m = ask_map if side > 0 else bid_map
            m[p] = m.get(p, 0.0) + v
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

        if residual:
            a_pass = False

        dur_ms = int((blk_ts[-1] - blk_ts[0]) // 1_000_000)
        last_bid = blk_bid[-1] * tick_size
        last_ask = blk_ask[-1] * tick_size
        spread_ticks = ((blk_ask[-1] - blk_bid[-1]) if (blk_ask[-1] > 0 and blk_bid[-1] > 0 and blk_ask[-1] >= blk_bid[-1]) else float("nan"))
        
        # Mid calculation
        mid0 = (blk_ask[0] + blk_bid[0]) * 0.5 if (blk_ask[0] > 0 and blk_bid[0] > 0 and blk_ask[0] >= blk_bid[0]) else float("nan")
        mid1 = (blk_ask[-1] + blk_bid[-1]) * 0.5 if (blk_ask[-1] > 0 and blk_bid[-1] > 0 and blk_ask[-1] >= blk_bid[-1]) else float("nan")
        d_ticks_mid = (mid1 - mid0) if (not math.isnan(mid0) and not math.isnan(mid1)) else float("nan")

        log_event(blk_ts[-1], "ABS_SCORE",
                  f"bar={b_idx};residual={residual};signed_flow={plain(signed_flow)};d_ticks={plain(d_ticks)};"
                  f"a_score={plain(a_score)};a_thr={plain(a_thr)};a_pass={a_pass};n_hist={len(abs_ring)};"
                  f"t_start={t_start_iso};n_ticks={len(blk)};dur_ms={dur_ms};spread_ticks={plain(spread_ticks)};"
                  f"d_ticks_mid={plain(d_ticks_mid)};td={trade_date}")

        # Rows
        row_ask = {}
        row_bid = {}
        for tk, v in ask_map.items():
            r = floor_div(tk, ticks_per_row)
            row_ask[r] = row_ask.get(r, 0.0) + v
        for tk, v in bid_map.items():
            r = floor_div(tk, ticks_per_row)
            row_bid[r] = row_bid.get(r, 0.0) + v

        row_keys = sorted(set(row_ask.keys()) | set(row_bid.keys()))
        close_half = 2 * c_tick
        rng = hi_px - lo_px
        wick_hi_floor = hi_px - rng * (wick_pct / 100.0)
        wick_lo_ceil = lo_px + rng * (wick_pct / 100.0)

        buy_runs = []
        sell_runs = []
        b_act = False; b_prev = -999999; b_cur = None
        s_act = False; s_prev = -999999; s_cur = None

        for r in row_keys:
            a = row_ask.get(r, 0.0)
            b = row_bid.get(r, 0.0)
            total = a + b
            skip = abs(a - b) < min_delta

            if not skip:
                if imbalance_mode == "Diagonal":
                    bDn = row_bid.get(r - 1, 0.0)
                    aUp = row_ask.get(r + 1, 0.0)
                    buy_ratio = a / max(bDn, 1.0)
                    sell_ratio = b / max(aUp, 1.0)
                else:
                    buy_ratio = a / max(b, 1.0)
                    sell_ratio = b / max(a, 1.0)
            else:
                buy_ratio = 0.0
                sell_ratio = 0.0

            row_price = (r * ticks_per_row + (ticks_per_row - 1) / 2.0) * tick_size
            row_half = 2 * r * ticks_per_row + (ticks_per_row - 1)
            contrib_buy = a if trap_vol_src == "AggressiveSide" else total
            contrib_sell = b if trap_vol_src == "AggressiveSide" else total

            buyQ = (not skip and a >= 1 and buy_ratio >= imbalance_ratio and row_half > close_half
                    and (not use_wick or (rng > 0 and row_price >= wick_hi_floor)))
            sellQ = (not skip and b >= 1 and sell_ratio >= imbalance_ratio and row_half < close_half
                     and (not use_wick or (rng > 0 and row_price <= wick_lo_ceil)))

            if buyQ:
                if b_act and r == b_prev + 1:
                    b_cur["hi"] = r
                    b_cur["vol"] += contrib_buy
                    b_cur["nrows"] += 1
                else:
                    if b_act: buy_runs.append(b_cur)
                    b_cur = dict(lo=r, hi=r, vol=contrib_buy, nrows=1)
                    b_act = True
                b_prev = r
            elif b_act:
                buy_runs.append(b_cur)
                b_act = False

            if sellQ:
                if s_act and r == s_prev + 1:
                    s_cur["hi"] = r
                    s_cur["vol"] += contrib_sell
                    s_cur["nrows"] += 1
                else:
                    if s_act: sell_runs.append(s_cur)
                    s_cur = dict(lo=r, hi=r, vol=contrib_sell, nrows=1)
                    s_act = True
                s_prev = r
            elif s_act:
                sell_runs.append(s_cur)
                s_act = False

        if b_act: buy_runs.append(b_cur)
        if s_act: sell_runs.append(s_cur)

        flow_side = 1 if signed_flow > 0 else (-1 if signed_flow < 0 else 0)

        for is_bull, runs, side_match in [(True, buy_runs, flow_side == 1), (False, sell_runs, flow_side == -1)]:
            if not a_pass:
                continue
            if require_flow_side and not side_match:
                continue

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

            z_entry = {
                "id": f"{b_idx}_{'B' if is_bull else 'S'}",
                "created_bar": b_idx,
                "is_bull": is_bull,
                "side": "trapped_buyers" if is_bull else "trapped_sellers",
                "dir": "short" if is_bull else "long",
                "lo": z_lo,
                "hi": z_hi,
                "vol": best_run["vol"],
                "nrows": best_run["nrows"],
                "frac": best_run["vol"] / max(bar_vol, 1.0),
                "touches": 0,
                "created_ms": ns_to_ms(blk_ts[-1]),
                "state": "ACTIVE",
                "ended_ms": None,
                "end_reason": None,
                "a_score": a_score,
                "a_thr": a_thr,
                "sig_ts": blk_ts[-1],
                "sig_idx": blk[-1]
            }
            active_zones.append(z_entry)
            pending_fills.append(z_entry)

            log_event(blk_ts[-1], "ZONE_CREATED",
                      f"zone_id={z_entry['id']};created_bar={b_idx};side={z_entry['side']};"
                      f"dir={z_entry['dir']};lo={plain(z_lo)};hi={plain(z_hi)};vol={plain(best_run['vol'])};"
                      f"rows={best_run['nrows']};frac={plain(z_entry['frac'])};a_score={plain(a_score)};"
                      f"a_thr={plain(a_thr)};available_at={t_end_iso};td={trade_date}")

        # Update circular ring buffer
        if not residual:
            if len(abs_ring) < abs_lookback:
                abs_ring.append(a_score)
            else:
                abs_ring.pop(0)
                abs_ring.append(a_score)

    # Main streaming loop over ticks
    for i in range(n_ticks):
        sess_i = s_ids[i]
        if cur_session is None:
            cur_session = sess_i
        elif sess_i != cur_session:
            if len(cur_block) > 0:
                flush_block(cur_block, True, cur_session)
                cur_block = []
            cur_session = sess_i

        # Fill pending zones with the first tick of the next block
        if len(pending_fills) > 0:
            px_val = float(ticks.price_ticks[i]) * tick_size
            ts_val = int(ticks.ts_ns[i])
            fill_iso = datetime.fromtimestamp(ts_val / 1e9, tz=_tz.utc).strftime("%Y-%m-%dT%H:%M:%S.%f0")
            for p_zone in pending_fills:
                p_zone["fill_px"] = px_val
                p_zone["fill_ts"] = ts_val
                p_zone["fill_idx"] = i
                zones.append(p_zone)
                sig_iso = datetime.fromtimestamp(p_zone["sig_ts"] / 1e9, tz=_tz.utc).strftime("%Y-%m-%dT%H:%M:%S.%f0")
                log_event(ts_val, "FILL",
                          f"side={p_zone['side']};dir={p_zone['dir']};fill_px={plain(px_val)};"
                          f"fill_at={fill_iso};signal_at={sig_iso};a_score={plain(p_zone['a_score'])};fill_bar={p_zone['created_bar']}")
            pending_fills = []

        cur_block.append(i)
        if len(cur_block) >= tape_window:
            flush_block(cur_block, False, cur_session)
            cur_block = []

    if len(cur_block) > 0:
        flush_block(cur_block, True, cur_session)

    # Any remaining pending fills at EOF
    if len(pending_fills) > 0:
        px_val = float(ticks.price_ticks[-1]) * tick_size
        ts_val = int(ticks.ts_ns[-1])
        fill_iso = datetime.fromtimestamp(ts_val / 1e9, tz=_tz.utc).strftime("%Y-%m-%dT%H:%M:%S.%f0")
        for p_zone in pending_fills:
            p_zone["fill_px"] = px_val
            p_zone["fill_ts"] = ts_val
            p_zone["fill_idx"] = n_ticks - 1
            zones.append(p_zone)
            sig_iso = datetime.fromtimestamp(p_zone["sig_ts"] / 1e9, tz=_tz.utc).strftime("%Y-%m-%dT%H:%M:%S.%f0")
            log_event(ts_val, "FILL",
                      f"side={p_zone['side']};dir={p_zone['dir']};fill_px={plain(px_val)};"
                      f"fill_at={fill_iso};signal_at={sig_iso};a_score={plain(p_zone['a_score'])};fill_bar={p_zone['created_bar']}")
        pending_fills = []

    return dict(
        indicator=NAME,
        params=p,
        zones=zones,
        n_zones=len(zones),
        events=events
    )
