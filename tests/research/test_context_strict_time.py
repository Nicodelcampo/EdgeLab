from __future__ import annotations

import pandas as pd

from edgelab.context import attach_context_at_event_time


def _context(at: str) -> pd.DataFrame:
    return pd.DataFrame({
        "instrument": ["GC"],
        "contract": ["GC 06-26"],
        "cme_session": ["20260324"],
        "data_window_end": [at],
        "feature_available_at": [at],
        "context_state": ["normal"],
        "context_model_id": ["gate_gc_l1_hmm3_forward_v0"],
        "context_run_id": ["run-1"],
    })


def _event(at: str) -> pd.DataFrame:
    return pd.DataFrame({
        "event_id": ["e0"],
        "instrument": ["GC"],
        "contract": ["GC 06-26"],
        "cme_session": ["20260324"],
        "event_time": [at],
    })


def test_pandas3_no_degrada_epoch_ns_a_microsegundos():
    out = attach_context_at_event_time(
        _event("2026-03-24T14:02:00Z"),
        _context("2026-03-24T14:00:00Z"),
    )
    assert not out.frame.loc[0, "context_as_of_ok"]
    assert out.frame.loc[0, "context_fail_reason"] == "STALE_CONTEXT"


def test_mismo_timestamp_sin_sequence_es_ambiguo_y_falla_cerrado():
    out = attach_context_at_event_time(
        _event("2026-03-24T14:00:00Z"),
        _context("2026-03-24T14:00:00Z"),
    )
    assert not out.frame.loc[0, "context_as_of_ok"]
    assert out.frame.loc[0, "context_fail_reason"] == "NO_STRICT_PRIOR_CONTEXT"
