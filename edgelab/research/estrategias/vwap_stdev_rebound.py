"""VWAP StDev Bands + Coinrule VWAP & RSI Rebound: toque a bandas VWAP ± k*sigma confirmado con RSI."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-VWAP-STDEV-REBOUND"
FAMILIA = "EXT_COINRULE_VWAP"
INSTRUMENTO = "NQ"
PARAMETROS = dict(k_sigma=[1.5, 2.0], rsi_lim=[35, 45])


def senales(barras, k_sigma: float = 1.5, rsi_lim: int = 35) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 30:
        return []
    vwap, sd = IX.vwap_sesion(h, l, c, v, ses)
    rsi_v = IX.rsi(c, 14)
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)

    idxs, dirs = [], []
    en_ses = 0
    for i in range(n):
        en_ses = 1 if (i == 0 or ses[i] != ses[i - 1]) else (en_ses + 1)
        if en_ses < 20 or sd[i] <= 1e-9:
            continue
        up = vwap[i] + float(k_sigma) * sd[i]
        dn = vwap[i] - float(k_sigma) * sd[i]
        if c[i] <= dn and rsi_v[i] < float(rsi_lim):
            idxs.append(i)
            dirs.append(1)
        elif c[i] >= up and rsi_v[i] > (100.0 - float(rsi_lim)):
            idxs.append(i)
            dirs.append(-1)
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=2.0, mult_sl=1.2, cooldown_bars=15, time_stop_min=180)
