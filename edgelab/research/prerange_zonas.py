"""PRERANGE-ZONAS (2026-10-31): barrido del rango 08:12-09:12 NY (disparos de `prerange_hft`) filtrado por CUÁNTAS zonas hay encima,
debajo y dentro del rango, cada posición con su distancia máxima en ATR. Spec: `docs/research/prerange_zonas_20261031/SPEC_PRERANGE_ZONAS.md`.

Zonas as-of: disponibles en una vela cerrada ANTES de la del disparo (zi < k), de hace <= VIDA velas y no terminadas (`t_fin_ns`).
AVZP2 se indexa en `t_decidida_ns`, no en `t_ns`: el almacén guarda el fin de la zona, que es anterior a la decisión.
Posición por el punto medio contra el rango. Distancia en ATR as-of k: encima/debajo, al borde más cercano; dentro, al borde barrido.
Conjunto = un indicador o un par. En un par la cantidad es min(nA, nB): ambos deben aportar, y el más denso no tapa al otro.
Por fila: disparo × conjunto × nivel de distancia (2 por posición), porque la cantidad depende de la distancia. Cortes de distancia y de
cantidad y lista de conjuntos: congelados en `prerange_zonas_cortes` desde el E0 sin desenlaces; DESC, REP y holdout usan los mismos.
"""
from __future__ import annotations

import glob
import hashlib
import os
from itertools import combinations, product

import numpy as np
import pandas as pd

from edgelab.research import prerange_hft as X
from edgelab.research import u1_combo_e0 as C
from edgelab.research import u1_zonas as UZ
from edgelab.research.grilla_generica import Variable
from edgelab.research.otr_930_sweep import njit
from edgelab.research.prerange_hft import niveles, niveles_lote  # noqa: F401
from edgelab.research.prerange_zonas_cortes import CORTES, CORTES_PRUEBA

NOMBRE = "PRERANGE-ZONAS"
CONFIRMADOR = True
INDICADORES = ["HFTZones2", "HFTZonesNQ"]
POS = ("sup", "inf", "den")
N_DIST, N_CANT, N_CONJ = 2, 3, 11                       # N_CONJ: tope por campaña; niveles sobrantes quedan vacíos
VIDA = 500
ZONA_AVZG_YM = 17                                       # 95/2/10/3, la BASE de U1-ZONAS-GRILLA: en YM no hay réplica AVZP2
Q_DIST, Q_CANT = (0.5, 0.9), (0.5, 0.9)
MIN_DISPAROS, MIN_SESIONES, COBERTURA_DEGENERADA = 30, 20, 0.95
IND_POR_INST = {"NQ": ("HFT2", "HFTNQ", "AVZP2", "AVCL", "BT2", "LUX_CFD", "LUX_FUT"),
                "ES": ("HFT2", "AVZP2", "AVCL", "BT2", "LUX_CFD", "LUX_FUT"),
                "YM": ("HFT2", "AVZG", "BT2", "LUX_CFD", "LUX_FUT")}          # sin almacén AVCL/YM ni AVZP2/YM

VARIABLES = [Variable("conjunto", "conj", "grupo", categoria=N_CONJ), Variable("gatillo", "gat", "grupo", categoria=len(X.GATILLOS))]
VARIABLES += [Variable(f"d_{p}", f"d_{p}", "grupo", categoria=N_DIST) for p in POS]
VARIABLES += [Variable(f"n_{p}", f"n_{p}", "ge", categoria=N_CANT) for p in POS]   # nivel 0 = cualquiera: el control sin cantidades
EJECUCIONES = [(md, "CIERRE", tp, "S_SWEEP") for md in X.MODOS_DIR for tp in ("OPUESTO_100", "MID_50")]
BASE = {"conjunto": 0, "gatillo": 0, "d_sup": 1, "d_inf": 1, "d_den": 1, "n_sup": 0, "n_inf": 0, "n_den": 0, "ejecución": 0}
EJES_ORDINALES = (5, 6, 7)
_COLS = ["k", "gat", "lado", "lo_rng", "hi_rng", "H_rng", "E_exc", "exc_rel", "atr"]


