"""PAR-REL (2026-11-03, programa R): valor relativo intradía entre dos índices (pares).

Fuente: Gatev, Goetzmann y Rouwenhorst (2006), «Pairs Trading: Performance of a Relative-Value Arbitrage Rule», RFS; en futuros de
índices el diferencial NQ/ES (o YM/ES) revierte porque comparten el factor de mercado y los desvíos intradía vienen de flujos
sectoriales transitorios (rebalanceos, órdenes grandes en un solo contrato). Diversificación: es una apuesta relativa, casi neutral
a la dirección del mercado, distinta de las reglas direccionales de la cartera (zonas, áreas, corredores). Programa:
docs/research/programa_r_20261103/DISENO_FAMILIAS_NUEVAS.md.

Construcción (causal): sensor = instrumento que se opera (NQ o YM), confirmador = ES (`ctx["conf"]`, alineado por minuto). β de la
sesión = cov/var de los retornos de 1 minuto de la sesión ANTERIOR. Spread s = ln(sensor) − β·ln(ES). z = (s − media W) / desvío W
(W velas, dentro de la sesión). Disparo: la primera vela del horario 09:45–15:30 NY en que |z| ≥ 2 después de haber estado |z| < 1
(un episodio por cruce). Lado = −signo(z) en el sensor (se apuesta a que el spread vuelve). σ en puntos del sensor = desvío W × precio.
Ejecución: objetivo a `frac` del camino de vuelta a z = 0 y stop a `m` desvíos más allá de la entrada; salida forzada al fin de la
ventana (TOPE_BARRAS).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable
from edgelab.research.regimen_sesion import minuto_ny

NOMBRE = "PAR-REL"
INDICADORES = ["PAR-REL"]
CONFIRMADOR = True                                    # el preflight le arma un confirmador sintético
VENTANAS = (30, 60, 120)
M0, M1 = 9 * 60 + 45, 15 * 60 + 30
TOPE_BARRAS = 120
VARIABLES = [
    Variable("ventana", "w", "grupo", categoria=3),
    Variable("z", "zabs", "ge", cortes=(2.5, 3.0)),
    Variable("franja", "franja", "grupo", categoria=3),
]
EJES_ORDINALES = (1,)
EJECUCIONES = [("OBJ", f, "STOP", m) for f in (0.5, 1.0) for m in (1.0, 2.0)]
BASE = {"ventana": 1, "z": 0, "franja": 0, "ejecución": 1}
VACIO = ["k", "ses", "lado", "w", "zabs", "franja", "sd_pts"]


def _alinear(ctx):
    cf = ctx["conf"]; t = np.asarray(ctx["t"], np.int64); tc = np.asarray(cf["t"], np.int64)
    j = np.searchsorted(tc, t); jc = np.clip(j, 0, len(tc) - 1)
    return np.where((j < len(tc)) & (tc[jc] == t), np.asarray(cf["c"], float)[jc], np.nan)


def _franja(m):
    return np.where(m < 11 * 60 + 30, 0, np.where(m < 14 * 60, 1, 2))


def disparos(ctx: dict) -> pd.DataFrame:
    c = np.asarray(ctx["c"], float); ces = _alinear(ctx); ses = np.asarray(ctx["ses"], np.int64)
    m = minuto_ny(np.asarray(ctx["t"], np.int64)); ls, lc = np.log(c), np.log(ces)
    rs, rc = np.r_[np.nan, np.diff(ls)], np.r_[np.nan, np.diff(lc)]
    nueva = np.r_[True, ses[1:] != ses[:-1]]; rs[nueva] = np.nan; rc[nueva] = np.nan
    us = np.unique(ses); beta = {}
    for a, b in zip(us[:-1], us[1:]):                                   # β de la sesión b = el de la sesión anterior a
        k = (ses == a) & np.isfinite(rs) & np.isfinite(rc)
        if k.sum() >= 100 and np.var(rc[k]) > 0: beta[b] = float(np.cov(rs[k], rc[k])[0, 1] / np.var(rc[k], ddof=1))
    bv = pd.Series(ses).map(beta).to_numpy(float); s = ls - bv * lc
    filas = []
    for wi, W in enumerate(VENTANAS):
        g = pd.Series(s).groupby(ses)
        mu = g.transform(lambda x: x.rolling(W, min_periods=W).mean()).to_numpy()
        sd = g.transform(lambda x: x.rolling(W, min_periods=W).std()).to_numpy()
        z = (s - mu) / sd
        armado = np.zeros(len(c), bool); listo = {}
        for k in range(len(c)):
            if not np.isfinite(z[k]) or not sd[k] > 0: continue
            sg = ses[k]
            if abs(z[k]) < 1.0: listo[sg] = True; continue
            if abs(z[k]) >= 2.0 and listo.get(sg) and M0 <= m[k] <= M1:
                listo[sg] = False
                filas.append((k, int(sg), int(-np.sign(z[k])), wi, float(abs(z[k])), int(_franja(m[k])), float(sd[k] * c[k])))
    return pd.DataFrame(filas, columns=VACIO).sort_values("k", kind="stable", ignore_index=True) if filas else pd.DataFrame(columns=VACIO)


def _lote(D, ej, ctx):
    tick = float(ctx["tick"]); c = np.asarray(ctx["c"], float)
    k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64); e = c[k]; sd = D["sd_pts"].to_numpy(float); z = D["zabs"].to_numpy(float)
    dtp = np.maximum(ej[1] * z * sd, tick); dst = np.maximum(ej[3] * sd, 2 * tick)
    tp = np.where(s == 1, np.round((e + dtp) / tick) * tick, np.round((e - dtp) / tick) * tick)
    st = np.where(s == 1, np.floor((e - dst) / tick) * tick, np.ceil((e + dst) / tick) * tick)
    return k, s, e, st, tp


def niveles(d, ej: tuple, ctx: dict):
    k, s, e, st, tp = _lote(pd.DataFrame([d]), ej, ctx)
    return (int(k[0]), 2, int(s[0]), float(e[0]), float(st[0]), float(tp[0]), 0)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    if not len(D): return np.full((0, 7), np.nan)
    k, s, e, st, tp = _lote(D, ej, ctx)
    return np.column_stack([k, np.full(len(D), 2), s, e, st, tp, np.zeros(len(D))]).astype(float)
