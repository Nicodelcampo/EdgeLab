"""Semántica de barras [inicio, fin): sin pérdida de ticks, gaps -> barra
vacía, conservación de primer/último tick y tick_count. Infra sintética
(NO EURUSD)."""
import numpy as np
import pandas as pd


def _bars():
    base = np.int64(1_700_000_000_000_000_000)
    # ticks cada 200ms con un gap: falta la ventana [4s, 5s)
    ms = np.concatenate([np.arange(0, 4000, 200), np.arange(5000, 7000, 200)]).astype(np.int64)
    ts = base + ms * 1_000_000
    price = 100 + np.arange(len(ts), dtype=np.int64)
    bar_ns = np.int64(1_000_000_000)  # 1s
    bin_id = (ts - base) // bar_ns     # floor -> [inicio, fin)
    df = pd.DataFrame({"bin": bin_id, "price": price})
    g = df.groupby("bin")
    return ts, price, bin_id, g


def test_no_tick_loss_and_counts():
    ts, price, bin_id, g = _bars()
    counts = g.size()
    assert int(counts.sum()) == len(ts)  # ningún tick perdido


def test_first_last_tick_preserved():
    ts, price, bin_id, g = _bars()
    first, last = g["price"].first(), g["price"].last()
    assert int(first.iloc[0]) == 100
    assert int(last.iloc[-1]) == int(price[-1])


def test_gap_produces_empty_bar():
    ts, price, bin_id, g = _bars()
    present = set(g.size().index.tolist())
    full = set(range(int(bin_id.min()), int(bin_id.max()) + 1))
    empty = full - present
    assert 4 in empty  # la ventana [4s,5s) quedó sin ticks
