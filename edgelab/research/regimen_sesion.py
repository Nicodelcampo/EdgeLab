"""Primitivas causales con corte estricto por sesión (2026-10-31, plan del paquete del 31-oct).

Por qué existe: el parche de filtros del PR #162 calculaba la eficiencia de Kaufman, la volatilidad y el momentum sobre la serie
concatenada sin reiniciar en el cambio de sesión, así que el salto overnight entraba como un retorno de un minuto. Acá cada ventana
usa sólo velas de la MISMA sesión que la vela k y hasta k inclusive; si la sesión todavía no tiene `w` velas, el valor es NaN.
`existente.py` no encontró un ER con corte por sesión (`corredor_vol_gaps` y `expansion_zonas` traen ATR, no ER); el ATR se reutiliza
de `zonas_gaps._atr_causal`.
"""
from __future__ import annotations

import numpy as np

from edgelab.research.otr_930_sweep import _offset_ny_seg_nb

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]


@njit(cache=False)
def er_sesion(c, ses, w):
    """Eficiencia de Kaufman de las últimas `w` velas de la sesión: |c_k − c_{k−w}| / Σ|Δc| (1 = recta, 0 = serrucho)."""
    n = len(c); out = np.full(n, np.nan); ini = 0
    for k in range(n):
        if k == 0 or ses[k] != ses[k - 1]: ini = k
        if k - ini < w: continue
        tot = 0.0
        for j in range(k - w + 1, k + 1): tot += abs(c[j] - c[j - 1])
        out[k] = abs(c[k] - c[k - w]) / tot if tot > 0.0 else 0.0
    return out


@njit(cache=False)
def minuto_ny(t):
    """Minuto del día en Nueva York (con horario de verano) de cada vela; `t` en segundos UTC (cierre de la vela)."""
    n = len(t); out = np.empty(n, np.int64)
    for i in range(n):
        tl = int(t[i]) + _offset_ny_seg_nb(int(t[i]))
        out[i] = (tl % 86400) // 60
    return out


@njit(cache=False)
def rv_relativa(c, ses, corta, larga):
    """Raíz de RV(corta)/RV(larga) con medias exponenciales de r², reiniciadas en cada sesión; conocida al cierre de k."""
    n = len(c); out = np.full(n, np.nan); a = 0.0; b = 0.0; m = 0
    for k in range(n):
        if k == 0 or ses[k] != ses[k - 1]:
            a = 0.0; b = 0.0; m = 0; continue
        r = c[k] - c[k - 1]
        a += (r * r - a) / corta; b += (r * r - b) / larga; m += 1
        if m >= corta and b > 0.0: out[k] = (a / b) ** 0.5
    return out
