"""WM-FIXING (2026-11-03, programa R): flujo institucional del WMR 4:00 PM London Fix (10:30–11:00 ET -> reacción a las 11:00 ET).

Fuente: Melvin y Prins (2015), «Equity Hedging and Exchange Rates at the London 4 p.m. Fix», Journal of Financial Markets;
Evans (2018), «FX Fixings», Journal of Finance; Ito y Yamada (2017). Los gestores globales de renta fija y variable ejecutan
rebalanceos de divisas y oro en la ventana hacia las 16:00 de Londres (11:00 ET). La presión acumulada entre 10:30 y 11:00 ET
genera sobrerreacción transitoria por falta de contraparte (regla 0: reversión post-Fix) o continuación cuando el flujo inicia
el tramo de media mañana (regla 1: continuación post-Fix). Diseño: docs/research/programa_r_20261103/DISENO_WM_FIXING.md.

Construcción (100% causal):
- Ventana pre-Fix: (630, 660] minutos NY (10:30–11:00 ET). Decisión al cierre de la vela de las 11:00 ET (m == 660).
- Variables causales en k: regla (0=reversión del impulso pre-Fix, 1=continuación), impulso |c_1100 − o_1031| / ATR14,
  participación de volumen de la media hora pre-Fix frente a la hora previa (09:30–10:30 ET) y régimen de volatilidad rv_relativa.
- Ejecución: entrada en el primer tick tras las 11:00 ET, stop a 1,0x o 1,5x del rango 10:30–11:00 ET (piso 4 ticks),
  objetivo a 2,5R o 3,5R sin break-even, y salida forzada a las 12:30 ET (750 min NY).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import rango_ruptura as RR
from edgelab.research.grilla_generica import Variable
from edgelab.research.oro_almuerzo_ruptura import _offset_madrid_segundos_nb
from edgelab.research.regimen_sesion import minuto_ny, rv_relativa
from edgelab.research.zonas_gaps import _atr_causal

NOMBRE = "WM-FIXING"
INDICADORES = ["WM-FIXING"]
M_PRE0_UK, M_INI_UK, M_FIX_UK, M_SALE = 870, 930, 960, 750
PREFLIGHT_T0_S = 1_760_047_200
EXCLUIR_EVENTOS = dict(antes_min=15, despues_min=15, tipos=("CPI", "NFP_EMPLOYMENT_SITUATION", "FOMC_DECISION"))
VARIABLES = [
    Variable("regla", "regla", "grupo", categoria=2),
    Variable("impulso_fix", "imp_atr", "ge", cortes=(0.75, 1.35)),
    Variable("volumen_fix", "v_ratio", "ge", cortes=(0.95, 1.15)),
    Variable("regimen_vol", "rv_rel", "extremos", cuantiles=3),
]
EJES_ORDINALES = (1, 2)
EJECUCIONES = [("RANGO", 1.0, 2.5), ("RANGO", 1.5, 3.5)]
BASE = {"regla": 0, "impulso_fix": 0, "volumen_fix": 0, "regimen_vol": 2, "ejecución": 0}
VACIO = ["k", "ses", "regla", "lado", "imp_atr", "v_ratio", "rv_rel", "rango_fix"]


def disparos(ctx: dict) -> pd.DataFrame:
    o, h, l, c, v = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c", "v"))
    t_arr = np.asarray(ctx["t"], np.int64); ses = np.asarray(ctx["ses"], np.int64)
    m_uk = np.array([((int(ts) + _offset_madrid_segundos_nb(int(ts)) - 3600) % 86400) // 60 for ts in t_arr], dtype=np.int64)
    atr = _atr_causal(h, l, c); rv = rv_relativa(c, ses, 30, 390); filas = []
    for sg in np.unique(ses):
        idx = np.flatnonzero(ses == sg); mm = m_uk[idx]
        w_fix = idx[(mm > M_INI_UK) & (mm <= M_FIX_UK)]
        w_prev = idx[(mm > M_PRE0_UK) & (mm <= M_INI_UK)]
        if len(w_fix) < 20 or len(w_prev) < 30 or m_uk[w_fix[-1]] != M_FIX_UK: continue
        k = int(w_fix[-1]); a = int(w_fix[0])
        if k <= a: continue
        r_fix = float(c[k] - o[a]); rng_fix = float(h[w_fix].max() - l[w_fix].min())
        if r_fix == 0.0 or not rng_fix > 0.0 or not atr[k] > 0.0: continue
        v_prev = float(v[w_prev].mean()); v_fx = float(v[w_fix].mean())
        vr = v_fx / v_prev if v_prev > 0 else np.nan
        imp = abs(r_fix) / float(atr[k]); dir_imp = int(np.sign(r_fix))
        for regla, s in ((0, -dir_imp), (1, dir_imp)):
            filas.append((k, int(sg), regla, s, imp, vr, float(rv[k]), rng_fix))
    return pd.DataFrame(filas, columns=VACIO).sort_values(["k", "regla"], kind="stable", ignore_index=True) if filas else pd.DataFrame(columns=VACIO)


def lineas_salida(ctx) -> np.ndarray:
    return RR.lineas_salida(ctx, M_SALE)


def _lote(D, ej, ctx):
    tick = float(ctx["tick"]); k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64); e = np.asarray(ctx["c"], float)[k]
    d = np.maximum(float(ej[1]) * D["rango_fix"].to_numpy(float), 4.0 * tick)
    st = np.where(s == 1, np.floor((e - d) / tick) * tick, np.ceil((e + d) / tick) * tick)
    tp = np.round((e + s * float(ej[2]) * np.abs(e - st)) / tick) * tick
    return np.ones(len(D), bool), k, s, e, st, tp, (s == -1).astype(np.int64)


def niveles(d, ej: tuple, ctx: dict):
    return RR.niveles_con(_lote, d, ej, ctx)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    return RR.niveles_lote_con(_lote, D, ej, ctx)
