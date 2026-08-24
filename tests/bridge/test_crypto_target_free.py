from __future__ import annotations

import json

import numpy as np
import pytest

from edgelab.bridge.ticks import TickSeries
from edgelab.crypto.target_free import (
    TARGET_FREE_CENSUS_SCHEMA,
    build_unit_sensitivity_plan,
    load_target_free_spec,
    target_free_census,
)


def _ticks(*, ask=(101, 102, 103), sequence=(0, 1, 2)) -> TickSeries:
    return TickSeries(
        ts_ns=np.asarray([1_000, 1_000, 2_000], dtype=np.int64),
        price_ticks=np.asarray([101, 101, 102], dtype=np.int64),
        volume=np.asarray([1.0, 2.0, 3.0], dtype=np.float64),
        bid_ticks=np.asarray([100, 101, 102], dtype=np.int64),
        ask_ticks=np.asarray(ask, dtype=np.int64),
        sequence=np.asarray(sequence, dtype=np.int64),
        tick_size=0.1,
        instrument="BTCUSDT",
        contract="BTCUSDT-PERP",
        source="fixture",
    )


def test_sensibilidad_de_unidad_es_explicita_determinista_y_sin_default():
    points = build_unit_sensitivity_plan("btcusdt", "0.001", ["0.5", "1", "2"])
    assert [p.quantity_unit_base for p in points] == ["0.0005", "0.001", "0.002"]
    assert len({p.config_id for p in points}) == 3
    assert points == build_unit_sensitivity_plan("BTCUSDT", "0.001", ["0.5", "1", "2"])
    with pytest.raises(ValueError, match="incluir 1"):
        build_unit_sensitivity_plan("BTCUSDT", "0.001", ["0.5", "2"])


def test_preregistro_versionado_permanece_target_free():
    spec = load_target_free_spec("specs/crypto_bt2_target_free_v1.json")
    assert spec["firewall"]["outcomes_accessed"] is False
    assert spec["firewall"]["response_columns"] == []
    assert [stage["symbol"] for stage in spec["stages"]] == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def test_preregistro_rechaza_cualquier_apertura_de_respuesta(tmp_path):
    spec = json.loads(open("specs/crypto_bt2_target_free_v1.json", encoding="utf-8").read())
    spec["firewall"]["returns_accessed"] = True
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(ValueError, match="firewall"):
        load_target_free_spec(path)


def test_censo_usa_identidad_timestamp_mas_secuencia_y_no_abre_outcomes():
    census = target_free_census(_ticks())
    assert census["schema"] == TARGET_FREE_CENSUS_SCHEMA
    assert census["same_timestamp_adjacent_pairs"] == 1
    assert census["outcomes_opened"] is False
    assert census["target_free"] is True
    assert census["n_ticks"] == 3


def test_censo_falla_cerrado_ante_orden_ambiguo_o_book_cruzado():
    with pytest.raises(ValueError, match="orden causal"):
        target_free_census(_ticks(sequence=(1, 0, 2)))
    with pytest.raises(ValueError, match="book cruzado"):
        target_free_census(_ticks(ask=(99, 102, 103)))
