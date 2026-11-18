"""London / Asian Box Breakout (MQL5 N22 / Gold / Simple London Breakout) traducido para EdgeLab."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-LONDON-ASIAN-BREAKOUT"
FAMILIA = "EXT_MQL5_LONDON_BOX"
INSTRUMENTO = "GC"
PARAMETROS = dict(box_bars=[30, 60], rr=[1.5, 2.0])


def senales(barras, box_bars: int = 45, rr: float = 1.5) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n <= box_bars:
        return []
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)
    ini = np.flatnonzero(np.r_[True, ses[1:] != ses[:-1]])
    fin = np.r_[ini[1:], n]
    out = []
    for a, b in zip(ini, fin):
        if (b - a) <= box_bars:
            continue
        box_hi = float(np.max(h[a : a + box_bars]))
        box_lo = float(np.min(l[a : a + box_bars]))
        r = box_hi - box_lo
        if not np.isfinite(r) or r <= 0.0:
            continue
        max_i = min(b, a + box_bars + 180)
        for i in range(a + box_bars, max_i):
            buf = 0.1 * float(atr_v[i])
            if c[i] > box_hi + buf:
                stp = max(min(r, 2.5 * float(atr_v[i])), 0.5)
                tgt = max(float(rr) * stp, 0.5)
                out.append(dict(available_at=int(ts[i]), dir=1, target_pts=tgt, stop_pts=stp, time_stop_min=180))
                break
            if c[i] < box_lo - buf:
                stp = max(min(r, 2.5 * float(atr_v[i])), 0.5)
                tgt = max(float(rr) * stp, 0.5)
                out.append(dict(available_at=int(ts[i]), dir=-1, target_pts=tgt, stop_pts=stp, time_stop_min=180))
                break
    return out
