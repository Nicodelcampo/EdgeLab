from __future__ import annotations

import json

import pytest

import edgelab.research.promotion as promotion
from edgelab.research.g2_decision import (
    CLUSTER_UNIT,
    ESTIMAND_ID,
    G2_REQUIRED_GATES,
    MULTIPLICITY_METHOD,
    DSREvidence,
    G2ValidationDecision,
    GateResult,
    PrimaryCI,
)
from edgelab.research.g2_dsr import (
    DSR_DEPENDENCE_METHOD,
    DSR_IMPLEMENTATION_SHA256,
    DSR_METHOD_SHA256_V2,
)
from edgelab.research.promotion import (
    PromotionError,
    RegistryIntegrityError,
    append_record,
    current_status,
    load_registry,
    validate_record,
)

A = "a" * 64
B = "b" * 64
CALENDAR = "c" * 64


@pytest.fixture(autouse=True)
def approved(monkeypatch):
    monkeypatch.setattr(promotion, "APPROVED_G2_CONTRACT_SHA256S", frozenset({A}))
    monkeypatch.setattr(
        promotion,
        "APPROVED_G2_IMPLEMENTATION_SHA256S",
        frozenset({DSR_IMPLEMENTATION_SHA256}),
    )


def record(record_id, candidate="edge-1", status="idea", **extra):
    value = dict(
        record_id=record_id,
        candidate_id=candidate,
        status=status,
        recorded_utc="2026-08-04T03:00:00Z",
        reason="fixture",
        evidence_refs=[],
    )
    value.update(extra)
    return value


def dsr_evidence(probability=0.96):
    return DSREvidence(
        probability,
        0.2,
        "eligible_session_calendar",
        "non_annualized",
        197,
        98.5,
        48.0,
        -0.2,
        4.0,
        15,
        1.0,
        2.0,
        2.0,
        17,
        CALENDAR,
        DSR_DEPENDENCE_METHOD,
        DSR_METHOD_SHA256_V2,
        DSR_IMPLEMENTATION_SHA256,
    )


def gate(name, passed, evidence):
    if name == "dsr":
        return evidence.gate_result()
    values = {
        "campaign_null": (0.01 if passed else 0.1, 0.05),
        "pbo": (0.2 if passed else 0.8, 0.5),
        "walk_forward": (0.1 if passed else 0.0, 0.0),
        "parameter_sensitivity": (0.1 if passed else -0.1, 0.0),
    }
    value, threshold = values[name]
    return GateResult(name, passed, value, threshold, B)


def canonical_decision(
    *,
    campaign="camp-1",
    run="run-1",
    config="cfg-1",
    lower=0.1,
    failed_gate=None,
    contract=A,
):
    evidence = dsr_evidence(0.90 if failed_gate == "dsr" else 0.96)
    gates = tuple(
        gate(name, name != failed_gate, evidence) for name in G2_REQUIRED_GATES
    )
    return G2ValidationDecision(
        "g2-1",
        campaign,
        run,
        config,
        contract,
        ESTIMAND_ID,
        CLUSTER_UNIT,
        "null-1",
        gates,
        evidence,
        PrimaryCI(
            lower,
            0.5,
            0.95,
            "stationary_bootstrap_t",
            197,
            CALENDAR,
            B,
        ),
        MULTIPLICITY_METHOD,
        48.0,
        "2026-08-04T03:00:00Z",
    ).to_dict()


def supported(record_id="r4", **extra):
    value = dict(
        campaign_id="camp-1",
        run_id="run-1",
        config_id="cfg-1",
        validation_decision=canonical_decision(),
    )
    value.update(extra)
    return record(record_id, status="statistically_supported", **value)


def advance(path):
    append_record(path, record("r1"))
    append_record(path, record("r2", status="technically_valid"))
    append_record(path, record("r3", status="exploratory_candidate"))


def test_estados_previos_no_exigen_g2():
    for status in (
        "external_candidate",
        "idea",
        "technically_valid",
        "exploratory_candidate",
    ):
        validate_record(record("r-" + status, status=status))


def test_promocion_canonica_valida():
    validate_record(supported())


def test_no_confia_en_passed_o_digest():
    raw = canonical_decision()
    raw["passed"] = False
    with pytest.raises(PromotionError, match="passed"):
        validate_record(supported(validation_decision=raw))
    raw = canonical_decision()
    raw["evidence_digest"] = A
    with pytest.raises(PromotionError, match="evidence_digest"):
        validate_record(supported(validation_decision=raw))


def test_evidencia_ausente_o_gate_fallido_bloquea():
    raw = canonical_decision()
    del raw["dsr_evidence"]
    with pytest.raises(PromotionError, match="incompleta"):
        validate_record(supported(validation_decision=raw))
    with pytest.raises(PromotionError, match="no aprobó"):
        validate_record(
            supported(validation_decision=canonical_decision(failed_gate="pbo"))
        )


def test_ic_con_cota_no_positiva_bloquea():
    with pytest.raises(PromotionError, match="no aprobó"):
        validate_record(
            supported(validation_decision=canonical_decision(lower=0.0))
        )


@pytest.mark.parametrize(
    "field,keyword",
    [
        ("campaign_id", {"campaign": "otra"}),
        ("run_id", {"run": "otro"}),
        ("config_id", {"config": "otra"}),
    ],
)
def test_identidad_de_registro_y_decision_coincide(field, keyword):
    with pytest.raises(PromotionError, match=field):
        validate_record(
            supported(validation_decision=canonical_decision(**keyword))
        )


def test_contrato_e_implementacion_necesitan_aprobaciones_separadas(monkeypatch):
    monkeypatch.setattr(promotion, "APPROVED_G2_CONTRACT_SHA256S", frozenset())
    with pytest.raises(PromotionError, match="contrato G2 no aprobado"):
        validate_record(supported())
    monkeypatch.setattr(promotion, "APPROVED_G2_CONTRACT_SHA256S", frozenset({A}))
    monkeypatch.setattr(
        promotion,
        "APPROVED_G2_IMPLEMENTATION_SHA256S",
        frozenset(),
    )
    with pytest.raises(PromotionError, match="implementación G2 no aprobada"):
        validate_record(supported())


def test_secuencia_append_only(tmp_path):
    path = tmp_path / "registry.jsonl"
    advance(path)
    append_record(path, supported())
    assert current_status(path, "edge-1") == "statistically_supported"
    assert len(load_registry(path)) == 4


def test_no_salto_de_gate(tmp_path):
    path = tmp_path / "registry.jsonl"
    append_record(path, record("r1"))
    with pytest.raises(PromotionError, match="salto|transición"):
        append_record(path, supported("r2"))


def test_integridad_detecta_alteracion(tmp_path):
    path = tmp_path / "registry.jsonl"
    append_record(path, record("r1"))
    row = json.loads(path.read_text())
    row["reason"] = "alterado"
    path.write_text(json.dumps(row) + "\n")
    with pytest.raises(RegistryIntegrityError, match="record_digest"):
        load_registry(path)


def test_terminal_no_reabre(tmp_path):
    path = tmp_path / "registry.jsonl"
    append_record(path, record("r1"))
    append_record(path, record("r2", status="failed"))
    with pytest.raises(PromotionError, match="terminal"):
        append_record(path, record("r3"))


def test_timestamp_utc_y_campos_sistema():
    with pytest.raises(PromotionError, match="UTC"):
        validate_record(
            record("x", recorded_utc="2026-08-04T00:00:00-03:00")
        )
    with pytest.raises(PromotionError, match="campos de integridad"):
        validate_record(
            record("x", record_digest="x"),
            allow_system_fields=False,
        )
