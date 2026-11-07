"""ESPEJO-REGLA — la orden del espejo, sin los umbrales que el censo tenía clavados.

El censo sigue en `edgelab/bridge/indicators/espejo_impulsos.py`. Acá no se usa su percentil,
ni la etiqueta `ineficiente`, ni el nulo f. Cada fila es el primer cierre que cruza una
fracción declarada del retroceso, y la grilla corta eficiencia, volumen por tick y
semejanza sobre el E0 de la misma fuente.

Orden, una sola:
- entrada a mercado en la vela siguiente (el tick siguiente del simulador);
- stop un tick más allá de B;
- objetivo en A;
- tenencia máxima 60 velas de 1 minuto (3 × el máximo del detector) o fin de sesión.

Población: impulsos confirmados por retroceso 0,3·W, eficiencia mínima 0,3, ancho mínimo
17 ticks, en la sesión CME completa. RTH (09:30–16:00 ET) es una perilla, no un filtro
elegido después. La dirección de la orden es la de la vuelta, no la del impulso.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from edgelab.bridge.indicators.espejo_impulsos import detect, params_of, semejanza_niveles, _tramo_espejo
from edgelab.research.grilla_generica import Variable
from edgelab.research.regimen_sesion import minuto_ny

NOMBRE = "ESPEJO-REGLA"
INDICADORES = ["ESPEJO-REGLA"]
PREFLIGHT_T0_S = 1_760_047_200
MIN_W_TICKS = 17.0
ENTRADAS = (0.25, 0.50)
TOPE_BARRAS = 60
RTH = (570, 960)
VARIABLES = [
    Variable("eficiencia", "eff", "extremos", cuantiles=3),
    Variable("volumen_por_tick", "vpt", "extremos", cuantiles=3),
    Variable("semejanza", "sim", "extremos", cuantiles=3),
    Variable("direccion", "dir_cat", "grupo", categoria=2),
    Variable("entrada", "x_cat", "grupo", categoria=2),
    Variable("solo_rth", "rth", "ge", cortes=(0.5,)),
]
EJES_ORDINALES = (0, 1, 2)
EJECUCIONES = [("A",)]
BASE = {"eficiencia": 2, "volumen_por_tick": 2, "semejanza": 2, "direccion": 0, "entrada": 0, "solo_rth": 0, "ejecución": 0}
VACIO = ["k", "ses", "lado", "eff", "vpt", "sim", "dir_cat", "x_cat", "rth", "B", "A"]


def lineas_salida(ctx) -> np.ndarray:
    """Sin línea de precio: la salida por tiempo es el tope de 60 velas y el fin de sesión del simulador."""
    return np.full((1, len(ctx["c"])), np.nan)


def _params(tick: float) -> dict:
    return params_of(dict(max_bars=20, min_w=MIN_W_TICKS * float(tick), atr_k=None, e_min=0.3, retr=0.3, npts=20))


def disparos(ctx: dict) -> pd.DataFrame:
    H, L, C, V = (np.asarray(ctx[x], float) for x in ("h", "l", "c", "v"))
    t = np.asarray(ctx["t"], float); ses = np.asarray(ctx["ses"], np.int64); m = minuto_ny(t)
    p = _params(ctx["tick"]); n = len(C); filas = []
    if n < 30: return pd.DataFrame(columns=VACIO)
    cuts = np.r_[0, np.where(ses[1:] != ses[:-1])[0] + 1, n]
    for a0, b0 in zip(cuts[:-1], cuts[1:]):
        sl = slice(a0, b0)
        for im in detect(t[sl], H[sl], L[sl], C[sl], V[sl], np.full(b0 - a0, p["min_w"]), p):
            if im["why"] != 1: continue
            d, a, ext = im["d"], im["a"], im["ext"]; W = abs(ext - a)
            if not W > 0: continue
            i0, iext, jc = im["i0"], im["iext"], im["jconf"]
            horizon = iext + int(math.ceil(p["horizon_mult"] * (iext - i0 + 1)))
            visto = set(); eff = float(im["eff"]); vpt = float(im["vol"] / W)
            for j in range(iext + 1, b0 - a0):
                if j > horizon: break
                nuevo = (d == 1 and H[a0 + j] > ext) or (d == -1 and L[a0 + j] < ext)
                retr = (ext - L[a0 + j]) if d == 1 else (H[a0 + j] - ext)
                f = min(max(retr, 0.0) / W, 1.0)
                if nuevo: break
                barra = max(j, jc)
                if barra >= b0 - a0: break
                for xi, x in enumerate(ENTRADAS):
                    if xi in visto or f < x or f >= 1.0: continue
                    visto.add(xi)
                    gk = a0 + barra
                    base = dict(d=d, a=a, ext=ext, i0=a0 + i0, iext=a0 + iext)
                    base["m"] = _tramo_espejo(C, base, f)
                    sim = float(semejanza_niveles(t, H, L, V, base, a0 + j, f, a0, p)["sim_abs"])
                    lado = -int(d)
                    filas.append((gk, int(ses[gk]), lado, eff, vpt, sim, 0 if lado == 1 else 1, xi,
                                  1 if RTH[0] <= int(m[gk]) <= RTH[1] else 0, float(ext), float(a)))
                if f >= 1.0 or len(visto) == len(ENTRADAS): break
    return pd.DataFrame(filas, columns=VACIO) if filas else pd.DataFrame(columns=VACIO)


def _lote(D, ctx):
    tick = float(ctx["tick"]); k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64)
    e = np.asarray(ctx["c"], float)[k]; B = D["B"].to_numpy(float); A = D["A"].to_numpy(float)
    st = np.where(s == 1, np.floor(B / tick) * tick - tick, np.ceil(B / tick) * tick + tick)
    tp = np.where(s == 1, np.ceil(A / tick) * tick, np.floor(A / tick) * tick)
    ok = ((e - st) * s >= tick) & ((tp - e) * s >= tick)
    return ok, k, s, e, st, tp


def niveles(d, ej: tuple, ctx: dict):
    ok, k, s, e, st, tp = _lote(pd.DataFrame([d]), ctx)
    if not ok[0]: return None
    return (int(k[0]), 2, int(s[0]), float(e[0]), float(st[0]), float(tp[0]), 0, -1, 0.0)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    out = np.full((len(D), 9), np.nan)
    if not len(D): return out
    ok, k, s, e, st, tp = _lote(D, ctx)
    if ok.any():
        out[ok] = np.column_stack([k[ok], np.full(int(ok.sum()), 2), s[ok], e[ok], st[ok], tp[ok],
                                   np.zeros(int(ok.sum())), np.full(int(ok.sum()), -1), np.zeros(int(ok.sum()))])
    return out
