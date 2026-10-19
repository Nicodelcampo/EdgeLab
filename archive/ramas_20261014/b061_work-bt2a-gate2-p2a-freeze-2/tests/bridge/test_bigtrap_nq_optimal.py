"""Unit tests for BigTrapNQ Optimal indicator."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from edgelab.bridge import bars as B
from edgelab.bridge.ticks import TickSeries
from edgelab.bridge.indicators import bigtrap_nq_optimal
from edgelab.bridge.indicators.bigtrap_nq_optimal import BigTrapNQOptimalConfig, detect_nq_zones, run_on_ticks

NS = 1_000_000_000


def test_bigtrap_nq_optimal_pipeline_runs():
    base_t = pd.to_datetime("2026-03-10 09:30:00").tz_localize("America/Chicago").value
    t0 = np.linspace(base_t, base_t + 50 * NS, 25, dtype=np.int64)
    p0 = np.full(25, 100, dtype=np.int64)

    # Barra 1: 25 ticks, compras masivas en 110 (Ask) con finished auction (sin bid en 110)
    t1 = np.linspace(base_t + 60 * NS, base_t + 110 * NS, 25, dtype=np.int64)
    p1 = np.concatenate([np.full(10, 100, dtype=np.int64), np.full(10, 110, dtype=np.int64), np.full(5, 100, dtype=np.int64)])
    v1 = np.concatenate([np.full(10, 1.0, dtype=np.float64), np.full(10, 10.0, dtype=np.float64), np.full(5, 1.0, dtype=np.float64)])

    ts = np.concatenate([t0, t1])
    px = np.concatenate([p0, p1])
    vol = np.concatenate([np.full(25, 1.0, dtype=np.float64), v1])
    bids = (px - 1).copy()
    asks = px.copy()

    tk = TickSeries(ts, px, vol, bids, asks, np.arange(len(ts), dtype=np.int64), 0.25, "NQ", "NQ_SYN", "test")
    cfg = BigTrapNQOptimalConfig(min_trap_volume=50.0, ticks_per_bar=25)
    res = run_on_ticks(tk, config=cfg, chart_tz="America/Chicago")

    assert res["indicator"] == "BigTrapNQ_Optimal"
    assert res["total_zones"] == 1
    z = res["zones"][0]
    assert z["kind"] == "trapped_buyers"
    assert z["side"] == "SHORT"
    assert z["vol"] == 100.0
    assert z["top"] > (110 * 0.25)
