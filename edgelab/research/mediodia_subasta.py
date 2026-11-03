"""MEDIODIA-SUBASTA (2026-11-03, programa R): compresión del almuerzo de Nueva York (11:30–13:00 ET) y ruptura vespertina.

Fuente: Admati y Pfleiderer (1988), «A Theory of Intraday Patterns: Volume and Price Variability», Review of Financial Studies;
curva en U de liquidez y volatilidad intradía en renta variable de EE.UU. Entre las 11:30 y las 13:00 ET la actividad institucional
cae al mínimo del día y el precio forma una caja de compresión. Al regresar las mesas a las 13:00 ET, el primer cierre fuera de la
caja de almuerzo entre las 13:00 y las 14:45 ET inicia el tramo direccional de la tarde hasta las 15:55 ET.
Diseño: docs/research/programa_r_20261103/DISENO_MEDIODIA_SUBASTA.md.

Construcción (100% causal):
- Tramo matutino: (570, 690] minutos NY (09:30–11:30 ET). Caja de almuerzo: (690, 780] (11:30–13:00 ET).
- Disparo: para cada lado (largo/corto), el PRIMER cierre M1 fuera de [lo_alm, hi_alm] en (780, 885] (13:00–14:45 ET).
- Variables causales en k: razón de compresión (rango del almuerzo / rango de la mañana), fracción de cuerpo de la vela de quiebre
  y alineación con la dirección de la mañana (0=en contra, 1=a favor, 2=cualquiera).
- Ejecución: entrada en el primer tick de la vela siguiente, stop en el punto medio (MID) o borde opuesto (OPUESTO) de la caja de
  almuerzo con piso de 4 ticks, objetivo a 2,0R, 3,0R o 3,5R, y salida forzada a las 15:55 ET (955 min NY).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import rango_ruptura as RR
from edgelab.research.londres_impulso import _lote  # noqa: F401
from edgelab.research.grilla_generica import Variable
from edgelab.research.regimen_sesion import minuto_ny

NOMBRE = "MEDIODIA-SUBASTA"
INDICADORES = ["MEDIODIA-SUBASTA"]
M_AM0, M_INI, M_FIN, M_LIM, M_SALE = 570, 690, 780, 885, 955
PREFLIGHT_T0_S = 1_760_047_200
VARIABLES = [
    Variable("compresion_almuerzo", "comp_ratio", "le", cortes=(0.75, 1.05)),
    Variable("cuerpo_quiebre", "cuerpo", "ge", cortes=(0.45, 0.65)),
    Variable("sesgo_manana", "alineado", "eq_any", categoria=2),
]
EJES_ORDINALES = (0, 1)
EJECUCIONES = [("MID", 2.0), ("MID", 3.5), ("OPUESTO", 2.0), ("OPUESTO", 3.0)]
BASE = {"compresion_almuerzo": 1, "cuerpo_quiebre": 0, "sesgo_manana": 2, "ejecución": 1}
VACIO = ["k", "ses", "lado", "hi", "lo", "mid", "comp_ratio", "cuerpo", "alineado"]


def disparos(ctx: dict) -> pd.DataFrame:
    o, h, l, c = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c"))
    ses = np.asarray(ctx["ses"], np.int64); m = minuto_ny(np.asarray(ctx["t"], np.int64)); filas = []
    for sg in np.unique(ses):
        idx = np.flatnonzero(ses == sg); mm = m[idx]
        am = idx[(mm > M_AM0) & (mm <= M_INI)]
        alm = idx[(mm > M_INI) & (mm <= M_FIN)]
        if len(am) < 80 or len(alm) < 65: continue
        hi_am, lo_am = float(h[am].max()), float(l[am].min())
        hi, lo = float(h[alm].max()), float(l[alm].min()); mid = 0.5 * (hi + lo)
        if not (hi > lo and hi_am > lo_am): continue
        comp = (hi - lo) / (hi_am - lo_am); dir_am = int(np.sign(c[am[-1]] - o[am[0]]))
        post = idx[(idx > alm[-1]) & (mm > M_FIN) & (mm <= M_LIM)]
        for s in (1, -1):
            fuera = post[c[post] > hi] if s == 1 else post[c[post] < lo]
            if not len(fuera): continue
            k = int(fuera[0]); rk = float(h[k] - l[k])
            cuerpo = abs(float(c[k] - o[k])) / rk if rk > 0 else 0.0
            alin = (1 if s == dir_am else 0) if dir_am != 0 else 0
            filas.append((k, int(sg), s, hi, lo, mid, float(comp), cuerpo, alin))
    return pd.DataFrame(filas, columns=VACIO).sort_values("k", kind="stable", ignore_index=True) if filas else pd.DataFrame(columns=VACIO)


def lineas_salida(ctx) -> np.ndarray:
    return RR.lineas_salida(ctx, M_SALE)


def niveles(d, ej: tuple, ctx: dict):
    return RR.niveles_con(_lote, d, ej, ctx)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    return RR.niveles_lote_con(_lote, D, ej, ctx)
