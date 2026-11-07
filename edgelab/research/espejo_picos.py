"""ESPEJO-PICOS (2026-11-07, hipótesis de Nico): el espejo de ESPEJO-MACRO-10T clasificado por QUÉ PICOS TOMÓ LA IDA.

Hipótesis: si el primer impulso existió para tomar picos de liquidez, cuando los tomó el motivo desapareció y la vuelta completa el
espejo o va más allá de A. Familia hija de ESPEJO_MACRO_10T (linaje): mismo detector causal (`espejo_macro_grilla._detectar`, umbrales
laxos), sin tocar el módulo padre, y las perillas de retroceso del padre quedan fijas en el valor laxo.

Pico = pivote del lado del impulso (máximos si sube, mínimos si baja) de `w` velas por lado, confirmado `w` velas después y ANTES del
inicio A, que sigue SIN ROMPER hasta A (liquidez viva). Los picos sin romper forman por construcción una escalera (cada uno no supera al
anterior), como en `tools/peaks_rule.py`. Dos definiciones (perilla, decisión de Nico «los dos»):
  - CUALQUIERA: todo pico vivo dentro de LOOK velas antes de A;
  - CONSECUTIVO: sólo los que forman series de >= 3 con separación <= MAX_GAP velas entre picos seguidos (el pool de liquidez).
Dos escalas de pivote (w = 3 y w = 10 velas de 10 ticks). Todo se mide en la vela de decisión k con datos <= k.

Qué tomó la ida (extremo de la ida por mechas, de A al extremo B):
  - n_tom: picos tomados (entre A y el extremo de la ida);
  - pos: dónde estaban dentro del impulso (0 ninguno · 1 inicio · 2 medio · 3 final, por la posición media);
  - sobre: cuánto pasó el extremo al último pico tomado, en fracción de W (0 ninguno · 1 <= 0,10 · 2 <= 0,25 · 3 más);
  - quedan: picos vivos más allá del extremo que la ida NO tomó (0 · 1 o más): liquidez que queda del lado del impulso.
Ejecuciones: stop en B (1 tick o 10 % de W) × objetivo A, 1,25·W, 1,5·W (más allá de A, la hipótesis) o 2R.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import espejo_macro_grilla as P
from edgelab.research.grilla_generica import Variable
from edgelab.research.intento_fallido import EXCLUIR_EVENTOS, lineas_salida  # noqa: F401

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "ESPEJO-PICOS"
INDICADORES = ["ESPEJO-MACRO-10T"]
LINEAS_SOLO_TIEMPO = True
TOPE_BARRAS = P.TOPE_BARRAS
ESCALAS = (3, 10)                     # w del pivote, en velas de 10 ticks
LOOK = 2000                           # velas hacia atrás desde A para buscar picos vivos
MAX_GAP = (60, 200)                   # separación máxima entre picos seguidos de una serie, por escala
N_SERIE = 3
VARIABLES = [
    Variable("fraccion", "fi", "grupo", categoria=len(P.FRACCIONES)),
    Variable("viajes", "viajes", "ge", cortes=(10.0, 20.0, 40.0), piso=True),
    Variable("rth", "rth", "eq_any", categoria=2),
    Variable("tipo_pico", "ti", "grupo", categoria=2),            # 0 cualquiera · 1 consecutivo
    Variable("escala_pico", "ei", "grupo", categoria=2),          # 0 w = 3 · 1 w = 10
    Variable("n_tomados", "n_tom", "eq_any", cortes=(0.5, 2.5)),  # 0 · 1–2 · 3+ · cualquiera
    Variable("posicion", "pos", "eq_any", categoria=4),
    Variable("sobrepaso", "sobre", "eq_any", categoria=4),
    Variable("quedan", "quedan", "eq_any", categoria=2),
]
EJES_ORDINALES = ()
STOPS = ("B1", "B10")
TPS = ("A", "A125", "A150", "2R")
EJECUCIONES = [(sl, tp) for sl in STOPS for tp in TPS]
BASE = {"fraccion": 1, "viajes": 1, "rth": 2, "tipo_pico": 0, "escala_pico": 0, "n_tomados": 3, "posicion": 4, "sobrepaso": 4,
        "quedan": 2, "ejecución": 0}


@njit(cache=False)
def _pivotes(x, ses, w):
    """Pivotes de máximo de `x` (para mínimos se pasa −l), dentro de la sesión; el de q se confirma en q + w."""
    n = len(x); piv = np.zeros(n, np.bool_)
    for q in range(w, n - w):
        if ses[q - w] != ses[q] or ses[q + w] != ses[q]: continue
        ok = True
        for o in range(1, w + 1):
            if x[q] < x[q - o] or x[q] < x[q + o]: ok = False; break
        piv[q] = ok
    return piv


@njit(cache=False)
def _clasificar(x, piv, w, i0, ie, A, look, max_gap, consecutivo):
    """En el espacio «techo» (x = h si el impulso sube, −l si baja): picos vivos antes de A, cuáles tomó la ida (de i0 a ie) y cuántos
    quedan más allá. Devuelve (n_tom, pos_media, sobre, n_quedan, techo_ida). Sólo usa velas <= ie."""
    techo = A
    for j in range(i0, ie + 1):
        if x[j] > techo: techo = x[j]
    W = techo - A
    lo = max(0, i0 - look); qs = []
    for q in range(lo, i0 - w + 1):                                  # confirmado (q + w <= i0)
        if not piv[q] or x[q] <= A: continue
        vivo = True
        for j in range(q + 1, i0):
            if x[j] > x[q]: vivo = False; break
        if vivo: qs.append(q)
    if consecutivo and len(qs) > 0:                                  # series de >= N_SERIE con separación <= max_gap
        keep = []; grupo = [qs[0]]
        for u in range(1, len(qs)):
            if qs[u] - qs[u - 1] <= max_gap: grupo.append(qs[u])
            else:
                if len(grupo) >= 3: keep.extend(grupo)
                grupo = [qs[u]]
        if len(grupo) >= 3: keep.extend(grupo)
        qs = keep
    n_tom = 0; spos = 0.0; ult = -1e18; n_q = 0
    for q in qs:
        if x[q] <= techo:
            n_tom += 1; spos += (x[q] - A) / W if W > 0 else 0.0
            if x[q] > ult: ult = x[q]
        else: n_q += 1
    pos = spos / n_tom if n_tom > 0 else -1.0
    sobre = (techo - ult) / W if (n_tom > 0 and W > 0) else -1.0
    return n_tom, pos, sobre, n_q, techo


def disparos(ctx) -> pd.DataFrame:
    tick = float(ctx["tick"]); C = np.asarray(ctx["c"], float) / tick; ses = np.asarray(ctx["ses"], np.int64)
    h = np.asarray(ctx["h"], float) / tick; l = np.asarray(ctx["l"], float) / tick
    fr = P._friccion_ticks(ctx); min_w = 2.0 * P.VIAJES_MIN * fr
    piv = {(s, ei): P_ for ei, w in enumerate(ESCALAS) for s, P_ in ((1, _pivotes(h, ses, w)), (-1, _pivotes(-l, ses, w)))}
    filas = []
    for fi, f in enumerate(P.FRACCIONES):
        for (i0, ie, k, lado, W, ri, rv) in P._detectar(C, ses, P.RETRO_LAXO, f, min_w, P.MIN_IDA, P.MIN_VUELTA, P.MAX_IDA):
            i0, ie, k, lado = int(i0), int(ie), int(k), int(lado)
            x = h if lado == 1 else -l                               # espacio «techo»: los picos del lado del impulso son máximos
            A = l[i0] if lado == 1 else -h[i0]                       # origen de la ida por mecha, en ese espacio
            for ei, w in enumerate(ESCALAS):
                for ti in (0, 1):
                    n_t, pos, sob, n_q, techo = _clasificar(x, piv[(lado, ei)], w, i0, ie, A, LOOK, MAX_GAP[ei], ti == 1)
                    filas.append((k, -lado, fi, W / 2.0 / fr, ti, ei, n_t,
                                  0 if n_t == 0 else (1 if pos < 1 / 3 else (2 if pos < 2 / 3 else 3)),
                                  0 if n_t == 0 else (1 if sob <= 0.10 else (2 if sob <= 0.25 else 3)),
                                  1 if n_q > 0 else 0, C[i0] * tick, C[ie] * tick, W * tick))
    cols = ["k", "lado", "fi", "viajes", "ti", "ei", "n_tom", "pos", "sobre", "quedan", "A", "B", "W"]
    if not filas: return pd.DataFrame(columns=cols + ["rth", "ses"])
    D = pd.DataFrame(filas, columns=cols)
    from edgelab.research.regimen_sesion import minuto_ny
    mny = minuto_ny(np.asarray(ctx["t"], float)[D.k.to_numpy()].astype(np.int64))
    D["rth"] = ((mny >= P.RTH_INI) & (mny < P.RTH_FIN)).astype(np.int64); D["ses"] = ses[D.k.to_numpy()]
    return D.sort_values(["k", "fi", "ei", "ti"], kind="stable", ignore_index=True)


def niveles(r, ej, ctx):
    """Como el padre (hacia A, stop más allá de B), con objetivos más allá de A: 1,25·W y 1,5·W desde B (hipótesis de Nico)."""
    sl_, tp_ = ej; k = int(r["k"]); c = ctx["c"]; ses = ctx["ses"]; tick = float(ctx["tick"]); s = int(r["lado"])
    if k + 1 >= len(c) or ses[k + 1] != ses[k]: return None
    e = float(c[k]); B = float(r["B"]); A = float(r["A"]); W = float(r["W"])
    st = B - s * (tick if sl_ == "B1" else max(tick, 0.10 * W))
    st = np.ceil(st / tick) * tick if s == -1 else np.floor(st / tick) * tick
    R = (e - st) * s
    if R < tick: return None
    tp = {"A": A, "A125": B + s * 1.25 * W, "A150": B + s * 1.50 * W}.get(tp_, e + s * 2.0 * R)
    tp = np.round(tp / tick) * tick
    if (tp - e) * s < tick: return None
    return k, 2, s, e, st, tp, 0, (0 if s == 1 else 1), 0.0
