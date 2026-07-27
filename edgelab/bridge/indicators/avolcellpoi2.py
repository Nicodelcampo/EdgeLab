"""aVolCellPOI2 v2.0 — traduccion 1:1 del kernel NT8 (aVolCellPOI2.cs).

Perfil historico por bucket temporal (SessionRelative o WallClock) congelado
por sesion (el perfil solo cambia en el roll de sesion). Deteccion por
cuantil ponderado sin interpolacion o robust-z log1p/MAD. La sesion actual
nunca entra al perfil contra el que se compara (anti look-ahead). El roll
replica RollSessionIntoHistory: el primer roll observado descarta pending.

Footprint reconstruido desde la subserie de 1 tick con bid/ask (guia SS11/SS13),
IDÉNTICO en ambos lados: el .cs de NT8 (aVolCellPOI2.cs) fue reescrito para usar
el mismo motor de reconstrucción por subserie 1-tick (no barras Volumetric
nativas de OrderFlow) — un solo motor de cálculo, sin dependencia de OrderFlow+,
y sin el dual-path que la guia §13 prohíbe. Así la paridad de celdas (P1B) es
exacta por construcción, no una equivalencia a validar.

Fidelidad 1:1 verificada contra avolcellpoi.txt (AMejorasIndicadoresVectorbt/):
- firstRollDone descarta la primera sesión observada (potencialmente parcial);
  roll en IsFirstBarOfSession (acá: b==0 o cambio de session_key).
- la sesión actual se acumula a `pending` DESPUÉS de comparar, y solo entra al
  historial en el roll siguiente -> el perfil nunca se contamina con la sesión
  en curso (anti look-ahead). La barra creadora tampoco toca su propia zona.
- EqualSessionWeight: cada sesión pesa 1 en total (w = 1/len(sesión)).
- RobustLogZ: y = ln(1+v); z = (y - mediana_pond) / (1.4826 * MAD_pond);
  si MAD == 0 -> z = 999 si y > mediana, si no 0. Cuantil ponderado sin interp.
- bucket anclado en (cierre - 1 s); SessionRelative = minutos desde el inicio
  real de sesión / TimeBucketMinutes.
- guards: sin >= MinSessions sesiones ni >= MinCellSamples celdas, cache = None
  y NO se detecta nada (jamás fallback silencioso con historia pobre).

Requisito de paridad real (docs/nt8_indicator_parity_contract.md §5): con
min_sessions=15 y lookback_sessions=20, el oráculo NT8 necesita SEMANAS de
historia cargada antes de que se creen zonas. Sobre muestras cortas el kernel
correctamente produce 0 zonas (historia insuficiente), no detecciones falsas.
"""
from __future__ import annotations

import math
from collections import deque

from .. import sessions
from ..common import gnum, ns_to_ms, plain, ts_str, tz_of

NAME = "aVolCellPOI2"

