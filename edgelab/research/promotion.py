"""Registro append-only y fail-closed de promociones de candidatos.

G2 exige una decisión canónica ligada a campaña/run/config y doble autorización
explícita: hash del contrato y hash AST de la implementación DSR. Ambas
allowlists permanecen vacías hasta aprobación humana separada.
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
    "PromotionError",
    "RegistryIntegrityError",
    "PROMOTION_STATES",
    "G2_REQUIRED_GATES",
    "APPROVED_G2_CONTRACT_SHA256S",
    "APPROVED_G2_IMPLEMENTATION_SHA256S",
    "DEFAULT_REGISTRY_PATH",
    "validate_record",
    "load_registry",
    "append_record",
    "current_status",
]

PROMOTION_STATES = (
    "external_candidate",
    "idea",
    "technically_valid",
    "exploratory_candidate",
    "statistically_supported",
    "economically_viable",
    "holdout_confirmed",
    "paper_validated",
    "live_candidate",
)
TERMINAL_STATES = ("failed", "retired")
_STATE_RANK = {name: index for index, name in enumerate(PROMOTION_STATES)}
_G2_MIN_RANK = _STATE_RANK["statistically_supported"]
APPROVED_G2_CONTRACT_SHA256S = frozenset()
APPROVED_G2_IMPLEMENTATION_SHA256S = frozenset()
_REPO = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = str(_REPO / "docs" / "promotion_registry.jsonl")
_SYSTEM_FIELDS = {"previous_digest", "record_digest"}


class PromotionError(RuntimeError):
    pass


class RegistryIntegrityError(PromotionError):
    pass


def _canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(record):
    payload = {key: value for key, value in record.items() if key != "record_digest"}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _required_text(mapping, field, where):
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PromotionError("%s: `%s` debe ser texto no vacío" % (where, field))
    return value


def _utc_timestamp(value, where):
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise PromotionError(
            "%s: `recorded_utc` no es ISO-8601 válido" % where
        ) from exc
    if (
        timestamp.tzinfo is None
        or timestamp.utcoffset() is None
        or timestamp.utcoffset().total_seconds() != 0
    ):
        raise PromotionError("%s: `recorded_utc` debe declarar UTC" % where)


def _validate_g2(decision, row, where):
    if not isinstance(decision, Mapping):
        raise PromotionError(
            "%s: `validation_decision` debe ser un objeto" % where
        )
    decision_where = where + ".validation_decision"
    try:
        rebuilt = validate_decision_dict(dict(decision))
    except G2DecisionError as exc:
        raise PromotionError(
            "%s: decisión G2 canónica inválida: %s" % (decision_where, exc)
        ) from exc
    if not rebuilt.passed:
        raise PromotionError("%s: la decisión G2 canónica no aprobó" % decision_where)
    contract_sha = rebuilt.contract_sha256.lower()
    implementation_sha = rebuilt.dsr_evidence.implementation_sha256.lower()
    if contract_sha not in APPROVED_G2_CONTRACT_SHA256S:
        raise PromotionError(
            "%s: contrato G2 no aprobado `%s`; promociones congeladas"
            % (where, contract_sha)
        )
    if implementation_sha not in APPROVED_G2_IMPLEMENTATION_SHA256S:
        raise PromotionError(
            "%s: implementación G2 no aprobada `%s`; promociones congeladas"
            % (where, implementation_sha)
        )
    for field in ("campaign_id", "run_id", "config_id"):
        if getattr(rebuilt, field) != row[field]:
            raise PromotionError(
                "%s: `%s` no coincide entre promotion record y decisión G2"
                % (where, field)
            )


def validate_record(record, *, allow_system_fields=True):
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
    references = row.get("evidence_refs")
    if not isinstance(references, list) or any(
        not isinstance(reference, str) or not reference for reference in references
    ):
        raise PromotionError(
            "%s: `evidence_refs` debe ser una lista de strings" % where
        )
    if status in _STATE_RANK and _STATE_RANK[status] >= _G2_MIN_RANK:
        for field in ("campaign_id", "run_id", "config_id"):
            _required_text(row, field, where)
        _validate_g2(row.get("validation_decision"), row, where)
    return row


def load_registry(path=DEFAULT_REGISTRY_PATH):
    path = str(path)
    if not os.path.exists(path):
        return []
    rows = []
    previous = None
    with open(path, encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                raise RegistryIntegrityError(
                    "%s:%d: línea vacía en un registro JSONL"
                    % (path, line_number)
                )
            try:
                row = json.loads(line)
                validate_record(row)
            except (json.JSONDecodeError, PromotionError) as exc:
                raise RegistryIntegrityError(
                    "%s:%d: fila inválida: %s" % (path, line_number, exc)
                ) from exc
            if row.get("previous_digest") != previous:
                raise RegistryIntegrityError(
                    "%s:%d: cadena rota" % (path, line_number)
                )
            actual = _digest(row)
            if row.get("record_digest") != actual:
                raise RegistryIntegrityError(
                    "%s:%d: record_digest no coincide" % (path, line_number)
                )
            previous = actual
            rows.append(row)
    return rows


def _check_transition(rows, new):
    if any(row["record_id"] == new["record_id"] for row in rows):
        raise PromotionError("record_id duplicado: %s" % new["record_id"])
    previous = [row for row in rows if row["candidate_id"] == new["candidate_id"]]
    if not previous:
        if new["status"] not in ("external_candidate", "idea"):
            raise PromotionError(
                "un candidato nuevo debe comenzar en external_candidate o idea"
            )
        return
    old_status = previous[-1]["status"]
    new_status = new["status"]
    if old_status in TERMINAL_STATES:
        raise PromotionError("%s es terminal; no admite transiciones" % old_status)
    if new_status in TERMINAL_STATES or new_status == old_status:
        return
    if old_status in ("external_candidate", "idea"):
        if new_status != "technically_valid":
            raise PromotionError(
                "transición prohibida: %s -> %s" % (old_status, new_status)
            )
        return
    old_rank = _STATE_RANK[old_status]
    new_rank = _STATE_RANK[new_status]
    if new_rank < old_rank:
        raise PromotionError(
            "regresión de estado prohibida: %s -> %s" % (old_status, new_status)
        )
    if new_rank != old_rank + 1:
        raise PromotionError(
            "salto de gate prohibido: %s -> %s" % (old_status, new_status)
        )


def append_record(path, record):
    path = str(path)
    row = validate_record(record, allow_system_fields=False)
    rows = load_registry(path)
    _check_transition(rows, row)
    row["previous_digest"] = rows[-1]["record_digest"] if rows else None
    row["record_digest"] = _digest(row)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as stream:
        stream.write(_canonical_json(row) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return row


def current_status(path, candidate_id):
    if not isinstance(candidate_id, str) or not candidate_id:
        raise PromotionError("candidate_id debe ser texto no vacío")
    matches = [
        row for row in load_registry(path) if row["candidate_id"] == candidate_id
    ]
    return matches[-1]["status"] if matches else None
