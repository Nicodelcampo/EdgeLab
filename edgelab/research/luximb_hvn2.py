"""LUXIMB-HVN2 (2026-11-11, pedido de Nico: «las dos»): el nodo de volumen más allá de B REDEFINIDO en relativo, sobre la cadena
estándar (edgelab/research/tablas.py). Motivo (`F-LUXIMB-HVN-DEFINICION`): la definición de LUXIMB-HVN (franja de medio impulso con
≥ x veces el volumen de cada vecina) casi nunca ocurre (hvn ≥ 2 en 3 de 925 eventos del visor) y no permite probar el mecanismo.
Pre-registro: docs/research/luximb_hvn_20261111/PREREGISTRO_HVN2.md.

Eventos: los de LUXIMB-HVN (`luximb_hvn.eventos`, mismas 40 definiciones del impulso; se usan 4). Rasgos nuevos, todos con el perfil de
volumen de las L velas ANTERIORES al inicio del impulso (sin el volumen del propio impulso) y por nivel de precio:
  hvr_<L>     densidad de volumen (por nivel) en la franja más allá de B de alto rg/2, dividida por la MEDIANA de la densidad de
              los niveles negociados en la ventana (> 1 = más intercambio que lo típico ahí)
  poc_d_<L>   distancia de B al nivel de MÁS volumen dentro de [B, B + rg] (más allá), en rangos (0 = en B)
  poc_f_<L>   volumen de ese nivel sobre la mediana por nivel de la ventana (fuerza del nodo)
Justificación económica: un nodo de intercambio previo más allá del extremo es liquidez que puede absorber la extensión y darla
vuelta. Cómo podría refutarse: la entrada en la vuelta rinde igual con nodo fuerte que sin nodo (real − sin nodo ≈ 0).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import luximb_hvn as H

try:
    from numba import njit
except ImportError:                                     # sin numba: misma lógica en Python (lento; sólo tests chicos)
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "LUXIMB-HVN2"
CARPETA = "docs/research/luximb_hvn_20261111/hvn2"
VISOR, CTRL = "D3_20_a0_z2", "D3_20_a0_z0"
DEFINICIONES = [VISOR, CTRL, "D3_20_a0_z3", "D2_20_a0_z2"]
CONTROL = {VISOR: CTRL, "D3_20_a0_z3": CTRL}
LOOKBACKS = (240, 1440)
FILTROS = {**{f"hvr{L}>={u}": (f"hvr_{L}", ">=", u) for L in LOOKBACKS for u in (1.5, 2.0, 3.0)},
           **{f"hvr{L}<1": (f"hvr_{L}", "<", 1.0) for L in LOOKBACKS},
           "poc_cerca_fuerte": ("poc_cf_1440", "==", 1.0)}
EJECUCIONES = [("MERCADO", sl, tp, 0, be) for sl in (0.35, 0.5) for tp in (0.5, 1.0) for be in (0, 0.25)] + \
              [("VUELTA", e, r, 0.1, o, round(e + 0.5, 4)) for e in (0.1, 0.25, 0.5) for r in (0.1, 0.2) for o in (0, 1)]


@njit(cache=False)
def _perfil_nb(k, i0, a0, d, B, rg, vps, vpx, vvo, L):
    n = len(k); hvr = np.full(n, np.nan); pd_ = np.full(n, np.nan); pf = np.full(n, np.nan)
    for q in range(n):
        lo = max(a0[q], i0[q] - L); hi = i0[q]
        if hi <= lo or rg[q] <= 0: continue
        z0 = vps[lo]; z1 = vps[hi]
        if z1 - z0 < 3: continue
        px = vpx[z0:z1].copy(); vo = vvo[z0:z1].copy(); o = np.argsort(px); px = px[o]; vo = vo[o]
        niv = np.empty(len(px)); vol = np.empty(len(px)); m = 0
        for j in range(len(px)):                                   # suma por nivel de precio
            if m > 0 and px[j] == niv[m - 1]: vol[m - 1] += vo[j]
            else:
                niv[m] = px[j]; vol[m] = vo[j]; m += 1
        med = np.median(vol[:m])
        if med <= 0: continue
        w = rg[q] / 2.0; sb = 0.0; nb = 0; best = -1.0; bx = np.nan
        for j in range(m):
            x = d[q] * (niv[j] - B[q])
            if 0.0 <= x <= w:
                sb += vol[j]; nb += 1
            if 0.0 <= x <= rg[q] and vol[j] > best:
                best = vol[j]; bx = x / rg[q]
        hvr[q] = (sb / nb) / med if nb > 0 else 0.0
        if best > 0:
            pd_[q] = bx; pf[q] = best / med
    return hvr, pd_, pf


def eventos(ctx) -> pd.DataFrame:
    E = H.eventos(ctx)
    if not len(E): return E.assign(lado=[], ref=[])
    E = E[E[DEFINICIONES].any(axis=1)].reset_index(drop=True)               # sólo las 4 definiciones de este estudio
    seg = np.asarray(ctx["seg"]); k = E.k.to_numpy(np.int64)
    ini = np.r_[0, np.flatnonzero(seg[1:] != seg[:-1]) + 1]; a0 = ini[np.searchsorted(ini, k, side="right") - 1].astype(np.int64)
    for L in LOOKBACKS:
        h, pd_, pf = _perfil_nb(k, E.i0.to_numpy(np.int64), a0, E.d.to_numpy(np.int64), E.ext.to_numpy(float), E.rg.to_numpy(float),
                                np.asarray(ctx["vp_start"], np.int64), np.asarray(ctx["vp_px"], float), np.asarray(ctx["vp_vol"], float), L)
        E[f"hvr_{L}"] = h; E[f"poc_d_{L}"] = pd_; E[f"poc_f_{L}"] = pf
    E["poc_cf_1440"] = ((E.poc_d_1440 <= 0.25) & (E.poc_f_1440 >= 3.0)).astype(float)   # nodo fuerte a ≤ 1/4 de rango más allá de B
    E["lado"] = -E.d.to_numpy(np.int64); E["ref"] = E.pa.to_numpy(float)                # contrato de ejecucion: fade hacia A
    return E
