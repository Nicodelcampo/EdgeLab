"""AlphaTrend (KivancOzbilgic): bandas ATR adaptadas por MFI/RSI con confirmación de cruce contra 2 barras previas."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-ALPHATREND-MFI"
FAMILIA = "EXT_TV_ALPHATREND"
INSTRUMENTO = "NQ"
PARAMETROS = dict(ap=[10, 14], coeff=[1.0, 1.5])


def senales(barras, ap: int = 14, coeff: float = 1.0) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < ap + 10:
        return []
    atr_sma = IX.atr(h, l, c, ap, usar_rma=False)
    mfi_v = IX.mfi(h, l, c, v, ap)
    at_line = np.empty(n, dtype=np.float64)
    at_line[0] = c[0]
    for i in range(1, n):
        up_t = l[i] - coeff * atr_sma[i]
        dn_t = h[i] + coeff * atr_sma[i]
        if mfi_v[i] >= 50.0:
            at_line[i] = max(up_t, at_line[i - 1])
        else:
            at_line[i] = min(dn_t, at_line[i - 1])

    idxs, dirs = [], []
    warmup = max(ap + 5, 20)
    for i in range(warmup, n):
        if ses[i] != ses[i - 1]:
            continue
        if at_line[i - 1] <= at_line[i - 3] and at_line[i] > at_line[i - 2]:
            idxs.append(i)
            dirs.append(1)
        elif at_line[i - 1] >= at_line[i - 3] and at_line[i] < at_line[i - 2]:
            idxs.append(i)
            dirs.append(-1)
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_sma, mult_tp=2.0, mult_sl=1.2, cooldown_bars=12, time_stop_min=180)
