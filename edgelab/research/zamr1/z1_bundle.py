# -*- coding: utf-8 -*-
"""Fail-closed helpers for the formal ZAMR-1 Z1 bundle.

Runtime/RSS/timestamps of execution are deliberately outside deterministic
identity. Data, plan, source observations and static contract inputs are inside.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

STATIC_INPUTS = {
    "contract.json": "specs/zamr1_structural_contract_v0.json",
    "parameter_registry.json": "specs/zamr1_parameter_registry_v0.json",
    "structural_contract.py": "edgelab/research/zamr1/structural_contract.py",
    "pilot_plan.json": "specs/zamr1_z1_pilot_plan_2026-08-12.json",
}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_source_observation(plan_source: dict, observed: dict, instrument_manifest: dict) -> None:
    """Reject a source whose observed identity differs from the frozen plan."""
    required_plan = ("filename", "sha256", "contract")
    missing = [key for key in required_plan if not plan_source.get(key)]
    if missing:
        raise RuntimeError("SOURCE_PLAN_INCOMPLETE: %s" % missing)
    expected = {
        "filename": plan_source["filename"],
        "sha256": plan_source["sha256"],
        "instrument": instrument_manifest["instrument"],
        "contract": plan_source["contract"],
        "tick_size": float(instrument_manifest["tick_size"]),
    }
    absent = [key for key in expected if key not in observed]
    if absent:
        raise RuntimeError("SOURCE_OBSERVATION_INCOMPLETE: %s" % absent)
    mismatches = {}
    for key, value in expected.items():
        actual = observed[key]
        equal = abs(float(actual) - value) <= 1e-15 if key == "tick_size" else actual == value
        if not equal:
            mismatches[key] = {"expected": value, "observed": actual}
    if mismatches:
        raise RuntimeError("SOURCE_CONTRACT_MISMATCH: %s" % json.dumps(mismatches, sort_keys=True))


def deterministic_identity(*, plan_sha256: str, code_commit: str, sources: list, data_artifacts: dict) -> dict:
    """Return identity payload with no clock, runtime, RSS or host fields."""
    payload = {
        "schema_version": "zamr1_z1_deterministic_identity_v1",
        "plan_sha256": plan_sha256,
        "code_commit": code_commit,
        "sources": sources,
        "data_artifacts": data_artifacts,
    }
    payload["identity_sha256"] = canonical_hash(payload)
    return payload


def materialize_static_bundle(out_dir: Path, repo_root: Path, plan_path: Path) -> dict:
    """Copy the validator inputs required for an offline self-contained audit."""
    out = Path(out_dir)
    root = Path(repo_root)
    out.mkdir(parents=True, exist_ok=True)
    copied = {}
    for target, relative in STATIC_INPUTS.items():
        source = Path(plan_path) if target == "pilot_plan.json" else root / relative
        if not source.is_file():
            raise RuntimeError("BUNDLE_INPUT_MISSING: %s" % source)
        destination = out / target
        shutil.copyfile(source, destination)
        copied[target] = file_hash(destination)
    return copied


def write_hash_ledger(out_dir: Path, names: list[str], ledger_name: str = "hashes.sha256") -> dict:
    """Hash an explicit allowlist. The ledger never hashes itself."""
    out = Path(out_dir)
    if ledger_name in names:
        raise RuntimeError("hash ledger cannot include itself")
    hashes = {}
    for name in sorted(set(names)):
        path = out / name
        if not path.is_file():
            raise RuntimeError("BUNDLE_ARTIFACT_MISSING: %s" % name)
        hashes[name] = file_hash(path)
    (out / ledger_name).write_text(
        "".join("%s  %s\n" % (digest, name) for name, digest in sorted(hashes.items())),
        "utf-8",
    )
    return hashes
