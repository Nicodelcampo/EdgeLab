"""Larry Connors RSI(2) + ATR Mean Reversion (ZenAndTheArtOfTrading) traducido para EdgeLab."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-CONNORS-RSI2-ATR-MR"
FAMILIA = "EXT_TV_CONNORS_ATR"
INSTRUMENTO = "ES"
PARAMETROS = dict(rsi_os=[10, 15], atr_mult=[1.0, 1.5])


def senales(barras, rsi_os: int = 10, atr_mult: float = 1.0) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 110:
        return []
    sma_trend = IX.sma(c, 100)
    ema_short = IX.ema(c, 20)
    atr5 = IX.atr(h, l, c, 5, usar_rma=True)
    rsi2 = IX.rsi(c, 2)
    atr14 = IX.atr(h, l, c, 14, usar_rma=True)

    idxs, dirs = [], []
    for i in range(105, n):
        if ses[i] != ses[i - 1]:
            continue
        long_cond = (c[i] > sma_trend[i]) and (rsi2[i] < rsi_os or c[i] < ema_short[i] - atr_mult * atr5[i])
        short_cond = (c[i] < sma_trend[i]) and (rsi2[i] > (100.0 - rsi_os) or c[i] > ema_short[i] + atr_mult * atr5[i])
        if long_cond:
            idxs.append(i)
            dirs.append(1)
        elif short_cond:
            idxs.append(i)
            dirs.append(-1)
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr14, mult_tp=1.8, mult_sl=1.2, cooldown_bars=12, time_stop_min=120)