# --- v2.1 (2026-07-26): recalibracion de defaults, autorizada por Nico ---------
#
# Los defaults de v2.0 eran INTERNAMENTE INCOHERENTES, con independencia de que
# dibujaran poco. Para un cuantil empirico de nivel p sobre n muestras quedan
# n*(1-p) observaciones por encima del umbral. Con p=99.5 y min_cell_samples=500
# eso da **2,5**: el umbral lo definia practicamente un solo outlier.
#
# Regla estructural adoptada: pedir ~10 observaciones sobre el umbral, o sea
#
#       min_cell_samples  >=  10 / (1 - detection_percentile/100)
#
# p=98.0 con n=500 da exactamente 10. Ese es el ancla; el resto se deriva.
#
# | param                   | v2.0 | v2.1 | por que                                |
# |-------------------------|------|------|----------------------------------------|
# | detection_percentile    | 99.5 | 99.0 | con n=1000 da 10 obs sobre el umbral   |
# | min_cell_samples        | 500  | 1000 | = 10/(1-0.99). Sube junto al percentil |
# | time_bucket_minutes     |  5   | 30   | 6x muestras por bucket SIN tocar el    |
# |                         |      |      | estimador: el gate deja de excluir     |
# | min_sessions            | 15   | 10   | mitad de warmup; la calidad la sigue   |
# |                         |      |      | protegiendo min_cell_samples           |
# | lookback_sessions       | 20   | 20   | sin cambio                             |
# | export_floor_percentile | 95.0 | 95.0 | sin cambio: permite barrer [95,100]    |
#
# EFECTO MEDIDO sobre 6E 09-26 (2,08M ticks, 33 sesiones, barras M1):
#
#   |            | zonas | z/sesion | buckets activos |
#   |------------|-------|----------|-----------------|
#   | v2.0       |    37 |      1.6 | 16 de ~276 (6%) |
#   | v2.1       |   872 |     37.9 | 45 de 46  (98%) |
#
# El cuello de botella NO era el percentil sino el TAMANO DEL BUCKET. Una celda
# es (bucket, tick) pero el gate min_cell_samples aplica al BUCKET: con 5 min un
# bucket necesitaba ~25 ticks distintos visitados por sesion, y fuera de la
# manana de EEUU 6E toca 5-15. El dia quedaba 94% ciego por construccion.
#
# La resolucion en PRECIO no cambia: el bucket agrupa el baseline en el tiempo,
# no la celda. Se evaluo tambien bucket=15 (14,3 z/sesion) y se descarto: deja
# el 60% del dia sin evaluar, y para un POI un agujero estructural de ese tamano
# pesa mas que la resolucion temporal del baseline.
#
# Por que el cuello de botella era el bucket y no el percentil: una celda es
# (bucket, tick) y el gate min_cell_samples aplica al BUCKET. Con buckets de
# 5 min un bucket necesitaba ~25 ticks distintos visitados por sesion; fuera de
# la manana de EEUU 6E toca 5-15, asi que **solo 9 de ~276 buckets del dia**
# calificaban jamas. Medido sobre el oraculo denso del 2026-07-26.
#
# DECLARADO: la eleccion se hizo por el argumento estadistico de arriba, ANTES
# de medir cuantas zonas produce. El conteo resultante se reporta como
# consecuencia, no como criterio -- elegir parametros por "cuantas zonas
# dibuja" es un proceso de seleccion y consume grados de libertad.
DEFAULTS = dict(
    bucket_anchor="SessionRelative", time_bucket_minutes=30, lookback_sessions=20,
    profile_weighting="EqualSessionWeight", detection_source="TotalVolume",
    detection_method="Quantile", detection_percentile=99.0, robust_z_threshold=4.0,
    min_absolute_volume=10.0, min_sessions=10, min_cell_samples=1000,
    export_floor_percentile=95.0, merge_gap_ticks=0, min_zone_cells=1,
    invalidation_mode="CloseThrough", max_age_bars=2000, max_touches=0,
)

# Espacio paramétrico declarado (F6.1).
PARAM_SPEC = {
    "bucket_anchor": {"type": "str", "default": "SessionRelative",
                      "choices": ["SessionRelative", "WallClock"], "class": "recompute",
                      "branches": ["bucket_anchor"]},
    "time_bucket_minutes": {"type": "int", "default": 30, "min": 1, "class": "recompute",
                            "branches": ["bucket_size"], "suggested_grid": [15, 30, 60]},
    "lookback_sessions": {"type": "int", "default": 20, "min": 1, "class": "recompute",
                          "branches": ["lookback"], "suggested_grid": [10, 20, 40]},
    "profile_weighting": {"type": "str", "default": "EqualSessionWeight",
                          "choices": ["EqualSessionWeight", "PooledCells"], "class": "recompute",
                          "branches": ["weighting"]},
    "detection_source": {"type": "str", "default": "TotalVolume",
                         "choices": ["TotalVolume", "AbsDelta", "MaxSide"], "class": "recompute",
                         "branches": ["detection_source"]},
    "detection_method": {"type": "str", "default": "Quantile",
                         "choices": ["Quantile", "RobustZ"], "class": "recompute",
                         "branches": ["detection_method"]},
    "export_floor_percentile": {"type": "float", "default": 95.0, "min": 0.0, "max": 100.0,
                                "class": "recompute", "branches": ["export_floor"]},
    "detection_percentile": {"type": "float", "default": 99.0, "min": 0.0, "max": 100.0,
                             "class": "offline", "branches": ["quantile_cut"],
                             "requires_covered_by": "export_floor_percentile",
                             "suggested_grid": [98.0, 99.0, 99.5, 99.75]},
    "robust_z_threshold": {"type": "float", "default": 4.0, "min": 0.0, "class": "offline",
                           "branches": ["robustz_cut"], "suggested_grid": [3.0, 4.0, 5.0]},
    "min_absolute_volume": {"type": "float", "default": 10.0, "min": 0.0, "class": "offline",
                            "branches": ["min_vol"]},
    "min_sessions": {"type": "int", "default": 10, "min": 1, "class": "recompute",
                     "branches": ["profile_gate"]},
    "min_cell_samples": {"type": "int", "default": 1000, "min": 1, "class": "recompute",
                         "branches": ["profile_gate"]},
    "merge_gap_ticks": {"type": "int", "default": 0, "min": 0, "class": "offline",
                        "branches": ["geometry_merge"]},
    "min_zone_cells": {"type": "int", "default": 1, "min": 1, "class": "offline",
                       "branches": ["geometry_min_cells"]},
    "invalidation_mode": {"type": "str", "default": "CloseThrough",
                          "choices": ["CloseThrough", "FirstTouch"], "class": "lifecycle",
                          "branches": ["lifecycle_invalidation"]},
    "max_age_bars": {"type": "int", "default": 2000, "min": 1, "class": "lifecycle",
                     "branches": ["expiration"]},
    "max_touches": {"type": "int", "default": 0, "min": 0, "class": "lifecycle",
                    "branches": ["lifecycle_max_touches"]},
}

