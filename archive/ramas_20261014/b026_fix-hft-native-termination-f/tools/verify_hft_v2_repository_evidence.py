#!/usr/bin/env python3
"""Verify repository-side consistency of the HFT V2 certification evidence.

This deliberately does not claim to re-hash the local-only SQLite. It verifies
that the committed manifest, machine-readable outputs, code hashes and
arithmetic agree with each other on every platform.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/research/HFT_V2_NATIVE_TERMINATION_PROVENANCE_MANIFEST.json"
PARITY = ROOT / "artifacts/paridad_hftzones_nq_v2_exact_certified.json"
PREFLIGHT = ROOT / "artifacts/hft_v2_native_preflight_validation.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _hashes(path: Path) -> tuple[str, str]:
    lf = path.read_bytes().replace(b"\r\n", b"\n")
    return (
        hashlib.sha256(lf).hexdigest(),
        hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest(),
    )


def verify() -> dict:
    manifest = _load(MANIFEST)
    parity = _load(PARITY)
    preflight = _load(PREFLIGHT)
    errors: list[str] = []

    boundary = 1782856800000000000
    verdict = manifest["certification_verdict"]
    provenance = manifest["provenance_adjudication"]
    replay = manifest["export_replay_target"]
    ledger = manifest["input_tick_ledger"]

    if provenance["holdout_start_ns"] != boundary:
        errors.append("manifest holdout boundary mismatch")
    if preflight.get("holdout_boundary_ts_ns") != boundary:
        errors.append("preflight holdout boundary missing or mismatched")
    if preflight.get("holdout_ticks") != 0 or preflight.get("holdout_zones") != 0:
        errors.append("preflight reports holdout contamination")
    if replay["sqlite_sha256_at_close"] != replay["sqlite_sha256_post_python"]:
        errors.append("SQLite pre/post Python hashes differ")
    if replay["sqlite_sha256_at_close"] != replay["preservation_copy_sha256"]:
        errors.append("SQLite preservation hash differs")
    if ledger["ledger_reconciliation"]["sessions_20260602_to_20260612_ticks"] + ledger["ledger_reconciliation"]["session_20260601_ticks"] != ledger["total_rows_actual"]:
        errors.append("tick ledger arithmetic mismatch")
    if parity["fields_compared_per_zone"] * parity["matched_exact_count"] != parity["fields_compared_total"]:
        errors.append("field comparison arithmetic mismatch")
    if parity["fields_compared_total"] != verdict["fields_compared_total"]:
        errors.append("manifest/parity field total mismatch")
    if parity["total_nt8_zones"] != preflight["zone_count"]:
        errors.append("parity/preflight zone count mismatch")
    if parity["total_nt8_zones"] != parity["total_python_zones"] or parity["matched_diffs_count"] != 0:
        errors.append("parity result is not exact")

    specs = manifest["python_comparator"]["files"]
    for spec in specs:
        lf_hash, crlf_hash = _hashes(ROOT / spec["path"])
        if lf_hash != spec["repository_lf_sha256"]:
            errors.append(f"LF hash mismatch: {spec['path']}")
        if crlf_hash != spec["executed_windows_crlf_sha256"]:
            errors.append(f"CRLF hash mismatch: {spec['path']}")

    return {
        "status": "PASS_REPOSITORY_EVIDENCE_CONSISTENCY" if not errors else "FAIL_REPOSITORY_EVIDENCE_CONSISTENCY",
        "is_pass": not errors,
        "errors": errors,
        "scope": "COMMITTED_EVIDENCE_ONLY_LOCAL_SQLITE_BYTES_NOT_PRESENT_IN_GIT",
    }


def main() -> int:
    result = verify()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["is_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
