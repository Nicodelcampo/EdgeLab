"""APERTURA-EUROPA-ORO (2026-11-03, programa R): rango pre-mercado de lingotes Zurich/Londres (02:00–03:30 ET) hacia NY.

Fuente: Caminschi y Heaney (2014), «Fixing a Leaky Fix: Short-Term Market Reactions to the London PM Gold Price Fixing»,
Journal of Futures Markets; Baur et al. (2016), microestructura del mercado físico LBMA en la apertura europea.
Entre las 02:00 y las 03:30 ET (07:00–08:30 UK / 08:00–09:30 Zurich) los bancos de lingotes consolidan el inventario físico
procedente de Asia/Shanghái antes del inicio de la subasta matutina de Londres. La ruptura de esa caja de 90 minutos guía el
tramo europeo hasta antes del London AM Fix (10:25 ET). Distinto de ORO-ALMUERZO-RUPTURA (caja de 6 horas 08:00–14:00 Madrid)
y de ORO-0530 (burst de 05:30 UTC). Diseño: docs/research/programa_r_20261103/DISENO_APERTURA_EUROPA_ORO.md.

Construcción (100% causal):
- Deriva asiática previa: retorno entre 18:00 y 02:00 ET (rel en (0, 480]).
- Caja europea de lingotes: velas M1 que cierran en (120, 210] minutos NY (02:00–03:30 ET), exigiendo >= 65 velas.
- Disparo: para cada lado (largo/corto), el PRIMER cierre M1 fuera de [lo, hi] en (210, 450] (03:30–07:30 ET).
- Variables causales en k: alineación con la deriva asiática (0=contra Asia, 1=a favor de Asia, 2=cualquiera), fracción de cuerpo
  de la vela de quiebre y compresión de la caja en unidades de ATR14.
- Ejecución: stop en el punto medio (MID) o borde opuesto (OPUESTO) con piso de 4 ticks, objetivo amplio a 2,0R, 3,0R o 3,5R,
  y salida forzada a las 10:25 ET (625 min NY).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import rango_ruptura as RR
from edgelab.research.londres_impulso import _lote  # noqa: F401
from edgelab.research.grilla_generica import Variable
from edgelab.research.oro_almuerzo_ruptura import _offset_madrid_segundos_nb
from edgelab.research.zonas_gaps import _atr_causal

NOMBRE = "APERTURA-EUROPA-ORO"
INDICADORES = ["APERTURA-EUROPA-ORO"]
REL_ASIA_FIN, M_INI_UK, M_FIN_UK, M_LIM_UK, M_SALE = 480, 420, 510, 750, 505
PREFLIGHT_T0_S = 1_760_047_200
EXCLUIR_EVENTOS = dict(antes_min=15, despues_min=15, tipos=("CPI", "NFP_EMPLOYMENT_SITUATION", "FOMC_DECISION"))
VARIABLES = [
    Variable("alineacion_asia", "alin_asia", "eq_any", categoria=2),
    Variable("cuerpo_quiebre", "cuerpo", "ge", cortes=(0.45, 0.65)),
    Variable("compresion_caja", "ancho_atr", "extremos", cuantiles=3),
]
EJES_ORDINALES = (1, 2)
EJECUCIONES = [("MID", 2.0), ("MID", 3.5), ("OPUESTO", 2.0), ("OPUESTO", 3.0)]
BASE = {"alineacion_asia": 2, "cuerpo_quiebre": 0, "compresion_caja": 2, "ejecución": 1}
VACIO = ["k", "ses", "lado", "hi", "lo", "mid", "alin_asia", "cuerpo", "ancho_atr"]


def disparos(ctx: dict) -> pd.DataFrame:
    o, h, l, c = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c"))
    t_arr = np.asarray(ctx["t"], np.int64); ses = np.asarray(ctx["ses"], np.int64)
    m_uk = np.array([((int(ts) + _offset_madrid_segundos_nb(int(ts)) - 3600) % 86400) // 60 for ts in t_arr], dtype=np.int64)
    atr = _atr_causal(h, l, c); filas = []
    for sg in np.unique(ses):
        idx = np.flatnonzero(ses == sg); mm = m_uk[idx]
        asia = idx[(mm >= 0) & (mm <= M_INI_UK)]
        rg = idx[(mm > M_INI_UK) & (mm <= M_FIN_UK)]
        if len(asia) < 60 or len(rg) < 65: continue
        hi, lo = float(h[rg].max()), float(l[rg].min()); mid = 0.5 * (hi + lo)
        if not hi > lo or not atr[rg[-1]] > 0: continue
        dir_asia = int(np.sign(c[asia[-1]] - o[asia[0]]))
        ancho_atr = (hi - lo) / float(atr[rg[-1]])
        post = idx[(idx > rg[-1]) & (mm > M_FIN_UK) & (mm <= M_LIM_UK)]
        for s in (1, -1):
            fuera = post[c[post] > hi] if s == 1 else post[c[post] < lo]
            if not len(fuera): continue
            k = int(fuera[0]); rk = float(h[k] - l[k])
            cuerpo = abs(float(c[k] - o[k])) / rk if rk > 0 else 0.0
            alin = (1 if s == dir_asia else 0) if dir_asia != 0 else 0
            filas.append((k, int(sg), s, hi, lo, mid, alin, cuerpo, float(ancho_atr)))
    return pd.DataFrame(filas, columns=VACIO).sort_values("k", kind="stable", ignore_index=True) if filas else pd.DataFrame(columns=VACIO)


def lineas_salida(ctx) -> np.ndarray:
    return RR.lineas_salida(ctx, M_SALE)


def niveles(d, ej: tuple, ctx: dict):
    return RR.niveles_con(_lote, d, ej, ctx)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    return RR.niveles_lote_con(_lote, D, ej, ctx)
