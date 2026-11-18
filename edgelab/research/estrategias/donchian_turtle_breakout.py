"""Donchian Turtle Breakout (TuTCI / QuantConnect / MQL5 Original Turtle Rules) traducido para EdgeLab."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-DONCHIAN-TURTLE"
FAMILIA = "EXT_TURTLE_DONCHIAN"
INSTRUMENTO = "ES"
PARAMETROS = dict(n_entry=[20, 40], mult_tp=[2.0, 3.0])


def senales(barras, n_entry: int = 20, mult_tp: float = 2.0) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < n_entry + 5:
        return []
    hi_prev, lo_prev = IX.donchian_prev(h, l, n_entry)
    atr_v = IX.atr(h, l, c, 20, usar_rma=True)

    idxs, dirs = [], []
    for i in range(n_entry + 2, n):
        if ses[i] != ses[i - 1]:
            continue
        if h[i] > hi_prev[i] and h[i - 1] <= hi_prev[i - 1]:
            idxs.append(i)
            dirs.append(1)
        elif l[i] < lo_prev[i] and l[i - 1] >= lo_prev[i - 1]:
            idxs.append(i)
            dirs.append(-1)
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=mult_tp, mult_sl=2.0, cooldown_bars=15, time_stop_min=240)
