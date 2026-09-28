# -*- coding: utf-8 -*-
"""Auditoría 051 §2: el extractor de features por minuto ante inversión de reloj intercalada, BBO vieja, libro
invalidado y huecos de minutos. Fixtures chicos y deterministas."""
import numpy as np
import pandas as pd

from edgelab.context.l2_gate import extract_minute_features

M = 60_000_000
BASE = 29_000_000 * M     # minuto arbitrario


def _stream(minutes, *, quote_every=True, invert_at=None, invalid_at=None):
    """Por minuto: (L2) libro de 1 nivel por lado; (L1) bid, ask y un trade. source_row intercalado y creciente.
    `invert_at`: en ese minuto la fila L2 va DESPUÉS de las L1 con reloj 30 s atrás (cada flujo sigue monótono por
    separado; la inversión sólo aparece al intercalar). `invalid_at`: una actualización a un nivel inexistente."""
    l2, l1 = [], []
    row = 0
    for i, m in enumerate(minutes):
        t = BASE + m * M
        if i == 0:
            l2 += [dict(side=0, operation=0, level=0, price_tick=101, size=5, source_row=row, ts_us=t),
                   dict(side=1, operation=0, level=0, price_tick=99, size=5, source_row=row + 1, ts_us=t)]
            row += 2
        l2_row = dict(side=0, operation=1, level=0, price_tick=101, size=6 + i % 3, ts_us=t + 1_000)
        if not (invert_at is not None and i == invert_at):
            l2.append(dict(l2_row, source_row=row)); row += 1
        if quote_every or i == 0:
            l1 += [dict(side=1, price_tick=99 + i % 2, size=3, source_row=row, ts_us=t + 2_000),
                   dict(side=0, price_tick=101 + i % 2, size=3, source_row=row + 1, ts_us=t + 3_000)]
            row += 2
        l1.append(dict(side=2, price_tick=101 + i % 2, size=1, source_row=row, ts_us=t + 4_000)); row += 1
        if invert_at is not None and i == invert_at:
            l2.append(dict(l2_row, source_row=row, ts_us=t - 30 * 1_000_000)); row += 1
        if invalid_at is not None and i == invalid_at:
            l2.append(dict(side=0, operation=1, level=7, price_tick=150, size=1, source_row=row, ts_us=t + 5_000)); row += 1
    return pd.DataFrame(l2), pd.DataFrame(l1)


def test_interleaved_clock_inversion_marks_minute_ineligible():
    l2, l1 = _stream(range(30), invert_at=20)
    f, diag = extract_minute_features(l2, l1, session="s", min_ready_levels=1)
    assert diag["clock_inversions_interleaved"] == 1
    bad = f[f["clock_inversions"] > 0]
    assert len(bad) == 1 and not bool(bad["feature_eligible"].iloc[0])


def test_stale_bbo_trades_fall_back_and_old_bbo_makes_minute_ineligible():
    l2, l1 = _stream(range(30), quote_every=False)      # sólo hay cotización en el primer minuto
    f, diag = extract_minute_features(l2, l1, session="s", min_ready_levels=1)
    assert diag["stale_bbo_trades"] > 0
    late = f[f["minute_id"] >= f["minute_id"].min() + 2]
    assert late["mid_tick_close"].isna().all()          # BBO de más de 60 s: sin mid, sin spread
    assert not late["feature_eligible"].any()


def test_time_windows_do_not_cross_gaps():
    minutes = list(range(0, 20)) + list(range(40, 60))
    l2, l1 = _stream(minutes)
    f, _ = extract_minute_features(l2, l1, session="s", min_ready_levels=1)
    first_after_gap = f[f["minute_id"] == f["minute_id"].min() + 40]
    assert first_after_gap["mid_return_ticks"].isna().all()       # el retorno que cruza el hueco no existe
    within10 = f[(f["minute_id"] >= f["minute_id"].min() + 40) & (f["minute_id"] < f["minute_id"].min() + 50)]
    assert within10["efficiency_ratio_10m"].isna().all()          # ventana de 10 que cruzaría el hueco


def test_book_invalid_event_marks_its_minute_ineligible():
    l2, l1 = _stream(range(30), invalid_at=25)
    f, diag = extract_minute_features(l2, l1, session="s", min_ready_levels=1)
    assert diag["book_invalid_events"] > 0
    assert not f[f["book_invalid_events_minute"] > 0]["feature_eligible"].any()
