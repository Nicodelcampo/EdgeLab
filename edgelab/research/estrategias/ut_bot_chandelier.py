"""UT Bot (QuantNomad) y Chandelier Exit (everget): máquinas de estado de trailing stop por ATR."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-UTBOT-CHANDELIER"
FAMILIA = "EXT_TV_UTBOT"
INSTRUMENTO = "NQ"
PARAMETROS = dict(modo=["utbot", "chandelier"], mult=[1.5, 2.5])


def senales(barras, modo: str = "utbot", mult: float = 1.5) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 30:
        return []
    if modo == "utbot":
        atr_v = IX.atr(h, l, c, 10, usar_rma=True)
        stop = np.empty(n, dtype=np.float64)
        stop[0] = c[0]
        idxs, dirs = [], []
        for i in range(1, n):
            n_loss = mult * atr_v[i]
            prev = stop[i - 1]
            if c[i] > prev and c[i - 1] > prev:
                stop[i] = max(prev, c[i] - n_loss)
            elif c[i] < prev and c[i - 1] < prev:
                stop[i] = min(prev, c[i] + n_loss)
            elif c[i] > prev:
                stop[i] = c[i] - n_loss
            else:
                stop[i] = c[i] + n_loss
            if i >= 15 and ses[i] == ses[i - 1]:
                if c[i - 1] <= stop[i - 1] and c[i] > stop[i]:
                    idxs.append(i)
                    dirs.append(1)
                elif c[i - 1] >= stop[i - 1] and c[i] < stop[i]:
                    idxs.append(i)
                    dirs.append(-1)
        return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=2.2, mult_sl=1.2, cooldown_bars=12, time_stop_min=180)

    # Modo Chandelier Exit (period=22)
    per = 22
    atr_v = IX.atr(h, l, c, per, usar_rma=True)
    l_stop = np.empty(n, dtype=np.float64)
    s_stop = np.empty(n, dtype=np.float64)
    tdir = np.ones(n, dtype=np.int64)
    l_stop[0] = c[0] - mult * atr_v[0]
    s_stop[0] = c[0] + mult * atr_v[0]
    idxs, dirs = [], []
    for i in range(1, n):
        start = max(0, i - per + 1)
        hi_c = float(np.max(c[start : i + 1]))
        lo_c = float(np.min(c[start : i + 1]))
        raw_l = hi_c - mult * atr_v[i]
        raw_s = lo_c + mult * atr_v[i]
        l_stop[i] = max(raw_l, l_stop[i - 1]) if c[i - 1] > l_stop[i - 1] else raw_l
        s_stop[i] = min(raw_s, s_stop[i - 1]) if c[i - 1] < s_stop[i - 1] else raw_s
        if c[i] > s_stop[i - 1]:
            tdir[i] = 1
        elif c[i] < l_stop[i - 1]:
            tdir[i] = -1
        else:
            tdir[i] = tdir[i - 1]
        if i >= 25 and ses[i] == ses[i - 1] and tdir[i] != tdir[i - 1]:
            idxs.append(i)
            dirs.append(int(tdir[i]))
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=2.5, mult_sl=1.5, cooldown_bars=15, time_stop_min=240)
