from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


class LedgerIntegrityError(ValueError):
    """Raised when the append-only evidence ledger fails verification."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _read_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise LedgerIntegrityError(f"Invalid JSON at line {line_number}: {exc}") from exc
    return records


def append_record(
    path: str | Path,
    *,
    record_type: str,
    record_id: str,
    payload: dict[str, Any],
    recorded_at_utc: str,
) -> dict[str, Any]:
    """Append a hash-chained record. Existing bytes are never rewritten."""
    ledger_path = Path(path)
    records = _read_records(ledger_path)
    verification = verify_registry(ledger_path)
    if not verification["valid"]:
        raise LedgerIntegrityError("Refusing to append to an invalid ledger")
    if any(record.get("record_id") == record_id for record in records):
        raise LedgerIntegrityError(f"Duplicate record_id: {record_id}")

    previous_hash = records[-1]["record_hash"] if records else None
    body = {
        "schema_version": "1.0.0",
        "record_type": record_type,
        "record_id": record_id,
        "recorded_at_utc": recorded_at_utc,
        "previous_record_hash": previous_hash,
        "payload": payload,
    }
    record = {**body, "record_hash": content_sha256(body)}
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_json(record) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


def verify_registry(path: str | Path) -> dict[str, Any]:
    ledger_path = Path(path)
    records = _read_records(ledger_path)
    previous_hash = None
    seen_ids: set[str] = set()
    for index, record in enumerate(records):
        record_id = record.get("record_id")
        if record_id in seen_ids:
            return {"valid": False, "records": len(records), "failure_index": index, "reason": "DUPLICATE_RECORD_ID"}
        seen_ids.add(record_id)
        if record.get("previous_record_hash") != previous_hash:
            return {"valid": False, "records": len(records), "failure_index": index, "reason": "BROKEN_PREVIOUS_HASH"}
        body = {key: value for key, value in record.items() if key != "record_hash"}
        expected_hash = content_sha256(body)
        if record.get("record_hash") != expected_hash:
            return {"valid": False, "records": len(records), "failure_index": index, "reason": "RECORD_HASH_MISMATCH"}
        previous_hash = expected_hash
    return {"valid": True, "records": len(records), "head_hash": previous_hash}
