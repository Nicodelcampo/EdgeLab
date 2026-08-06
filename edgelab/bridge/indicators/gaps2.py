"""Gaps2 v2.0 — traducción 1:1 del kernel NT8 (Gaps2.cs).

Motor tick-driven sobre subserie 1-tick + expiración por barra primaria.
Orden por tick: reopen-check -> lifecycle -> detección -> PushVol.
El tick de creación nunca toca su propio gap (el baseline de volumen se
actualiza DESPUÉS de la detección: anti look-ahead). Iteración de zonas en
reversa (igual que NT8) para preservar el orden de eventos dentro de un tick.

Desviaciones declaradas (solo campos de export, nunca de decisión):
- atr_at_creation usa el ATR NT8 replicado (common.Nt8Atr); tolerancia en
  paridad vía FEATURE_DIFF.
- created_bar antes del primer cierre primario = -1 (NT8 puede reportar 0).
"""
from __future__ import annotations

import math

from ..common import Nt8Atr, fnum, fnum_or_empty, ns_to_ms, tick_and_bar_events, ts_str, tz_of

NAME = "Gaps2"

DEFAULTS = dict(
    min_gap_ticks=5, export_floor_ticks=2, reopen_pause_minutes=60,
    reopen_warmup_minutes=30, atr_period=14, vol_baseline_ticks=2000,
    min_vol_baseline_samples=500, partial_fill_pct=50.0,
    reversal_confirm_ticks=2, max_age_bars=2000, max_logged_touches=20,
)

# Espacio paramétrico declarado (F6.1). class: recompute|lifecycle|offline|
# instrument|visual|forbidden. `branches` alimenta la matriz de cobertura (F7).
PARAM_SPEC = {
    "export_floor_ticks": {"type": "int", "default": 2, "min": 1, "class": "recompute",
                           "branches": ["gap_detection"], "suggested_grid": [2, 3, 5]},
    "min_gap_ticks": {"type": "int", "default": 5, "min": 1, "class": "offline",
                      "branches": ["gap_display"], "requires_covered_by": "export_floor_ticks",
                      "suggested_grid": [3, 5, 8]},
    "reopen_pause_minutes": {"type": "float", "default": 60.0, "min": 0.0,
                             "class": "recompute", "branches": ["session_gap"]},
    "reopen_warmup_minutes": {"type": "float", "default": 30.0, "min": 0.0,
                              "class": "recompute", "branches": ["session_gap"]},
    "atr_period": {"type": "int", "default": 14, "min": 1, "class": "recompute",
                   "branches": ["atr_feature"]},
    "vol_baseline_ticks": {"type": "int", "default": 2000, "min": 1, "class": "recompute",
                           "branches": ["vol_baseline"]},
    "min_vol_baseline_samples": {"type": "int", "default": 500, "min": 0,
                                 "class": "recompute", "branches": ["vol_baseline"]},
    "partial_fill_pct": {"type": "float", "default": 50.0, "min": 0.0, "max": 100.0,
                         "class": "lifecycle", "branches": ["lifecycle_partial"]},
    "reversal_confirm_ticks": {"type": "int", "default": 2, "min": 0, "class": "lifecycle",
                               "branches": ["lifecycle_invalidation"], "suggested_grid": [0, 2, 4]},
    "max_age_bars": {"type": "int", "default": 2000, "min": 1, "class": "lifecycle",
                     "branches": ["expiration"]},
    "max_logged_touches": {"type": "int", "default": 20, "min": 0, "class": "offline",
                           "branches": ["touch_logging"]},
}

HEADER = ("event_seq,event_type,ts,unix_ms,gap_id,created_unix_ms,top,bottom,"
          "size_ticks,is_bullish,atr_at_creation,vol_at_creation,vol_baseline,"
          "vol_ratio,state,max_pen_pct,touches,bars_since,price_at_event,extra")


def params_line(p, instrument, tick_size, chart_period="?"):
    return ("# params instrument={0},tick_size={1},min_gap_ticks={2},export_floor_ticks={3},"
            "partial_fill_pct={4},reversal_confirm_ticks={5},max_age_bars={6},"
            "vol_baseline_ticks={7},min_vol_baseline_samples={8},atr_period={9},"
            "reopen_pause_min={10},reopen_warmup_min={11},max_logged_touches={12},chart_period={13}").format(
        instrument, tick_size, p["min_gap_ticks"], p["export_floor_ticks"],
        p["partial_fill_pct"], p["reversal_confirm_ticks"], p["max_age_bars"],
        p["vol_baseline_ticks"], p["min_vol_baseline_samples"], p["atr_period"],
        p["reopen_pause_minutes"], p["reopen_warmup_minutes"], p["max_logged_touches"], chart_period)


