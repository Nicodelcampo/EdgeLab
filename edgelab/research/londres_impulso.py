"""LONDRES-IMPULSO (2026-11-03, programa R): ruptura del balance inicial de apertura de Londres (02:00–03:00 ET).

Fuente: Breedon y Ranaldo (2013), «Intraday Patterns in FX Returns and Order Flow», Journal of Money, Credit and Banking;
Andersen y Bollerslev (1998), patrones intradía de liquidez institucional en la transición Asia → Londres. En la primera hora
de Londres (07:00–08:00 UK / 02:00–03:00 ET) la mesa interbancaria europea acumula inventario en una caja de equilibrio;
el primer quiebre con cuerpo firme entre las 03:00 y las 05:30 ET libera flujo direccional antes de la ventana macro de EE.UU.
Diseño: docs/research/programa_r_20261103/DISENO_LONDRES_IMPULSO.md.

Construcción (100% causal):
- Caja de Londres: máximo y mínimo de las velas M1 que cierran en (120, 180] minutos NY (02:00–03:00 ET), exigiendo >= 45 velas.
- Disparo: para cada dirección (largo/corto), el PRIMER cierre M1 fuera de [lo, hi] en (180, 330] (03:00–05:30 ET).
- Variables causales en k: fracción de cuerpo de la vela de ruptura, ancho de la caja en unidades de ATR14 al cierre de la caja,
  y eficiencia de Kaufman de 60 velas de la sesión hasta k.
- Ejecución: entrada en el primer tick de la vela siguiente (limite=2), stop en el punto medio (MID) o borde opuesto (OPUESTO)
  con piso de 4 ticks, objetivo amplio (2,0R, 3,0R o 3,5R) sin break-even, y salida forzada a las 08:25 ET (505 min NY).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import rango_ruptura as RR
from edgelab.research.grilla_generica import Variable
from edgelab.research.regimen_sesion import er_sesion, minuto_ny
from edgelab.research.zonas_gaps import _atr_causal

NOMBRE = "LONDRES-IMPULSO"
INDICADORES = ["LONDRES-IMPULSO"]
M_INI, M_FIN, M_LIM, M_SALE = 120, 180, 330, 505
PREFLIGHT_T0_S = 1_760_047_200
VARIABLES = [
    Variable("cuerpo_ruptura", "cuerpo", "ge", cortes=(0.45, 0.65)),
    Variable("ancho_caja", "ancho_atr", "extremos", cuantiles=3),
    Variable("eficiencia_previa", "er60", "ge", cortes=(0.20, 0.35)),
]
EJES_ORDINALES = (0, 2)
EJECUCIONES = [("MID", 2.0), ("MID", 3.0), ("OPUESTO", 2.0), ("OPUESTO", 3.5)]
BASE = {"cuerpo_ruptura": 0, "ancho_caja": 2, "eficiencia_previa": 0, "ejecución": 1}
VACIO = ["k", "ses", "lado", "hi", "lo", "mid", "cuerpo", "ancho_atr", "er60"]


def disparos(ctx: dict) -> pd.DataFrame:
    o, h, l, c = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c"))
    ses = np.asarray(ctx["ses"], np.int64); m = minuto_ny(np.asarray(ctx["t"], np.int64))
    atr = _atr_causal(h, l, c); er = er_sesion(c, ses, 60); filas = []
    for sg in np.unique(ses):
        idx = np.flatnonzero(ses == sg); mm = m[idx]
        rg = idx[(mm > M_INI) & (mm <= M_FIN)]
        if len(rg) < 45: continue
        hi, lo = float(h[rg].max()), float(l[rg].min()); mid = 0.5 * (hi + lo)
        if not hi > lo: continue
        atr_fin = float(atr[rg[-1]]) if atr[rg[-1]] > 0 else np.nan
        ancho_atr = (hi - lo) / atr_fin if np.isfinite(atr_fin) and atr_fin > 0 else np.nan
        post = idx[(idx > rg[-1]) & (mm > M_FIN) & (mm <= M_LIM)]
        for s in (1, -1):
            fuera = post[c[post] > hi] if s == 1 else post[c[post] < lo]
            if not len(fuera): continue
            k = int(fuera[0]); rk = float(h[k] - l[k])
            cuerpo = abs(float(c[k] - o[k])) / rk if rk > 0 else 0.0
            filas.append((k, int(sg), s, hi, lo, mid, cuerpo, float(ancho_atr), float(er[k])))
    return pd.DataFrame(filas, columns=VACIO).sort_values("k", kind="stable", ignore_index=True) if filas else pd.DataFrame(columns=VACIO)


def lineas_salida(ctx) -> np.ndarray:
    return RR.lineas_salida(ctx, M_SALE)


def _lote(D, ej, ctx):
    tick = float(ctx["tick"]); k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64); e = np.asarray(ctx["c"], float)[k]
    ref = D["mid"].to_numpy(float) if ej[0] == "MID" else np.where(s == 1, D["lo"].to_numpy(float), D["hi"].to_numpy(float))
    d = np.maximum(np.abs(e - ref) + tick, 4.0 * tick)
    st = np.where(s == 1, np.floor((e - d) / tick) * tick, np.ceil((e + d) / tick) * tick)
    tp = np.round((e + s * float(ej[1]) * np.abs(e - st)) / tick) * tick
    return np.ones(len(D), bool), k, s, e, st, tp, (s == -1).astype(np.int64)


def niveles(d, ej: tuple, ctx: dict):
    return RR.niveles_con(_lote, d, ej, ctx)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    return RR.niveles_lote_con(_lote, D, ej, ctx)
