"""Dual Thrust (QuantConnect Strategy Library, Michael Chalek) adaptado por sesión para EdgeLab."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-DUAL-THRUST"
FAMILIA = "EXT_QC_DUAL_THRUST"
INSTRUMENTO = "ES"
PARAMETROS = dict(k=[0.35, 0.50], mult_tp=[1.0, 1.5])


def senales(barras, k: float = 0.50, mult_tp: float = 1.5) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 20:
        return []
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)
    ini = np.flatnonzero(np.r_[True, ses[1:] != ses[:-1]])
    fin = np.r_[ini[1:], n]
    out = []
    hist_hi, hist_lo, hist_c = [], [], []
    for s_idx, (a, b) in enumerate(zip(ini, fin)):
        if s_idx >= 1 and hist_hi:
            win_h = hist_hi[-4:]
            win_l = hist_lo[-4:]
            win_c = hist_c[-4:]
            rng = max(max(win_h) - min(win_c), max(win_c) - min(win_l))
            if np.isfinite(rng) and rng > 0.0:
                open_s = float(o[a])
                buy_trig = open_s + float(k) * rng
                sell_trig = open_s - float(k) * rng
                for i in range(a + 1, b):
                    if c[i] >= buy_trig:
                        stp = max(0.5 * rng, float(atr_v[i]), 0.5)
                        tgt = max(float(mult_tp) * rng, 0.5)
                        out.append(dict(available_at=int(ts[i]), dir=1, target_pts=tgt, stop_pts=stp, time_stop_min=240))
                        break
                    if c[i] <= sell_trig:
                        stp = max(0.5 * rng, float(atr_v[i]), 0.5)
                        tgt = max(float(mult_tp) * rng, 0.5)
                        out.append(dict(available_at=int(ts[i]), dir=-1, target_pts=tgt, stop_pts=stp, time_stop_min=240))
                        break
        hist_hi.append(float(np.max(h[a:b])))
        hist_lo.append(float(np.min(l[a:b])))
        hist_c.append(float(c[b - 1]))
    return out
