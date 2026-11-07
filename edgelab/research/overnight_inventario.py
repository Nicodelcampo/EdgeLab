"""OVERNIGHT-INVENTARIO (2026-11-03, programa R): desequilibrio de inventario Globex (18:00–09:29 ET) en la apertura RTH (09:30 ET).

Fuente: Lou, Polk y Skouras (2019), «A Tug of War: Overnight vs. Intraday Expected Returns», Journal of Financial Economics;
Dalton, Jones y Dalton (1990), «Mind Over Markets» (corrección de inventario overnight en la subasta de apertura RTH).
Cuando la sesión electrónica overnight (18:00–09:29 ET) acumula un inventario unilateral fuera de su punto medio, la entrada
de liquidez institucional a las 09:30 ET fuerza o bien la liquidación hacia el equilibrio overnight (regla 0) o bien la absorción
y continuación direccional (regla 1). Distinto de GAP-RTH (que mide el salto respecto al cierre de las 15:59 del día previo).
Diseño: docs/research/programa_r_20261103/DISENO_OVERNIGHT_INVENTARIO.md.

Construcción (100% causal):
- Tramo overnight de la misma sesión CME: velas antes de la apertura de las 09:30 ET (rel_ny en (0, 929], es decir 18:00–09:29 ET).
- Decisión al cierre de la vela de las 09:30 ET (m == 570, rel == 930).
- Variables causales en k: regla (0=liquidación hacia el punto medio overnight, 1=continuación del inventario), desequilibrio neto
  |c_0929 − o_1800| / rango_on, fracción de velas overnight del mismo lado del punto medio y empuje de la vela 09:30 / ATR14.
- Ejecución: entrada en el primer tick tras las 09:30 ET, stop a 0,35x o 0,50x del rango overnight (piso 4 ticks), objetivo a
  2,5R o 3,5R sin break-even, y salida forzada a las 11:30 ET (690 min NY).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import rango_ruptura as RR
from edgelab.research.grilla_generica import Variable
from edgelab.research.regimen_sesion import minuto_ny
from edgelab.research.zonas_gaps import _atr_causal

NOMBRE = "OVERNIGHT-INVENTARIO"
INDICADORES = ["OVERNIGHT-INVENTARIO"]
REL_FIN_ON, M_DEC, M_SALE = 929, 570, 690
PREFLIGHT_T0_S = 1_760_047_200
VARIABLES = [
    Variable("regla", "regla", "grupo", categoria=2),
    Variable("desequilibrio_on", "imb_on", "ge", cortes=(0.30, 0.55)),
    Variable("tiempo_en_extremo", "frac_ext", "ge", cortes=(0.52, 0.65)),
    Variable("apertura_rth", "empuje_930", "extremos", cuantiles=3),
]
EJES_ORDINALES = (1, 2)
EJECUCIONES = [("ON", 0.35, 2.5), ("ON", 0.50, 3.5)]
BASE = {"regla": 0, "desequilibrio_on": 0, "tiempo_en_extremo": 0, "apertura_rth": 2, "ejecución": 0}
VACIO = ["k", "ses", "regla", "lado", "imb_on", "frac_ext", "empuje_930", "rng_on"]


def disparos(ctx: dict) -> pd.DataFrame:
    o, h, l, c = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c"))
    ses = np.asarray(ctx["ses"], np.int64); m = minuto_ny(np.asarray(ctx["t"], np.int64)); rel = (m - 1080) % 1440
    atr = _atr_causal(h, l, c); filas = []
    for sg in np.unique(ses):
        idx = np.flatnonzero(ses == sg); rr = rel[idx]; mm = m[idx]
        on = idx[(rr > 0) & (rr <= REL_FIN_ON)]
        dec = idx[(mm == M_DEC) & (idx > (on[-1] if len(on) else -1))]
        if len(on) < 120 or not len(dec): continue
        k = int(dec[0]); hi_on, lo_on = float(h[on].max()), float(l[on].min()); rng_on = hi_on - lo_on
        if not rng_on > 0.0 or not atr[k] > 0.0: continue
        r_on = float(c[on[-1]] - o[on[0]])
        if r_on == 0.0: continue
        mid_on = 0.5 * (hi_on + lo_on); dir_on = int(np.sign(r_on))
        frac = float(np.mean(c[on] > mid_on)) if dir_on == 1 else float(np.mean(c[on] < mid_on))
        emp930 = float(h[k] - l[k]) / float(atr[k])
        for regla, s in ((0, -dir_on), (1, dir_on)):
            filas.append((k, int(sg), regla, s, abs(r_on) / rng_on, frac, emp930, rng_on))
    return pd.DataFrame(filas, columns=VACIO).sort_values(["k", "regla"], kind="stable", ignore_index=True) if filas else pd.DataFrame(columns=VACIO)


def lineas_salida(ctx) -> np.ndarray:
    return RR.lineas_salida(ctx, M_SALE)


def _lote(D, ej, ctx):
    tick = float(ctx["tick"]); k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64); e = np.asarray(ctx["c"], float)[k]
    d = np.maximum(float(ej[1]) * D["rng_on"].to_numpy(float), 4.0 * tick)
    st = np.where(s == 1, np.floor((e - d) / tick) * tick, np.ceil((e + d) / tick) * tick)
    tp = np.round((e + s * float(ej[2]) * np.abs(e - st)) / tick) * tick
    return np.ones(len(D), bool), k, s, e, st, tp, (s == -1).astype(np.int64)


def niveles(d, ej: tuple, ctx: dict):
    return RR.niveles_con(_lote, d, ej, ctx)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    return RR.niveles_lote_con(_lote, D, ej, ctx)
