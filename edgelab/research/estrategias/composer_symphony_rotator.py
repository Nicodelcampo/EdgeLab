"""Composer Symphony Rotator (FTLT / RSI Tester / Deez Max-Drawdown Gate) traducido a barras M1 en EdgeLab."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-COMPOSER-SYMPHONY"
FAMILIA = "EXT_COMPOSER_SYMPHONY"
INSTRUMENTO = "NQ"
PARAMETROS = dict(rsi_ob=[75, 80], rsi_os=[25, 30])


def senales(barras, rsi_ob: int = 75, rsi_os: int = 25) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 110:
        return []
    sma100 = IX.sma(c, 100)
    rsi10 = IX.rsi(c, 10)
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)

    idxs, dirs = [], []
    for i in range(105, n):
        if ses[i] != ses[i - 1]:
            continue
        peak17 = float(np.max(c[i - 17 : i + 1]))
        dd17 = (peak17 - c[i]) / max(peak17, 1e-9)
        if rsi10[i] > float(rsi_ob):
            # Sobrecompra extrema -> rotación defensiva / corta tipo UVXY/SQQQ
            idxs.append(i)
            dirs.append(-1)
        elif (c[i] > sma100[i] and rsi10[i] < float(rsi_os)) or (dd17 > 0.002 and rsi10[i] < 35.0):
            # Retroceso en tendencia alcista o sobreventa -> compra de rebote
            idxs.append(i)
            dirs.append(1)
    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=2.2, mult_sl=1.3, cooldown_bars=15, time_stop_min=180)