@njit(cache=False)
def _relativas_nb(kk, lo_r, hi_r, lado, atr, zi, zlo, zhi, zfin, vida):
    """(disparo, posición, distancia en ATR) por zona viva. `zi` ordenado; sólo zi < k. Oráculo: `relativas_py`."""
    a = np.searchsorted(zi, kk - vida, side="left"); b = np.searchsorted(zi, kk, side="left"); cap = int((b - a).sum())
    D = np.empty(cap, np.int64); P = np.empty(cap, np.int64); Y = np.empty(cap); c = 0
    for d in range(len(kk)):
        for z in range(a[d], b[d]):
            if zfin[z] <= kk[d]: continue
            mid = (zlo[z] + zhi[z]) / 2.0
            if mid > hi_r[d]:
                p = 0; x = max(0.0, zlo[z] - hi_r[d])
            elif mid < lo_r[d]:
                p = 1; x = max(0.0, lo_r[d] - zhi[z])
            else:
                p = 2; bd = hi_r[d] if lado[d] == 1 else lo_r[d]
                x = zlo[z] - bd if bd < zlo[z] else (bd - zhi[z] if bd > zhi[z] else 0.0)
            D[c] = d; P[c] = p; Y[c] = x / atr[d]; c += 1
    return D[:c], P[:c], Y[:c]


def relativas_py(kk, lo_r, hi_r, lado, atr, zi, zlo, zhi, zfin, vida):
    fil = []
    for d in range(len(kk)):
        for z in range(len(zi)):
            if not kk[d] - vida <= zi[z] < kk[d] or zfin[z] <= kk[d]: continue
            m = (zlo[z] + zhi[z]) / 2
            if m > hi_r[d]: fil.append((d, 0, max(0.0, zlo[z] - hi_r[d]) / atr[d]))
            elif m < lo_r[d]: fil.append((d, 1, max(0.0, lo_r[d] - zhi[z]) / atr[d]))
            else:
                bd = hi_r[d] if lado[d] == 1 else lo_r[d]; fil.append((d, 2, max(0.0, zlo[z] - bd, bd - zhi[z]) / atr[d]))
    return sorted(fil)


def _control(ctx, paso):
    """SOLO preflight y tests: zona de 2 ticks cada `paso` velas."""
    k = np.arange(paso, len(ctx["c"]), paso); px = ctx["c"][k] + (k % 7 - 3) * ctx["tick"] * 8
    return pd.DataFrame(dict(t_ns=ctx["t"][k].astype(np.int64) * 10**9, lo=px, hi=px + ctx["tick"]))


def _almacen(ind, sensor, ent):
    f = glob.glob(f"{ent}/**/ZONAS_{ind}_{sensor}.parquet", recursive=True)
    return pd.read_parquet(f[0]) if f else None


def cargar_zonas(ctx, ind, sensor=None):
    """Zonas de un indicador, sin caer nunca a otra fuente."""
    if "zonas" in ctx: return ctx["zonas"][ind]
    sensor = sensor or ctx.get("sensor") or os.environ.get("SENSOR"); ent = os.environ.get("ENTRADA", "/kaggle/input")
    if ind == "LUX_FUT": return C.lux_almacen(ctx)
    if ind == "LUX_CFD": return C.trasladar(C.lux_almacen(ctx["conf"]), ctx["conf"], ctx)[0]
    if ind in ("HFT2", "HFTNQ"): return X.cargar(ind, sensor, ent)
    if ind == "AVZP2":
        Z = _almacen(ind, sensor, ent)
        if Z is None: return UZ.cargar(ind, sensor, ent)
        Z = Z[Z.t_decidida_ns > 0]
        return Z.assign(t_ns=np.maximum(Z.t_ns.to_numpy(np.int64), Z.t_decidida_ns.to_numpy(np.int64)))[["t_ns", "lo", "hi"]].sort_values("t_ns", kind="stable", ignore_index=True)
    if ind == "AVZG":
        Z = _almacen(ind, sensor, ent)
        if Z is None: raise FileNotFoundError(f"sin almacén AVZG/{sensor} en {ent}")
        return Z[Z.zona == ZONA_AVZG_YM][["t_ns", "lo", "hi"]].reset_index(drop=True)
    return UZ.cargar(ind, sensor, ent)


