# -*- coding: utf-8 -*-
"""Parity tests derived directly from nt8/aVolClusterPOI.cs v0.5."""
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from edgelab.bridge.indicators.avolclusterpoi import (
    NS,
    SessionProfile,
    empirical_quantile,
    median_upper,
    session_relative_bucket,
)


def test_empirical_quantile_and_upper_median_match_cs_contract():
    assert median_upper([1, 2, 3, 4]) == 3
    assert empirical_quantile([1, 2, 3, 4], 0.50) == 2
    assert empirical_quantile([1, 2, 3, 4], 0.98) == 4


def test_first_complete_session_is_retained():
    p = SessionProfile(lookback_sessions=20)
    for x in (10, 20, 30):
        p.add_block(7, x)
    p.commit()
    assert p.history_session_count(7) == 1
    assert p.history_scores(7) == [10.0, 20.0, 30.0]


def test_lookback_is_sessions_not_scores():
    p = SessionProfile(lookback_sessions=2)
    for session in range(3):
        for block in range(3):
            p.add_block(7, 100 * session + block)
        p.commit()
    # C# retains the last 2 complete sessions = 6 scores, not the last 2 scores.
    assert p.history_session_count(7) == 2
    assert p.history_scores(7) == [100.0, 101.0, 102.0, 200.0, 201.0, 202.0]


def test_bucket_anchor_is_close_minus_one_second():
    start = 1_000 * NS
    minute = 60 * NS
    # Three disjoint ten-minute blocks all belong to bucket 0 in the C#.
    assert session_relative_bucket(start + 10 * minute, start, 30) == 0
    assert session_relative_bucket(start + 20 * minute, start, 30) == 0
    assert session_relative_bucket(start + 30 * minute, start, 30) == 0
    # The next block is bucket 1.
    assert session_relative_bucket(start + 40 * minute, start, 30) == 1


def test_absent_bucket_still_ages_by_global_session():
    p = SessionProfile(lookback_sessions=1)
    p.add_block(0, 1); p.add_block(1, 10); p.commit()  # session 0
    p.add_block(0, 2); p.commit()                       # session 1; bucket 1 absent
    assert p.history_scores(0) == [2.0]
    # C# prunes bucket 1 using minSession=1 although it got no new sample.
    assert p.history_scores(1) == []


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print("PASS", test.__name__)
    print("TODOS LOS TESTS DE PARIDAD PASARON")
