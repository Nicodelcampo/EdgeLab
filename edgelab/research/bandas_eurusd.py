"""BANDAS-EURUSD (2026-11-11, pedido de Nico): ¿hay alguna distancia entre el precio y una banda de concentración OG+VI
(`edgelab/bridge/indicators/bandas_concentracion.py`) desde la cual ir HACIA la banda, con 1:1 o 1:1,5 y objetivo en el inicio
(borde cercano) o en el final (borde lejano) de la banda, sea rentable? Con distintos criterios de muerte de la banda.
Pre-registro: docs/research/bandas_concentracion_20261111/PREREGISTRO_BANDAS_EURUSD.md. Cadena estándar (edgelab/research/tablas.py).

Construcción (causal; todo con velas ≤ k):
  1. Zonas LUX-IMB OG+VI en M1 (`areas_expansion.zonas`, vida 500 min; en FX la paridad con NT8 está en ABSTENCIÓN: declarado).
  2. Bandas con la regla de `bandas_concentracion.detectar` (alto 8 pips, umbral 22, vida 500 min), portada a numba con el mismo
     orden y desempates (test de paridad contra la referencia). Cada extensión de la banda queda registrada con su hora: «viva
     según el detector» en t se sabe en t (t ≤ última extensión ≤ t + vida).
  3. Evento: la PRIMERA vela (cierre) de las 72 h posteriores al nacimiento de la banda en que la distancia del cierre al borde
     cercano pasa de > x a ≤ x pips, con el precio fuera de la banda. x ∈ DISTANCIAS.
  4. Operación: a mercado hacia la banda (primer tick de la vela siguiente). Objetivo: borde cercano («ini») o lejano («fin»).
     Riesgo: 1:1 (stop = distancia al objetivo) o 1:1,5 (stop = distancia / 1,5): ejecuciones MERCADO sl 1,0 y 0,6667 con tp 1,0.
  5. Criterios de muerte (columna booleana por criterio, evaluada en la vela del evento): DET (viva según el detector), V2/V8/V24/V72
     (horas desde el nacimiento), TOQUE (≤ 72 h y el precio todavía no entró a la banda) y CRUCE (≤ 72 h y todavía no cerró del otro
     lado de la banda).
  6. Control («esp»): la misma operación hacia una franja ESPEJO a la misma distancia del otro lado del precio (sin concentración).
Definiciones = criterio × distancia × objetivo × (real | espejo); CONTROL empareja cada real con su espejo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import areas_expansion as AX

try:
    from numba import njit
except ImportError:                                     # sin numba: misma lógica en Python (lento; sólo tests chicos)
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "BANDAS-EURUSD"
CARPETA = "docs/research/bandas_concentracion_20261111/eurusd"
PIP = 0.0001
ALTO_PIPS, UMBRAL, VIDA_S = 8.0, 22, 500 * 60
DISTANCIAS = (5, 10, 15, 20, 30, 50)                    # pips
CRITERIOS = ("DET", "V2", "V8", "V24", "V72", "TOQUE", "CRUCE")
HORAS = {"V2": 2, "V8": 8, "V24": 24, "V72": 72}
OBJETIVOS = ("ini", "fin")
EJECUCIONES = [("MERCADO", 1.0, 1.0, 0, 0), ("MERCADO", 0.6667, 1.0, 0, 0)]    # 1:1 y 1:1,5 (stop = 1/1,5 de la distancia)
PREFLIGHT_PRECIO = (1.10, 0.00001)                       # preflight con sintéticos a escala de EURUSD (tablas.bloques_sinteticos)
PERIODOS = [("EXPLORA", 20200101, 20241231), ("CONFIRMA", 20250101, 20260930)]
FUENTE_COSTO = {"EURUSDIDXUSD": "6E", "EURUSD": "6E"}
DEFINICIONES = [f"{c}|x{x}|{o}|{r}" for c in CRITERIOS for x in DISTANCIAS for o in OBJETIVOS for r in ("real", "esp")]
CONTROL = {f"{c}|x{x}|{o}|real": f"{c}|x{x}|{o}|esp" for c in CRITERIOS for x in DISTANCIAS for o in OBJETIVOS}


# ----------------------------------------------------------------------------------------------- bandas (port numba)
@njit(cache=False)
def _bandas_nb(t_ab, z_t0, z_t1, z_lo, z_hi, alto, umbral, vida):
    """Port de `bandas_concentracion.detectar` sobre arreglos (zonas ordenadas por t0). Devuelve las bandas (t0, piso, n0) y las
    extensiones (índice de banda, t). Mismo orden de iteración y desempates que la referencia (paridad en los tests)."""
    nz = len(z_t0); act = np.empty(nz, np.int64); na = 0; j = 0
    cap = 64; b_t0 = np.empty(cap, np.int64); b_t1 = np.empty(cap, np.int64); b_pi = np.empty(cap); b_n = np.empty(cap, np.int64); nb = 0                     # b_n = n0 (conteo al nacer)
    ecap = 256; e_b = np.empty(ecap, np.int64); e_t = np.empty(ecap, np.int64); ne = 0
    for t in t_ab:
        while j < nz and z_t0[j] <= t:
            act[na] = j; na += 1; j += 1
        m = 0
        for q in range(na):                                          # vivas: t1 > t (mantiene el orden de llegada)
            if z_t1[act[q]] > t:
                act[m] = act[q]; m += 1
        na = m
        if na < umbral: continue
        lo = np.empty(na); hi = np.empty(na)
        for q in range(na): lo[q] = z_lo[act[q]]; hi[q] = z_hi[act[q]]
        o = np.argsort(lo, kind="mergesort"); lo = lo[o]; hi = hi[o]; vivo = np.ones(na, np.bool_)
        while True:
            bn = 0; bb = 0.0; bi = -1
            for i in range(na):
                if not vivo[i]: continue
                b = lo[i]; cnt = 0
                for k in range(i, na):
                    if vivo[k] and hi[k] <= b + alto: cnt += 1
                if cnt > bn:
                    bn = cnt; bb = b; bi = i
            if bn < umbral: break
            for k in range(bi, na):
                if vivo[k] and hi[k] <= bb + alto: vivo[k] = False
            hecho = False
            for ob in range(nb):
                if t <= b_t1[ob] and bb < b_pi[ob] + alto and bb + alto > b_pi[ob]:
                    b_t1[ob] = t + vida
                    if ne == ecap:
                        ecap *= 2; e_b = np.concatenate((e_b, np.empty(ecap - ne, np.int64))); e_t = np.concatenate((e_t, np.empty(ecap - ne, np.int64)))
                    e_b[ne] = ob; e_t[ne] = t; ne += 1; hecho = True
                    break
            if not hecho:
                if nb == cap:
                    cap *= 2
                    b_t0 = np.concatenate((b_t0, np.empty(cap - nb, np.int64))); b_t1 = np.concatenate((b_t1, np.empty(cap - nb, np.int64)))
                    b_pi = np.concatenate((b_pi, np.empty(cap - nb))); b_n = np.concatenate((b_n, np.empty(cap - nb, np.int64)))
                b_t0[nb] = t; b_t1[nb] = t + vida; b_pi[nb] = bb; b_n[nb] = bn; nb += 1
    return b_t0[:nb], b_pi[:nb], b_n[:nb], e_b[:ne], e_t[:ne]


def bandas(ctx, alto_pips=ALTO_PIPS, umbral=UMBRAL):
    """Zonas M1 + bandas por segmento. Devuelve DataFrame (t0 apertura de la vela de detección, piso, techo, n0, ext: horas de
    las extensiones, a0 primera vela del segmento)."""
    o, h, l, c, t, seg = (np.asarray(ctx[x]) for x in ("o", "h", "l", "c", "t", "seg"))
    partes = []
    for sg in pd.unique(seg):
        idx = np.flatnonzero(seg == sg); a0, b0 = idx[0], idx[-1] + 1
        tc = t[a0:b0].astype(np.int64); Z = AX.zonas(tc, o[a0:b0], h[a0:b0], l[a0:b0], c[a0:b0])
        if not len(Z["zi"]): continue
        zt0 = tc[Z["zi"]]; ordn = np.argsort(zt0, kind="mergesort")
        bt0, bpi, bn0, eb, et = _bandas_nb(tc - 60, zt0[ordn], zt0[ordn] + VIDA_S, Z["zlo"][ordn].astype(float), Z["zhi"][ordn].astype(float),
                                           alto_pips * PIP, int(umbral), VIDA_S)
        for i in range(len(bt0)):
            partes.append(dict(t0=int(bt0[i]), piso=float(bpi[i]), techo=float(bpi[i] + alto_pips * PIP), n0=int(bn0[i]), ext=et[eb == i].tolist(), a0=int(a0), b0=int(b0)))
    return pd.DataFrame(partes)


# ----------------------------------------------------------------------------------------------- eventos (contrato de tablas)
def eventos(ctx) -> pd.DataFrame:
    t = np.asarray(ctx["t"], np.int64); c = np.asarray(ctx["c"], float); h = np.asarray(ctx["h"], float); l = np.asarray(ctx["l"], float)
    B = bandas(ctx); filas = []
    for b in B.itertuples():
        j0 = int(np.searchsorted(t - 60, b.t0)); jfin = int(min(np.searchsorted(t, b.t0 + 72 * 3600, side="right"), b.b0))
        if j0 >= jfin: continue
        cc = c[j0:jfin]; dentro = (cc >= b.piso) & (cc <= b.techo)
        arriba = cc > b.techo                                                     # el precio está ARRIBA de la banda: se va hacia abajo
        dist = np.where(arriba, cc - b.techo, b.piso - cc) / PIP
        tocada = np.maximum.accumulate((h[j0:jfin] >= b.piso) & (l[j0:jfin] <= b.techo))
        lado_ini = np.where(cc[0] > b.techo, 1, -1)                               # cruzó si cerró del otro lado del lado inicial
        cruzada = np.maximum.accumulate(np.where(lado_ini > 0, cc < b.piso, cc > b.techo))
        ext = np.array([b.t0] + list(b.ext), np.int64)
        for x in DISTANCIAS:
            cerca = (~dentro) & (dist <= x); previo = np.r_[False, cerca[:-1]]
            ks = np.flatnonzero(cerca & ~previo & (np.arange(len(cc)) > 0))     # cruce de > x a ≤ x (no en la primera vela)
            if not len(ks): continue
            q = int(ks[0]); k = j0 + q; tk = int(t[k])
            vivo = {"DET": bool(tk <= ext[ext <= tk].max() + VIDA_S), "TOQUE": not bool(tocada[q - 1]) if q > 0 else True,
                    "CRUCE": not bool(cruzada[q])}
            for nm, hh in HORAS.items(): vivo[nm] = tk <= b.t0 + hh * 3600
            vivo["TOQUE"] &= vivo["V72"]; vivo["CRUCE"] &= vivo["V72"]
            lado = -1 if arriba[q] else 1                                         # hacia la banda
            borde_ini = b.techo if lado < 0 else b.piso; borde_fin = b.piso if lado < 0 else b.techo
            for obj, ref in (("ini", borde_ini), ("fin", borde_fin)):
                d = abs(ref - c[k])
                for rol, ld, rf in (("real", lado, ref), ("esp", -lado, c[k] - lado * d)):
                    filas.append(dict(k=k, lado=int(ld), ref=float(rf), ext=float(c[k]), rg=float(max(d, PIP)), x=x, obj=obj, rol=rol,
                                      n0=b.n0, horas_desde_nacer=(tk - b.t0) / 3600, dist_pips=float(dist[q]), **{f"viv_{cr}": vivo[cr] for cr in CRITERIOS}))
    base = ["k", "lado", "ref", "ext", "rg", "x", "obj", "rol", "n0", "horas_desde_nacer", "dist_pips"] + [f"viv_{cr}" for cr in CRITERIOS]
    E = pd.DataFrame(filas, columns=base)
    defs = {}
    for cr in CRITERIOS:                                                          # definición = criterio × distancia × objetivo × rol
        for xx in DISTANCIAS:
            for oo in OBJETIVOS:
                for rr in ("real", "esp"):
                    defs[f"{cr}|x{xx}|{oo}|{rr}"] = E[f"viv_{cr}"].astype(bool).to_numpy() & (E.x.to_numpy() == xx) & (E.obj.to_numpy() == oo) & (E.rol.to_numpy() == rr)
    return pd.concat([E, pd.DataFrame(defs, index=E.index)], axis=1).sort_values("k", kind="mergesort").reset_index(drop=True)
