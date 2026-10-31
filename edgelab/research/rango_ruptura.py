"""Núcleo de RANGO-RUPTURA (2026-10-31): ruptura de un rango de 15 minutos fijo del reloj de Nueva York, con a lo sumo una reentrada.

Lo usan dos familias independientes, cada una con su módulo, su ventana y su pre-registro (docs/research/paquete_20261031/):
  - `rango_asia0100`: rango 01:00–01:15 ET (transición Asia → pre-Londres; ranking de sesiones de @theagent_trades, secc. 2.4 y 4.1).
  - `rango_preapertura`: rango 09:15–09:30 ET (pre-apertura de Nueva York; el mismo ranking la pone arriba de 09:30–09:45, saturada).
Hipótesis económica: el rango de 15 minutos concentra órdenes en sus bordes (stops y órdenes de entrada); la ruptura con cuerpo
fuerte y volumen libera ese flujo en la dirección del quiebre. Si el primer quiebre falla y barre la mitad del rango, los stops del
lado atrapado ya salieron y el segundo quiebre (en cualquier dirección) es el limpio (regla de una reentrada, secc. 3.3).

Construcción (causal): rango = máximo y mínimo de las velas que cierran en (INI, FIN]. Primer disparo: primer cierre fuera del rango en
(FIN, LIMITE]. Reentrada: si después del primer disparo el precio toca la mitad del rango (el stop MID del primero habría saltado), el
siguiente cierre fuera del rango, en cualquier dirección y antes de LIMITE, es el intento 2. Nada más por sesión.
Perillas: cuerpo fuerte (|c−o| ≥ 55 % del rango de la vela), volumen relativo de la vela de ruptura (≥ 1,15 × media de 30 velas),
ancho del rango / ATR14 (terciles), eficiencia de 60 velas de la sesión y número de intento.
Ejecuciones: stop en la MITAD del rango o en el borde OPUESTO × objetivo 1R, 2R o salida forzada a la hora SALIDA (salida por línea).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable
from edgelab.research.regimen_sesion import er_sesion, minuto_ny
from edgelab.research.zonas_gaps import _atr_causal

VARIABLES = [
    Variable("cuerpo_fuerte", "cuerpo", "eq_any", categoria=2),
    Variable("volumen_rel", "rvol", "ge", cortes=(1.15,)),
    Variable("ancho_rango", "ancho", "extremos", cuantiles=3),
    Variable("eficiencia", "er", "ge", cortes=(0.25, 0.42)),
    Variable("intento", "intento", "grupo", categoria=2),
]
EJES_ORDINALES = (3,)
EJECUCIONES = [(sl, tp) for sl in ("MID", "OPUESTO") for tp in ("1R", "2R", "SALIDA")]
BASE = {"cuerpo_fuerte": 2, "volumen_rel": 0, "ancho_rango": 2, "eficiencia": 0, "intento": 0, "ejecución": 1}


def disparos(ctx: dict, ini: int, fin: int, limite: int) -> pd.DataFrame:
    o, h, l, c, v = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c", "v"))
    ses = np.asarray(ctx["ses"], np.int64); m = minuto_ny(np.asarray(ctx["t"], np.int64))
    atr = _atr_causal(h, l, c); er = er_sesion(c, ses, 60)
    vm = pd.Series(v).groupby(ses).transform(lambda x: x.shift(1).rolling(30, min_periods=30).mean()).to_numpy()
    filas = []
    for sg in np.unique(ses):
        idx = np.flatnonzero(ses == sg); mm = m[idx]
        rg = idx[(mm > ini) & (mm <= fin)]
        if len(rg) < 0.8 * (fin - ini): continue
        hi, lo = h[rg].max(), l[rg].min(); mid = (hi + lo) / 2
        if not hi > lo: continue
        post = idx[(idx > rg[-1]) & (mm > fin) & (mm <= limite)]
        intento = 0; lado1 = 0
        for k in post:
            if intento == 1:
                if (lado1 == 1 and l[k] <= mid) or (lado1 == -1 and h[k] >= mid): intento = 2; continue
            if intento == 1 or intento == 3: continue
            s = 1 if c[k] > hi else (-1 if c[k] < lo else 0)
            if s == 0: continue
            rk = h[k] - l[k]
            filas.append((int(k), int(sg), s, hi, lo, mid, int(rk > 0 and abs(c[k] - o[k]) >= 0.55 * rk),
                          v[k] / vm[k] if vm[k] > 0 else np.nan, (hi - lo) / atr[k] if atr[k] > 0 else np.nan, float(er[k]), 0 if intento == 0 else 1))
            if intento == 0: intento = 1; lado1 = s
            else: intento = 3
    return pd.DataFrame(filas, columns=["k", "ses", "lado", "hi", "lo", "mid", "cuerpo", "rvol", "ancho", "er", "intento"])


def lineas_salida(ctx, salida: int) -> np.ndarray:
    m = minuto_ny(np.asarray(ctx["t"], np.int64)); f = (m >= salida) & (m < salida + 120)
    return np.vstack([np.where(f, np.inf, np.nan), np.where(f, -np.inf, np.nan)])


def _lote(D, ej, ctx):
    tick = float(ctx["tick"]); c = np.asarray(ctx["c"], float)
    k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64); e = c[k]
    ref = D["mid"].to_numpy(float) if ej[0] == "MID" else np.where(s == 1, D["lo"].to_numpy(float), D["hi"].to_numpy(float))
    st = np.where(s == 1, np.floor(ref / tick) * tick - tick, np.ceil(ref / tick) * tick + tick)
    R = (e - st) * s; ok = R >= tick
    if ej[1] == "SALIDA": tp = e + s * 1000.0 * tick; kl = (s == -1).astype(np.int64)
    else: tp = np.round((e + s * (1.0 if ej[1] == "1R" else 2.0) * R) / tick) * tick; kl = np.full(len(D), -1)
    return ok, k, s, e, st, tp, kl


def niveles(d, ej: tuple, ctx: dict):
    ok, k, s, e, st, tp, kl = _lote(pd.DataFrame([d]), ej, ctx)
    if not ok[0]: return None
    return (int(k[0]), 2, int(s[0]), float(e[0]), float(st[0]), float(tp[0]), 0, int(kl[0]), 0.0)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    out = np.full((len(D), 9), np.nan)
    if not len(D): return out
    ok, k, s, e, st, tp, kl = _lote(D, ej, ctx)
    out[ok] = np.column_stack([k, np.full(len(D), 2), s, e, st, tp, np.zeros(len(D)), kl, np.zeros(len(D))])[ok]
    return out
