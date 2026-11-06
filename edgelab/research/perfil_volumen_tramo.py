"""Filtro de perfil de volumen entre la entrada y más allá del objetivo (`PERFIL-TP`, 2026-11-05, idea de Nico).

Para una operación con entrada `e`, objetivo `tp` y lado `s` (D = |tp - e|):
  - Rango A (camino):  entre la entrada y el objetivo, ambos extremos incluidos.
  - Rango B (más allá): un rango del mismo tamaño D que arranca justo después del objetivo (sin incluirlo), en la dirección del trade.
Perfil de volumen CAUSAL: suma del volumen negociado por nivel de precio en las últimas `n_barras` velas M1 hasta la vela de decisión `k`
inclusive (`n_barras <= 0` = toda la sesión CME hasta `k`). La operación PASA si `Vol(B) > 0` y `Vol(B) >= ratio * Vol(A)` (ratio base 2).
Un B sin volumen negociado en la ventana es territorio sin referencia: no pasa.
"""
from __future__ import annotations

import numpy as np

try:
    from numba import njit
except ImportError:  # pragma: no cover
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

N_BARRAS = (60, 240, 1440, 0)          # 0 = sesión
RATIOS = (1.5, 2.0, 3.0)
EPS = 1e-9


@njit(cache=False)
def vol_rangos_nb(k_ops, s_ops, e_ops, tp_ops, vp_px, vp_vol, vp_start, ses, n_barras):
    """Devuelve `(vol_A, vol_B)` por operación con el perfil de las últimas `n_barras` velas hasta `k` (inclusive)."""
    m = len(k_ops)
    va = np.zeros(m, np.float64)
    vb = np.zeros(m, np.float64)
    for j in range(m):
        k = k_ops[j]
        if k < 0 or k >= len(ses):
            continue
        k0 = k - n_barras + 1 if n_barras > 0 else k
        if n_barras <= 0:
            while k0 > 0 and ses[k0 - 1] == ses[k]:
                k0 -= 1
        if k0 < 0:
            k0 = 0
        s = s_ops[j]
        e = e_ops[j]
        tp = tp_ops[j]
        D = abs(tp - e)
        if D <= 0.0:
            continue
        if s == 1:
            a_lo, a_hi = e - EPS, tp + EPS
            b_lo, b_hi = tp + EPS, tp + D + EPS
        else:
            a_lo, a_hi = tp - EPS, e + EPS
            b_lo, b_hi = tp - D - EPS, tp - EPS
        i0 = vp_start[k0]
        i1 = vp_start[k + 1]
        sa = 0.0
        sb = 0.0
        for i in range(i0, i1):
            p = vp_px[i]
            if p >= a_lo and p <= a_hi:
                sa += vp_vol[i]
            elif p >= b_lo and p <= b_hi:
                sb += vp_vol[i]
        va[j] = sa
        vb[j] = sb
    return va, vb


def vol_rangos(ctx: dict, k_ops, s_ops, e_ops, tp_ops, n_barras: int):
    return vol_rangos_nb(
        np.asarray(k_ops, np.int64), np.asarray(s_ops, np.int64), np.asarray(e_ops, np.float64), np.asarray(tp_ops, np.float64),
        np.asarray(ctx["vp_px"], np.float64), np.asarray(ctx["vp_vol"], np.float64), np.asarray(ctx["vp_start"], np.int64),
        np.asarray(ctx["ses"], np.int64), int(n_barras),
    )


def pasa_perfil(va: np.ndarray, vb: np.ndarray, ratio: float) -> np.ndarray:
    return (vb > 0.0) & (vb >= float(ratio) * va)


# --- Variantes declaradas el 2026-11-05 tras ver que la regla base casi nunca pasa (B suele no tener volumen reciente) ---------------
@njit(cache=False)
def conteos_rangos_nb(k_ops, s_ops, e_ops, tp_ops, vp_px, vp_vol, vp_start, ses, n_barras):
    """Como `vol_rangos_nb` pero devuelve además la cantidad de celdas (vela, nivel) con volumen en A y en B."""
    m = len(k_ops)
    ca = np.zeros(m, np.float64)
    cb = np.zeros(m, np.float64)
    for j in range(m):
        k = k_ops[j]
        if k < 0 or k >= len(ses):
            continue
        k0 = k - n_barras + 1 if n_barras > 0 else k
        if n_barras <= 0:
            while k0 > 0 and ses[k0 - 1] == ses[k]:
                k0 -= 1
        if k0 < 0:
            k0 = 0
        s = s_ops[j]
        e = e_ops[j]
        tp = tp_ops[j]
        D = abs(tp - e)
        if D <= 0.0:
            continue
        if s == 1:
            a_lo, a_hi = e - EPS, tp + EPS
            b_lo, b_hi = tp + EPS, tp + D + EPS
        else:
            a_lo, a_hi = tp - EPS, e + EPS
            b_lo, b_hi = tp - D - EPS, tp - EPS
        for i in range(vp_start[k0], vp_start[k + 1]):
            p = vp_px[i]
            if vp_vol[i] > 0.0:
                if p >= a_lo and p <= a_hi:
                    ca[j] += 1.0
                elif p >= b_lo and p <= b_hi:
                    cb[j] += 1.0
    return ca, cb


def conteos_rangos(ctx: dict, k_ops, s_ops, e_ops, tp_ops, n_barras: int):
    return conteos_rangos_nb(
        np.asarray(k_ops, np.int64), np.asarray(s_ops, np.int64), np.asarray(e_ops, np.float64), np.asarray(tp_ops, np.float64),
        np.asarray(ctx["vp_px"], np.float64), np.asarray(ctx["vp_vol"], np.float64), np.asarray(ctx["vp_start"], np.int64),
        np.asarray(ctx["ses"], np.int64), int(n_barras),
    )


def pasa_perfil_media(va, vb, ca, cb, ratio: float) -> np.ndarray:
    """Variante MEDIA: volumen medio por celda negociada (vela, nivel) de B >= ratio x el de A (A sin celdas: basta que B tenga volumen)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        ma = np.where(ca > 0, va / np.maximum(ca, 1.0), 0.0)
        mb = np.where(cb > 0, vb / np.maximum(cb, 1.0), 0.0)
    return (cb > 0) & (mb >= float(ratio) * ma)


def pasa_perfil_vacio(va: np.ndarray, vb: np.ndarray, ratio: float) -> np.ndarray:
    """Variante VACIO: B sin volumen reciente cuenta como camino libre (pasa); si tiene volumen, debe cumplir `Vol(B) >= ratio x Vol(A)`."""
    return (vb <= 0.0) | (vb >= float(ratio) * va)

