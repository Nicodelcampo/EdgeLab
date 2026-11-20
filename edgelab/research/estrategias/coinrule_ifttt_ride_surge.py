"""Coinrule IFTTT Engine (Ride The Trend & Volatility Trend Surge) traducido para EdgeLab."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-COINRULE-IFTTT"
FAMILIA = "EXT_COINRULE_IFTTT"
INSTRUMENTO = "NQ"
PARAMETROS = dict(modo=["ride_trend", "vol_surge"], mult_tp=[1.5, 2.5])


def senales(barras, modo: str = "ride_trend", mult_tp: float = 2.0) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 60:
        return []
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)
    idxs, dirs = [], []

    if modo == "ride_trend":
        rsi_v = IX.rsi(c, 14)
        macd = IX.ema(c, 12) - IX.ema(c, 26)
        mfi_v = IX.mfi(h, l, c, v, 14)
        for i in range(30, n):
            if ses[i] != ses[i - 1]:
                continue
            if rsi_v[i] < 35.0 and macd[i] < 0.0 and mfi_v[i] < 35.0:
                idxs.append(i)
                dirs.append(1)
            elif rsi_v[i] > 65.0 and macd[i] > 0.0 and mfi_v[i] > 65.0:
                idxs.append(i)
                dirs.append(-1)
    else:
        ma2 = IX.sma(c, 2)
        ma50 = IX.sma(c, 50)
        for i in range(55, n):
            if ses[i] != ses[i - 1] or atr_v[i - 5] <= 1e-9:
                continue
            salto_atr = (atr_v[i] - atr_v[i - 5]) / atr_v[i - 5]
            if salto_atr >= 0.15:
                if ma2[i] > ma50[i]:
                    idxs.append(i)
                    dirs.append(1)
                elif ma2[i] < ma50[i]:
                    idxs.append(i)
                    dirs.append(-1)

    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=mult_tp, mult_sl=1.2, cooldown_bars=15, time_stop_min=180)
