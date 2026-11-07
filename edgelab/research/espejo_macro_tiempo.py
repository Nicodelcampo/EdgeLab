"""ESPEJO-MACRO-10T-TIEMPO (2026-11-07, Nico: «ajustá los parámetros para que sí aparezcan operaciones donde no alcanzan»).

Variante de ESPEJO-MACRO-10T (`espejo_macro_grilla.py`, que no se toca: sus réplicas siguen corriendo con ese código). En el barrido
original el límite de la ida era de 400 VELAS de 10 ticks: en NQ son ~11 minutos de media, pero en ES (muchas más operaciones por
minuto) son pocos minutos y casi nunca entra un movimiento del ancho mínimo, así que ES quedó con 0 celdas evaluables e YM con 504.

Cambio único, declarado: el límite de la ida y de la búsqueda pasa a TIEMPO (ida <= 60 min desde A; ida + vuelta <= 120 min), y la
duración de la ida pasa a ser una perilla EN MINUTOS (<= 10 · <= 30 · <= 60). La celda <= 10 min queda cerca de la regla original;
30 y 60 abren el espacio donde no alcanzaba. Ancho mínimo en viajes de fricción severa, mínimos de velas de ida (8) y vuelta (4),
retrocesos, fracciones, ejecuciones y salidas: iguales al padre. El detector es el mismo (causal, A = origen real), con el corte en
segundos en vez de en velas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import espejo_macro_grilla as P
from edgelab.research.espejo_macro_grilla import (EJECUCIONES, EXCLUIR_EVENTOS, FRACCIONES, LINEAS_SOLO_TIEMPO, RETRO_LAXO,  # noqa: F401
                                                  TOPE_BARRAS, VIAJES_MIN, _friccion_ticks, _vuelta, lineas_salida, niveles)
from edgelab.research.grilla_generica import Variable

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "ESPEJO-MACRO-10T-TIEMPO"
INDICADORES = ["ESPEJO-MACRO-10T"]
MAX_SEG_IDA = 3600.0                  # 60 min desde A hasta el último extremo nuevo
MAX_SEG_TOTAL = 7200.0                # 120 min para ida + vuelta
VARIABLES = [
    Variable("fraccion", "fi", "grupo", categoria=len(FRACCIONES)),
    Variable("retro_ida", "retro_ida", "le", cortes=(0.20, 0.30, 0.40)),
    Variable("retro_vuelta", "retro_vuelta", "le", cortes=(0.20, 0.30, 0.40)),
    Variable("viajes", "viajes", "ge", cortes=(10.0, 20.0, 40.0), piso=True),
    Variable("min_ida", "min_ida", "le", cortes=(10.0, 30.0, 60.0)),         # duración de la ida en minutos
    Variable("ritmo", "ritmo", "extremos", cuantiles=3),
    Variable("rth", "rth", "eq_any", categoria=2),
]
EJES_ORDINALES = (1, 2, 3, 4)
BASE = {"fraccion": 1, "retro_ida": 0, "retro_vuelta": 0, "viajes": 1, "min_ida": 0, "ritmo": 2, "rth": 2, "ejecución": 0}


@njit(cache=False)
def _candidato_t(C, T, i0, n, lado, retro, f, min_w, min_ida, min_vuelta, max_ida_s, max_total_s):
    """Como `espejo_macro_grilla._candidato`, con los topes en segundos (T = instante de cierre de cada vela)."""
    for j in range(max(0, i0 - min_ida), i0):
        if (lado == 1 and C[j] < C[i0]) or (lado == -1 and C[j] > C[i0]): return -1, 0, 0.0, 0.0, 0.0
    A = C[i0]; ext = A; iext = i0; peor = 0.0
    for k in range(i0 + 1, n):
        if T[k] - T[i0] > max_total_s: return -1, 0, 0.0, 0.0, 0.0
        ck = C[k]
        nuevo = (lado == 1 and ck > ext) or (lado == -1 and ck < ext)
        if nuevo:
            if T[k] - T[i0] > max_ida_s: return -1, 0, 0.0, 0.0, 0.0
            if iext < k - 1 and (ext - A) * lado >= min_w * 0.5:
                if lado == 1:
                    m = C[iext + 1]
                    for j in range(iext + 1, k):
                        if C[j] < m: m = C[j]
                    dip = ext - m
                else:
                    m = C[iext + 1]
                    for j in range(iext + 1, k):
                        if C[j] > m: m = C[j]
                    dip = m - ext
                if dip > retro * (ext - A) * lado: return -1, 0, 0.0, 0.0, 0.0
                if dip > peor: peor = dip
            ext = ck; iext = k
            continue
        W = (ext - A) * lado
        if W < min_w or iext - i0 + 1 < min_ida:
            if (A - ck) * lado > 0: return -1, 0, 0.0, 0.0, 0.0
            continue
        if (ext - ck) * lado < f * W:
            if (A - ck) * lado > 0: return -1, 0, 0.0, 0.0, 0.0
            continue
        if k - iext < min_vuelta: return -1, 0, 0.0, 0.0, 0.0
        rv = _vuelta(C, iext, k, lado)
        if rv > retro: return -1, 0, 0.0, 0.0, 0.0
        return k, iext, W, peor / W, rv
    return -1, 0, 0.0, 0.0, 0.0


@njit(cache=False)
def _detectar_t(C, T, ses, retro, f, min_w, min_ida, min_vuelta, max_ida_s, max_total_s):
    """Causal, como `espejo_macro_grilla._detectar`: vela de confirmación de cada inicio y recorrido en orden de tiempo."""
    n = len(C); out = []
    a = 0
    while a < n:
        b = a
        while b < n and ses[b] == ses[a]: b += 1
        Cs = C[a:b]; Ts = T[a:b]; m = b - a
        K = np.full(m, -1, np.int64); E = np.zeros(m, np.int64); L = np.zeros(m, np.int64)
        Wv = np.zeros(m); RI = np.zeros(m); RV = np.zeros(m)
        for i in range(max(m - min_ida, 0)):
            ku, eu, wu, riu, rvu = _candidato_t(Cs, Ts, i, m, 1, retro, f, min_w, min_ida, min_vuelta, max_ida_s, max_total_s)
            kd, ed, wd, rid, rvd = _candidato_t(Cs, Ts, i, m, -1, retro, f, min_w, min_ida, min_vuelta, max_ida_s, max_total_s)
            if ku >= 0 and (kd < 0 or ku <= kd):
                K[i] = ku; E[i] = eu; L[i] = 1; Wv[i] = wu; RI[i] = riu; RV[i] = rvu
            elif kd >= 0:
                K[i] = kd; E[i] = ed; L[i] = -1; Wv[i] = wd; RI[i] = rid; RV[i] = rvd
        orden = np.argsort(K * (m + 1) + np.arange(m), kind="mergesort")
        ultimo = -1
        for q in range(m):
            i = orden[q]
            if K[i] < 0 or i <= ultimo: continue
            out.append((a + i, a + E[i], a + K[i], L[i], Wv[i], RI[i], RV[i])); ultimo = K[i]
        a = b
    return out


def disparos(ctx) -> pd.DataFrame:
    tick = float(ctx["tick"]); C = np.asarray(ctx["c"], float) / tick; T = np.asarray(ctx["t"], float)
    ses = np.asarray(ctx["ses"], np.int64); fr = _friccion_ticks(ctx); min_w = 2.0 * VIAJES_MIN * fr
    partes = []
    for fi, f in enumerate(FRACCIONES):
        F = _detectar_t(C, T, ses, RETRO_LAXO, f, min_w, P.MIN_IDA, P.MIN_VUELTA, MAX_SEG_IDA, MAX_SEG_TOTAL)
        if not len(F): continue
        F = np.array(F); i0, ie, k = (F[:, j].astype(np.int64) for j in range(3)); lado = F[:, 3].astype(np.int64); W = F[:, 4]
        partes.append(pd.DataFrame(dict(k=k, lado=-lado, fi=fi, retro_ida=F[:, 5], retro_vuelta=F[:, 6], viajes=W / 2.0 / fr,
                                        min_ida=(T[ie] - T[i0]) / 60.0, ritmo=(T[k] - T[ie]) / np.maximum(T[ie] - T[i0], 1.0) / f,
                                        A=C[i0] * tick, B=C[ie] * tick, W=W * tick)))
    cols = ["k", "lado", "fi", "retro_ida", "retro_vuelta", "viajes", "min_ida", "ritmo", "A", "B", "W", "rth", "ses"]
    if not partes: return pd.DataFrame(columns=cols)
    D = pd.concat(partes, ignore_index=True)
    from edgelab.research.regimen_sesion import minuto_ny
    mny = minuto_ny(T[D.k.to_numpy()].astype(np.int64))
    D["rth"] = ((mny >= P.RTH_INI) & (mny < P.RTH_FIN)).astype(np.int64); D["ses"] = ses[D.k.to_numpy()]
    return D.sort_values(["k", "fi"], kind="stable", ignore_index=True)
