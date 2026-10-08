# -*- coding: utf-8 -*-
"""aVolZonePOI — espejo de nt8/aVolZonePOI.cs (versión EdgeLab 2026-10-07, sin grupos de alerta).

Reglas del .cs, en orden:
- La barra 0 no se procesa (`CurrentBar < 1 → return`). Sus ticks quedan en el acumulador y se suman a la barra 1,
  filtrados al rango de la barra 1.
- Bloques de `window_bars` barras **consecutivas, sin reinicio por sesión**.
- Al cerrar el bloque, se suman los perfiles por precio. Si hay menos de 3 niveles, score 0. Si no:
  - mediana = valor ordenado en `n // 2`;
  - un nivel es hot si su volumen es ≥ mediana × `median_multiplier`;
  - clusters de niveles hot con hueco ≤ `max_gap_ticks`, de `min_cluster_ticks` niveles o más.
- **Cada** cluster se evalúa contra el percentil (interpolación lineal) de la cola de su franja de `bucket_min`
  minutos, en hora del chart, si esa cola tiene ≥ `min_samples` valores. Si no, usa la cola global, y si tampoco
  alcanza, no se evalúa. Es zona si score ≥ umbral y umbral > 0.
- Después se encola el mejor score del bloque (0 si no hubo clusters) en la cola de la franja y en la global, con
  un máximo de 2.000 valores cada una.
"""
from __future__ import annotations

from collections import deque
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

DEFAULTS = dict(window_bars=10, median_multiplier=2.0, max_gap_ticks=1, min_cluster_ticks=2, bucket_min=5,
                detection_percentile=95.0, min_samples=10, max_samples=2000)


def _pct(sorted_v, p):
    n = len(sorted_v)
    if n == 0:
        return 0.0
    if n == 1:
        return float(sorted_v[0])
    r = p * (n - 1)
    lo = int(np.floor(r))
    hi = min(lo + 1, n - 1)
    return float(sorted_v[lo] + (r - lo) * (sorted_v[hi] - sorted_v[lo]))


def run(bars, footprints, params=None, chart_tz="America/Argentina/Buenos_Aires"):
    """footprints: TotalFootprintCSR (build_total_footprint_csr_nt8). Devuelve dict(zones=[...], blocks=[...]).
    La barra 0 se suma a la barra 1 (acumulador del .cs), filtrada al rango de la barra 1."""
    p = {**DEFAULTS, **(params or {})}
    n = len(bars.close_t)
    end = pd.to_datetime(np.asarray(bars.end_ns, dtype=np.int64), utc=True).tz_convert(ZoneInfo(chart_tz))
    bucket = ((end.hour * 60 + end.minute) // max(1, int(p["bucket_min"]))).to_numpy()
    F_off, F_t, F_v = footprints.offsets, footprints.ticks, footprints.vols
    lo_t, hi_t = np.asarray(bars.low_t), np.asarray(bars.high_t)
    W, mult, gap, minc = int(p["window_bars"]), float(p["median_multiplier"]), int(p["max_gap_ticks"]), int(p["min_cluster_ticks"])
    q, minS, maxS = float(p["detection_percentile"]) / 100.0, int(p["min_samples"]), int(p["max_samples"])
    queues, glob = {}, deque(maxlen=maxS)
    zones, blocks = [], []
    blk = []
    for b in range(1, n):
        if b == 1:                                  # ticks de la barra 0 que caen en el rango de la barra 1
            t0, v0 = F_t[F_off[0]:F_off[2]], F_v[F_off[0]:F_off[2]]
            m = (t0 >= lo_t[1]) & (t0 <= hi_t[1])
            blk.append((t0[m], v0[m]))
        else:
            blk.append((F_t[F_off[b]:F_off[b + 1]], F_v[F_off[b]:F_off[b + 1]]))
        if len(blk) < W:
            continue
        tt = np.concatenate([x[0] for x in blk]); vv = np.concatenate([x[1] for x in blk])
        blk = []
        bk = int(bucket[b])
        qb = queues.setdefault(bk, deque(maxlen=maxS))
        best = 0.0
        lv = 0
        if len(tt):
            ut, inv = np.unique(tt, return_inverse=True)
            uv = np.bincount(inv, weights=vv)
            lv = len(ut)
        if lv >= 3:
            med = np.sort(uv)[lv // 2]
            hm = uv >= med * mult
            ht, hv = ut[hm], uv[hm]
            if len(ht) >= minc:
                brk = np.flatnonzero(np.diff(ht) - 1 > gap + 0.01) + 1
                st = np.r_[0, brk]; en = np.r_[brk, len(ht)]
                ev_q = qb if len(qb) >= minS else (glob if len(glob) >= minS else None)
                thr = _pct(np.sort(np.fromiter(ev_q, float)), q) if ev_q is not None else None
                for s_, e_ in zip(st, en):
                    if e_ - s_ < minc:
                        continue
                    sc = float(hv[s_:e_].sum())
                    best = max(best, sc)
                    if thr is None or sc < thr or thr <= 0:
                        continue
                    zones.append(dict(bar=b, end_ns=int(bars.end_ns[b]), low_tick=int(ht[s_]), high_tick=int(ht[e_ - 1]),
                                      levels=int(e_ - s_), score=sc, thresh=thr, eval_samples=len(ev_q), bucket=bk))
        blocks.append((b, lv, best, bk))
        qb.append(best)
        glob.append(best)
    return dict(zones=zones, blocks=blocks)
