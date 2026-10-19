# -*- coding: utf-8 -*-
"""Detector de régimen rango / tendencia (target-free). Etapa 0 de VTD-DIR (docs/research/VTD_DIR_PROPUESTA_20261006.md).

Por barra t, sólo con información hasta t y sin cruzar sesiones:
- eficiencia E_N = |close_t − close_{t−N}| / Σ|Δclose| en las últimas N barras ∈ [0, 1] (1 = recorrido recto);
- amplitud A_N = (máx high − mín low en N barras) / minutos transcurridos (ticks por minuto).
Umbrales de E salen de un NULO de random walk: los incrementos de la misma sesión permutados al azar (rompe la
dependencia serial y conserva su distribución). Estado: RANGO si E < q33 del nulo, TENDENCIA si E > q67 del nulo,
NEUTRO en el resto. Bajo el nulo, cada estado ocupa un tercio por construcción; en datos reales la desviación de ese
tercio, y la persistencia contra el nulo, es la información.
"""
from __future__ import annotations

import numpy as np

RANGO, NEUTRO, TENDENCIA = -1, 0, 1


def _session_starts(send):
    return np.r_[0, np.flatnonzero(np.diff(send)) + 1]


def efficiency(close, send, N):
    """E_N por barra (NaN si la ventana cruza sesión o no hay N barras previas)."""
    c = np.asarray(close, dtype=float)
    n = len(c)
    d = np.abs(np.diff(c, prepend=c[0]))
    d[_session_starts(send)] = 0.0
    cs = np.cumsum(d)
    E = np.full(n, np.nan)
    t = np.arange(N, n)
    same = send[t - N] == send[t]
    path = cs[t] - cs[t - N]
    net = np.abs(c[t] - c[t - N])
    with np.errstate(invalid="ignore", divide="ignore"):
        e = np.where(path > 0, net / path, 0.0)
    E[t[same]] = e[same]
    return E


def amplitude(high, low, end_ns, send, N):
    import pandas as pd
    hi = pd.Series(np.asarray(high, float)).rolling(N).max().to_numpy()
    lo = pd.Series(np.asarray(low, float)).rolling(N).min().to_numpy()
    end = np.asarray(end_ns, dtype=np.int64)
    A = np.full(len(end), np.nan)
    t = np.arange(N, len(end))
    same = send[t - N] == send[t]
    mins = np.maximum((end[t] - end[t - N]) / 6e10, 1e-3)
    A[t[same]] = ((hi[t] - lo[t]) / mins)[same]
    return A


def null_close(close, send, rng):
    """Serie nula: incrementos permutados dentro de cada sesión, anclados al primer close de la sesión."""
    c = np.asarray(close, dtype=float)
    out = np.empty_like(c)
    st = _session_starts(send)
    en = np.r_[st[1:], len(c)]
    for a, b in zip(st, en):
        inc = np.diff(c[a:b])
        rng.shuffle(inc)
        out[a:b] = c[a] + np.r_[0.0, np.cumsum(inc)]
    return out


def null_thresholds(close, send, N, rng, reps=3):
    vals = []
    for _ in range(reps):
        e = efficiency(null_close(close, send, rng), send, N)
        vals.append(e[np.isfinite(e)])
    v = np.concatenate(vals)
    return float(np.quantile(v, 1 / 3)), float(np.quantile(v, 2 / 3))


def classify(E, q33, q67):
    s = np.full(len(E), np.nan)
    ok = np.isfinite(E)
    s[ok] = np.where(E[ok] < q33, RANGO, np.where(E[ok] > q67, TENDENCIA, NEUTRO))
    return s
