"""BigTrap2 v2.0 — traduccion 1:1 del kernel NT8 (BigTrap2.cs).

Por cierre de barra primaria: barra 0 descartada (footprint potencialmente
parcial) -> FOOTPRINT_MISMATCH -> UpdateZones (lifecycle ANTES de crear:
la barra creadora nunca toca su propia zona) -> ProcessBar (filas ancladas
a la grilla absoluta con FloorDiv, POC empate fila mas baja, imbalance
Diagonal/SameLevel con piso max(opuesto,1), filtro de mecha opcional) ->
EmitSide (export continuo TRAP desde MinExportVolume; zona on-chart solo
desde MinTrapVolume). Log en formato pipe: seq|iso|type|payload, seq desde 0.

Fidelidad 1:1 verificada contra BigTrap.txt (AMejorasIndicadoresVectorbt/):
- FloorDiv: el .cs hace floor division real (`if((a%b!=0)&&((a<0)!=(b<0)))q--`);
  acá common.floor_div == Python `a//b` (floor para negativos). Idéntico.
- POC: `total > pocVol` con filas ascendentes -> empate a la fila más baja.
  El POC es SOLO visual en el .cs (ShowPOC); no entra al export analítico, por
  eso el kernel computa pocVol pero no exporta pocRow (contrato: lo visual nunca
  es analítico).
- Imbalance Diagonal: buy = ask[r]/max(bid[r-1],1); sell = bid[r]/max(ask[r+1],1).
- iso "o" de C# (DateTime Kind=Unspecified) = 7 decimales sin offset (100 ns).
- seq post-incremento desde 0; barra 0 descartada (footprint parcial).

Identidad multi-barra: cada resolución (time:1, tick:5, tick:25, …) es una
configuración distinta. El bar_key entra al param_set_id (viewer_export) y es
columna del zone store, así que las zonas de tick:5 y tick:25 no colisionan
aunque compartan zone_id `{bar}_{B|S}` (el índice de barra reinicia por config).
"""
from __future__ import annotations

from datetime import datetime, timezone as _tz

from ..common import floor_div, ns_to_ms, plain, tz_of

NAME = "BigTrap2"

DEFAULTS = dict(
    ticks_per_row=1, imbalance_mode="Diagonal", trap_volume_source="AggressiveSide",
    imbalance_ratio=3.0, use_wick_filter=True, wick_zone_pct=30.0,
    min_delta_filter=0.0, min_trap_volume=30.0, min_export_volume=1.0,
    invalidation_mode="CloseThrough", max_age_bars=2000, max_touches=0,
)

# Espacio paramétrico declarado (F6.1). Los params de renderer analítico del .cs
# (TopPercentFilter/AutoScale/OutlierPercentile) son FORBIDDEN: look-ahead que
# no existe en el kernel; la CLI los rechaza si alguien intenta barrerlos.
PARAM_SPEC = {
    "ticks_per_row": {"type": "int", "default": 1, "min": 1, "class": "recompute",
                      "branches": ["row_anchor"], "suggested_grid": [1, 2, 4]},
    "imbalance_mode": {"type": "str", "default": "Diagonal",
                       "choices": ["Diagonal", "SameLevel"], "class": "recompute",
                       "branches": ["imbalance_detection"]},
    "trap_volume_source": {"type": "str", "default": "AggressiveSide",
                           "choices": ["AggressiveSide", "TotalLevel"], "class": "recompute",
                           "branches": ["trap_volume"]},
    "imbalance_ratio": {"type": "float", "default": 3.0, "min": 1.0, "class": "recompute",
                        "branches": ["imbalance_detection"], "suggested_grid": [1.5, 2.0, 3.0, 4.0]},
    "use_wick_filter": {"type": "bool", "default": True, "class": "recompute",
                        "branches": ["wick_filter"]},
    "wick_zone_pct": {"type": "float", "default": 30.0, "min": 0.0, "max": 100.0,
                      "class": "recompute", "branches": ["wick_filter"]},
    "min_delta_filter": {"type": "float", "default": 0.0, "min": 0.0, "class": "recompute",
                         "branches": ["delta_filter"]},
    "min_export_volume": {"type": "float", "default": 1.0, "min": 0.0, "class": "recompute",
                          "branches": ["export_floor"]},
    "min_trap_volume": {"type": "float", "default": 30.0, "min": 0.0, "class": "offline",
                        "branches": ["trap_selection"], "requires_covered_by": "min_export_volume",
                        "suggested_grid": [20.0, 30.0, 50.0]},
    "invalidation_mode": {"type": "str", "default": "CloseThrough",
                          "choices": ["CloseThrough", "FirstTouch"], "class": "lifecycle",
                          "branches": ["lifecycle_invalidation"]},
    "max_age_bars": {"type": "int", "default": 2000, "min": 1, "class": "lifecycle",
                     "branches": ["expiration"]},
    "max_touches": {"type": "int", "default": 0, "min": 0, "class": "lifecycle",
                    "branches": ["lifecycle_max_touches"]},
    # Renderer analítico / look-ahead: PROHIBIDOS en cualquier grilla.
    "TopPercentFilter": {"class": "forbidden", "optimizable": False,
                         "reason": "renderer selecciona por percentil sobre historia acumulada (look-ahead)"},
    "AutoScale": {"class": "forbidden", "optimizable": False,
                  "reason": "escalado visual dependiente de la historia cargada"},
    "OutlierPercentile": {"class": "forbidden", "optimizable": False,
                          "reason": "corte visual retroactivo sobre todas las detecciones"},
}


