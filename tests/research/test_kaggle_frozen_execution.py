from __future__ import annotations

import json
from pathlib import Path

import pytest

from edgelab.kaggle.execution import (
    DRAFT_STATUS,
    KaggleContractError,
    atomic_write_json,
    canonical_sha256,
    load_execution_spec,
    render_argv,
    verify_package_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "specs/kaggle_frozen_execution_v1.template.json"


def test_template_is_non_executable_and_has_required_firewalls():
    spec = load_execution_spec(TEMPLATE)
    assert spec["status"] == DRAFT_STATUS
    assert spec["authorization"]["run_capability"] is False
    assert spec["input_package"]["physical_holdout_absence_required"] is True
    assert not any(spec["firewalls"].values())
    assert spec["execution"]["shell"] is False
    assert spec["execution"]["parallelism"]["max_workers"] == 1


def _package(tmp_path: Path):
    data = tmp_path / "ticks.parquet"
    data.write_bytes(b"PAR1-edgelab-test")
    import hashlib

    digest = hashlib.sha256(data.read_bytes()).hexdigest()
    manifest = {
        "schema_version": "edgelab_kaggle_research_package_v1",
        "generated_utc": "2026-08-28T00:00:00Z",
        "holdout_open_utc_ns": 1782856800000000000,
        "research_dataset_holdout_present": False,
        "files": [
            {
                "file": data.name,
                "bytes": data.stat().st_size,
                "sha256": digest,
                "ts_max_utc_ns": 1782856799999999999,
            }
        ],
    }
    manifest["payload_sha256"] = canonical_sha256(manifest)
    path = tmp_path / "kaggle_research_package_manifest.json"
    atomic_write_json(path, manifest)
    return data, path


def test_package_verification_is_byte_exact(tmp_path: Path):
    data, manifest = _package(tmp_path)
    result = verify_package_manifest(manifest, tmp_path)
    assert result["verified_file_count"] == 1
    assert result["physical_holdout_absence"] is True
    data.write_bytes(b"changed")
    with pytest.raises(KaggleContractError, match="byte-size mismatch|SHA-256 mismatch"):
        verify_package_manifest(manifest, tmp_path)


def test_package_rejects_holdout_boundary(tmp_path: Path):
    _, manifest_path = _package(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][0]["ts_max_utc_ns"] = 1782856800000000000
    manifest["payload_sha256"] = canonical_sha256(
        {k: v for k, v in manifest.items() if k != "payload_sha256"}
    )
    atomic_write_json(manifest_path, manifest)
    with pytest.raises(KaggleContractError, match="holdout"):
        verify_package_manifest(manifest_path, tmp_path)


def test_package_rejects_path_traversal(tmp_path: Path):
    _, manifest_path = _package(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][0]["file"] = "../ticks.parquet"
    manifest["payload_sha256"] = canonical_sha256(
        {k: v for k, v in manifest.items() if k != "payload_sha256"}
    )
    atomic_write_json(manifest_path, manifest)
    with pytest.raises(KaggleContractError, match="unsafe relative path"):
        verify_package_manifest(manifest_path, tmp_path)


def test_parallelism_requires_frozen_partition_key(tmp_path: Path):
    spec = json.loads(TEMPLATE.read_text())
    spec["execution"]["parallelism"]["max_workers"] = 2
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec))
    with pytest.raises(KaggleContractError, match="safe_partition_key"):
        load_execution_spec(path)


def test_argv_rendering_has_no_unresolved_placeholders():
    rendered = render_argv(
        ["python", "job.py", "--data", "{data_dir}"], {"data_dir": "/x"}
    )
    assert rendered == ["python", "job.py", "--data", "/x"]
    with pytest.raises(KaggleContractError, match="unresolved"):
        render_argv(["{missing}"], {})


def test_legacy_metadata_no_longer_claims_cc0():
    metadata = json.loads((ROOT / "kaggle_dataset/dataset-metadata.json").read_text())
    assert metadata["isPrivate"] is True
    assert metadata["licenses"][0]["name"].lower() not in {"cc0-1.0", "pddl", "odbl-1.0"}
