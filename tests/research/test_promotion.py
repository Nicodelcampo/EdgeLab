"""Regresiones de INC-007: la promoción deja de ser una etiqueta documental."""
from __future__ import annotations

import json

import pytest

from edgelab.research.promotion import (
    PromotionError,
    RegistryIntegrityError,
    append_record,
    current_status,
    load_registry,
    validate_record,
)

SHA_A = "a" * 64
SHA_B = "b" * 64


def record(record_id, candidate="edge-1", status="idea", **extra):
    out = dict(record_id=record_id, candidate_id=candidate, status=status,
               recorded_utc="2026-08-03T21:00:00Z", reason="fixture sintetico",
               evidence_refs=[])
    out.update(extra)
    return out


def g2(*, passed=True, required=None, results=None):
    required = required or ["mcpt", "pbo", "dsr", "walk_forward", "sensitivity"]
    results = results or {name: {"passed": True, "value": 1} for name in required}
    return dict(decision_id="g2-fixture", gate="G2", passed=passed,
                contract_sha256=SHA_A, evidence_digest=SHA_B,
                required_gates=required, gate_results=results)


def advance_to_exploratory(path):
    append_record(path, record("r1", status="idea"))
    append_record(path, record("r2", status="technically_valid"))
    append_record(path, record("r3", status="exploratory_candidate"))


def supported(record_id="r4", **extra):
    base = dict(campaign_id="camp-1", run_id="run-1", config_id="cfg-1",
                validation_decision=g2())
    base.update(extra)
    return record(record_id, status="statistically_supported", **base)


def test_estados_previos_no_exigen_g2():
    validate_record(record("r1", status="external_candidate"))
    validate_record(record("r2", status="idea"))
    validate_record(record("r3", status="technically_valid"))
    validate_record(record("r4", status="exploratory_candidate"))


@pytest.mark.parametrize("field", ["campaign_id", "run_id", "config_id"])
def test_statistically_supported_exige_identidad_completa(field):
    r = supported()
    del r[field]
    with pytest.raises(PromotionError, match=field):
        validate_record(r)


def test_statistically_supported_exige_decision_g2():
    r = supported()
    del r["validation_decision"]
    with pytest.raises(PromotionError, match="validation_decision"):
        validate_record(r)


def test_g2_false_no_promueve():
    with pytest.raises(PromotionError, match="passed=true"):
        validate_record(supported(validation_decision=g2(passed=False)))


def test_no_alcanza_un_booleano_global_si_falta_un_gate():
    required = ["mcpt", "pbo", "dsr"]
    results = {"mcpt": {"passed": True}, "pbo": {"passed": True}}
    with pytest.raises(PromotionError, match="coincidir exactamente"):
        validate_record(supported(validation_decision=g2(
            required=required, results=results)))


def test_un_gate_requerido_en_false_bloquea():
    required = ["mcpt", "pbo", "dsr"]
    results = {name: {"passed": name != "dsr"} for name in required}
    with pytest.raises(PromotionError, match="dsr"):
        validate_record(supported(validation_decision=g2(
            required=required, results=results)))


def test_estados_posteriores_siguen_exigiendo_g2():
    for status in ("economically_viable", "holdout_confirmed",
                   "paper_validated", "live_candidate"):
        r = record("r-" + status, status=status)
        with pytest.raises(PromotionError, match="campaign_id"):
            validate_record(r)


def test_sha_de_contrato_y_evidencia_deben_ser_completos():
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


def test_no_se_pueden_saltar_gates(tmp_path):
    p = tmp_path / "registry.jsonl"
    append_record(p, record("r1", status="idea"))
    with pytest.raises(PromotionError, match="salto de gate"):
        append_record(p, supported("r2"))
    assert len(load_registry(p)) == 1


def test_secuencia_completa_permite_promocion_g2(tmp_path):
    p = tmp_path / "registry.jsonl"
    advance_to_exploratory(p)
    row = append_record(p, supported())
    assert row["status"] == "statistically_supported"
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
    assert len(after.splitlines()) == 2


def test_record_id_duplicado_bloquea_sin_escribir(tmp_path):
    p = tmp_path / "registry.jsonl"
    append_record(p, record("r1"))
    before = p.read_bytes()
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
    append_record(p, record("r1", status="idea"))
    append_record(p, record("r2", status="technically_valid"))
    with pytest.raises(PromotionError, match="regresion"):
        append_record(p, record("r3", status="idea"))


def test_alterar_una_fila_rompe_integridad_y_bloquea_append(tmp_path):
    p = tmp_path / "registry.jsonl"
    append_record(p, record("r1", status="idea"))
    row = json.loads(p.read_text(encoding="utf-8"))
    row["reason"] = "contenido alterado"
    p.write_text(json.dumps(row) + "\n", encoding="utf-8")
    before = p.read_bytes()
    with pytest.raises(RegistryIntegrityError, match="record_digest"):
        append_record(p, record("r2", status="technically_valid"))
    assert p.read_bytes() == before


def test_borrar_primera_fila_rompe_la_cadena(tmp_path):
    p = tmp_path / "registry.jsonl"
    append_record(p, record("r1", status="idea"))
    append_record(p, record("r2", status="technically_valid"))
    lines = p.read_text(encoding="utf-8").splitlines()
    p.write_text(lines[1] + "\n", encoding="utf-8")
    with pytest.raises(RegistryIntegrityError, match="cadena rota"):
        load_registry(p)


def test_callers_no_pueden_inyectar_hashes(tmp_path):
    p = tmp_path / "registry.jsonl"
    r = record("r1", record_digest="falso")
    with pytest.raises(PromotionError, match="campos de integridad"):
        append_record(p, r)
