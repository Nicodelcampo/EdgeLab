# -*- coding: utf-8 -*-
"""`edgelab/sessions.py` — sin tests hasta hoy, pese a tener 5 consumidores
reales (`strategies/orb.py`, `orb_tickfill.py`, `noise_area.py`,
`cross_check.py`, `validation/smoke_test.py`).

Generalizado el 2026-08-10 de RTH-only a ventana configurable
(`build_session_matrices`), investigado primero en una sesión paralela
(Google Antigravity). Estos tests verifican dos cosas antes de confiar en el
cambio: que ningún consumidor existente cambia de comportamiento (el alias
`rth_matrices` es exacto), y que la ventana nueva (YM-PRERANGE, 08:12–09:12
ET) arma la matriz correcta — con verdad conocida, no por inspección visual.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from edgelab.sessions import build_session_matrices, rth_matrices, valid_days_mask


def _velas_un_dia(fecha_et, filas):
    """`filas`: lista de (hora_et, minuto_et, close). Un dia, sin gaps salvo
    los que `filas` deje afuera. Indice UTC naive, como pide el modulo
    (ET = UTC-5 en enero, sin DST -- evita el cruce de DST en el fixture)."""
    idx, close = [], []
    for h, m, c in filas:
        et = pd.Timestamp(fecha_et, tz="America/New_York").replace(hour=h, minute=m)
        idx.append(et.tz_convert("UTC").tz_localize(None))
        close.append(c)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                       "close": close, "volume": [1.0] * len(close)}, index=idx)
    return df


def test_rth_matrices_es_identico_a_build_session_matrices_con_rth():
    """El alias no puede cambiar el resultado para NINGUN consumidor viejo."""
    df = _velas_un_dia("2026-01-05", [(9, 30, 100.0), (9, 31, 101.0), (15, 59, 99.0)])
    viejo = rth_matrices(df)
    nuevo = build_session_matrices(df, start_h=9, start_m=30, duration_min=390)
    assert viejo.keys() == nuevo.keys()
    for k in viejo:
        if k == "days":
            assert list(viejo[k]) == list(nuevo[k])
        else:
            np.testing.assert_array_equal(viejo[k], nuevo[k])


def test_rth_matrices_forma_390_minutos():
    df = _velas_un_dia("2026-01-05", [(9, 30, 100.0), (12, 0, 105.0), (15, 59, 99.0)])
    r = rth_matrices(df)
    assert r["O"].shape == (1, 390)
    # minuto 0 = 09:30, minuto 389 = 15:59
    assert r["O"][0, 0] == 100.0
    assert r["O"][0, 389] == 99.0
    assert np.isnan(r["O"][0, 1])          # 09:31 sin dato


def test_ventana_YM_PRERANGE_08_12_a_09_12():
    """La ventana que RTH-only descartaba en silencio (m_rth negativo)."""
    df = _velas_un_dia("2026-01-05", [
        (8, 12, 10.0),   # primer minuto de la ventana
        (8, 45, 12.0),
        (9, 11, 11.0),   # ultimo minuto de la ventana (duration_min=60 -> [0,60))
        (9, 12, 999.0),  # AFUERA -- no debe aparecer en la matriz
        (9, 30, 999.0),  # RTH, tambien afuera de esta ventana
    ])
    r = build_session_matrices(df, start_h=8, start_m=12, duration_min=60)
    assert r["O"].shape == (1, 60)
    assert r["O"][0, 0] == 10.0             # 08:12
    assert r["O"][0, 33] == 12.0            # 08:45
    assert r["O"][0, 59] == 11.0            # 09:11
    assert not np.isnan(r["O"][0, 59])
    assert np.isnan(r["O"][0, 0:59]).sum() == 57   # solo 3 minutos con dato


def test_ventana_vacia_falla_declarado_no_en_silencio():
    df = _velas_un_dia("2026-01-05", [(9, 30, 100.0)])   # solo RTH
    with pytest.raises(ValueError, match="ventana"):
        build_session_matrices(df, start_h=8, start_m=12, duration_min=60)


def test_prev_close_encadena_dias_validos_salteando_huecos():
    d1 = _velas_un_dia("2026-01-05", [(9, 30, 100.0), (15, 59, 110.0)])
    d3 = _velas_un_dia("2026-01-07", [(9, 30, 200.0), (15, 59, 210.0)])
    df = pd.concat([d1, d3]).sort_index()
    r = rth_matrices(df)
    assert len(r["days"]) == 2
    assert np.isnan(r["prev_close"][0])     # primer dia, sin previo
    assert r["prev_close"][1] == 110.0      # segundo dia valido, no importa el gap real de fechas


def test_valid_days_mask_exige_apertura_y_cobertura():
    O = np.full((3, 60), np.nan)
    O[0, 0:60] = 1.0            # dia 0: apertura + cobertura completa
    O[1, 5:60] = 1.0            # dia 1: SIN apertura (minuto 0 vacio)
    O[2, 0] = 1.0                # dia 2: apertura pero sin cobertura
    mask = valid_days_mask(O, min_minutes=30)
    assert list(mask) == [True, False, False]
