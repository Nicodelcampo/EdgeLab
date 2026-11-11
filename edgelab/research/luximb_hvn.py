"""LUXIMB-HVN (2026-11-11, pedido de Nico): la regla del visor de LUX-IMB (expansión con zonas OG/VI en su 25 % inicial, fade
hacia A) medida a fondo, en NQ y en USATECH (zonas propias de cada uno), con tres preguntas:

1. **Mecanismo:** cuando el precio primero se extiende más allá del extremo B y recién después vuelve hacia A, ¿es porque más allá
   de B había un nodo de volumen alto (HVN) del pasado que «frenó» al precio? Rasgo `hvn_<L>`: volumen de la franja más allá de B
   (alto = la mitad del impulso) en las `L` velas anteriores al inicio del impulso, dividido por el mayor de las dos franjas
   vecinas del mismo alto (la de adentro del impulso y la siguiente más allá).
2. **Entrada al confirmar (E0):** la del visor, con stop y objetivo en fracciones de D = |entrada − A|, y gestión: toma parcial
   del 50 % y/o break even a una distancia fija.
3. **Entrada en la vuelta (EXT):** esperar que el precio se extienda `e`·rango más allá de B (sin pasar de `c`·rango: se cancela),
   y entrar cuando vuelve `r`·rango desde el extremo; stop `b`·rango más allá del extremo; objetivo A o la mitad del impulso. El HVN
   NO es parte de la ejecución: es un rasgo para filtrar en el análisis (con y sin volumen se mide con la misma ejecución).

La definición del impulso es parametrizable (`DETECTORES` × amplitud × zonas, `luximb_grilla.marcas_segmento`); la del visor es
`D3_20` / amplitud 0 / zonas 2, y la definición de zonas 0 (sin condición de zonas) es el CONTROL de cada detector.

Convención de salidas: el stop es a mercado y sale al precio del tick que lo cruza (un salto se paga entero); objetivo y parcial
son límites y se cobran en su nivel. (Acreditar el stop en su nivel sesga a favor: en una caminata con saltos daba +0,3 R.)

Todo causal: los eventos se conocen al cierre de la vela M1 de marca `k`; las ejecuciones usan los ticks desde la vela k+1; el
perfil de volumen sólo velas anteriores al inicio del impulso. R bruto en unidades del riesgo inicial; el neto resta la fricción
de `edgelab/costos.py` sobre `riesgo_pts` en el análisis. Sin holdout: los lectores de `fuentes_ticks` lo rechazan.
Pre-registro: docs/research/luximb_hvn_20261111/PREREGISTRO.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import areas_expansion as AX
from edgelab.research import luximb_grilla as LG
from edgelab.research.agente.regimen import agregar

try:
    from numba import njit
except ImportError:                                     # sin numba: misma lógica en Python (lento; sólo tests chicos)
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "LUXIMB-HVN"
DETECTORES = {"D3_20": (3.0, 20), "D2_20": (2.0, 20), "D4_20": (4.0, 20), "D3_40": (3.0, 40)}   # (k·ATR(14), velas máx.)
AMP = ((60.0, 60.0), (80.0, 60.0))                     # (percentil causal de amplitud, piso en puntos); 0 = la del visor
ZON = LG.ZON                                           # (franja inicial, mínimo de zonas); 0 = control sin zonas, 2 = visor
VISOR = "D3_20_a0_z2"
LOOKBACKS = (240, 1440)                                # velas M1 hacia el pasado para el perfil (≈ 4 h y ≈ 1 día)
TOPE = 240                                             # velas: espera de la entrada y vida de la operación
GAP_S = 1800.0

# --- ejecuciones (fijadas antes de mirar; ver PREREGISTRO.md §4) ---------------------------------------------------------
# E0: (sl en D, tp en D, parcial en D o 0, be en D o 0). Parcial = 50 % de la posición; «PB» = parcial y BE a la misma distancia.
_GEST = ((0.0, 0.0), (0.25, 0.0), (0.5, 0.0), (0.0, 0.25), (0.0, 0.5), (0.25, 0.25), (0.5, 0.5))
E0 = [(sl, tp, pt, be) for sl in (0.2, 0.35, 0.5) for tp in (0.5, 1.0) for pt, be in _GEST if max(pt, be) < tp]
# EXT: (e, r, b, tp: 0 = A / 1 = mitad del impulso, c) — todo en fracciones del rango del impulso; c = e + {0,25; 0,5}
EXT = [(e, r, b, tp, round(e + dc, 4)) for e in (0.1, 0.25, 0.5) for r in (0.05, 0.1, 0.2) for b in (0.05, 0.1) for tp in (0, 1)
       for dc in (0.25, 0.5)]


def nombre_e0(x) -> str:
    sl, tp, pt, be = x
    g = "N" if not pt and not be else ("P" if pt and not be else ("B" if be and not pt else "PB"))
    return f"E0_sl{sl}_tp{tp}_{g}{max(pt, be) if g != 'N' else ''}"


def nombre_ext(x) -> str:
    e, r, b, tp, c = x
    return f"EXT_e{e}_r{r}_b{b}_{'A' if tp == 0 else 'M'}_c{c}"


# ----------------------------------------------------------------------------------------------------------- eventos
def eventos(ctx) -> pd.DataFrame:
    """Una fila por evento único (k, d, i0) con una columna booleana por definición `<det>_a<i>_z<j>` y los rasgos causales."""
    o, h, l, c, v, t, ses, seg = (np.asarray(ctx[x]) for x in ("o", "h", "l", "c", "v", "t", "ses", "seg"))
    tick = float(ctx["tick"]); partes = []
    for sg in pd.unique(seg):
        idx = np.flatnonzero(seg == sg); a0, b0 = idx[0], idx[-1] + 1
        Z = AX.zonas(t[a0:b0], o[a0:b0], h[a0:b0], l[a0:b0], c[a0:b0])
        for det, (ak, mb) in DETECTORES.items():
            M = LG.marcas_segmento(t[a0:b0], o[a0:b0], h[a0:b0], l[a0:b0], c[a0:b0], tick, Z=Z, atr_k=ak, max_bars=mb, amp=AMP, zon=ZON)
            if not len(M): continue
            for col in ("k", "i0", "iext"): M[col] = M[col].astype(np.int64) + a0
            M["defn"] = [f"{det}_a{int(a)}_z{int(z)}" for a, z in zip(M.amp, M.zon)]; M["a0"] = a0
            partes.append(M)
    defs = [f"{d}_a{a}_z{z}" for d in DETECTORES for a in range(len(AMP)) for z in range(len(ZON))]
    if not partes: return pd.DataFrame(columns=["k", "d", "i0", "pa", "ext", "rg"] + defs)
    D = pd.concat(partes, ignore_index=True)
    piv = pd.crosstab([D.k, D.d, D.i0], D.defn).reindex(columns=defs, fill_value=0).astype(bool)
    U = D.drop_duplicates(["k", "d", "i0"]).set_index(["k", "d", "i0"])[["pa", "ext", "rg", "velas", "nz", "nini25", "nini50", "a0"]]
    E = U.join(piv).reset_index().sort_values(["k", "i0"], kind="mergesort").reset_index(drop=True)
    k = E.k.to_numpy(np.int64); i0 = E.i0.to_numpy(np.int64)
    rate = pd.DataFrame(dict(ses=ses, v=v.astype(float))).groupby("ses").v.mean(); us = np.array(sorted(rate.index))
    base = pd.Series(np.r_[np.nan, rate.loc[us].to_numpy()[:-1]], index=us).reindex(ses).to_numpy(float)
    cv = np.r_[0.0, np.cumsum(v.astype(float))]
    with np.errstate(invalid="ignore", divide="ignore"):
        E["vrel"] = np.where(base[k] > 0, (cv[k + 1] - cv[i0]) / (k - i0 + 1) / base[k], np.nan)
        E["vel"] = E.rg.to_numpy(float) / np.maximum(E.velas.to_numpy(float), 1)
    E["ses"] = ses[k]; E["t"] = np.asarray(t, float)[k]
    for L in LOOKBACKS:
        r, cen = _hvn_nb(k, i0, E.a0.to_numpy(np.int64), E.d.to_numpy(np.int64), E.ext.to_numpy(float), E.rg.to_numpy(float),
                         np.asarray(ctx["vp_start"], np.int64), np.asarray(ctx["vp_px"], float), np.asarray(ctx["vp_vol"], float), L)
        E[f"hvn_{L}"] = r; E[f"hvn_cen_{L}"] = cen
    return agregar(E.drop(columns=["a0"]), ctx)


@njit(cache=False)
def _hvn_nb(k, i0, a0, d, B, rg, vps, vpx, vvo, L):
    """Volumen de la franja más allá de B (alto rg/2) en las velas [max(a0, i0−L), i0) sobre el mayor de las franjas vecinas del
    mismo alto (adentro del impulso y la siguiente más allá). Tope 100 (vecinas vacías). `cen`: centro de masa del volumen dentro
    de la franja más allá (0 = en B, 1 = en el borde lejano); NaN si no hubo volumen ahí."""
    n = len(k); out = np.full(n, np.nan); cen = np.full(n, np.nan)
    for q in range(n):
        lo = max(a0[q], i0[q] - L); hi = i0[q]
        if hi <= lo: continue
        w = rg[q] / 2.0
        if w <= 0: continue
        vb = 0.0; vi = 0.0; vf = 0.0; sx = 0.0
        for z in range(vps[lo], vps[hi]):
            x = d[q] * (vpx[z] - B[q])                     # > 0: más allá de B (sigue la dirección del impulso)
            if 0.0 <= x <= w:
                vb += vvo[z]; sx += vvo[z] * x / w
            elif -w <= x < 0.0: vi += vvo[z]
            elif w < x <= 2 * w: vf += vvo[z]
        m = max(vi, vf)
        out[q] = min(vb / m, 100.0) if m > 0 else (100.0 if vb > 0 else 0.0)
        if vb > 0: cen[q] = sx / vb
    return out, cen


# ------------------------------------------------------------------------------------------------------------ desenlaces
def limites(ctx, k):
    """Por evento: primer tick de la vela k+1, tick de fin de la espera (TOPE velas o fin de sesión o hueco) y tick de fin de sesión."""
    t = np.asarray(ctx["t"], float); ses = np.asarray(ctx["ses"]); ts = np.asarray(ctx["tstart"], np.int64); n = len(t)
    corte = np.r_[(ses[1:] != ses[:-1]) | (np.diff(t) > GAP_S), True]            # la vela i es la última de su tramo continuo
    fin = np.empty(n, np.int64); nxt = n
    for i in range(n - 1, -1, -1):
        if corte[i]: nxt = i + 1
        fin[i] = nxt                                                              # primera vela fuera del tramo de i
    k = np.asarray(k, np.int64)
    return ts[np.minimum(k + 1, n)], ts[np.minimum(np.minimum(k + 1 + TOPE, fin[k]), n)], fin


@njit(cache=False)
def _e0_nb(tpx, j0, jend, d, pa, sl, tp, pt, be):
    """Entrada a mercado en el primer tick de la vela k+1, hacia A. Devuelve R bruto (NaN si no hay ticks o D <= 0)."""
    s = -d; e = tpx[j0]; D = s * (pa - e)
    if D <= 0: return np.nan
    risk = sl * D; stop = -risk; pos = 1.0; real = 0.0; hecho_p = pt <= 0; hecho_b = be <= 0; fav = 0.0
    for j in range(j0 + 1, jend):
        fav = s * (tpx[j] - e)
        if fav <= stop: return (real + pos * fav) / risk               # stop a mercado: sale al tick que lo cruza (con el salto)
        if fav >= tp * D: return (real + pos * tp * D) / risk
        if not hecho_p and fav >= pt * D:
            real += 0.5 * pt * D; pos = 0.5; hecho_p = True
        if not hecho_b and fav >= be * D:
            stop = max(stop, 0.0); hecho_b = True
    return (real + pos * fav) / risk


@njit(cache=False)
def _ext_nb(tpx, ts, fin, j0, jw, d, pa, B, rg, e, r, b, tpm, c):
    """Espera la extensión más allá de B y la vuelta; devuelve (R bruto, riesgo en puntos). NaN si no hubo entrada (se canceló
    por pasar de c, tocó A antes, o venció la espera)."""
    s = -d; deep = B; armado = False; je = -1
    for j in range(j0, jw):
        p = tpx[j]
        if d * (p - deep) > 0: deep = p
        if d * (deep - B) > c * rg: return np.nan, np.nan
        if s * (p - pa) >= 0: return np.nan, np.nan
        if not armado and d * (deep - B) >= e * rg: armado = True
        if armado and d * (deep - p) >= r * rg:
            je = j; break
    if je < 0: return np.nan, np.nan
    ent = tpx[je]; stop = deep + d * b * rg; obj = pa if tpm == 0 else (pa + B) / 2.0
    risk = s * (ent - stop); rew = s * (obj - ent)
    if risk <= 0 or rew <= 0: return np.nan, np.nan
    kb = np.searchsorted(ts, je, side="right") - 1                      # vela de la entrada
    jend = ts[min(min(kb + 1 + 240, fin[kb]), len(ts) - 1)]
    fav = 0.0
    for j in range(je + 1, jend):
        fav = s * (tpx[j] - ent)
        if fav <= -risk: return fav / risk, risk                         # stop a mercado: al tick que lo cruza
        if fav >= rew: return rew / risk, risk
    return fav / risk, risk


@njit(cache=False)
def _mec_nb(tpx, j0, jw, d, pa, B, rg):
    """Mecanismo (sin ejecución): máxima extensión más allá de B (en rangos) antes de tocar A o la mitad, y si los tocó."""
    s = -d; deep = B; ext_a = 0.0; ext_m = np.nan; toca_a = 0; toca_m = 0; mid = (pa + B) / 2.0
    for j in range(j0, jw):
        p = tpx[j]
        if d * (p - deep) > 0: deep = p
        x = d * (deep - B) / rg
        if not toca_m and s * (p - mid) >= 0:
            toca_m = 1; ext_m = x
        if s * (p - pa) >= 0:
            toca_a = 1; break
        ext_a = x
    return ext_a, ext_m, toca_a, toca_m


def desenlaces(E: pd.DataFrame, ctx) -> pd.DataFrame:
    """Agrega a la tabla de eventos el mecanismo y el R bruto (y riesgo en puntos) de cada ejecución E0 y EXT."""
    if not len(E): return E
    tpx = np.asarray(ctx["tpx"], float); ts = np.asarray(ctx["tstart"], np.int64)
    k = E.k.to_numpy(np.int64); j0, jw, fin = limites(ctx, k)
    d = E.d.to_numpy(np.int64); pa = E.pa.to_numpy(float); B = E.ext.to_numpy(float); rg = E.rg.to_numpy(float)
    n = len(E); cols = {}
    mec = np.array([_mec_nb(tpx, j0[q], jw[q], d[q], pa[q], B[q], rg[q]) if jw[q] > j0[q] else (np.nan,) * 4 for q in range(n)], float)
    cols.update(ext_antes_A=mec[:, 0], ext_antes_mid=mec[:, 1], toca_A=mec[:, 2], toca_mid=mec[:, 3])
    for x in E0:
        sl, tp, pt, be = x
        r = np.array([_e0_nb(tpx, j0[q], jw[q], d[q], pa[q], sl, tp, pt, be) if jw[q] > j0[q] + 1 else np.nan for q in range(n)])
        D = np.where(jw > j0, np.abs(pa - tpx[np.minimum(j0, len(tpx) - 1)]), np.nan)
        cols[f"r_{nombre_e0(x)}"] = r; cols[f"k_{nombre_e0(x)}"] = sl * D
    for x in EXT:
        e, rr, b, tp, cc = x
        o = np.array([_ext_nb(tpx, ts, fin, j0[q], jw[q], d[q], pa[q], B[q], rg[q], e, rr, b, tp, cc) if jw[q] > j0[q] else (np.nan, np.nan)
                      for q in range(n)], float)
        cols[f"r_{nombre_ext(x)}"] = o[:, 0]; cols[f"k_{nombre_ext(x)}"] = o[:, 1]
    return pd.concat([E.reset_index(drop=True), pd.DataFrame(cols)], axis=1)


def tabla(ctx) -> pd.DataFrame:
    return desenlaces(eventos(ctx), ctx)