def meta_line(p, instrument, tick_size):
    return ("# meta indicator=BigTrap2,version=2.0,footprint=reconstructed_1tick_subseries,"
            "classifier=bidask_then_tickrule,row_anchor=absolute_grid,"
            "ratio_floor=max(opposite,1),poc_tiebreak=lowest_row,"
            "imbalance_mode={0},trap_volume={1},ticks_per_row={2},imbalance_ratio={3},"
            "wick_filter={4},wick_zone_pct={5},min_delta={6},invalidation={7},"
            "max_age_bars={8},max_touches={9},tick_size={10},instrument={11}").format(
        p["imbalance_mode"], p["trap_volume_source"], p["ticks_per_row"],
        p["imbalance_ratio"], p["use_wick_filter"], p["wick_zone_pct"],
        p["min_delta_filter"], p["invalidation_mode"], p["max_age_bars"],
        p["max_touches"], tick_size, instrument)


def _iso_o(ns, tz):
    """Formato C# \"o\" para DateTime sin offset: yyyy-MM-ddTHH:mm:ss.fffffff."""
    d = datetime.fromtimestamp(ns / 1e9, tz=_tz.utc).astimezone(tz)
    frac = int(ns % 1_000_000_000) // 100
    return d.strftime("%Y-%m-%dT%H:%M:%S") + ".%07d" % frac


