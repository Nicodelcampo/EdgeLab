"""BigTrapNQ v1.0 — Indicador de detección de trampas y absorción rediseñado para Nasdaq (NQ).

Diferencias estructurales respecto a BigTrap2 / BigTrap2Absorption:
1. Dynamic Bracket Pooling: Agrupación en micro-bloques de 2 a 4 ticks (0.50 a 1.00 pt en NQ),
   evitando la fragmentación de volumen que produce ticks_per_row=1 en índices volátiles.
2. Dwell-Time & Tape Deceleration: Mide el tiempo de permanencia (milisegundos) y la velocidad
   de ticks en el extremo de la mecha, discriminando absorción pasiva real de barridas de
   liquidez / corridas de stop sin freno (flash sweeps).
3. Clock & Causal RVol Scaling: Clasifica la sesión CME en 4 regímenes de reloj (RTH_OPEN,
   RTH_CORE, RTH_CLOSE, GLOBEX) y calcula el volumen relativo (RVol) respecto a la mediana
   causal de esa franja, sustituyendo umbrales rígidos de contratos.
4. Buffer Anti-Overshoot: Protección geométrica contra la excursión local adversa de 2 a 4 ticks
   típica de las cascadas de stops en NQ.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone as _tz
from typing import Any, Dict, List, Optional
import numpy as np

from ..common import floor_div, ns_to_ms, plain, tz_of
from edgelab.research.nq_microstructure import (
    classify_cme_clock_regime,
    compute_dwell_and_speed_at_extreme,
    CausalRVolTracker,
    CLOCK_RTH_OPEN,
    CLOCK_RTH_CORE,
    CLOCK_RTH_CLOSE,
    CLOCK_GLOBEX,
)

NAME = "BigTrapNQ"

DEFAULTS = dict(
    ticks_per_row=2,                # Filas de 2 ticks (0.50 pt)
    bracket_pooling_ticks=4,        # Pooling de hasta 4 ticks contiguos (1.00 pt)
    imbalance_ratio=2.5,            # Ratio agresor vs opuesto en el cluster
    min_trap_volume=40.0,           # Volumen mínimo en contratos del cluster
    min_export_volume=1.0,          # Umbral de exportación continua para research
    use_wick_filter=True,           # Restricción a zona de mecha
    wick_zone_pct=35.0,             # Mecha superior/inferior (35%)
    use_dwell_filter=True,          # Filtro de permanencia / deceleración
    min_dwell_ms=100.0,             # Mínimo 100 ms de lucha en el extremo
    max_tape_speed=500.0,           # Máxima velocidad tolerada (ticks/segundo en el extremo)
    use_dwell_fraction=False,       # Fracción de tiempo de la barra en el extremo
    min_dwell_fraction=0.25,        # Mínimo 25% de la vida de la barra en el extremo
    use_rvol_filter=True,           # Filtro de volumen relativo causal
    min_rvol=1.1,                   # Mínimo 1.1x la mediana causal del horario
    require_finished_auction=False, # Subasta terminada en extremo (sin volumen cruzado en el pico)
    finished_auction_tol=0.0,       # Tolerancia de contratos en lado opuesto del extremo
    require_delta_exhaustion=False, # Delta de la barra adverso al trap (vendedores ganaron la barra)
    require_poc_in_wick=False,      # POC de la barra concentrado en la mecha de rechazo
    anti_overshoot_buffer_ticks=2,  # Buffer de 2 ticks en la zona contra stop-runs
    invalidation_mode="CloseThrough",  # CloseThrough o FirstTouch
    max_age_bars=2000,
    max_touches=0,
)

PARAM_SPEC = {
    "ticks_per_row": {"type": "int", "default": 2, "min": 1, "max": 8},
    "bracket_pooling_ticks": {"type": "int", "default": 4, "min": 2, "max": 16},
    "imbalance_ratio": {"type": "float", "default": 2.5, "min": 1.5, "max": 10.0},
    "min_trap_volume": {"type": "float", "default": 40.0, "min": 0.0, "max": 1000.0},
    "min_export_volume": {"type": "float", "default": 1.0, "min": 0.0},
    "use_wick_filter": {"type": "bool", "default": True},
    "wick_zone_pct": {"type": "float", "default": 35.0, "min": 10.0, "max": 50.0},
    "use_dwell_filter": {"type": "bool", "default": True},
    "min_dwell_ms": {"type": "float", "default": 100.0, "min": 0.0, "max": 5000.0},
    "max_tape_speed": {"type": "float", "default": 500.0, "min": 50.0, "max": 5000.0},
    "use_dwell_fraction": {"type": "bool", "default": False},
    "min_dwell_fraction": {"type": "float", "default": 0.25, "min": 0.05, "max": 0.90},
    "use_rvol_filter": {"type": "bool", "default": True},
    "min_rvol": {"type": "float", "default": 1.1, "min": 0.5, "max": 5.0},
    "require_finished_auction": {"type": "bool", "default": False},
    "finished_auction_tol": {"type": "float", "default": 0.0, "min": 0.0, "max": 10.0},
    "require_delta_exhaustion": {"type": "bool", "default": False},
    "require_poc_in_wick": {"type": "bool", "default": False},
    "anti_overshoot_buffer_ticks": {"type": "int", "default": 2, "min": 0, "max": 8},
    "invalidation_mode": {"type": "str", "default": "CloseThrough", "choices": ["CloseThrough", "FirstTouch"]},
    "max_age_bars": {"type": "int", "default": 2000, "min": 1},
    "max_touches": {"type": "int", "default": 0, "min": 0},
}


def _iso_o(ns: int, tz) -> str:
    """Formato ISO con 7 decimales de segundos."""
    d = datetime.fromtimestamp(ns / 1e9, tz=_tz.utc).astimezone(tz)
    frac = int(ns % 1_000_000_000) // 100
    return d.strftime("%Y-%m-%dT%H:%M:%S") + ".%07d" % frac


def meta_line(p: dict, instrument: str, tick_size: float) -> str:
    return (
        f"# meta indicator={NAME},version=1.0,instrument={instrument},tick_size={tick_size},"
        f"ticks_per_row={p['ticks_per_row']},bracket_pooling={p['bracket_pooling_ticks']},"
        f"imbalance_ratio={p['imbalance_ratio']},min_trap_vol={p['min_trap_volume']},"
        f"use_dwell={p['use_dwell_filter']},min_dwell_ms={p['min_dwell_ms']},"
        f"use_rvol={p['use_rvol_filter']},min_rvol={p['min_rvol']},"
        f"invalidation={p['invalidation_mode']}"
    )


def run(ticks, bars, footprints, params: Optional[dict] = None, chart_tz: str = "America/Chicago") -> dict:
    """Ejecuta el kernel BigTrapNQ sobre una serie de barras y footprints reconstruidos."""
    p = {**DEFAULTS, **(params or {})}
    tz = tz_of(chart_tz)
    tick_size = float(ticks.tick_size)

    rows_out: List[dict] = []
    lines: List[str] = []
    active: List[dict] = []
    all_zones: List[dict] = []
    seq = 0

    # RVol tracker causal
    rvol_tracker = CausalRVolTracker()

    # Pre-clasificación de regímenes de reloj para todas las barras
    bar_regimes = classify_cme_clock_regime(bars.end_ns, tz_name=chart_tz)

    # Localizar inicios y finales de ticks por barra O(N)
    n_ticks = len(ticks)
    if n_ticks > 0 and len(bars) > 0:
        bar_changes = np.flatnonzero(np.diff(bars.tick_bar_idx)) + 1
        bar_starts = np.concatenate(([0], bar_changes))
        bar_ends = np.concatenate((bar_changes, [n_ticks]))
    else:
        bar_starts = np.zeros(len(bars), dtype=int)
        bar_ends = np.zeros(len(bars), dtype=int)

    def log_event(etype: str, payload: str, t_ns: int, bar: int, zone: Optional[dict] = None, touches: int = 0, reason: str = ""):
        nonlocal seq
        lines.append(f"{seq}|{_iso_o(t_ns, tz)}|{etype}|{payload}")
        rows_out.append(dict(
            seq=seq, type=etype, ts_ns=int(t_ns), unix_ms=ns_to_ms(t_ns),
            bar_index=bar, zone_id=None if zone is None else zone["id"],
            touch_count=touches, reason=reason
        ))
        seq += 1

    def zone_desc(z: dict) -> str:
        return (
            f"zone_id={z['id']};created_bar={z['created_bar']};"
            f"side={'trapped_buyers' if z['is_bull'] else 'trapped_sellers'};"
            f"lo={plain(z['lo'])};hi={plain(z['hi'])};vol={plain(z['vol'])}"
        )

    def update_zones(b: int, t_ns: int):
        if not active:
            return
        hi = float(bars.high_t[b]) * tick_size
        lo = float(bars.low_t[b]) * tick_size
        close = float(bars.close_t[b]) * tick_size

        for z in list(active):
            # Expiración por edad máxima
            if p["max_age_bars"] > 0 and b - z["created_bar"] > p["max_age_bars"]:
                log_event("ZONE_EXPIRED", zone_desc(z) + f";bar={b}", t_ns, b,
                          zone=z, touches=z["touches"], reason="max_age")
                z.update(state="EXPIRED", ended_ms=ns_to_ms(t_ns), end_reason="max_age")
                active.remove(z)
                continue

            touched = (hi >= z["lo"]) and (lo <= z["hi"])
            if touched:
                z["touches"] += 1
                log_event("ZONE_TOUCHED", zone_desc(z) + f";bar={b};touches={z['touches']}",
                          t_ns, b, zone=z, touches=z["touches"])

            adverse_close = (close > z["hi"]) if z["is_bull"] else (close < z["lo"])
            reason = None

            if p["invalidation_mode"] == "FirstTouch" and touched:
                reason = "first_touch"
            elif p["invalidation_mode"] == "CloseThrough" and adverse_close:
                reason = "close_through" if touched else "close_through_gap"

            if reason is None and p["max_touches"] > 0 and z["touches"] >= p["max_touches"]:
                reason = "max_touches"

            if reason is not None:
                log_event("ZONE_INVALIDATED", zone_desc(z) + f";reason={reason};bar={b}",
                          t_ns, b, zone=z, touches=z["touches"], reason=reason)
                z.update(state="INVALIDATED", ended_ms=ns_to_ms(t_ns), end_reason=reason)
                active.remove(z)

    def process_bar(b: int, t_ns: int, ask_map: dict, bid_map: dict):
        bar_vol = float(bars.volume[b])
        regime = str(bar_regimes[b])
        rvol = rvol_tracker.get_rvol(regime, bar_vol)
        rvol_tracker.record_bar_volume(regime, bar_vol)

        row_ticks = max(1, int(p["ticks_per_row"]))
        row_ask: Dict[int, float] = {}
        row_bid: Dict[int, float] = {}

        for tk, v in ask_map.items():
            r = floor_div(int(tk), row_ticks)
            row_ask[r] = row_ask.get(r, 0.0) + float(v)
        for tk, v in bid_map.items():
            r = floor_div(int(tk), row_ticks)
            row_bid[r] = row_bid.get(r, 0.0) + float(v)

        row_keys = sorted(set(row_ask) | set(row_bid))
        if not row_keys:
            return

        close = float(bars.close_t[b]) * tick_size
        lo = float(bars.low_t[b]) * tick_size
        hi = float(bars.high_t[b]) * tick_size
        rng = hi - lo
        wick_hi_floor = hi - rng * (float(p["wick_zone_pct"]) / 100.0)
        wick_lo_ceil = lo + rng * (float(p["wick_zone_pct"]) / 100.0)

        # Buscar clusters de desbalance en extremos
        # Lado comprador (Trapped Buyers): por encima del close
        buy_imbalances = []
        for r in row_keys:
            a = row_ask.get(r, 0.0)
            bv = row_bid.get(r - 1, 0.0)
            ratio = a / max(bv, 1.0)
            row_px = (r * row_ticks + (row_ticks - 1) / 2.0) * tick_size
            if a >= 1 and ratio >= p["imbalance_ratio"] and row_px > close:
                if not p["use_wick_filter"] or (rng > 0 and row_px >= wick_hi_floor):
                    buy_imbalances.append((r, a, bv, ratio, row_px))

        # Lado vendedor (Trapped Sellers): por debajo del close
        sell_imbalances = []
        for r in row_keys:
            bv = row_bid.get(r, 0.0)
            a = row_ask.get(r + 1, 0.0)
            ratio = bv / max(a, 1.0)
            row_px = (r * row_ticks + (row_ticks - 1) / 2.0) * tick_size
            if bv >= 1 and ratio >= p["imbalance_ratio"] and row_px < close:
                if not p["use_wick_filter"] or (rng > 0 and row_px <= wick_lo_ceil):
                    sell_imbalances.append((r, bv, a, ratio, row_px))

        # Evaluar microestructura y dwell en ticks reales de la barra
        t_start_i = bar_starts[b]
        t_end_i = bar_ends[b]
        bar_dur_ms = max(1.0, (bars.end_ns[b] - bars.start_ns[b]) / 1e6)
        bar_delta = sum(ask_map.values()) - sum(bid_map.values())

        # Cálculo de POC de la barra
        tot_by_tk = {tk: ask_map.get(tk, 0.0) + bid_map.get(tk, 0.0) for tk in (set(ask_map) | set(bid_map))}
        poc_tk = max(tot_by_tk, key=tot_by_tk.get) if tot_by_tk else 0
        poc_px = poc_tk * tick_size

        # Subasta en extremos absolutos (Finished vs Unfinished Auction)
        hi_bar_tk = int(bars.high_t[b])
        lo_bar_tk = int(bars.low_t[b])
        is_finished_hi = (bid_map.get(hi_bar_tk, 0.0) <= p["finished_auction_tol"])
        is_finished_lo = (ask_map.get(lo_bar_tk, 0.0) <= p["finished_auction_tol"])

        # ── Evaluación Compradores Atrapados (Bull side = trapped buyers) ──
        if buy_imbalances:
            pool_vol = sum(x[1] for x in buy_imbalances)
            pool_opp = sum(x[2] for x in buy_imbalances)
            pool_ratio = pool_vol / max(pool_opp, 1.0)
            min_r = min(x[0] for x in buy_imbalances)
            max_r = max(x[0] for x in buy_imbalances)
            centroid = sum(x[4] * x[1] for x in buy_imbalances) / max(pool_vol, 1.0)

            lo_tk = min_r * row_ticks
            hi_tk = (max_r + 1) * row_ticks - 1
            dwell_ms, dwell_vol, tape_speed, dwell_dens = compute_dwell_and_speed_at_extreme(
                ticks.ts_ns, ticks.price_ticks, ticks.volume, ticks.ask_ticks, ticks.bid_ticks,
                t_start_i, t_end_i, lo_tk, hi_tk, target_side=1
            )
            dwell_frac = dwell_ms / bar_dur_ms
            poc_in_wick = (poc_px >= wick_hi_floor)

            # Export continuo para análisis
            log_event(
                "TRAP_NQ",
                f"bar={b};side=trapped_buyers;vol={plain(pool_vol)};centroid={plain(centroid)};"
                f"lo_tk={lo_tk};hi_tk={hi_tk};ratio={plain(pool_ratio)};dwell_ms={plain(dwell_ms)};"
                f"tape_speed={plain(tape_speed)};dwell_frac={dwell_frac:.2f};bar_delta={plain(bar_delta)};"
                f"finished_auction={int(is_finished_hi)};poc_in_wick={int(poc_in_wick)};"
                f"rvol={plain(rvol)};regime={regime};bar_vol={plain(bar_vol)}",
                t_ns, b
            )

            # Gates para creación de zona activa
            passes_vol = pool_vol >= p["min_trap_volume"]
            passes_dwell = (not p["use_dwell_filter"]) or (dwell_ms >= p["min_dwell_ms"] and tape_speed <= p["max_tape_speed"])
            passes_dwell_frac = (not p["use_dwell_fraction"]) or (dwell_frac >= p["min_dwell_fraction"])
            passes_rvol = (not p["use_rvol_filter"]) or (rvol >= p["min_rvol"])
            passes_auction = (not p["require_finished_auction"]) or is_finished_hi
            passes_delta = (not p["require_delta_exhaustion"]) or (bar_delta <= 0.0)
            passes_poc = (not p["require_poc_in_wick"]) or poc_in_wick

            if passes_vol and passes_dwell and passes_dwell_frac and passes_rvol and passes_auction and passes_delta and passes_poc:
                buffer_pts = p["anti_overshoot_buffer_ticks"] * tick_size
                z_lo = lo_tk * tick_size - tick_size / 2.0
                z_hi = hi_tk * tick_size + tick_size / 2.0 + buffer_pts  # buffer adverse
                z = dict(
                    id=f"{b}_B", created_bar=b, is_bull=True, lo=z_lo, hi=z_hi,
                    vol=pool_vol, touches=0, created_ms=ns_to_ms(t_ns),
                    state="ACTIVE", ended_ms=None, end_reason=None,
                    rvol=rvol, dwell_ms=dwell_ms, regime=regime
                )
                active.append(z)
                all_zones.append(z)
                log_event("ZONE_CREATED", zone_desc(z), t_ns, b, zone=z)

        # ── Evaluación Vendedores Atrapados (Bear side = trapped sellers) ──
        if sell_imbalances:
            pool_vol = sum(x[1] for x in sell_imbalances)
            pool_opp = sum(x[2] for x in sell_imbalances)
            pool_ratio = pool_vol / max(pool_opp, 1.0)
            min_r = min(x[0] for x in sell_imbalances)
            max_r = max(x[0] for x in sell_imbalances)
            centroid = sum(x[4] * x[1] for x in sell_imbalances) / max(pool_vol, 1.0)

            lo_tk = min_r * row_ticks
            hi_tk = (max_r + 1) * row_ticks - 1
            dwell_ms, dwell_vol, tape_speed, dwell_dens = compute_dwell_and_speed_at_extreme(
                ticks.ts_ns, ticks.price_ticks, ticks.volume, ticks.ask_ticks, ticks.bid_ticks,
                t_start_i, t_end_i, lo_tk, hi_tk, target_side=-1
            )
            dwell_frac = dwell_ms / bar_dur_ms
            poc_in_wick = (poc_px <= wick_lo_ceil)

            # Export continuo
            log_event(
                "TRAP_NQ",
                f"bar={b};side=trapped_sellers;vol={plain(pool_vol)};centroid={plain(centroid)};"
                f"lo_tk={lo_tk};hi_tk={hi_tk};ratio={plain(pool_ratio)};dwell_ms={plain(dwell_ms)};"
                f"tape_speed={plain(tape_speed)};dwell_frac={dwell_frac:.2f};bar_delta={plain(bar_delta)};"
                f"finished_auction={int(is_finished_lo)};poc_in_wick={int(poc_in_wick)};"
                f"rvol={plain(rvol)};regime={regime};bar_vol={plain(bar_vol)}",
                t_ns, b
            )

            passes_vol = pool_vol >= p["min_trap_volume"]
            passes_dwell = (not p["use_dwell_filter"]) or (dwell_ms >= p["min_dwell_ms"] and tape_speed <= p["max_tape_speed"])
            passes_dwell_frac = (not p["use_dwell_fraction"]) or (dwell_frac >= p["min_dwell_fraction"])
            passes_rvol = (not p["use_rvol_filter"]) or (rvol >= p["min_rvol"])
            passes_auction = (not p["require_finished_auction"]) or is_finished_lo
            passes_delta = (not p["require_delta_exhaustion"]) or (bar_delta >= 0.0)
            passes_poc = (not p["require_poc_in_wick"]) or poc_in_wick

            if passes_vol and passes_dwell and passes_dwell_frac and passes_rvol and passes_auction and passes_delta and passes_poc:
                buffer_pts = p["anti_overshoot_buffer_ticks"] * tick_size
                z_lo = lo_tk * tick_size - tick_size / 2.0 - buffer_pts  # buffer adverse
                z_hi = hi_tk * tick_size + tick_size / 2.0
                z = dict(
                    id=f"{b}_S", created_bar=b, is_bull=False, lo=z_lo, hi=z_hi,
                    vol=pool_vol, touches=0, created_ms=ns_to_ms(t_ns),
                    state="ACTIVE", ended_ms=None, end_reason=None,
                    rvol=rvol, dwell_ms=dwell_ms, regime=regime
                )
                active.append(z)
                all_zones.append(z)
                log_event("ZONE_CREATED", zone_desc(z), t_ns, b, zone=z)

    # Ciclo principal por barra
    for b in range(len(bars)):
        t_ns = int(bars.end_ns[b])
        if b == 0:
            continue  # Primera barra descartada (potencial footprint parcial)

        # Actualizar ciclo de vida de zonas previas (la barra creadora nunca toca su propia zona)
        update_zones(b, t_ns)

        ask_map = footprints.ask[b]
        bid_map = footprints.bid[b]
        if not ask_map and not bid_map:
            continue

        process_bar(b, t_ns, ask_map, bid_map)

    zones_dict_list = [
        dict(
            id=z["id"], indicator=NAME, top=z["hi"], bottom=z["lo"],
            created_ms=z["created_ms"], created_bar=z["created_bar"],
            ended_ms=z["ended_ms"], state=z["state"],
            kind="trapped_buyers" if z["is_bull"] else "trapped_sellers",
            touches=z["touches"], end_reason=z["end_reason"],
            rvol=z.get("rvol", 1.0), dwell_ms=z.get("dwell_ms", 0.0),
            regime=z.get("regime", "UNKNOWN"), timeline=[]
        )
        for z in all_zones
    ]

    return dict(
        indicator=NAME,
        params=p,
        header=None,
        csv_lines=lines,
        events=rows_out,
        zones=zones_dict_list,
        params_line=meta_line(p, ticks.instrument if hasattr(ticks, "instrument") else "NQ", tick_size)
    )