def run(ticks, bars, params=None, chart_tz="UTC"):
    p = {**DEFAULTS, **(params or {})}
    tz = tz_of(chart_tz)
    tick_size = ticks.tick_size
    atr = Nt8Atr(int(p["atr_period"]))
    rct = int(p["reversal_confirm_ticks"])

    ring_len = int(p["vol_baseline_ticks"])
    ring = [0.0] * ring_len
    head = count = 0
    vsum = 0.0

    gaps, rows, lines = [], [], []
    seq = 0
    next_id = 0
    closed_bar = -1          # CurrentBars[0]
    warmup_until = -1
    last_tick_ns = -1

    tns, pticks, vols = ticks.ts_ns, ticks.price_ticks, ticks.volume

    def log(etype, g, t_ns, price, extra=""):
        nonlocal seq
        seq += 1
        if g is not None:
            vb = g["vol_baseline"]
            ratio = g["vol_at_creation"] / vb if (not math.isnan(vb) and vb > 0) else float("nan")
            bars_since = closed_bar - g["created_bar"] if closed_bar >= 0 else -1
            zone_fields = [
                "G" + format(g["id"], "06d"), str(g["created_ms"]),
                fnum(g["top"], 6), fnum(g["bottom"], 6), str(g["size_ticks"]),
                "1" if g["is_bullish"] else "0", fnum_or_empty(g["atr_at_creation"]),
                fnum(g["vol_at_creation"], 2), fnum_or_empty(vb), fnum_or_empty(ratio),
                g["state"], fnum(g["max_pen"], 4), str(g["touches"]), str(bars_since),
            ]
        else:
            zone_fields = [""] * 14
        line = ",".join([str(seq), etype, ts_str(t_ns, tz), str(ns_to_ms(t_ns))]
                        + zone_fields + [fnum(price, 6), extra or ""])
        lines.append(line)
        # Normalizacion 2026-08-06: el censo de primeros toques exige `touch_count`
        # ENTERO y `zone_id` STRING para poder PROBAR la regla anti look-ahead de
        # EXPLORE-001. Solo se toca el dict de `events`; la linea del CSV queda
        # intacta. Verificado que no puede romper paridad: parity.py::match_zones
        # consume `zones`, no `events`, y empareja por created_ms + geometria
        # (grep -c zone_id parity.py -> 0; grep -c touch_count -> 0).
        #
        rows.append(dict(seq=seq, type=etype, ts_ns=int(t_ns), unix_ms=ns_to_ms(t_ns),
                         zone_id=("G" + format(g["id"], "06d")) if g else None,
                         price=price, extra=extra,
                         touch_count=int(g["touches"]) if g is not None else 0,
                         state=g["state"] if g else None))
        if g is not None:
            g["timeline"].append(dict(ms=ns_to_ms(t_ns), type=etype, extra=extra, state=g["state"]))

    def invalidate(g, t_ns, price, reason, extra):
        g["state"] = "INVALIDATED"
        g["archived"] = True
        g["ended_ms"] = ns_to_ms(t_ns)
        g["end_reason"] = reason
        log("ZONE_INVALIDATED", g, t_ns, price, reason if not extra else reason + ";" + extra)

    def update_zones(price, t_ns):
        for g in reversed(gaps):
            if g["archived"]:
                continue
            pen = (g["top"] - price) / g["size"] if g["is_bullish"] else (price - g["bottom"]) / g["size"]
            pen = min(1.0, max(0.0, pen))
            if pen > g["max_pen"]:
                g["max_pen"] = pen

            inside = g["bottom"] < price < g["top"]
            if inside and not g["inside_epoch"]:
                g["touches"] += 1
                g["inside_epoch"] = True
                if g["touches"] <= p["max_logged_touches"]:
                    log("ZONE_TOUCHED", g, t_ns, price, "epoch=" + str(g["touches"]))
                if g["state"] == "VIRGIN":
                    g["state"] = "TOUCHED"
            elif not inside:
                g["inside_epoch"] = False

            if g["state"] == "TOUCHED" and g["max_pen"] >= p["partial_fill_pct"] / 100.0:
                g["state"] = "PARTIAL"
                log("ZONE_PARTIAL", g, t_ns, price, "")

            if g["max_pen"] >= 1.0 and g["state"] != "FULLFILLED" and not g["archived"]:
                if rct == 0:
                    invalidate(g, t_ns, price, "full_fill", "")
                    continue
                g["state"] = "FULLFILLED"

            if g["state"] == "FULLFILLED":
                inverse = (price <= g["bottom"] - rct * tick_size) if g["is_bullish"] \
                    else (price >= g["top"] + rct * tick_size)
                back = (price >= g["top"]) if g["is_bullish"] else (price <= g["bottom"])
                if inverse:
                    invalidate(g, t_ns, price, "inverse", "")
                elif back:
                    invalidate(g, t_ns, price, "full_fill", "")

    def create_gap(prev, cur, vol, t_ns, gap_ticks):
        nonlocal next_id
        next_id += 1
        top, bottom = max(prev, cur), min(prev, cur)
        atr_val = float("nan")
        if closed_bar >= p["atr_period"] + 1:
            atr_val = atr.values[closed_bar - 1]   # _atr[1]
        g = dict(id=next_id, created_ms=ns_to_ms(t_ns), created_bar=closed_bar,
                 top=top, bottom=bottom, size=top - bottom, is_bullish=cur > prev,
                 size_ticks=gap_ticks, atr_at_creation=atr_val, vol_at_creation=vol,
                 vol_baseline=(vsum / count if count >= p["min_vol_baseline_samples"] else float("nan")),
                 state="VIRGIN", max_pen=0.0, touches=0, inside_epoch=False,
                 archived=False, display=gap_ticks >= p["min_gap_ticks"],
                 ended_ms=None, end_reason=None, timeline=[])
        gaps.append(g)
        log("ZONE_CREATED", g, t_ns, cur, "")

    for kind, idx in tick_and_bar_events(tns, bars.end_ns):
        if kind == "bar":
            b = idx
            prev_close = float(bars.close_t[b - 1]) * tick_size if b > 0 else None
            atr.on_bar(float(bars.high_t[b]) * tick_size, float(bars.low_t[b]) * tick_size, prev_close)
            closed_bar = b
            if closed_bar < 1:
                continue
            t_bar, px = int(bars.end_ns[b]), float(bars.close_t[b]) * tick_size
            for g in reversed(gaps):
                if g["archived"] or closed_bar - g["created_bar"] <= p["max_age_bars"]:
                    continue
                if g["state"] == "FULLFILLED":
                    invalidate(g, t_bar, px, "full_fill", "resolved_by_expiry")
                else:
                    g["state"] = "EXPIRED"
                    g["archived"] = True
                    g["ended_ms"] = ns_to_ms(t_bar)
                    g["end_reason"] = "expired"
                    log("ZONE_EXPIRED", g, t_bar, px, "")
            continue

        i = idx
        if i < 1:                       # CurrentBars[1] < 1: necesita tick previo
            continue
        price = float(pticks[i]) * tick_size
        prev = float(pticks[i - 1]) * tick_size
        vol = float(vols[i])
        t_ns = int(tns[i])

        skip_detection = False
        if last_tick_ns >= 0:
            pause_min = (t_ns - last_tick_ns) / 60e9
            if pause_min >= p["reopen_pause_minutes"]:
                warmup_until = t_ns + int(p["reopen_warmup_minutes"] * 60e9)
                jump = abs(price - prev)
                log("SESSION_GAP_SKIPPED", None, t_ns, price,
                    "pause_min={0}".format(fnum(pause_min, 1)) + ";jump_pts=" + fnum(jump, 4))
        if t_ns < warmup_until:
            skip_detection = True
        last_tick_ns = t_ns

        update_zones(price, t_ns)

        if not skip_detection:
            gap_ticks = int(round(abs(price - prev) / tick_size))
            if gap_ticks >= p["export_floor_ticks"]:
                create_gap(prev, price, vol, t_ns, gap_ticks)

        # PushVol DESPUÉS de la detección: el tick actual nunca entra a su baseline
        if count < ring_len:
            ring[head] = vol; vsum += vol; count += 1
        else:
            vsum += vol - ring[head]; ring[head] = vol
        head = (head + 1) % ring_len

    # Snapshot al cierre (State.Terminated -> SESSION_END por zona viva)
    if len(bars) > 0:
        t_end, px_end = int(bars.end_ns[-1]), float(bars.close_t[-1]) * tick_size
        for g in gaps:
            if not g["archived"]:
                log("SESSION_END", g, t_end, px_end, "snapshot")

    zones = [dict(id="G" + format(g["id"], "06d"), indicator=NAME,
                  top=g["top"], bottom=g["bottom"], created_ms=g["created_ms"],
                  ended_ms=g["ended_ms"], state=g["state"],
                  kind=("bull_gap" if g["is_bullish"] else "bear_gap"),
                  display=g["display"], size_ticks=g["size_ticks"],
                  touches=g["touches"], max_pen_pct=g["max_pen"],
                  end_reason=g["end_reason"], timeline=g["timeline"])
             for g in gaps]

    return dict(indicator=NAME, params=p, header=HEADER, csv_lines=lines,
                events=rows, zones=zones,
                params_line=params_line(p, ticks.instrument, tick_size))
