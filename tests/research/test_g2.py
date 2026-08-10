"""G2-A1: fixtures sintéticos con verdad conocida y regresiones adversariales."""
import math

import pytest

from edgelab.research import g2
from edgelab.research.g2_ratio import RatioCell


def _noise(n, seed=7, amplitude=1.0):
    rng = g2._lcg(seed)
    return [
        amplitude * (((next(rng) >> 8) % 2001) - 1000) / 1000.0
        for _ in range(n)
    ]


# Nulo de campaña y retiro del MCPT legado
def test_nulo_exige_mil_replicas():
    with pytest.raises(g2.G2SemanticError, match="1000"):
        g2.campaign_null_pvalue(1.0, [0.0] * 999)


def test_nulo_detecta_estadistico_fuera_de_todas_las_replicas():
    p_value, observed = g2.campaign_null_pvalue(1.0, [0.0] * 1000)
    assert p_value == pytest.approx(1 / 1001)
    assert observed == 1.0


def test_nulo_cuenta_empates_de_forma_conservadora():
    p_value, _ = g2.campaign_null_pvalue(0.0, [0.0] * 1000)
    assert p_value == 1.0


def test_mcpt_legado_no_puede_usarse_como_gate():
    with pytest.raises(g2.G2SemanticError, match="retirado"):
        g2.mcpt([1.0, -1.0], ["d1", "d2"])


def test_diagnostico_legado_rechaza_un_edge_estable_y_por_eso_no_es_gate():
    returns = [1.0] * 200
    sessions = ["d%02d" % (index // 10) for index in range(200)]
    p_value, _ = g2.temporal_concentration_test(returns, sessions)
    assert p_value == 1.0


def test_diagnostico_exige_sesiones_contiguas_y_ordenadas():
    with pytest.raises(g2.G2SemanticError, match="contiguo"):
        g2.temporal_concentration_test([1.0, 1.0, 1.0], ["d1", "d2", "d1"])


# PBO canónico por ratio
def test_pbo_usa_expectativa_y_no_pnl_total():
    matrix = [(RatioCell(100, 100), RatioCell(2, 1)) for _ in range(16)]
    pbo, lambdas = g2.pbo_cscv(matrix)
    assert pbo == 0.0
    assert len(lambdas) == math.comb(g2.CSCV_S, g2.CSCV_S // 2) == 70


def test_pbo_rechaza_escalares_ambiguos():
    with pytest.raises(Exception, match="RatioCell"):
        g2.pbo_cscv([[1.0, 2.0] for _ in range(8)])


# DSR
def test_dsr_castiga_el_numero_de_intentos():
    base = dict(n_obs=500, skew=0.0, kurt=3.0)
    one = g2.deflated_sharpe(0.1, n_trials=1, **base)
    many = g2.deflated_sharpe(0.1, n_trials=48, **base)
    thousand = g2.deflated_sharpe(0.1, n_trials=1000, **base)
    assert one > many > thousand


def test_dsr_bajo_para_sharpe_mediocre_no_aprueba():
    probability = g2.deflated_sharpe(0.1, n_obs=300, n_trials=48)
    assert probability < 0.5 < g2.DSR_MIN


def test_dsr_formal_persiste_metodo_versionado():
    values = [0.20 + (((index * 17) % 11) - 5) / 10.0 for index in range(240)]
    result = g2.deflated_sharpe_sessions(values, n_trials=8, hac_lag=4)
    assert result.n_observations == 240
    assert 2 <= result.n_effective <= 240
    assert result.dependence_method == g2.DSR_DEPENDENCE_METHOD
    assert result.method_sha256 == g2.DSR_METHOD_SHA256_V1
    assert len(result.method_sha256) == 64


def test_dsr_hac_reduce_n_efectivo_con_clustering_positivo():
    clustered = [-1.0] * 60 + [1.0] * 60
    alternating = [-1.0, 1.0] * 60
    first = g2.deflated_sharpe_sessions(clustered, n_trials=2, hac_lag=10)
    second = g2.deflated_sharpe_sessions(alternating, n_trials=2, hac_lag=10)
    assert first.n_effective < second.n_effective


def test_dsr_rechaza_serie_sin_varianza():
    with pytest.raises(g2.G2SemanticError, match="varianza"):
        g2.deflated_sharpe_sessions([1.0] * 20, n_trials=2)


# Walk-forward canónico por ratio
def test_walk_forward_selecciona_expectativa_no_frecuencia():
    folds = ("f1", "f2", "f3", "f4")
    per_fold = {
        "frecuente": {fold: RatioCell(100, 100) for fold in folds},
        "mejor": {fold: RatioCell(2, 1) for fold in folds},
    }
    observed, detail = g2.walk_forward(per_fold, folds)
    assert observed == 2.0
    assert all(row["ganador_in_sample"] == "mejor" for row in detail)


def test_walk_forward_no_admite_selector_post_hoc():
    folds = ("f1", "f2")
    per_fold = {
        "a": {fold: RatioCell(1, 1) for fold in folds},
        "b": {fold: RatioCell(2, 1) for fold in folds},
    }
    with pytest.raises(g2.G2SemanticError, match="ad-hoc"):
        g2.walk_forward(per_fold, folds, seleccionar=lambda values: values[0])


# Sensibilidad
def test_sensibilidad_detecta_pico_y_acepta_meseta():
    peak = {"winner": 5.0, "a": -1.0, "b": -2.0, "c": -0.5}
    median, positives, count = g2.parameter_sensitivity(
        peak, "winner", ["a", "b", "c"]
    )
    assert median < 0 and positives == 0 and count == 3
    plateau = {"winner": 5.0, "a": 4.0, "b": 3.0, "c": 4.5}
    median, positives, count = g2.parameter_sensitivity(
        plateau, "winner", ["a", "b", "c"]
    )
    assert median > 0 and positives == count == 3


def test_sensibilidad_sin_vecinos_falla_cerrado():
    median, positives, count = g2.parameter_sensitivity(
        {"winner": 1.0}, "winner", ["missing"]
    )
    assert median is None and positives == count == 0


# Composición
def _passing_evaluation():
    return dict(
        null_p=0.01,
        pbo=0.20,
        dsr=0.96,
        wf_oos=0.10,
        sensibilidad_mediana=0.05,
        primary_ci_lower=0.01,
    )


def test_aprueba_solo_con_seis_requisitos_verdes():
    results, passed = g2.evaluar(**_passing_evaluation())
    assert passed and len(results) == 6


@pytest.mark.parametrize(
    "change",
    [
        {"null_p": 0.051},
        {"pbo": 0.51},
        {"dsr": 0.949},
        {"wf_oos": 0.0},
        {"sensibilidad_mediana": 0.0},
        {"primary_ci_lower": 0.0},
    ],
)
def test_cada_requisito_es_excluyente(change):
    values = _passing_evaluation()
    values.update(change)
    _, passed = g2.evaluar(**values)
    assert not passed


def test_un_requisito_no_evaluado_nunca_aprueba():
    values = _passing_evaluation()
    del values["primary_ci_lower"]
    results, passed = g2.evaluar(**values)
    assert not passed
    assert any("no evaluado" in result.detail for result in results)
