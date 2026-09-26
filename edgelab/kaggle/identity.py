"""Identidad inmutable de la corrida (Contrato Kaggle v2).

El contrato enumera los campos minimos que toda ejecucion debe guardar. Este
modulo los construye y los verifica contra bytes reales, porque el contrato
tambien dice: "la mera presencia del campo no alcanza".

Extra propio de EdgeLab: `git_blob_sha1` reproduce el hash de blob de git
("blob <len>\\0" + bytes) para que la identidad del codigo que corrio en Kaggle
sea comparable con `git ls-files -s` del repo sin necesidad de git dentro del
notebook. Es el mismo mecanismo con el que se cerro la identidad de los kernels
en la replica del auditor P-16.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime, timezone

CHUNK = 1 << 20


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(CHUNK), b""):
            h.update(blk)
    return h.hexdigest()


def git_blob_sha1(path: str) -> str:
    data = open(path, "rb").read()
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(obj) -> str:
    """Hash canonico de un objeto JSON (claves ordenadas, sin espacios)."""
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return sha256_bytes(payload)


def pip_freeze_sha256() -> tuple[str, int]:
    """Hash del pip freeze y cantidad de paquetes. Sin red."""
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pip", "freeze", "--disable-pip-version-check"],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        ).stdout
    except Exception as exc:  # pragma: no cover
        return f"UNAVAILABLE:{type(exc).__name__}", 0
    lines = sorted(l.strip() for l in out.splitlines() if l.strip())
    return sha256_bytes("\n".join(lines).encode()), len(lines)


def environment_manifest() -> dict:
    """environment_manifest del contrato: imagen, paquetes, threads y seeds."""
    freeze_sha, n_pkgs = pip_freeze_sha256()
    env_keys = (
        "KAGGLE_KERNEL_RUN_TYPE",
        "KAGGLE_DOCKER_IMAGE",
        "KAGGLE_URL_BASE",
        "KAGGLE_DATA_PROXY_PROJECT",
        "CPU_COUNT",
    )
    return {
        "python_version": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "cpu_affinity": len(os.sched_getaffinity(0))
        if hasattr(os, "sched_getaffinity")
        else None,
        "hostname_sha256": sha256_bytes(socket.gethostname().encode())[:16],
        "pip_freeze_sha256": freeze_sha,
        "pip_packages": n_pkgs,
        "thread_env": {
            k: os.environ.get(k)
            for k in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
                "POLARS_MAX_THREADS",
            )
        },
        "kaggle_env": {k: os.environ.get(k) for k in env_keys},
        "internet_expected": False,
    }


def code_identity(module_paths: dict) -> dict:
    """{nombre: path} -> {nombre: {blob_sha1, sha256, bytes}}."""
    out = {}
    for name, path in sorted(module_paths.items()):
        try:
            out[name] = {
                "path": path,
                "bytes": os.path.getsize(path),
                "git_blob_sha1": git_blob_sha1(path),
                "sha256": sha256_file(path),
            }
        except OSError as exc:
            out[name] = {"path": path, "error": f"{type(exc).__name__}: {exc}"}
    return out


def imported_module_paths(prefix: str = "edgelab") -> dict:
    """Paths de todos los modulos importados bajo `prefix` (identidad real)."""
    out = {}
    for name, mod in sorted(sys.modules.items()):
        if not name.startswith(prefix):
            continue
        path = getattr(mod, "__file__", None)
        if path and os.path.exists(path):
            out[name] = path
    return out


CONTRACT_FIELDS = (
    "dataset_id",
    "dataset_schema_version",
    "code_commit",
    "code_dirty",
    "builder_id",
    "source_dataset_sha256",
    "feature_set_id",
    "target_set_id",
    "fold_plan_id",
    "cutoff_policy_id",
    "created_at_utc",
    "manifest_sha256",
    "calendar_manifest_sha256",
    "roll_schedule_sha256",
    "feature_manifest_sha256",
    "target_manifest_sha256",
    "fold_manifest_sha256",
    "environment_manifest_sha256",
)


def build_run_manifest(
    *,
    notebook_id: str,
    stage: str,
    fields: dict | None = None,
    extra: dict | None = None,
) -> dict:
    """run_manifest.json con los campos del contrato.

    Los campos aun no aplicables se declaran explicitamente como
    "NOT_APPLICABLE_<stage>" en vez de omitirse: el contrato exige que toda
    identidad este declarada, y una omision silenciosa es indistinguible de un
    olvido.
    """
    env = environment_manifest()
    code = code_identity(imported_module_paths())
    fields = dict(fields or {})
    manifest = {
        "notebook_id": notebook_id,
        "stage": stage,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment_manifest": env,
        "environment_manifest_sha256": sha256_json(env),
        "code_identity": code,
        "code_identity_sha256": sha256_json(code),
    }
    for key in CONTRACT_FIELDS:
        if key in fields:
            manifest[key] = fields.pop(key)
        elif key not in manifest:
            manifest[key] = f"NOT_APPLICABLE_{stage}"
    manifest.update(fields)
    if extra:
        manifest["extra"] = extra
    manifest["manifest_sha256"] = sha256_json(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    )
    return manifest


def write_json(path: str, obj: dict) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    payload = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(payload + "\n")
    return sha256_bytes((payload + "\n").encode())
