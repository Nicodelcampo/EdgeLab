"""MACD + ADX / Momentum (Freqtrade ADXMomentum, TradingView MACD+ADX, QuantConnect ADX Trend)."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-MACD-ADX-TREND"
FAMILIA = "EXT_MACD_ADX"
INSTRUMENTO = "NQ"
PARAMETROS = dict(adx_min=[20, 25], mult_tp=[2.0, 3.0])


def senales(barras, adx_min: int = 20, mult_tp: float = 2.0) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 40:
        return []
    macd = IX.ema(c, 12) - IX.ema(c, 26)
    sig = IX.ema(macd, 9)
    adx, pdi, mdi = IX.adx_di(h, l, c, adx_period=14, di_period=14)
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)

    idxs, dirs = [], []
    for i in range(30, n):
        if ses[i] != ses[i - 1]:
            continue
        if adx[i] < adx_min:
            continue
        if macd[i - 1] <= sig[i - 1] and macd[i] > sig[i] and pdi[i] > mdi[i]:
            idxs.append(i)
            dirs.append(1)
        elif macd[i - 1] >= sig[i - 1] and macd[i] < sig[i] and mdi[i] > pdi[i]:
            idxs.append(i)
            dirs.append(-1)
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=mult_tp, mult_sl=1.2, cooldown_bars=15, time_stop_min=180)
