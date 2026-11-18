"""WaveTrend [LazyBear] (WT_LB): cruces wt1/wt2 en zonas extremas de sobrecompra/sobreventa para EdgeLab."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-WAVETREND-LB"
FAMILIA = "EXT_TV_WAVETREND"
INSTRUMENTO = "NQ"
PARAMETROS = dict(n1=[10, 14], nivel_ob=[45, 53])


def senales(barras, n1: int = 10, nivel_ob: int = 53) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 35:
        return []
    wt1, wt2 = IX.wavetrend(h, l, c, n1=n1, n2=21)
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)

    idxs, dirs = [], []
    for i in range(30, n):
        if ses[i] != ses[i - 1]:
            continue
        if wt1[i - 1] <= wt2[i - 1] and wt1[i] > wt2[i] and wt1[i] < -float(nivel_ob):
            idxs.append(i)
            dirs.append(1)
        elif wt1[i - 1] >= wt2[i - 1] and wt1[i] < wt2[i] and wt1[i] > float(nivel_ob):
            idxs.append(i)
            dirs.append(-1)
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=2.2, mult_sl=1.2, cooldown_bars=12, time_stop_min=180)
