"""COMEX-CIERRE-ORO (2026-11-03, programa R): flujo de liquidación del pit de COMEX (12:30–13:30 ET -> post 13:30 ET).

Fuente: microestructura de liquidación diaria de futuros de metales en CME/COMEX (13:30 ET); Bessembinder y Seguin (1992), JF;
Baur et al. (2016). La ventana de tasación oficial del pit de oro de COMEX cierra a las 13:30 ET: productores, bancos de lingotes y
fondos de opciones concentran órdenes entre las 12:30 y las 13:30 ET. Al terminar la ventana de liquidación a las 13:30 ET, el
precio revierte la presión de tasación (regla 0) o continúa por arrastre de márgenes hacia el cierre electrónico (regla 1).
Diseño: docs/research/programa_r_20261103/DISENO_COMEX_CIERRE_ORO.md.

Construcción (100% causal):
- Ventana de liquidación: (750, 810] minutos NY (12:30–13:30 ET). Decisión al cierre de la vela de las 13:30 ET (m == 810).
- Variables causales en k: regla (0=reversión post-cierre COMEX, 1=continuación), eficiencia del desplazamiento |c_1330 − o_1231| / rango,
  tamaño de la subasta en unidades de ATR14 y eficiencia de Kaufman de 120 velas de la sesión.
- Ejecución: entrada en el primer tick tras las 13:30 ET, stop a 0,75x o 1,25x del rango 12:30–13:30 ET (piso 4 ticks),
  objetivo a 2,5R o 3,5R sin break-even, y salida forzada a las 15:55 ET (955 min NY).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import rango_ruptura as RR
from edgelab.research.grilla_generica import Variable
from edgelab.research.regimen_sesion import er_sesion, minuto_ny
from edgelab.research.zonas_gaps import _atr_causal

NOMBRE = "COMEX-CIERRE-ORO"
INDICADORES = ["COMEX-CIERRE-ORO"]
M_PIT0, M_PIT1, M_SALE = 750, 810, 835
PREFLIGHT_T0_S = 1_760_047_200
EXCLUIR_EVENTOS = dict(antes_min=15, despues_min=15, tipos=("CPI", "NFP_EMPLOYMENT_SITUATION", "FOMC_DECISION"))
VARIABLES = [
    Variable("regla", "regla", "grupo", categoria=2),
    Variable("desplazamiento_pit", "desp_rango", "ge", cortes=(0.35, 0.60)),
    Variable("tamano_subasta", "rango_atr", "extremos", cuantiles=3),
    Variable("eficiencia_sesion", "er120", "ge", cortes=(0.18, 0.32)),
]
EJES_ORDINALES = (1, 3)
EJECUCIONES = [("PIT", 0.75, 2.5), ("PIT", 1.25, 3.5)]
BASE = {"regla": 0, "desplazamiento_pit": 0, "tamano_subasta": 2, "eficiencia_sesion": 0, "ejecución": 0}
VACIO = ["k", "ses", "regla", "lado", "desp_rango", "rango_atr", "er120", "rng_pit"]


def disparos(ctx: dict) -> pd.DataFrame:
    o, h, l, c = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c"))
    ses = np.asarray(ctx["ses"], np.int64); m = minuto_ny(np.asarray(ctx["t"], np.int64))
    atr = _atr_causal(h, l, c); er = er_sesion(c, ses, 120); filas = []
    for sg in np.unique(ses):
        idx = np.flatnonzero(ses == sg); mm = m[idx]
        w_pit = idx[(mm > M_PIT0) & (mm <= M_PIT1)]
        if len(w_pit) < 45 or m[w_pit[-1]] != M_PIT1: continue
        k = int(w_pit[-1]); a = int(w_pit[0])
        r_pit = float(c[k] - o[a]); rng = float(h[w_pit].max() - l[w_pit].min())
        if r_pit == 0.0 or not rng > 0.0 or not atr[k] > 0.0: continue
        desp = abs(r_pit) / rng; ratr = rng / float(atr[k]); d0 = int(np.sign(r_pit))
        for regla, s in ((0, -d0), (1, d0)):
            filas.append((k, int(sg), regla, s, desp, ratr, float(er[k]), rng))
    return pd.DataFrame(filas, columns=VACIO).sort_values(["k", "regla"], kind="stable", ignore_index=True) if filas else pd.DataFrame(columns=VACIO)


def lineas_salida(ctx) -> np.ndarray:
    return RR.lineas_salida(ctx, M_SALE)


def _lote(D, ej, ctx):
    tick = float(ctx["tick"]); k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64); e = np.asarray(ctx["c"], float)[k]
    d = np.maximum(float(ej[1]) * D["rng_pit"].to_numpy(float), 4.0 * tick)
    st = np.where(s == 1, np.floor((e - d) / tick) * tick, np.ceil((e + d) / tick) * tick)
    tp = np.round((e + s * float(ej[2]) * np.abs(e - st)) / tick) * tick
    return np.ones(len(D), bool), k, s, e, st, tp, (s == -1).astype(np.int64)


def niveles(d, ej: tuple, ctx: dict):
    return RR.niveles_con(_lote, d, ej, ctx)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    return RR.niveles_lote_con(_lote, D, ej, ctx)
