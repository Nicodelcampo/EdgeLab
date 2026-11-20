"""The Dynamic Breakout II (QuantConnect Strategy Library, George Pruitt) con lookback adaptativo causal."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-DYNAMIC-BREAKOUT-II"
FAMILIA = "EXT_QC_DYN_BREAKOUT"
INSTRUMENTO = "ES"
PARAMETROS = dict(base_len=[20, 30], bb_mult=[1.2, 1.8])


def senales(barras, base_len: int = 20, bb_mult: float = 1.5) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 70:
        return []
    atr_v = IX.atr(h, l, c, 20, usar_rma=True)
    _, upband, lowband, _ = IX.bollinger(c, period=20, mult=bb_mult)

    numdays = int(base_len)
    idxs, dirs = [], []
    for i in range(65, n):
        vol_curr = float(np.std(c[i - numdays + 1 : i + 1]))
        vol_prev = float(np.std(c[i - numdays : i]))
        if vol_curr > 1e-12:
            deltavol = (vol_curr - vol_prev) / vol_curr
            numdays = max(20, min(60, int(round(numdays * (1.0 + deltavol)))))
        if ses[i] != ses[i - 1]:
            continue
        buy_pt = float(np.max(h[i - numdays : i]))
        sell_pt = float(np.min(l[i - numdays : i]))
        if c[i - 1] > upband[i - 1] and c[i] > buy_pt:
            idxs.append(i)
            dirs.append(1)
        elif c[i - 1] < lowband[i - 1] and c[i] < sell_pt:
            idxs.append(i)
            dirs.append(-1)
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=2.5, mult_sl=1.5, cooldown_bars=15, time_stop_min=240)
