"""IMPULSO-POST-MACRO (2026-11-03, programa R): digestión post-macro (08:35–09:00 ET) tras la ventana de anuncios de las 08:30 ET.

Fuente: Andersen, Bollerslev, Diebold y Vega (2003), «Micro Effects of Macro Announcements: Real-Time Price Discovery in Foreign
Exchange», American Economic Review; Ederington y Lee (1993), «How Markets Process Information: News Releases and Volatility», JF.
El proceso de descubrimiento de precios tras la ventana macro de las 08:30 ET ocurre en dos etapas: los primeros 5 minutos
(08:30–08:35 ET) son ajuste mecánico de inventario y ensanchamiento de spreads; los 25 minutos siguientes (08:35–09:00 ET) forman
la caja de digestión donde el flujo institucional informado re-acumula posición. La ruptura de la caja 08:35–09:00 ET entre las
09:00 y las 10:30 ET captura la segunda etapa direccional hasta el mediodía (12:00 ET).
Diseño: docs/research/programa_r_20261103/DISENO_IMPULSO_POST_MACRO.md.

Construcción (100% causal):
- Ventana del choque inicial: (505, 515] minutos NY (08:25–08:35 ET). Caja de digestión: (515, 540] (08:35–09:00 ET, >= 20 velas).
- Disparo: para cada lado (largo/corto), el PRIMER cierre M1 fuera de [lo_dig, hi_dig] en (540, 630] (09:00–10:30 ET).
- Variables causales en k: intensidad del choque 08:30 (rango 08:25–08:35 / ATR14), fracción de cuerpo de la vela de ruptura
  y eficiencia de Kaufman de 25 velas al momento del quiebre.
- Ejecución: entrada en el primer tick siguiente, stop en el punto medio (MID) o borde opuesto (OPUESTO) con piso de 4 ticks,
  objetivo amplio a 2,0R, 3,0R o 3,5R, y salida forzada a las 12:00 ET (720 min NY).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import rango_ruptura as RR
from edgelab.research.londres_impulso import _lote  # noqa: F401
from edgelab.research.grilla_generica import Variable
from edgelab.research.eventos import TIPOS_TIER1, cerca
from edgelab.research.eventos_datos import EVENTOS
from edgelab.research.regimen_sesion import er_sesion, minuto_ny
from edgelab.research.zonas_gaps import _atr_causal

NOMBRE = "IMPULSO-POST-MACRO"
INDICADORES = ["IMPULSO-POST-MACRO"]
M_CH0, M_INI, M_FIN, M_LIM, M_SALE = 505, 515, 540, 630, 720
# 2026-11-03 (revisión de Gemini; Nico 2026-10-25 «no operar durante noticias»): sin entradas a ±5 min de un dato tier1 y salida
# forzada antes de cada dato (`RR.lineas_salida_noticias`).
EXCLUIR_EVENTOS = dict(antes_min=5, despues_min=5, tipos=TIPOS_TIER1)
# 2026-11-03 (revisión de Gemini): la familia es «después de un dato macro», pero la ventana de 08:30 corría también los días sin dato.
# Ahora sólo dispara las sesiones con un dato programado (cualquier impacto del calendario canónico) a las 08:30 ET.
TIPOS_DATO = tuple(sorted({k for _, k, _ in EVENTOS}))
PREFLIGHT_T0_S = 1_760_047_200
VARIABLES = [
    Variable("choque_0830", "choque_atr", "extremos", cuantiles=3),
    Variable("cuerpo_ruptura", "cuerpo", "ge", cortes=(0.45, 0.65)),
    Variable("eficiencia_digestion", "er25", "ge", cortes=(0.20, 0.38)),
]
EJES_ORDINALES = (1, 2)
EJECUCIONES = [("MID", 2.0), ("MID", 3.5), ("OPUESTO", 2.0), ("OPUESTO", 3.0)]
BASE = {"choque_0830": 2, "cuerpo_ruptura": 0, "eficiencia_digestion": 0, "ejecución": 1}
VACIO = ["k", "ses", "lado", "hi", "lo", "mid", "choque_atr", "cuerpo", "er25"]


def disparos(ctx: dict) -> pd.DataFrame:
    o, h, l, c = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c"))
    ses = np.asarray(ctx["ses"], np.int64); m = minuto_ny(np.asarray(ctx["t"], np.int64))
    atr = _atr_causal(h, l, c); er = er_sesion(c, ses, 25); filas = []
    dato = cerca(np.asarray(ctx["t"], np.int64), 0, 1, TIPOS_DATO)          # vela que cierra en [dato, dato + 1 min]: conocido de antemano
    for sg in np.unique(ses):
        idx = np.flatnonzero(ses == sg); mm = m[idx]
        ch = idx[(mm > M_CH0) & (mm <= M_INI)]
        dig = idx[(mm > M_INI) & (mm <= M_FIN)]
        if len(ch) < 6 or len(dig) < 20 or not dato[ch].any(): continue
        hi, lo = float(h[dig].max()), float(l[dig].min()); mid = 0.5 * (hi + lo)
        if not hi > lo or not atr[dig[-1]] > 0: continue
        choque = float(h[ch].max() - l[ch].min()) / float(atr[dig[-1]])
        post = idx[(idx > dig[-1]) & (mm > M_FIN) & (mm <= M_LIM)]
        for s in (1, -1):
            fuera = post[c[post] > hi] if s == 1 else post[c[post] < lo]
            if not len(fuera): continue
            k = int(fuera[0]); rk = float(h[k] - l[k])
            cuerpo = abs(float(c[k] - o[k])) / rk if rk > 0 else 0.0
            filas.append((k, int(sg), s, hi, lo, mid, choque, cuerpo, float(er[k])))
    return pd.DataFrame(filas, columns=VACIO).sort_values("k", kind="stable", ignore_index=True) if filas else pd.DataFrame(columns=VACIO)


def lineas_salida(ctx) -> np.ndarray:
    return RR.lineas_salida_noticias(ctx, M_SALE)


def niveles(d, ej: tuple, ctx: dict):
    return RR.niveles_con(_lote, d, ej, ctx)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    return RR.niveles_lote_con(_lote, D, ej, ctx)