def run(ticks, bars, footprints, params=None, chart_tz="UTC"):
    p = {**DEFAULTS, **(params or {})}
    tz = tz_of(chart_tz)
    tick_size = ticks.tick_size

    rows_out, lines, active, all_zones = [], [], [], []
    seq = 0  # post-incremento: el primer evento lleva seq=0

    def log_event(etype, payload, t_ns, bar, zone=None, touches=0, reason=""):
        nonlocal seq
        lines.append("{0}|{1}|{2}|{3}".format(seq, _iso_o(t_ns, tz), etype, payload))
        rows_out.append(dict(seq=seq, type=etype, ts_ns=int(t_ns), unix_ms=ns_to_ms(t_ns),
                             bar_index=bar, zone_id=None if zone is None else zone["id"],
                             touch_count=touches, reason=reason))
        seq += 1

    def zone_desc(z):
        return "zone_id={0}_{1};created_bar={0};side={2};lo={3};hi={4};vol={5}".format(
            z["created_bar"], "B" if z["is_bull"] else "S",
            "trapped_buyers" if z["is_bull"] else "trapped_sellers",
            plain(z["lo"]), plain(z["hi"]), plain(z["vol"]))

    def update_zones(b, t_ns):
        if not active:
            return
        hi = float(bars.high_t[b]) * tick_size
        lo = float(bars.low_t[b]) * tick_size
        close = float(bars.close_t[b]) * tick_size
        for z in list(active):
            if p["max_age_bars"] > 0 and b - z["created_bar"] > p["max_age_bars"]:
                log_event("ZONE_EXPIRED", zone_desc(z) + ";bar=" + str(b), t_ns, b,
                          zone=z, touches=z["touches"], reason="max_age")
                z.update(state="EXPIRED", ended_ms=ns_to_ms(t_ns), end_reason="max_age")
                active.remove(z)
                continue
            touched = hi >= z["lo"] and lo <= z["hi"]
            if touched:
                z["touches"] += 1
                log_event("ZONE_TOUCHED",
                          zone_desc(z) + ";bar={0};touches={1}".format(b, z["touches"]),
                          t_ns, b, zone=z, touches=z["touches"])
            adverse_close = close > z["hi"] if z["is_bull"] else close < z["lo"]
            reason = None
            if p["invalidation_mode"] == "FirstTouch" and touched:
                reason = "first_touch"
            elif p["invalidation_mode"] == "CloseThrough" and adverse_close:
                reason = "close_through" if touched else "close_through_gap"
            if reason is None and p["max_touches"] > 0 and z["touches"] >= p["max_touches"]:
                reason = "max_touches"
            if reason is not None:
                log_event("ZONE_INVALIDATED",
                          zone_desc(z) + ";reason={0};bar={1}".format(reason, b),
                          t_ns, b, zone=z, touches=z["touches"], reason=reason)
                z.update(state="INVALIDATED", ended_ms=ns_to_ms(t_ns), end_reason=reason)
                active.remove(z)

    def emit_side(is_bull, vol, w_sum, lo_row, hi_row, n_rows, max_ratio,
                  fp_vol, n_quote, n_rule, row_ticks, b, t_ns):
        if n_rows == 0 or vol <= 0 or vol < p["min_export_volume"]:
            return
        centroid = w_sum / vol
        lo_tick = lo_row * row_ticks
        hi_tick = (hi_row + 1) * row_ticks - 1
        zone_lo = lo_tick * tick_size - tick_size / 2.0
        zone_hi = hi_tick * tick_size + tick_size / 2.0
        close = float(bars.close_t[b]) * tick_size
        bar_vol = float(bars.volume[b])
        # Export continuo: los umbrales de seleccion se barren offline en vectorbt.
        log_event("TRAP",
                  "bar={0};side={1};vol={2};centroid={3};zone_lo={4};zone_hi={5};"
                  "n_rows={6};max_ratio={7};close={8};bar_vol={9};fp_vol={10};"
                  "n_quote={11};n_rule={12}".format(
                      b, "trapped_buyers" if is_bull else "trapped_sellers",
                      plain(vol), plain(centroid), plain(zone_lo), plain(zone_hi),
                      n_rows, plain(max_ratio), plain(close), plain(bar_vol),
                      plain(fp_vol), n_quote, n_rule), t_ns, b)
        if vol < p["min_trap_volume"]:
            return
        z = dict(id="{0}_{1}".format(b, "B" if is_bull else "S"), created_bar=b,
                 is_bull=is_bull, lo=zone_lo, hi=zone_hi, vol=vol, touches=0,
                 created_ms=ns_to_ms(t_ns), state="ACTIVE", ended_ms=None,
                 end_reason=None)
        active.append(z)
        all_zones.append(z)
        log_event("ZONE_CREATED", zone_desc(z), t_ns, b, zone=z)

    def process_bar(ask_map, bid_map, fp_vol, n_quote, n_rule, b, t_ns):
        row_ticks = max(1, int(p["ticks_per_row"]))
        row_ask, row_bid = {}, {}
        for tk, v in ask_map.items():
            r = floor_div(tk, row_ticks)
            row_ask[r] = row_ask.get(r, 0.0) + v
        for tk, v in bid_map.items():
            r = floor_div(tk, row_ticks)
            row_bid[r] = row_bid.get(r, 0.0) + v
        row_keys = sorted(set(row_ask) | set(row_bid))
        if not row_keys:
            return
        close = float(bars.close_t[b]) * tick_size
        lo = float(bars.low_t[b]) * tick_size
        hi = float(bars.high_t[b]) * tick_size
        rng = hi - lo
        wick_hi_floor = hi - rng * (p["wick_zone_pct"] / 100.0)
        wick_lo_ceil = lo + rng * (p["wick_zone_pct"] / 100.0)

        poc_vol = -1.0  # POC: en empate gana la fila mas baja (asc + estrictamente mayor)
        buy = dict(vol=0.0, wsum=0.0, mx=0.0, lo=None, hi=None, n=0)
        sell = dict(vol=0.0, wsum=0.0, mx=0.0, lo=None, hi=None, n=0)

        for r in row_keys:
            a = row_ask.get(r, 0.0)
            bv = row_bid.get(r, 0.0)
            total = a + bv
            if total > poc_vol:
                poc_vol = total
            if abs(a - bv) < p["min_delta_filter"]:
                continue
            if p["imbalance_mode"] == "Diagonal":
                buy_ratio = a / max(row_bid.get(r - 1, 0.0), 1.0)
                sell_ratio = bv / max(row_ask.get(r + 1, 0.0), 1.0)
            else:
                buy_ratio = a / max(bv, 1.0)
                sell_ratio = bv / max(a, 1.0)
            row_price = (r * row_ticks + (row_ticks - 1) / 2.0) * tick_size
            contrib_buy = a if p["trap_volume_source"] == "AggressiveSide" else total
            contrib_sell = bv if p["trap_volume_source"] == "AggressiveSide" else total
            # Trapped buyers: agresion compradora que quedo por ENCIMA del close.
            if (a >= 1 and buy_ratio >= p["imbalance_ratio"] and row_price > close
                    and (not p["use_wick_filter"] or (rng > 0 and row_price >= wick_hi_floor))):
                buy["vol"] += contrib_buy
                buy["wsum"] += row_price * contrib_buy
                buy["n"] += 1
                buy["lo"] = r if buy["lo"] is None else min(buy["lo"], r)
                buy["hi"] = r if buy["hi"] is None else max(buy["hi"], r)
                buy["mx"] = max(buy["mx"], buy_ratio)
            # Trapped sellers: agresion vendedora que quedo por DEBAJO del close.
            if (bv >= 1 and sell_ratio >= p["imbalance_ratio"] and row_price < close
                    and (not p["use_wick_filter"] or (rng > 0 and row_price <= wick_lo_ceil))):
                sell["vol"] += contrib_sell
                sell["wsum"] += row_price * contrib_sell
                sell["n"] += 1
                sell["lo"] = r if sell["lo"] is None else min(sell["lo"], r)
                sell["hi"] = r if sell["hi"] is None else max(sell["hi"], r)
                sell["mx"] = max(sell["mx"], sell_ratio)

        emit_side(True, buy["vol"], buy["wsum"], buy["lo"] or 0, buy["hi"] or 0,
                  buy["n"], buy["mx"], fp_vol, n_quote, n_rule, row_ticks, b, t_ns)
        emit_side(False, sell["vol"], sell["wsum"], sell["lo"] or 0, sell["hi"] or 0,
                  sell["n"], sell["mx"], fp_vol, n_quote, n_rule, row_ticks, b, t_ns)

    for b in range(len(bars)):
        t_ns = int(bars.end_ns[b])
        ask_map = footprints.ask[b]
        bid_map = footprints.bid[b]
        n_quote = int(footprints.n_quote[b])
        n_rule = int(footprints.n_rule[b])
        if b == 0:
            continue  # primera barra primaria: footprint potencialmente parcial
        fp_vol = float(sum(ask_map.values()) + sum(bid_map.values()))
        bar_vol = float(bars.volume[b])
        if abs(fp_vol - bar_vol) > 0.5:
            log_event("FOOTPRINT_MISMATCH",
                      "bar={0};fp_vol={1};bar_vol={2};n_quote={3};n_rule={4}".format(
                          b, plain(fp_vol), plain(bar_vol), n_quote, n_rule), t_ns, b)
        # Lifecycle primero: la barra creadora nunca toca su propia zona.
        update_zones(b, t_ns)
        if not ask_map and not bid_map:
            continue
        process_bar(ask_map, bid_map, fp_vol, n_quote, n_rule, b, t_ns)

    zones = [dict(id=z["id"], indicator=NAME, top=z["hi"], bottom=z["lo"],
                  created_ms=z["created_ms"], ended_ms=z["ended_ms"], state=z["state"],
                  kind="trapped_buyers" if z["is_bull"] else "trapped_sellers",
                  touches=z["touches"], end_reason=z["end_reason"], timeline=[])
             for z in all_zones]

    return dict(indicator=NAME, params=p, header=None, csv_lines=lines,
                events=rows_out, zones=zones,
                params_line=meta_line(p, ticks.instrument, tick_size))
