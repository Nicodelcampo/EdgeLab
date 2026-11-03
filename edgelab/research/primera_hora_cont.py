"""PRIMERA-HORA-CONT (2026-11-03, programa R): continuación del Initial Balance de primera hora RTH (09:30–10:30 ET).

Fuente: Steidlmayer y Koy (1986), «Markets & Market Logic» (CBOT Market Profile Initial Balance de 60 minutos);
Bogousslavsky (2016), «Infrequent Rebalancing, Return Autocorrelation, and Seasonality», JF; Gao et al. (2018), JFE.
La primera hora regular (09:30–10:30 ET) absorbe las órdenes institucionales de apertura y define el Initial Balance (IB).
El primer cierre M1 fuera del IB entre las 10:30 y las 12:30 ET refleja continuación del flujo de ejecución TWAP/VWAP
institucional con tenencia amplia hacia el cierre RTH (15:55 ET). Diseño: docs/research/programa_r_20261103/DISENO_PRIMERA_HORA_CONT.md.

Construcción (100% causal):
- Initial Balance (IB): máximo y mínimo de las velas M1 que cierran en (570, 630] minutos NY (09:30–10:30 ET), exigiendo >= 45 velas.
- Disparo: para cada dirección (largo/corto), el PRIMER cierre M1 fuera de [lo_ib, hi_ib] en (630, 750] (10:30–12:30 ET).
- Variables causales en k: asimetría direccional de la primera hora |c_1030 − o_0931| / (hi_ib − lo_ib), ancho del IB en ATR14
  y volumen relativo de la vela de ruptura frente a las 30 velas previas.
- Ejecución: entrada en el primer tick de la vela siguiente, stop a 1/3 (TERCIO) o 1/2 (MITAD) del ancho del IB (piso 4 ticks),
  objetivo a 2,0R, 2,5R, 3,5R o 4,0R sin break-even, y salida forzada a las 15:55 ET (955 min NY).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import rango_ruptura as RR
from edgelab.research.grilla_generica import Variable
from edgelab.research.regimen_sesion import minuto_ny
from edgelab.research.zonas_gaps import _atr_causal

NOMBRE = "PRIMERA-HORA-CONT"
INDICADORES = ["PRIMERA-HORA-CONT"]
M_INI, M_FIN, M_LIM, M_SALE = 570, 630, 750, 955
PREFLIGHT_T0_S = 1_760_047_200
VARIABLES = [
    Variable("asim_ib", "asim", "ge", cortes=(0.30, 0.55)),
    Variable("ancho_ib", "ib_atr", "extremos", cuantiles=3),
    Variable("volumen_quiebre", "rvol", "ge", cortes=(1.0, 1.25)),
]
EJES_ORDINALES = (0, 2)
EJECUCIONES = [("TERCIO", 2.5), ("TERCIO", 4.0), ("MITAD", 2.0), ("MITAD", 3.5)]
BASE = {"asim_ib": 0, "ancho_ib": 2, "volumen_quiebre": 0, "ejecución": 1}
VACIO = ["k", "ses", "lado", "hi", "lo", "ancho", "asim", "ib_atr", "rvol"]


def disparos(ctx: dict) -> pd.DataFrame:
    o, h, l, c, v = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c", "v"))
    ses = np.asarray(ctx["ses"], np.int64); m = minuto_ny(np.asarray(ctx["t"], np.int64))
    atr = _atr_causal(h, l, c); filas = []
    for sg in np.unique(ses):
        idx = np.flatnonzero(ses == sg); mm = m[idx]
        ib = idx[(mm > M_INI) & (mm <= M_FIN)]
        if len(ib) < 45: continue
        hi, lo = float(h[ib].max()), float(l[ib].min()); ancho = hi - lo
        if not ancho > 0.0: continue
        asim = abs(float(c[ib[-1]] - o[ib[0]])) / ancho
        ib_atr = ancho / float(atr[ib[-1]]) if atr[ib[-1]] > 0 else np.nan
        post = idx[(idx > ib[-1]) & (mm > M_FIN) & (mm <= M_LIM)]
        for s in (1, -1):
            fuera = post[c[post] > hi] if s == 1 else post[c[post] < lo]
            if not len(fuera): continue
            k = int(fuera[0])
            w0 = max(int(idx[0]), k - 30); vm = float(v[w0:k].mean()) if k - w0 >= 10 else np.nan
            rvol = float(v[k]) / vm if np.isfinite(vm) and vm > 0 else np.nan
            filas.append((k, int(sg), s, hi, lo, ancho, asim, float(ib_atr), rvol))
    return pd.DataFrame(filas, columns=VACIO).sort_values("k", kind="stable", ignore_index=True) if filas else pd.DataFrame(columns=VACIO)


def lineas_salida(ctx) -> np.ndarray:
    return RR.lineas_salida(ctx, M_SALE)


def _lote(D, ej, ctx):
    tick = float(ctx["tick"]); k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64); e = np.asarray(ctx["c"], float)[k]
    frac = 0.3333333333333333 if ej[0] == "TERCIO" else 0.5
    d = np.maximum(frac * D["ancho"].to_numpy(float), 4.0 * tick)
    st = np.where(s == 1, np.floor((e - d) / tick) * tick, np.ceil((e + d) / tick) * tick)
    tp = np.round((e + s * float(ej[1]) * np.abs(e - st)) / tick) * tick
    return np.ones(len(D), bool), k, s, e, st, tp, (s == -1).astype(np.int64)


def niveles(d, ej: tuple, ctx: dict):
    return RR.niveles_con(_lote, d, ej, ctx)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    return RR.niveles_lote_con(_lote, D, ej, ctx)
