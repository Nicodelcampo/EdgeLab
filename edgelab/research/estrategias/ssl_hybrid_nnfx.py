"""SSL Hybrid NNFX (Mihkel00): Baseline HMA + canal ATR 0.2x + máquina de estado SSL sobre High/Low."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-SSL-HYBRID"
FAMILIA = "EXT_TV_SSL"
INSTRUMENTO = "NQ"
PARAMETROS = dict(len_base=[40, 60], len_ssl=[5, 10])


def senales(barras, len_base: int = 60, len_ssl: int = 5) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < len_base + 10:
        return []
    baseline = IX.hma(c, len_base)
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)
    base_up = baseline + 0.2 * atr_v
    base_dn = baseline - 0.2 * atr_v

    h_ma = IX.sma(h, len_ssl)
    l_ma = IX.sma(l, len_ssl)
    hlv = np.ones(n, dtype=np.int64)
    ssl1 = np.empty(n, dtype=np.float64)
    for i in range(n):
        if c[i] > h_ma[i]:
            hlv[i] = 1
        elif c[i] < l_ma[i]:
            hlv[i] = -1
        else:
            hlv[i] = hlv[i - 1] if i > 0 else 1
        ssl1[i] = l_ma[i] if hlv[i] == 1 else h_ma[i]

    idxs, dirs = [], []
    warmup = max(len_base + 5, 65)
    for i in range(warmup, n):
        if ses[i] != ses[i - 1]:
            continue
        if c[i] > base_up[i] and c[i] > ssl1[i] and (c[i - 1] <= base_up[i - 1] or c[i - 1] <= ssl1[i - 1]):
            if abs(c[i] - ssl1[i]) <= 1.2 * atr_v[i]:
                idxs.append(i)
                dirs.append(1)
        elif c[i] < base_dn[i] and c[i] < ssl1[i] and (c[i - 1] >= base_dn[i - 1] or c[i - 1] >= ssl1[i - 1]):
            if abs(c[i] - ssl1[i]) <= 1.2 * atr_v[i]:
                idxs.append(i)
                dirs.append(-1)
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=2.0, mult_sl=1.2, cooldown_bars=15, time_stop_min=180)
