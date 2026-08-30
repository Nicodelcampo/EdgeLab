# -*- coding: utf-8 -*-
"""Reusable logical-identity contract for research event stores.

The physical Parquet hash is transport provenance, not the scientific identity.
Scientific identity is the canonical, typed and sorted row payload governed by a
frozen contract.  This module deliberately knows nothing about instruments,
indicators or outcomes.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping


class EventStoreContractError(ValueError):
    """Fail-closed contract violation with a stable machine label."""

    def __init__(self, message: str, label: str = "ABSTAIN_EVENT_STORE_CONTRACT"):
        super().__init__(message)
        self.label = label


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _field_map(contract: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    fields = contract.get("fields")
    if not isinstance(fields, list) or not fields:
        raise EventStoreContractError("contract.fields must be a non-empty list")
    result: dict[str, Mapping[str, Any]] = {}
    for field in fields:
        if not isinstance(field, Mapping):
            raise EventStoreContractError("each contract field must be an object")
        name = field.get("name")
        kind = field.get("type")
        if not isinstance(name, str) or not name:
            raise EventStoreContractError("field name must be a non-empty string")
        if name in result:
            raise EventStoreContractError(f"duplicate contract field: {name}")
        if kind not in {"str", "int", "float", "bool"}:
            raise EventStoreContractError(f"unsupported type for {name}: {kind}")
        result[name] = field
    return result


def validate_contract(contract: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    fields = _field_map(contract)
    names = set(fields)
    sort_keys = contract.get("sort_keys")
    identity_fields = contract.get("identity_fields")
    identity_column = contract.get("identity_column")
    unique_fields = contract.get("unique_fields")
    for label, values in (("sort_keys", sort_keys), ("identity_fields", identity_fields),
                          ("unique_fields", unique_fields)):
        if not isinstance(values, list) or not values or not all(isinstance(x, str) for x in values):
            raise EventStoreContractError(f"contract.{label} must be a non-empty string list")
        missing = sorted(set(values) - names)
        if missing:
            raise EventStoreContractError(f"contract.{label} references missing fields: {missing}")
    if not isinstance(identity_column, str) or identity_column not in names:
        raise EventStoreContractError("contract.identity_column must reference a declared field")
    if identity_column in identity_fields:
        raise EventStoreContractError("identity column cannot hash itself")
    if fields[identity_column].get("type") != "str" or fields[identity_column].get("nullable", False):
        raise EventStoreContractError("identity column must be a non-nullable string")
    for key in sort_keys:
        if fields[key].get("nullable", False):
            raise EventStoreContractError(f"sort key cannot be nullable: {key}")
    return fields


def _normalize_scalar(value: Any, field: Mapping[str, Any]) -> Any:
    name = str(field["name"])
    kind = str(field["type"])
    nullable = bool(field.get("nullable", False))
    if value is None:
        if nullable:
            return None
        raise EventStoreContractError(f"null in non-nullable field: {name}")
    if kind == "bool":
        if type(value) is not bool:
            raise EventStoreContractError(f"{name} must be bool")
        return value
    if kind == "str":
        if not isinstance(value, str):
            raise EventStoreContractError(f"{name} must be str")
        if field.get("non_empty", False) and not value:
            raise EventStoreContractError(f"{name} must be non-empty")
        return value
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise EventStoreContractError(f"{name} must be an exact int")
        return int(value)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EventStoreContractError(f"{name} must be numeric")
    out = float(value)
    if not math.isfinite(out):
        raise EventStoreContractError(f"{name} must be finite")
    return 0.0 if out == 0.0 else out


def identity_sha256(row: Mapping[str, Any], contract: Mapping[str, Any]) -> str:
    validate_contract(contract)
    fields = list(contract["identity_fields"])
    missing = sorted(set(fields) - set(row))
    if missing:
        raise EventStoreContractError(f"identity source fields missing: {missing}")
    return canonical_sha256({name: row[name] for name in fields})


def stamp_identity(row: Mapping[str, Any], contract: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(row)
    column = str(contract["identity_column"])
    out[column] = identity_sha256(out, contract)
    return normalize_rows([out], contract)[0]


def normalize_rows(rows: Iterable[Mapping[str, Any]], contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = validate_contract(contract)
    expected = set(fields)
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise EventStoreContractError(f"row {index} is not an object")
        present = set(raw)
        missing = sorted(expected - present)
        extra = sorted(present - expected)
        if missing:
            raise EventStoreContractError(f"row {index} missing fields: {missing}")
        if contract.get("exact_columns", True) and extra:
            raise EventStoreContractError(f"row {index} has undeclared fields: {extra}")
        row = {name: _normalize_scalar(raw[name], field) for name, field in fields.items()}
        expected_identity = identity_sha256(row, contract)
        identity_column = str(contract["identity_column"])
        if row[identity_column] != expected_identity:
            raise EventStoreContractError(f"row {index} identity_sha256 mismatch")
        normalized.append(row)

    sort_keys = list(contract["sort_keys"])
    normalized.sort(key=lambda row: tuple(row[key] for key in sort_keys))
    for field in contract["unique_fields"]:
        values = [row[field] for row in normalized]
        if len(values) != len(set(values)):
            raise EventStoreContractError(f"duplicate values in unique field: {field}")
    return normalized


def logical_payload_sha256(rows: Iterable[Mapping[str, Any]], contract: Mapping[str, Any]) -> str:
    return canonical_sha256(normalize_rows(rows, contract))


def validate_logical_equivalence(
    checkpoint_rows: Iterable[Mapping[str, Any]],
    transport_rows: Iterable[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    expected = normalize_rows(checkpoint_rows, contract)
    observed = normalize_rows(transport_rows, contract)
    expected_hash = canonical_sha256(expected)
    observed_hash = canonical_sha256(observed)
    if observed != expected:
        raise EventStoreContractError(
            f"logical payload differs: checkpoints={expected_hash} transport={observed_hash}"
        )
    return {
        "ready": True,
        "logical_identity": "PASS",
        "rows": len(expected),
        "logical_payload_sha256": expected_hash,
        "transport_matches_checkpoints_1to1": True,
    }


def load_checkpoint_rows(directory: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not directory.is_dir():
        raise EventStoreContractError(f"checkpoint directory missing: {directory}")
    files = sorted(directory.glob("*.json"))
    if not files:
        raise EventStoreContractError(f"no checkpoint JSON files in: {directory}")
    rows: list[dict[str, Any]] = []
    metadata: list[dict[str, Any]] = []
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise EventStoreContractError(f"invalid checkpoint JSON: {path.name}") from exc
        events = payload.get("events") if isinstance(payload, dict) else None
        if not isinstance(events, list):
            raise EventStoreContractError(f"checkpoint has no events list: {path.name}")
        rows.extend(events)
        metadata.append({
            "file": path.name,
            "sha256": sha256_file(path),
            "session_id": payload.get("session_id"),
            "n_events": len(events),
            "spec_payload_sha256": payload.get("spec_payload_sha256"),
            "source_data_sha256": payload.get("source_data_sha256"),
        })
    return rows, metadata


def read_parquet_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise EventStoreContractError(f"Parquet missing: {path}")
    try:
        import pyarrow.parquet as pq
        return pq.read_table(path).to_pylist()
    except Exception as exc:
        raise EventStoreContractError(f"Parquet unreadable: {path}") from exc


def validate_parquet_against_rows(
    path: Path,
    checkpoint_rows: Iterable[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    result = validate_logical_equivalence(checkpoint_rows, read_parquet_rows(path), contract)
    return {
        **result,
        "parquet_readable": True,
        "parquet_physical_sha256": sha256_file(path),
        "parquet_matches_checkpoints_1to1": True,
    }
