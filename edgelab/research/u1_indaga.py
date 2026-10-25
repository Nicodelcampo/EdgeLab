"""U1-INDAGA (2026-10-23): indagación de la idea U1 antes de cualquier P&L básico (pedido de Nico: «al encontrar variantes buenas,
no se pasa a un P&L sin más: se indaga»). Spec: docs/research/areas_expansion_20261022/SPEC_U1_INDAGA.md.

U1 (AREAS-EXP-1 v1.4, réplica informativa en USATECH): >= 3 zonas LUX-IMB en una banda de 40 pts; el precio se aleja >= 8x la
altura del área y vuelve el 75 % del camino; se opera HACIA el área. Acá se abre por dentro:
  - VOLUMEN: dónde está (perfil por pierna, 5 franjas del borde al extremo), cuánto (por pierna, relativo a la sesión
    anterior) y en qué pierna (ida = alejamiento, vuelta = acercamiento);
  - VELOCIDAD de la vuelta frente a la ida (agotamiento: Bhatti 2026, «momentum exhaustion», corpus 0238);
  - VWAP de la sesión: si el valor justo queda del lado del objetivo (reversión a VWAP, corpus 0238/0372);
  - ESPERAS antes de entrar: retroceso (corpus 0022, «pullback and rejection»), volver a la franja de más volumen de cada
    pierna, y esperar a que se haga volumen.
Todas las variables usan sólo velas <= k (la decisión). Las esperas usan velas posteriores a k pero sólo hasta el llenado:
son reglas de entrada causales (se decide en el momento, no se mira el futuro).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import areas_expansion as AX
from edgelab.research.grilla_generica import Variable

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "U1-INDAGA"
NS_U1, W_U1, XS_U1, G_U1 = (3, 5), 40.0, (0.33, 0.25, 0.15), 1.0
AH_CORTES = (4.0, 8.0, 16.0)
FRANJAS = 5                                   # perfil por pierna: 5 franjas del borde cercano (0) al extremo (1)
ESPERA_VOL_MAX = 60                           # velas para que «se haga volumen»
ENTRADAS = ("E1A", "RET05", "RET10", "RET20", "VOL_IDA", "VOL_VUELTA", "HACEV15", "HACEV25")
OBJETIVOS = ("T1", "T2", "T3")
STOPS = ("S3", "S2")                          # S3: más allá del extremo (U1); S2: 1x la distancia al objetivo
EJECUCIONES = [(e, o, s, b) for e in ENTRADAS for o in OBJETIVOS for s in STOPS for b in (0, 1)]       # 96

VARIABLES = [
    Variable("N", "ni", "grupo", categoria=len(NS_U1)),
    Variable("x", "xi", "grupo", categoria=len(XS_U1)),
    Variable("A/H", "A_H", "ge", cortes=AH_CORTES, piso=True),
    Variable("vol_vuelta/ida", "r_vol", "extremos", cuantiles=3),
    Variable("vol_ida_rel", "vol_ida_rel", "extremos", cuantiles=3),
    Variable("vel_vuelta/ida", "r_vel", "extremos", cuantiles=3),
    Variable("franja_ida", "fr_ida", "eq_any", categoria=3),         # 0 junto al área · 1 medio · 2 junto al extremo
    Variable("franja_vuelta", "fr_vuelta", "eq_any", categoria=3),
    Variable("vwap", "vwap_pos", "eq_any", cortes=(0.0, 0.5)),         # 0 pasando el área · 1 entre área y mitad · 2 detrás del precio
]
EJES_ORDINALES = (1, 2)
# Celda de referencia = U1 tal como replicó: N>=3, x=0.25, A/H>=8, resto «cualquiera», entrada E1A, T1, S3, sin BE.
BASE = {"N": 0, "x": 1, "A/H": 1, "ejecución": EJECUCIONES.index(("E1A", "T1", "S3", 0))}


def _franja3(f):
    return np.where(f < 0, np.nan, np.where(f <= 1, 0, np.where(f == 2, 1, 2)))


@njit(cache=False)
def anatomia(m, k, lado, lo, hi, E, A, h, l, c, v, ses, vp_start, vp_px, vp_vol, base_rate, nf, espera):
    """Por disparo: piernas (ida = desde que dejó el área hasta el extremo; vuelta = del extremo a la decisión), volumen y
    duración de cada una, franja de máximo volumen de cada pierna (perfil por precio) y su precio, y la vela en que «se hizo
    volumen» después de la decisión (>= q x mediana por vela de la vuelta) para q = 1,5 y 2,5, si llega antes de tocar el área."""
    T = len(m); out = np.full((T, 12), np.nan); hb = np.zeros(nf)
    for t in range(T):
        d = lado[t]; borde = hi[t] if d == 1 else lo[t]
        tE = k[t]
        while tE > m[t] + 1 and not ((d == 1 and h[tE] >= E[t] - 1e-9) or (d == -1 and l[tE] <= E[t] + 1e-9)): tE -= 1
        js = tE
        while js > m[t] + 1 and not (lo[t] <= c[js - 1] <= hi[t]): js -= 1
        di, dv = tE - js + 1, k[t] - tE
        vi = v[js:tE + 1].sum(); vv = v[tE + 1:k[t] + 1].sum() if dv > 0 else 0.0
        out[t, 0] = di; out[t, 1] = dv; out[t, 2] = vi; out[t, 3] = vv
        out[t, 4] = (vi / di) / base_rate[k[t]] if base_rate[k[t]] > 0 else np.nan
        for p, (a, b) in enumerate(((js, tE), (tE + 1, k[t]))):
            if b < a: continue
            hb[:] = 0.0; tot = 0.0
            for i in range(vp_start[a], vp_start[b + 1]):
                pos = (vp_px[i] - borde) * d / max(A[t], 1e-9)
                if pos < 0 or pos > 1: continue
                j = min(int(pos * nf), nf - 1); hb[j] += vp_vol[i]; tot += vp_vol[i]
            if tot <= 0: continue
            jm = 0
            for q in range(1, nf):
                if hb[q] > hb[jm]: jm = q
            out[t, 5 + 2 * p] = jm; out[t, 6 + 2 * p] = borde + d * (jm + 0.5) / nf * A[t]
        if dv > 0:
            med = np.median(v[tE + 1:k[t] + 1])
            for col, qv in ((9, 1.5), (10, 2.5)):
                j = k[t] + 1
                while j < len(c) and j - k[t] <= espera and ses[j] == ses[k[t]]:
                    if (c[j] - borde) * d <= 0: break                      # ya llegó al área: tarde para entrar
                    if v[j] >= qv * med: out[t, col] = j; break
                    j += 1
    return out


def disparos(ctx):
    o, h, l, c, v, t, ses, seg = (ctx[x] for x in ("o", "h", "l", "c", "v", "t", "ses", "seg"))
    filas = []
    esc = ctx.get("escala_seg")                      # opcional {segmento: factor} (traslado de U1 a otro instrumento, u1_oro)
    for sg in pd.unique(seg):
        idx = np.flatnonzero(seg == sg); a, b = idx[0], idx[-1] + 1
        f = 1.0 if esc is None else float(esc[sg])
        if not np.isfinite(f) or f <= 0: continue        # segmento sin escala causal (el primero): no dispara
        Z = AX.zonas(t[a:b], o[a:b], h[a:b], l[a:b], c[a:b])
        EV = AX.eventos(Z, t[a:b], G_U1 * f, ns=NS_U1, ws=(W_U1 * f,))
        for (n_, _w), lista in EV.items():
            for ev in lista:
                for d in AX.disparos(ev, h[a:b], l[a:b], c[a:b], t[a:b], fin=int(Z["zfin"][ev[3]].max()), xs=XS_U1):
                    filas.append(dict(d, m=d["m"] + a, k=d["k"] + a, ni=NS_U1.index(n_), A_H=d["A"] / d["H"]))
    D = pd.DataFrame(filas)
    if not len(D): return D
    D = D[D.A_H >= AH_CORTES[0]].reset_index(drop=True)
    df = pd.DataFrame(dict(ses=ses, v=v)); rate = df.groupby("ses").v.mean(); us = np.array(sorted(rate.index))
    prev = pd.Series(np.r_[np.nan, rate.loc[us].to_numpy()[:-1]], index=us)
    base_rate = prev.reindex(ses).to_numpy(float)
    X = anatomia(D.m.to_numpy(np.int64), D.k.to_numpy(np.int64), D.lado.to_numpy(np.int64), D.lo.to_numpy(float), D.hi.to_numpy(float),
                 D.E.to_numpy(float), D.A.to_numpy(float), h, l, c, v, ses, ctx["vp_start"].astype(np.int64), ctx["vp_px"], ctx["vp_vol"],
                 base_rate, FRANJAS, ESPERA_VOL_MAX)
    D["dur_ida"], D["dur_vuelta"], D["vol_ida"], D["vol_vuelta"], D["vol_ida_rel"] = X[:, 0], X[:, 1], X[:, 2], X[:, 3], X[:, 4]
    D["fr_ida"], D["px_vol_ida"], D["fr_vuelta"], D["px_vol_vuelta"] = _franja3(np.nan_to_num(X[:, 5], nan=-1)), X[:, 6], _franja3(np.nan_to_num(X[:, 7], nan=-1)), X[:, 8]
    D["j_hacev15"], D["j_hacev25"] = X[:, 9], X[:, 10]
    with np.errstate(invalid="ignore", divide="ignore"):
        D["r_vol"] = (D.vol_vuelta / D.dur_vuelta) / (D.vol_ida / D.dur_ida)
        D["r_vel"] = ((1 - np.array(XS_U1)[D.xi.to_numpy()]) / D.dur_vuelta) / (1 / D.dur_ida)       # recorrido de vuelta / ida por vela
    pv = (df.assign(pv=c * v).groupby("ses").pv.cumsum() / df.groupby("ses").v.cumsum()).to_numpy()   # VWAP de la sesión hasta cada vela
    borde = np.where(D.lado == 1, D.hi, D.lo)
    D["vwap_pos"] = (pv[D.k.to_numpy()] - borde) * D.lado.to_numpy() / D.A.to_numpy()
    return D


def niveles(r, ej, ctx):
    en, ob, sl, be = ej; d = int(r["lado"]); s = -d; k = int(r["k"]); c0 = float(ctx["c"][k]); tick = ctx["tick"]
    borde, lejos = (r["hi"], r["lo"]) if d == 1 else (r["lo"], r["hi"])
    start, lim, e = k, 2, c0
    if en.startswith("RET"):
        lim, e = 1, c0 + d * (int(en[3:]) / 100) * r["A"]                      # retroceso: límite más lejos del área
    elif en in ("VOL_IDA", "VOL_VUELTA"):
        e = r["px_vol_ida" if en == "VOL_IDA" else "px_vol_vuelta"]
        if not np.isfinite(e) or (e - c0) * d < tick: return None              # sólo si la franja quedó detrás del precio
        lim = 1
    elif en.startswith("HACEV"):
        j = r["j_hacev15" if en == "HACEV15" else "j_hacev25"]
        if not np.isfinite(j): return None
        start = int(j); e = float(ctx["c"][start])
    tp = {"T1": borde, "T2": (r["lo"] + r["hi"]) / 2, "T3": lejos}[ob]; dist = (e - tp) * -s
    if dist < tick: return None
    st = r["E"] - s * tick if sl == "S3" else e - s * dist
    if (e - st) * s < tick: return None
    return start, lim, s, e, st, tp, be
