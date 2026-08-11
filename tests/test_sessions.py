from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from edgelab.sessions import (
    NEW_YORK_TZ,
    build_session_matrices,
    minute_window_matrices,
    rth_matrices,
    valid_days_mask,
    valid_window_mask,
    ym_prerange_matrices,
)


def _frame(local_ranges, aware=False):
    indexes = []
    values = []
    cursor = 1000.0
    for start, periods in local_ranges:
        local = pd.date_range(start, periods=periods, freq="min", tz=NEW_YORK_TZ)
        utc = local.tz_convert("UTC")
        indexes.extend(utc if aware else utc.tz_localize(None))
        for offset in range(periods):
            price = cursor + offset
            values.append((price, price + 2, price - 1, price + 0.5, 10 + offset))
        cursor += 1000
    return pd.DataFrame(
        values,
        index=pd.DatetimeIndex(indexes),
        columns=["open", "high", "low", "close", "volume"],
    )


def _sparse_day(date, rows):
    indexes = []
    values = []
    for hour, minute, close in rows:
        local = pd.Timestamp(date, tz=NEW_YORK_TZ).replace(hour=hour, minute=minute)
        indexes.append(local.tz_convert("UTC").tz_localize(None))
        values.append((close, close, close, close, 1.0))
    return pd.DataFrame(
        values,
        index=pd.DatetimeIndex(indexes),
        columns=["open", "high", "low", "close", "volume"],
    )


def test_api_existente_rth_es_alias_exacto():
    frame = _sparse_day(
        "2026-01-05", [(9, 30, 100.0), (9, 31, 101.0), (15, 59, 99.0)]
    )
    rth = rth_matrices(frame)
    configurable = build_session_matrices(
        frame, start_h=9, start_m=30, duration_min=390
    )
    assert rth.keys() == configurable.keys()
    for key in rth:
        if key == "days":
            assert list(rth[key]) == list(configurable[key])
        else:
            np.testing.assert_array_equal(rth[key], configurable[key])
    assert set(rth) == {
        "O", "H", "L", "C", "V", "days", "prev_close", "rth_close"
    }


def test_api_existente_ym_half_open_se_conserva():
    frame = _sparse_day(
        "2026-01-05",
        [(8, 12, 10.0), (8, 45, 12.0), (9, 11, 11.0), (9, 12, 999.0)],
    )
    result = build_session_matrices(
        frame, start_h=8, start_m=12, duration_min=60
    )
    assert result["O"].shape == (1, 60)
    assert result["O"][0, 0] == 10.0
    assert result["O"][0, 33] == 12.0
    assert result["O"][0, 59] == 11.0
    assert 999.0 not in result["O"]


def test_ventana_vacia_falla_declarado():
    frame = _sparse_day("2026-01-05", [(9, 30, 100.0)])
    with pytest.raises(ValueError, match="ventana"):
        build_session_matrices(frame, start_h=8, start_m=12, duration_min=60)


def test_prev_close_historico_encadena_dias_validos():
    first = _sparse_day("2026-01-05", [(9, 30, 100.0), (15, 59, 110.0)])
    third = _sparse_day("2026-01-07", [(9, 30, 200.0), (15, 59, 210.0)])
    result = rth_matrices(pd.concat([first, third]).sort_index())
    assert np.isnan(result["prev_close"][0])
    assert result["prev_close"][1] == 110.0


def test_ym_prerange_es_60_minutos_y_respeta_est_ed_t():
    frame = _frame(
        [
            ("2026-01-12 08:12", 60),
            ("2026-08-07 08:12", 60),
        ]
    )
    out = ym_prerange_matrices(
        frame, session_days=["2026-01-12", "2026-08-07"]
    )
    assert out["O"].shape == (2, 60)
    assert out["window_start"] == "08:12"
    assert out["window_end"] == "09:12"
    assert out["endpoint_policy"] == "half_open"
    assert out["m_rth"][0] == -78 and out["m_rth"][-1] == -19
    assert out["timezone"] == NEW_YORK_TZ
    assert out["calendar_complete"]
    assert out["valid"].tolist() == [True, True]
    assert out["range_width"].tolist() == pytest.approx([62.0, 62.0])
    assert len(out["calendar_sha256"]) == 64


def test_calendario_explicito_preserva_dia_sin_datos():
    frame = _frame([("2026-01-12 08:12", 60)])
    out = ym_prerange_matrices(
        frame, session_days=["2026-01-12", "2026-01-13"]
    )
    assert out["O"].shape == (2, 60)
    assert np.isnan(out["O"][1]).all()
    assert out["valid"].tolist() == [True, False]
    assert np.isnan(out["range_width"][1])


def test_inferir_dias_queda_marcado_como_no_formal():
    frame = _frame([("2026-08-07 08:12", 60)])
    out = minute_window_matrices(frame, start="08:12", end="09:12")
    assert not out["calendar_complete"]
    assert valid_window_mask(out["O"]).tolist() == [True]


def test_barra_fuera_del_calendario_falla_cerrado():
    frame = _frame(
        [("2026-08-07 08:12", 60), ("2026-08-10 08:12", 60)]
    )
    with pytest.raises(ValueError, match="fuera de session_days"):
        ym_prerange_matrices(frame, session_days=["2026-08-07"])


def test_indice_aware_y_naive_producen_lo_mismo():
    naive = _frame([("2026-08-07 08:12", 60)], aware=False)
    aware = _frame([("2026-08-07 08:12", 60)], aware=True)
    first = ym_prerange_matrices(naive, session_days=["2026-08-07"])
    second = ym_prerange_matrices(aware, session_days=["2026-08-07"])
    assert np.array_equal(first["O"], second["O"])
    assert first["calendar_sha256"] == second["calendar_sha256"]


def test_timestamps_duplicados_no_se_sobrescriben():
    frame = _frame([("2026-08-07 08:12", 60)])
    duplicate = pd.concat([frame.iloc[:1], frame]).sort_index()
    with pytest.raises(ValueError, match="duplicados"):
        ym_prerange_matrices(duplicate, session_days=["2026-08-07"])


def test_window_cross_midnight_asigna_fecha_de_inicio():
    frame = _frame([("2026-08-07 23:58", 4)])
    out = minute_window_matrices(
        frame,
        start="23:58",
        end="00:02",
        session_days=["2026-08-07"],
    )
    assert out["O"].shape == (1, 4)
    assert not np.isnan(out["O"]).any()


def test_valid_days_mask_exige_apertura_y_cobertura():
    matrix = np.full((3, 60), np.nan)
    matrix[0, :60] = 1.0
    matrix[1, 5:60] = 1.0
    matrix[2, 0] = 1.0
    assert valid_days_mask(matrix, min_minutes=30).tolist() == [True, False, False]
