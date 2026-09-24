"""Familia 6E-REGIMES, etapa 1: el sustituto P1, la verdad L2 por bloque y la autocorrelacion dentro de la sesion."""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.liquidity_regimes import (block_proxy, session_bootstrap_mean, session_date, spearman,
                                                truth_blocks, within_session_autocorr)

NS = 1_000_000_000


def _utc(s):
    return pd.Timestamp(s, tz="UTC").value


def test_session_date_une_la_apertura_del_domingo_con_el_lunes_y_respeta_el_horario_de_verano():
    # 2026-06-28 domingo 17:30 CT (CDT, UTC-5) = 22:30 UTC -> sesion del lunes 29
    # 2026-01-11 domingo 17:30 CT (CST, UTC-6) = 23:30 UTC -> sesion del lunes 12
    # 2026-06-29 15:59 CT = 20:59 UTC -> sigue siendo la sesion del 29
    d = session_date([_utc("2026-06-28 22:30"), _utc("2026-01-11 23:30"), _utc("2026-06-29 20:59")])
    assert list(d) == [20260629, 20260112, 20260629]


def test_p1_cuenta_cambios_del_medio_dentro_de_la_sesion_y_marca_la_pausa():
    t0 = _utc("2026-06-29 14:00")                     # 09:00 CT
    ts = [t0, t0 + 10 * NS, t0 + 20 * NS, t0 + 30 * NS]
    bid = [100, 100, 101, 101]
    ask = [101, 101, 102, 102]                          # un solo cambio de medio (en el 3er trade)
    vol = [5, 5, 10, 20]
    halt_t = _utc("2026-06-29 21:05")                   # 16:05 CT: pausa
    g = block_proxy(ts + [halt_t], vol + [1], bid + [101], ask + [102], block_s=900)
    row = g.iloc[0]
    assert (row.volume, row.mid_changes, row.trades, row.p1) == (40, 1, 4, 40.0)
    assert not row.halt and g.iloc[1].halt


def test_p1_sin_cambios_divide_por_uno_y_no_cuenta_el_salto_entre_sesiones():
    t0 = _utc("2026-06-29 20:50")                     # 15:50 CT, fin de la sesion del 29
    t1 = _utc("2026-06-29 22:05")                     # 17:05 CT, sesion del 30
    g = block_proxy([t0, t1], [7, 3], [100, 150], [101, 151], block_s=900)
    assert list(g.session) == [20260629, 20260630]
    assert list(g.mid_changes) == [0, 0] and list(g.p1) == [7.0, 3.0]


def test_truth_blocks_promedia_mejor_nivel_y_cinco_niveles():
    t = [_utc("2026-06-29 14:00") + i * NS for i in range(3)]
    bid = [[10, 1, 1, 1, 1, 9], [20, 1, 1, 1, 1, 9], [30, 1, 1, 1, 1, 9]]
    ask = [[2, 1, 1, 1, 1, 9]] * 3
    g = truth_blocks(t, bid, ask, block_s=900, levels=5)
    assert g.t1.iloc[0] == (6 + 11 + 16) / 3 and g.t2.iloc[0] == ((14 + 6) + (24 + 6) + (34 + 6)) / 2 / 3


def test_autocorrelacion_dentro_de_la_sesion_recupera_un_ar1_y_no_cruza_dias():
    rng = np.random.default_rng(0)
    rows = []
    for day in range(40):
        x = 0.0
        base = _utc("2026-01-05 15:00") + day * 86400 * NS
        for k in range(60):
            x = 0.8 * x + rng.normal()
            rows.append(dict(session=day, block=base + k * 900 * NS, v=x))
    df = pd.DataFrame(rows)
    ac1 = session_bootstrap_mean(within_session_autocorr(df, "v", 1, 900))
    ac4 = session_bootstrap_mean(within_session_autocorr(df, "v", 4, 900))
    assert 0.65 < ac1[0] < 0.85 and ac1[1] < ac1[0] < ac1[2]
    assert ac4[0] < ac1[0]
    assert ac1[3] == 40


def test_spearman_es_de_rangos():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 1000]) == 1.0
