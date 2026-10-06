# -*- coding: utf-8 -*-
"""aVolClusterPOI v0.5 — versión RÁPIDA de avolclusterpoi_full.run_full (mismo resultado, verificado por
tests/test_avolclusterpoi_fast.py y por la paridad NT8 50t 934/934 y 200t 338/338).
Cambios, todos sin efecto en el resultado: footprint del bloque agregado con numpy desde el CSR al cerrar el bloque
(no por tick en cada barra); historia del umbral ordenada una vez por sesión; clusters y scores vectorizados; fin de
sesión precalculado. Requiere footprints CSR (`build_total_footprint_csr_nt8`).

Original: espejo COMPLETO de nt8/aVolClusterPOI.cs (OnBarUpdate barra a barra).

Agregado 2026-10-05 para el visor (panel de Indicadores con los mismos parámetros que NT8) y para la paridad de
eventos: ZONE_CREATED / AT_PRICE_CREATED / FIRST_TOUCH / ZONE_INVALIDATED / ZONE_EXPIRED, métricas por zona
(score, ratio, share, densidad, calidad, distancia, ráfaga) y reacciones (target / stop / timeout / ambiguo).
Orden por barra idéntico al .cs: (1.ª barra de sesión → commit de historia) → perfil al bloque → ciclo de vida
(sólo zonas de barras anteriores, sólo OFF_PRICE) → cierre de bloque. Los ids siguen la misma secuencia que NT8
(OFF_PRICE y AT_PRICE comparten contador).
Para paridad, los footprints se arman con `build_footprints(..., nt8_subseries=True)`.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import math

import numpy as np

from edgelab.bridge.indicators.avolclusterpoi import NAME, NS, VERSION
from edgelab.bridge.indicators.avolclusterpoi_full import FULL_DEFAULTS, INVALIDATION_MODES, _clamp01

def run_full_fast(ticks, bars, footprints, params=None, chart_tz="America/Argentina/Buenos_Aires", session_ends=None):
    from edgelab.bridge.sessions import session_begin_ns, session_end_ns

    p = {**FULL_DEFAULTS, **(params or {})}
    if p["invalidation_mode"] not in INVALIDATION_MODES:
        raise ValueError("invalidation_mode: " + str(p["invalidation_mode"]))
    n = len(bars.close_t)
    tz = ZoneInfo(chart_tz)
    tick_size = float(ticks.tick_size)
    if not hasattr(footprints, "offsets"):
        raise TypeError("run_full_fast requiere footprints CSR (build_total_footprint_csr_nt8)")
    F_off, F_t, F_v = footprints.offsets, footprints.ticks, footprints.vols
    if session_ends is None:
        from edgelab.bridge.sessions import session_end_ns as _se
        ends_all = np.asarray(bars.end_ns, dtype=np.int64)
        # fin de sesión por barra: misma función que el original, evaluada una vez por minuto único
        um, inv_ = np.unique(ends_all // 60_000_000_000, return_inverse=True)
        first = np.zeros(len(um), dtype=np.int64)
        first[inv_[::-1]] = np.arange(n)[::-1]
        se_first = np.fromiter((_se(int(ends_all[k])) for k in first), dtype=np.int64, count=len(um))
        session_ends = se_first[inv_]
        # dentro de un mismo minuto el fin de sesión sólo puede cambiar si el minuto contiene el cierre 16:00 CT:
        # esas barras se recalculan una por una
        chk = np.flatnonzero(se_first[inv_] <= ends_all)
        for k in chk:
            session_ends[k] = _se(int(ends_all[k]))
    hs_sorted = {}                            # bucket -> np.ndarray ordenado (se invalida en cada commit de sesión)
    block_start = 0
    W = int(p["window_bars"])
    inv = p["invalidation_mode"]
    hist = defaultdict(list)                  # bucket -> [(sesión, score)]
    pending = defaultdict(list)
    session_index, prev_sess, sess_begin = -1, None, None
    last_session_first_bar = 0
    block, block_n = {}, 0
    zones, events, creations, live, blocks = [], [], [], [], []
    next_id = 1
    cnt = dict(target=0, stop=0, timeout=0, ambiguous=0)

    def t_ms(b):
        return int(bars.end_ns[b]) // 1_000_000

    def ev(kind, z, b, reason="", touches=0):
        events.append(dict(event_type=kind, zone_id=z["id"], bar=b, time_ms=t_ms(b), lower_tick=z["lower_tick"],
                           upper_tick=z["upper_tick"], reason=reason, touch_count=touches))

    def bucket_of(b):
        anchor = int(bars.end_ns[b]) - NS
        if p["use_session_buckets"] and sess_begin is not None and anchor >= sess_begin:
            return int((anchor - sess_begin) // (int(p["time_bucket_minutes"]) * 60 * NS))
        lt = datetime.fromtimestamp(anchor / NS, timezone.utc).astimezone(tz)
        return (lt.hour * 60 + lt.minute) // int(p["time_bucket_minutes"])

    def finish(z, outcome):
        if z["outcome_done"]:
            return
        z["outcome_done"] = True
        z["outcome"] = outcome
        cnt[outcome.lower()] += 1

    def update_outcome(z, b, lo, hi):
        if z["direction"] > 0:
            fav, adv = max(0, hi - z["upper_tick"]), max(0, z["upper_tick"] - lo)
        else:
            fav, adv = max(0, z["lower_tick"] - lo), max(0, hi - z["lower_tick"])
        z["mfe_ticks"] = max(z["mfe_ticks"], fav)
        z["mae_ticks"] = max(z["mae_ticks"], adv)
        hit_t, hit_s = fav >= p["reaction_target_ticks"], adv >= p["reaction_stop_ticks"]
        if hit_t and hit_s:
            finish(z, "AMBIGUOUS")
        elif hit_t:
            finish(z, "TARGET")
        elif hit_s:
            finish(z, "STOP")
        elif b - z["touch_bar"] + 1 >= p["reaction_horizon_bars"]:
            finish(z, "TIMEOUT")

    def kill(z, b, kind, reason):
        z["active"] = False
        z["ended_bar"] = b
        z["ended_ms"] = t_ms(b)
        z["state"] = "EXPIRED" if kind == "ZONE_EXPIRED" else "INVALIDATED"
        z["end_reason"] = reason
        ev(kind, z, b, reason, z["touches"])

    for b in range(n):
        s_end = int(session_ends[b])
        if s_end != prev_sess:                                      # Bars.IsFirstBarOfSession → CommitSession
            if session_index >= 0 and pending:
                for k, v in pending.items():
                    hist[k].extend((session_index, x) for x in v)
                mn = session_index - int(p["lookback_sessions"]) + 1
                for k in list(hist):
                    hist[k] = [s for s in hist[k] if s[0] >= mn]
                hs_sorted.clear()
            pending = defaultdict(list)
            session_index += 1
            prev_sess = s_end
            sess_begin = session_begin_ns(int(bars.end_ns[b]))
            last_session_first_bar = b
            block_n = 0
            block_start = b
        lo, hi, cl = int(bars.low_t[b]), int(bars.high_t[b]), int(bars.close_t[b])
        block_n += 1

        # ---- ciclo de vida
        for z in live:
            if z["created_bar"] >= b or z["kind"] == "AT_PRICE":
                continue
            if z["outcome_started"] and not z["outcome_done"]:
                update_outcome(z, b, lo, hi)
            if not z["active"]:
                continue
            if p["max_age_bars"] > 0 and b - z["created_bar"] >= p["max_age_bars"]:
                kill(z, b, "ZONE_EXPIRED", "max_age")
                continue
            if lo <= z["upper_tick"] and hi >= z["lower_tick"]:
                z["touches"] += 1
                if not z["first_touch"]:
                    z["first_touch"] = True
                    z["first_touch_ms"] = t_ms(b)
                    ev("FIRST_TOUCH", z, b, "first_touch", 1)
                    if not z["outcome_started"] and z["direction"] != 0:
                        z["outcome_started"] = True
                        z["touch_bar"] = b
                        update_outcome(z, b, lo, hi)
                if inv == "FirstTouch":
                    kill(z, b, "ZONE_INVALIDATED", "first_touch")
                    continue
                if p["max_touches"] > 0 and z["touches"] >= p["max_touches"]:
                    kill(z, b, "ZONE_INVALIDATED", "max_touches")
                    continue
            if inv == "CloseThrough":
                if z["ref_side"] == 1 and cl < z["lower_tick"]:
                    kill(z, b, "ZONE_INVALIDATED", "close_through_down")
                    continue
                if z["ref_side"] == -1 and cl > z["upper_tick"]:
                    kill(z, b, "ZONE_INVALIDATED", "close_through_up")
                    continue

        # ---- cierre de bloque
        if block_n < W:
            continue
        bucket = bucket_of(b)
        best = 0.0
        a_, z_ = F_off[block_start], F_off[b + 1]
        bt_, inv_b = np.unique(F_t[a_:z_], return_inverse=True)
        bv_ = np.bincount(inv_b, weights=F_v[a_:z_], minlength=len(bt_)) if len(bt_) else np.zeros(0)
        best_c = None
        if len(bt_) >= 3:
            if p["use_topk_hot_cells"]:
                k_ = max(int(p["min_cluster_ticks"]), round(float(p["hot_fraction"]) * len(bt_)))
                o_ = np.lexsort((bt_, -bv_))[:k_]
                hm = np.zeros(len(bt_), bool); hm[o_] = True
            else:
                med = np.sort(bv_)[len(bv_) // 2]
                hm = bv_ >= med * float(p["median_multiplier"])
            ht, hv = bt_[hm], bv_[hm]
            if len(ht):
                brk = np.flatnonzero(np.diff(ht) - 1 > int(p["max_gap_ticks"])) + 1
                st_ = np.r_[0, brk]; en_ = np.r_[brk, len(ht)]
                ln_ = en_ - st_
                cs_ = np.r_[0.0, np.cumsum(hv)]
                sc_all = cs_[en_] - cs_[st_]
                okc = ln_ >= p["min_cluster_ticks"]
                st_, en_, sc_all = st_[okc], en_[okc], sc_all[okc]
            else:
                st_ = en_ = sc_all = np.zeros(0)
            hsv = hs_sorted.get(bucket)
            if hsv is None:
                hsv = np.sort(np.array([x for _s, x in hist.get(bucket, [])], dtype=float))
                hs_sorted[bucket] = hsv
            nh = len(hsv)
            if nh and nh >= p["min_samples_per_bucket"]:
                kq = min(max(int(math.ceil(float(p["detection_percentile"] / 100.0) * nh)), 1), nh)
                thr = float(hsv[kq - 1])
            else:
                thr = None
            total = float(bv_.sum())
            best_s = 0.0
            if len(sc_all):
                best = max(best, float(sc_all.max()))
                if thr is not None and thr > 0:
                    q_ = np.flatnonzero(sc_all >= thr)
                    if len(q_):
                        iq = q_[np.argmax(sc_all[q_])]
                        best_c = [int(x) for x in ht[int(st_[iq]):int(en_[iq])]]
                        best_s = float(sc_all[iq])
            hs = hsv
            if best_c is not None:
                lower, upper = best_c[0], best_c[-1]
                direction = 1 if cl > upper else (-1 if cl < lower else 0)
                distance = (cl - upper) if direction == 1 else ((lower - cl) if direction == -1 else 0)
                width = upper - lower + 1
                ratio = best_s / thr
                share = best_s / total if total > 0 else 0.0
                density = len(best_c) / width if width > 0 else 0.0
                creations[:] = [c for c in creations if b - c[0] <= p["burst_window_bars"]]
                burst = sum(1 for c in creations if abs(c[1] - (lower + upper)) <= 2 * p["burst_range_ticks"]) + 1
                q = 100.0 * (0.35 * _clamp01((ratio - 1.0) / 0.5) + 0.25 * _clamp01(share / 0.2)
                             + 0.15 * _clamp01(density)
                             + 0.15 * _clamp01(distance / max(1, p["rejection_full_score_ticks"]))
                             + 0.10 * (_clamp01(burst / p["burst_min_zones"]) if p["burst_min_zones"] > 0 else 0.0))
                off = direction != 0
                passes = off and q >= p["min_quality_score"]
                if p["max_distance_from_zone_ticks"] > 0 and distance > p["max_distance_from_zone_ticks"]:
                    passes = False
                if not (p["enable_predictive_filter"] and not passes):
                    kind = "OFF_PRICE" if off else "AT_PRICE"
                    side = "OCC" if not off else ("SOP" if direction > 0 else "RES")
                    z = dict(id=str(next_id), indicator=NAME, kind=kind, created_bar=b, created_ms=t_ms(b),
                             lower_tick=lower, upper_tick=upper, top=(upper + 0.5) * tick_size,
                             bottom=(lower - 0.5) * tick_size, score=best_s, threshold=thr, samples=len(hs),
                             bucket=bucket, direction=direction, ref_side=direction, anomaly_ratio=ratio,
                             cluster_share=share, density=density, quality_score=q, distance_ticks=distance,
                             burst_count=burst, active=True, state="ACTIVE", ended_ms=None, ended_bar=None,
                             end_reason=None, touches=0, first_touch=False, first_touch_ms=None,
                             outcome_started=False, outcome_done=False, outcome="", touch_bar=None,
                             mfe_ticks=0, mae_ticks=0, label="%s Q%.0f R%.2f" % (side, q, ratio))
                    next_id += 1
                    zones.append(z)
                    if off:                                 # AT_PRICE: el ciclo de vida siempre la saltea
                        live.append(z)
                    creations.append((b, lower + upper))
                    ev("AT_PRICE_CREATED" if not off else "ZONE_CREATED", z, b, kind)
        pending[bucket].append(best)
        blocks.append((b, float(bv_.sum()), bucket))      # registro liviano de cada bloque cerrado (controles)
        block_n = 0
        block_start = b + 1
        # NT8: zones.RemoveAll(!Active && (!OutcomeStarted || OutcomeDone)) al cerrar bloque (sólo afecta el recorrido)
        live[:] = [z for z in live if z["active"] or (z["outcome_started"] and not z["outcome_done"])]

    ready = sum(1 for v in hist.values() if len(v) >= p["min_samples_per_bucket"])
    last = zones[-1] if zones else None
    act = [z for z in zones if z["active"] and z["kind"] == "OFF_PRICE"]
    return dict(indicator=NAME, version=VERSION, params=p, zones=zones, events=events, blocks=blocks,
                dashboard=dict(sessions_complete=max(session_index, 0), buckets_ready=ready,
                               samples=sum(len(v) for v in hist.values()), zones_total=len(zones),
                               zones_last_session=sum(1 for z in zones if z["created_bar"] >= last_session_first_bar),
                               active=len(act), active_support=sum(1 for z in act if z["direction"] > 0),
                               active_resistance=sum(1 for z in act if z["direction"] < 0), outcomes=cnt,
                               last_zone=None if last is None else dict(kind=last["kind"], direction=last["direction"],
                                   quality=last["quality_score"], ratio=last["anomaly_ratio"],
                                   mid=(last["lower_tick"] + last["upper_tick"]) * 0.5 * tick_size)))
