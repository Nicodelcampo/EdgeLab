"""ESPEJO-PICOS2 (2026-11-07, pedido de Nico: «definiciones nuevas de picos que sean distintas entre sí»): el espejo clasificado por qué
picos tomó la ida, con cuatro definiciones de pico que miden cosas distintas. Hermana de ESPEJO-PICOS (pivote de w velas) y de
ESPEJO-ZONAS: misma base de eventos (detector causal con topes en tiempo, ancho laxo de 5 viajes), mismas ejecuciones y las mismas
preguntas sobre la ida (cuántos tomó, dónde, cuánto los pasó, si quedan), con la antigüedad en los cortes de 30 y 120 min de Nico.

Todo en el espacio «techo» x (h si la ida sube; −l si baja), con su «piso» y (l si sube; −h si baja) para medir reversiones:
  - ZIGZAG (amplitud): extremo confirmado cuando el precio revierte >= R desde él (R = 2 o 5 viajes de fricción severa). Mide el
    tamaño del movimiento que lo dejó, no la cantidad de velas.
  - IGUALES (pool de stops): pivote de 3 velas con otro pivote anterior de la misma sesión a <= tol (0,1 o 0,4 viajes de fricción: 1 y 4 ticks en NQ), sin
    que el precio haya pasado los dos en el medio. Nivel = el mayor de los dos. Los techos/pisos dobles son donde se juntan stops.
  - MECHA (rechazo): pivote de 3 velas cuya vela tiene una mecha del lado del pico >= 40 % o 60 % de su rango. Mide rechazo, no forma.
  - HORARIO (reloj): extremo de cada ventana de reloj de 15 o 60 min, confirmado al cerrar la ventana. Independiente de la forma.
Un pico cuenta si está confirmado hasta A, es de la misma sesión que A (roll), está más allá de A y sigue SIN ROMPER hasta A (ninguna
mecha lo pasó entre el pico y A). Antigüedad = tiempo del pico a A: <= 30 min · 30–120 min · > 120 min · todos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import espejo_macro_grilla as P, espejo_macro_tiempo as TI
from edgelab.research.espejo_picos import EJECUCIONES, STOPS, TPS, _pivotes, niveles  # noqa: F401
from edgelab.research.espejo_zonas import _primer_cruce
from edgelab.research.grilla_generica import Variable
from edgelab.research.intento_fallido import EXCLUIR_EVENTOS, lineas_salida  # noqa: F401

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "ESPEJO-PICOS2"
INDICADORES = ["ESPEJO-MACRO-10T"]
LINEAS_SOLO_TIEMPO = True
TOPE_BARRAS = P.TOPE_BARRAS
VIAJES_LAXO = 5.0
TIPOS = ("ZIGZAG", "IGUALES", "MECHA", "HORARIO")
ESCALAS = {"ZIGZAG": (2.0, 5.0),        # R en viajes de fricción severa
           "IGUALES": (0.10, 0.40),     # tolerancia en viajes de fricción severa (NQ: 1 y 4 ticks)
           "MECHA": (0.40, 0.60),       # mecha del lado del pico / rango de la vela
           "HORARIO": (900.0, 3600.0)}  # ventana de reloj en segundos
W_PIVOTE = 3
EDAD_CORTES_S = (1800.0, 7200.0)
BANDAS = 4                              # 0 <= 30 min · 1 30–120 · 2 > 120 · 3 todos
VARIABLES = [
    Variable("fraccion", "fi", "grupo", categoria=len(P.FRACCIONES)),
    Variable("viajes", "viajes", "ge", cortes=(5.0, 10.0, 20.0), piso=True),
    Variable("rth", "rth", "eq_any", categoria=2),
    Variable("tipo_pico", "ti", "grupo", categoria=len(TIPOS)),
    Variable("escala_pico", "ei", "grupo", categoria=2),
    Variable("antiguedad", "ai", "grupo", categoria=BANDAS),
    Variable("n_tomados", "n_tom", "eq_any", cortes=(0.5, 2.5)),
    Variable("posicion", "pos", "eq_any", categoria=4),
    Variable("sobrepaso", "sobre", "eq_any", categoria=4),
    Variable("quedan", "quedan", "eq_any", categoria=2),
]
EJES_ORDINALES = ()
BASE = {"fraccion": 1, "viajes": 1, "rth": 2, "tipo_pico": 0, "escala_pico": 0, "antiguedad": 3, "n_tomados": 3, "posicion": 4,
        "sobrepaso": 4, "quedan": 2, "ejecución": 0}


# ---------------------------------------------------------------- definiciones: cada una devuelve (q, conf, val) ordenado por conf
@njit(cache=False)
def _zigzag(x, y, ses, R):
    """Picos de zigzag: extremo de x confirmado en la primera vela cuyo piso y cae >= R desde él; luego se espera una suba >= R desde
    el mínimo para volver a buscar techo. Dentro de la sesión."""
    n = len(x); Q = []; Cf = []; V = []
    if n == 0: return np.array(Q, np.int64), np.array(Cf, np.int64), np.array(V, np.float64)
    modo = 1; ext = x[0]; iext = 0; mn = y[0]
    for j in range(1, n):
        if ses[j] != ses[j - 1]:
            modo = 1; ext = x[j]; iext = j; mn = y[j]; continue
        if modo == 1:
            if x[j] > ext: ext = x[j]; iext = j
            elif ext - y[j] >= R:
                Q.append(iext); Cf.append(j); V.append(ext); modo = -1; mn = y[j]
        else:
            if y[j] < mn: mn = y[j]
            if x[j] - mn >= R: modo = 1; ext = x[j]; iext = j
    return np.array(Q, np.int64), np.array(Cf, np.int64), np.array(V, np.float64)


@njit(cache=False)
def _iguales(x, ses, piv, w, tol, max_prev):
    """Pivotes (confirmados en q + w) con un pivote anterior de la misma sesión a <= tol y sin que el precio haya pasado el mayor de
    los dos entre ambos. Nivel = el mayor."""
    idx = np.flatnonzero(piv); Q = []; Cf = []; V = []
    for a in range(len(idx)):
        q = idx[a]
        for b in range(a - 1, max(-1, a - 1 - max_prev), -1):
            p = idx[b]
            if ses[p] != ses[q]: break
            if abs(x[q] - x[p]) > tol: continue
            top = max(x[q], x[p]); ok = True
            for j in range(p + 1, q):
                if x[j] > top: ok = False; break
            if ok:
                Q.append(q); Cf.append(q + w); V.append(top); break
    return np.array(Q, np.int64), np.array(Cf, np.int64), np.array(V, np.float64)


def _mecha(x, ses, piv, w, cuerpo_alto, rango, frac):
    """Pivotes cuya vela tiene mecha del lado del pico (x − max(o, c) en espacio techo) >= frac del rango."""
    q = np.flatnonzero(piv & (rango > 0) & ((x - cuerpo_alto) >= frac * np.where(rango > 0, rango, 1.0)))
    return q.astype(np.int64), (q + w).astype(np.int64), x[q].astype(float)


def _horario(x, T, ses, ventana):
    """Extremo de x en cada ventana de reloj completa [m·v, (m+1)·v) de la sesión; confirmado en la primera vela de la ventana siguiente."""
    blo = np.floor(T / ventana).astype(np.int64); n = len(x)
    corte = np.r_[True, (blo[1:] != blo[:-1]) | (ses[1:] != ses[:-1])]; ini = np.flatnonzero(corte); fin = np.r_[ini[1:], n]
    Q, Cf = [], []
    for a, b in zip(ini, fin):
        if b >= n or ses[b] != ses[a]: continue                  # ventana sin cerrar dentro de la sesión
        Q.append(a + int(np.argmax(x[a:b]))); Cf.append(b)
    Q = np.array(Q, np.int64); return Q, np.array(Cf, np.int64), x[Q].astype(float) if len(Q) else np.zeros(0)


# ---------------------------------------------------------------- clasificación
@njit(cache=False)
def _clasificar(q, conf, val, brk, ses, T, i0, ie, A, techo, c1, c2):
    """Picos (ordenados por conf) contra la ida. Devuelve, por banda (4), (n_tomados, pos_media, sobre, n_quedan)."""
    W = techo - A; out = np.zeros((BANDAS, 4)); out[:, 1] = -1.0; out[:, 2] = -1.0
    if W <= 0: return out
    n_t = np.zeros(BANDAS); sp = np.zeros(BANDAS); ult = np.full(BANDAS, -1e18); n_q = np.zeros(BANDAS)
    hi = np.searchsorted(conf, i0, side="right")
    for u in range(hi - 1, -1, -1):
        p = q[u]
        if ses[p] != ses[i0]: break                              # todas confirman dentro de su sesión: lo anterior es de otra
        if val[u] <= A or brk[u] < i0: continue                  # detrás de A, o roto antes de A
        edad = T[i0] - T[p]
        b0 = 0 if edad <= c1 else (1 if edad <= c2 else 2)
        for b in (b0, 3):
            if val[u] <= techo:
                n_t[b] += 1; sp[b] += (val[u] - A) / W
                if val[u] > ult[b]: ult[b] = val[u]
            else: n_q[b] += 1
    for b in range(BANDAS):
        out[b, 0] = n_t[b]; out[b, 3] = n_q[b]
        if n_t[b] > 0: out[b, 1] = sp[b] / n_t[b]; out[b, 2] = (techo - ult[b]) / W
    return out


def _conjuntos(ctx, fr):
    """{(lado, tipo, escala): (q, conf, val, brk)} en ticks, con brk = primera vela posterior al pico cuya mecha lo pasa."""
    tick = float(ctx["tick"]); T = np.asarray(ctx["t"], float); ses = np.asarray(ctx["ses"], np.int64)
    h = np.asarray(ctx["h"], float) / tick; l = np.asarray(ctx["l"], float) / tick
    o = np.asarray(ctx["o"], float) / tick; c = np.asarray(ctx["c"], float) / tick
    out = {}
    for lado in (1, -1):
        x, y = (h, l) if lado == 1 else (-l, -h)
        cuerpo = np.maximum(o, c) if lado == 1 else np.maximum(-o, -c)
        piv = _pivotes(x, ses, W_PIVOTE)
        for ti, tipo in enumerate(TIPOS):
            for ei, e in enumerate(ESCALAS[tipo]):
                if tipo == "ZIGZAG": q, cf, v = _zigzag(x, y, ses, e * fr)
                elif tipo == "IGUALES": q, cf, v = _iguales(x, ses, piv, W_PIVOTE, e * fr, 50)
                elif tipo == "MECHA": q, cf, v = _mecha(x, ses, piv, W_PIVOTE, cuerpo, h - l, e)
                else: q, cf, v = _horario(x, T, ses, e)
                o_ = np.argsort(cf, kind="stable"); q, cf, v = q[o_], cf[o_], v[o_]
                out[(lado, ti, ei)] = (q, cf, v, _primer_cruce(x, q, v, True))
    return out


def disparos(ctx) -> pd.DataFrame:
    tick = float(ctx["tick"]); C = np.asarray(ctx["c"], float) / tick; ses = np.asarray(ctx["ses"], np.int64)
    h = np.asarray(ctx["h"], float) / tick; l = np.asarray(ctx["l"], float) / tick; T = np.asarray(ctx["t"], float)
    fr = P._friccion_ticks(ctx); min_w = 2.0 * VIAJES_LAXO * fr
    conj = _conjuntos(ctx, fr); filas = []
    for fi, f in enumerate(P.FRACCIONES):
        for (i0, ie, k, lado, W, ri, rv) in TI._detectar_t(C, T, ses, P.RETRO_LAXO, f, min_w, P.MIN_IDA, P.MIN_VUELTA,
                                                           TI.MAX_SEG_IDA, TI.MAX_SEG_TOTAL):
            i0, ie, k, lado = int(i0), int(ie), int(k), int(lado)
            if lado == 1: A = l[i0]; techo = h[i0:ie + 1].max()
            else: A = -h[i0]; techo = (-l[i0:ie + 1]).max()
            for ti in range(len(TIPOS)):
                for ei in range(2):
                    q, cf, v, brk = conj[(lado, ti, ei)]
                    R = _clasificar(q, cf, v, brk, ses, T, i0, ie, A, techo, *EDAD_CORTES_S)
                    for ai in range(BANDAS):
                        n_t, pos, sob, n_q = R[ai]
                        filas.append((k, -lado, fi, W / 2.0 / fr, ti, ei, ai, int(n_t),
                                      0 if n_t == 0 else (1 if pos < 1 / 3 else (2 if pos < 2 / 3 else 3)),
                                      0 if n_t == 0 else (1 if sob <= 0.10 else (2 if sob <= 0.25 else 3)),
                                      1 if n_q > 0 else 0, C[i0] * tick, C[ie] * tick, W * tick))
    cols = ["k", "lado", "fi", "viajes", "ti", "ei", "ai", "n_tom", "pos", "sobre", "quedan", "A", "B", "W"]
    if not filas: return pd.DataFrame(columns=cols + ["rth", "ses"])
    D = pd.DataFrame(filas, columns=cols)
    from edgelab.research.regimen_sesion import minuto_ny
    mny = minuto_ny(T[D.k.to_numpy()].astype(np.int64))
    D["rth"] = ((mny >= P.RTH_INI) & (mny < P.RTH_FIN)).astype(np.int64); D["ses"] = ses[D.k.to_numpy()]
    return D.sort_values(["k", "fi", "ti", "ei", "ai"], kind="stable", ignore_index=True)
