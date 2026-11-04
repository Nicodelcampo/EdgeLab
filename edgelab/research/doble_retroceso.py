"""DOBLE-RETROCESO (2026-11-04, Nico + Gemini): patrón de 5 piernas P0→P1→P2→P3→P4→P5, en barras de N ticks.

  1. Impulso 1 (P0→P1).
  2. Retroceso 1 (P1→P2): fija el pico de referencia P2.
  3. Impulso 2 (P2→P3): toma P1, pero sin ir mucho más allá.
  4. Retroceso 2 (P3→P4): vuelve cerca de P2 SIN tomarlo.
  5. Impulso 3 (P4→P5): la continuación. Se opera a favor (corto si el impulso 1 fue bajista).

Diseño para MUCHÍSIMAS combinaciones (pedido de Nico): el detector corre UNA vez por resolución con umbrales mínimos y guarda cada pierna
medida (distancias en ATR causal de la resolución y velas por pierna). La grilla masiva (`grilla_masiva`, tensor acumulado) cruza después
todas las combinaciones de distancias y velas como variables, con el FDR (cola t) y el embudo. Correr el detector por combinación sería
millones de pasadas; así es una por resolución.

Resoluciones: barras de N ∈ {50, 100, 250} ticks armadas con los ticks del propio contexto (`tpx`/`tstart`, los mismos que usa el
simulador), cortadas por sesión. El disparo de una barra de ticks se ubica en la vela M1 que contiene su último tick y se entra en el
primer tick de la vela M1 siguiente: puede llegar hasta un minuto tarde (conservador), nunca antes. Diseño y pre-registro:
docs/research/doble_retroceso_20261104/PREREGISTRO_DOBLE_RETROCESO.md. NT8: nt8_tools/EdgeLabDobleRetrocesoCercano.cs (paridad aparte).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.eventos import TIPOS_TIER1
from edgelab.research.grilla_generica import Variable
from edgelab.research.intento_fallido import lineas_salida  # noqa: F401   (sólo salida forzada antes de noticias)
from edgelab.research.zonas_gaps import _atr_causal

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "DOBLE-RETROCESO"
INDICADORES = ["DOBLE-RETROCESO"]
RESOLUCIONES = (50, 100, 250)
# Umbrales MÍNIMOS del detector (en ATR de la resolución): todo lo demás es variable de la grilla.
IMP1_MIN, RET1_MIN, RET2_MIN, GIRO, IMP3_CONF = 1.0, 0.3, 0.3, 0.25, 1.0
VELAS_MAX = 60                      # tope de velas por pierna (de la resolución)
MAX_CAND = 8192
EXCLUIR_EVENTOS = dict(antes_min=5, despues_min=5, tipos=TIPOS_TIER1)
LINEAS_SOLO_TIEMPO = True
VARIABLES = [
    Variable("modo", "modo", "grupo", categoria=2),                 # 0 giro temprano desde P4 · 1 impulso 3 confirmado
    Variable("resolucion", "res", "grupo", categoria=len(RESOLUCIONES)),
    Variable("imp1", "imp1_atr", "ge", cuantiles=4),                # tamaño del impulso 1 (ATR)
    Variable("ret1", "ret1_frac", "le", cuantiles=4),               # retroceso 1 / impulso 1
    Variable("pasa_p1", "pasa_p1_atr", "le", cuantiles=4),          # cuánto P3 se pasó de P1 (ATR): «no mucho más profundo»
    Variable("cerca_p2", "cerca_p2_atr", "le", cuantiles=4),        # cuán cerca de P2 quedó P4 sin tomarlo (ATR)
    Variable("velas_imp1", "v_imp1", "le", cuantiles=3),
    Variable("velas_ret1", "v_ret1", "le", cuantiles=3),
    Variable("velas_imp2", "v_imp2", "le", cuantiles=3),
    Variable("velas_ret2", "v_ret2", "le", cuantiles=3),
]
EJES_ORDINALES = (2, 3, 4, 5, 6, 7, 8, 9)
EJECUCIONES = [(st, tp) for st in ("P2", "P2_ATR") for tp in ("2R", "3R", "MM")]   # stop detrás de P2 (+0,25 ATR); TP 2R, 3R o
BASE = {"modo": 0, "resolucion": 1, "ejecución": 0}                                # medida igual al impulso 1 desde P4
VACIO = ["k", "ses", "lado", "modo", "res", "imp1_atr", "ret1_frac", "pasa_p1_atr", "cerca_p2_atr", "v_imp1", "v_ret1", "v_imp2",
         "v_ret2", "p2", "p4", "imp1", "atr"]


@njit(cache=False)
def barras_ticks(tpx, tstart, ses_m1, n):
    """Barras de `n` ticks por sesión desde los ticks del contexto. Devuelve o, h, l, c, sesión y vela M1 del último tick. La última
    barra de los datos, si tiene menos de `n` ticks, NO se emite: en tiempo real todavía no cerró (sí se emite la incompleta que cierra
    una sesión que ya terminó)."""
    nm = len(ses_m1); tot = tstart[nm]
    cap = tot // max(n, 1) + nm + 8
    o = np.empty(cap); h = np.empty(cap); l = np.empty(cap); c = np.empty(cap)
    s = np.empty(cap, np.int64); m = np.empty(cap, np.int64); b = 0
    i = 0
    while i < nm:
        j = i
        while j + 1 < nm and ses_m1[j + 1] == ses_m1[i]: j += 1
        a, z = tstart[i], tstart[j + 1]; q = a; mi = i
        while q < z:
            e = min(q + n, z)
            o[b] = tpx[q]; c[b] = tpx[e - 1]; hh = tpx[q]; ll = tpx[q]
            for t in range(q, e):
                if tpx[t] > hh: hh = tpx[t]
                if tpx[t] < ll: ll = tpx[t]
            while mi < j and tstart[mi + 1] <= e - 1: mi += 1
            if e - q < n and j + 1 >= nm: break                                  # barra final abierta: no cerró
            h[b] = hh; l[b] = ll; s[b] = ses_m1[i]; m[b] = mi; b += 1
            q = e
        i = j + 1
    return o[:b], h[:b], l[:b], c[:b], s[:b], m[:b]


@njit(cache=False)
def detectar(o, h, l, c, ses, atr, tick, imp1_min, ret1_min, ret2_min, giro, imp3_conf, vmax, maxc):
    """Máquina de estados causal (cierre de cada barra). Un candidato por cada extremo P1 tras un impulso; sin tope silencioso de
    candidatos (si se llena, devuelve desbordes > 0). Emite a lo sumo una vez por modo y candidato. Filas:
    (i, lado, modo, imp1, ret1, pasa_p1, cerca_p2, v_imp1, v_ret1, v_imp2, v_ret2, p2, p4, atr)."""
    n = len(c); out = []
    viv = np.zeros(maxc, np.int64); d_ = np.zeros(maxc, np.int64); fa = np.zeros(maxc, np.int64)
    b0 = np.zeros(maxc, np.int64); b1 = np.zeros(maxc, np.int64); b2 = np.zeros(maxc, np.int64); b3 = np.zeros(maxc, np.int64); b4 = np.zeros(maxc, np.int64)
    p0 = np.zeros(maxc); p1 = np.zeros(maxc); p2 = np.zeros(maxc); p3 = np.zeros(maxc); p4 = np.zeros(maxc); u = np.zeros(maxc)
    em0 = np.zeros(maxc, np.int64); desb = 0; nviv = 0; ini = 0
    for i in range(n):
        if i > 0 and ses[i] != ses[i - 1]:
            for q in range(nviv): viv[q] = 0
            nviv = 0; ini = i
        hi = h[i]; lo = l[i]; cl = c[i]; op = o[i]
        k = 0
        while k < nviv:
            if viv[k] == 0:
                k += 1; continue
            dd = d_[k]; us = u[k]; muere = False
            # trabajamos en coordenada «a favor del impulso»: x = -precio si el impulso 1 fue bajista (dd = -1)
            if dd == -1:
                xh = -lo; xl = -hi; xc = -cl; xo = -op
            else:
                xh = hi; xl = lo; xc = cl; xo = op
            # (en esa coordenada el impulso 1 SUBE: P0 abajo, P1 arriba, P2 retroceso abajo, P3 > P1, P4 > P2, impulso 3 sube)
            f = fa[k]
            if f == 1:                                                       # retroceso 1
                if xh > p1[k]:                                               # el impulso 1 se extendió: este P1 ya no es el extremo
                    muere = True
                elif xl <= p0[k] or i - b1[k] > vmax:
                    muere = True
                else:
                    if xl < p2[k]: p2[k] = xl; b2[k] = i
                    if p1[k] - p2[k] >= ret1_min * us and i > b2[k] and xc > p2[k]:
                        fa[k] = 2; p3[k] = xh; b3[k] = i
            elif f == 2:                                                     # impulso 2
                if xl < p2[k]:
                    if xl > p0[k] and i - b1[k] <= vmax: p2[k] = xl; b2[k] = i; p3[k] = xh; b3[k] = i
                    else: muere = True
                else:
                    if xh > p3[k]: p3[k] = xh; b3[k] = i
                    if i - b2[k] > vmax: muere = True
                    elif p3[k] - p1[k] >= tick and i > b3[k] and xc < p3[k]:
                        if xl <= p2[k] + tick: muere = True                     # el retroceso 2 arrancó tomando P2
                        else: fa[k] = 3; p4[k] = xl; b4[k] = i
            elif f == 3 or f == 4:                                           # retroceso 2 / impulso 3
                if xl <= p2[k] + tick:
                    muere = True                                             # tomó P2 (o quedó a menos de 1 tick): anulado
                elif f == 3 and xh > p3[k]:
                    if i - b2[k] <= vmax: p3[k] = xh; b3[k] = i; p4[k] = xl; b4[k] = i
                    else: muere = True
                else:
                    if f == 3:
                        if xl < p4[k]: p4[k] = xl; b4[k] = i
                        if i - b3[k] > vmax: muere = True
                        elif p3[k] - p4[k] >= ret2_min * us and i > b4[k] and xc > p4[k]: fa[k] = 4
                    if not muere and fa[k] == 4 and p4[k] > p2[k] + tick:
                        if i - b4[k] > vmax: muere = True
                        else:
                            fila_base = (p1[k] - p0[k]) / us, (p1[k] - p2[k]) / (p1[k] - p0[k]), (p3[k] - p1[k]) / us, (p4[k] - p2[k]) / us
                            if em0[k] == 0 and xc - p4[k] >= giro * us and xc > xo:
                                em0[k] = 1
                                out.append((i, dd, 0, fila_base[0], fila_base[1], fila_base[2], fila_base[3], b1[k] - b0[k], b2[k] - b1[k],
                                            b3[k] - b2[k], b4[k] - b3[k], p2[k] * dd, p4[k] * dd, us))
                            if xc - p4[k] >= imp3_conf * us and xc > xo:
                                out.append((i, dd, 1, fila_base[0], fila_base[1], fila_base[2], fila_base[3], b1[k] - b0[k], b2[k] - b1[k],
                                            b3[k] - b2[k], b4[k] - b3[k], p2[k] * dd, p4[k] * dd, us))
                                muere = True
            if muere:
                viv[k] = 0
            k += 1
        # compactar
        w = 0
        for q in range(nviv):
            if viv[q] == 1:
                if w != q:
                    viv[w] = 1; d_[w] = d_[q]; fa[w] = fa[q]; b0[w] = b0[q]; b1[w] = b1[q]; b2[w] = b2[q]; b3[w] = b3[q]; b4[w] = b4[q]
                    p0[w] = p0[q]; p1[w] = p1[q]; p2[w] = p2[q]; p3[w] = p3[q]; p4[w] = p4[q]; u[w] = u[q]; em0[w] = em0[q]
                w += 1
        for q in range(w, nviv): viv[q] = 0
        nviv = w
        # nuevo impulso 1 con extremo P1 en la barra i-1 (la barra i ya giró)
        j = i - 1
        if j - ini < 2 or not atr[i] > 0: continue
        ak = atr[i]
        for dd in (1, -1):
            if dd == 1: gira = h[i] <= h[j] and l[i] < l[j]
            else: gira = l[i] >= l[j] and h[i] > h[j]
            if not gira: continue
            x1 = h[j] if dd == 1 else -l[j]
            best = 1e300; bb = -1; ok = True
            lim = max(ini, j - vmax)
            for t in range(j - 1, lim - 1, -1):
                xt_hi = h[t] if dd == 1 else -l[t]
                if xt_hi > x1: break                                         # P1 no es el extremo del tramo
                xt = l[t] if dd == 1 else -h[t]
                if xt < best: best = xt; bb = t
            if bb < 0 or x1 - best < imp1_min * ak: continue
            if nviv >= maxc:
                desb += 1; continue
            q = nviv; nviv += 1
            viv[q] = 1; d_[q] = dd; fa[q] = 1; b0[q] = bb; b1[q] = j; b2[q] = i; b3[q] = i; b4[q] = i
            p0[q] = best; p1[q] = x1; p2[q] = (l[i] if dd == 1 else -h[i]); u[q] = ak; em0[q] = 0
    return out, desb


def disparos(ctx) -> pd.DataFrame:
    tpx = np.asarray(ctx["tpx"], float); tstart = np.asarray(ctx["tstart"], np.int64); ses_m1 = np.asarray(ctx["ses"], np.int64)
    tick = float(ctx["tick"]); partes = []
    for ri, n in enumerate(RESOLUCIONES):
        o, h, l, c, s, m = barras_ticks(tpx, tstart, ses_m1, int(n))
        if len(c) < 30: continue
        atr = _atr_causal(h, l, c)
        F, desb = detectar(o, h, l, c, s, atr, tick, IMP1_MIN, RET1_MIN, RET2_MIN, GIRO, IMP3_CONF, VELAS_MAX, MAX_CAND)
        if desb: raise RuntimeError(f"DOBLE-RETROCESO: {desb} candidatos descartados por tope en {n}T; subir MAX_CAND")
        if not len(F): continue
        A = np.array(F, float); i = A[:, 0].astype(np.int64)
        partes.append(pd.DataFrame(dict(k=m[i], ses=s[i], lado=A[:, 1].astype(np.int64), modo=A[:, 2].astype(np.int64), res=ri,
                                        imp1_atr=A[:, 3], ret1_frac=A[:, 4], pasa_p1_atr=A[:, 5], cerca_p2_atr=A[:, 6], v_imp1=A[:, 7],
                                        v_ret1=A[:, 8], v_imp2=A[:, 9], v_ret2=A[:, 10], p2=A[:, 11], p4=A[:, 12], imp1=A[:, 3] * A[:, 13],
                                        atr=A[:, 13])))
    if not partes: return pd.DataFrame(columns=VACIO)
    D = pd.concat(partes, ignore_index=True)
    # varios candidatos (P0/P1 distintos) pueden disparar en la misma vela M1 con la misma dirección y modo: queda el de mayor
    # impulso 1 (regla declarada; evita contar la misma operación varias veces)
    D = D.sort_values(["k", "res", "modo", "lado", "imp1_atr"], ascending=[True, True, True, True, False], kind="stable")
    return D.drop_duplicates(["k", "res", "modo", "lado"]).reset_index(drop=True)


def niveles(r, ej, ctx):
    """9 valores. Lado = dirección del impulso 1 (continuación). Stop detrás de P2; TP 2R, 3R o MM (impulso 1 medido desde P4)."""
    st_, tp_ = ej; s = int(r["lado"]); k = int(r["k"]); tick = float(ctx["tick"]); e = float(ctx["c"][k])
    st = r["p2"] - s * (tick + (0.25 * r["atr"] if st_ == "P2_ATR" else 0.0))
    st = np.floor(st / tick) * tick if s == 1 else np.ceil(st / tick) * tick
    R = (e - st) * s
    if R < tick: return None
    tp = e + s * (2.0 if tp_ == "2R" else 3.0) * R if tp_ != "MM" else r["p4"] + s * r["imp1"]
    tp = np.round(tp / tick) * tick
    if (tp - e) * s < tick: return None
    return k, 2, s, e, st, tp, 0, (0 if s == 1 else 1), 0.0
