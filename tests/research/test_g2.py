"""Pruebas de la fachada canónica G2 con verdad conocida."""
import math

import pytest

from edgelab.research import g2
from edgelab.research.g2_dsr import DSR_METHOD_SHA256_V2
from edgelab.research.g2_ratio import RatioCell
from edgelab.stats.cluster_estimand import (
    aggregate_sessions,
    studentized_stationary_interval,
)


def _noise(n, seed=7, amplitude=1.0):
    generator = g2._lcg(seed)
    return [
        amplitude * (((next(generator) >> 8) % 2001) - 1000) / 1000.0
        for _ in range(n)
    ]


def test_concentration_is_diagnostic_and_reproducible():
    returns = _noise(400)
    sessions = ["s%03d" % (index // 20) for index in range(400)]
    first = g2.temporal_concentration_test(
        returns, sessions, n_perm=1000, seed=42
    )
    second = g2.temporal_concentration_test(
        returns, sessions, n_perm=1000, seed=42
    )
    assert first == second
    assert first[0] > 0.05
    with pytest.raises(ValueError):
        g2.temporal_concentration_test(returns, sessions, n_perm=999)


def test_concentration_detects_placement_not_presence():
    concentrated = []
    sessions = []
    for session in range(20):
        for _ in range(20):
            concentrated.append(1.0 if session < 10 else -1.0)
            sessions.append("s%03d" % session)
    p_value, observed = g2.temporal_concentration_test(
        concentrated, sessions, n_perm=1000
    )
    assert p_value <= 0.05 and observed > 0

    stable = [1.0 + value / 4.0 for value in _noise(200, seed=11)]
    stable_sessions = ["s%03d" % index for index in range(200)]
    p_value, _ = g2.temporal_concentration_test(
        stable, stable_sessions, n_perm=1000
    )
    assert p_value > 0.30


def test_campaign_null_is_the_hard_gate_reduction():
    p_value, observed = g2.campaign_null_pvalue(1.0, [0.0] * 1000)
    assert p_value == pytest.approx(1 / 1001)
    assert observed == 1.0


def test_pbo_requires_trade_counts_and_ranks_ratio():
    matrix = [
        (RatioCell(100, 100), RatioCell(2, 1))
        for _ in range(16)
    ]
    result = g2.pbo_cscv(matrix)
    assert result.pbo == 0.0
    assert result.n_splits == math.comb(8, 4) == 70
    assert set(result.selected_configs) == {1}
    with pytest.raises(Exception):
        g2.pbo_cscv([[1.0, 2.0] for _ in range(8)])


def test_dsr_scalar_compatibility_and_method_identity():
    base = dict(n_obs=500, skew=0.0, kurtosis=3.0)
    single = g2.deflated_sharpe(0.1, n_trials=1, **base)
    many = g2.deflated_sharpe(0.1, n_trials=48, **base)
    more = g2.deflated_sharpe(0.1, n_trials=1000, **base)
    assert single > many > more
    assert g2.dsr_method_sha256() == DSR_METHOD_SHA256_V2


def test_walk_forward_requires_ratio_cells():
    folds = ("f1", "f2", "f3", "f4")
    per_fold = {
        "frequent": {fold: RatioCell(100, 100) for fold in folds},
        "better": {fold: RatioCell(2, 1) for fold in folds},
    }
    result = g2.walk_forward(per_fold, folds)
    assert result.observed == 2.0
    assert all(
        selection.selected_config == "better"
        for selection in result.selections
    )


def test_parameter_sensitivity_detects_cliff_and_plateau():
    cliff = {"winner": 5.0, "a": -1.0, "b": -2.0, "c": -0.5}
    median, positives, count = g2.parameter_sensitivity(
        cliff, "winner", ["a", "b", "c"]
    )
    assert median < 0 and positives == 0 and count == 3
    plateau = {"winner": 5.0, "a": 4.0, "b": 3.5, "c": 4.2}
    median, positives, _ = g2.parameter_sensitivity(
        plateau, "winner", ["a", "b", "c"]
    )
    assert median > 0 and positives == 3


def test_stable_edge_passes_primary_ci_not_concentration_gate():
    trades = {}
    for session in range(200):
        total = 0.5 + (((session * 2654435761) % 3000) - 1500) / 1000.0
        trades["s%03d" % session] = (total / 2 + 0.1, total / 2 - 0.1)
    calendar = sorted(trades)
    returns = [value for session in calendar for value in trades[session]]
    session_ids = [session for session in calendar for _ in trades[session]]
    p_value, _ = g2.temporal_concentration_test(
        returns, session_ids, n_perm=1000
    )
    interval = studentized_stationary_interval(
        aggregate_sessions(calendar, trades),
        n_replicates=2000,
        seed=20260810,
        confidence=0.95,
    )
    assert p_value > 0.30
    assert interval.lower > 0