HEADER = ("event_seq,event_type,bar_index,bar_close_time,session_index,"
          "bucket,lower_tick,upper_tick,value,total_volume,threshold,empirical_pct,"
          "robust_z,sample_count,session_count,zone_id,touch_count,reason")


def meta_line(p, instrument, tick_size):
    return ("# meta,indicator=aVolCellPOI2,version=2.1,instrument={0},tick_size={1},"
            "bucket_anchor={2},bucket_minutes={3},lookback_sessions={4},weighting={5},"
            "source={6},method={7},percentile={8},robust_z={9},export_floor={10}").format(
        instrument, tick_size, p["bucket_anchor"], p["time_bucket_minutes"],
        p["lookback_sessions"], p["profile_weighting"], p["detection_source"],
        p["detection_method"], p["detection_percentile"], p["robust_z_threshold"],
        p["export_floor_percentile"])


class _Cache:
    __slots__ = ("values", "cumw", "totw", "n", "sessions", "threshold", "log_median", "mad_scaled")


def _weighted_quantile(c, q):
    """Menor valor con peso acumulado >= q * total (sin interpolacion)."""
    target = q * c.totw
    lo, hi = 0, len(c.values) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if c.cumw[mid] >= target:
            hi = mid
        else:
            lo = mid + 1
    return c.values[lo]


def _empirical_pct(c, x):
    lo, hi, idx = 0, len(c.values) - 1, -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if c.values[mid] <= x:
            idx = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return 0.0 if idx < 0 else c.cumw[idx] / c.totw


def _robust_z(c, v):
    y = math.log(1.0 + v)
    if c.mad_scaled == 0:
        return 999.0 if y > c.log_median else 0.0
    return (y - c.log_median) / c.mad_scaled


