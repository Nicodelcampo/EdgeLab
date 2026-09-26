from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pyarrow as pa
import pyarrow.parquet as pq

from .registry import (
    LedgerIntegrityError,
    _read_records,
    append_record,
    canonical_json,
    content_sha256,
    verify_registry,
)
from .schema_validator import validate_record

TYPED_RELATIONS: frozenset[str] = frozenset({
    "DERIVED_FROM",
    "EXPLAINS",
    "CAUSED_BY",
    "MITIGATED_BY",
    "APPLIES_TO",
    "FAILS_UNDER",
    "REQUIRES",
    "SPECIALIZES",
    "GENERALIZES",
    "TRANSFERS_TO",
    "CO_OCCURRED_WITH",
    "USED_IN",
    "HELPED",
    "HARMED",
    "REQUIRES_REAUDIT",
    "OPERATIONALIZED_AS",
    "NORMALIZES",
    "GATES",
    "CONDITIONS",
    "CONFIRMS",
    "DIVERGES_FROM",
    "REDUNDANT_WITH",
    "COMPLEMENTS",
    "VERSION_OF",
    "SAME_WORK_DIFFERENT_VERSION",
    # Legacy core relations
    "DEPENDS_ON",
    "MEASURED_BY",
    "IMPLEMENTED_BY",
    "TESTED_BY",
    "SUPPORTED_BY",
    "CONTRADICTED_BY",
    "REPLICATED_BY",
    "INVALIDATED_BY",
    "SUPERSEDES",
})


class TypedRegistryError(ValueError):
    """Raised when typed relation, precedence or evidentiary rules are violated."""


@dataclass(frozen=True)
class TypedEdge:
    edge_id: str
    source_id: str
    target_id: str
    relation: str
    source_record_id: str
    status: str = "PROPOSED"

    def __post_init__(self) -> None:
        if self.relation not in TYPED_RELATIONS:
            raise TypedRegistryError(f"Unsupported typed relation: {self.relation}")
        if self.source_id == self.target_id:
            raise TypedRegistryError("Self-referential edges are forbidden")


def append_typed_record(
    path: str | Path,
    *,
    record_type: str,
    record_id: str,
    payload: dict[str, Any],
    recorded_at_utc: str,
    validate: bool = True,
) -> dict[str, Any]:
    """Validate schema and policy before appending to the hash-chained ledger."""
    if validate:
        # Schema validation
        validate_record(record_type, payload)

        # Evidentiary policy: LLM proposals are never acceptable as evidence
        if record_type == "causal_hypothesis":
            if payload.get("source_type") == "LLM_PROPOSAL":
                if payload.get("is_proposal_not_evidence") is not True:
                    raise TypedRegistryError("LLM proposal must have is_proposal_not_evidence=True")
                if payload.get("status") in {"CORROBORATED", "SUPPORTED"}:
                    raise TypedRegistryError("LLM proposal cannot be self-promoted to evidence")

    return append_record(
        path,
        record_type=record_type,
        record_id=record_id,
        payload=payload,
        recorded_at_utc=recorded_at_utc,
    )


def project_to_json(ledger_path: str | Path, out_path: str | Path) -> dict[str, Any]:
    """Build a deterministic JSON projection from the canonical hash-chained ledger."""
    ledger_p = Path(ledger_path)
    out_p = Path(out_path)
    verification = verify_registry(ledger_p)
    if not verification["valid"]:
        raise LedgerIntegrityError("Cannot project an invalid ledger")

    records = _read_records(ledger_p)
    projection_data = {
        "source_ledger_hash": verification["head_hash"],
        "record_count": len(records),
        "records": records,
    }
    content_str = canonical_json(projection_data)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(content_str, encoding="utf-8")
    return {
        "record_count": len(records),
        "head_hash": verification["head_hash"],
        "projection_sha256": hashlib.sha256(content_str.encode("utf-8")).hexdigest(),
    }


def project_to_parquet_zstd(ledger_path: str | Path, out_path: str | Path) -> dict[str, Any]:
    """Build a reconstructible Parquet projection compressed with ZSTD from the canonical ledger."""
    ledger_p = Path(ledger_path)
    out_p = Path(out_path)
    verification = verify_registry(ledger_p)
    if not verification["valid"]:
        raise LedgerIntegrityError("Cannot project an invalid ledger")

    records = _read_records(ledger_p)
    record_ids = [r["record_id"] for r in records]
    record_types = [r["record_type"] for r in records]
    recorded_at = [r["recorded_at_utc"] for r in records]
    prev_hashes = [r.get("previous_record_hash") or "" for r in records]
    record_hashes = [r["record_hash"] for r in records]
    payload_jsons = [canonical_json(r["payload"]) for r in records]

    table = pa.Table.from_arrays(
        [
            pa.array(record_ids, type=pa.string()),
            pa.array(record_types, type=pa.string()),
            pa.array(recorded_at, type=pa.string()),
            pa.array(prev_hashes, type=pa.string()),
            pa.array(record_hashes, type=pa.string()),
            pa.array(payload_jsons, type=pa.string()),
        ],
        names=[
            "record_id",
            "record_type",
            "recorded_at_utc",
            "previous_record_hash",
            "record_hash",
            "payload_json",
        ],
    )

    out_p.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, str(out_p), compression="zstd")

    file_bytes = out_p.read_bytes()
    return {
        "record_count": len(records),
        "head_hash": verification["head_hash"],
        "file_size_bytes": len(file_bytes),
        "parquet_sha256": hashlib.sha256(file_bytes).hexdigest(),
    }


def read_parquet_projection(parquet_path: str | Path) -> list[dict[str, Any]]:
    """Read a Parquet projection and reconstruct the canonical records."""
    table = pq.read_table(str(parquet_path))
    records = []
    pydict = table.to_pydict()
    for i in range(table.num_rows):
        rec = {
            "record_id": pydict["record_id"][i],
            "record_type": pydict["record_type"][i],
            "recorded_at_utc": pydict["recorded_at_utc"][i],
            "previous_record_hash": pydict["previous_record_hash"][i] or None,
            "record_hash": pydict["record_hash"][i],
            "payload": json.loads(pydict["payload_json"][i]),
        }
        records.append(rec)
    return records


def validate_synthesis_promotion(synthesis_payload: dict[str, Any]) -> None:
    """A synthesis with unresolved conflict cannot be promoted."""
    if synthesis_payload.get("has_unresolved_conflicts") is True:
        if synthesis_payload.get("can_promote") is True or synthesis_payload.get("status") == "ACCEPTED":
            raise TypedRegistryError("Cannot promote a synthesis with unresolved conflicts")
