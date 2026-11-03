"""ESTRUCTURA-HHLL (2026-11-03, programa R): continuación en retroceso sobre estructura causal de pivotes (HH+HL / LL+LH).

Fuente: Lo, Mamaysky y Wang (2000), «Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and
Empirical Implementation», Journal of Finance. A diferencia de TAU-TENDENCIA (que entra por ruptura del último pivote y sale por
cruce de línea τ), ESTRUCTURA-HHLL entra en el RETROCESO (pullback) hacia la media exponencial de 60 minutos de la sesión cuando
la estructura de pivotes de orden p=5 confirmados es alcista (HH y HL) o bajista (LL y LH) y la vela k retoma la dirección con
cierre firme. El riesgo inicial se ancla detrás del pivote de soporte/resistencia confirmado (stop estructural, como validó el
Atlas en R). Diseño: docs/research/programa_r_20261103/DISENO_ESTRUCTURA_HHLL.md.

Construcción (100% causal):
- Un pivote alto en j de orden P=5 se confirma recién en j+P (máximo estricto de h[j−P : j+P+1]); análogo para pivote bajo.
- En la vela k (03:00–14:30 ET), con los dos últimos pivotes altos confirmados (h1, h2) y los dos últimos bajos confirmados (l1, l2)
  de la sesión: estructura alcista si h2 > h1 y l2 > l1; bajista si h2 < h1 y l2 < l1.
- Disparo en k si el precio retrocedió hacia la EMA60 de la sesión (|c[k] − ema60[k]| <= 1,2 * ATR14), se mantiene por encima de l2
  (o debajo de h2 en cortos) y cierra retomando a favor de la estructura, con enfriamiento de 35 velas por sesión.
- Ejecución: stop detrás del pivote estructural l2/h2 (multiplicador 1,0x o 1,4x de la distancia al pivote, piso 4 ticks),
  objetivo amplio a 2,0R, 2,5R, 3,5R o 4,0R, y tope de 180 barras.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable
from edgelab.research.regimen_sesion import minuto_ny
from edgelab.research.zonas_gaps import _atr_causal

NOMBRE = "ESTRUCTURA-HHLL"
INDICADORES = ["ESTRUCTURA-HHLL"]
ORDEN_P = 5
M0, M1 = 180, 870
ENFRIAMIENTO = 35
TOPE_BARRAS = 180
PREFLIGHT_T0_S = 1_760_047_200
VARIABLES = [
    Variable("pendiente_estructura", "pend_atr", "ge", cortes=(0.50, 1.10)),
    Variable("profundidad_pullback", "prof_ret", "extremos", cuantiles=3),
    Variable("vela_retoma", "cuerpo", "ge", cortes=(0.45, 0.65)),
]
EJES_ORDINALES = (0, 2)
EJECUCIONES = [("PIVOTE", 1.0, 2.0), ("PIVOTE", 1.0, 3.5), ("PIVOTE", 1.4, 2.5), ("PIVOTE", 1.4, 4.0)]
BASE = {"pendiente_estructura": 0, "profundidad_pullback": 2, "vela_retoma": 0, "ejecución": 1}
VACIO = ["k", "ses", "lado", "pend_atr", "prof_ret", "cuerpo", "dist_piv"]


def disparos(ctx: dict) -> pd.DataFrame:
    o, h, l, c = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c"))
    ses = np.asarray(ctx["ses"], np.int64); m = minuto_ny(np.asarray(ctx["t"], np.int64))
    atr = _atr_causal(h, l, c); P = ORDEN_P; filas = []
    for sg in np.unique(ses):
        idx = np.flatnonzero(ses == sg)
        if len(idx) < 80: continue
        hs, ls, cs, os_, ms, atrs = h[idx], l[idx], c[idx], o[idx], m[idx], atr[idx]
        ema = pd.Series(cs).ewm(span=60, adjust=False).mean().to_numpy()
        p_hi = []; p_lo = []; ult = -10**9
        for p in range(2 * P + 1, len(idx)):
            cand = p - P
            if hs[cand] == hs[cand - P:p + 1].max(): p_hi.append(float(hs[cand]))
            if ls[cand] == ls[cand - P:p + 1].min(): p_lo.append(float(ls[cand]))
            if p - ult < ENFRIAMIENTO or not (M0 <= ms[p] <= M1) or len(p_hi) < 2 or len(p_lo) < 2: continue
            ak = float(atrs[p]); rk = float(hs[p] - ls[p])
            if not (ak > 0 and rk > 0): continue
            h1, h2 = p_hi[-2], p_hi[-1]; l1, l2 = p_lo[-2], p_lo[-1]
            s = 1 if (h2 > h1 and l2 > l1 and cs[p] > l2 and cs[p] > os_[p]) else (-1 if (h2 < h1 and l2 < l1 and cs[p] < h2 and cs[p] < os_[p]) else 0)
            if s == 0 or abs(float(cs[p] - ema[p])) > 1.2 * ak: continue
            imp_leg = max(h2 - l2, ak) if s == 1 else max(h2 - l2, ak)
            prof = (h2 - float(cs[p])) / imp_leg if s == 1 else (float(cs[p]) - l2) / imp_leg
            if prof <= 0.0 or prof >= 1.0: continue
            pend = (abs(h2 - h1) + abs(l2 - l1)) / (2.0 * ak)
            dist_piv = float(cs[p] - l2) if s == 1 else float(h2 - cs[p])
            ult = p
            filas.append((int(idx[p]), int(sg), s, float(pend), float(prof), abs(float(cs[p] - os_[p])) / rk, dist_piv))
    return pd.DataFrame(filas, columns=VACIO) if filas else pd.DataFrame(columns=VACIO)


def _lote(D, ej, ctx):
    tick = float(ctx["tick"]); k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64); e = np.asarray(ctx["c"], float)[k]
    d = np.maximum(float(ej[1]) * D["dist_piv"].to_numpy(float) + tick, 4.0 * tick)
    st = np.where(s == 1, np.floor((e - d) / tick) * tick, np.ceil((e + d) / tick) * tick)
    return k, s, e, st, np.round((e + s * float(ej[2]) * np.abs(e - st)) / tick) * tick


def niveles(d, ej: tuple, ctx: dict):
    k, s, e, st, tp = _lote(pd.DataFrame([d]), ej, ctx)
    return (int(k[0]), 2, int(s[0]), float(e[0]), float(st[0]), float(tp[0]), 0)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    if not len(D): return np.full((0, 7), np.nan)
    k, s, e, st, tp = _lote(D, ej, ctx)
    return np.column_stack([k, np.full(len(D), 2), s, e, st, tp, np.zeros(len(D))]).astype(float)
