"""Regresiones de INC-007: promoción fail-closed y sin saltos."""
from __future__ import annotations

import json

import pytest

import edgelab.research.promotion as promotion
from edgelab.research.promotion import (
    G2_REQUIRED_GATES,
    PromotionError,
    RegistryIntegrityError,
    append_record,
    current_status,
    load_registry,
    validate_record,
)

SHA_A = "a" * 64
SHA_B = "b" * 64


@pytest.fixture(autouse=True)
def approved_contract(monkeypatch):
    """Los tests positivos habilitan sólo el contrato sintético explícito."""
    monkeypatch.setattr(promotion, "APPROVED_G2_CONTRACT_SHA256S",
                        frozenset({SHA_A}))


def record(record_id, candidate="edge-1", status="idea", **extra):
    out = dict(record_id=record_id, candidate_id=candidate, status=status,
               recorded_utc="2026-08-03T21:00:00Z", reason="fixture sintetico",
               evidence_refs=[])
    out.update(extra)
    return out


def g2(*, passed=True, required=None, results=None, contract_sha=SHA_A):
    required = list(required or G2_REQUIRED_GATES)
    if results is None:
        results = {name: {"passed": True, "value": 1} for name in required}
    return dict(decision_id="g2-fixture", gate="G2", passed=passed,
                contract_sha256=contract_sha, evidence_digest=SHA_B,
                required_gates=required, gate_results=results)


def advance_to_exploratory(path, start="idea"):
    append_record(path, record("r1", status=start))
    append_record(path, record("r2", status="technically_valid"))
    append_record(path, record("r3", status="exploratory_candidate"))


def supported(record_id="r4", **extra):
    base = dict(campaign_id="camp-1", run_id="run-1", config_id="cfg-1",
                validation_decision=g2())
    base.update(extra)
    return record(record_id, status="statistically_supported", **base)


def test_estados_previos_no_exigen_g2():
    for status in ("external_candidate", "idea", "technically_valid",
                   "exploratory_candidate"):
        validate_record(record("r-" + status, status=status))


@pytest.mark.parametrize("field", ["campaign_id", "run_id", "config_id"])
def test_statistically_supported_exige_identidad_completa(field):
    r = supported(); del r[field]
    with pytest.raises(PromotionError, match=field):
        validate_record(r)


def test_statistically_supported_exige_decision_g2():
    r = supported(); del r["validation_decision"]
    with pytest.raises(PromotionError, match="validation_decision"):
        validate_record(r)


def test_g2_false_no_promueve():
    with pytest.raises(PromotionError, match="passed=true"):
        validate_record(supported(validation_decision=g2(passed=False)))


def test_contrato_no_aprobado_congela_toda_promocion(monkeypatch):
    monkeypatch.setattr(promotion, "APPROVED_G2_CONTRACT_SHA256S", frozenset())
    with pytest.raises(PromotionError, match="no aprobado"):
        validate_record(supported())


def test_cualquier_sha_bien_formado_no_alcanza():
    with pytest.raises(PromotionError, match="no aprobado"):
        validate_record(supported(validation_decision=g2(contract_sha="c" * 64)))


def test_required_gates_debe_ser_el_contrato_exacto():
    incomplete = list(G2_REQUIRED_GATES[:-1])
    with pytest.raises(PromotionError, match="coincidir exactamente"):
        validate_record(supported(validation_decision=g2(required=incomplete)))
    extra = list(G2_REQUIRED_GATES) + ["inventado"]
    with pytest.raises(PromotionError, match="coincidir exactamente"):
        validate_record(supported(validation_decision=g2(required=extra)))


def test_gate_results_sin_faltantes_ni_extras():
    results = {name: {"passed": True} for name in G2_REQUIRED_GATES[:-1]}
    with pytest.raises(PromotionError, match="gate_results"):
        validate_record(supported(validation_decision=g2(results=results)))


def test_un_gate_requerido_en_false_bloquea():
    results = {name: {"passed": name != "dsr"} for name in G2_REQUIRED_GATES}
    with pytest.raises(PromotionError, match="dsr"):
        validate_record(supported(validation_decision=g2(results=results)))


def test_estados_posteriores_siguen_exigiendo_g2():
    for status in ("economically_viable", "holdout_confirmed",
                   "paper_validated", "live_candidate"):
        with pytest.raises(PromotionError, match="campaign_id"):
            validate_record(record("r-" + status, status=status))


