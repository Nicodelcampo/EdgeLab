"""Profit Maximizer PMax (KivancOzbilgic): bandas ATR con trinquete alrededor de EMA(hl2) para EdgeLab."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-PMAX-EXPLORER"
FAMILIA = "EXT_TV_PMAX"
INSTRUMENTO = "NQ"
PARAMETROS = dict(ma_len=[10, 14], mult_atr=[2.5, 3.0])


def senales(barras, ma_len: int = 10, mult_atr: float = 3.0) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < ma_len + 10:
        return []
    hl2 = 0.5 * (h + l)
    ma = IX.ema(hl2, ma_len)
    atr_v = IX.atr(h, l, c, ma_len, usar_rma=True)

    long_stop = np.empty(n, dtype=np.float64)
    short_stop = np.empty(n, dtype=np.float64)
    tdir = np.ones(n, dtype=np.int64)
    long_stop[0] = ma[0] - mult_atr * atr_v[0]
    short_stop[0] = ma[0] + mult_atr * atr_v[0]

    for i in range(1, n):
        ls_raw = ma[i] - mult_atr * atr_v[i]
        ss_raw = ma[i] + mult_atr * atr_v[i]
        long_stop[i] = max(ls_raw, long_stop[i - 1]) if ma[i] > long_stop[i - 1] else ls_raw
        short_stop[i] = min(ss_raw, short_stop[i - 1]) if ma[i] < short_stop[i - 1] else ss_raw
        if ma[i] > short_stop[i - 1]:
            tdir[i] = 1
        elif ma[i] < long_stop[i - 1]:
            tdir[i] = -1
        else:
            tdir[i] = tdir[i - 1]

    idxs, dirs = [], []
    warmup = max(ma_len + 5, 20)
    for i in range(warmup, n):
        if ses[i] == ses[i - 1] and tdir[i] != tdir[i - 1]:
            idxs.append(i)
            dirs.append(int(tdir[i]))
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=2.5, mult_sl=1.5, cooldown_bars=12, time_stop_min=180)
