"""Opening Range Breakout intradía (QuantConnect ORB Stocks in Play, Option Alpha ORB, TradingView ORB)."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-ORB-RVOL"
FAMILIA = "EXT_ORB_INTRADIA"
INSTRUMENTO = "NQ"
PARAMETROS = dict(n_velas=[15, 30], rr=[1.5, 2.0])


def senales(barras, n_velas: int = 15, rr: float = 1.5) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n <= n_velas:
        return []
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)
    out = []
    ini = np.flatnonzero(np.r_[True, ses[1:] != ses[:-1]])
    fin = np.r_[ini[1:], n]
    for a, b in zip(ini, fin):
        if (b - a) <= n_velas:
            continue
        hi = float(np.max(h[a : a + n_velas]))
        lo = float(np.min(l[a : a + n_velas]))
        r = hi - lo
        if not np.isfinite(r) or r <= 0.0:
            continue
        for i in range(a + n_velas, b):
            d = 0
            if c[i] > hi:
                d = 1
            elif c[i] < lo:
                d = -1
            if d != 0:
                stp = max(min(r, 2.5 * float(atr_v[i])), 0.5)
                tgt = max(float(rr) * stp, 0.5)
                out.append(dict(available_at=int(ts[i]), dir=d, target_pts=tgt, stop_pts=stp, time_stop_min=240))
                break
    return out
