"""Precios fuera de la grilla de tick: abortan por default, se excluyen sólo si se declara."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from decimal import Decimal

from edgelab.crypto.binance_usdm import offtick_mask


def test_offtick_mask_marca_solo_lo_desalineado():
    v = np.array([100.0, 100.1, 100.15, 100.2], dtype=np.float64)
    m = offtick_mask(v, Decimal("0.10"))
    assert m.tolist() == [False, False, True, False]


def test_offtick_mask_no_aborta():
    """A diferencia de _prices_to_ticks, marca en vez de levantar."""
    v = np.array([1.005], dtype=np.float64)
    assert offtick_mask(v, Decimal("0.01")).tolist() == [True]


def test_offtick_mask_tolera_ruido_de_punto_flotante():
    v = np.array([70344.8, 69856.9], dtype=np.float64)
    assert not offtick_mask(v, Decimal("0.10")).any()


@pytest.mark.parametrize("tick,precio,esperado", [
    ("0.10", 70344.83, True),
    ("0.01", 70344.83, False),
    ("0.10", 70344.80, False),
])
def test_offtick_depende_del_tick_declarado(tick, precio, esperado):
    """El mismo precio esta dentro o fuera segun el tick_size: por eso el tick
    es argumento obligatorio y no se infiere del dato."""
    assert bool(offtick_mask(np.array([precio]), Decimal(tick))[0]) is esperado


def test_modo_diagnostico_excluye_cuenta_y_marca(tmp_path):
    """Con el flag: no aborta, pero deja rastro imborrable en el reporte."""
    from tests.bridge.test_binance_usdm import _write_pair, _contract
    from edgelab.crypto.binance_usdm import load_binance_usdm_pair

    tp, bp = _write_pair(tmp_path)
    trades = pd.read_csv(tp, header=None)
    trades.iloc[0, 1] = 100.15
    trades.to_csv(tp, index=False, header=False)

    out = load_binance_usdm_pair(tp, bp, _contract(), allow_offtick_prices=True)
    assert out.report.n_offtick_prices_excluded == 1
    assert out.report.offtick_exclusion_invoked is True
    assert out.report.offtick_price_sample[0]["price"] == pytest.approx(100.15)
    assert out.report.outcomes_opened is False


def test_sin_offtick_el_flag_no_marca_nada(tmp_path):
    """El flag encendido sobre datos limpios no debe marcar la corrida."""
    from tests.bridge.test_binance_usdm import _write_pair, _contract
    from edgelab.crypto.binance_usdm import load_binance_usdm_pair

    tp, bp = _write_pair(tmp_path)
    out = load_binance_usdm_pair(tp, bp, _contract(), allow_offtick_prices=True)
    assert out.report.n_offtick_prices_excluded == 0
    assert out.report.offtick_exclusion_invoked is False
