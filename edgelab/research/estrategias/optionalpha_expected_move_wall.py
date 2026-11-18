"""Option Alpha 0DTE Theta Fly Trap & Challenged Exit Switch traducidos a muros intradía de Expected Move en EdgeLab."""
from __future__ import annotations

import math
import numpy as np

from edgelab.research.estrategias import _indicadores_ext as IX

NOMBRE = "EXT-OA-EXPECTED-MOVE-WALL"
FAMILIA = "EXT_OPTIONALPHA_0DTE"
INSTRUMENTO = "ES"
PARAMETROS = dict(modo=["fade_em", "challenged_switch"], mult_em=[0.8, 1.1])


def senales(barras, modo: str = "fade_em", mult_em: float = 0.8) -> list[dict]:
    ts, o, h, l, c, v, ses = IX.extraer_arrays(barras)
    n = len(c)
    if n < 50:
        return []
    atr20 = IX.atr(h, l, c, 20, usar_rma=True)

    idxs, dirs = [], []
    pos_ses = 0
    open_ses = float(o[0])
    for i in range(n):
        if i == 0 or ses[i] != ses[i - 1]:
            pos_ses = 1
            open_ses = float(o[i])
        else:
            pos_ses += 1
        if i < 40 or pos_ses < 15:
            continue

        start_iv = max(0, i - 199)
        win_atr = atr20[start_iv : i + 1]
        lo_iv = float(np.min(win_atr))
        hi_iv = float(np.max(win_atr))
        iv_rank_proxy = 100.0 * (atr20[i] - lo_iv) / max(hi_iv - lo_iv, 1e-9) if hi_iv > lo_iv else 50.0

        em = float(atr20[i]) * math.sqrt(max(1.0, 390.0 - float(pos_ses)))
        upper_wall = open_ses + float(mult_em) * em
        lower_wall = open_ses - float(mult_em) * em

        if modo == "fade_em":
            if iv_rank_proxy < 80.0:
                if c[i] >= upper_wall and c[i - 1] < upper_wall:
                    idxs.append(i)
                    dirs.append(-1)
                elif c[i] <= lower_wall and c[i - 1] > lower_wall:
                    idxs.append(i)
                    dirs.append(1)
        else:
            if c[i] >= upper_wall and c[i - 1] < upper_wall:
                idxs.append(i)
                dirs.append(1)
            elif c[i] <= lower_wall and c[i - 1] > lower_wall:
                idxs.append(i)
                dirs.append(-1)

    return IX.emitir_espaciadas(ts, ses, idxs, dirs, atr20, mult_tp=2.5, mult_sl=1.5, cooldown_bars=20, time_stop_min=180)
