"""Supertrend ATR (TradingView Built-in & KivancOzbilgic / Hummingbot SuperTrendV1) traducido para EdgeLab."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-SUPERTREND-ATR"
FAMILIA = "EXT_TV_SUPERTREND"
INSTRUMENTO = "NQ"
PARAMETROS = dict(periodo=[10, 20], mult=[2.5, 3.5])


def senales(barras, periodo: int = 10, mult: float = 3.0) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    if len(c) < periodo + 5:
        return []
    atr_v = IX.atr(h, l, c, periodo, usar_rma=True)
    _, tdir = IX.supertrend(h, l, c, period=periodo, mult=mult)
    idxs = []
    dirs = []
    warmup = max(periodo + 2, 15)
    for i in range(warmup, len(c)):
        if ses[i] == ses[i - 1] and tdir[i] != tdir[i - 1]:
            idxs.append(i)
            dirs.append(int(tdir[i]))
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=2.5, mult_sl=1.5, cooldown_bars=12, time_stop_min=180)
