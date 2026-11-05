"""LEAD-LAG (2026-11-03, programa R): un activo «líder» se mueve fuerte y el que se opera todavía no lo acompañó.

Fuente: formación del precio entre mercados (Hasbrouck 1995, JF, «One Security, Many Markets»; Chordia y Swaminathan 2000, JF,
lead-lag por velocidad de ajuste). Caso principal: EURUSD (el dólar) lidera al oro (GC): una caída del dólar sube el oro, y el
futuro de oro incorpora el movimiento con rezago de minutos en horarios de poca liquidez. Diversificación: otro instrumento (GC)
y otro mecanismo (cruzado entre clases de activos), sin relación con las zonas y corredores de la cartera. Programa:
docs/research/programa_r_20261103/DISENO_FAMILIAS_NUEVAS.md.

Construcción (causal): sensor = el que se opera; confirmador = el líder (`ctx["conf"]`, alineado por minuto). Retornos de L minutos en
unidades de su desvío de la sesión ANTERIOR (zc líder, zs seguidor) y correlación ρ de esos retornos en la sesión anterior; la perilla
`rho_fuerte` separa |ρ| ≥ 0,2 (la relación que justifica la idea) del resto (control). Disparo: |zc| ≥ 2 y el seguidor no acompañó (zs·signo(zc·ρ) < 0,25·|zc|); un disparo cada L velas como máximo. Lado =
signo(zc·ρ). Ejecución: objetivo a `a` desvíos de L minutos del seguidor y stop a `b`; salida forzada a las TOPE_BARRAS velas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable
from edgelab.research.par_relativo import _alinear  # noqa: F401 (minuto del confirmador alineado al del sensor)
from edgelab.research.regimen_sesion import minuto_ny

NOMBRE = "LEAD-LAG"
INDICADORES = ["LEAD-LAG"]
CONFIRMADOR = True
LS = (5, 15, 30)
TOPE_BARRAS = 60
VARIABLES = [
    Variable("horizonte", "li", "grupo", categoria=3),
    Variable("z_lider", "zc_abs", "ge", cortes=(2.5, 3.0)),
    Variable("franja", "franja", "grupo", categoria=3),
    Variable("rho_fuerte", "rho_f", "grupo", categoria=2),        # 1 si |ρ| de la sesión anterior ≥ 0,2
]
EJES_ORDINALES = (1,)
EJECUCIONES = [("OBJ", a, "STOP", b) for a in (1.0, 2.0) for b in (1.0, 2.0)]
BASE = {"horizonte": 1, "z_lider": 0, "franja": 0, "rho_fuerte": 1, "ejecución": 1}
VACIO = ["k", "ses", "lado", "li", "zc_abs", "franja", "rho_f", "sd_pts"]


def _franja(m):                                         # Asia 18:00–03:00, Europa 03:00–09:30, EE.UU. 09:30–17:00 (hora NY)
    return np.where((m >= 18 * 60) | (m < 3 * 60), 0, np.where(m < 9 * 60 + 30, 1, 2))


def disparos(ctx: dict) -> pd.DataFrame:
    c = np.asarray(ctx["c"], float); cl = _alinear(ctx); ses = np.asarray(ctx["ses"], np.int64)
    m = minuto_ny(np.asarray(ctx["t"], np.int64)); us = np.unique(ses); filas = []
    for li, L in enumerate(LS):
        rs = pd.Series(np.log(c)).groupby(ses).diff(L).to_numpy(); rc = pd.Series(np.log(cl)).groupby(ses).diff(L).to_numpy()
        prev = {}
        for a, b in zip(us[:-1], us[1:]):
            k = (ses == a) & np.isfinite(rs) & np.isfinite(rc)
            if k.sum() >= 100 and np.std(rs[k]) > 0 and np.std(rc[k]) > 0:
                prev[b] = (float(np.std(rs[k])), float(np.std(rc[k])), float(np.corrcoef(rs[k], rc[k])[0, 1]))
        ultimo = -10**9
        for k in range(len(c)):
            p = prev.get(ses[k])
            if p is None or not np.isfinite(rs[k]) or not np.isfinite(rc[k]) or p[2] == 0 or k - ultimo < L: continue
            zs, zc = rs[k] / p[0], rc[k] / p[1]; d = np.sign(zc * p[2])
            if abs(zc) >= 2.0 and zs * d < 0.25 * abs(zc):
                ultimo = k; filas.append((k, int(ses[k]), int(d), li, float(abs(zc)), int(_franja(m[k])), int(abs(p[2]) >= 0.2), float(p[0] * c[k])))
    return pd.DataFrame(filas, columns=VACIO).sort_values("k", kind="stable", ignore_index=True) if filas else pd.DataFrame(columns=VACIO)


def _lote(D, ej, ctx):
    tick = float(ctx["tick"]); c = np.asarray(ctx["c"], float)
    k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64); e = c[k]; sd = D["sd_pts"].to_numpy(float)
    dtp = np.maximum(ej[1] * sd, tick); dst = np.maximum(ej[3] * sd, 2 * tick)
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
