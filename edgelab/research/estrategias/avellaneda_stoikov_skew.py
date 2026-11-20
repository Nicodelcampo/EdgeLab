"""Avellaneda-Stoikov Market Making Skew (Hummingbot) adaptado a ejecución direccional intradía en EdgeLab."""
from __future__ import annotations

import math
import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-AVELLANEDA-STOIKOV"
FAMILIA = "EXT_HUMMINGBOT_AS"
INSTRUMENTO = "ES"
PARAMETROS = dict(gamma=[0.5, 1.5], kappa=[1.5, 3.0])


def senales(barras, gamma: float = 0.5, kappa: float = 1.5) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 30:
        return []
    ema20 = IX.ema(c, 20)
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)
    diffs = np.zeros(n, dtype=np.float64)
    diffs[1:] = np.diff(c)

    g = max(float(gamma), 1e-4)
    kap = max(float(kappa), 1e-4)
    spread_kappa = (1.0 / g) * math.log(1.0 + g / kap)

    idxs, dirs = [], []
    pos_ses = 0
    for i in range(n):
        pos_ses = 1 if (i == 0 or ses[i] != ses[i - 1]) else (pos_ses + 1)
        if i < 25 or pos_ses < 5:
            continue
        sigma = max(float(np.std(diffs[i - 19 : i + 1])), 0.25)
        t_left = max(0.05, (390.0 - float(pos_ses)) / 390.0)
        s_ref = float(ema20[i])
        q = max(-1.0, min(1.0, (c[i] - s_ref) / max(2.0 * sigma, 1e-6)))
        var_t = g * (sigma * sigma) * t_left
        r = s_ref - q * var_t
        delta = 0.5 * var_t + spread_kappa
        opt_bid = r - delta
        opt_ask = r + delta
        if c[i] <= opt_bid:
            idxs.append(i)
            dirs.append(1)
        elif c[i] >= opt_ask:
            idxs.append(i)
            dirs.append(-1)
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=1.8, mult_sl=1.2, cooldown_bars=12, time_stop_min=120)
