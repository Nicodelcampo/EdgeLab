"""INTENTO-FALLIDO-HACIA (2026-11-03, Nico): profundizar la pista B80_HACIA de INTENTO-FALLIDO, con las piernas medidas.

Pedido de Nico: «agregar variables: cuánto se alejó desde que se creó la zona, cómo es la zona (nivel de comercio sobre ella), cuánto se
acercó luego de alejarse, cuánto se alejó luego de acercarse y cuánto se acercó otra vez; y cuántas velas tiene cada pierna (¿la cantidad de
velas de algún impulso cambia el resultado?); y probar varias lógicas de entrada». Pre-registro:
docs/research/intento_fallido_20261103/PREREGISTRO_IF_HACIA.md. Lógica base y tests en `intento_fallido`.

Las cuatro piernas, todas causales (medidas con velas <= la decisión) y en unidades del recorrido A (las distancias) o en velas M1 (las
duraciones; el motor de la grilla corre en M1, no en velas de 25 ticks: la duración en minutos es el reloj común a todas las fuentes):
  1. IDA:        de la zona al extremo E (U1: `A/H` y `dur_ida`);
  2. APROX:      del extremo al punto más cercano al objetivo sin tocarlo (`acerco` = 1 − dist/A, `dur_aprox`);
  3. RECHAZO:    del punto más cercano al extremo del rechazo (`rechazo` = cuánto se alejó / A, `dur_rech`);
  4. REACERC:    del extremo del rechazo a la decisión (la fracción r recuperada es la regla; `dur_reac`).
Zona: `vol_zona` = volumen medio por vela de las velas que tocan la zona entre su marca y el disparo de U1, relativo al de la sesión
anterior (cuánto se comerció sobre ella).

Entrada siempre HACIA la zona (la idea), decisión al cierre:
  - MERC: a mercado en el primer tick de la vela siguiente a la que recupera r;
  - CONF: espera una vela más que cierre también hacia la zona y entra en el tick siguiente;
  - LIM:  orden límite un 25 % del reacercamiento más atrás (mejor precio), vigente 120 velas.
Stop: un tick más allá del extremo del rechazo. TP: Z1/Z2/Z3 (borde cercano, medio, borde lejano de la zona) o 2R.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.eventos import TIPOS_TIER1
from edgelab.research.grilla_generica import Variable
from edgelab.research.intento_fallido import LIMITE, lineas_salida  # noqa: F401

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "INTENTO-FALLIDO-HACIA"
Y_CERCA, Z_RECH = 0.33, 0.10          # umbrales mínimos del evento (Nico: cuánto se acercó y cuánto rechazó van como VARIABLES, no como cortes)
RS = (0.5, 0.8, 1.0)                 # cuánto del rechazo recupera antes de entrar (1,0 = vuelve al punto más cercano)
EXCLUIR_EVENTOS = dict(antes_min=5, despues_min=5, tipos=TIPOS_TIER1)
LINEAS_SOLO_TIEMPO = True
VARIABLES = [
    Variable("r", "ri", "grupo", categoria=len(RS)),
    Variable("A/H", "A_H", "extremos", cuantiles=3),
    Variable("vol_zona", "vol_zona", "extremos", cuantiles=3),
    Variable("acerco", "acerco", "extremos", cuantiles=3),
    Variable("rechazo", "rechazo", "extremos", cuantiles=3),
    Variable("dur_ida", "dur_ida", "extremos", cuantiles=3),
    Variable("dur_aprox", "dur_aprox", "extremos", cuantiles=3),
    Variable("dur_rech", "dur_rech", "extremos", cuantiles=3),
    Variable("dur_reac", "dur_reac", "extremos", cuantiles=3),
]
EJES_ORDINALES = ()
ENTRADAS = ("MERC", "CONF", "LIM")
TPS = ("Z1", "Z2", "Z3", "2R")
EJECUCIONES = [(e, tp) for e in ENTRADAS for tp in TPS]
BASE = {"r": 1, "ejecución": 0}
VACIO = ["k", "ses", "lado", "ri", "A_H", "vol_zona", "acerco", "rechazo", "dur_ida", "dur_aprox", "dur_rech", "dur_reac",
         "stop_ref", "e_lim", "T", "mid", "lejos_zona", "k_lim"]


@njit(cache=False)
def _piernas(k0, d, T, A, h, l, c, ses, y_, z_, rs, limite):
    """Por aproximación: (i, ri, jB, j_best, j_far, best, far) del primer reacercamiento r tras un intento fallido (y_, z_ en unidades de A)."""
    out = []
    n = len(c)
    for i in range(len(k0)):
        di = d[i]; Ti = T[i]; Ai = A[i]; s0 = ses[k0[i]]; y = y_ * Ai; z = z_ * Ai
        best = np.inf; jbest = -1; far = 0.0; jfar = -1; cerca_ = False; jA = -1
        j = k0[i] + 1
        while j < n and j <= k0[i] + limite and ses[j] == s0:
            pc = l[j] if di == 1 else h[j]; pf = h[j] if di == 1 else l[j]
            dc = (pc - Ti) * di
            if dc <= 0.0: break
            if dc < best:
                best = dc; jbest = j; far = pf; jfar = j
            elif (pf - far) * di > 0:
                far = pf; jfar = j
            if best <= y: cerca_ = True
            if cerca_ and (c[j] - Ti) * di - best >= z:
                jA = j; break
            j += 1
        if jA < 0: continue
        dA = (c[jA] - Ti) * di
        for ri in range(len(rs)):
            meta = dA - rs[ri] * (dA - best); far2 = far; jfar2 = jfar; j = jA + 1
            while j < n and j <= k0[i] + limite and ses[j] == s0:
                pf = h[j] if di == 1 else l[j]; pc = l[j] if di == 1 else h[j]
                if (pc - Ti) * di <= 0.0: break                          # tocó el objetivo antes de decidir: tarde
                if (pf - far2) * di > 0:
                    far2 = pf; jfar2 = j
                if (c[j] - Ti) * di <= meta:
                    out.append((i, ri, j, jbest, jfar2, best, far2))
                    break
                j += 1
    return out


def construir(D: pd.DataFrame, ctx: dict) -> pd.DataFrame:
    if D is None or not len(D): return pd.DataFrame(columns=VACIO)
    D = D[D.xi == 0].drop_duplicates(["k", "lado", "lo", "hi"]).reset_index(drop=True)            # primer disparo de cada camino
    if not len(D): return pd.DataFrame(columns=VACIO)
    h, l, c, v = (np.asarray(ctx[x], float) for x in ("h", "l", "c", "v")); ses = np.asarray(ctx["ses"], np.int64)
    d = D.lado.to_numpy(np.int64); lo, hi = D.lo.to_numpy(float), D.hi.to_numpy(float)
    T = np.where(d == 1, hi, lo); LZ = np.where(d == 1, lo, hi); A = D.A.to_numpy(float); k0 = D.k.to_numpy(np.int64)
    # cómo es la zona: volumen medio por vela de las velas que la tocan entre su marca (m) y el disparo, sobre el de la sesión anterior
    rate = pd.Series(v).groupby(ses).mean(); us = np.array(sorted(rate.index))
    prev = pd.Series(np.r_[np.nan, rate.loc[us].to_numpy()[:-1]], index=us)
    m = D.m.to_numpy(np.int64) if "m" in D else k0 - 1
    vz = np.full(len(D), np.nan)
    for t in range(len(D)):
        a, b = max(int(m[t]), 0), int(k0[t]) + 1
        toca = (l[a:b] <= hi[t]) & (h[a:b] >= lo[t])
        base = prev.get(ses[k0[t]], np.nan)
        if toca.any() and base == base and base > 0: vz[t] = v[a:b][toca].mean() / base
    F = _piernas(k0, d, T, A, h, l, c, ses, Y_CERCA, Z_RECH, np.array(RS), LIMITE)
    if not len(F): return pd.DataFrame(columns=VACIO)
    F = np.array(F); i = F[:, 0].astype(np.int64); jB = F[:, 2].astype(np.int64); jb = F[:, 3].astype(np.int64); jf = F[:, 4].astype(np.int64)
    best, far = F[:, 5], F[:, 6]; Ti = T[i]; di = d[i]
    p_best = Ti + di * best
    reac = (far - c[jB]) * di                                            # cuánto recorrió el reacercamiento (en precio)
    dur_ida = D.dur_ida.to_numpy(float)[i] if "dur_ida" in D else np.full(len(i), np.nan)
    dur_v = D.dur_vuelta.to_numpy(float)[i] if "dur_vuelta" in D else np.zeros(len(i))
    X = pd.DataFrame(dict(
        k=jB, ses=ses[jB], lado=-di, ri=F[:, 1].astype(np.int64), A_H=D.A_H.to_numpy(float)[i], vol_zona=vz[i],
        acerco=1.0 - best / A[i], rechazo=(far - p_best) * di / A[i],
        dur_ida=dur_ida, dur_aprox=dur_v + (jb - k0[i]), dur_rech=(jf - jb).astype(float), dur_reac=(jB - jf).astype(float),
        stop_ref=far, e_lim=c[jB] + di * 0.25 * reac, T=Ti, mid=(lo[i] + hi[i]) / 2, lejos_zona=LZ[i], k_lim=jB))
    return X.sort_values(["k", "ri"], kind="stable", ignore_index=True)


def niveles(r, ej, ctx):
    """9 valores (entrada, stop estructural, TP; línea de noticias). Siempre hacia la zona: s = lado."""
    en, tp_ = ej; s = int(r["lado"]); k = int(r["k"]); tick = float(ctx["tick"]); c = ctx["c"]; start, lim, e = k, 2, float(c[k])
    if en == "CONF":
        if k + 1 >= len(c) or ctx["ses"][k + 1] != ctx["ses"][k] or (c[k + 1] - c[k]) * s <= 0: return None
        start, e = k + 1, float(c[k + 1])
    elif en == "LIM":
        lim, e = 1, float(np.round(r["e_lim"] / tick) * tick)
        if (c[k] - e) * s < tick: return None                                # el límite tiene que quedar detrás del precio
    st = r["stop_ref"] + (-s) * tick
    st = np.floor(st / tick) * tick if s == 1 else np.ceil(st / tick) * tick
    R = (e - st) * s
    if R < tick: return None
    tp = e + s * 2.0 * R if tp_ == "2R" else {"Z1": r["T"], "Z2": r["mid"], "Z3": r["lejos_zona"]}[tp_]
    tp = np.round(tp / tick) * tick
    if (tp - e) * s < tick: return None
    return start, lim, s, e, st, tp, 0, (0 if s == 1 else 1), 0.0
