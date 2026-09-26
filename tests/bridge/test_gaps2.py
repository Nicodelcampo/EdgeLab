"""Smoke sintético determinista de Gaps2 (F4A). Valida infraestructura, NO
paridad real con NT8 (esa exige un EventLogPath real, gate P2)."""
import numpy as np

from edgelab.bridge import bars as B
from edgelab.bridge.indicators import gaps2
from edgelab.bridge.ticks import TickSeries, make_synthetic

NS = 1_000_000_000


def _mk(ts, px, vol):
    n = len(ts)
    return TickSeries(np.asarray(ts, np.int64), np.asarray(px, np.int64),
                      np.asarray(vol, np.float64), None, None,
                      np.arange(n, dtype=np.int64), 0.25, "SYN", "SYN", "test")


def test_gap_detection_and_fill_lifecycle():
    base = 1000 * 60 * NS
    # tick1->tick2 salta 6 ticks (gap bull); después el precio vuelve y lo llena
    ts = [base + i * NS for i in range(8)]
    px = [100, 106, 106, 105, 103, 100, 97, 97]
    tk = _mk(ts, px, [1] * 8)
    bars = B.build_time_bars(tk, minutes=1)
    res = gaps2.run(tk, bars, params=dict(min_gap_ticks=5, export_floor_ticks=2,
                                          reversal_confirm_ticks=2,
                                          vol_baseline_ticks=10, min_vol_baseline_samples=1))
    zones = res["zones"]
    assert zones, "el salto de 6 ticks debe crear una zona"
    z = zones[0]
    assert z["kind"] == "bull_gap" and z["size_ticks"] == 6
    assert z["top"] == 106 * 0.25 and z["bottom"] == 100 * 0.25
    # el precio cruzó hasta 97 (< bottom - 2 ticks) -> INVALIDATED por inverse
    assert z["state"] == "INVALIDATED" and z["end_reason"] == "inverse"
    types = [e["type"] for e in res["events"]]
    assert "ZONE_CREATED" in types and "ZONE_INVALIDATED" in types


def test_creation_tick_does_not_touch_own_gap():
    base = 1000 * 60 * NS
    ts = [base, base + NS, base + 2 * NS]
    px = [100, 108, 108]
    res = gaps2.run(_mk(ts, px, [1, 1, 1]), B.build_time_bars(_mk(ts, px, [1] * 3), minutes=1),
                    params=dict(export_floor_ticks=2))
    z = res["zones"][0]
    assert z["touches"] == 0 and z["state"] in ("VIRGIN",)


def test_deterministic_on_synthetic():
    tk = make_synthetic(n_sessions=1, ticks_per_session=4000)
    bars = B.build_time_bars(tk, minutes=1)
    r1 = gaps2.run(tk, bars, params=dict(min_gap_ticks=3))
    r2 = gaps2.run(tk, bars, params=dict(min_gap_ticks=3))
    assert r1["csv_lines"] == r2["csv_lines"]          # determinismo bit a bit
    assert len(r1["zones"]) > 0
    seqs = [e["seq"] for e in r1["events"]]
    assert seqs == sorted(seqs)                         # orden de eventos estable


def test_param_change_changes_zones():
    tk = make_synthetic(n_sessions=1, ticks_per_session=4000)
    bars = B.build_time_bars(tk, minutes=1)
    loose = gaps2.run(tk, bars, params=dict(export_floor_ticks=2))
    tight = gaps2.run(tk, bars, params=dict(export_floor_ticks=6))
    assert len(loose["zones"]) > len(tight["zones"])    # el grid paramétrico discrimina
