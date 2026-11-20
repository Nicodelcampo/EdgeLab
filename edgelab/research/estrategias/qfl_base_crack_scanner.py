"""QFL (Quickfingers Luc) / Altrady Crypto Base Scanner: detección causal de bases + crack en múltiplos de ATR."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-QFL-BASE-CRACK"
FAMILIA = "EXT_ALTRADY_QFL"
INSTRUMENTO = "NQ"
PARAMETROS = dict(win_base=[20, 35], crack_atr=[0.8, 1.2])


def senales(barras, win_base: int = 20, crack_atr: float = 1.0) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < win_base + 15:
        return []
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)

    base_sup = None
    base_res = None
    idxs, dirs = [], []

    for i in range(win_base + 4, n):
        p = i - 3
        start = max(0, p - win_base)
        if l[p] <= float(np.min(l[start : i + 1])) and (float(np.max(h[p + 1 : i + 1])) - l[p]) >= float(atr_v[p]):
            base_sup = float(l[p])
        if h[p] >= float(np.max(h[start : i + 1])) and (h[p] - float(np.min(l[p + 1 : i + 1]))) >= float(atr_v[p]):
            base_res = float(h[p])

        if ses[i] != ses[i - 1]:
            continue
        umbral = float(crack_atr) * float(atr_v[i])
        if base_sup is not None and c[i] <= base_sup - umbral:
            idxs.append(i)
            dirs.append(1)
            base_sup = None
        elif base_res is not None and c[i] >= base_res + umbral:
            idxs.append(i)
            dirs.append(-1)
            base_res = None

    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=2.0, mult_sl=1.3, cooldown_bars=15, time_stop_min=180)
