from __future__ import annotations

import pytest

from edgelab.stats.cluster_estimand import (
    ClusterEstimandError, SessionAggregate, aggregate_sessions,
    percentile_interval, ratio_influence_series, resample_session_clusters,
    resample_stationary_session_clusters, ratio_hac_standard_error,
    stationary_block_length, studentized_stationary_interval,
    trade_weighted_expectancy,
)


def test_estimando_es_trade_weighted_no_media_de_dias():
    rows = (SessionAggregate("d1", 100.0, 100), SessionAggregate("d2", -9.0, 1))
    assert trade_weighted_expectancy(rows) == pytest.approx(91 / 101)
    assert trade_weighted_expectancy(rows) != pytest.approx(-4.0)


def test_agregacion_preserva_sesiones_sin_trades():
    rows = aggregate_sessions(["d1", "d2", "d3"],
                              {"d1": [1.0, -0.5], "d3": [2.0]})
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
    rows = (SessionAggregate("d1", 100.0, 100),
            SessionAggregate("d2", -9.0, 1), SessionAggregate("d3", 0.0, 0))
    a = resample_session_clusters(rows, n_replicates=50, seed=42)
    assert a == resample_session_clusters(rows, n_replicates=50, seed=42)
    allowed = {1.0, -9.0, 91/101, 191/201, 41/51}
    assert all(any(x == pytest.approx(y) for y in allowed) for x in a.replicates)


def test_replica_sin_denominador_se_registra_no_se_inventa():
    rows = (SessionAggregate("active", 1.0, 1),
            SessionAggregate("zero1", 0.0, 0), SessionAggregate("zero2", 0.0, 0))
    result = resample_session_clusters(rows, n_replicates=500, seed=7)
    assert result.invalid_zero_denominator > 0
    assert len(result.replicates) + result.invalid_zero_denominator == 500


def test_bootstrap_no_acepta_universo_totalmente_inactivo():
    with pytest.raises(ClusterEstimandError, match="cero trades"):
        resample_session_clusters((SessionAggregate("d1", 0.0, 0),),
                                  n_replicates=10, seed=1)


def test_intervalo_percentil_es_diagnostico_determinista():
    rows = tuple(SessionAggregate("d%d" % i, float(i), 1) for i in range(1, 4))
    result = resample_session_clusters(rows, n_replicates=200, seed=9)
    lo, hi = percentile_interval(result)
    assert lo <= result.observed <= hi


def test_inputs_booleanos_no_pasan_por_enteros():
    with pytest.raises(ClusterEstimandError): SessionAggregate("d", 0.0, True)
    with pytest.raises(ClusterEstimandError): SessionAggregate("d", True, 1)
    with pytest.raises(ClusterEstimandError): aggregate_sessions(["d"], {"d": [True]})
    with pytest.raises(ClusterEstimandError):
        resample_session_clusters([SessionAggregate("d", 1.0, 1)],
                                  n_replicates=True, seed=1)


def test_string_no_se_interpreta_como_calendario_de_caracteres():
    with pytest.raises(ClusterEstimandError, match="secuencia"):
        aggregate_sessions("d1", {})


def test_influencia_del_ratio_suma_cero_en_la_muestra():
    rows = (SessionAggregate("d1", 10.0, 10), SessionAggregate("d2", -2.0, 1),
            SessionAggregate("d3", 0.0, 0))
    psi = ratio_influence_series(rows)
    assert sum(psi) == pytest.approx(0.0)


def test_stationary_remuestrea_pares_y_es_reproducible():
    rows = tuple(SessionAggregate("d%d" % i, float(i-4), 1+i%3) for i in range(1,10))
    a = resample_stationary_session_clusters(rows, n_replicates=100,
                                             seed=77, block_length=3)
    assert a == resample_stationary_session_clusters(
        rows, n_replicates=100, seed=77, block_length=3)
    assert a.method == "stationary_session_clusters" and a.block_length == 3


def test_block_length_auto_usa_influencia_y_queda_acotado():
    rows = tuple(SessionAggregate("d%d" % i, float(i%4-1), 1+i%3)
                 for i in range(1,30))
    b = stationary_block_length(rows)
    assert 1 <= b <= len(rows)//3
    assert resample_stationary_session_clusters(
        rows, n_replicates=20, seed=1).block_length == b


def _studentized_rows():
    return tuple(SessionAggregate(
        "d%03d" % i, 0.25*(1+i%3)+((i*17)%11-5)/5.0, 1+i%3)
        for i in range(160))


def test_hac_del_ratio_es_positivo_y_finito():
    assert ratio_hac_standard_error(_studentized_rows(), lag=3) > 0


def test_bootstrap_t_es_determinista_y_persiste_metodo():
    rows = _studentized_rows()
    a = studentized_stationary_interval(
        rows, n_replicates=200, seed=55, block_length=4, hac_lag=4)
    assert a == studentized_stationary_interval(
        rows, n_replicates=200, seed=55, block_length=4, hac_lag=4)
    assert a.method == "stationary_bootstrap_t"
    assert a.block_length == a.hac_lag == 4
    assert a.lower < a.upper and a.valid_replicates == 200
    assert a.n_sessions == 160 and a.n_trades == sum(r.n_trades for r in rows)


def test_bootstrap_t_falla_fuera_del_dominio_de_cobertura():
    short = tuple(SessionAggregate("d%d" % i, float(i), 1) for i in range(159))
    with pytest.raises(ClusterEstimandError, match="160 sesiones"):
        studentized_stationary_interval(short, n_replicates=20, seed=1)


def test_bootstrap_t_rechaza_lag_y_fraccion_invalidos():
    rows = _studentized_rows()
    with pytest.raises(ClusterEstimandError, match="HAC lag"):
        studentized_stationary_interval(
            rows, n_replicates=20, seed=1, block_length=2, hac_lag=len(rows))
    with pytest.raises(ClusterEstimandError, match="min_valid_fraction"):
        studentized_stationary_interval(
            rows, n_replicates=20, seed=1, block_length=2,
            min_valid_fraction=True)


def test_hac_no_inventa_varianza_si_psi_es_cero():
    rows = tuple(SessionAggregate("d%d" % i, 2.0, 2) for i in range(10))
    with pytest.raises(ClusterEstimandError, match="no positiva"):
        ratio_hac_standard_error(rows, lag=2)
