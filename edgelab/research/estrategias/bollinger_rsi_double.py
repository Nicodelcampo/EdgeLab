"""Bollinger + RSI Double Strategy (ChartArt, MQL5 BB Mean Reversion EA, Hummingbot BollingerV1) para EdgeLab."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-BOLLINGER-RSI-DOUBLE"
FAMILIA = "EXT_TV_BB_RSI"
INSTRUMENTO = "NQ"
PARAMETROS = dict(len_bb=[20, 50], len_rsi=[6, 14])


def senales(barras, len_bb: int = 20, len_rsi: int = 14) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    warmup = max(int(len_bb), int(len_rsi)) + 5
    if n < warmup + 5:
        return []
    _, bb_up, bb_lo, _ = IX.bollinger(c, period=len_bb, mult=2.0)
    rsi_v = IX.rsi(c, period=len_rsi)
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)

    idxs, dirs = [], []
    for i in range(warmup, n):
        if ses[i] != ses[i - 1]:
            continue
        if (c[i - 1] <= bb_lo[i - 1] and c[i] > bb_lo[i] and rsi_v[i] < 45.0) or (c[i] <= bb_lo[i] and rsi_v[i] < 35.0):
            idxs.append(i)
            dirs.append(1)
        elif (c[i - 1] >= bb_up[i - 1] and c[i] < bb_up[i] and rsi_v[i] > 55.0) or (c[i] >= bb_up[i] and rsi_v[i] > 65.0):
            idxs.append(i)
            dirs.append(-1)
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=2.0, mult_sl=1.3, cooldown_bars=12, time_stop_min=180)
