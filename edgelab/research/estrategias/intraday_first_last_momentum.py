"""Intraday First-to-Last Momentum (QuantConnect / Gao, Han, Li & Zhou 2017) estrictamente causal."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-INTRADAY-MOM-GAO"
FAMILIA = "EXT_QC_GAO_INTRADAY"
INSTRUMENTO = "ES"
PARAMETROS = dict(n_open=[30, 45], umbral_atr=[0.5, 1.0])


def senales(barras, n_open: int = 30, umbral_atr: float = 0.5) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    bar_entrada = 240
    if n <= bar_entrada:
        return []
    atr_v = IX.atr(h, l, c, 20, usar_rma=True)
    ini = np.flatnonzero(np.r_[True, ses[1:] != ses[:-1]])
    fin = np.r_[ini[1:], n]
    out = []
    for a, b in zip(ini, fin):
        if (b - a) <= bar_entrada or n_open <= 0:
            continue
        ret_open = float(c[a + n_open - 1] - o[a])
        atr_ref = max(float(atr_v[a + bar_entrada]), 0.5)
        if abs(ret_open) > float(umbral_atr) * atr_ref:
            d = 1 if ret_open > 0.0 else -1
            out.append(
                dict(
                    available_at=int(ts[a + bar_entrada]),
                    dir=d,
                    target_pts=max(2.0 * atr_ref, 0.5),
                    stop_pts=max(1.5 * atr_ref, 0.5),
                    time_stop_min=120,
                )
            )
    return out
