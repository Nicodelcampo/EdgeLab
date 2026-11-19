"""PICOS-DEFENDIDOS (2026-11-19, idea de Nico): un nivel de picos que el precio fue a buscar y NO tomó termina tomándose.

Secuencia (techos; los pisos son el espejo y se operan en corto):
  1. Nivel P: un pico de swing (zigzag de r·ATR) o un par de picos parecidos (δ = |P1−P2| / central ≤ 0,25).
  2. Alejamiento 1: el precio se aleja de P al menos X1·A.
  3. Acercamiento: vuelve a menos de D·A de P SIN tomarlo (ningún máximo por encima de P).
  4. Alejamiento 2: se vuelve a alejar; queda ARMADO cuando un cierre está X2·A por debajo del máximo del acercamiento.
  5. Disparador (uno por fila, como perilla): ALEJA (en el armado), REACERCA_33/50 (vuelve 1/3 o 1/2 del camino a P), EMA_TOQUE,
     EMA_DOBLE_CRUCE (cruza la EMA en contra y vuelve a cruzarla a favor, 0,25 A), CRUCE_EMAS (rápida cruza a la lenta a favor),
     ESPEJO_75/100 (impulso contrario y vuelta del 75 % / 100 % de su tamaño en ≤ 2× su duración: espejo laxo) y POC (cruza en contra
     y a favor el POC de los 60 minutos previos al armado, 0,25 A).
  6. Operación HACIA P y más allá: objetivo P + m·A (m = 2 ticks, 0,5, 1, 2), stop estructural (más allá del extremo del alejamiento 2)
     o 1 A / 2 A desde la entrada; el riesgo nunca es menor a 0,5 A (se ensancha: R acotado).
El nivel muere si se toma antes del disparo, a las ESPERA velas del armado o al fin de la sesión.

Temporalidades: velas de 1, 3, 5, 10 y 15 minutos armadas desde las M1 del contexto. Una vela de N minutos se conoce en la M1 que
cierra su bloque (o en la primera M1 del bloque siguiente si faltan minutos); la última vela abierta nunca cuenta. La decisión `k` es
esa M1 y se entra en el primer tick siguiente (límite 2).

Tendencia (perilla, para las variantes «tendencial» y «sin filtro»): cuatro definiciones, cada disparo se repite una vez por definición
(`def_tend`) con su estado `tend`: 0 a favor de la operación, 1 en contra, 2 neutra; `eq_any` agrega «cualquiera» (sin filtro).
  E20 / E50: cierre del lado de la EMA y EMA con pendiente (5 velas) del mismo lado. X9_21 / X20_50: EMA rápida contra lenta.
  La EMA de los disparadores es la de su definición (20, 50, 21, 50) y el par de CRUCE_EMAS (9/20, 20/50, 9/21, 20/50).

Todo usa sólo velas <= k. Spec: docs/research/agente/PICOS_DEFENDIDOS_20261119.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.estrategias._indicadores_ext import ema
from edgelab.research.grilla_generica import Variable
from edgelab.research.picos_robustos import zigzag_alterno
from edgelab.research.zonas_gaps import _atr_causal

try:
    from numba import njit
except ImportError:                                                    # pragma: no cover
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "PICOS-DEFENDIDOS"
INDICADORES = ["PICOS-DEFENDIDOS"]

TFS = (1, 3, 5, 10, 15)                                    # minutos
PICOS = (("Z15", 1.5, 0), ("Z3", 3.0, 0), ("PAR", 1.5, 1))  # (nombre, r del zigzag en A, par de picos)
DELTA_PAR = 0.25
X1_MIN, D_MAX, X2_MIN = 2.0, 1.0, 1.0                      # mínimos del detector, en A; lo demás es variable con cortes del E0
ESPERA = 60                                                # velas de la temporalidad después del armado
CRUCE_X = 0.25                                             # margen de cruce (EMA y POC), en A
POC_MIN = 60                                               # minutos de perfil para el POC
RIESGO_MIN = 0.5                                           # en A
MAX_CAND = 4096
DEFS = (("E20", 0, 20, 9, 20), ("E50", 0, 50, 20, 50), ("X9_21", 1, 21, 9, 21), ("X20_50", 1, 50, 20, 50))   # (nombre, cruce?, ema, rápida, lenta)
DISPARADORES = ("ALEJA", "REACERCA_33", "REACERCA_50", "EMA_TOQUE", "EMA_DOBLE_CRUCE", "CRUCE_EMAS", "ESPEJO_75", "ESPEJO_100", "POC")
STOPS = ("S_ESTR", "S_1A", "S_2A")
OBJETIVOS = (("T_2TK", 0.0), ("T_05", 0.5), ("T_1", 1.0), ("T_2", 2.0))
EJECUCIONES = [(s, o) for s in STOPS for o, _ in OBJETIVOS]          # 12

VARIABLES = [
    Variable("tf", "tf", "grupo", categoria=len(TFS)),
    Variable("pico", "pico", "grupo", categoria=len(PICOS)),
    Variable("alej1", "alej1", "ge", cuantiles=2),                    # alejamiento 1 (A): «considerable» desde el E0
    Variable("cerca", "cerca", "le", cuantiles=2),                    # distancia del acercamiento a P (A)
    Variable("alej2", "alej2", "ge", cuantiles=2),                    # alejamiento 2 hasta la decisión (A)
    Variable("def_tend", "deft", "grupo", categoria=len(DEFS)),
    Variable("tendencia", "tend", "eq_any", categoria=3),
    Variable("disparador", "disp", "grupo", categoria=len(DISPARADORES)),
]
EJES_ORDINALES = (0, 2, 3, 4)
BASE = {"tf": TFS.index(10), "pico": 2, "def_tend": 0, "tendencia": 0, "disparador": 0,
        "ejecución": EJECUCIONES.index(("S_ESTR", "T_05"))}
VACIO = ["k", "ses", "lado", "tf", "pico", "deft", "tend", "disp", "alej1", "cerca", "alej2", "P", "ext2", "A", "kp"]


# ------------------------------------------------------------------------------------------------ velas de N minutos
def velas_tf(t, o, h, l, c, ses, tf):
    """Velas de `tf` minutos desde M1 (t = cierre en s). Devuelve (o, h, l, c, ses, k_decision, m_ini) sólo de velas cerradas."""
    t = np.asarray(t, np.int64); n = len(t)
    if tf == 1:
        k = np.arange(n, dtype=np.int64); return o.copy(), h.copy(), l.copy(), c.copy(), ses.copy(), k, k.copy()
    w = 60 * tf; blk = (t - 1) // w
    nuevo = np.r_[True, (blk[1:] != blk[:-1]) | (ses[1:] != ses[:-1])]
    ini = np.flatnonzero(nuevo); fin = np.r_[ini[1:] - 1, n - 1]
    en_borde = (t[fin] % w) == 0
    sig_misma = np.zeros(len(fin), bool); ok_sig = fin + 1 < n
    sig_misma[ok_sig] = ses[fin[ok_sig] + 1] == ses[fin[ok_sig]]
    cerrada = en_borde | sig_misma                                     # cerrada por reloj o porque ya llegó una M1 del bloque siguiente
    kdec = np.where(en_borde, fin, fin + 1)
    sel = np.flatnonzero(cerrada); ini, fin, kdec = ini[sel], fin[sel], kdec[sel]
    H = np.maximum.reduceat(h, np.flatnonzero(nuevo))[sel] if len(sel) else np.zeros(0)
    L = np.minimum.reduceat(l, np.flatnonzero(nuevo))[sel] if len(sel) else np.zeros(0)
    return o[ini], H, L, c[fin], ses[ini], kdec.astype(np.int64), ini.astype(np.int64)


# ------------------------------------------------------------------------------------------------ niveles (en espacio «techo»)
def niveles_picos(xh, xl, ses, A, r, par, kind_ok):
    """Niveles P (techos en el espacio x): (i_pico, i_conf, P). `kind_ok`: +1 techos de x. Par: dos techos consecutivos del zigzag con
    |P1−P2| ≤ DELTA_PAR · central; el nivel es el mayor y se conoce en la confirmación del segundo."""
    R = np.where(np.isfinite(A), r * A, np.inf)
    I, K, Pp, Cf = zigzag_alterno(xh, xl, ses, R)
    pos = np.flatnonzero(K == kind_ok)
    if not par:
        return I[pos], Cf[pos], xh[I[pos]]
    out_i, out_c, out_p = [], [], []
    for a_, b_ in zip(pos[:-1], pos[1:]):
        if b_ - a_ != 2 or ses[I[a_]] != ses[I[b_]]: continue
        p1, p2 = xh[I[a_]], xh[I[b_]]; v = xl[I[a_ + 1]]; C = 0.5 * (p1 + p2) - v
        if C <= 0 or abs(p1 - p2) > DELTA_PAR * C: continue
        out_i.append(I[a_] if p1 >= p2 else I[b_]); out_c.append(Cf[b_]); out_p.append(max(p1, p2))
    return np.array(out_i, np.int64), np.array(out_c, np.int64), np.array(out_p, float)


@njit(cache=False)
def _poc(m_fin, vp_start, vp_px, vp_vol, signo, tick):
    """POC (precio de mayor volumen) de las M1 [m_fin − POC_MIN + 1, m_fin], en el espacio x (signo · precio). NaN si no hay volumen."""
    a = max(0, m_fin - POC_MIN + 1); i0 = vp_start[a]; i1 = vp_start[m_fin + 1]
    if i1 <= i0: return np.nan
    q = np.empty(i1 - i0, np.int64); w = np.empty(i1 - i0)
    for j in range(i0, i1):
        q[j - i0] = int(np.round(vp_px[j] / tick)); w[j - i0] = vp_vol[j]
    o = np.argsort(q, kind="mergesort"); best = -1.0; bq = 0; j = 0; n = len(q)
    while j < n:
        z = j; s = 0.0
        while z < n and q[o[z]] == q[o[j]]:
            s += w[o[z]]; z += 1
        if s > best: best = s; bq = q[o[j]]
        j = z
    return signo * bq * tick


@njit(cache=False)
def detectar(xh, xl, xc, ses, A, kdec, niv_i, niv_c, niv_p, emat, emaf, emas, signo, vp_start, vp_px, vp_vol, tick,
             x1, dmax, x2, espera, cruce, maxc):
    """Máquina causal por vela cerrada. Filas: (i, disparador, P, A, alej1, cerca, alej2, ext2, vela del pico). `ext2` = extremo del alejamiento 2
    (mínimo de x desde el acercamiento hasta i). Devuelve también los candidatos descartados por tope (debe ser 0)."""
    n = len(xc); out = []
    P = np.zeros(maxc); Au = np.zeros(maxc); f = np.zeros(maxc, np.int64); ip = np.zeros(maxc, np.int64)
    bot1 = np.zeros(maxc); alej1 = np.zeros(maxc); ap = np.zeros(maxc); iap = np.zeros(maxc, np.int64)
    bot2 = np.zeros(maxc); ib2 = np.zeros(maxc, np.int64); iarm = np.zeros(maxc, np.int64); hecho = np.zeros((maxc, 9), np.int64)
    fema = np.zeros(maxc, np.int64); fpoc = np.zeros(maxc, np.int64); poc = np.zeros(maxc); nv = 0; desb = 0; q = 0
    for i in range(n):
        if i > 0 and ses[i] != ses[i - 1]: nv = 0
        # vivos
        w = 0
        for k in range(nv):
            muere = False
            if xh[i] >= P[k] + tick:
                muere = True                                                   # tomado
            if not muere and f[k] == 0:
                if xl[i] < bot1[k]: bot1[k] = xl[i]
                if P[k] - bot1[k] >= x1 * Au[k] and xh[i] >= P[k] - dmax * Au[k]:
                    f[k] = 1; alej1[k] = P[k] - bot1[k]; ap[k] = xh[i]; iap[k] = i; bot2[k] = 1e300
            if not muere and f[k] == 1:
                if xh[i] > ap[k]:
                    ap[k] = xh[i]; iap[k] = i; bot2[k] = 1e300
                elif xl[i] < bot2[k]:
                    bot2[k] = xl[i]; ib2[k] = i
                if xc[i] <= ap[k] - x2 * Au[k]:
                    if xl[i] < bot2[k]: bot2[k] = xl[i]; ib2[k] = i
                    f[k] = 2; iarm[k] = i; fema[k] = 0; fpoc[k] = 0
                    for d in range(9): hecho[k, d] = 0
                    poc[k] = _poc(kdec[i], vp_start, vp_px, vp_vol, signo, tick)
            if not muere and f[k] == 2:                                        # el armado se evalúa en la MISMA vela: ALEJA dispara ahí
                if i - iarm[k] > espera:
                    muere = True
                else:
                    if i > iarm[k] and xl[i] < bot2[k]: bot2[k] = xl[i]; ib2[k] = i
                    u = Au[k]; dist = P[k] - bot2[k]
                    for d in range(9):
                        if hecho[k, d] == 1: continue
                        fire = False
                        if d == 0: fire = i == iarm[k]
                        elif d == 1: fire = i > iarm[k] and xc[i] >= bot2[k] + dist / 3.0
                        elif d == 2: fire = i > iarm[k] and xc[i] >= bot2[k] + dist / 2.0
                        elif d == 3: fire = i > iarm[k] and xl[i] <= emat[i] <= xh[i]
                        elif d == 4:
                            if fema[k] == 0 and xc[i] < emat[i] - cruce * u: fema[k] = 1
                            elif fema[k] == 1 and i > iarm[k] and xc[i] > emat[i] + cruce * u: fire = True
                        elif d == 5: fire = i > iarm[k] and emaf[i] > emas[i] and emaf[i - 1] <= emas[i - 1]
                        elif d == 6 or d == 7:
                            rho = 0.75 if d == 6 else 1.0; S = ap[k] - bot2[k]; dur = ib2[k] - iap[k]
                            fire = i > ib2[k] and dur >= 1 and S > 0 and xc[i] >= bot2[k] + rho * S and i - ib2[k] <= max(2 * dur, 2)
                        else:
                            if poc[k] == poc[k]:
                                if fpoc[k] == 0 and xc[i] < poc[k] - cruce * u: fpoc[k] = 1
                                elif fpoc[k] == 1 and i > iarm[k] and xc[i] > poc[k] + cruce * u: fire = True
                        if fire:
                            hecho[k, d] = 1
                            out.append((float(i), float(d), P[k], u, alej1[k] / u, (P[k] - ap[k]) / u, (ap[k] - bot2[k]) / u, bot2[k], float(ip[k])))
            if not muere:
                if w != k:
                    P[w] = P[k]; Au[w] = Au[k]; f[w] = f[k]; ip[w] = ip[k]; bot1[w] = bot1[k]; alej1[w] = alej1[k]; ap[w] = ap[k]
                    iap[w] = iap[k]; bot2[w] = bot2[k]; ib2[w] = ib2[k]; iarm[w] = iarm[k]; fema[w] = fema[k]; fpoc[w] = fpoc[k]
                    poc[w] = poc[k]
                    for d in range(9): hecho[w, d] = hecho[k, d]
                w += 1
        nv = w
        # niveles que se confirman en esta vela
        while q < len(niv_c) and niv_c[q] <= i:
            if niv_c[q] == i and A[i] > 0 and ses[niv_i[q]] == ses[i]:
                lo = 1e300; tomado = False
                for j in range(niv_i[q] + 1, i + 1):
                    if xl[j] < lo: lo = xl[j]
                    if xh[j] >= niv_p[q] + tick: tomado = True
                if not tomado:
                    if nv >= maxc:
                        desb += 1
                    else:
                        P[nv] = niv_p[q]; Au[nv] = A[i]; f[nv] = 0; ip[nv] = niv_i[q]; bot1[nv] = lo; alej1[nv] = 0.0; nv += 1
            q += 1
    return out, desb


def _tendencia(xc, ema_t, emaf, emas, cruce_def):
    """0 a favor (x sube), 1 en contra, 2 neutra; por vela de la temporalidad (sólo velas <= i)."""
    n = len(xc); out = np.full(n, 2, np.int64)
    if cruce_def:
        out[emaf > emas] = 0; out[emaf < emas] = 1
    else:
        pend = np.r_[np.zeros(min(5, n)), ema_t[5:] - ema_t[:-5]] if n > 5 else np.zeros(n)
        out[(xc > ema_t) & (pend > 0)] = 0; out[(xc < ema_t) & (pend < 0)] = 1
    return out


def disparos(ctx) -> pd.DataFrame:
    t = np.asarray(ctx["t"], np.int64); ses_m1 = np.asarray(ctx["ses"], np.int64); tick = float(ctx["tick"])
    o, h, l, c = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c"))
    vps, vpp, vpv = np.asarray(ctx["vp_start"], np.int64), np.asarray(ctx["vp_px"], float), np.asarray(ctx["vp_vol"], float)
    partes = []
    for ti, tf in enumerate(TFS):
        O, H, L, C, S, K, _ = velas_tf(t, o, h, l, c, ses_m1, tf)
        if len(C) < 30: continue
        A = _atr_causal(H, L, C)
        emas = {p: ema(C, p) for p in sorted({x for d in DEFS for x in d[2:]})}
        for signo, lado in ((1, 1), (-1, -1)):                       # techos -> compra; pisos (x = −precio) -> venta
            xh, xl, xc = (H, L, C) if signo == 1 else (-L, -H, -C)
            for pi, (_, r, par) in enumerate(PICOS):
                ni, nc, npx = niveles_picos(xh, xl, S, A, r, par, 1)
                if not len(ni): continue
                for di, (_, cruce_def, pe, pf, ps) in enumerate(DEFS):
                    et, ef, es = signo * emas[pe], signo * emas[pf], signo * emas[ps]
                    F, desb = detectar(xh, xl, xc, S, A, K, ni, nc, npx, et, ef, es, signo, vps, vpp, vpv, tick,
                                       X1_MIN, D_MAX, X2_MIN, ESPERA, CRUCE_X, MAX_CAND)
                    if desb: raise RuntimeError(f"{NOMBRE}: {desb} niveles descartados por tope (tf {tf}); subir MAX_CAND")
                    if not len(F): continue
                    Z = np.array(F, float); i = Z[:, 0].astype(np.int64)
                    td = _tendencia(xc, et, ef, es, cruce_def)
                    partes.append(pd.DataFrame(dict(k=K[i], ses=S[i], lado=lado, tf=ti, pico=pi, deft=di, tend=td[i],
                                                    disp=Z[:, 1].astype(np.int64), alej1=Z[:, 4], cerca=Z[:, 5], alej2=Z[:, 6],
                                                    P=signo * Z[:, 2], ext2=signo * Z[:, 7], A=Z[:, 3], kp=K[Z[:, 8].astype(np.int64)])))
    if not partes: return pd.DataFrame(columns=VACIO)
    D = pd.concat(partes, ignore_index=True)
    # varios niveles pueden disparar lo mismo en la misma decisión: queda el de mayor alejamiento 1 (regla declarada)
    D = D.sort_values(["k", "tf", "pico", "deft", "lado", "disp", "alej1"], ascending=[True] * 6 + [False], kind="stable")
    return D.drop_duplicates(["k", "tf", "pico", "deft", "lado", "disp"]).reset_index(drop=True)


# ------------------------------------------------------------------------------------------------ ejecución
def _niveles_arr(k, lado, P, ext2, A, c, tick, ej):
    """(start, limite, s, entrada, stop, objetivo, be) por fila; NaN en start donde no hay operación."""
    st_, tp_ = ej; m = dict(OBJETIVOS)[tp_]
    s = lado.astype(float); e = c[k]
    if st_ == "S_ESTR": st = ext2 - s * tick
    else: st = e - s * (1.0 if st_ == "S_1A" else 2.0) * A
    st = np.where(s * (e - st) < RIESGO_MIN * A, e - s * RIESGO_MIN * A, st)          # riesgo mínimo 0,5 A (se ensancha)
    st = np.where(s == 1, np.floor(st / tick) * tick, np.ceil(st / tick) * tick)
    tp = P + s * (2 * tick if m == 0 else m * A)
    tp = np.round(tp / tick) * tick
    ok = ((tp - e) * s >= tick) & ((e - st) * s >= tick) & np.isfinite(A)
    X = np.column_stack([np.where(ok, k, np.nan), np.full(len(k), 2.0), s, e, st, tp, np.zeros(len(k))])
    return X


def niveles_lote(D, ej, ctx):
    return _niveles_arr(D.k.to_numpy(np.int64), D.lado.to_numpy(np.int64), D.P.to_numpy(float), D.ext2.to_numpy(float),
                        D.A.to_numpy(float), np.asarray(ctx["c"], float), float(ctx["tick"]), ej)


def niveles(r, ej, ctx):
    X = _niveles_arr(np.array([int(r["k"])]), np.array([int(r["lado"])]), np.array([float(r["P"])]), np.array([float(r["ext2"])]),
                     np.array([float(r["A"])]), np.asarray(ctx["c"], float), float(ctx["tick"]), ej)[0]
    if not np.isfinite(X[0]): return None
    return int(X[0]), int(X[1]), int(X[2]), float(X[3]), float(X[4]), float(X[5]), int(X[6])
