# -*- coding: utf-8 -*-
"""Tests para el cálculo de costos y fricciones multiactivo en edgelab.research.costs."""
import pytest
from edgelab.research.costs import (
    COMMISSIONS_PER_SIDE_USD,
    TICK_VALUES_USD,
    friccion_rt_ticks,
    friccion_rt_usd,
    get_scenario,
)


def test_escenarios_disponibles():
    for inst in ("6E", "ES", "NQ", "YM", "ZB"):
        sc_base = get_scenario("base", instrument=inst)
        assert sc_base.commission_per_side_usd == COMMISSIONS_PER_SIDE_USD[inst]
        assert sc_base.slip_entry == 1
        assert sc_base.slip_exit == 1


def test_friccion_rt_6e_exacta():
    # 6E: 2.40 USD / lado -> RT comision = 4.80 USD.
    # 1 tick = 6.25 USD -> 4.80 / 6.25 = 0.768 ticks.
    # Slippage base = 1 + 1 = 2 ticks -> total = 2.768 ticks.
    f_ticks = friccion_rt_ticks("base", instrument="6E")
    assert round(f_ticks, 4) == 2.7680
    f_usd = friccion_rt_usd("base", instrument="6E")
    assert round(f_usd, 2) == 17.30


def test_friccion_rt_es_exacta():
    # ES: 2.40 USD / lado -> RT comision = 4.80 USD.
    # 1 tick = 12.50 USD -> 4.80 / 12.50 = 0.384 ticks.
    # Slippage base = 2 ticks -> total = 2.384 ticks.
    f_ticks = friccion_rt_ticks("base", instrument="ES")
    assert round(f_ticks, 4) == 2.3840
    f_usd = friccion_rt_usd("base", instrument="ES")
    assert round(f_usd, 2) == 29.80


def test_friccion_rt_zb_exacta():
    # ZB: 2.40 USD / lado -> RT comision = 4.80 USD.
    # 1 tick = 31.25 USD -> 4.80 / 31.25 = 0.1536 ticks.
    # Slippage base = 2 ticks -> total = 2.1536 ticks.
    f_ticks = friccion_rt_ticks("base", instrument="ZB")
    assert round(f_ticks, 4) == 2.1536
    f_usd = friccion_rt_usd("base", instrument="ZB")
    assert round(f_usd, 2) == 67.30


def test_escenario_ideal_es_cero():
    for inst in ("6E", "ES", "ZB"):
        assert friccion_rt_ticks("ideal", instrument=inst) == 0.0
        assert friccion_rt_usd("ideal", instrument=inst) == 0.0
