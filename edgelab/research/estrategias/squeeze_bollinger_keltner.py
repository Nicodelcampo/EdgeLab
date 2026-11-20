"""Squeeze Momentum (LazyBear) & Volatility-Squeeze Breakout (cTrader Sample Breakout cBot) para EdgeLab."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-SQUEEZE-MOMENTUM"
FAMILIA = "EXT_TV_SQUEEZE"
INSTRUMENTO = "NQ"
PARAMETROS = dict(kc_mult=[1.3, 1.6], mult_tp=[2.0, 3.0])


def senales(barras, kc_mult: float = 1.5, mult_tp: float = 2.0) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 30:
        return []
    mid, bb_up, bb_lo, _ = IX.bollinger(c, period=20, mult=2.0)
    atr_v = IX.atr(h, l, c, 20, usar_rma=False)
    kc_up = mid + float(kc_mult) * atr_v
    kc_lo = mid - float(kc_mult) * atr_v

    sqz_on = (bb_lo > kc_lo) & (bb_up < kc_up)
    _, slope = IX.linreg_slope(c, period=20)

    idxs, dirs = [], []
    for i in range(22, n):
        if ses[i] != ses[i - 1]:
            continue
        if sqz_on[i - 1] and not sqz_on[i]:
            if slope[i] > 0.0:
                idxs.append(i)
                dirs.append(1)
            elif slope[i] < 0.0:
                idxs.append(i)
                dirs.append(-1)
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=mult_tp, mult_sl=1.2, cooldown_bars=15, time_stop_min=180)
