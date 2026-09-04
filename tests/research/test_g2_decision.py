import math

import pytest

import edgelab.research.g2_decision as decision
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
from edgelab.research.g2_dsr import (
    DSR_DEPENDENCE_METHOD,
    DSR_IMPLEMENTATION_SHA256,
    DSR_METHOD_SHA256_V2,
)

A = "a" * 64
B = "b" * 64
CALENDAR = "c" * 64


def dsr(probability=0.96, implementation=DSR_IMPLEMENTATION_SHA256):
    return DSREvidence(
        probability=probability,
        sharpe=0.2,
        observational_unit="eligible_session_calendar",
        scale="non_annualized",
        n_observations=197,
        n_effective=98.5,
        n_trials_effective=48.0,
        skew=-0.2,
        kurtosis=4.0,
        hac_lag=15,
        sample_variance=1.0,
        hac_variance=2.0,
        dependence_factor=2.0,
        zero_trade_sessions=17,
        calendar_sha256=CALENDAR,
        dependence_method=DSR_DEPENDENCE_METHOD,
        method_sha256=DSR_METHOD_SHA256_V2,
        implementation_sha256=implementation,
    )


def gate(name, passed=True, dsr_evidence=None):
    if name == "dsr":
        evidence = dsr_evidence or dsr()
        return evidence.gate_result()
    values = {
        "campaign_null": (0.01 if passed else 0.10, 0.05),
        "pbo": (0.20 if passed else 0.75, 0.50),
        "walk_forward": (0.10 if passed else 0.0, 0.0),
        "parameter_sensitivity": (0.05 if passed else -0.01, 0.0),
    }
    value, threshold = values[name]
    return GateResult(name, passed, value, threshold, B)


def primary(lower=0.1, calendar=CALENDAR):
    return PrimaryCI(
        lower,
        0.5,
        0.95,
        "stationary_bootstrap_t",
        197,
        calendar,
        B,
    )


def complete(**changes):
    evidence = changes.pop("dsr_evidence", dsr())
    values = dict(
        decision_id="g2-1",
        campaign_id="camp",
        run_id="run",
        config_id="cfg",
        contract_sha256=A,
        estimand_id=ESTIMAND_ID,
        cluster_unit=CLUSTER_UNIT,
        null_id="null",
        gate_results=tuple(gate(name, dsr_evidence=evidence) for name in G2_REQUIRED_GATES),
        dsr_evidence=evidence,
        primary_ci=primary(),
        multiplicity_method=MULTIPLICITY_METHOD,
        n_effective=48.0,
        created_utc="2026-08-04T00:30:00Z",
    )
    values.update(changes)
    return G2ValidationDecision(**values)


def test_dsr_umbral_y_fingerprint():
    assert not dsr(0.949).passed
    assert dsr(0.95).passed
    with pytest.raises(G2DecisionError, match="implementation"):
        dsr(0.99, B)


def test_ic_y_cada_gate_bloquean():
    assert not complete(primary_ci=primary(0)).passed
    for failed in G2_REQUIRED_GATES:
        evidence = dsr(0.90) if failed == "dsr" else dsr()
        gates = tuple(
            gate(name, passed=name != failed, dsr_evidence=evidence)
            for name in G2_REQUIRED_GATES
        )
        assert not complete(dsr_evidence=evidence, gate_results=gates).passed


def test_gate_no_acepta_booleano_forjado():
    with pytest.raises(G2DecisionError, match="passed"):
        GateResult("pbo", True, 0.9, 0.5, B)
    with pytest.raises(G2DecisionError, match="threshold"):
        GateResult("pbo", True, 0.2, 0.9, B)


def test_dsr_e_ic_comparten_calendario_y_poblacion():
    with pytest.raises(G2DecisionError, match="mismo calendario"):
        complete(primary_ci=primary(calendar=B))
    short = primary()
    object.__setattr__(short, "n_sessions", 196)
    with pytest.raises(G2DecisionError, match="mismas sesiones"):
        complete(primary_ci=short)


def test_n_effective_es_presupuesto_de_intentos():
    with pytest.raises(G2DecisionError, match="n_trials_effective"):
        complete(n_effective=47.0)


def test_decision_determinista_y_reconstruible():
    first = complete()
    second = complete()
    assert first.passed
    assert first.evidence_digest == second.evidence_digest
    assert first.decision_digest == second.decision_digest
    assert validate_decision_dict(first.to_dict()).passed


def test_no_confia_en_flags_ni_digests_recibidos():
    raw = complete().to_dict()
    raw["passed"] = False
    with pytest.raises(G2DecisionError, match="passed"):
        validate_decision_dict(raw)
    raw = complete().to_dict()
    raw["evidence_digest"] = A
    with pytest.raises(G2DecisionError, match="evidence_digest"):
        validate_decision_dict(raw)


def test_evidencia_faltante_bloquea():
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
    with pytest.raises(G2DecisionError, match="UTC"):
        complete(created_utc="2026-08-03T21:30:00-03:00")
    with pytest.raises(G2DecisionError, match="160 sesiones"):
        PrimaryCI(0.1, 0.5, 0.95, "stationary_bootstrap_t", 159, CALENDAR, B)
