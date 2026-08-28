#!/usr/bin/env python3
"""Independently verify the uploaded private NQ package before any kernel."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.kaggle.execution import canonical_sha256, load_json, sha256_file
from tools.prepare_kaggle_research_dataset import _extract_ts_ns


class PostUploadRehashError(RuntimeError):
    pass


def _hex64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value
    )


def parse_checksum_file(path: Path) -> dict[str, str]:
    if not path.is_file() or path.is_symlink():
        raise PostUploadRehashError("missing or non-regular files.sha256")
    records: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise PostUploadRehashError(f"invalid checksum line {line_number}")
        digest, name = parts[0].lower(), parts[1].strip().lstrip("*")
        candidate = Path(name)
        if not _hex64(digest):
            raise PostUploadRehashError(f"invalid SHA-256 on line {line_number}")
        if not name or candidate.is_absolute() or len(candidate.parts) != 1 or name in records:
            raise PostUploadRehashError(f"unsafe or duplicate checksum path: {name!r}")
        records[name] = digest
    if not records:
        raise PostUploadRehashError("files.sha256 contains no records")
    return records


def parquet_metrics(path: Path, holdout_open_utc_ns: int) -> dict:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise PostUploadRehashError("pyarrow is required") from exc

    parquet = pq.ParquetFile(path)
    names = set(parquet.schema_arrow.names)
    if "timestamp" in names:
        columns = ["timestamp"]
    elif {"date", "time"}.issubset(names):
        columns = ["date", "time"]
    else:
        raise PostUploadRehashError(f"cannot identify timestamp columns: {path.name}")

    row_count = int(parquet.metadata.num_rows)
    observed_rows = 0
    maximum: int | None = None
    for index in range(parquet.num_row_groups):
        table = parquet.read_row_group(index, columns=columns)
        values = _extract_ts_ns(table)
        observed_rows += len(values)
        if len(values):
            value = int(values.max())
            maximum = value if maximum is None else max(maximum, value)
    if observed_rows != row_count:
        raise PostUploadRehashError(f"row-group count mismatch: {path.name}")
    if row_count < 1 or maximum is None:
        raise PostUploadRehashError(f"empty parquet is forbidden: {path.name}")
    if maximum >= holdout_open_utc_ns:
        raise PostUploadRehashError(f"holdout boundary reached: {path.name}")
    return {
        "file": path.name,
        "rows": row_count,
        "bytes": path.stat().st_size,
        "ts_max_utc_ns": maximum,
    }


def verify_post_upload(data_dir: Path, contract: dict) -> dict:
    data_dir = data_dir.resolve()
    if not data_dir.is_dir():
        raise PostUploadRehashError(f"data directory does not exist: {data_dir}")
    canonical = contract.get("canonical_dataset") or {}
    if contract.get("owner_identity_reconciled") is not True:
        raise PostUploadRehashError("canonical owner is not reconciled")
    if canonical.get("id") != "nicolasbuttaro/edgelab-ticks-nq-preholdout":
        raise PostUploadRehashError("canonical dataset ID mismatch")

    expected_files = contract.get("remote_payload_files_reported")
    if not isinstance(expected_files, list) or not all(
        isinstance(name, str) and name and len(Path(name).parts) == 1
        for name in expected_files
    ):
        raise PostUploadRehashError("invalid expected remote inventory")
    if len(expected_files) != len(set(expected_files)):
        raise PostUploadRehashError("duplicate expected remote file")
    actual_files = sorted(path.name for path in data_dir.iterdir() if path.is_file())
    expected_sorted = sorted(expected_files)
    if actual_files != expected_sorted:
        raise PostUploadRehashError(
            f"remote inventory mismatch: expected={expected_sorted!r} actual={actual_files!r}"
        )

    local = contract.get("local_package") or {}
    checksum_path = data_dir / "files.sha256"
    actual_self_hash = sha256_file(checksum_path)
    if actual_self_hash != local.get("files_sha256_self_hash"):
        raise PostUploadRehashError(
            f"files.sha256 self-hash mismatch: expected={local.get('files_sha256_self_hash')} "
            f"actual={actual_self_hash}"
        )
    checksums = parse_checksum_file(checksum_path)
    expected_hashed = set(expected_files) - {"files.sha256"}
    if set(checksums) != expected_hashed:
        raise PostUploadRehashError("files.sha256 payload inventory mismatch")

    verified = []
    for name in sorted(checksums):
        path = data_dir / name
        actual = sha256_file(path)
        if actual != checksums[name]:
            raise PostUploadRehashError(f"payload SHA-256 mismatch: {name}")
        verified.append({"file": name, "bytes": path.stat().st_size, "sha256": actual})

    registry_hash = sha256_file(data_dir / "effective_input_registry.json")
    if registry_hash != local.get("effective_input_registry_sha256"):
        raise PostUploadRehashError("effective input registry SHA-256 mismatch")
    manifest_path = data_dir / "kaggle_research_package_manifest.json"
    manifest_hash = sha256_file(manifest_path)
    if manifest_hash != local.get("package_manifest_sha256"):
        raise PostUploadRehashError("package manifest SHA-256 mismatch")
    manifest = load_json(manifest_path)
    payload = manifest.get("payload_sha256")
    body = {key: value for key, value in manifest.items() if key != "payload_sha256"}
    if not _hex64(payload) or canonical_sha256(body) != payload:
        raise PostUploadRehashError("package manifest payload hash mismatch")

    holdout = local.get("holdout_open_utc_ns")
    if not isinstance(holdout, int):
        raise PostUploadRehashError("invalid holdout boundary")
    parquet_names = sorted(name for name in expected_files if name.endswith(".parquet"))
    if len(parquet_names) != local.get("parquet_files"):
        raise PostUploadRehashError("parquet file count mismatch")
    metrics = [parquet_metrics(data_dir / name, holdout) for name in parquet_names]
    rows = sum(item["rows"] for item in metrics)
    parquet_bytes = sum(item["bytes"] for item in metrics)
    maximum = max(item["ts_max_utc_ns"] for item in metrics)
    if rows != local.get("parquet_rows"):
        raise PostUploadRehashError(f"parquet row total mismatch: {rows}")
    if parquet_bytes != local.get("parquet_bytes"):
        raise PostUploadRehashError(f"parquet byte total mismatch: {parquet_bytes}")
    if maximum != local.get("maximum_timestamp_utc_ns"):
        raise PostUploadRehashError(f"maximum timestamp mismatch: {maximum}")

    return {
        "schema_version": "edgelab_kaggle_nq_post_upload_rehash_v1",
        "status": "PASS_POST_UPLOAD_BYTE_REHASH",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_dataset_id": canonical["id"],
        "data_dir": str(data_dir),
        "inventory": actual_files,
        "remote_file_count": len(actual_files),
        "files_sha256_self_hash": actual_self_hash,
        "verified_payloads": verified,
        "verified_payload_count": len(verified),
        "parquet_metrics": metrics,
        "parquet_rows": rows,
        "parquet_bytes": parquet_bytes,
        "maximum_timestamp_utc_ns": maximum,
        "holdout_open_utc_ns": holdout,
        "strict_margin_ns": holdout - maximum,
        "physical_holdout_absence": True,
        "scientific_execution_started": False,
        "future_price_path_accessed": False,
        "first_touch_accessed": False,
        "pnl_accessed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument(
        "--contract",
        type=Path,
        default=REPO_ROOT / "specs/kaggle_nq_private_upload_v1.draft.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/kaggle/working/nq_post_upload_rehash.json"),
    )
    args = parser.parse_args(argv)
    try:
        result = verify_post_upload(args.data_dir, load_json(args.contract))
        code = 0
    except Exception as exc:
        result = {
            "schema_version": "edgelab_kaggle_nq_post_upload_rehash_v1",
            "status": "FAIL_CLOSED_POST_UPLOAD_REHASH",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "message": str(exc),
            "scientific_execution_started": False,
        }
        code = 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
