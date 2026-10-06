"""run_full_fast debe dar EXACTAMENTE lo mismo que run_full (zonas, eventos, bloques, dashboard).

La equivalencia sobre datos reales (MNQ 12-26 completo, 50t y 200t, 6 configuraciones) y la paridad NT8 (50t 934/934,
200t 338/338) están en docs/research/AVCL_OPTIMIZACION_20261006.md. Este test fija la equivalencia con ticks sintéticos
deterministas para que una modificación futura de cualquiera de las dos versiones no las separe en silencio."""
import numpy as np
import pytest

from edgelab.bridge import bars as B
from edgelab.bridge import ticks as T
from edgelab.bridge.indicators.avolclusterpoi_fast import run_full_fast
from edgelab.bridge.indicators.avolclusterpoi_full import run_full


def _ticks(seed=7, days=10, per_day=8000):
    rng = np.random.default_rng(seed)
    ts, px = [], []
    base = np.datetime64("2026-03-02T00:00:00", "ns").astype(np.int64)    # lunes; sesiones CME completas
    p = 80000
    for d in range(days):
        day0 = base + d * 86_400_000_000_000
        t = np.sort(rng.integers(0, 86_400_000_000_000, per_day)) + day0
        steps = rng.choice([-2, -1, 0, 0, 0, 1, 2], per_day)
        lvl = p + np.cumsum(steps)
        p = int(lvl[-1])
        ts.append(t); px.append(lvl)
    ts = np.concatenate(ts); px = np.concatenate(px)
    vol = rng.choice([1, 1, 1, 2, 3, 8, 20], len(ts)).astype(np.int64)
    return T.TickSeries(ts_ns=ts, price_ticks=px.astype(np.int64), volume=vol, bid_ticks=None, ask_ticks=None,
                        sequence=np.arange(len(ts), dtype=np.int64), tick_size=0.25, instrument="MNQ", contract="TEST")


PARAMS = [
    dict(detection_percentile=95.0, invalidation_mode="None", max_age_bars=500, lookback_sessions=5, min_samples_per_bucket=2, time_bucket_minutes=240),
    dict(lookback_sessions=5, min_samples_per_bucket=2, time_bucket_minutes=240),
    dict(detection_percentile=80.0, window_bars=5, use_topk_hot_cells=True, max_touches=3, invalidation_mode="FirstTouch",
         lookback_sessions=2, min_samples_per_bucket=2),
    dict(detection_percentile=70.0, median_multiplier=1.5, min_cluster_ticks=3, max_gap_ticks=2, use_session_buckets=False,
         lookback_sessions=3, min_samples_per_bucket=2, enable_predictive_filter=True),
]


@pytest.mark.parametrize("n", [20, 40])
@pytest.mark.parametrize("params", PARAMS)
def test_fast_equals_full(n, params):
    tk = _ticks()
    bars = B.build_tick_bars(tk, n)
    fp = B.build_total_footprint_csr_nt8(tk, bars)
    a = run_full(tk, bars, fp, params)
    b = run_full_fast(tk, bars, fp, params)
    assert len(a["zones"]) > 0
    assert a["zones"] == b["zones"]
    assert a["events"] == b["events"]
    assert a["blocks"] == b["blocks"]
    assert a["dashboard"] == b["dashboard"]


def test_ohlc_vectorizado_igual_al_bucle():
    tk = _ticks(seed=3, days=3)
    bars = B.build_tick_bars(tk, 37)
    st = np.searchsorted(np.arange(len(tk.ts_ns)), np.flatnonzero(np.r_[True, np.diff(bars.tick_bar_idx) != 0]))
    for b in range(0, len(bars.close_t), 97):
        sel = bars.tick_bar_idx == b
        p = tk.price_ticks[sel]
        assert (bars.open_t[b], bars.high_t[b], bars.low_t[b], bars.close_t[b]) == (p[0], p.max(), p.min(), p[-1])
        assert bars.volume[b] == tk.volume[sel].sum()
    assert (bars.tick_bar_idx >= 0).all() and len(st) == len(bars.close_t)
