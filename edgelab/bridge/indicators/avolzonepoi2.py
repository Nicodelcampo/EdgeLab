# -*- coding: utf-8 -*-
"""aVolZonePOI2 — espejo de nt8/aVolZonePOI2.cs (EdgeLab 2026-10-07).

Por barra primaria, en el orden del .cs:
1. Si es la primera barra de la sesión: se pasan a la historia los scores de la sesión que terminó (se conservan
   las últimas `lookback` sesiones) y se descarta el bloque parcial.
2. El perfil de la barra (ticks dentro de [low, high]) se suma al bloque.
3. Las zonas en observación de orderblock acumulan el volumen operado dentro y el total. En la primera barra en que el
   precio queda a max(away_heights x altura, min_away_ticks) ticks del borde, la zona es orderblock (2) si el volumen
   dentro es <= max_inside_pct %, y si no es normal (1). Si pasan `ob_bars` barras sin alejarse, es normal.
4. Si el bloque llegó a `window_bars` barras, se procesa:
   - con >= 3 niveles: hot si el volumen es >= mediana (valor ordenado en n // 2) x mult;
   - clusters de niveles hot con hueco de precio <= gap y >= minc niveles;
   - score = suma, o suma / ancho en modo densidad;
   - es zona si el umbral es > 0 y el score es >= umbral. El umbral es el percentil, con interpolación lineal, de la
     historia de su franja de `bucket_min` minutos en hora de Chicago, y sólo se calcula si hay >= `min_samples` valores;
   - se encola el mejor score (0 si no hubo clusters) en la sesión en curso.
5. Racimo (al nacer cada zona, antes de agregarla): candidatas = zonas creadas en las últimas `racimo_bars` barras
   (recorridas de la más nueva a la más vieja) + la nueva. Para cada candidata como base, franja
   [low_base, low_base + altura - 1]; tiene que contener a la nueva; se cuentan las candidatas completas adentro; gana
   la primera franja con más zonas. Si son >= racimo_min: se arma o amplía un racimo (sólo si sigue entrando en la
   altura) y las zonas sin racimo_bar lo reciben = barra actual.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

DEFAULTS = dict(window_bars=10, median_multiplier=2.0, max_gap_ticks=1, min_cluster_ticks=2, score_mode="Suma",
                bucket_min=15, detection_percentile=95.0, lookback_sessions=20, min_samples=20,
                ob_bars=100, ob_away_heights=3.0, ob_min_away_ticks=8, ob_max_inside_pct=2.0,
                racimo_min=5, racimo_bars=135, racimo_altura_ticks=18)


def _pct(s, p):
    n = len(s)
    if n == 0:
        return 0.0
    if n == 1:
        return float(s[0])
    r = p * (n - 1)
    lo = int(np.floor(r))
    hi = min(lo + 1, n - 1)
    return float(s[lo] + (r - lo) * (s[hi] - s[lo]))


def run(bars, footprints, session_id, params=None):
    """footprints: TotalFootprintCSR NT8 (ya filtrado al rango de cada barra). session_id: id de sesión por barra."""
    p = {**DEFAULTS, **(params or {})}
    n = len(bars.close_t)
    end = pd.to_datetime(np.asarray(bars.end_ns, dtype=np.int64), utc=True).tz_convert("America/Chicago")
    bucket = ((end.hour * 60 + end.minute) // max(1, int(p["bucket_min"]))).to_numpy()
    F_off, F_t, F_v = footprints.offsets, footprints.ticks, footprints.vols
    lo_t, hi_t = np.asarray(bars.low_t, dtype=np.int64), np.asarray(bars.high_t, dtype=np.int64)
    W, mult, gap, minc = int(p["window_bars"]), float(p["median_multiplier"]), int(p["max_gap_ticks"]), int(p["min_cluster_ticks"])
    dens = p["score_mode"] == "Densidad"
    q = float(p["detection_percentile"]) / 100.0
    hist = defaultdict(list)
    pending = defaultdict(list)
    cache = {}
    sess_idx = -1
    blk_t, blk_v = [], []
    cnt = 0
    zones, blocks, watching, clusters = [], [], [], []
    for b in range(n):
        if b == 0 or session_id[b] != session_id[b - 1]:
            if sess_idx >= 0:
                for k, v in pending.items():
                    hist[k].extend((sess_idx, x) for x in v)
                mn = sess_idx - int(p["lookback_sessions"]) + 1
                for k in list(hist):
                    hist[k] = [x for x in hist[k] if x[0] >= mn]
                cache.clear()
            pending = defaultdict(list)
            sess_idx += 1
            blk_t, blk_v, cnt = [], [], 0
        t, v = F_t[F_off[b]:F_off[b + 1]], F_v[F_off[b]:F_off[b + 1]]
        blk_t.append(t); blk_v.append(v)
        if watching:
            tot = float(v.sum())
            lo, hi = int(lo_t[b]), int(hi_t[b])
            keep = []
            for z in watching:
                z["vin"] += float(v[(t >= z["low_tick"]) & (t <= z["high_tick"])].sum())
                z["vall"] += tot
                z["max_away"] = max(z["max_away"], hi - z["high_tick"], z["low_tick"] - lo)
                z["seen"] += 1
                need = max(p["ob_away_heights"] * (z["high_tick"] - z["low_tick"] + 1), p["ob_min_away_ticks"])
                z["inside_pct"] = 100.0 * z["vin"] / z["vall"] if z["vall"] > 0 else 0.0
                if z["max_away"] >= need:
                    z["state"] = 2 if z["inside_pct"] <= p["ob_max_inside_pct"] else 1
                elif z["seen"] >= p["ob_bars"]:
                    z["state"] = 1
                else:
                    keep.append(z)
                    continue
                z["decided_bar"] = b
            watching = keep
        cnt += 1
        if cnt < W:
            continue
        tt = np.concatenate(blk_t); vv = np.concatenate(blk_v)
        blk_t, blk_v, cnt = [], [], 0
        bk = int(bucket[b])
        best = 0.0
        ut = np.unique(tt)
        nl = len(ut)
        if nl >= 3:
            inv = np.searchsorted(ut, tt)
            uv = np.bincount(inv, weights=vv, minlength=nl)
            hot = np.sort(uv)[nl // 2] * mult
            hi_idx = np.flatnonzero(uv >= hot)
            if bk not in cache:
                cache[bk] = np.sort(np.array([x for _s, x in hist.get(bk, [])], dtype=float))
            srt = cache[bk]
            thr = _pct(srt, q) if len(srt) >= p["min_samples"] else -1.0
            g = 0
            while g < len(hi_idx):
                e = g
                while e + 1 < len(hi_idx) and ut[hi_idx[e + 1]] - ut[hi_idx[e]] - 1 <= gap:
                    e += 1
                c = e - g + 1
                if c >= minc:
                    s = float(uv[hi_idx[g:e + 1]].sum())
                    lk, hk = int(ut[hi_idx[g]]), int(ut[hi_idx[e]])
                    sc = s / (hk - lk + 1) if dens else s
                    best = max(best, sc)
                    if thr > 0 and sc >= thr:
                        z = dict(bar=b, end_ns=int(bars.end_ns[b]), low_tick=lk, high_tick=hk, levels=c, score=sc,
                                 thresh=thr, samples=len(srt), state=0, vin=0.0, vall=0.0, max_away=0, seen=0,
                                 inside_pct=0.0, decided_bar=None, racimo_bar=-1, rac=None)
                        _racimo(z, zones, clusters, b, p)
                        zones.append(z)
                        if p["ob_bars"] > 0:
                            watching.append(z)
                        else:
                            z["state"] = 1
                g = e + 1
        pending[bk].append(best)
        blocks.append((b, nl, best, bk, sess_idx))
    ids = {id(c): i for i, c in enumerate(clusters)}
    for z in zones:
        z["racimo_id"] = ids[id(z["rac"])] if z["rac"] is not None else -1
        del z["rac"]
    return dict(zones=zones, blocks=blocks, clusters=[dict(c) for c in clusters])


def _racimo(nz, zones, clusters, b, p):
    if p["racimo_min"] <= 1:
        return
    cand = []
    for z in reversed(zones):
        if nz["bar"] - z["bar"] > p["racimo_bars"]:
            break
        cand.append(z)
    cand.append(nz)
    A = int(p["racimo_altura_ticks"])
    best = None
    for bz in cand:
        lo, hi = bz["low_tick"], bz["low_tick"] + A - 1
        if nz["low_tick"] < lo or nz["high_tick"] > hi:
            continue
        inside = [z for z in cand if z["low_tick"] >= lo and z["high_tick"] <= hi]
        if best is None or len(inside) > len(best):
            best = inside
    if best is None or len(best) < p["racimo_min"]:
        return
    clo = min(m["low_tick"] for m in best); chi = max(m["high_tick"] for m in best); cst = min(m["bar"] for m in best)
    cl = None
    for m in best:
        r = m.get("rac")
        if r is not None and max(chi, r["high"]) - min(clo, r["low"]) + 1 <= A:
            cl = r
            break
    if cl is None:
        cl = dict(start=cst, low=clo, high=chi, bar=b, start0=cst, low0=clo, high0=chi)   # *0 = snapshot al formarse
        clusters.append(cl)
    else:
        cl["start"] = min(cl["start"], cst); cl["low"] = min(cl["low"], clo); cl["high"] = max(cl["high"], chi)
    for m in best:
        if m.get("rac") is None:
            m["rac"] = cl
    for m in best:
        if m["racimo_bar"] < 0:
            m["racimo_bar"] = b
