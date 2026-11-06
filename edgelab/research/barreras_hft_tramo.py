"""Conteo causal de Barreras HFT dentro del tramo entrada -> objetivo (`BARRERAS-HFT-R`, 2026-11-05, pedido de Nico).

Complementa `barreras_hft.py` (que NO se toca: sus SHA están embebidos en las campañas `HFT-GC-P10-VETO-R` y `-CAPTP-R` en curso).
Usa el MISMO inventario causal (`BH.preparar_inventario_barreras`) y los mismos filtros de vigencia (tipo, antigüedad, mitigación), pero
en vez de la distancia a la primera barrera cuenta cuántas barreras vigentes caen en el tramo `(entrada, objetivo]` y cuántas de ellas
están en la mitad CERCANA a la entrada (borde cercano a menos de `0.5 * D`, con `D = |objetivo - entrada|`).

Reglas derivadas (todas causales: sólo usan zonas con `zi <= k`):
  - `todo`    : pasa si `n_total <= N` (se admiten hasta N zonas en cualquier lugar del tramo).
  - `lejana`  : pasa si `n_cerca == 0` y `n_total <= N` (las zonas admitidas sólo pueden estar en el 50 % más alejado de la entrada).
"""
from __future__ import annotations

import numpy as np

from edgelab.research import barreras_hft as BH

try:
    from numba import njit
except ImportError:  # pragma: no cover
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

REGLAS_TRAMO = (("todo", 0), ("todo", 1), ("todo", 2), ("lejana", 1), ("lejana", 2))   # (modo, N máximo de zonas en el tramo)


@njit(cache=False)
def conteo_tramo_nb(
    k_ops, s_ops, e_ops, r_ops, d_ops,
    mc_m1, ses_m1,
    zi, z_mc, z_ses, zlo, zhi, z_fuerte, z_away_k, z_away_dir, z_first_any, z_first_full,
    ci, c_mc, c_ses, clo, chi, c_first_any, c_first_full,
    tipo_barrera, max_edad_seg, solo_misma_sesion, modo_mitigacion,
):
    """Devuelve `(n_total, n_cerca)` por operación: barreras vigentes con borde cercano a distancia `<= D` y `< 0.5 * D` de la entrada."""
    m = len(k_ops)
    n_tot = np.zeros(m, np.int64)
    n_cer = np.zeros(m, np.int64)
    if m == 0:
        return n_tot, n_cer
    es_cluster = tipo_barrera == 3
    b_i = ci if es_cluster else zi
    b_mc = c_mc if es_cluster else z_mc
    b_ses = c_ses if es_cluster else z_ses
    b_lo = clo if es_cluster else zlo
    b_hi = chi if es_cluster else zhi
    b_f_any = c_first_any if es_cluster else z_first_any
    b_f_full = c_first_full if es_cluster else z_first_full
    nb = len(b_i)
    if nb == 0:
        return n_tot, n_cer
    for j in range(m):
        k = k_ops[j]
        s = s_ops[j]
        e = e_ops[j]
        r = r_ops[j]
        D = d_ops[j]
        if k < 0 or k >= len(mc_m1) or r <= 0.0 or D <= 0.0:
            continue
        mc_k = mc_m1[k]
        ses_k = ses_m1[k]
        delta_min = 0.15 * r
        atras_max = 0.50 * r
        lo_idx = 0
        hi_idx = nb
        while lo_idx < hi_idx:
            mid = (lo_idx + hi_idx) // 2
            if b_i[mid] <= k:
                lo_idx = mid + 1
            else:
                hi_idx = mid
        top = lo_idx - 1
        for idx in range(top, -1, -1):
            if mc_k - b_mc[idx] > max_edad_seg + 1e-9:
                break
            if solo_misma_sesion == 1 and b_ses[idx] != ses_k:
                continue
            f_mit = b_f_any[idx] if modo_mitigacion == 0 else b_f_full[idx]
            if f_mit <= k:
                continue
            if not es_cluster:
                if tipo_barrera == 1 and z_fuerte[idx] == 0:
                    continue
                elif tipo_barrera == 2:
                    ak = z_away_k[idx]
                    if ak < 0 or ak > k or z_away_dir[idx] != -s:
                        continue
            lz = b_lo[idx]
            hz = b_hi[idx]
            if s == 1:
                if hz <= e + delta_min or lz < e - atras_max:
                    continue
                d_px = lz - e
            else:
                if lz >= e - delta_min or hz > e + atras_max:
                    continue
                d_px = e - hz
            if d_px < 0.0:
                d_px = 0.0
            if d_px <= D:
                n_tot[j] += 1
                if d_px < 0.5 * D:
                    n_cer[j] += 1
    return n_tot, n_cer


def conteo_tramo(inv: dict, k_ops, s_ops, e_ops, r_ops, d_ops, tipo_idx: int, edad_idx: int, mit_idx: int):
    """Wrapper indexado por `(tipo, antigüedad, mitigación)`, igual que `BH.evaluar_distancia_frontal`."""
    _, max_seg, solo_ses = BH.ANTIGUEDADES[int(edad_idx)]
    return conteo_tramo_nb(
        np.asarray(k_ops, np.int64), np.asarray(s_ops, np.int64), np.asarray(e_ops, np.float64),
        np.asarray(r_ops, np.float64), np.asarray(d_ops, np.float64),
        inv["mc_m1"], inv["ses_m1"],
        inv["zi"], inv["z_mc"], inv["z_ses"], inv["zlo"], inv["zhi"],
        inv["z_fuerte"], inv["z_away_k"], inv["z_away_dir"], inv["z_first_any"], inv["z_first_full"],
        inv["ci"], inv["c_mc"], inv["c_ses"], inv["clo"], inv["chi"], inv["c_first_any"], inv["c_first_full"],
        int(tipo_idx), float(max_seg), int(solo_ses), int(mit_idx),
    )


def pasa_regla(n_tot: np.ndarray, n_cer: np.ndarray, modo: str, n_max: int) -> np.ndarray:
    """`True` donde la operación pasa la regla de tramo."""
    ok = n_tot <= int(n_max)
    return ok & (n_cer == 0) if modo == "lejana" else ok

