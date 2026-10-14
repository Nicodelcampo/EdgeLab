"""Canal de lado informado por el venue: aditivo, con precedencia sobre la inferencia."""
from __future__ import annotations

import numpy as np

from edgelab.bridge.bars import build_footprints, build_tick_bars
from edgelab.bridge.ticks import TickSeries


def _ticks(side=None, bid=None, ask=None, n=6):
    return TickSeries(
        ts_ns=np.arange(n, dtype=np.int64) * 1_000_000_000,
        price_ticks=np.full(n, 100, dtype=np.int64),
        volume=np.ones(n, dtype=np.float64),
        bid_ticks=(np.full(n, 99, dtype=np.int64) if bid is None else bid),
        ask_ticks=(np.full(n, 101, dtype=np.int64) if ask is None else ask),
        sequence=np.arange(n, dtype=np.int64),
        tick_size=0.1,
        aggressor_side=side)


def test_sin_canal_el_comportamiento_no_cambia():
    """Aditivo: si la fuente no informa lado, nada se altera."""
    t = _ticks()
    fps = build_footprints(t, build_tick_bars(t, 3, reiniciar_por_sesion=False))
    assert int(fps.n_exchange.sum()) == 0
    assert int(fps.n_quote.sum()) + int(fps.n_rule.sum()) == len(t)


def test_el_lado_del_venue_tiene_precedencia_sobre_el_quote():
    """Precio 100 esta entre bid 99 y ask 101: el quote no clasificaria.
    Con lado del venue, los 6 quedan clasificados sin inferencia."""
    t = _ticks(side=np.array([1, -1, 1, -1, 1, -1], dtype=np.int64))
    fps = build_footprints(t, build_tick_bars(t, 3, reiniciar_por_sesion=False))
    assert int(fps.n_exchange.sum()) == 6
    assert int(fps.n_quote.sum()) == 0
    assert int(fps.n_rule.sum()) == 0


def test_el_venue_gana_incluso_cuando_el_quote_diria_otra_cosa():
    """Precio en el ask => el quote diria compra. El venue dice venta y manda."""
    n = 4
    t = TickSeries(
        ts_ns=np.arange(n, dtype=np.int64) * 1_000_000_000,
        price_ticks=np.full(n, 101, dtype=np.int64),      # en el ask
        volume=np.ones(n, dtype=np.float64),
        bid_ticks=np.full(n, 99, dtype=np.int64),
        ask_ticks=np.full(n, 101, dtype=np.int64),
        sequence=np.arange(n, dtype=np.int64), tick_size=0.1,
        aggressor_side=np.full(n, -1, dtype=np.int64))     # venue: venta
    fps = build_footprints(t, build_tick_bars(t, 4, reiniciar_por_sesion=False))
    assert int(fps.n_exchange.sum()) == 4
    assert sum(fps.bid[0].values()) == 4.0, "todo el volumen va al lado vendedor"
    assert sum(fps.ask[0].values()) == 0.0


def test_lado_cero_cae_a_la_inferencia_y_no_se_cuenta_como_venue():
    t = _ticks(side=np.zeros(6, dtype=np.int64))
    fps = build_footprints(t, build_tick_bars(t, 3, reiniciar_por_sesion=False))
    assert int(fps.n_exchange.sum()) == 0


def test_sin_book_pero_con_lado_del_venue_clasifica_igual():
    """El caso que da disponibilidad a crypto: trades sin bookTicker."""
    n = 6
    t = TickSeries(
        ts_ns=np.arange(n, dtype=np.int64) * 1_000_000_000,
        price_ticks=np.full(n, 100, dtype=np.int64),
        volume=np.ones(n, dtype=np.float64),
        bid_ticks=np.zeros(n, dtype=np.int64),   # sin book
        ask_ticks=np.zeros(n, dtype=np.int64),
        sequence=np.arange(n, dtype=np.int64), tick_size=0.1,
        aggressor_side=np.array([1, 1, -1, -1, 1, -1], dtype=np.int64))
    fps = build_footprints(t, build_tick_bars(t, 6, reiniciar_por_sesion=False))
    assert int(fps.n_exchange.sum()) == 6
    assert int(fps.n_rule.sum()) == 0, "no hace falta tick-rule si el venue informa"
    assert sum(fps.ask[0].values()) == 3.0
    assert sum(fps.bid[0].values()) == 3.0
