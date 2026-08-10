"""Registro append-only y fail-closed de promociones de candidatos.

La promoción a ``statistically_supported`` o estados posteriores sólo acepta
una ``G2ValidationDecision`` canónica reconstruida, ligada a la misma campaña,
run y configuración del registro, a un contrato aprobado y a la implementación
DSR exacta que fue revisada.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Mapping

from edgelab.research.g2_decision import (
    G2DecisionError,
    G2_REQUIRED_GATES,
    validate_decision_dict,
)

__all__ = [
    "PromotionError", "RegistryIntegrityError", "PROMOTION_STATES",
    "G2_REQUIRED_GATES", "APPROVED_G2_CONTRACT_SHA256S",
    "APPROVED_G2_IMPLEMENTATION_SHA256S", "DEFAULT_REGISTRY_PATH",
    "validate_record", "load_registry", "append_record", "current_status",
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
APPROVED_G2_CONTRACT_SHA256S = frozenset()
APPROVED_G2_IMPLEMENTATION_SHA256S = frozenset()
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

def _utc_timestamp(value: str, where: str) -> None:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise PromotionError("%s: `recorded_utc` no es ISO-8601 valido" % where) from exc
    if dt.tzinfo is None or dt.utcoffset() is None or dt.utcoffset().total_seconds() != 0:
        raise PromotionError("%s: `recorded_utc` debe declarar UTC" % where)

def _validate_g2(decision: Mapping, row: Mapping, where: str) -> None:
    if not isinstance(decision, Mapping):
        raise PromotionError("%s: `validation_decision` debe ser un objeto" % where)
    dwhere = where + ".validation_decision"
    try:
        rebuilt = validate_decision_dict(dict(decision))
    except G2DecisionError as exc:
        raise PromotionError("%s: decision G2 canonica invalida: %s" %
                             (dwhere, exc)) from exc
    if not rebuilt.passed:
        raise PromotionError("%s: la decision G2 canonica no aprobo" % dwhere)
    contract_sha = rebuilt.contract_sha256.lower()
    if contract_sha not in APPROVED_G2_CONTRACT_SHA256S:
        raise PromotionError("%s: contrato G2 no aprobado `%s`; promociones congeladas" %
                             (where, contract_sha))
    implementation_sha = rebuilt.dsr_evidence.implementation_sha256.lower()
    if implementation_sha not in APPROVED_G2_IMPLEMENTATION_SHA256S:
        raise PromotionError(
            "%s: implementacion G2 no aprobada `%s`; promociones congeladas" %
            (where, implementation_sha)
        )
    for field in ("campaign_id", "run_id", "config_id"):
        if getattr(rebuilt, field) != row[field]:
            raise PromotionError("%s: `%s` no coincide entre promotion record y decision G2" %
                                 (where, field))

def validate_record(record: Mapping, *, allow_system_fields: bool = True) -> dict:
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
    _utc_timestamp(_required_text(row, "recorded_utc", where), where)
    _required_text(row, "reason", where)
    refs = row.get("evidence_refs")
    if not isinstance(refs, list) or any(not isinstance(x, str) or not x for x in refs):
        raise PromotionError("%s: `evidence_refs` debe ser una lista de strings" % where)
    if status in _STATE_RANK and _STATE_RANK[status] >= _G2_MIN_RANK:
        for field in ("campaign_id", "run_id", "config_id"):
            _required_text(row, field, where)
        _validate_g2(row.get("validation_decision"), row, where)
    return row

def load_registry(path=DEFAULT_REGISTRY_PATH) -> list[dict]:
    path = str(path)
    if not os.path.exists(path):
        return []
    rows, previous = [], None
    with open(path, encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            if not line.strip():
                raise RegistryIntegrityError("%s:%d: linea vacia en un registro JSONL" % (path, line_no))
            try:
                row = json.loads(line)
                validate_record(row)
            except (json.JSONDecodeError, PromotionError) as exc:
                raise RegistryIntegrityError("%s:%d: fila invalida: %s" % (path, line_no, exc)) from exc
            if row.get("previous_digest") != previous:
                raise RegistryIntegrityError("%s:%d: cadena rota (previous_digest=%r, esperado=%r)" %
                                             (path, line_no, row.get("previous_digest"), previous))
            actual = _digest(row)
            if row.get("record_digest") != actual:
                raise RegistryIntegrityError("%s:%d: record_digest no coincide" % (path, line_no))
            previous = actual
            rows.append(row)
    return rows

def _check_transition(rows: list[dict], new: Mapping) -> None:
    if any(r["record_id"] == new["record_id"] for r in rows):
        raise PromotionError("record_id duplicado: %s" % new["record_id"])
    previous = [r for r in rows if r["candidate_id"] == new["candidate_id"]]
    if not previous:
        if new["status"] not in ("external_candidate", "idea"):
            raise PromotionError("un candidato nuevo debe comenzar en external_candidate o idea")
        return
    old_status, new_status = previous[-1]["status"], new["status"]
    if old_status in TERMINAL_STATES:
        raise PromotionError("%s es terminal; no admite transiciones" % old_status)
    if new_status in TERMINAL_STATES or new_status == old_status:
        return
    if old_status in ("external_candidate", "idea"):
        if new_status != "technically_valid":
            raise PromotionError("transicion prohibida: %s -> %s" % (old_status, new_status))
        return
    old_rank, new_rank = _STATE_RANK[old_status], _STATE_RANK[new_status]
    if new_rank < old_rank:
        raise PromotionError("regresion de estado prohibida: %s -> %s" % (old_status, new_status))
    if new_rank != old_rank + 1:
        raise PromotionError("salto de gate prohibido: %s -> %s" % (old_status, new_status))

def append_record(path, record: Mapping) -> dict:
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
    if not isinstance(candidate_id, str) or not candidate_id:
        raise PromotionError("candidate_id debe ser texto no vacio")
    matches = [r for r in load_registry(path) if r["candidate_id"] == candidate_id]
    return matches[-1]["status"] if matches else None
