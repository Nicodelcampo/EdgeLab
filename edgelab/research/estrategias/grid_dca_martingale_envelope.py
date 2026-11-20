"""Grid / Scaled DCA / Martingale Envelope (Pionex / Gainium / WunderTrading / 3Commas) traducido para EdgeLab."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-GRID-DCA-ENVELOPE"
FAMILIA = "EXT_PIONEX_GAINIUM_GRID"
INSTRUMENTO = "NQ"
PARAMETROS = dict(step_scale=[1.1, 1.3], n_steps=[3, 5])


def senales(barras, step_scale: float = 1.1, n_steps: int = 3) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 35:
        return []
    ema30 = IX.ema(c, 30)
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)

    # Escalera geométrica normalizada por ATR: CD_k = D * sum_{j=0}^{k-1} SS^j
    mults = []
    acum = 0.0
    for j in range(int(n_steps)):
        acum += 0.7 * (float(step_scale) ** j)
        mults.append(acum)

    idxs, dirs = [], []
    for i in range(32, n):
        if ses[i] != ses[i - 1]:
            continue
        desv = c[i] - ema30[i]
        a = max(float(atr_v[i]), 0.5)
        for m in mults:
            umbral = m * a
            if desv <= -umbral and c[i] > o[i]:
                idxs.append(i)
                dirs.append(1)
                break
            if desv >= umbral and c[i] < o[i]:
                idxs.append(i)
                dirs.append(-1)
                break
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=1.8, mult_sl=1.4, cooldown_bars=12, time_stop_min=150)
