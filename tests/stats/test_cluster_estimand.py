from __future__ import annotations

import pytest

from edgelab.stats.cluster_estimand import (
    ClusterEstimandError,
    SessionAggregate,
    aggregate_sessions,
    percentile_interval,
    resample_session_clusters,
    trade_weighted_expectancy,
)


def test_estimando_es_trade_weighted_no_media_de_dias():
    rows = (
        SessionAggregate("d1", pnl_net=100.0, n_trades=100),
        SessionAggregate("d2", pnl_net=-9.0, n_trades=1),
    )
    assert trade_weighted_expectancy(rows) == pytest.approx(91 / 101)
    assert trade_weighted_expectancy(rows) != pytest.approx((1.0 - 9.0) / 2)


def test_agregacion_preserva_sesiones_sin_trades():
    rows = aggregate_sessions(
        ["d1", "d2", "d3"],
        {"d1": [1.0, -0.5], "d3": [2.0]},
    )
    assert rows[1] == SessionAggregate("d2", 0.0, 0)
    assert trade_weighted_expectancy(rows) == pytest.approx(2.5 / 3)


def test_trades_fuera_del_calendario_fallan_cerrado():
    with pytest.raises(ClusterEstimandError, match="fuera del calendario"):
        aggregate_sessions(["d1"], {"d2": [1.0]})


def test_cluster_invalido_no_permite_pnl_sin_trades():
    with pytest.raises(ClusterEstimandError, match="sin trades"):
        SessionAggregate("d1", 1.0, 0)


def test_cero_trades_hace_estimando_indefinido():
    with pytest.raises(ClusterEstimandError, match="cero trades"):
        trade_weighted_expectancy([SessionAggregate("d1", 0.0, 0)])


def test_bootstrap_es_reproducible_y_recalcula_ratio():
    rows = (
        SessionAggregate("d1", 100.0, 100),
        SessionAggregate("d2", -9.0, 1),
        SessionAggregate("d3", 0.0, 0),
    )
    a = resample_session_clusters(rows, n_replicates=50, seed=42)
    b = resample_session_clusters(rows, n_replicates=50, seed=42)
    assert a == b
    assert a.observed == pytest.approx(91 / 101)
    allowed = {1.0, -9.0, 91 / 101, 191 / 201, 41 / 51}
    assert all(any(x == pytest.approx(y) for y in allowed) for x in a.replicates)


def test_replica_sin_denominador_se_registra_no_se_inventa():
    rows = (
        SessionAggregate("active", 1.0, 1),
        SessionAggregate("zero1", 0.0, 0),
        SessionAggregate("zero2", 0.0, 0),
    )
    result = resample_session_clusters(rows, n_replicates=500, seed=7)
    assert result.invalid_zero_denominator > 0
    assert len(result.replicates) + result.invalid_zero_denominator == 500


def test_bootstrap_no_acepta_universo_totalmente_inactivo():
    rows = (SessionAggregate("d1", 0.0, 0), SessionAggregate("d2", 0.0, 0))
    with pytest.raises(ClusterEstimandError, match="cero trades"):
        resample_session_clusters(rows, n_replicates=10, seed=1)


def test_intervalo_percentil_es_diagnostico_determinista():
    rows = (
        SessionAggregate("d1", 1.0, 1),
        SessionAggregate("d2", 2.0, 1),
        SessionAggregate("d3", 3.0, 1),
    )
    result = resample_session_clusters(rows, n_replicates=200, seed=9)
    lo, hi = percentile_interval(result)
    assert lo <= result.observed <= hi


def test_inputs_booleanos_no_pasan_por_enteros():
    with pytest.raises(ClusterEstimandError):
        SessionAggregate("d", 0.0, True)
    with pytest.raises(ClusterEstimandError):
        SessionAggregate("d", True, 1)
    with pytest.raises(ClusterEstimandError):
        aggregate_sessions(["d"], {"d": [True]})
    with pytest.raises(ClusterEstimandError):
        resample_session_clusters([SessionAggregate("d", 1.0, 1)],
                                  n_replicates=True, seed=1)


def test_string_no_se_interpreta_como_calendario_de_caracteres():
    with pytest.raises(ClusterEstimandError, match="secuencia"):
        aggregate_sessions("d1", {})
