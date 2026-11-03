"""TOKIO-APERTURA-FX (2026-11-03, programa R): balance de apertura de Tokio y fijación bancaria (19:00–20:00 ET).

Fuente: Ito y Yamada (2017), «Was the Tokyo Foreign Exchange Fix Manipulated?», Journal of Futures Markets;
microestructura del Nakane Fix japonés (09:55 JST = 19:55 ET invierno / 20:55 ET verano). Durante la primera hora activa de
Tokio (19:00–20:00 ET) los bancos comerciales japoneses y las mesas de lingotes de Asia concentran órdenes corporativas;
el primer quiebre fuera del balance 19:00–20:00 ET entre las 20:00 y las 23:30 ET marca el flujo asiático real antes de la
pre-apertura europea (01:55 ET). Distinto de MODELO-ASIA (que usa filtro de 100–300 pts de NQ y EMA20 M5 hasta NY).
Diseño: docs/research/programa_r_20261103/DISENO_TOKIO_APERTURA_FX.md.

Construcción (100% causal):
- Caja de Tokio: velas con `rel = (minuto_ny - 1080) % 1440` en (60, 120] (19:00–20:00 ET), exigiendo >= 45 velas.
- Disparo: para cada lado (largo/corto), el PRIMER cierre M1 fuera de [lo, hi] con rel en (120, 330] (20:00–23:30 ET).
- Variables causales en k: fracción de cuerpo de la vela de ruptura, volumen relativo respecto a las 30 velas previas y
  ancho de la caja en unidades de ATR14.
- Ejecución: entrada en el primer tick siguiente, stop en el punto medio (MID) o borde opuesto (OPUESTO) con piso de 4 ticks,
  objetivo amplio a 2,0R, 3,0R o 3,5R sin break-even, y salida forzada a las 01:55 ET (115 min NY).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import rango_ruptura as RR
from edgelab.research.londres_impulso import _lote  # noqa: F401
from edgelab.research.grilla_generica import Variable
from edgelab.research.regimen_sesion import minuto_ny
from edgelab.research.zonas_gaps import _atr_causal

NOMBRE = "TOKIO-APERTURA-FX"
INDICADORES = ["TOKIO-APERTURA-FX"]
M_JST_INI, M_JST_FIN, M_JST_LIM, M_SALE = 540, 600, 810, 115
PREFLIGHT_T0_S = 1_760_047_200
EXCLUIR_EVENTOS = dict(antes_min=15, despues_min=15, tipos=("CPI", "NFP_EMPLOYMENT_SITUATION", "FOMC_DECISION"))
VARIABLES = [
    Variable("cuerpo_ruptura", "cuerpo", "ge", cortes=(0.45, 0.65)),
    Variable("volumen_rel", "rvol", "ge", cortes=(1.0, 1.25)),
    Variable("ancho_tokio", "ancho_atr", "extremos", cuantiles=3),
]
EJES_ORDINALES = (0, 1)
EJECUCIONES = [("MID", 2.0), ("MID", 3.5), ("OPUESTO", 2.0), ("OPUESTO", 3.0)]
BASE = {"cuerpo_ruptura": 0, "volumen_rel": 0, "ancho_tokio": 2, "ejecución": 1}
VACIO = ["k", "ses", "lado", "hi", "lo", "mid", "cuerpo", "rvol", "ancho_atr"]


def disparos(ctx: dict) -> pd.DataFrame:
    o, h, l, c, v = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c", "v"))
    t_arr = np.asarray(ctx["t"], np.int64); ses = np.asarray(ctx["ses"], np.int64)
    m_jst = ((t_arr + 9 * 3600) % 86400) // 60
    atr = _atr_causal(h, l, c); filas = []
    for sg in np.unique(ses):
        idx = np.flatnonzero(ses == sg); mj = m_jst[idx]
        rg = idx[(mj > M_JST_INI) & (mj <= M_JST_FIN)]
        if len(rg) < 45: continue
        hi, lo = float(h[rg].max()), float(l[rg].min()); mid = 0.5 * (hi + lo)
        if not hi > lo or not atr[rg[-1]] > 0: continue
        ancho_atr = (hi - lo) / float(atr[rg[-1]])
        post = idx[(idx > rg[-1]) & (mj > M_JST_FIN) & (mj <= M_JST_LIM)]
        for s in (1, -1):
            fuera = post[c[post] > hi] if s == 1 else post[c[post] < lo]
            if not len(fuera): continue
            k = int(fuera[0]); rk = float(h[k] - l[k])
            cuerpo = abs(float(c[k] - o[k])) / rk if rk > 0 else 0.0
            w0 = max(int(idx[0]), k - 30); vm = float(v[w0:k].mean()) if k - w0 >= 10 else np.nan
            rvol = float(v[k]) / vm if np.isfinite(vm) and vm > 0 else np.nan
            filas.append((k, int(sg), s, hi, lo, mid, cuerpo, rvol, float(ancho_atr)))
    return pd.DataFrame(filas, columns=VACIO).sort_values("k", kind="stable", ignore_index=True) if filas else pd.DataFrame(columns=VACIO)


def lineas_salida(ctx) -> np.ndarray:
    return RR.lineas_salida(ctx, M_SALE)


def niveles(d, ej: tuple, ctx: dict):
    return RR.niveles_con(_lote, d, ej, ctx)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    return RR.niveles_lote_con(_lote, D, ej, ctx)
