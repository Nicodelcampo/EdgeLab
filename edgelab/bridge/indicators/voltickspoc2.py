"""VolTicksPOC2 v2.0 — traducción 1:1 del kernel NT8 (VolTicksPOC2.cs).

Por cierre de barra primaria: footprint (reconstruido de ticks, idéntico a la
subserie 1-tick de NT8) -> mismatch check -> ciclo de vida -> ratio vs
baseline (excluye la barra actual) -> detección por percentil empírico sin
interpolación -> POC (empate: tick más bajo) -> OBS/ZONE_CREATED. Las
ventanas se actualizan DESPUÉS de la comparación.

Fidelidad 1:1 verificada contra VolTicksPOC2.cs (AMejorasIndicadoresVectorbt/):
- POC: el .cs usa desempate explícito `kv.Value > pocVol || (kv.Value==pocVol
  && kv.Key < pocTick)`; acá se itera `sorted(fp.keys())` con `>` estricto ->
  el tick más bajo entre los de máximo volumen gana (mismo resultado).
- baseline = media de Volume[1..AvgPeriod] EXCLUYENDO la barra actual; sin
  baseline completo -> sin detección.
- threshold = QuantileNoInterp(ratios, det_cut) sobre los últimos
  RatioWindowBars ratios; detección por percentil empírico count(<=)/n.

Desviación declarada (solo numérica, nunca de decisión):
- El .cs mantiene `baselineSum` incremental (`baselineSum/AvgPeriod`); acá se
  recomputa `sum(baseline_win)/len` cada barra. Cuando la ventana está llena
  len==AvgPeriod, así que es la misma media salvo orden de suma en punto
  flotante (diferencia despreciable; si aflora, FEATURE_DIFF en ratio).
"""
from __future__ import annotations

from collections import deque

from ..common import empirical_pct, gnum, ns_to_ms, plain, quantile_exact, ts_str, tz_of

NAME = "VolTicksPOC2"

DEFAULTS = dict(
    avg_period=200, ratio_window_bars=2000, detection_percentile=99.5,
    min_ratio_samples=500, export_floor_percentile=95.0, price_mark_ticks=1,
    invalidation_mode="CloseThrough", max_age_bars=2000, max_touches=0,
)

# Espacio paramétrico declarado (F6.1).
PARAM_SPEC = {
    "avg_period": {"type": "int", "default": 200, "min": 1, "class": "recompute",
                   "branches": ["baseline_window"]},
    "ratio_window_bars": {"type": "int", "default": 2000, "min": 1, "class": "recompute",
                          "branches": ["ratio_window"]},
    "min_ratio_samples": {"type": "int", "default": 500, "min": 1, "class": "recompute",
                          "branches": ["ratio_window"]},
    "export_floor_percentile": {"type": "float", "default": 95.0, "min": 0.0, "max": 100.0,
                                "class": "recompute", "branches": ["export_floor"]},
    "detection_percentile": {"type": "float", "default": 99.5, "min": 0.0, "max": 100.0,
                             "class": "offline", "branches": ["detection_cut"],
                             "requires_covered_by": "export_floor_percentile",
                             "suggested_grid": [99.0, 99.5, 99.75, 99.9]},
    "price_mark_ticks": {"type": "int", "default": 1, "min": 1, "class": "offline",
                         "branches": ["geometry"]},
    "invalidation_mode": {"type": "str", "default": "CloseThrough",
                          "choices": ["CloseThrough", "FirstTouch"], "class": "lifecycle",
                          "branches": ["lifecycle_invalidation"]},
    "max_age_bars": {"type": "int", "default": 2000, "min": 1, "class": "lifecycle",
                     "branches": ["expiration"]},
    "max_touches": {"type": "int", "default": 0, "min": 0, "class": "lifecycle",
                    "branches": ["lifecycle_max_touches"]},
}

HEADER = ("event_seq,event_type,bar_index,bar_close_time,poc_tick,ratio,"
          "baseline,bar_volume,tick_volume,poc_volume,poc_share,threshold,"
          "window_count,zone_id,touch_count,reason")


def meta_line(p, instrument, tick_size):
    return ("# meta,indicator=VolTicksPOC2,version=2.0,instrument={0},tick_size={1},"
            "avg_period={2},ratio_window={3},percentile={4},min_samples={5},"
            "export_floor={6},poc_tiebreak=lowest_tick,footprint=reconstructed_1tick_subseries").format(
        instrument, tick_size, p["avg_period"], p["ratio_window_bars"],
        p["detection_percentile"], p["min_ratio_samples"], p["export_floor_percentile"])


