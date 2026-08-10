import pytest

from edgelab.research.g2 import (
    DSR_DEPENDENCE_METHOD,
    DSR_IMPLEMENTATION_SHA256,
    DSR_METHOD_SHA256_V2,
    DSR_MIN,
)
from edgelab.research.g2_decision import (
    CLUSTER_UNIT,
    ESTIMAND_ID,
    G2_REQUIRED_GATES,
    MULTIPLICITY_METHOD,
    DSREvidence,
    G2DecisionError,
    G2ValidationDecision,
    GateResult,
    PrimaryCI,
    validate_decision_dict,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64

PASS_VALUES = {
    "mcpt": (0.01, 0.05),
    "pbo": (0.20, 0.50),
    "walk_forward": (0.10, 0.0),
    "parameter_sensitivity": (0.05, 0.0),
}
FAIL_VALUES = {
    "mcpt": 0.06,
    "pbo": 0.51,
    "walk_forward": 0.0,
    "parameter_sensitivity": 0.0,
}


def dsr(
    probability=0.96,
    method_sha=DSR_METHOD_SHA256_V2,
    dependence_method=DSR_DEPENDENCE_METHOD,
    implementation_sha=DSR_IMPLEMENTATION_SHA256,
    calendar_sha=C,
):
    return DSREvidence(
        probability=probability,
        sharpe=0.2,
        observational_unit="session",
        scale="non_annualized",
        n_observations=197,
        n_effective=120.0,
        n_trials_effective=48.0,
        skew=-0.2,
        kurtosis=4.0,
        hac_lag=15,
        sample_variance=1.0,
        hac_variance=197 / 120,
        dependence_factor=197 / 120,
        zero_trade_sessions=7,
        calendar_sha256=calendar_sha,
        dependence_method=dependence_method,
        method_sha256=method_sha,
        implementation_sha256=implementation_sha,
    )


def gate(name, passed=True):
    if name == "dsr":
        return dsr(0.96 if passed else 0.94).gate_result()
    value, threshold = PASS_VALUES[name]
    if not passed:
        value = FAIL_VALUES[name]
    return GateResult(name, passed, value, threshold, B)


def primary(lower=0.1, calendar_sha=C):
    return PrimaryCI(
        lower, 0.5, 0.95, "stationary_bootstrap_t", 197,
        calendar_sha, B,
    )


def complete(**overrides):
    evidence = overrides.pop("dsr_evidence", dsr())
    gates = overrides.pop(
        "gate_results",
        tuple(
            evidence.gate_result() if name == "dsr" else gate(name)
            for name in G2_REQUIRED_GATES
        ),
    )
    values = dict(
        decision_id="g2-1",
        campaign_id="camp",
        run_id="run",
        config_id="cfg",
        contract_sha256=A,
        estimand_id=ESTIMAND_ID,
        cluster_unit=CLUSTER_UNIT,
        null_id="null",
        gate_results=gates,
        primary_ci=primary(calendar_sha=evidence.calendar_sha256),
        dsr_evidence=evidence,
        multiplicity_method=MULTIPLICITY_METHOD,
        n_effective=evidence.n_effective,
        created_utc="2026-08-04T00:30:00Z",
    )
    values.update(overrides)
    return G2ValidationDecision(**values)


def test_dsr_umbral_y_autorizacion():
    assert not dsr(DSR_MIN - 0.001).passed
    assert dsr(DSR_MIN).passed
    assert not dsr(0.99, B).passed
    assert not dsr(0.99, DSR_METHOD_SHA256_V2, "otro_metodo").passed


def test_gate_no_confia_en_bool_ni_umbral_recibidos():
    with pytest.raises(G2DecisionError, match="no puede aprobar"):
        GateResult("pbo", True, 0.9, 0.5, B)
    with pytest.raises(G2DecisionError, match="umbral"):
        GateResult("pbo", True, 0.2, 0.6, B)


def test_ic_y_gate_bloquean():
    assert not complete(primary_ci=primary(0)).passed
    failed = tuple(gate(name, name != "pbo") for name in G2_REQUIRED_GATES)
    assert not complete(gate_results=failed).passed


def test_dsr_embebida_debe_coincidir_con_gate():
    evidence = dsr(0.96)
    gates = tuple(gate(name, name != "dsr") for name in G2_REQUIRED_GATES)
    with pytest.raises(G2DecisionError, match="DSREvidence"):
        complete(dsr_evidence=evidence, gate_results=gates)


def test_decision_determinista_y_reconstruible():
    first, second = complete(), complete()
    assert first.passed
    assert first.evidence_digest == second.evidence_digest
    assert first.decision_digest == second.decision_digest
    assert validate_decision_dict(first.to_dict()).passed


def test_no_confia_en_flags_ni_digests_serializados():
    raw = complete().to_dict()
    bad = dict(raw)
    bad["passed"] = False
    with pytest.raises(G2DecisionError, match="passed"):
        validate_decision_dict(bad)
    bad = dict(raw)
    bad["evidence_digest"] = A
    with pytest.raises(G2DecisionError, match="evidence_digest"):
        validate_decision_dict(bad)


def test_sin_ic_o_dsr_embebida_no_promueve():
    raw = complete().to_dict()
    del raw["primary_ci"]
    with pytest.raises(G2DecisionError, match="incompleta"):
        validate_decision_dict(raw)
    raw = complete().to_dict()
    del raw["dsr_evidence"]
    with pytest.raises(G2DecisionError, match="incompleta"):
        validate_decision_dict(raw)


def test_rechaza_semantica_incompatible():
    with pytest.raises(G2DecisionError, match="estimand"):
        complete(estimand_id="sharpe")
    with pytest.raises(G2DecisionError, match="cluster_unit"):
        complete(cluster_unit="trade")
    with pytest.raises(G2DecisionError, match="multiplicity"):
        complete(multiplicity_method="holm")
    with pytest.raises(G2DecisionError, match="n_effective"):
        complete(n_effective=119.0)
    with pytest.raises(G2DecisionError, match="UTC"):
        complete(created_utc="2026-08-03T21:30:00-03:00")
    with pytest.raises(G2DecisionError, match="160 sesiones"):
        PrimaryCI(0.1, 0.5, 0.95, "stationary_bootstrap_t", 159, C, B)


def test_dsr_e_ic_deben_compartir_calendario():
    with pytest.raises(G2DecisionError, match="mismo calendario"):
        complete(primary_ci=primary(calendar_sha=A))


def test_fingerprint_de_implementacion_es_evidencia_obligatoria():
    raw = complete().to_dict()
    del raw["dsr_evidence"]["implementation_sha256"]
    with pytest.raises(G2DecisionError, match="incompleta"):
        validate_decision_dict(raw)
