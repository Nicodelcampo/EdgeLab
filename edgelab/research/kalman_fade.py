"""KALMAN-FADE (2026-10-30): sorpresas extremas contra un nivel oculto estimado con un filtro de Kalman de nivel local.

Origen: propuesta de Nico del 2026-10-30 (material de QuantFinanceToGo, «Observed = TRUE + noise»), evaluada en la sala ese día:
de esa lista sólo esta idea aplica a futuros direccionales sin libro de opciones. Pre-registro: docs/research/kalman_fade_20261030/SPEC_KALMAN_FADE.md.

Hipótesis económica: el precio M1 es un nivel «justo» que se mueve despacio más ruido de microestructura (barridos, órdenes de mercado
grandes, falta de liquidez momentánea). Cuando la innovación del filtro (precio menos nivel previsto) es extrema en unidades de su
propio desvío, una parte es ruido transitorio y el precio vuelve hacia el nivel. Si no vuelve (la sorpresa era información), el canal
de continuación lo muestra: por eso las ejecuciones incluyen las dos direcciones y el embudo decide.

Modelo (causal, una pasada): nivel x_t = x_{t-1} + w_t, precio c_t = x_t + v_t. R (varianza del ruido) se estima con una EWMA de las
innovaciones al cuadrado ANTES de actualizar con la vela t; Q = q·R con q fijo por nivel de `suavidad`. El estado se reinicia al cierre
de la primera vela de cada sesión. Disparo en la vela k si |z_k| >= Z_MIN, con z_k = (c_k - x_{k|k-1}) / sqrt(P_{k|k-1} + R_{k-1}),
a lo sumo uno cada ENFRIAMIENTO velas por suavidad y sesión. Todo lo que usa la fila k se conoce al cierre de k.

Perillas (pocas, para no inflar N_eff): `suavidad` (q = 1e-3, 1e-2, 1e-1), `z_extremo` (|z| >= 2.5 / 3 / 4), `regimen_vol` (terciles
causales de RV corta / RV larga). Ejecuciones: FADE o CONTINUACION × objetivo (nivel o mitad del camino) × stop (1 o 2 desvíos).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable

try:
    from numba import njit
except ImportError:                                            # el kernel de Kaggle y el Debian tienen numba; los tests corren igual sin él
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "KALMAN-FADE"
INDICADORES = ["KALMAN-FADE"]

Q_REL = (1e-3, 1e-2, 1e-1)                                     # Q / R por nivel de suavidad (más chico = nivel más lento)
Z_MIN = 2.5
ENFRIAMIENTO = 15                                              # velas entre disparos de la misma suavidad en la sesión
ALFA_R = 0.05                                                  # EWMA de las innovaciones al cuadrado (≈ 20 velas)

VARIABLES = [
    Variable("suavidad", "suav", "grupo", categoria=3),                     # 0: q=1e-3 · 1: q=1e-2 · 2: q=1e-1
    Variable("z_extremo", "z_abs", "ge", cortes=(3.0, 4.0)),                # |z| >= 2.5 (piso del disparo) / >= 3 / >= 4
    Variable("regimen_vol", "rv_rel", "extremos", cuantiles=3),             # terciles causales de RV(30 velas) / RV(390 velas)
]
EJES_ORDINALES = (1, 2)

MODOS = ("FADE", "CONTINUACION")
OBJETIVOS = ("NIVEL", "MITAD")
STOPS = ("S1", "S2")
EJECUCIONES = [(m, tp, sl) for m in MODOS for tp in OBJETIVOS for sl in STOPS]

BASE = {"suavidad": 1, "z_extremo": 0, "regimen_vol": 1, "ejecución": EJECUCIONES.index(("FADE", "NIVEL", "S2"))}


@njit(cache=False)
def _kalman_nb(c, ses, q_rel, z_min, enfriamiento, alfa_r):
    n = len(c)
    nq = len(q_rel)
    max_out = max(n, 16)
    out_k = np.empty(max_out, dtype=np.int64); out_suav = np.empty(max_out, dtype=np.int64)
    out_z = np.empty(max_out, dtype=np.float64); out_x = np.empty(max_out, dtype=np.float64)
    out_sd = np.empty(max_out, dtype=np.float64); out_rv = np.empty(max_out, dtype=np.float64)
    cnt = 0
    x = np.zeros(nq); P = np.zeros(nq); R = np.zeros(nq); ult = np.full(nq, -10**9)
    viva = np.zeros(nq, dtype=np.int64)
    rv_c = 0.0; rv_l = 0.0
    for i in range(n):
        if i == 0 or ses[i] != ses[i - 1]:
            for j in range(nq):
                x[j] = c[i]; P[j] = 0.0; R[j] = 0.0; ult[j] = -10**9; viva[j] = 0
            continue
        r = c[i] - c[i - 1]
        rel = (rv_c / rv_l) ** 0.5 if rv_l > 0.0 else np.nan            # régimen conocido ANTES de la vela i
        for j in range(nq):
            Rj = R[j]
            if viva[j] >= 30 and Rj > 0.0:                               # 30 velas de la sesión para estimar R
                Pp = P[j] + q_rel[j] * Rj
                S = Pp + Rj
                innov = c[i] - x[j]
                z = innov / S ** 0.5
                if abs(z) >= z_min and i - ult[j] >= enfriamiento and cnt < max_out:
                    out_k[cnt] = i; out_suav[cnt] = j; out_z[cnt] = z; out_x[cnt] = x[j]
                    out_sd[cnt] = S ** 0.5; out_rv[cnt] = rel; cnt += 1; ult[j] = i
                K = Pp / S
                x[j] = x[j] + K * innov
                P[j] = (1.0 - K) * Pp
                R[j] = (1.0 - alfa_r) * Rj + alfa_r * innov * innov
            else:
                innov = c[i] - x[j]
                R[j] = (Rj * viva[j] + innov * innov) / (viva[j] + 1)       # media simple hasta tener 30 velas
                x[j] = c[i]
            viva[j] += 1
        rv_c = rv_c + (r * r - rv_c) / 30.0
        rv_l = rv_l + (r * r - rv_l) / 390.0
    return out_k[:cnt], out_suav[:cnt], out_z[:cnt], out_x[:cnt], out_sd[:cnt], out_rv[:cnt]


def disparos(ctx: dict) -> pd.DataFrame:
    c = np.asarray(ctx["c"], dtype=np.float64)
    ses = np.asarray(ctx["ses"], dtype=np.int64)
    k, su, z, x, sd, rv = _kalman_nb(c, ses, np.asarray(Q_REL, dtype=np.float64), Z_MIN, ENFRIAMIENTO, ALFA_R)
    return pd.DataFrame(dict(k=k, ses=ses[k], suav=su, z=z, z_abs=np.abs(z), nivel=x, sd=sd, rv_rel=rv))


def _niveles_arr(k, z, nivel, sd, ej, ctx):
    modo, obj, stop = ej
    tick = float(ctx["tick"])
    e = np.round(np.asarray(ctx["c"], dtype=np.float64)[k] / tick) * tick
    s = -np.sign(z) if modo == "FADE" else np.sign(z)
    dist = np.abs(nivel - e) * (1.0 if obj == "NIVEL" else 0.5)
    dist = np.maximum(dist, 2.0 * tick)
    tp = np.round((e + s * dist) / tick) * tick
    m = 1.0 if stop == "S1" else 2.0
    dsl = np.maximum(m * sd, 2.0 * tick)
    sl_raw = e - s * dsl
    sl = np.where(s > 0, np.floor(sl_raw / tick) * tick, np.ceil(sl_raw / tick) * tick)
    return e, s, sl, tp


def niveles(d, ej: tuple, ctx: dict):
    k = int(d["k"])
    e, s, sl, tp = _niveles_arr(np.array([k]), np.array([float(d["z"])]), np.array([float(d["nivel"])]), np.array([float(d["sd"])]), ej, ctx)
    if s[0] == 0:
        return None
    return (k, 2, int(s[0]), float(e[0]), float(sl[0]), float(tp[0]), 0)     # entrada en el tick siguiente al cierre de k


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    out = np.full((len(D), 7), np.nan, dtype=np.float64)
    if len(D) == 0:
        return out
    k = D["k"].to_numpy(np.int64)
    e, s, sl, tp = _niveles_arr(k, D["z"].to_numpy(np.float64), D["nivel"].to_numpy(np.float64), D["sd"].to_numpy(np.float64), ej, ctx)
    ok = s != 0
    out[ok, 0] = k[ok]; out[ok, 1] = 2.0; out[ok, 2] = s[ok]; out[ok, 3] = e[ok]; out[ok, 4] = sl[ok]; out[ok, 5] = tp[ok]; out[ok, 6] = 0.0
    return out
