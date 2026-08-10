import pytest

from edgelab.research.g2 import (
    DSR_DEPENDENCE_METHOD,
    DSR_METHOD_SHA256_V1,
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


def dsr(probability=0.96, method_sha=DSR_METHOD_SHA256_V1,
        dependence_method=DSR_DEPENDENCE_METHOD):
    return DSREvidence(
        probability,
        "session",
        "non_annualized",
        197,
        120.0,
        48.0,
        -0.2,
        4.0,
        dependence_method,
        method_sha,
    )


def gate(name, passed=True):
    if name == "dsr":
        return dsr(0.96 if passed else 0.94).gate_result()
    value, threshold = PASS_VALUES[name]
    if not passed:
        value = FAIL_VALUES[name]
    return GateResult(name, passed, value, threshold, B)


def primary(lower=0.1):
    return PrimaryCI(lower, 0.5, 0.95, "stationary_bootstrap_t", 197, B)


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
        primary_ci=primary(),
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
    assert not dsr(0.99, DSR_METHOD_SHA256_V1, "otro_metodo").passed


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
        PrimaryCI(0.1, 0.5, 0.95, "stationary_bootstrap_t", 159, B)
