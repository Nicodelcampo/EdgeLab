"""Freqtrade CombinedBinHAndCluc y SampleStrategy (TEMA + RSI + Bollinger) adaptados a barras M1 en EdgeLab."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-FREQTRADE-BINH-CLUC"
FAMILIA = "EXT_FREQTRADE_SCALP"
INSTRUMENTO = "NQ"
PARAMETROS = dict(variante=["binh_cluc", "sample_tema"], mult_tp=[1.5, 2.0])


def senales(barras, variante: str = "binh_cluc", mult_tp: float = 1.5) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 55:
        return []
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)
    idxs, dirs = [], []

    if variante == "binh_cluc":
        mid40, up40, lo40, _ = IX.bollinger(c, period=40, mult=2.0)
        tp = (h + l + c) / 3.0
        _, up20, lo20, _ = IX.bollinger(tp, period=20, mult=2.0)
        ema50 = IX.ema(c, 50)
        for i in range(45, n):
            if ses[i] != ses[i - 1]:
                continue
            bbdelta = abs(mid40[i] - lo40[i])
            closedelta = abs(c[i] - c[i - 1])
            tail = abs(c[i] - l[i])
            wick_top = abs(h[i] - c[i])
            binh_long = (
                bbdelta > 0.4 * atr_v[i]
                and closedelta > 0.3 * atr_v[i]
                and tail < 0.35 * bbdelta
                and c[i] < lo40[i - 1]
                and c[i] <= c[i - 1]
            )
            cluc_long = c[i] < ema50[i] and c[i] < lo20[i] - 0.1 * atr_v[i]
            binh_short = (
                bbdelta > 0.4 * atr_v[i]
                and closedelta > 0.3 * atr_v[i]
                and wick_top < 0.35 * bbdelta
                and c[i] > up40[i - 1]
                and c[i] >= c[i - 1]
            )
            cluc_short = c[i] > ema50[i] and c[i] > up20[i] + 0.1 * atr_v[i]
            if binh_long or cluc_long:
                idxs.append(i)
                dirs.append(1)
            elif binh_short or cluc_short:
                idxs.append(i)
                dirs.append(-1)
    else:
        rsi_v = IX.rsi(c, 14)
        tp = (h + l + c) / 3.0
        bb_mid, _, _, _ = IX.bollinger(tp, period=20, mult=2.0)
        tema9 = IX.tema(c, 9)
        for i in range(25, n):
            if ses[i] != ses[i - 1]:
                continue
            if rsi_v[i - 1] <= 30.0 and rsi_v[i] > 30.0 and tema9[i] <= bb_mid[i] and tema9[i] > tema9[i - 1]:
                idxs.append(i)
                dirs.append(1)
            elif rsi_v[i - 1] >= 70.0 and rsi_v[i] < 70.0 and tema9[i] >= bb_mid[i] and tema9[i] < tema9[i - 1]:
                idxs.append(i)
                dirs.append(-1)

    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=mult_tp, mult_sl=1.2, cooldown_bars=12, time_stop_min=120)
