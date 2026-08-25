#!/usr/bin/env python3
"""Runner canónico de exportación de BigTrap2Absorption v1.1.1 para MBT.

Genera los archivos de export exactos con contrato v1.1.1 (BARRA_PROCESADA,
ABS_SCORE, TRAP, ZONE_CREATED, FILL) sobre la cinta de ticks especificada.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import sys
from datetime import datetime, timezone as _tz
from pathlib import Path
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.bars import session_ids
from tools.sweep_bigtrap2_tickframes import load_canonical_ticks

IND_VERSION = "1.1.1"


def round_away_from_zero(val: float) -> int:
    if val >= 0:
        return int(math.floor(val + 0.5))
    else:
        return int(math.ceil(val - 0.5))


def percentile(arr: list[float], q: float) -> float:
    n = len(arr)
    if n == 0:
        return float("nan")
    if n == 1:
        return float(arr[0])
    tmp = sorted(arr)
    qq = 0.0 if q < 0.0 else (100.0 if q > 100.0 else float(q))
    pos = (qq / 100.0) * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo < 0:
        lo = 0
    if hi >= n:
        hi = n - 1
    if lo == hi:
        return float(tmp[lo])
    return float(tmp[lo] + (tmp[hi] - tmp[lo]) * (pos - lo))


def fmt_iso(t_ns: int) -> str:
    dt = datetime.fromtimestamp(t_ns / 1e9, tz=_tz.utc)
    # Formato con 7 digitos de fraccion
    frac_7 = f"{(t_ns % 1_000_000_000) // 100:07d}"
    return f"{dt.strftime('%Y-%m-%dT%H:%M:%S')}.{frac_7}"


def fmt_float(v: float) -> str:
    if math.isnan(v):
        return "NaN"
    if v == int(v) and not math.isinf(v):
        # si es entero exacto
        return str(v)
    return str(v)


def run_export(
    tape_path: Path,
    out_dir: Path,
    tape_window_ticks: int = 25,
    tick_size: float = 5.0,
    score_mode: str = "AbsDirectional",
    absorption_pct: float = 90.0,
    absorption_lookback: int = 500,
    min_history_buckets: int = 200,
    require_flow_side_match: bool = True,
    imbalance_mode: str = "Diagonal",
    trap_volume_source: str = "AggressiveSide",
    ticks_per_row: int = 1,
    imbalance_ratio: float = 3.0,
    min_stacked_rows: int = 2,
    min_trap_frac: float = 0.20,
    min_delta_filter: float = 0.0,
    min_trap_volume: float = 0.0,
    min_export_volume: float = 1.0,
    use_wick_filter: bool = True,
    wick_zone_pct: float = 30.0,
    invalidation_mode: str = "CloseThrough",
    max_touches: int = 0,
    max_age_bars: int = 2000,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"mbt_export__TW{tape_window_ticks}.csv"
    k = 2
    while out_path.exists():
        out_path = out_dir / f"mbt_export__TW{tape_window_ticks}_{k}.csv"
        k += 1

    print(f"[*] Procesando {tape_path.name} con TW={tape_window_ticks} -> {out_path.name}...")
    ticks, _, _, _, _, _ = load_canonical_ticks(tape_path, tick_size=tick_size)
    n_ticks_total = len(ticks)

    # Session IDs
    s_ids = session_ids(ticks.ts_ns)
    trade_dates = pd.to_datetime(s_ids * 86400, unit="s").strftime("%Y%m%d").values

    ring_cap = max(20, absorption_lookback)
    abs_ring = [0.0] * ring_cap
    abs_count = 0
    abs_pos = 0

    cur_block: list[dict] = []
    skipped_first = False
    analyze_bar_seq = 0
    event_seq = 0

    last_tick_price = float("nan")
    last_tick_dir = 0

    class PendingFill:
        def __init__(self, is_bull, zone_lo, zone_hi, volume, score, signal_at):
            self.is_bull = is_bull
            self.zone_lo = zone_lo
            self.zone_hi = zone_hi
            self.volume = volume
            self.score = score
            self.signal_at = signal_at

    pending: list[PendingFill] = []
    active_zones: list[dict] = []

    def get_ring_slice():
        if abs_count < ring_cap:
            return abs_ring[:abs_count]
        return abs_ring[:]

    def push_abs(val: float):
        nonlocal abs_pos, abs_count
        abs_ring[abs_pos] = val
        abs_pos = (abs_pos + 1) % ring_cap
        if abs_count < ring_cap:
            abs_count += 1

    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        # Header # meta
        fh.write(
            f"# meta indicator=BigTrap2Absorption,version={IND_VERSION}"
            f",attribution=self_cut_1tick,classifier=bidask_then_tickrule"
            f",export=v1.1_context_keys,fill_anchor=bar_index"
            f",tape_window={max(2, tape_window_ticks)}"
            f",score_mode={score_mode}"
            f",absorption_pct={absorption_pct}"
            f",absorption_lookback={absorption_lookback}"
            f",min_history={min_history_buckets}"
            f",require_flow_side_match={require_flow_side_match}"
            f",imbalance_mode={imbalance_mode}"
            f",trap_volume={trap_volume_source}"
            f",ticks_per_row={ticks_per_row}"
            f",imbalance_ratio={imbalance_ratio}"
            f",min_stacked_rows={min_stacked_rows}"
            f",min_trap_frac={min_trap_frac}"
            f",min_trap_volume={min_trap_volume}"
            f",min_export_volume={min_export_volume}"
            f",wick_filter={use_wick_filter}"
            f",wick_zone_pct={wick_zone_pct}"
            f",min_delta={min_delta_filter}"
            f",invalidation={invalidation_mode}"
            f",max_age_bars={max_age_bars}"
            f",tick_size={tick_size}\n"
        )

        def log_event(t_ns: int, ev_type: str, payload: str):
            nonlocal event_seq
            iso_t = fmt_iso(t_ns)
            fh.write(f"{event_seq}|{iso_t}|{ev_type}|{payload}\n")
            event_seq += 1

        def fill_pendings(ev_tick: dict):
            if not pending:
                return
            px = ev_tick["tick"] * tick_size
            t_ns = ev_tick["time_ns"]
            for p in pending:
                side_str = "trapped_buyers" if p.is_bull else "trapped_sellers"
                dir_str = "short" if p.is_bull else "long"
                fill_iso = fmt_iso(t_ns)
                sig_iso = fmt_iso(p.signal_at)
                log_event(
                    t_ns,
                    "FILL",
                    f"side={side_str};dir={dir_str};fill_px={px};fill_at={fill_iso};signal_at={sig_iso};a_score={p.score};fill_bar={analyze_bar_seq}",
                )
            pending.clear()

        def update_zones(s: dict):
            if not active_zones:
                return
            hi = s["High"]
            lo = s["Low"]
            close = s["Close"]
            for i in range(len(active_zones) - 1, -1, -1):
                z = active_zones[i]
                if max_age_bars > 0 and (s["Bar"] - z["CreatedBar"]) > max_age_bars:
                    log_event(s["Time_ns"], "ZONE_EXPIRED", f"bar={s['Bar']}")
                    active_zones.pop(i)
                    continue
                z_lo = z["LoTick"] * tick_size - tick_size / 2.0
                z_hi = z["HiTick"] * tick_size + tick_size / 2.0
                touched = (hi >= z_lo and lo <= z_hi)
                adverse = (close > z_hi) if z["IsBull"] else (close < z_lo)
                if touched:
                    z["Touches"] += 1
                reason = None
                if invalidation_mode == "FirstTouch" and touched:
                    reason = "first_touch"
                elif invalidation_mode == "CloseThrough" and adverse:
                    reason = "close_through"
                elif max_touches > 0 and z["Touches"] >= max_touches:
                    reason = "max_touches"
                if reason is not None:
                    log_event(s["Time_ns"], "ZONE_INVALIDATED", f"reason={reason};bar={s['Bar']}")
                    active_zones.pop(i)

        def flush_block(residual: bool, trade_date: str):
            nonlocal skipped_first, analyze_bar_seq
            if len(cur_block) == 0:
                return
            if not skipped_first:
                cur_block.clear()
                skipped_first = True
                return

            analyze_bar_seq += 1
            f0 = cur_block[0]
            f1 = cur_block[-1]
            o_tick = f0["tick"]
            c_tick = f1["tick"]
            mn_tick = min(e["tick"] for e in cur_block)
            mx_tick = max(e["tick"] for e in cur_block)
            bar_vol = sum(e["vol"] for e in cur_block)

            # Mid calculation
            mid_o = (f0["bid"] + f0["ask"]) * 0.5 if (f0["bid"] > 0 and f0["ask"] > 0 and f0["ask"] >= f0["bid"]) else float("nan")
            mid_c = (f1["bid"] + f1["ask"]) * 0.5 if (f1["bid"] > 0 and f1["ask"] > 0 and f1["ask"] >= f1["bid"]) else float("nan")
            d_ticks_mid = ((mid_c - mid_o) / tick_size) if (not math.isnan(mid_o) and not math.isnan(mid_c)) else float("nan")
            spread_close_ticks = ((f1["ask"] - f1["bid"]) / tick_size) if (f1["bid"] > 0 and f1["ask"] > 0 and f1["ask"] >= f1["bid"]) else float("nan")
            dur_ms = int((f1["time_ns"] - f0["time_ns"]) // 1_000_000)

            s = {
                "Bar": analyze_bar_seq,
                "OpenTick": o_tick,
                "CloseTick": c_tick,
                "Open": o_tick * tick_size,
                "High": mx_tick * tick_size,
                "Low": mn_tick * tick_size,
                "Close": c_tick * tick_size,
                "Volume": bar_vol,
                "Time_ns": f1["time_ns"],
                "StartTime_ns": f0["time_ns"],
                "NTicks": len(cur_block),
                "DurMs": dur_ms,
                "SpreadCloseTicks": spread_close_ticks,
                "DTicksMid": d_ticks_mid,
                "TradeDate": trade_date,
            }

            update_zones(s)

            log_event(
                s["Time_ns"],
                "BARRA_PROCESADA",
                f"bar={s['Bar']};largo={s['NTicks']};residual={residual};tape_window={max(2, tape_window_ticks)};td={s['TradeDate']}",
            )

            ask_map: dict[int, float] = {}
            bid_map: dict[int, float] = {}
            fp_vol = 0.0
            signed_flow = 0.0
            n_quote = 0
            n_rule = 0

            for e in cur_block:
                m = ask_map if e["side"] > 0 else bid_map
                m[e["tick"]] = m.get(e["tick"], 0.0) + e["vol"]
                fp_vol += e["vol"]
                signed_flow += (e["vol"] if e["side"] > 0 else -e["vol"])
                if e["by_quote"]:
                    n_quote += 1
                else:
                    n_rule += 1

            d_px = float(c_tick - o_tick)
            if score_mode == "AbsDirectional":
                sgn = 1.0 if signed_flow > 0 else (-1.0 if signed_flow < 0 else 0.0)
                denom = 1.0 + max(0.0, sgn * d_px)
            else:
                denom = 1.0 + abs(d_px)
            a_score = abs(signed_flow) / denom

            a_thr = float("nan")
            if absorption_pct <= 0.0:
                a_pass = True
            elif abs_count >= max(1, min_history_buckets):
                a_thr = percentile(get_ring_slice(), absorption_pct)
                a_pass = (a_score >= a_thr)
            else:
                a_pass = False

            if residual:
                a_pass = False

            log_event(
                s["Time_ns"],
                "ABS_SCORE",
                f"bar={s['Bar']};residual={residual};signed_flow={signed_flow};d_ticks={d_px};a_score={a_score};a_thr={a_thr};a_pass={a_pass};n_hist={abs_count};t_start={fmt_iso(s['StartTime_ns'])};n_ticks={s['NTicks']};dur_ms={s['DurMs']};spread_ticks={s['SpreadCloseTicks']};d_ticks_mid={s['DTicksMid']};td={s['TradeDate']}",
            )

            if ask_map or bid_map:
                process_bar(s, ask_map, bid_map, fp_vol, n_quote, n_rule, signed_flow, d_px, a_score, a_thr, a_pass)

            if not residual:
                push_abs(a_score)

            cur_block.clear()

        def process_bar(s, ask_map, bid_map, fp_vol, n_quote, n_rule, signed_flow, d_px, a_score, a_thr, a_pass):
            row_ticks = max(1, ticks_per_row)
            row_ask: dict[int, float] = {}
            row_bid: dict[int, float] = {}
            for tk, v in ask_map.items():
                r = tk // row_ticks
                row_ask[r] = row_ask.get(r, 0.0) + v
            for tk, v in bid_map.items():
                r = tk // row_ticks
                row_bid[r] = row_bid.get(r, 0.0) + v

            row_keys = sorted(set(row_ask.keys()) | set(row_bid.keys()))
            if not row_keys:
                return

            close = s["Close"]
            close_half_tick = 2 * round_away_from_zero(close / tick_size)
            lo = s["Low"]
            hi = s["High"]
            rng = hi - lo
            wick_hi_floor = hi - rng * (wick_zone_pct / 100.0)
            wick_lo_ceil = lo + rng * (wick_zone_pct / 100.0)

            buy_vol = 0.0; buy_w_sum = 0.0; buy_max_ratio = 0.0
            buy_lo = 10**12; buy_hi = -10**12; buy_rows = 0
            sell_vol = 0.0; sell_w_sum = 0.0; sell_max_ratio = 0.0
            sell_lo = 10**12; sell_hi = -10**12; sell_rows = 0

            buy_runs: list[dict] = []
            sell_runs: list[dict] = []
            b_act = False; b_prev = -10**12; b_cur: dict = {}
            s_act = False; s_prev = -10**12; s_cur: dict = {}

            for r in row_keys:
                a = row_ask.get(r, 0.0)
                b = row_bid.get(r, 0.0)
                total = a + b
                skip = abs(a - b) < min_delta_filter

                buy_ratio = 0.0
                sell_ratio = 0.0
                if not skip:
                    if imbalance_mode == "Diagonal":
                        b_dn = row_bid.get(r - 1, 0.0)
                        a_up = row_ask.get(r + 1, 0.0)
                        buy_ratio = a / max(b_dn, 1.0)
                        sell_ratio = b / max(a_up, 1.0)
                    else:
                        buy_ratio = a / max(b, 1.0)
                        sell_ratio = b / max(a, 1.0)

                row_price = (r * row_ticks + (row_ticks - 1) / 2.0) * tick_size
                row_half_tick = 2 * r * row_ticks + (row_ticks - 1)
                contrib_buy = a if trap_volume_source == "AggressiveSide" else total
                contrib_sell = b if trap_volume_source == "AggressiveSide" else total

                buy_q = (
                    not skip
                    and a >= 1
                    and buy_ratio >= imbalance_ratio
                    and row_half_tick > close_half_tick
                    and (not use_wick_filter or (rng > 0 and row_price >= wick_hi_floor))
                )
                sell_q = (
                    not skip
                    and b >= 1
                    and sell_ratio >= imbalance_ratio
                    and row_half_tick < close_half_tick
                    and (not use_wick_filter or (rng > 0 and row_price <= wick_lo_ceil))
                )

                if buy_q:
                    buy_vol += contrib_buy
                    buy_w_sum += row_price * contrib_buy
                    buy_rows += 1
                    if r < buy_lo: buy_lo = r
                    if r > buy_hi: buy_hi = r
                    if buy_ratio > buy_max_ratio: buy_max_ratio = buy_ratio

                    if b_act and r == b_prev + 1:
                        b_cur["hi"] = r
                        b_cur["vol"] += contrib_buy
                        b_cur["w_sum"] += row_price * contrib_buy
                        b_cur["n_rows"] += 1
                        if buy_ratio > b_cur["max_ratio"]:
                            b_cur["max_ratio"] = buy_ratio
                    else:
                        if b_act: buy_runs.append(b_cur)
                        b_cur = {"lo": r, "hi": r, "vol": contrib_buy, "w_sum": row_price * contrib_buy, "max_ratio": buy_ratio, "n_rows": 1}
                        b_act = True
                    b_prev = r
                elif b_act:
                    buy_runs.append(b_cur)
                    b_act = False

                if sell_q:
                    sell_vol += contrib_sell
                    sell_w_sum += row_price * contrib_sell
                    sell_rows += 1
                    if r < sell_lo: sell_lo = r
                    if r > sell_hi: sell_hi = r
                    if sell_ratio > sell_max_ratio: sell_max_ratio = sell_ratio

                    if s_act and r == s_prev + 1:
                        s_cur["hi"] = r
                        s_cur["vol"] += contrib_sell
                        s_cur["w_sum"] += row_price * contrib_sell
                        s_cur["n_rows"] += 1
                        if sell_ratio > s_cur["max_ratio"]:
                            s_cur["max_ratio"] = sell_ratio
                    else:
                        if s_act: sell_runs.append(s_cur)
                        s_cur = {"lo": r, "hi": r, "vol": contrib_sell, "w_sum": row_price * contrib_sell, "max_ratio": sell_ratio, "n_rows": 1}
                        s_act = True
                    s_prev = r
                elif s_act:
                    sell_runs.append(s_cur)
                    s_act = False

            if b_act: buy_runs.append(b_cur)
            if s_act: sell_runs.append(s_cur)

            flow_side = 1 if signed_flow > 0 else (-1 if signed_flow < 0 else 0)

            emit_side(s, True, buy_vol, buy_w_sum, buy_lo, buy_hi, buy_rows, buy_max_ratio, buy_runs,
                      fp_vol, n_quote, n_rule, row_ticks, signed_flow, d_px, a_score, a_thr, a_pass, flow_side == 1)
            emit_side(s, False, sell_vol, sell_w_sum, sell_lo, sell_hi, sell_rows, sell_max_ratio, sell_runs,
                      fp_vol, n_quote, n_rule, row_ticks, signed_flow, d_px, a_score, a_thr, a_pass, flow_side == -1)

        def emit_side(s, is_bull, vol, w_sum, lo_row, hi_row, n_rows, max_ratio, runs,
                      fp_vol, n_quote, n_rule, row_ticks, signed_flow, d_px, a_score, a_thr, a_pass, side_match):
            if n_rows == 0 or vol <= 0 or vol < min_export_volume:
                return

            centroid = w_sum / vol
            lo_tick = lo_row * row_ticks
            hi_tick = (hi_row + 1) * row_ticks - 1
            zone_lo = lo_tick * tick_size - tick_size / 2.0
            zone_hi = hi_tick * tick_size + tick_size / 2.0
            bar_vol = s["Volume"] if s["Volume"] > 0 else 1.0
            trap_frac = vol / bar_vol

            min_rows = max(1, min_stacked_rows)
            i_k = -1
            for i, r in enumerate(runs):
                if r["n_rows"] >= min_rows and (i_k < 0 or r["vol"] > runs[i_k]["vol"]):
                    i_k = i

            has_run = (i_k >= 0)
            run_vol = runs[i_k]["vol"] if has_run else 0.0
            run_rows = runs[i_k]["n_rows"] if has_run else 0
            run_frac = run_vol / bar_vol
            run_lo_tick = runs[i_k]["lo"] * row_ticks if has_run else 0
            run_hi_tick = (runs[i_k]["hi"] + 1) * row_ticks - 1 if has_run else 0
            run_zone_lo = run_lo_tick * tick_size - tick_size / 2.0 if has_run else 0.0
            run_zone_hi = run_hi_tick * tick_size + tick_size / 2.0 if has_run else 0.0
            run_centroid = (runs[i_k]["w_sum"] / run_vol) if (has_run and run_vol > 0) else 0.0

            side_name = "trapped_buyers" if is_bull else "trapped_sellers"
            dir_name = "short" if is_bull else "long"

            log_event(
                s["Time_ns"],
                "TRAP",
                f"bar={s['Bar']};side={side_name};vol={vol};centroid={centroid};zone_lo={zone_lo};zone_hi={zone_hi};n_rows={n_rows};max_ratio={max_ratio};close={s['Close']};bar_vol={s['Volume']};fp_vol={fp_vol};n_quote={n_quote};n_rule={n_rule};trap_frac={trap_frac};signed_flow={signed_flow};d_ticks={d_px};a_score={a_score};a_thr={a_thr};a_pass={a_pass};side_match={side_match};n_runs={len(runs)};run_vol={run_vol};run_rows={run_rows};run_frac={run_frac};run_lo={run_zone_lo};run_hi={run_zone_hi};run_centroid={run_centroid};available_at={fmt_iso(s['Time_ns'])};t_start={fmt_iso(s['StartTime_ns'])};n_ticks={s['NTicks']};dur_ms={s['DurMs']};spread_ticks={s['SpreadCloseTicks']};d_ticks_mid={s['DTicksMid']};td={s['TradeDate']}",
            )

            if not a_pass: return
            if require_flow_side_match and not side_match: return
            if not has_run: return
            if run_vol < min_trap_volume: return
            if run_frac < min_trap_frac: return

            pending.append(
                PendingFill(
                    is_bull=is_bull,
                    zone_lo=run_zone_lo,
                    zone_hi=run_zone_hi,
                    volume=run_vol,
                    score=a_score,
                    signal_at=s["Time_ns"],
                )
            )
            active_zones.append(
                {
                    "CreatedBar": s["Bar"],
                    "CreatedAt_ns": s["Time_ns"],
                    "IsBull": is_bull,
                    "LoTick": run_lo_tick,
                    "HiTick": run_hi_tick,
                    "Volume": run_vol,
                    "Touches": 0,
                }
            )
            log_event(
                s["Time_ns"],
                "ZONE_CREATED",
                f"zone_id={s['Bar']}_{'B' if is_bull else 'S'};created_bar={s['Bar']};side={side_name};dir={dir_name};lo={run_zone_lo};hi={run_zone_hi};vol={run_vol};rows={run_rows};frac={run_frac};a_score={a_score};a_thr={a_thr};available_at={fmt_iso(s['Time_ns'])};td={s['TradeDate']}",
            )

        # Main tick loop
        cur_td = None
        for i in range(n_ticks_total):
            t_ns = int(ticks.ts_ns[i])
            px = float(ticks.price_ticks[i]) * tick_size
            vol = float(ticks.volume[i])
            bid = float(ticks.bid_ticks[i]) * tick_size if ticks.bid_ticks is not None else 0.0
            ask = float(ticks.ask_ticks[i]) * tick_size if ticks.ask_ticks is not None else 0.0
            td = trade_dates[i]

            side = 0
            by_quote = False
            if ask > 0 and bid > 0 and ask >= bid:
                if px >= ask:
                    side = 1
                    by_quote = True
                elif px <= bid:
                    side = -1
                    by_quote = True
            if side == 0:
                if not math.isnan(last_tick_price):
                    if px > last_tick_price:
                        side = 1
                    elif px < last_tick_price:
                        side = -1
                    else:
                        side = last_tick_dir
                if side == 0:
                    side = 1
            last_tick_price = px
            last_tick_dir = side

            tick_idx = round_away_from_zero(px / tick_size)
            ev = {
                "tick": tick_idx,
                "vol": vol,
                "side": side,
                "by_quote": by_quote,
                "time_ns": t_ns,
                "bid": bid,
                "ask": ask,
            }

            if cur_td is None:
                cur_td = td
            elif td != cur_td:
                if cur_block:
                    flush_block(residual=True, trade_date=cur_td)
                cur_td = td

            fill_pendings(ev)
            cur_block.append(ev)
            if len(cur_block) >= max(2, tape_window_ticks):
                flush_block(residual=False, trade_date=cur_td)

        # End of tape flush
        if cur_block:
            flush_block(residual=True, trade_date=cur_td)

    # Compute sha256 and bytes
    h = hashlib.sha256()
    size = out_path.stat().st_size
    with open(out_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    sha = h.hexdigest()
    print(f"    -> Terminado: {out_path.name} ({size:,} bytes, sha256: {sha[:16]}...)")
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Generar export MBT BigTrap2Absorption")
    ap.add_argument("--tape", default="E:/DatosNT8/MBT 08-26.Last.txt")
    ap.add_argument("--out-dir", default="E:/DatosNT8/mbt_apriori")
    ap.add_argument("--tw", type=int, nargs="+", default=[10, 15, 25, 50])
    ap.add_argument("--tick-size", type=float, default=5.0)
    args = ap.parse_args()

    tape_path = Path(args.tape)
    out_dir = Path(args.out_dir)
    for tw in args.tw:
        run_export(tape_path, out_dir, tape_window_ticks=tw, tick_size=args.tick_size)


if __name__ == "__main__":
    main()
