"""Smart Money Concepts [LuxAlgo]: detección causal de FVG con desplazamiento ATR y retesteo sin mitigar."""
from __future__ import annotations

import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-SMC-FVG-OB"
FAMILIA = "EXT_TV_LUX_SMC"
INSTRUMENTO = "NQ"
PARAMETROS = dict(disp_atr=[0.8, 1.2], max_edad=[15, 30])


def senales(barras, disp_atr: float = 0.8, max_edad: int = 20) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 25:
        return []
    atr_v = IX.atr(h, l, c, 14, usar_rma=True)

    # Cada zona: [dir (+1/-1), lo, hi, barra_creacion, ses_id]
    zonas: list[list[float | int]] = []
    idxs, dirs = [], []

    for i in range(18, n):
        # Detección causal de FVG en vela i usando i-2, i-1, i
        if ses[i] == ses[i - 2]:
            cuerpo = abs(c[i - 1] - o[i - 1])
            if l[i] > h[i - 2] and (c[i - 1] > o[i - 1]) and cuerpo >= float(disp_atr) * atr_v[i - 1]:
                zonas.append([1, float(h[i - 2]), float(l[i]), i, int(ses[i])])
            elif h[i] < l[i - 2] and (c[i - 1] < o[i - 1]) and cuerpo >= float(disp_atr) * atr_v[i - 1]:
                zonas.append([-1, float(h[i]), float(l[i - 2]), i, int(ses[i])])

        if len(zonas) > 25:
            zonas = zonas[-25:]

        if ses[i] != ses[i - 1]:
            continue

        restantes = []
        disparo = 0
        for z in zonas:
            zd, zlo, zhi, zbar, zses = int(z[0]), float(z[1]), float(z[2]), int(z[3]), int(z[4])
            if (i - zbar) > max_edad or zses != int(ses[i]):
                continue
            if i == zbar:
                restantes.append(z)
                continue
            if disparo == 0 and zd == 1 and l[i] <= zhi and c[i] >= zlo and c[i] > o[i]:
                disparo = 1
                continue  # mitigada tras disparar
            if disparo == 0 and zd == -1 and h[i] >= zlo and c[i] <= zhi and c[i] < o[i]:
                disparo = -1
                continue
            restantes.append(z)
        zonas = restantes
        if disparo != 0:
            idxs.append(i)
            dirs.append(disparo)

    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr_v, mult_tp=2.0, mult_sl=1.0, cooldown_bars=12, time_stop_min=180)
