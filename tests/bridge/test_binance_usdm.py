from __future__ import annotations

import pandas as pd
import pytest

from edgelab.crypto.binance_usdm import BinanceUsdmContract, load_binance_usdm_pair

_BASE_MS = 1_711_756_800_000


def _write_pair(tmp_path, *, first_book_time=None, trade_ids=(10, 11)):
    first_book_time = _BASE_MS - 1 if first_book_time is None else first_book_time
    trades = pd.DataFrame(
        [
            [trade_ids[0], 100.1, 0.002, 0.2002, _BASE_MS, "false"],
            [trade_ids[1], 100.0, 0.003, 0.3000, _BASE_MS + 1, "true"],
        ]
    )
    books = pd.DataFrame(
        [
            [1, 100.0, 2.0, 100.1, 3.0, first_book_time, first_book_time],
            [2, 100.1, 2.0, 100.2, 3.0, _BASE_MS, _BASE_MS],
            [3, 99.9, 2.0, 100.0, 3.0, _BASE_MS + 1, _BASE_MS + 1],
        ]
    )
    tp = tmp_path / "BTCUSDT-trades.csv"
    bp = tmp_path / "BTCUSDT-bookTicker.csv"
    trades.to_csv(tp, index=False, header=False)
    books.to_csv(bp, index=False, header=False)
    return tp, bp


def _contract():
    return BinanceUsdmContract(symbol="BTCUSDT", tick_size="0.1", quantity_unit_base="0.001",
                               quantity_unit_status="PROVISIONAL_EXCHANGE_STEP_SIZE",
                               quantity_unit_source="exchangeInfo.LOT_SIZE.stepSize")


def test_join_usa_book_estrictamente_anterior_y_no_el_de_igual_timestamp(tmp_path):
    tp, bp = _write_pair(tmp_path)
    out = load_binance_usdm_pair(tp, bp, _contract())
    assert out.report.join_coverage == 1.0
    assert out.report.strict_prior_violations == 0
    assert out.sidecar["book_update_id"].tolist() == [1, 2]
    assert (out.sidecar["book_transaction_time_ns"] < out.sidecar["trade_time_ns"]).all()


def test_unidad_de_volumen_es_explicita_y_no_heredada_de_futuros_cme(tmp_path):
    tp, bp = _write_pair(tmp_path)
    out = load_binance_usdm_pair(tp, bp, _contract())
    assert out.ticks.volume.tolist() == pytest.approx([2.0, 3.0])
    assert out.report.quantity_unit_base == "0.001"
    # La unidad sigue siendo PROVISIONAL y con procedencia declarada. La etiqueta
    # dejo de decir USER_SUPPLIED porque el valor sale de exchangeInfo, no del
    # usuario; lo que el test protege —que sea explicita y no heredada de CME—
    # no cambia.
    assert out.report.quantity_unit_status == "PROVISIONAL_EXCHANGE_STEP_SIZE"
    assert out.report.quantity_unit_source == "exchangeInfo.LOT_SIZE.stepSize"
    assert out.report.quantity_unit_status.startswith("PROVISIONAL_")


def test_join_sin_book_previo_falla_cerrado(tmp_path):
    tp, bp = _write_pair(tmp_path, first_book_time=_BASE_MS)
    with pytest.raises(ValueError, match="join causal incompleto"):
        load_binance_usdm_pair(tp, bp, _contract())


def test_gaps_de_trade_id_quedan_declarados(tmp_path):
    tp, bp = _write_pair(tmp_path, trade_ids=(10, 12))
    out = load_binance_usdm_pair(tp, bp, _contract())
    assert out.report.id_gap_ranges == 1
    assert out.report.missing_trade_ids == 1
    assert out.report.status == "PILOT_ACCEPTED_TARGET_FREE_WITH_ID_GAPS"


def test_precio_fuera_del_tick_size_falla_cerrado(tmp_path):
    tp, bp = _write_pair(tmp_path)
    trades = pd.read_csv(tp, header=None)
    trades.iloc[0, 1] = 100.15
    trades.to_csv(tp, index=False, header=False)
    with pytest.raises(ValueError, match="no alinea"):
        load_binance_usdm_pair(tp, bp, _contract())
