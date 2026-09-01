"""Fail-closed execution envelope for EdgeLab jobs running on Kaggle/cloud.

This module does not implement a research kernel. It verifies the frozen code
identity and physically pre-holdout input package, executes one argv without a
shell, and emits a hash-bound downloadable evidence bundle.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHUNK = 1 << 20
SCHEMA = "edgelab_kaggle_frozen_execution_v1"
PACKAGE_SCHEMA = "edgelab_kaggle_research_package_v1"
FROZEN_STATUS = "FROZEN_PREFLIGHT_READY"
DRAFT_STATUS = "DRAFT_TEMPLATE_NOT_EXECUTABLE"


class KaggleContractError(RuntimeError):
    def __init__(self, message: str, label: str = "ABSTAIN_KAGGLE_CONTRACT") -> None:
        super().__init__(message)
        self.label = label


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise KaggleContractError(f"invalid or missing JSON: {path}") from exc
    if not isinstance(value, dict):
        raise KaggleContractError(f"JSON root must be an object: {path}")
    return value


def atomic_write_json(path: Path, value: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False
    ) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(raw, encoding="utf-8", newline="\n")
    os.replace(tmp, path)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_hex64(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(c in "0123456789abcdef" for c in value)


def _safe_path(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not relative:
        raise KaggleContractError(f"unsafe relative path: {relative!r}")
    root = root.resolve()
    candidate = (root / rel).resolve()
    if not candidate.is_relative_to(root):
        raise KaggleContractError(f"path escapes root: {relative!r}")
    return candidate


def load_execution_spec(path: Path) -> dict:
    spec = load_json(path)
    if spec.get("schema_version") != SCHEMA:
        raise KaggleContractError("unsupported Kaggle execution spec schema")
    if spec.get("status") not in {DRAFT_STATUS, FROZEN_STATUS}:
        raise KaggleContractError("invalid Kaggle execution spec status")
    if spec.get("north_star_sha256") != "d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1":
        raise KaggleContractError("North Star binding mismatch")
    execution = spec.get("execution") or {}
    argv = execution.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
        raise KaggleContractError("execution.argv must be a non-empty string array")
    if execution.get("shell") is not False:
        raise KaggleContractError("shell execution is forbidden")
    parallel = execution.get("parallelism") or {}
    workers = parallel.get("max_workers")
    if not isinstance(workers, int) or workers < 1:
        raise KaggleContractError("parallelism.max_workers must be >= 1")
    if workers > 1 and not parallel.get("safe_partition_key"):
        raise KaggleContractError("parallel execution requires a frozen safe_partition_key")
    package = spec.get("input_package") or {}
    if package.get("holdout_open_utc_ns") != 1782856800000000000:
        raise KaggleContractError("holdout boundary mismatch")
    if package.get("physical_holdout_absence_required") is not True:
        raise KaggleContractError("physical holdout absence must be required")
    if spec.get("status") == FROZEN_STATUS:
        commit = (spec.get("frozen_code") or {}).get("commit")
        if not isinstance(commit, str) or len(commit) != 40:
            raise KaggleContractError("frozen spec requires a full 40-character commit")
        if not _is_hex64(package.get("manifest_sha256")):
            raise KaggleContractError("frozen spec requires input package file SHA-256")
        if (spec.get("authorization") or {}).get("run_capability") is not True:
            raise KaggleContractError("frozen status requires explicit run capability")
    return spec


def git_state(repo_root: Path) -> dict:
    def run(*args: str) -> str | None:
        proc = subprocess.run(
            ["git", *args], cwd=repo_root, text=True, capture_output=True, check=False
        )
        return proc.stdout.strip() if proc.returncode == 0 else None

    commit = run("rev-parse", "HEAD")
    status = run("status", "--porcelain", "--untracked-files=all")
    return {
        "available": commit is not None,
        "commit": commit,
        "branch": run("branch", "--show-current") or "",
        "dirty": status is None or bool(status),
    }


def resource_snapshot() -> dict:
    mem_kib = None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                mem_kib = int(line.split()[1])
                break
    except OSError:
        pass
    disk = shutil.disk_usage("/kaggle/working" if Path("/kaggle/working").exists() else ".")
    affinity = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None
    return {
        "python": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
        "cpu_affinity": affinity,
        "memory_total_kib": mem_kib,
        "working_disk_total_bytes": disk.total,
        "working_disk_free_bytes": disk.free,
        "thread_env": {
            key: os.environ.get(key)
            for key in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
                "POLARS_MAX_THREADS",
            )
        },
    }


def verify_package_manifest(
    manifest_path: Path,
    data_dir: Path,
    *,
    expected_file_sha256: str | None = None,
    holdout_open_utc_ns: int = 1782856800000000000,
) -> dict:
    if expected_file_sha256 and sha256_file(manifest_path) != expected_file_sha256:
        raise KaggleContractError("input package manifest file SHA-256 mismatch")
    manifest = load_json(manifest_path)
    if manifest.get("schema_version") != PACKAGE_SCHEMA:
        raise KaggleContractError("unsupported input package manifest schema")
    payload = manifest.get("payload_sha256")
    body = {k: v for k, v in manifest.items() if k != "payload_sha256"}
    if not _is_hex64(payload) or canonical_sha256(body) != payload:
        raise KaggleContractError("input package manifest payload hash mismatch")
    if manifest.get("holdout_open_utc_ns") != holdout_open_utc_ns:
        raise KaggleContractError("input package holdout boundary mismatch")
    if manifest.get("research_dataset_holdout_present") is not False:
        raise KaggleContractError("research package does not certify physical holdout absence")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise KaggleContractError("input package contains no declared files")
    seen: set[str] = set()
    verified = []
    for record in files:
        if not isinstance(record, dict):
            raise KaggleContractError("invalid input package file record")
        rel = record.get("file")
        if not isinstance(rel, str) or rel in seen:
            raise KaggleContractError("missing or duplicate input package file")
        seen.add(rel)
        path = _safe_path(data_dir, rel)
        if not path.is_file() or path.is_symlink():
            raise KaggleContractError(f"missing or non-regular input: {rel}")
        actual_bytes = path.stat().st_size
        actual_sha = sha256_file(path)
        if actual_bytes != record.get("bytes"):
            raise KaggleContractError(f"input byte-size mismatch: {rel}")
        if actual_sha != record.get("sha256"):
            raise KaggleContractError(f"input SHA-256 mismatch: {rel}")
        max_ns = record.get("ts_max_utc_ns")
        if not isinstance(max_ns, int) or max_ns >= holdout_open_utc_ns:
            raise KaggleContractError(f"input overlaps or cannot prove holdout boundary: {rel}")
        verified.append({"file": rel, "bytes": actual_bytes, "sha256": actual_sha})
    return {
        "manifest_file_sha256": sha256_file(manifest_path),
        "manifest_payload_sha256": payload,
        "verified_files": verified,
        "verified_file_count": len(verified),
        "verified_bytes": sum(x["bytes"] for x in verified),
        "physical_holdout_absence": True,
    }


def require_authorized(
    spec: dict, *, authorization_token: str | None, expected_commit: str, state: dict
) -> None:
    if spec.get("status") != FROZEN_STATUS:
        raise KaggleContractError("execution spec is not frozen")
    frozen = spec["frozen_code"]["commit"]
    if expected_commit != frozen:
        raise KaggleContractError("--expected-commit differs from frozen commit")
    if not state.get("available") or state.get("commit") != frozen:
        raise KaggleContractError("actual Git HEAD differs from frozen commit")
    if state.get("dirty"):
        raise KaggleContractError("dirty worktree")
    auth = spec.get("authorization") or {}
    if auth.get("run_capability") is not True:
        raise KaggleContractError("run capability is disabled")
    if not authorization_token or authorization_token != auth.get("run_token"):
        raise KaggleContractError("missing or invalid campaign authorization token")


def render_argv(argv: list[str], values: dict[str, str]) -> list[str]:
    out = []
    for item in argv:
        rendered = item
        for key, value in values.items():
            rendered = rendered.replace("{" + key + "}", value)
        if "{" in rendered or "}" in rendered:
            raise KaggleContractError(f"unresolved argv placeholder: {rendered}")
        out.append(rendered)
    return out


def build_artifact_manifest(output_dir: Path, provenance: dict) -> dict:
    output_dir = output_dir.resolve()
    records = []
    for path in sorted(output_dir.rglob("*"), key=lambda p: p.as_posix()):
        if path.is_symlink():
            raise KaggleContractError(f"symlink forbidden in output: {path}")
        if not path.is_file():
            continue
        rel = path.relative_to(output_dir).as_posix()
        if rel in {"artifact_manifest.json", "output.zip", "output.zip.sha256"}:
            continue
        records.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "edgelab_kaggle_artifact_manifest_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance,
        "files": records,
        "file_count": len(records),
        "total_bytes": sum(x["bytes"] for x in records),
    }
    manifest["payload_sha256"] = canonical_sha256(manifest)
    atomic_write_json(output_dir / "artifact_manifest.json", manifest)
    return manifest


def deterministic_zip(output_dir: Path, archive_path: Path) -> dict:
    output_dir = output_dir.resolve()
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = archive_path.with_suffix(archive_path.suffix + ".tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(output_dir.rglob("*"), key=lambda p: p.as_posix()):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(output_dir).as_posix()
            if path.resolve() in {archive_path.resolve(), tmp.resolve()}:
                continue
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            with path.open("rb") as src, zf.open(info, "w") as dst:
                shutil.copyfileobj(src, dst, length=CHUNK)
    os.replace(tmp, archive_path)
    digest = sha256_file(archive_path)
    checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    checksum_path.write_text(f"{digest}  {archive_path.name}\n", encoding="utf-8", newline="\n")
    return {"archive": str(archive_path), "bytes": archive_path.stat().st_size, "sha256": digest}