def run(ticks, bars, footprints, params=None, chart_tz="UTC"):
    p = {**DEFAULTS, **(params or {})}
    tz = tz_of(chart_tz)
    tick_size = ticks.tick_size
    det_cut = p["detection_percentile"] / 100.0

    rows, lines, active, all_zones = [], [], [], []
    seq = 0
    zone_seq = 0
    session_index = 0
    first_roll_done = False
    pending = {}          # bucket -> list[value]
    history = {}          # bucket -> deque[list[value]] (max lookback_sessions)
    cache_by_bucket = {}  # se limpia en cada roll (perfil congelado por sesion)

    skeys = [sessions.session_key(int(bars.start_ns[b])) for b in range(len(bars))]

    def emit(etype, b, t_ns, bucket, lo_t, hi_t, value, total, threshold, pct, z,
             n_samp, n_sess, zone_id, touches, reason):
        nonlocal seq
        seq += 1
        lines.append(",".join([
            str(seq), etype, str(b), ts_str(t_ns, tz, "%Y-%m-%dT%H:%M:%S"),
            str(session_index), str(bucket), str(lo_t), str(hi_t), plain(value),
            plain(total), plain(threshold), gnum(pct, 6), gnum(z, 4),
            str(n_samp), str(n_sess), str(zone_id), str(touches), reason or ""]))
        rows.append(dict(seq=seq, type=etype, bar_index=b, ts_ns=int(t_ns),
                         unix_ms=ns_to_ms(t_ns), bucket=bucket, lower_tick=lo_t,
                         upper_tick=hi_t, zone_id=zone_id, touch_count=touches,
                         reason=reason))

    def roll_session_into_history():
        nonlocal pending, first_roll_done, session_index
        if not first_roll_done:
            pending.clear()      # la primera sesion observada puede estar incompleta
            first_roll_done = True
        else:
            for bucket, vals in pending.items():
                if not vals:
                    continue
                q = history.setdefault(bucket, deque())
                q.append(vals)
                while len(q) > p["lookback_sessions"]:
                    q.popleft()
            pending = {}
            session_index += 1
        cache_by_bucket.clear()

    def build_cache(bucket):
        q = history.get(bucket)
        if q is None or len(q) < p["min_sessions"]:
            return None
        n = sum(len(s) for s in q)
        if n < p["min_cell_samples"]:
            return None
        pairs = []
        for s in q:
            w = 1.0 / len(s) if p["profile_weighting"] == "EqualSessionWeight" else 1.0
            pairs.extend((v, w) for v in s)
        pairs.sort(key=lambda x: x[0])
        c = _Cache()
        c.values = [v for v, _ in pairs]
        c.cumw = []
        tot = 0.0
        for _, w in pairs:
            tot += w
            c.cumw.append(tot)
        c.totw = tot
        c.n = n
        c.sessions = len(q)
        c.threshold = _weighted_quantile(c, det_cut)
        med_y = math.log(1.0 + _weighted_quantile(c, 0.5))
        dev = sorted((abs(math.log(1.0 + v) - med_y), w) for v, w in pairs)
        target, acc = 0.5 * tot, 0.0
        mad = dev[-1][0]
        for d, w in dev:
            acc += w
            if acc >= target:
                mad = d
                break
        c.log_median = med_y
        c.mad_scaled = 1.4826 * mad
        return c

    def get_cache(bucket):
        if bucket in cache_by_bucket:
            return cache_by_bucket[bucket]
        c = build_cache(bucket)
        cache_by_bucket[bucket] = c
        return c

    def get_bucket(b):
        anchor_ns = int(bars.end_ns[b]) - 1_000_000_000   # CONTRATO: cierre - epsilon
        if p["bucket_anchor"] == "SessionRelative":
            begin = sessions.session_begin_ns(anchor_ns)
            mins = (anchor_ns - begin) / 60e9
            if mins < 0:
                mins = 0.0
            return int(mins / max(1, p["time_bucket_minutes"]))
        from datetime import datetime, timezone as _tz
        d = datetime.fromtimestamp(anchor_ns / 1e9, tz=_tz.utc).astimezone(tz)
        return (d.hour * 60 + d.minute) // max(1, p["time_bucket_minutes"])

    def lifecycle(b, t_ns):
        hi = float(bars.high_t[b]) * tick_size
        lo = float(bars.low_t[b]) * tick_size
        close = float(bars.close_t[b]) * tick_size
        for z in list(reversed(active)):
            if z["created_bar"] >= b:
                continue
            touched = hi >= z["lower"] and lo <= z["upper"]
            if touched:
                z["touches"] += 1
                emit("ZONE_TOUCHED", b, t_ns, 0, z["lower_tick"], z["upper_tick"],
                     0, 0, 0, 0, 0, 0, 0, z["id"], z["touches"], "")
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
                emit("ZONE_INVALIDATED", b, t_ns, 0, z["lower_tick"], z["upper_tick"],
                     0, 0, 0, 0, 0, 0, 0, z["id"], z["touches"], reason)
                z.update(state="INVALIDATED", ended_ms=ns_to_ms(t_ns), end_reason=reason)
                active.remove(z)
            elif b - z["created_bar"] >= p["max_age_bars"]:
                emit("ZONE_EXPIRED", b, t_ns, 0, z["lower_tick"], z["upper_tick"],
                     0, 0, 0, 0, 0, 0, 0, z["id"], z["touches"], "max_age")
                z.update(state="EXPIRED", ended_ms=ns_to_ms(t_ns), end_reason="max_age")
                active.remove(z)

    def create_zones(anomalous, cache, bucket, b, t_ns):
        nonlocal zone_seq
        anomalous.sort(key=lambda c: c["tick"])
        groups, start = [], 0
        for i in range(1, len(anomalous) + 1):
            if i == len(anomalous) or anomalous[i]["tick"] - anomalous[i - 1]["tick"] > p["merge_gap_ticks"] + 1:
                groups.append(anomalous[start:i])
                start = i
        close = float(bars.close_t[b]) * tick_size
        for grp in groups:
            if len(grp) < p["min_zone_cells"]:
                continue
            zone_seq += 1
            lo_t, hi_t = grp[0]["tick"], grp[-1]["tick"]
            lower = (lo_t - 0.5) * tick_size
            upper = (hi_t + 0.5) * tick_size
            max_pct = max(c["pct"] for c in grp)
            max_z = max(c["z"] for c in grp)
            sum_val = sum(c["value"] for c in grp)
            sum_total = sum(c["total"] for c in grp)
            ref = 1 if close > upper else (-1 if close < lower else 0)
            z = dict(id=zone_seq, lower_tick=lo_t, upper_tick=hi_t, lower=lower,
                     upper=upper, created_bar=b, created_ms=ns_to_ms(t_ns),
                     ref_side=ref, touches=0, state="ACTIVE", ended_ms=None,
                     end_reason=None, max_pct=max_pct, max_z=max_z, cells=len(grp))
            active.append(z)
            all_zones.append(z)
            emit("ZONE_CREATED", b, t_ns, bucket, lo_t, hi_t, sum_val, sum_total,
                 cache.threshold, max_pct, max_z, cache.n, cache.sessions,
                 zone_seq, 0, "cells=" + str(len(grp)))

    for b in range(len(bars)):
        t_ns = int(bars.end_ns[b])

        # roll de sesion (mecanico: replica Bars.IsFirstBarOfSession)
        if b == 0 or skeys[b] != skeys[b - 1]:
            roll_session_into_history()

        # 1) ciclo de vida ANTES de crear zonas (anti look-ahead)
        lifecycle(b, t_ns)

        # 2) celdas de la barra actual (footprint reconstruido)
        fp_total = footprints.total[b]
        fp_ask = footprints.ask[b]
        fp_bid = footprints.bid[b]
        cells = []
        for tk in range(int(bars.low_t[b]), int(bars.high_t[b]) + 1):
            total = fp_total.get(tk, 0.0)
            if total <= 0:
                continue
            if p["detection_source"] == "AbsDelta":
                value = abs(fp_ask.get(tk, 0.0) - fp_bid.get(tk, 0.0))
            elif p["detection_source"] == "MaxSide":
                value = max(fp_ask.get(tk, 0.0), fp_bid.get(tk, 0.0))
            else:
                value = total
            cells.append(dict(tick=tk, value=value, total=total, pct=0.0, z=0.0))

        bucket = get_bucket(b)

        # 3) deteccion contra perfil congelado (sin la sesion actual)
        cache = get_cache(bucket)
        if cache is not None:
            anomalous = []
            for c in cells:
                c["pct"] = _empirical_pct(cache, c["value"])
                c["z"] = _robust_z(cache, c["value"])
                if c["pct"] * 100.0 >= p["export_floor_percentile"]:
                    emit("OBS", b, t_ns, bucket, c["tick"], c["tick"], c["value"],
                         c["total"], cache.threshold, c["pct"], c["z"],
                         cache.n, cache.sessions, 0, 0, "")
                is_anomaly = c["total"] >= p["min_absolute_volume"] and (
                    (c["value"] >= cache.threshold and c["pct"] >= det_cut)
                    if p["detection_method"] == "Quantile"
                    else c["z"] >= p["robust_z_threshold"])
                if is_anomaly:
                    anomalous.append(c)
            if anomalous:
                create_zones(anomalous, cache, bucket, b, t_ns)

        # 4) acumular la barra actual al pending (DESPUES de la comparacion)
        if cells:
            dst = pending.setdefault(bucket, [])
            for c in cells:
                dst.append(c["value"])

    zones = [dict(id=str(z["id"]), indicator=NAME, top=z["upper"], bottom=z["lower"],
                  created_ms=z["created_ms"], ended_ms=z["ended_ms"], state=z["state"],
                  kind="vol_cell_poi", touches=z["touches"], end_reason=z["end_reason"],
                  timeline=[]) for z in all_zones]

    return dict(indicator=NAME, params=p, header=HEADER, csv_lines=lines,
                events=rows, zones=zones,
                params_line=meta_line(p, ticks.instrument, tick_size))
