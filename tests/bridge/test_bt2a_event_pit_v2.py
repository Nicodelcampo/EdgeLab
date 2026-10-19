"""Regresiones del store PIT v2: cierre, secuencia, sesión, geometría y hash."""
from __future__ import annotations

import copy

import numpy as np
import pytest

from edgelab.bridge.ticks import TickSeries
from edgelab.research.bt2a_event_pit import (
    PIT_SCHEMA,
    build_event_pit_store,
    validate_event_pit_store,
)


def _ticks(*, crossed=False) -> TickSeries:
    ask = [101, 102, 103, 104, 105, 203 if crossed else 204]
    bid = [100, 101, 102, 103, 104, 204 if crossed else 105]
    return TickSeries(
        ts_ns=np.asarray([1_000_000_000, 1_000_001_000, 1_000_002_000,
                          1_000_003_000, 1_000_004_000, 1_000_004_000], dtype=np.int64),
        price_ticks=np.asarray([100, 101, 102, 103, 104, 105], dtype=np.int64),
        volume=np.ones(6, dtype=np.float64),
        bid_ticks=np.asarray(bid, dtype=np.int64),
        ask_ticks=np.asarray(ask, dtype=np.int64),
        sequence=np.arange(6, dtype=np.int64),
        tick_size=0.1,
        instrument="GC",
        contract="GC 02-26",
        source="fixture",
    )


def _result(*, duplicate=False):
    t0 = 1_000_004_000
    iso = np.datetime_as_string(np.datetime64(t0, "ns"), unit="ns")
    event = (
        f"7|{iso}|ABS_SCORE|bar=1;residual=False;signed_flow=7;d_ticks=-3;"
        "a_score=1.5;a_thr=1.0;a_pass=True;n_hist=500;t_start=1970-01-01T00:00:01.000002000;"
        "n_ticks=3;dur_ms=0;spread_ticks=1;d_ticks_mid=0;td=S"
    )
    zone = {
        "sig_ts": t0,
        "sig_idx": 4,
        "created_bar": 1,
        "lo": 10.05,
        "hi": 10.25,
        "nrows": 2,
        "frac": 0.3,
        "vol": 9.0,
        "dir": "long",
    }
    return {"events": [event], "zones": [zone, dict(zone)] if duplicate else [zone]}


def _build(*, labels=None, crossed=False, duplicate=False):
    labels = np.asarray(labels or ["S"] * 6)
    return build_event_pit_store(
        _result(duplicate=duplicate),
        _ticks(crossed=crossed),
        contract="GC 02-26",
        report_sessions={"S"},
        assignment={"S": "GC 02-26"},
        tick_size=0.1,
        tape_window_ticks=3,
        session_labels=labels,
    )


def test_corta_por_sig_idx_y_excluye_tick_posterior_con_mismo_timestamp():
    store = _build()
    row = store["rows"][0]
    assert row["schema"] == PIT_SCHEMA
    assert row["event_sequence"] == 4
    assert row["tape_window_start_idx"] == 2
    assert row["tape_window_end_idx"] == 4
    assert row["spread_p90_ticks"] == 1.0
    assert row["as_of_ok"] is True


def test_tasa_declara_n_menos_un_intervalos():
    row = _build()["rows"][0]
    assert row["tape_window_ticks"] == 3
    assert row["tape_interval_count"] == 2
    assert row["tape_span_ns"] == 2_000
    assert row["tape_rate_per_s"] == 1_000_000.0


def test_no_cruza_sesion_y_locked_es_valido_pero_crossed_no():
    row = _build(labels=["A", "A", "A", "S", "S", "S"])["rows"][0]
    assert row["as_of_ok"] is False
    assert row["tape_unavailable_reason"] == "SESSION_BOUNDARY"
    with pytest.raises(ValueError, match="book cruzado"):
        _build(crossed=True)


def test_abs_score_se_fecha_por_publicacion_no_por_t_start():
    row = _build()["rows"][0]
    assert row["indicator_available_at_ns"] == row["event_time_ns"]
    assert row["feature_available_at_ns"] == row["event_time_ns"]


def test_geometria_es_entera_en_medios_ticks_y_eventos_son_uno_a_uno():
    row = _build()["rows"][0]
    assert row["zone_lo_half_ticks"] == 201
    assert row["zone_hi_half_ticks"] == 205
    assert row["zone_width_half_ticks"] == 4
    with pytest.raises(ValueError, match="event_key duplicada"):
        _build(duplicate=True)


def test_manifest_y_hashes_detectan_mutacion():
    store = _build()
    validate_event_pit_store(store)
    damaged = copy.deepcopy(store)
    damaged["rows"][0]["a_score"] = 99.0
    with pytest.raises(ValueError, match="record_sha256"):
        validate_event_pit_store(damaged)


def test_no_hay_campos_de_respuesta():
    forbidden = ("mfe", "mae", "pnl", "return", "hit_rate", "d_hat", "net_ticks")
    for key in _build()["rows"][0]:
        assert not any(token in key.lower() for token in forbidden)
