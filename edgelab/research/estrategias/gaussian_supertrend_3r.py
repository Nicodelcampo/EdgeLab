"""Gaussian Trend Targets & Gaussian Channel [DW] (blitz_algo / DonovanWall) con salidas 3R para EdgeLab."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-GAUSSIAN-TREND-3R"
FAMILIA = "EXT_TV_GAUSSIAN"
INSTRUMENTO = "NQ"
PARAMETROS = dict(sampling=[14, 21], mult_banda=[1.414, 2.0])


def senales(barras, sampling: int = 14, mult_banda: float = 1.414) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    if len(c) < sampling + 10:
        return []
    hlc3 = (h + l + c) / 3.0
    filt = IX.ehlers_gaussian_filter(hlc3, period=sampling, poles=4)
    tr = IX.true_range(h, l, c)
    tr_filt = IX.ehlers_gaussian_filter(tr, period=sampling, poles=4)
    hband = filt + mult_banda * tr_filt
    lband = filt - mult_banda * tr_filt
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)
    rmi = 0.5 * (IX.rsi(c, 14) + IX.mfi(h, l, c, v, 14))

    idxs, dirs = [], []
    warmup = max(sampling + 5, 25)
    for i in range(warmup, len(c)):
        if ses[i] != ses[i - 1]:
            continue
        if c[i - 1] <= hband[i - 1] and c[i] > hband[i] and rmi[i] >= 48.0:
            idxs.append(i)
            dirs.append(1)
        elif c[i - 1] >= lband[i - 1] and c[i] < lband[i] and rmi[i] <= 52.0:
            idxs.append(i)
            dirs.append(-1)
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=3.0, mult_sl=1.0, cooldown_bars=15, time_stop_min=240)
