"""Registro append-only y fail-closed de promociones de candidatos.

Vuelve ejecutable la cadena de ``docs/NORTH_STAR.md`` e impide materializar
``statistically_supported`` o estados posteriores sin una decisión G2 completa,
ligada a campaña, run, config y un contrato explícitamente aprobado.

El JSONL usa una cadena de hashes. Detecta alteraciones, reordenamientos y
eliminaciones interiores; un registro corrupto bloquea nuevas promociones. La
eliminación de la última fila no es detectable sólo con una cadena hacia atrás:
la detecta el historial Git del ledger. El writer es local de un solo proceso;
no se afirma seguridad ante escritores concurrentes.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Mapping

__all__ = [
    "PromotionError", "RegistryIntegrityError", "PROMOTION_STATES",
    "G2_REQUIRED_GATES", "APPROVED_G2_CONTRACT_SHA256S",
    "DEFAULT_REGISTRY_PATH", "validate_record", "load_registry",
    "append_record", "current_status",
]

PROMOTION_STATES = (
    "external_candidate", "idea", "technically_valid",
    "exploratory_candidate", "statistically_supported",
    "economically_viable", "holdout_confirmed", "paper_validated",
    "live_candidate",
)
TERMINAL_STATES = ("failed", "retired")
_STATE_RANK = {name: i for i, name in enumerate(PROMOTION_STATES)}
_G2_MIN_RANK = _STATE_RANK["statistically_supported"]

# Estructura del contrato vigente. Cambiarla exige una enmienda versionada.
G2_REQUIRED_GATES = (
    "mcpt", "pbo", "dsr", "walk_forward", "parameter_sensitivity",
)

# Contención de INC-007: vacío a propósito. Mientras el contrato G2 actual siga
# semánticamente roto, NINGUNA decisión puede materializar statistically_supported.
# El commit de enmienda agregará el SHA-256 del contrato corregido.
APPROVED_G2_CONTRACT_SHA256S = frozenset()

_REPO = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = str(_REPO / "docs" / "promotion_registry.jsonl")
_SYSTEM_FIELDS = {"previous_digest", "record_digest"}


class PromotionError(RuntimeError):
    """El registro o una transición viola el contrato de promoción."""


class RegistryIntegrityError(PromotionError):
    """El JSONL no es íntegro; ninguna promoción nueva puede continuar."""


def _canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _digest(record: Mapping) -> str:
    payload = {k: v for k, v in record.items() if k != "record_digest"}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _required_text(mapping: Mapping, field: str, where: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PromotionError("%s: `%s` debe ser texto no vacio" % (where, field))
    return value


def _sha256(mapping: Mapping, field: str, where: str) -> str:
    value = _required_text(mapping, field, where)
    if len(value) != 64 or any(c not in "0123456789abcdefABCDEF" for c in value):
        raise PromotionError("%s: `%s` debe ser un SHA-256 hexadecimal completo" %
                             (where, field))
    return value.lower()


def _utc_timestamp(value: str, where: str) -> None:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise PromotionError("%s: `recorded_utc` no es ISO-8601 valido" % where) from exc
    if dt.tzinfo is None or dt.utcoffset() is None or dt.utcoffset().total_seconds() != 0:
        raise PromotionError("%s: `recorded_utc` debe declarar UTC" % where)


def _validate_g2(decision: Mapping, where: str) -> None:
    if not isinstance(decision, Mapping):
        raise PromotionError("%s: `validation_decision` debe ser un objeto" % where)
    dwhere = where + ".validation_decision"
    _required_text(decision, "decision_id", dwhere)
    if decision.get("gate") != "G2":
        raise PromotionError("%s: la decision requerida debe ser del gate G2" % where)
    if decision.get("passed") is not True:
        raise PromotionError("%s: G2 debe tener `passed=true` exacto" % where)

    contract_sha = _sha256(decision, "contract_sha256", dwhere)
    _sha256(decision, "evidence_digest", dwhere)
    if contract_sha not in APPROVED_G2_CONTRACT_SHA256S:
        raise PromotionError(
            "%s: contrato G2 no aprobado `%s`; promociones congeladas" %
            (where, contract_sha))

    required = decision.get("required_gates")
    results = decision.get("gate_results")
    if not isinstance(required, list):
        raise PromotionError("%s: `required_gates` debe ser una lista" % where)
    if tuple(required) != G2_REQUIRED_GATES:
        raise PromotionError(
            "%s: gates G2 deben coincidir exactamente y en orden con %s" %
            (where, G2_REQUIRED_GATES))
    if not isinstance(results, Mapping):
        raise PromotionError("%s: `gate_results` debe ser un objeto" % where)
    if set(results) != set(G2_REQUIRED_GATES):
        raise PromotionError(
            "%s: `gate_results` debe coincidir exactamente con el contrato G2" % where)
    failed = [name for name in G2_REQUIRED_GATES
              if not isinstance(results.get(name), Mapping)
              or results[name].get("passed") is not True]
    if failed:
        raise PromotionError("%s: gates requeridos sin PASS exacto: %s" %
                             (where, ", ".join(failed)))


def validate_record(record: Mapping, *, allow_system_fields: bool = True) -> dict:
    """Valida una fila sin persistirla y devuelve una copia ordinaria."""
    if not isinstance(record, Mapping):
        raise PromotionError("promotion record debe ser un objeto")
    row = dict(record)
    if not allow_system_fields and _SYSTEM_FIELDS.intersection(row):
        raise PromotionError("los campos de integridad los genera el registro")

    where = "promotion record"
    _required_text(row, "record_id", where)
    _required_text(row, "candidate_id", where)
    status = _required_text(row, "status", where)
    if status not in PROMOTION_STATES + TERMINAL_STATES:
        raise PromotionError("%s: status desconocido `%s`" % (where, status))
    recorded = _required_text(row, "recorded_utc", where)
    _utc_timestamp(recorded, where)
    _required_text(row, "reason", where)
    refs = row.get("evidence_refs")
    if not isinstance(refs, list) or any(not isinstance(x, str) or not x for x in refs):
        raise PromotionError("%s: `evidence_refs` debe ser una lista de strings" % where)

    if status in _STATE_RANK and _STATE_RANK[status] >= _G2_MIN_RANK:
        for field in ("campaign_id", "run_id", "config_id"):
            _required_text(row, field, where)
        _validate_g2(row.get("validation_decision"), where)
    return row


def load_registry(path=DEFAULT_REGISTRY_PATH) -> list[dict]:
    """Lee y verifica JSON, schema, digests y encadenamiento disponible."""
    path = str(path)
    if not os.path.exists(path):
        return []
    rows, previous = [], None
    with open(path, encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            if not line.strip():
                raise RegistryIntegrityError(
                    "%s:%d: linea vacia en un registro JSONL" % (path, line_no))
            try:
                row = json.loads(line)
                validate_record(row)
            except (json.JSONDecodeError, PromotionError) as exc:
                raise RegistryIntegrityError(
                    "%s:%d: fila invalida: %s" % (path, line_no, exc)) from exc
            if row.get("previous_digest") != previous:
                raise RegistryIntegrityError(
                    "%s:%d: cadena rota (previous_digest=%r, esperado=%r)" %
                    (path, line_no, row.get("previous_digest"), previous))
            actual = _digest(row)
            if row.get("record_digest") != actual:
                raise RegistryIntegrityError(
                    "%s:%d: record_digest no coincide" % (path, line_no))
            previous = actual
            rows.append(row)
    return rows


def _check_transition(rows: list[dict], new: Mapping) -> None:
    if any(r["record_id"] == new["record_id"] for r in rows):
        raise PromotionError("record_id duplicado: %s" % new["record_id"])
    previous = [r for r in rows if r["candidate_id"] == new["candidate_id"]]
    if not previous:
        if new["status"] not in ("external_candidate", "idea"):
            raise PromotionError(
                "un candidato nuevo debe comenzar en external_candidate o idea")
        return

    old_status = previous[-1]["status"]
    new_status = new["status"]
    if old_status in TERMINAL_STATES:
        raise PromotionError("%s es terminal; no admite transiciones" % old_status)
    if new_status in TERMINAL_STATES or new_status == old_status:
        return

    # external_candidate e idea son entradas alternativas al mismo pipeline.
    if old_status in ("external_candidate", "idea"):
        if new_status != "technically_valid":
            raise PromotionError("transicion prohibida: %s -> %s" %
                                 (old_status, new_status))
        return

    old_rank = _STATE_RANK[old_status]
    new_rank = _STATE_RANK[new_status]
    if new_rank < old_rank:
        raise PromotionError("regresion de estado prohibida: %s -> %s" %
                             (old_status, new_status))
    if new_rank != old_rank + 1:
        raise PromotionError("salto de gate prohibido: %s -> %s" %
                             (old_status, new_status))


def append_record(path, record: Mapping) -> dict:
    """Agrega una fila sin reescribir; valida todo antes de abrir en append."""
    path = str(path)
    row = validate_record(record, allow_system_fields=False)
    rows = load_registry(path)
    _check_transition(rows, row)
    row["previous_digest"] = rows[-1]["record_digest"] if rows else None
    row["record_digest"] = _digest(row)

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(_canonical_json(row) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return row


def current_status(path, candidate_id: str) -> str | None:
    """Estado más reciente, después de verificar todo el ledger disponible."""
    if not isinstance(candidate_id, str) or not candidate_id:
        raise PromotionError("candidate_id debe ser texto no vacio")
    matches = [r for r in load_registry(path) if r["candidate_id"] == candidate_id]
    return matches[-1]["status"] if matches else None