def test_sha_debe_ser_completo():
    bad = g2(); bad["contract_sha256"] = "abc"
    with pytest.raises(PromotionError, match="SHA-256"):
        validate_record(supported(validation_decision=bad))


def test_timestamp_debe_declarar_utc():
    with pytest.raises(PromotionError, match="UTC"):
        validate_record(record("r1", recorded_utc="2026-08-03T18:00:00-03:00"))


def test_candidato_nuevo_no_puede_arrancar_promovido(tmp_path):
    p = tmp_path / "registry.jsonl"
    with pytest.raises(PromotionError, match="debe comenzar"):
        append_record(p, record("r1", status="technically_valid"))
    assert not p.exists()


def test_idea_y_external_son_entradas_alternativas(tmp_path):
    p1 = tmp_path / "ideas.jsonl"
    append_record(p1, record("i1", status="idea"))
    append_record(p1, record("i2", status="technically_valid"))
    p2 = tmp_path / "external.jsonl"
    append_record(p2, record("e1", status="external_candidate"))
    append_record(p2, record("e2", status="technically_valid"))
    assert current_status(p1, "edge-1") == "technically_valid"
    assert current_status(p2, "edge-1") == "technically_valid"


def test_external_no_se_convierte_en_idea_para_esquivar_g0(tmp_path):
    p = tmp_path / "registry.jsonl"
    append_record(p, record("r1", status="external_candidate"))
    with pytest.raises(PromotionError, match="transicion prohibida"):
        append_record(p, record("r2", status="idea"))


def test_no_se_pueden_saltar_gates(tmp_path):
    p = tmp_path / "registry.jsonl"
    append_record(p, record("r1", status="idea"))
    with pytest.raises(PromotionError, match="transicion prohibida|salto de gate"):
        append_record(p, supported("r2"))
    assert len(load_registry(p)) == 1


def test_secuencia_completa_permite_promocion_g2(tmp_path):
    p = tmp_path / "registry.jsonl"
    advance_to_exploratory(p)
    append_record(p, supported())
    assert current_status(p, "edge-1") == "statistically_supported"
    assert len(load_registry(p)) == 4


def test_append_only_conserva_filas_y_encadena_digests(tmp_path):
    p = tmp_path / "registry.jsonl"
    first = append_record(p, record("r1", status="idea"))
    before = p.read_bytes()
    second = append_record(p, record("r2", status="technically_valid"))
    after = p.read_bytes()
    assert after.startswith(before)
    assert second["previous_digest"] == first["record_digest"]


def test_record_id_duplicado_bloquea_sin_escribir(tmp_path):
    p = tmp_path / "registry.jsonl"
    append_record(p, record("r1")); before = p.read_bytes()
    with pytest.raises(PromotionError, match="duplicado"):
        append_record(p, record("r1"))
    assert p.read_bytes() == before


def test_estado_terminal_no_se_reabre(tmp_path):
    p = tmp_path / "registry.jsonl"
    append_record(p, record("r1", status="idea"))
    append_record(p, record("r2", status="failed"))
    with pytest.raises(PromotionError, match="terminal"):
        append_record(p, record("r3", status="idea"))


def test_regresion_de_estado_bloqueada(tmp_path):
    p = tmp_path / "registry.jsonl"
    advance_to_exploratory(p)
    with pytest.raises(PromotionError, match="regresion"):
        append_record(p, record("r4", status="technically_valid"))


def test_alterar_fila_bloquea_append(tmp_path):
    p = tmp_path / "registry.jsonl"
    append_record(p, record("r1", status="idea"))
    row = json.loads(p.read_text(encoding="utf-8")); row["reason"] = "alterado"
    p.write_text(json.dumps(row) + "\n", encoding="utf-8")
    before = p.read_bytes()
    with pytest.raises(RegistryIntegrityError, match="record_digest"):
        append_record(p, record("r2", status="technically_valid"))
    assert p.read_bytes() == before


def test_borrar_fila_interior_rompe_cadena(tmp_path):
    p = tmp_path / "registry.jsonl"
    append_record(p, record("r1", status="idea"))
    append_record(p, record("r2", status="technically_valid"))
    lines = p.read_text(encoding="utf-8").splitlines()
    p.write_text(lines[1] + "\n", encoding="utf-8")
    with pytest.raises(RegistryIntegrityError, match="cadena rota"):
        load_registry(p)


def test_callers_no_inyectan_hashes(tmp_path):
    with pytest.raises(PromotionError, match="campos de integridad"):
        append_record(tmp_path / "r.jsonl", record("r1", record_digest="falso"))
