from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from edgelab.kaggle.execution import canonical_sha256
from tools.verify_kaggle_nq_post_upload import (
    PostUploadRehashError,
    verify_post_upload,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path, *, timestamp: int = 100) -> tuple[Path, dict]:
    names = [
        "NQ_09-25_ticks.parquet",
        "NQ_12-25_ticks.parquet",
        "NQ_03-26_ticks.parquet",
        "NQ_06-26_ticks.parquet",
        "NQ_09-26_ticks.parquet",
    ]
    for offset, name in enumerate(names):
        pq.write_table(
            pa.table({"ts_utc_ns": pa.array([timestamp + offset], type=pa.int64())}),
            tmp_path / name,
        )
    registry = tmp_path / "effective_input_registry.json"
    registry.write_text('{"ok":true}\n', encoding="utf-8", newline="\n")
    manifest = {
        "schema_version": "edgelab_kaggle_research_package_v1",
        "files": [{"file": name} for name in names],
        "research_dataset_holdout_present": False,
    }
    manifest["payload_sha256"] = canonical_sha256(manifest)
    manifest_path = tmp_path / "kaggle_research_package_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    payload_names = names + [registry.name, manifest_path.name]
    checksum = tmp_path / "files.sha256"
    checksum.write_text(
        "".join(f"{_sha(tmp_path / name)}  {name}\n" for name in payload_names),
        encoding="utf-8",
        newline="\n",
    )
    parquet_bytes = sum((tmp_path / name).stat().st_size for name in names)
    contract = {
        "owner_identity_reconciled": True,
        "canonical_dataset": {"id": "nicolasbuttaro/edgelab-ticks-nq-preholdout"},
        "remote_payload_files_reported": payload_names + [checksum.name],
        "phase1_canonical_evidence": {
            "files_sha256_self_hash": _sha(checksum),
            "effective_input_registry_sha256": _sha(registry),
            "package_manifest_sha256": _sha(manifest_path),
            "parquet_files": 5,
            "parquet_rows": 5,
            "parquet_bytes": parquet_bytes,
            "maximum_timestamp_utc_ns": timestamp + 4,
            "holdout_open_utc_ns": timestamp + 10,
        },
    }
    return tmp_path, contract


def test_post_upload_rehash_passes_and_starts_no_science(tmp_path: Path):
    data_dir, contract = _fixture(tmp_path)
    result = verify_post_upload(data_dir, contract)
    assert result["status"] == "PASS_POST_UPLOAD_BYTE_REHASH"
    assert result["verified_payload_count"] == 7
    assert result["parquet_rows"] == 5
    assert result["physical_holdout_absence"] is True
    assert result["scientific_execution_started"] is False


def test_post_upload_rehash_rejects_payload_mutation(tmp_path: Path):
    data_dir, contract = _fixture(tmp_path)
    (data_dir / "effective_input_registry.json").write_text("changed")
    with pytest.raises(PostUploadRehashError, match="payload SHA-256 mismatch"):
        verify_post_upload(data_dir, contract)


def test_post_upload_rehash_rejects_checksum_line_ending_change(tmp_path: Path):
    data_dir, contract = _fixture(tmp_path)
    checksum = data_dir / "files.sha256"
    checksum.write_bytes(checksum.read_bytes().replace(b"\n", b"\r\n"))
    with pytest.raises(PostUploadRehashError, match="self-hash mismatch"):
        verify_post_upload(data_dir, contract)


def test_post_upload_rehash_rejects_holdout_boundary(tmp_path: Path):
    data_dir, contract = _fixture(tmp_path, timestamp=100)
    contract["phase1_canonical_evidence"]["holdout_open_utc_ns"] = 104
    with pytest.raises(PostUploadRehashError, match="holdout boundary"):
        verify_post_upload(data_dir, contract)


def test_post_upload_rehash_rejects_unexpected_file(tmp_path: Path):
    data_dir, contract = _fixture(tmp_path)
    (data_dir / "unexpected.txt").write_text("no")
    with pytest.raises(PostUploadRehashError, match="remote inventory mismatch"):
        verify_post_upload(data_dir, contract)
