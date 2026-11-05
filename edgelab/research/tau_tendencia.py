"""TAU-TENDENCIA (2026-10-31): la regla de tendencia del paper de Tori Trades medida tal cual, con salida por tiempo de parada.

Fuente: "The Trend Is Your Friend Until the End: A Stopping-Time Theory of Swing Trading" (Tori Trades, 26-oct-2026), Definiciones
3.1–3.2, Proposiciones 3.4–3.6. Pre-registro: docs/research/paquete_20261031/SPEC_TAU_TENDENCIA.md.

Hipótesis económica: una línea de tendencia por los dos últimos pivotes es una señal de momentum adaptativo (Prop. 3.4): se mantiene la
posición mientras el rendimiento desde el último pivote supera la pendiente de la tendencia. La persistencia viene de la reacción
lenta a la información y del efecto disposición (vender ganadores temprano); la regla es su opuesto mecánico. El aporte para EdgeLab es
el PAGO: salir sólo cuando la estructura se rompe (τ) deja correr las ganancias, al revés de las reglas con acta, que ganan seguido
poco y pierden de a mucho (W/L 0,23–0,35 en la auditoría externa del PR #162).

Construcción (causal; todo lo de la vela k se conoce a su cierre; pivotes y líneas se reinician en cada sesión):
  - Pivote de orden p: la vela i−p es máximo (mínimo) de [i−2p, i] y supera estrictamente a las p velas anteriores; se confirma en i.
  - Estructura alcista: los dos últimos máximos y los dos últimos mínimos confirmados suben; bajista: bajan (Def. 3.1).
  - Línea de soporte en la vela j: recta por los dos últimos mínimos confirmados hasta j si suben; si no, horizontal en el último
    mínimo (Def. 3.2). Resistencia, simétrica. La línea se mueve cuando se confirma un pivote nuevo: es un stop de estructura.
  - Disparos: ESTRUCTURA (la estructura pasa a alcista/bajista en la vela k) y RUPTURA (con estructura alcista, primer cierre sobre el
    último máximo confirmado: el caso horizontal de la Prop. 3.4; simétrico abajo).
  - Salida TAU: primer cierre del lado equivocado de la línea, con margen δ = {0; 0,5; 1} × ATR14 de la vela de entrada
    (`areas_expansion.simular_cierre_linea`). Stop duro: el último pivote del lado contrario − 1 tick. Sin objetivo (lejano), con el
    tope de 240 velas y el fin de sesión del simulador. Control dentro de la familia: FIJO_2R (mismo stop, objetivo 2R, sin línea).
Perillas: orden de pivote (3, 5, 8), tipo de disparo, ángulo normalizado θ̃ = arctan(β̂/σ̂) a favor (terciles; Prop. 3.5), t de
Newey-West de los retornos a favor (≥ 1, ≥ 2; Prop. 3.6, nunca el t de la regresión en niveles) y ER de 60 velas de la sesión.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable
from edgelab.research.regimen_sesion import er_sesion
from edgelab.research.zonas_gaps import _atr_causal

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "TAU-TENDENCIA"
INDICADORES = ["TAU-TENDENCIA"]
ORDENES = (3, 5, 8)
W = 60                                                        # ventana de θ̃, t_NW y ER (velas de la sesión)

VARIABLES = [
    Variable("orden_pivote", "op", "grupo", categoria=3),
    Variable("disparo", "tipo", "grupo", categoria=2),                       # 0 ESTRUCTURA · 1 RUPTURA
    Variable("angulo_norm", "theta", "extremos", cuantiles=3),               # θ̃ a favor de la operación, terciles del E0
    Variable("t_nw", "tnw", "ge", cortes=(1.0, 2.0)),                        # cualquiera / ≥ 1 / ≥ 2 a favor
    Variable("eficiencia", "er", "ge", cortes=(0.25, 0.42)),                 # cualquiera / ≥ 0,25 / ≥ 0,42
]
EJES_ORDINALES = (3, 4)
EJECUCIONES = [("TAU", 0.0), ("TAU", 0.5), ("TAU", 1.0), ("FIJO_2R", None)]
BASE = {"orden_pivote": 1, "disparo": 0, "angulo_norm": 2, "t_nw": 0, "eficiencia": 0, "ejecución": 1}


@njit(cache=False)
def _estructura_nb(h, l, c, ses, p):
    """Una pasada por orden p: líneas de soporte/resistencia por vela y disparos (k, lado, tipo, stop)."""
    n = len(c)
    sup = np.full(n, np.nan); res = np.full(n, np.nan)
    dk = np.empty(n, np.int64); ds = np.empty(n, np.int64); dt = np.empty(n, np.int64); dst = np.empty(n)
    m = 0; ini = 0
    th1 = -1; vh1 = 0.0; th2 = -1; vh2 = 0.0; tl1 = -1; vl1 = 0.0; tl2 = -1; vl2 = 0.0
    est = 0; rot_h = -1; rot_l = -1
    for i in range(n):
        if i == 0 or ses[i] != ses[i - 1]:
            ini = i; th1 = -1; th2 = -1; tl1 = -1; tl2 = -1; est = 0; rot_h = -1; rot_l = -1
        q = i - p
        if q - p >= ini:
            esmax = True; esmin = True
            for j in range(q - p, i + 1):
                if j < q:
                    if h[j] >= h[q]: esmax = False
                    if l[j] <= l[q]: esmin = False
                elif j > q:
                    if h[j] > h[q]: esmax = False
                    if l[j] < l[q]: esmin = False
            if esmax:
                th1 = th2; vh1 = vh2; th2 = q; vh2 = h[q]; rot_h = -1
            if esmin:
                tl1 = tl2; vl1 = vl2; tl2 = q; vl2 = l[q]; rot_l = -1
        if tl2 >= 0:
            sup[i] = vl2 + (vl2 - vl1) / (tl2 - tl1) * (i - tl2) if (tl1 >= 0 and vl2 > vl1) else vl2
        if th2 >= 0:
            res[i] = vh2 + (vh2 - vh1) / (th2 - th1) * (i - th2) if (th1 >= 0 and vh2 < vh1) else vh2
        nuevo = 0
        if th1 >= 0 and tl1 >= 0:
            if vh2 > vh1 and vl2 > vl1: nuevo = 1
            elif vh2 < vh1 and vl2 < vl1: nuevo = -1
        if nuevo != 0 and nuevo != est:
            dk[m] = i; ds[m] = nuevo; dt[m] = 0; dst[m] = vl2 if nuevo == 1 else vh2; m += 1
        est = nuevo
        if est == 1 and th2 >= 0 and rot_h != th2 and c[i] > vh2 and (i == 0 or c[i - 1] <= vh2):
            dk[m] = i; ds[m] = 1; dt[m] = 1; dst[m] = vl2; m += 1; rot_h = th2
        if est == -1 and tl2 >= 0 and rot_l != tl2 and c[i] < vl2 and (i == 0 or c[i - 1] >= vl2):
            dk[m] = i; ds[m] = -1; dt[m] = 1; dst[m] = vh2; m += 1; rot_l = tl2
    return sup, res, dk[:m], ds[:m], dt[:m], dst[:m]


def _cache(ctx):
    """Las tres pasadas (una por orden) se calculan una vez por contexto."""
    key = ("_tau", id(ctx["c"]))
    if ctx.get("_tau_key") != key:
        h, l, c = (np.asarray(ctx[x], np.float64) for x in ("h", "l", "c")); ses = np.asarray(ctx["ses"], np.int64)
        ctx["_tau"] = [_estructura_nb(h, l, c, ses, p) for p in ORDENES]; ctx["_tau_key"] = key
    return ctx["_tau"]


def lineas_salida(ctx) -> np.ndarray:
    """Filas 2·o (soporte) y 2·o + 1 (resistencia) para cada orden o."""
    return np.vstack([np.vstack([r[0], r[1]]) for r in _cache(ctx)])


def _theta_tnw(c, ses, k, s):
    """θ̃ = arctan(β̂/σ̂) y t de Newey-West de los retornos de las últimas W velas de la sesión, firmados a favor de la operación."""
    if k - W < 0 or ses[k - W] != ses[k]: return np.nan, np.nan
    x = c[k - W:k + 1]; r = np.diff(x); sd = r.std(ddof=1)
    if not sd > 0: return np.nan, np.nan
    tt = np.arange(len(x)); beta = np.polyfit(tt, x, 1)[0]
    u = r - r.mean(); L = int(np.floor(4 * (len(r) / 100.0) ** (2 / 9)))
    om = (u @ u) / len(r)
    for j in range(1, L + 1): om += 2 * (1 - j / (L + 1)) * (u[j:] @ u[:-j]) / len(r)
    tnw = r.mean() / np.sqrt(om / len(r)) if om > 0 else np.nan
    return float(np.arctan(s * beta / sd)), float(s * tnw)


def disparos(ctx: dict) -> pd.DataFrame:
    c = np.asarray(ctx["c"], np.float64); ses = np.asarray(ctx["ses"], np.int64)
    atr = _atr_causal(np.asarray(ctx["h"], float), np.asarray(ctx["l"], float), c); er = er_sesion(c, ses, W)
    filas = []
    for o, (_, _, dk, ds, dt, dst) in enumerate(_cache(ctx)):
        for k, s, tp, st in zip(dk, ds, dt, dst):
            th, tn = _theta_tnw(c, ses, int(k), int(s))
            filas.append((int(k), int(ses[k]), o, int(tp), int(s), float(st), th, tn, float(er[k]), float(atr[k])))
    D = pd.DataFrame(filas, columns=["k", "ses", "op", "tipo", "lado", "stop_piv", "theta", "tnw", "er", "atr"])
    return D.sort_values(["k", "op", "tipo"], kind="stable").reset_index(drop=True)


def _lote(D, ej, ctx):
    tick = float(ctx["tick"]); c = np.asarray(ctx["c"], float)
    k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64); e = c[k]
    st = np.where(s == 1, np.floor(D["stop_piv"].to_numpy(float) / tick) * tick - tick, np.ceil(D["stop_piv"].to_numpy(float) / tick) * tick + tick)
    R = (e - st) * s; atr = D["atr"].to_numpy(float)
    ok = (R >= tick) & np.isfinite(atr)
    if ej[0] == "TAU":
        tp = e + s * 1000.0 * tick; kl = 2 * D["op"].to_numpy(np.int64) + (s == -1); dl = ej[1] * atr
    else:
        tp = np.round((e + s * 2.0 * R) / tick) * tick; kl = np.full(len(D), -1); dl = np.zeros(len(D))
    return ok, k, s, e, st, tp, kl, dl


def niveles(d, ej: tuple, ctx: dict):
    ok, k, s, e, st, tp, kl, dl = _lote(pd.DataFrame([d]), ej, ctx)
    if not ok[0]: return None
    return (int(k[0]), 2, int(s[0]), float(e[0]), float(st[0]), float(tp[0]), 0, int(kl[0]), float(dl[0]))


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    out = np.full((len(D), 9), np.nan)
    if not len(D): return out
    ok, k, s, e, st, tp, kl, dl = _lote(D, ej, ctx)
    out[ok] = np.column_stack([k, np.full(len(D), 2), s, e, st, tp, np.zeros(len(D)), kl, dl])[ok]
    return out
