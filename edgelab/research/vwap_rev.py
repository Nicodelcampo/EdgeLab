"""VWAP-REV (2026-11-03, programa R): reversión al VWAP de la sesión regular tras un desvío extremo con vela de giro.

Fuente: el VWAP es el ancla de ejecución de los algoritmos institucionales (Berkowitz, Logue y Noser 1988, JF; Madhavan 2002,
«VWAP Strategies»): los desvíos grandes fuera de las noticias los genera flujo transitorio que los ejecutores de VWAP absorben, y
el precio vuelve hacia el promedio ponderado. Da muchas operaciones por mes, que es lo que más potencia aporta al programa R.
Distinto de KALMAN-FADE (ancla filtrada sin volumen) y de las reglas de zonas. Programa:
docs/research/programa_r_20261103/DISENO_FAMILIAS_NUEVAS.md.

Construcción (causal): VWAP y desvío ponderado desde las 09:30 NY. Ventana de decisión 10:30–15:00. Disparo: |c − VWAP| ≥ 2 desvíos
y la vela cierra hacia el VWAP respecto de la anterior (giro); un episodio por desvío (rearma con |dev| < 1). Lado = hacia el VWAP.
Ejecución: objetivo a `frac` de la distancia al VWAP y stop a `m` desvíos más allá de la entrada; salida forzada a las 15:59.
Fuera de eventos macro (CPI, NFP, FOMC: ±15 min), porque ahí el desvío es información y no flujo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable
from edgelab.research.regimen_sesion import minuto_ny, rv_relativa

NOMBRE = "VWAP-REV"
INDICADORES = ["VWAP-REV"]
M_RTH, M0, M1, M_SALE = 9 * 60 + 31, 10 * 60 + 30, 15 * 60, 959
EXCLUIR_EVENTOS = dict(antes_min=15, despues_min=15, tipos=("CPI", "NFP_EMPLOYMENT_SITUATION", "FOMC_DECISION"))
VARIABLES = [
    Variable("desvio", "dev_abs", "ge", cortes=(2.5, 3.0)),
    Variable("franja", "franja", "grupo", categoria=2),
    Variable("regimen_vol", "rv_rel", "extremos", cuantiles=3),
]
EJES_ORDINALES = (0,)
EJECUCIONES = [("OBJ", f, "STOP", mm) for f in (0.5, 1.0) for mm in (1.0, 2.0)]
BASE = {"desvio": 0, "franja": 0, "regimen_vol": 1, "ejecución": 1}
VACIO = ["k", "ses", "lado", "dev_abs", "franja", "rv_rel", "dist_pts", "sd_pts"]


def disparos(ctx: dict) -> pd.DataFrame:
    c, o, v = (np.asarray(ctx[x], float) for x in ("c", "o", "v")); ses = np.asarray(ctx["ses"], np.int64)
    m = minuto_ny(np.asarray(ctx["t"], np.int64)); rv = rv_relativa(c, ses, 30, 390); filas = []
    sv = spv = spv2 = 0.0; ses_prev = None; listo = True
    for k in range(len(c)):
        if ses[k] != ses_prev: sv = spv = spv2 = 0.0; ses_prev = ses[k]; listo = True
        if m[k] < M_RTH or m[k] > M_SALE: continue
        w = max(v[k], 1.0); sv += w; spv += w * c[k]; spv2 += w * c[k] * c[k]
        vw = spv / sv; sd = np.sqrt(max(spv2 / sv - vw * vw, 0.0))
        if not sd > 0: continue
        dev = (c[k] - vw) / sd
        if abs(dev) < 1.0: listo = True; continue
        giro = k > 0 and ses[k - 1] == ses[k] and np.sign(c[k] - c[k - 1]) == -np.sign(dev) and np.sign(c[k] - o[k]) == -np.sign(dev)
        if listo and abs(dev) >= 2.0 and giro and M0 <= m[k] <= M1:
            listo = False
            filas.append((k, int(ses[k]), int(-np.sign(dev)), float(abs(dev)), int(m[k] >= 12 * 60 + 30), float(rv[k]), float(abs(c[k] - vw)), float(sd)))
    return pd.DataFrame(filas, columns=VACIO) if filas else pd.DataFrame(columns=VACIO)


def lineas_salida(ctx) -> np.ndarray:
    """Fuerza la salida en las velas que cierran entre 15:59 y 17:00 NY (como EOD-MOM)."""
    m = minuto_ny(np.asarray(ctx["t"], np.int64)); f = (m >= M_SALE) & (m < 1020)
    return np.vstack([np.where(f, np.inf, np.nan), np.where(f, -np.inf, np.nan)])


def _lote(D, ej, ctx):
    tick = float(ctx["tick"]); c = np.asarray(ctx["c"], float)
    k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64); e = c[k]
    dtp = np.maximum(ej[1] * D["dist_pts"].to_numpy(float), tick); dst = np.maximum(ej[3] * D["sd_pts"].to_numpy(float), 2 * tick)
    tp = np.where(s == 1, np.round((e + dtp) / tick) * tick, np.round((e - dtp) / tick) * tick)
    st = np.where(s == 1, np.floor((e - dst) / tick) * tick, np.ceil((e + dst) / tick) * tick)
    return k, s, e, st, tp, (s == -1).astype(np.int64)


def niveles(d, ej: tuple, ctx: dict):
    k, s, e, st, tp, kl = _lote(pd.DataFrame([d]), ej, ctx)
    return (int(k[0]), 2, int(s[0]), float(e[0]), float(st[0]), float(tp[0]), 0, int(kl[0]), 0.0)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    if not len(D): return np.full((0, 9), np.nan)
    k, s, e, st, tp, kl = _lote(D, ej, ctx)
    return np.column_stack([k, np.full(len(D), 2), s, e, st, tp, np.zeros(len(D)), kl, np.zeros(len(D))]).astype(float)
