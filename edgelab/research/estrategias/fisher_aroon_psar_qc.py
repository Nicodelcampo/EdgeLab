"""QuantConnect Lab Templates: Fisher Transform Reversal, Aroon Trend (+50/-50) y Parabolic SAR."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-QC-FISHER-AROON-PSAR"
FAMILIA = "EXT_QC_LAB_TEMPLATES"
INSTRUMENTO = "NQ"
PARAMETROS = dict(modelo=["fisher", "aroon", "psar"], mult_tp=[1.5, 2.5])


def senales(barras, modelo: str = "fisher", mult_tp: float = 2.0) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 35:
        return []
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)
    idxs, dirs = [], []

    if modelo == "fisher":
        fish, fish_prev = IX.fisher_transform(h, l, period=10)
        for i in range(15, n):
            if ses[i] != ses[i - 1]:
                continue
            if fish[i - 1] < -1.8 and fish[i] > fish_prev[i]:
                idxs.append(i)
                dirs.append(1)
            elif fish[i - 1] > 1.8 and fish[i] < fish_prev[i]:
                idxs.append(i)
                dirs.append(-1)
    elif modelo == "aroon":
        osc = IX.aroon_osc(h, l, period=25)
        for i in range(28, n):
            if ses[i] != ses[i - 1]:
                continue
            if osc[i - 1] <= 50.0 and osc[i] > 50.0:
                idxs.append(i)
                dirs.append(1)
            elif osc[i - 1] >= -50.0 and osc[i] < -50.0:
                idxs.append(i)
                dirs.append(-1)
    else:
        _, sdir = IX.parabolic_sar(h, l, c, af_step=0.02, af_max=0.20)
        for i in range(15, n):
            if ses[i] == ses[i - 1] and sdir[i] != sdir[i - 1]:
                idxs.append(i)
                dirs.append(int(sdir[i]))

    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=mult_tp, mult_sl=1.3, cooldown_bars=15, time_stop_min=180)
