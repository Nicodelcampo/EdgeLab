"""LUXIMB-GRILLA (2026-10-24): la familia LUX-IMB de impulsos por una grilla masiva, con la regla del visor como UNA celda.

Pedido de Nico (2026-10-24): correr la familia LUX-IMB por una grilla de variantes filtrada por el embudo, igual que se encontró
U1, con la regla congelada del visor (fade, TP 1,0·D / SL 0,2·D, entrada al cierre de la confirmación −1 tick, tope 240 min)
como una celda más. Spec: docs/research/luximb_grilla_20261024/SPEC.md (justificación económica, refutación y espacio de eventos).

Objeto (idéntico al de `tools/luximb_parity/luximb_impulsos.py --modo inicio`, congelado en el candidato del visor):
  1. Impulsos ESPEJO-IND en M1 (`detectar`, port del detector con el fix de supervivencia del 21/10): neto >= 3·ATR(14) de la
     vela anterior en <= 20 velas, eficiencia >= 0,3; A = origen (i0), extremo vela a vela; se confirma por retroceso >= 30 %,
     por tiempo o por hueco (> 30 min). Precios en ticks, como el original.
  2. Zonas LUX-IMB OG+VI M1 (`areas_expansion.zonas`, paridad NT8 1507/1507) ATRAVESADAS enteras por el tramo A -> extremo
     después de nacer, con vida de 500 velas (la definición de `crossed`).
  3. Marca en tiempo real: la PRIMERA vela M1 del impulso en curso (desde que el detector lo activa hasta su confirmación) en la
     que el tramo cumple a la vez la amplitud (>= percentil causal de los tramos ya confirmados, ventana 2.000, mínimo 500, y
     >= un piso en puntos), la rapidez (>= el mínimo causal, p0) y la condición de zonas (>= `min_ini` zonas en el `frac` inicial
     del rango y >= 50 % del total ahí). Cada definición (amplitud × zonas) marca su propia vela: es una perilla de EVENTO
     (`categoria`), no un filtro sobre una vela fija.
Diferencia declarada con el original: la rapidez se mide en velas M1 (el original cuenta velas de 25 ticks). Con una vela de 25t
por minuto (fixture del test del oráculo) son la misma cuenta; en datos reales sólo cambia el piso p0 de rapidez.

Perillas que filtran (sólo pasado de la vela de marca k): rapidez y actividad del impulso, régimen de volatilidad diaria y hora
(`edgelab/research/agente/regimen.py`) y dirección. Ejecuciones: FADE (hacia A) y CONTINUACIÓN, entrada al cierre / tick
siguiente / límite a una fracción de D, TP y SL como múltiplos de D = distancia de la entrada a A, con y sin BE.
El tope de 240 velas y el fin de sesión los pone el simulador común (`areas_expansion.simular`); no son perilla acá.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.bridge.indicators.espejo_impulsos import atr_prev
from edgelab.research import areas_expansion as AX
from edgelab.research.agente.regimen import VARIABLES_REGIMEN, agregar
from edgelab.research.grilla_generica import Variable

try:
    from numba import njit
except ImportError:                                    # sin numba: misma lógica en Python (lenta, sólo para tests mínimos)
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "LUXIMB-GRILLA"
INDICADORES = ["LUX-IMB"]       # el detector de impulsos es la lógica propia del experimento (ESPEJO-IND figura VERIFICAR; ver SPEC §3)

# --- detector de impulsos (valores del candidato del visor: luximb_impulsos.py --atr-k 3 --max-bars 20, defaults de ESPEJO-IND)
ATR_K, ATR_N, MAX_BARS, E_MIN, RETR, GAP_RESET_S = 3.0, 14, 20, 0.3, 0.3, 1800.0
VIDA = 500                      # vida de una zona para contar como atravesada (velas)
HIST, MIN_HIST = 2000, 500      # ventana de tramos confirmados para los percentiles causales
SHARE_INI = 0.5                 # >= 50 % de las zonas atravesadas en la franja inicial

# --- perillas de EVENTO (cada combinación marca su propia vela) -------------------------------------------------------------
# amplitud: (percentil causal de la amplitud de los tramos confirmados, piso en puntos). Orden de menos a más exigente.
AMP = ((60.0, 0.0), (60.0, 60.0), (80.0, 60.0), (90.0, 60.0))
# zonas: (franja inicial del rango, mínimo de zonas atravesadas en esa franja); (0, 0) = SIN condición de zonas (control).
ZON = ((0.0, 0), (0.25, 1), (0.25, 3), (0.25, 5), (0.50, 3))
FRACS = (0.25, 0.50)
VISOR_AMP, VISOR_ZON = 1, 2     # celda del visor: max(p60, 60 pts) y >= 3 zonas en el 25 % inicial

VARIABLES = [
    Variable("amplitud", "amp", "grupo", categoria=len(AMP)),
    Variable("zonas", "zon", "grupo", categoria=len(ZON)),
    Variable("rapidez", "vel", "extremos", cuantiles=3),           # puntos por vela M1 de A al extremo en la marca
    Variable("actividad", "vrel", "extremos", cuantiles=3),        # volumen por vela del impulso / de la sesión anterior
    VARIABLES_REGIMEN["vol_diaria"],                               # rango de la sesión anterior / mediana de las 20 previas
    VARIABLES_REGIMEN["hora"],                                     # bloque UTC fijo (Asia, Europa, NY, cierre)
    Variable("direccion", "dirc", "eq_any", categoria=2),          # 0 impulso alcista · 1 bajista
]
EJES_ORDINALES = (0,)           # la amplitud es ordinal (de menos a más exigente)

# --- ejecuciones: (lado, entrada, TP en D, SL en D, BE) -------------------------------------------------------------------
ENTRADAS = ("CIERRE", "SIG", "LIM10", "LIM25")     # cierre de la marca · primer tick siguiente · límite a 10 % / 25 % de D
LIM_FRAC = {"LIM10": 0.10, "LIM25": 0.25}          # FADE: más allá del cierre (vender más arriba); CONT: retroceso hacia A
_TP_F, _SL_F = (0.5, 1.0, 1.5), (0.1, 0.2, 0.5)
_TP_C, _SL_C = (0.5, 1.0, 1.5), (0.2, 0.5)


def _salidas(tps, sls):
    """TP × SL, y BE sólo donde puede armarse antes del objetivo (TP >= 2·SL): un BE que nunca se arma es una perilla muerta."""
    return [(tp, sl, be) for tp in tps for sl in sls for be in (0, 1) if be == 0 or tp >= 2 * sl]


EJECUCIONES = [("FADE", en, tp, sl, be) for en in ENTRADAS for tp, sl, be in _salidas(_TP_F, _SL_F)] + \
              [("CONT", en, tp, sl, be) for en in ENTRADAS for tp, sl, be in _salidas(_TP_C, _SL_C)]
VISOR_EJ = ("FADE", "CIERRE", 1.0, 0.2, 0)
BASE = {"amplitud": VISOR_AMP, "zonas": VISOR_ZON, "ejecución": EJECUCIONES.index(VISOR_EJ)}       # la regla del visor


# ----------------------------------------------------------------------------------------------- detector (target-free)
# atr_prev: la del indicador (ATR(n) cerrado en la vela anterior), importada; no se copia (tests/test_existente.py).


@njit(cache=False)
def _detectar_nb(t, H, L, C, thr_arr, W, e0, r, gap):
    """Port de `luximb_impulsos.detect_act` (oráculo: test_detector_igual_al_original). Devuelve (d, a, ext, i0, iext, jconf, why, jact)."""
    n = len(C); path = np.zeros(n)
    for j in range(1, n): path[j] = path[j - 1] + abs(C[j] - C[j - 1])
    od = np.zeros(n, np.int64); oa = np.zeros(n); oe = np.zeros(n); oi0 = np.zeros(n, np.int64); oie = np.zeros(n, np.int64)
    oj = np.zeros(n, np.int64); ow = np.zeros(n, np.int64); oja = np.zeros(n, np.int64); m = 0
    active = False; floorI = 0; d = 0; i0 = 0; a = 0.0; ext = 0.0; iext = 0; thr_t = 0.0; jact = 0
    for j in range(W, n):
        if t[j] - t[j - 1] > gap:
            if active:
                od[m] = d; oa[m] = a; oe[m] = ext; oi0[m] = i0; oie[m] = iext; oj[m] = j - 1; ow[m] = 3; oja[m] = jact; m += 1
            active = False
        if not active:
            w0 = max(j - W, floorI)
            if w0 >= j: continue
            thr = max(thr_arr[j], 2.0)
            if not thr < 1e17: continue
            ia = w0; ib = w0
            for q in range(w0 + 1, j + 1):
                if L[q] < L[ia]: ia = q
                if H[q] > H[ib]: ib = q
            found = False; bnet = 0.0
            if ia < j:
                net = C[j] - L[ia]; pp = path[j] - path[ia]
                if net >= thr and pp > 0 and (C[j] - C[ia]) / pp >= e0:
                    found = True; bnet = net; d = 1; i0 = ia; a = L[ia]; ext = H[j]
            if ib < j:
                net2 = H[ib] - C[j]; pp2 = path[j] - path[ib]
                if net2 >= thr and pp2 > 0 and (C[ib] - C[j]) / pp2 >= e0 and ((not found) or net2 > bnet):
                    found = True; d = -1; i0 = ib; a = H[ib]; ext = L[j]
            if found:
                active = True; iext = j; thr_t = thr; jact = j
            continue
        if d == 1 and H[j] > ext:
            ext = H[j]; iext = j
        elif d == -1 and L[j] < ext:
            ext = L[j]; iext = j
        tot = abs(ext - a)
        retr = (ext - L[j]) if d == 1 else (H[j] - ext)
        why = 1 if retr >= max(2.0, r * tot) else (2 if j - i0 >= W else 0)
        if why == 0: continue
        if tot >= thr_t:
            od[m] = d; oa[m] = a; oe[m] = ext; oi0[m] = i0; oie[m] = iext; oj[m] = j; ow[m] = why; oja[m] = jact; m += 1
        floorI = iext; active = False
    if active:
        od[m] = d; oa[m] = a; oe[m] = ext; oi0[m] = i0; oie[m] = iext; oj[m] = n - 1; ow[m] = 4; oja[m] = jact; m += 1
    return od[:m], oa[:m], oe[:m], oi0[:m], oie[:m], oj[:m], ow[:m], oja[:m]


def detectar(t, h, l, c, tick):
    """Tramos del detector sobre precios (se pasan a ticks enteros como en el original). Diccionario de arreglos."""
    H, L, C = np.round(h / tick), np.round(l / tick), np.round(c / tick)
    thr = ATR_K * atr_prev(H, L, C, ATR_N)
    if len(C) <= MAX_BARS: z = np.zeros(0, np.int64); return dict(d=z, a=np.zeros(0), ext=np.zeros(0), i0=z, iext=z, jconf=z, why=z, jact=z)
    r = _detectar_nb(np.asarray(t, float), H, L, C, thr, MAX_BARS, E_MIN, RETR, GAP_RESET_S)
    return dict(zip(("d", "a", "ext", "i0", "iext", "jconf", "why", "jact"), r))


@njit(cache=False)
def _tabla_nb(d, i0, ja, ic, pa, p0c, zs, ze, zi, zlo, zhi, h, l, vida, fracs):
    """Por tramo y por vela kb de [ja, ic] (el impulso en curso): extremo, rango, zonas atravesadas (regla de `crossed`) y cuántas
    caen en cada franja inicial. Una zona cuenta en kb si su cruce completo (primero el borde cercano, después el lejano, desde
    max(i0, nacimiento+1)) ocurrió en <= kb, a <= `vida` velas de su nacimiento, y está entera dentro de [A, extremo en kb].
    Oráculo: test_tabla_igual_a_crossed (llama al `crossed` original con empates)."""
    G = len(d); nrow = 0
    for g in range(G): nrow += ic[g] - ja[g] + 1
    nf = len(fracs)
    og = np.zeros(nrow, np.int64); okb = np.zeros(nrow, np.int64); oext = np.zeros(nrow); oie = np.zeros(nrow, np.int64)
    org = np.zeros(nrow); onz = np.zeros(nrow, np.int64); oni = np.zeros((nrow, nf), np.int64)
    row = 0
    for g in range(G):
        up = d[g] == 1; a = i0[g]; b = ic[g]; nz_c = ze[g] - zs[g]
        J = np.full(nz_c, -1, np.int64)
        for q in range(nz_c):
            z = zs[g] + q
            if up and zlo[z] < p0c[g]: continue
            if (not up) and zhi[z] > p0c[g]: continue
            s = max(a, zi[z] + 1)
            if s > b: continue
            j0 = -1
            for j in range(s, b + 1):
                if (up and l[j] <= zlo[z]) or ((not up) and h[j] >= zhi[z]):
                    j0 = j; break
            if j0 < 0: continue
            jf = -1
            for j in range(j0, b + 1):
                if (up and h[j] >= zhi[z]) or ((not up) and l[j] <= zlo[z]):
                    jf = j; break
            if jf < 0 or jf - zi[z] > vida: continue
            J[q] = jf
        ext = h[ja[g]] if up else l[ja[g]]; iext = ja[g]
        for kb in range(ja[g], b + 1):
            if kb > ja[g]:
                if up and h[kb] > ext:
                    ext = h[kb]; iext = kb
                elif (not up) and l[kb] < ext:
                    ext = l[kb]; iext = kb
            rg = abs(ext - pa[g])
            og[row] = g; okb[row] = kb; oext[row] = ext; oie[row] = iext; org[row] = rg
            nz = 0
            for q in range(nz_c):
                if J[q] < 0 or J[q] > kb: continue
                z = zs[g] + q
                if up and zhi[z] > ext: continue
                if (not up) and zlo[z] < ext: continue
                nz += 1
                pos = abs((zhi[z] + zlo[z]) / 2 - pa[g]) / rg
                for f in range(nf):
                    if pos < fracs[f]: oni[row, f] += 1
            onz[row] = nz; row += 1
    return og, okb, oext, oie, org, onz, oni


def _umbrales(R, V, ics, kbs, pcts):
    """Para cada vela kb: percentiles causales de amplitud (tramos con jconf < kb, ventana HIST), mínimo de rapidez (p0) y si hay
    MIN_HIST tramos. Mismas llamadas a np.percentile que el original (mismo redondeo)."""
    e = np.searchsorted(ics, kbs, side="left"); b0 = np.maximum(0, e - HIST); ok = (e - b0) >= MIN_HIST
    U = np.full((len(kbs), len(pcts)), np.nan); vmin = np.full(len(kbs), np.nan)
    filas = np.flatnonzero(ok); orden = filas[np.argsort(e[filas], kind="mergesort")]
    vals, ini, cnt = np.unique(e[orden], return_index=True, return_counts=True)
    for ee, i_, n_ in zip(vals, ini, cnt):
        bb = max(0, int(ee) - HIST); m = orden[i_:i_ + n_]
        U[m] = np.percentile(R[bb:ee], list(pcts)); vmin[m] = np.percentile(V[bb:ee], 0.0)
    return ok, U, vmin


def marcas_segmento(t, o, h, l, c, tick, Z=None):
    """Todas las marcas de un segmento contiguo (un contrato): DataFrame con una fila por (definición de amplitud, definición de
    zonas, tramo) marcado. Columnas: k (vela de marca), d, i0, iext, pa (precio de A), ext, rg, velas, nz, nini25, nini50, amp, zon."""
    T = detectar(t, h, l, c, tick)
    cols = ["k", "d", "i0", "iext", "pa", "ext", "rg", "velas", "nz", "nini25", "nini50", "amp", "zon"]
    if not len(T["d"]): return pd.DataFrame(columns=cols)
    Z = Z if Z is not None else AX.zonas(t, o, h, l, c)
    oz = np.argsort(Z["zi"], kind="mergesort"); zi, zlo, zhi = Z["zi"][oz].astype(np.int64), Z["zlo"][oz].astype(float), Z["zhi"][oz].astype(float)
    orden = np.lexsort((T["i0"], T["jconf"]))                                       # como el original: por (jconf, i0)
    T = {k: v[orden] for k, v in T.items()}
    d, i0, ja, ic = T["d"], T["i0"], T["jact"], T["jconf"]
    pa = T["a"] * tick; pb = T["ext"] * tick
    R = np.array([round(float(x), 8) for x in np.abs(pb - pa)])                    # round() de Python, como el original
    velas_fin = T["iext"] - i0 + 1; V = np.array([round(float(x) / max(int(n_), 1), 10) for x, n_ in zip(R, velas_fin)])
    p0c = np.where(d == 1, l[i0], h[i0])                                            # el original usa l[a] / h[a] en crossed
    zs = np.searchsorted(zi, i0 - VIDA, side="left"); ze = np.searchsorted(zi, ic, side="left")
    g, kb, ext, iext, rg, nz, nini = _tabla_nb(d.astype(np.int64), i0.astype(np.int64), ja.astype(np.int64), ic.astype(np.int64), pa, p0c,
                                              zs.astype(np.int64), ze.astype(np.int64), zi, zlo, zhi, h.astype(float), l.astype(float),
                                              VIDA, np.array(FRACS, float))
    if not len(g): return pd.DataFrame(columns=cols)
    ok, U, vmin = _umbrales(R, V, ic, kb, [p for p, _ in AMP])
    vl = iext - i0[g] + 1
    with np.errstate(invalid="ignore", divide="ignore"):
        rapido = ok & (rg / np.maximum(vl, 1) >= vmin)
    filas = []
    for ai, (_, piso) in enumerate(AMP):
        c_amp = rapido & (rg >= np.maximum(U[:, ai], piso))
        for zj, (frac, mini) in enumerate(ZON):
            if mini == 0: cond = c_amp
            else:
                n_ini = nini[:, FRACS.index(frac)]
                cond = c_amp & (n_ini >= mini) & (n_ini >= SHARE_INI * nz)
            idx = np.flatnonzero(cond)
            if not len(idx): continue
            gg, primera = np.unique(g[idx], return_index=True); r_ = idx[primera]   # la PRIMERA vela del tramo que cumple
            filas.append(pd.DataFrame(dict(k=kb[r_], d=d[gg], i0=i0[gg], iext=iext[r_], pa=pa[gg], ext=ext[r_], rg=rg[r_], velas=vl[r_], nz=nz[r_],
                                           nini25=nini[r_, 0], nini50=nini[r_, 1], amp=ai, zon=zj)))
    return pd.concat(filas, ignore_index=True)[cols] if filas else pd.DataFrame(columns=cols)


# ----------------------------------------------------------------------------------------------- interfaz de grilla_generica
def disparos(ctx):
    o, h, l, c, v, t, ses, seg = (np.asarray(ctx[x]) for x in ("o", "h", "l", "c", "v", "t", "ses", "seg"))
    tick = float(ctx["tick"]); partes = []
    for sg in pd.unique(seg):
        idx = np.flatnonzero(seg == sg); a0, b0 = idx[0], idx[-1] + 1
        M = marcas_segmento(t[a0:b0], o[a0:b0], h[a0:b0], l[a0:b0], c[a0:b0], tick)
        if not len(M): continue
        for col in ("k", "i0", "iext"): M[col] = M[col].astype(np.int64) + a0
        partes.append(M)
    cols = ["k", "d", "i0", "pa", "rg", "amp", "zon", "vel", "vrel", "dirc", "nz", "nini25"]
    if not partes: return pd.DataFrame(columns=cols + [vv.columna for vv in VARIABLES_REGIMEN.values()])
    D = pd.concat(partes, ignore_index=True)
    rate = pd.DataFrame(dict(ses=ses, v=v.astype(float))).groupby("ses").v.mean(); us = np.array(sorted(rate.index))
    base_rate = pd.Series(np.r_[np.nan, rate.loc[us].to_numpy()[:-1]], index=us).reindex(ses).to_numpy(float)
    k = D.k.to_numpy(np.int64); i0 = D.i0.to_numpy(np.int64); cv = np.r_[0.0, np.cumsum(v.astype(float))]
    with np.errstate(invalid="ignore", divide="ignore"):
        vol_imp = (cv[k + 1] - cv[i0]) / (k - i0 + 1)
        D["vrel"] = np.where(base_rate[k] > 0, vol_imp / base_rate[k], np.nan)
        D["vel"] = D.rg.to_numpy(float) / np.maximum(D.velas.to_numpy(float), 1)
    D["dirc"] = np.where(D.d.to_numpy() == 1, 0, 1)
    D = agregar(D, ctx)
    return D.sort_values(["k", "amp", "zon", "i0"], kind="mergesort").reset_index(drop=True)


def _niveles_arr(k, d, pa, ck, tick, ej):
    """Arreglo (n, 7) de (start, limite, s, entrada, stop, objetivo, be) con NaN donde la ejecución no aplica. Una sola cuenta
    para `niveles` y `niveles_lote` (son la misma aritmética: el preflight exige que coincidan exactamente)."""
    lado, en, ftp, fsl, be = ej; n = len(k)
    k = np.asarray(k, float); d = np.asarray(d, float); pa = np.asarray(pa, float); ck = np.asarray(ck, float)
    e_ref = ck - d * tick                                       # el visor: cierre de la marca, 1 tick en contra (niveles desde acá)
    D0 = d * (e_ref - pa)
    if en in ("CIERRE", "SIG"):
        lim = 0.0 if en == "CIERRE" else 2.0; ent = ck.copy(); base = e_ref; Db = D0
    else:
        paso = np.ceil(LIM_FRAC[en] * D0 / tick) * tick
        ent = ck + d * paso if lado == "FADE" else ck - d * paso    # FADE: vender más arriba (o comprar más abajo); CONT: retroceso
        lim = 1.0; base = ent; Db = d * (ent - pa)
    if lado == "FADE":
        s = -d; tp = base - d * ftp * Db; st = base + d * fsl * Db
    else:
        s = d; tp = base + d * ftp * Db; st = base - d * fsl * Db
    ok = (D0 > 0) & (Db > 0) & ((tp - ent) * s > 0) & ((ent - st) * s > 0)       # como el visor: un stop a < 1 tick también se opera
    X = np.column_stack([k, np.full(n, lim), s, ent, st, tp, np.full(n, float(be))])
    X[~ok] = np.nan
    return X


def niveles_lote(D, ej, ctx):
    k = D.k.to_numpy(np.int64)
    return _niveles_arr(k, D.d.to_numpy(float), D.pa.to_numpy(float), np.asarray(ctx["c"], float)[k], float(ctx["tick"]), ej)


def niveles(r, ej, ctx):
    k = int(r["k"])
    X = _niveles_arr(np.array([k]), np.array([float(r["d"])]), np.array([float(r["pa"])]), np.array([float(ctx["c"][k])]), float(ctx["tick"]), ej)[0]
    if not np.isfinite(X[0]): return None
    return int(X[0]), int(X[1]), int(X[2]), float(X[3]), float(X[4]), float(X[5]), int(X[6])


def celda_visor(cortes=None) -> list:
    """Índices de la celda de la regla del visor en la grilla (resto de las perillas en «cualquiera»)."""
    import sys
    from edgelab.research import grilla_generica as GG
    P = GG.perillas(sys.modules[__name__], cortes or {})
    nombres = [p.nombre for p in P]
    return [BASE.get(n, P[i].tamano_celdas() - 1) for i, n in enumerate(nombres)]