def run(ticks, bars, footprints, params=None, chart_tz="UTC"):
    p = {**DEFAULTS, **(params or {})}
    tz = tz_of(chart_tz)
    tick_size = ticks.tick_size
    det_cut = p["detection_percentile"] / 100.0

    # `ratio_win` es una ventana RODANTE acotada a `ratio_window_bars`: su
    # longitud nunca supera ese tope. Si `min_ratio_samples` es mayor, el gate de
    # detección (`len(ratio_win) >= min_ratio_samples`) NO PUEDE abrir nunca y el
    # kernel devuelve cero zonas — sin error, sin aviso, para siempre.
    #
    # Se detecta y se grita en vez de resolverlo en silencio: ni clamp ni
    # fallback. Un config imposible tiene que ser visible, no producir un
    # "no hay señales" indistinguible de un resultado real. (Incidente 2026-07-26:
    # un chart con ratio_window_bars=200 y min_ratio_samples=500 no marcaba nada
    # y no había forma de saber por qué.)
    if int(p["min_ratio_samples"]) > int(p["ratio_window_bars"]):
        raise ValueError(
            "config imposible: min_ratio_samples=%d > ratio_window_bars=%d. "
            "La ventana de ratios esta acotada a %d, asi que el gate de deteccion "
            "nunca abre y el kernel produciria CERO zonas en silencio. "
            "Subir ratio_window_bars a >= %d, o bajar min_ratio_samples a <= %d."
            % (int(p["min_ratio_samples"]), int(p["ratio_window_bars"]),
               int(p["ratio_window_bars"]), int(p["min_ratio_samples"]),
               int(p["ratio_window_bars"])))

    # Warmup: hasta `avg_period + min_ratio_samples` barras el gate de detección
    # NO puede abrir. Si la ventana no llega ni a eso, el resultado es CERO zonas
    # garantizado — y un cero por falta de datos es indistinguible de un cero por
    # ausencia de señal. Se declara en el resultado en vez de dejarlo implícito.
    warmup_bars = int(p["avg_period"]) + int(p["min_ratio_samples"])
    datos_insuficientes = len(bars) < warmup_bars

    rows, lines, all_zones, active = [], [], [], []
    seq = 0
    zone_seq = 0
    baseline_win = deque(maxlen=int(p["avg_period"]))
    ratio_win = deque(maxlen=int(p["ratio_window_bars"]))

    def emit(etype, bar, t_ns, poc_tick, ratio, baseline, bar_vol, tick_vol,
             poc_vol, poc_share, threshold, window_count, zone_id, touch_count, reason):
        nonlocal seq
        seq += 1
        lines.append(",".join([
            str(seq), etype, str(bar), ts_str(t_ns, tz, "%Y-%m-%dT%H:%M:%S"),
            str(poc_tick), gnum(ratio, 6), gnum(baseline, 4), plain(bar_vol),
            plain(tick_vol), plain(poc_vol), gnum(poc_share, 6), gnum(threshold, 6),
            str(window_count), str(zone_id), str(touch_count), reason or ""]))
        rows.append(dict(seq=seq, type=etype, bar_index=bar, ts_ns=int(t_ns),
                         unix_ms=ns_to_ms(t_ns), poc_tick=poc_tick, zone_id=zone_id,
                         touch_count=touch_count, reason=reason))

    def lifecycle(b, t_ns):
        hi = float(bars.high_t[b]) * tick_size
        lo = float(bars.low_t[b]) * tick_size
        close = float(bars.close_t[b]) * tick_size
        for z in list(reversed(active)):
            if z["created_bar"] >= b:      # la barra creadora no interactúa
                continue
            touched = hi >= z["lower"] and lo <= z["upper"]
            if touched:
                z["touches"] += 1
                emit("ZONE_TOUCHED", b, t_ns, z["poc_tick"], 0, 0, 0, 0, 0, 0, 0, 0,
                     z["id"], z["touches"], "")
            reason = None
            if p["invalidation_mode"] == "FirstTouch" and touched:
                reason = "first_touch"
            elif p["invalidation_mode"] == "CloseThrough":
                s = 1 if close > z["upper"] else (-1 if close < z["lower"] else 0)
                if s != 0:
                    if z["ref_side"] == 0:
                        z["ref_side"] = s
                    elif s == -z["ref_side"]:
                        reason = "close_through"
            if reason is None and p["max_touches"] > 0 and z["touches"] >= p["max_touches"]:
                reason = "max_touches"
            if reason is not None:
                emit("ZONE_INVALIDATED", b, t_ns, z["poc_tick"], 0, 0, 0, 0, 0, 0, 0, 0,
                     z["id"], z["touches"], reason)
                z["ended_ms"] = ns_to_ms(t_ns)
                z["state"] = "INVALIDATED"
                z["end_reason"] = reason
                active.remove(z)
            elif b - z["created_bar"] >= p["max_age_bars"]:
                emit("ZONE_EXPIRED", b, t_ns, z["poc_tick"], 0, 0, 0, 0, 0, 0, 0, 0,
                     z["id"], z["touches"], "max_age")
                z["ended_ms"] = ns_to_ms(t_ns)
                z["state"] = "EXPIRED"
                z["end_reason"] = "max_age"
                active.remove(z)

    for b in range(len(bars)):
        t_ns = int(bars.end_ns[b])
        fp = footprints.total[b]
        bar_vol = float(bars.volume[b])
        fp_vol = float(sum(fp.values()))

        if b > 0 and fp and abs(fp_vol - bar_vol) > 0.5:
            emit("FOOTPRINT_MISMATCH", b, t_ns, 0, 0, 0, bar_vol, fp_vol, 0, 0, 0,
                 len(ratio_win), 0, 0, "fp_vs_bar_volume")

        lifecycle(b, t_ns)

        ratio = None
        baseline = 0.0
        if len(baseline_win) >= int(p["avg_period"]):
            baseline = sum(baseline_win) / len(baseline_win)
            if baseline > 0:
                ratio = bar_vol / baseline

        if ratio is not None and len(ratio_win) >= int(p["min_ratio_samples"]):
            srt = sorted(ratio_win)
            threshold = quantile_exact(srt, det_cut)
            pct = empirical_pct(srt, ratio)
            if not fp:
                emit("ERROR", b, t_ns, 0, ratio, baseline, bar_vol, 0, 0, 0,
                     threshold, len(ratio_win), 0, 0, "empty_footprint")
            else:
                poc_tick, poc_vol = 0, -1.0
                for tk in sorted(fp.keys()):        # empate -> tick más bajo
                    if fp[tk] > poc_vol:
                        poc_tick, poc_vol = tk, fp[tk]
                poc_share = poc_vol / fp_vol if fp_vol > 0 else 0.0
                if pct * 100.0 >= p["export_floor_percentile"]:
                    emit("OBS", b, t_ns, poc_tick, ratio, baseline, bar_vol, fp_vol,
                         poc_vol, poc_share, threshold, len(ratio_win), 0, 0, "")
                if pct >= det_cut:
                    zone_seq += 1
                    poc_price = poc_tick * tick_size
                    half = max(1, int(p["price_mark_ticks"])) * tick_size / 2.0
                    close = float(bars.close_t[b]) * tick_size
                    lower, upper = poc_price - half, poc_price + half
                    ref = 1 if close > upper else (-1 if close < lower else 0)
                    z = dict(id=zone_seq, poc_tick=poc_tick, lower=lower, upper=upper,
                             created_bar=b, created_ms=ns_to_ms(t_ns), ref_side=ref,
                             touches=0, pct=pct, state="ACTIVE", ended_ms=None,
                             end_reason=None)
                    active.append(z)
                    all_zones.append(z)
                    emit("ZONE_CREATED", b, t_ns, poc_tick, ratio, baseline, bar_vol,
                         fp_vol, poc_vol, poc_share, threshold, len(ratio_win),
                         zone_seq, 0, "")

        # Ventanas: DESPUÉS de la comparación
        if ratio is not None:
            ratio_win.append(ratio)
        baseline_win.append(bar_vol)

    zones = [dict(id=str(z["id"]), indicator=NAME, top=z["upper"], bottom=z["lower"],
                  created_ms=z["created_ms"], ended_ms=z["ended_ms"], state=z["state"],
                  kind="poc_anomaly", touches=z["touches"], end_reason=z["end_reason"],
                  timeline=[]) for z in all_zones]

    return dict(indicator=NAME, params=p, header=HEADER, csv_lines=lines,
                events=rows, zones=zones,
                params_line=meta_line(p, ticks.instrument, tick_size),
                # Diagnóstico explícito: un consumidor que vea `zones == []` puede
                # distinguir "no hubo señal" de "no hubo datos para buscarla".
                warmup_bars=warmup_bars, n_bars=len(bars),
                datos_insuficientes=datos_insuficientes)