def _indexar(Z, t):
    """zi = primera vela que cierra en o después de la disponibilidad. Lo anterior a la primera vela queda afuera: su edad no se conoce."""
    t = np.asarray(t, np.int64); ts = (Z.t_ns.to_numpy(np.int64) + 999_999_999) // 1_000_000_000
    ok = (ts >= t[0]) & (ts <= t[-1]); zi = np.searchsorted(t, ts[ok], side="left").astype(np.int64)
    a, b = Z.lo.to_numpy(float)[ok], Z.hi.to_numpy(float)[ok]
    fin = np.full(len(zi), np.iinfo(np.int64).max, np.int64)
    if "t_fin_ns" in Z:
        tf = Z.t_fin_ns.to_numpy(np.int64)[ok]; m = tf > 0; fin[m] = np.searchsorted(t, (tf[m] + 999_999_999) // 1_000_000_000, side="left")
    o = np.argsort(zi, kind="stable")
    return zi[o], np.minimum(a, b)[o], np.maximum(a, b)[o], fin[o]


def base_disparos(ctx) -> pd.DataFrame:
    t, c, tick = np.asarray(ctx["t"], np.int64), np.asarray(ctx["c"], float), float(ctx["tick"])
    h, l = np.asarray(ctx["h"], float), np.asarray(ctx["l"], float)
    K, G, LA, F = X._disparos_nb(t, np.asarray(ctx["o"], float), h, l, c, np.asarray(ctx["ses"], np.int64), tick, X.INI_RANGO, X.FIN_RANGO, X.FIN_BUSQUEDA,
                                 X.MIN_VELAS_RANGO, X.MIN_ALTO_TICKS)
    return pd.DataFrame(dict(k=K, gat=G, lado=LA, lo_rng=F[:, 0], hi_rng=F[:, 1], H_rng=F[:, 2], E_exc=F[:, 3], exc_rel=F[:, 4], atr=F[:, 5]))


def relativas(B, ctx, ind):
    zi, lo, hi, fin = _indexar(cargar_zonas(ctx, ind), ctx["t"])
    return _relativas_nb(B.k.to_numpy(np.int64), B.lo_rng.to_numpy(float), B.hi_rng.to_numpy(float), B.lado.to_numpy(np.int64), B.atr.to_numpy(float), zi, lo, hi, fin, VIDA)


def conteos(rel, n, cortes_d) -> np.ndarray:
    """(disparos, 3 posiciones, N_DIST): zonas a distancia <= cada corte."""
    D, P, Y = rel; out = np.zeros((n, 3, N_DIST), np.int64)
    for p, nom in enumerate(POS):
        m = P == p
        for j, c in enumerate(cortes_d[nom]): out[:, p, j] = np.bincount(D[m & (Y <= c)], minlength=n)
    return out


def _conj(cuenta, nombre):
    a = nombre.split("+")
    return cuenta[a[0]] if len(a) == 1 else np.minimum(cuenta[a[0]], cuenta[a[1]])


def disparos(ctx: dict) -> pd.DataFrame:
    """Una fila por disparo × conjunto × (d_sup, d_inf, d_den). Las cantidades salen como nivel 0..N_CANT-1 con cortes congelados."""
    B = base_disparos(ctx); sensor = ctx.get("sensor") or os.environ.get("SENSOR")
    if not len(B): return pd.DataFrame(columns=_COLS + ["conj"] + [v.columna for v in VARIABLES[2:]])
    cf = CORTES.get(sensor) if sensor else CORTES_PRUEBA
    if sensor and not cf: raise ValueError(f"{sensor}: sin cortes congelados del E0")
    if not sensor and "zonas" not in ctx: ctx = dict(ctx, zonas={"A": _control(ctx, 15), "B": _control(ctx, 22)})
    if len(cf["conjuntos"]) > N_CONJ: raise ValueError("más conjuntos que N_CONJ")
    usados = sorted({i for c in cf["conjuntos"] for i in c.split("+")}); n = len(B)
    cuenta = {i: conteos(relativas(B, ctx, i), n, cf["dist"][i]) for i in usados}; out = []
    for ci, nombre in enumerate(cf["conjuntos"]):
        N = _conj(cuenta, nombre); cc = cf["cant"][nombre]
        niv = [[np.searchsorted(cc[p][j], N[:, pi, j], side="right") for j in range(N_DIST)] for pi, p in enumerate(POS)]
        for ds, di, dd in product(range(N_DIST), repeat=3):
            out.append(B.assign(conj=ci, d_sup=ds, d_inf=di, d_den=dd, n_sup=niv[0][ds], n_inf=niv[1][di], n_den=niv[2][dd]))
    return pd.concat(out, ignore_index=True).sort_values(["k", "gat", "lado", "conj", "d_sup", "d_inf", "d_den"], kind="stable").reset_index(drop=True)


def _qs(x, qs):
    return [float(np.quantile(x, q)) for q in qs] if len(x) else [float("inf")] * len(qs)


def censo(ctx, inds) -> dict:
    """E0 sin desenlaces. Cortes por cuantiles y, por conjunto: evaluables, degeneradas, duplicadas y distribución."""
    B = base_disparos(ctx); n = len(B); ses = np.asarray(ctx["ses"])[B.k.to_numpy(np.int64)]; gat = B.gat.to_numpy()
    dist, cuenta, zonas = {}, {}, {}
    for i in inds:
        rel = relativas(B, ctx, i); _, P, Y = rel; dist[i] = {nom: _qs(Y[P == p], Q_DIST) for p, nom in enumerate(POS)}
        cuenta[i] = conteos(rel, n, dist[i]); zonas[i] = dict(vistas=len(Y), por_pos={nom: int((P == p).sum()) for p, nom in enumerate(POS)})
    nombres = list(inds) + [f"{a}+{b}" for a, b in combinations(inds, 2)]; cant, filas, vistos = {}, {}, {}
    for nom in nombres:
        N = _conj(cuenta, nom); cant[nom] = {}
        f = dict(combinaciones=0, evaluables=0, degeneradas=0, duplicadas=0, unicas=0, sin_disparos=0, cortes_colapsados=0, frac_con_zona={}, n_q50={})
        for pi, p in enumerate(POS):
            cant[nom][p] = []
            for j in range(N_DIST):
                x = N[:, pi, j]; c = [max(1.0, float(np.ceil(v))) if np.isfinite(v) else float("inf") for v in _qs(x[x > 0], Q_CANT)]
                if c[0] == c[1]: f["cortes_colapsados"] += 1
                cant[nom][p].append(c)
            f["frac_con_zona"][p] = round(float((N[:, pi, 1] > 0).mean()), 4); f["n_q50"][p] = float(np.median(N[:, pi, 1]))
        for ds, di, dd in product(range(N_DIST), repeat=3):
            d3 = (ds, di, dd); ms = [[N[:, pi, d3[pi]] >= ([0.0] + cant[nom][p][d3[pi]])[v] for v in range(N_CANT)] for pi, p in enumerate(POS)]
            for ns, ni, nd in product(range(N_CANT), repeat=3):
                if ns == ni == nd == 0: continue
                m = ms[0][ns] & ms[1][ni] & ms[2][nd]
                for g in range(len(X.GATILLOS)):
                    f["combinaciones"] += 1; mg = m & (gat == g); c = int(mg.sum()); tot = max(int((gat == g).sum()), 1)
                    if c == 0: f["sin_disparos"] += 1; continue
                    if c >= COBERTURA_DEGENERADA * tot: f["degeneradas"] += 1; continue
                    if c < MIN_DISPAROS or len(np.unique(ses[mg])) < MIN_SESIONES: continue
                    f["evaluables"] += 1; h = hashlib.sha1(np.packbits(mg).tobytes()).digest()
                    if h in vistos: f["duplicadas"] += 1
                    else: vistos[h] = nom; f["unicas"] += 1
        filas[nom] = f
    return dict(disparos=n, sesiones=len(np.unique(ses)), zonas=zonas, dist=dist, cant=cant, conjuntos=filas)


def podar(c: dict, tope: int = N_CONJ, min_unicas: int = 20) -> list:
    """Sin P&L: conjuntos con al menos `min_unicas` combinaciones únicas, los de más únicas primero, hasta `tope`. Empate: nombre."""
    v = [(f["unicas"], n) for n, f in c["conjuntos"].items() if f["unicas"] >= min_unicas]
    return [n for _, n in sorted(v, key=lambda x: (-x[0], x[1]))[:tope]]
