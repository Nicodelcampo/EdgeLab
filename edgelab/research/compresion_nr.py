"""COMPRESION-NR (2026-11-03, programa R): compresión de volatilidad intradía tipo Narrow-Range (NR4 de 30 min) y ruptura.

Fuente: Crabel (1990), «Day Trading with Short Term Price Patterns and Opening Range Breakout» (principio de contracción/expansión
de rango NR4/NR7); Andersen y Bollerslev (1997), persistencia y clustering de volatilidad intradía. Cuando el rango realizado de
30 minutos es más estrecho que los tres bloques previos de 30 minutos de la misma sesión y la vela actual cierra rompiendo el canal
de las 15 velas anteriores, la transición de baja a alta volatilidad ofrece asimetría favorable en múltiplos de R.
Diseño: docs/research/programa_r_20261103/DISENO_COMPRESION_NR.md.

Construcción (100% causal):
- En cada sesión, desde la vela 120 de la sesión y dentro de 03:00–14:30 ET (180..870 min NY), se compara el rango de las 30 velas
  [k−29, k] con los tres bloques previos de 30 velas [k−59, k−30], [k−89, k−60] y [k−119, k−90].
- Condición de disparo: R0 <= 1,05 * min(R1, R2, R3) y cierre c[k] fuera del canal previo de 15 velas [k−15, k−1], con enfriamiento
  de 45 velas entre disparos de la misma sesión.
- Variables causales en k: grado de compresión R0 / media(R1, R2, R3), fracción de cuerpo de la vela k y franja horaria (Londres,
  NY mañana, NY tarde).
- Ejecución: entrada en el primer tick siguiente, stop a 1,0x o 1,5x del rango R0 (piso 4 ticks), objetivo amplio a 2,5R o 4,0R
  y tope de 180 barras.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable
from edgelab.research.regimen_sesion import minuto_ny

NOMBRE = "COMPRESION-NR"
INDICADORES = ["COMPRESION-NR"]
M0, M1 = 180, 870
ENFRIAMIENTO = 45
TOPE_BARRAS = 180
PREFLIGHT_T0_S = 1_760_047_200
VARIABLES = [
    Variable("grado_compresion", "ratio_nr", "le", cortes=(0.68, 0.88)),
    Variable("empuje_vela", "empuje", "ge", cortes=(0.45, 0.65)),
    Variable("franja_horaria", "franja", "grupo", categoria=3),
]
EJES_ORDINALES = (0, 1)
EJECUCIONES = [("CAJA", 1.0, 2.5), ("CAJA", 1.0, 4.0), ("CAJA", 1.5, 2.5), ("CAJA", 1.5, 4.0)]
BASE = {"grado_compresion": 1, "empuje_vela": 0, "franja_horaria": 1, "ejecución": 1}
VACIO = ["k", "ses", "lado", "ratio_nr", "empuje", "franja", "r0"]


def disparos(ctx: dict) -> pd.DataFrame:
    o, h, l, c = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c"))
    ses = np.asarray(ctx["ses"], np.int64); m = minuto_ny(np.asarray(ctx["t"], np.int64)); filas = []
    for sg in np.unique(ses):
        idx = np.flatnonzero(ses == sg)
        if len(idx) < 125: continue
        hs, ls, cs, os_, ms = h[idx], l[idx], c[idx], o[idx], m[idx]
        s_hi = pd.Series(hs); s_lo = pd.Series(ls)
        r30 = (s_hi.rolling(30).max() - s_lo.rolling(30).min()).to_numpy()
        hi15 = s_hi.shift(1).rolling(15).max().to_numpy()
        lo15 = s_lo.shift(1).rolling(15).min().to_numpy()
        ult = -10**9
        for p in range(120, len(idx)):
            if p - ult < ENFRIAMIENTO or not (M0 <= ms[p] <= M1): continue
            r0 = r30[p]; r1, r2, r3 = r30[p - 30], r30[p - 60], r30[p - 90]
            if not (r0 > 0 and r1 > 0 and r2 > 0 and r3 > 0): continue
            if r0 > 1.05 * min(r1, r2, r3): continue
            s = 1 if cs[p] > hi15[p] else (-1 if cs[p] < lo15[p] else 0)
            if s == 0: continue
            rk = float(hs[p] - ls[p]); emp = abs(float(cs[p] - os_[p])) / rk if rk > 0 else 0.0
            fr = 0 if ms[p] < 480 else (1 if ms[p] < 690 else 2)
            ult = p
            filas.append((int(idx[p]), int(sg), s, float(r0 / ((r1 + r2 + r3) / 3.0)), emp, fr, float(r0)))
    return pd.DataFrame(filas, columns=VACIO) if filas else pd.DataFrame(columns=VACIO)


def _lote(D, ej, ctx):
    tick = float(ctx["tick"]); k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64); e = np.asarray(ctx["c"], float)[k]
    d = np.maximum(float(ej[1]) * D["r0"].to_numpy(float), 4.0 * tick)
    st = np.where(s == 1, np.floor((e - d) / tick) * tick, np.ceil((e + d) / tick) * tick)
    tp = np.round((e + s * float(ej[2]) * np.abs(e - st)) / tick) * tick
    return k, s, e, st, tp


def niveles(d, ej: tuple, ctx: dict):
    k, s, e, st, tp = _lote(pd.DataFrame([d]), ej, ctx)
    return (int(k[0]), 2, int(s[0]), float(e[0]), float(st[0]), float(tp[0]), 0)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    if not len(D): return np.full((0, 7), np.nan)
    k, s, e, st, tp = _lote(D, ej, ctx)
    return np.column_stack([k, np.full(len(D), 2), s, e, st, tp, np.zeros(len(D))]).astype(float)
