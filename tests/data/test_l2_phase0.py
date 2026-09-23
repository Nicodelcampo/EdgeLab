"""Fase 0 L2: reconstruccion con pseudo-eventos, costos de barrido y reloj de cambios de mid."""
import math

import numpy as np

from edgelab.research.l2_phase0 import (ASK, BID, BOOTSTRAP_S, apply_event, block_table, defect_reasons,
                                        process_session, sweep_cost_ticks, time_to_k_changes)


def test_sweep_cost_walks_levels_and_reports_insufficient_depth():
    asks = [[101, 1], [102, 3]]
    # mid = (99 + 101) / 2 = 100 -> mid2 = 200
    assert sweep_cost_ticks(asks, 200, 1, ASK) == 1.0
    assert sweep_cost_ticks(asks, 200, 2, ASK) == 1.5          # (101 + 102)/2 - 100
    assert math.isnan(sweep_cost_ticks(asks, 200, 5, ASK))
    bids = [[99, 2]]
    assert sweep_cost_ticks(bids, 200, 2, BID) == 1.0


def test_apply_event_rejects_out_of_range_levels():
    b = []
    assert apply_event(b, 0, 0, 100, 5) and b == [[100, 5]]
    assert not apply_event(b, 2, 3, 100, 0)
    assert not apply_event(b, 1, 1, 100, 5)


def test_time_to_k_changes():
    ch = np.array([10, 20, 30], dtype=np.int64) * 1_000_000
    out = time_to_k_changes(np.array([0, 15_000_000]), ch, 2)
    assert list(out) == [20.0, 15.0]
    assert np.isnan(time_to_k_changes(np.array([25_000_000]), ch, 2)[0])


def _session(extra_seconds=120):
    """Libro de 10 niveles por lado armado en t=0, luego un cambio de mid por segundo y un trade al ask."""
    rows, r = [], 0
    for lvl in range(10):
        rows.append((ASK, 0, lvl, 101 + lvl, 5, 0, r)); r += 1
        rows.append((BID, 0, lvl, 99 - lvl, 5, 0, r)); r += 1
    for s in range(1, extra_seconds + 1):
        t = s * 1_000_000
        # dos filas del mismo pseudo-evento: el mid solo se lee al cierre del grupo
        rows.append((ASK, 1, 0, 101, 5 + s % 2, t, r)); r += 1
        rows.append((ASK, 1, 1, 102, 5, t, r)); r += 1
    l2 = {k: np.array([x[i] for x in rows]) for i, k in
          enumerate(("side", "operation", "level", "price_tick", "size", "ts_us", "source_row"))}
    l1 = dict(side=np.array([2]), price_tick=np.array([101]), size=np.array([3]),
              ts_us=np.array([(BOOTSTRAP_S + 5) * 1_000_000]), source_row=np.array([r + 100]))
    return l2, l1


def test_process_session_bootstrap_groups_and_qa():
    l2, l1 = _session()
    res = process_session(l2, l1)
    assert res.qa["invalid_events"] == 0 and res.qa["clock_inversions"] == 0
    assert res.qa["groups"] == 1 + 120                            # bootstrap en t=0 + 120 grupos de 2 filas
    assert res.snaps["t"].min() >= BOOTSTRAP_S * 1_000_000         # nada antes de cerrar el bootstrap
    assert set(res.snaps["ask"] - res.snaps["bid"]) == {2}
    rows = block_table(res, instrument="GC", contract="GC 08-26", session="20260615")
    assert rows and rows[0]["sweep1_p50"] == 1.0 and rows[0]["spread_1tick_share"] == 0.0
    assert defect_reasons(res.qa) == [f"FEW_SNAPSHOTS={res.qa['snapshots']}"]
