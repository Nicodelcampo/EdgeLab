"""Kalman Filter Z-Score Stat-Arb (QuantConnect / WunderTrading Market Neutral Z-Score) para EdgeLab."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-KALMAN-ZSCORE"
FAMILIA = "EXT_QC_KALMAN"
INSTRUMENTO = "ES"
PARAMETROS = dict(z_entry=[1.8, 2.2], mult_tp=[1.5, 2.0])


def senales(barras, z_entry: float = 2.0, mult_tp: float = 1.5) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 40:
        return []
    _, z = IX.kalman_1d(c, q=1e-4, r=1e-2, z_win=30)
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)

    idxs, dirs = [], []
    for i in range(35, n):
        if ses[i] != ses[i - 1]:
            continue
        if z[i] < -float(z_entry):
            idxs.append(i)
            dirs.append(1)
        elif z[i] > float(z_entry):
            idxs.append(i)
            dirs.append(-1)
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=mult_tp, mult_sl=1.2, cooldown_bars=15, time_stop_min=150)
