#!/usr/bin/env python3
"""EdgeLab <-> Google Drive <-> Kaggle local bridge and chunked transfer tool (versión endurecida).

Corre en la PC local (donde viven las credenciales de Kaggle) y atiende pedidos JSON que se dejan en una carpeta sincronizada
con Google Drive (EdgeLab_Bridge/inbox) y devuelve respuestas en outbox. Permite inspeccionar datasets de Kaggle y leer artefactos
grandes en trozos < 9 MB verificados con SHA-256, sin exponer credenciales en el chat ni en Git.

Cambios de seguridad respecto de la versión original (los pedidos del inbox son ENTRADA NO CONFIABLE: cualquiera con acceso de
escritura a la carpeta de Drive, o un modelo manipulado por prompt-injection, puede escribirlos):
  * `request_id` validado (^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$, sin "..") antes de usarlo en rutas: antes permitía path traversal y
    un `shutil.rmtree` fuera del puente.
  * `push_kernel` APAGADO por defecto (--allow-push); aun encendido: siempre privado, sin internet (enable_internet=True se rechaza),
    slug validado y fuentes de datos sólo de owners permitidos (--allow-source-owner).
  * `download_file_chunked` limitado por defecto a archivos de texto chicos (json/md/csv/txt/html, <= 50 MB). Datos binarios
    (Parquet de ticks CME, con licencia que prohíbe redistribuir) requieren --allow-data-download explícito.
  * Las descargas intermedias van a un directorio temporal LOCAL, no dentro de la carpeta sincronizada con Drive.
  * Pedidos de más de 1 MB se rechazan; la respuesta de error no incluye trazas.

Resuelve además R9/K9: normaliza `datasetFiles` vs `files` y reporta paginación/truncamiento explícitos.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping

KAGGLE_API_V1 = "https://www.kaggle.com/api/v1"
KAGGLE_RPC_V1 = "https://api.kaggle.com/v1"
DEFAULT_CHUNK_BYTES = 9_000_000  # 9 MB (< 10 MB Google Drive MCP download limit)
BRIDGE_SCHEMA = "edgelab_kaggle_drive_bridge_v1"
MAX_REQUEST_BYTES = 1_000_000
_REQ_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,49}$")
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./~^-]{0,99}$")          # nunca empieza con "-" (no se cuelan opciones de git)
_PATCH_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\.(patch|diff)$")
MAX_PATCH_BYTES = 5_000_000
MAX_DELTA_BYTES = 20_000_000
DELTA_EXCLUDES = (":(exclude)data", ":(exclude)*.parquet", ":(exclude)*.parq", ":(exclude)*.bundle", ":(exclude)oracles")


class KaggleBridgeError(RuntimeError):
    """Fail-closed error in Kaggle bridge operations."""


@dataclass(frozen=True)
class BridgePolicy:
    """Qué puede hacer el puente. Por defecto: sólo lectura de metadatos y archivos de texto chicos."""
    allow_push: bool = False
    allow_data_download: bool = False
    max_download_bytes: int = 50_000_000
    text_suffixes: tuple = (".json", ".md", ".csv", ".txt", ".html")
    allowed_source_owners: tuple = field(default_factory=tuple)
    repos: dict = field(default_factory=dict)       # nombre lógico -> ruta local de un repo git (acciones git_*)


def sanitize_request_id(value: Any) -> str:
    rid = str(value)
    if not _REQ_ID_RE.match(rid) or ".." in rid:
        raise KaggleBridgeError("request_id inválido (usar letras, números, _ . - ; máx 64; sin '..')")
    return rid


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def load_kaggle_auth_headers(
    env: Mapping[str, str] | None = None,
    kaggle_json_path: Path | None = None,
) -> dict[str, str]:
    """Build Authorization header from env or ~/.kaggle/kaggle.json without logging secrets."""
    env_map = os.environ if env is None else env
    bearer = env_map.get("KAGGLE_API_TOKEN", "").strip()
    if bearer:
        return {"Authorization": f"Bearer {bearer}"}

    username = env_map.get("KAGGLE_USERNAME", "").strip()
    key = env_map.get("KAGGLE_KEY", "").strip()
    if username and key:
        token = base64.b64encode(f"{username}:{key}".encode("utf-8")).decode("ascii")
        return {"Authorization": f"Basic {token}"}

    cfg_path = kaggle_json_path or (Path.home() / ".kaggle" / "kaggle.json")
    if cfg_path.is_file():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise KaggleBridgeError(f"Invalid JSON in {cfg_path}") from exc
        if isinstance(raw, Mapping):
            tok = str(raw.get("token") or "").strip()
            if tok:
                return {"Authorization": f"Bearer {tok}"}
            u = str(raw.get("username") or "").strip()
            k = str(raw.get("key") or "").strip()
            if u and k:
                b64 = base64.b64encode(f"{u}:{k}".encode("utf-8")).decode("ascii")
                return {"Authorization": f"Basic {b64}"}

    raise KaggleBridgeError(
        "Missing Kaggle credentials. Set KAGGLE_API_TOKEN (or KAGGLE_USERNAME/KAGGLE_KEY) "
        "or place your credentials in ~/.kaggle/kaggle.json."
    )


def parse_dataset_ref(ref: str) -> tuple[str, str, int | None]:
    """Parse 'owner/slug' or 'owner/slug/version' strictly."""
    parts = [p.strip() for p in ref.strip().split("/") if p.strip()]
    if len(parts) == 2:
        return parts[0], parts[1], None
    if len(parts) == 3:
        try:
            ver = int(parts[2])
        except ValueError as exc:
            raise KaggleBridgeError(f"Invalid dataset version in {ref!r}") from exc
        if ver <= 0:
            raise KaggleBridgeError(f"Dataset version must be positive in {ref!r}")
        return parts[0], parts[1], ver
    raise KaggleBridgeError(f"Expected 'owner/dataset' or 'owner/dataset/version', got {ref!r}")


def normalize_dataset_files_payload(payload: Any, requested_page_size: int = 100) -> dict[str, Any]:
    """Normalize Kaggle `/datasets/list/<owner>/<slug>` payload (fixes R9/K9 `datasetFiles` vs `files`)."""
    raw_files: list[Any] = []
    next_page_token: str | None = None
    error_message: str | None = None

    if isinstance(payload, Mapping):
        if payload.get("errorMessage"):
            error_message = str(payload["errorMessage"])
        if isinstance(payload.get("datasetFiles"), list):
            raw_files = list(payload["datasetFiles"])
        elif isinstance(payload.get("files"), list):
            raw_files = list(payload["files"])
        tok = payload.get("nextPageToken") or payload.get("next_page_token")
        if tok:
            next_page_token = str(tok)
    elif isinstance(payload, list):
        raw_files = list(payload)
    else:
        raise KaggleBridgeError(f"Unexpected dataset files payload type: {type(payload).__name__}")

    normalized = []
    for item in raw_files:
        if not isinstance(item, Mapping):
            continue
        name = item.get("name") or item.get("fileName") or item.get("ref") or ""
        size = item.get("totalBytes") if "totalBytes" in item else item.get("size")
        normalized.append(
            {
                "name": str(name),
                "totalBytes": int(size) if isinstance(size, (int, float)) else None,
                "creationDate": item.get("creationDate"),
                "description": item.get("description"),
            }
        )

    is_truncated = bool(next_page_token) or (requested_page_size > 0 and len(normalized) >= requested_page_size)
    return {
        "schema": "edgelab_kaggle_file_listing_v1",
        "files": normalized,
        "returned_count": len(normalized),
        "requested_page_size": requested_page_size,
        "next_page_token": next_page_token,
        "is_truncated": is_truncated,
        "exhaustive": not is_truncated and error_message is None,
        "error_message": error_message,
    }


class KaggleClient:
    """Minimal stdlib client for Kaggle REST v1 and RPC endpoints."""

    def __init__(self, auth_headers: Mapping[str, str], timeout_sec: int = 60) -> None:
        self._auth_headers = dict(auth_headers)
        self._timeout = timeout_sec

    def _get_json(self, path: str, params: Mapping[str, str] | None = None) -> Any:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = f"{KAGGLE_API_V1}{path}{query}"
        req = urllib.request.Request(
            url,
            headers={**self._auth_headers, "Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise KaggleBridgeError(f"Kaggle HTTP {exc.code} on {path}: {body}") from exc

    def _rpc_json(self, service: str, method: str, body: Mapping[str, Any]) -> Any:
        url = f"{KAGGLE_RPC_V1}/{service}/{method}"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                **self._auth_headers,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")[:800]
            raise KaggleBridgeError(f"Kaggle RPC {exc.code} on {service}/{method}: {err_body}") from exc

    def search_datasets(self, query: str, max_results: int = 20, sort_by: str = "updated", page: int = 1) -> dict[str, Any]:
        page = max(1, int(page))
        cap = max(1, min(50, int(max_results)))
        data = self._get_json("/datasets/list", {"search": query, "sortBy": sort_by, "page": str(page)})
        items = data if isinstance(data, list) else []
        sliced = items[:cap]
        return {
            "query": query,
            "page": page,
            "max_results": cap,
            "returned_count": len(sliced),
            "potentially_truncated": len(items) >= 20 or len(items) > cap,
            "results": sliced,
        }

    def list_my_datasets(self, query: str | None = None, page: int = 1) -> dict[str, Any]:
        page = max(1, int(page))
        params: dict[str, str] = {"group": "my", "sortBy": "updated", "page": str(page)}
        if query:
            params["search"] = query
        data = self._get_json("/datasets/list", params)
        items = data if isinstance(data, list) else []
        return {
            "group": "my",
            "query": query,
            "page": page,
            "returned_count": len(items),
            "potentially_truncated": len(items) >= 20,
            "results": items,
        }

    def list_dataset_files(self, dataset: str, page_size: int = 100, page_token: str | None = None) -> dict[str, Any]:
        owner, slug, _ = parse_dataset_ref(dataset)
        cap = max(1, min(200, int(page_size)))
        params: dict[str, str] = {"pageSize": str(cap)}
        if page_token:
            params["pageToken"] = page_token
        raw = self._get_json(f"/datasets/list/{urllib.parse.quote(owner)}/{urllib.parse.quote(slug)}", params)
        listing = normalize_dataset_files_payload(raw, requested_page_size=cap)
        listing["dataset"] = f"{owner}/{slug}"
        return listing

    def inspect_dataset(self, dataset: str) -> dict[str, Any]:
        owner, slug, _ = parse_dataset_ref(dataset)
        p = f"/{urllib.parse.quote(owner)}/{urllib.parse.quote(slug)}"
        metadata = self._get_json(f"/datasets/view{p}")
        files_listing = self.list_dataset_files(f"{owner}/{slug}", page_size=200)
        return {
            "dataset": f"{owner}/{slug}",
            "metadata": metadata,
            "files_listing": files_listing,
        }

    def read_dataset_file_preview(self, dataset: str, file_name: str, max_bytes: int = 200_000) -> dict[str, Any]:
        owner, slug, ver = parse_dataset_ref(dataset)
        clean_file = file_name.lstrip("/")
        if not clean_file or ".." in clean_file:
            raise KaggleBridgeError(f"Invalid file path: {file_name!r}")
        cap = max(1, min(500_000, int(max_bytes)))
        params = {"filename": clean_file}
        if ver is not None:
            params["datasetVersionNumber"] = str(ver)
        url = f"{KAGGLE_API_V1}/datasets/download/{urllib.parse.quote(owner)}/{urllib.parse.quote(slug)}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={**self._auth_headers, "Range": f"bytes=0-{cap}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            raw = resp.read(cap + 1)
            ctype = resp.headers.get("content-type", "")
        if len(raw) >= 2 and raw[0] == 0x50 and raw[1] == 0x4B:
            raise KaggleBridgeError("ZIP archive returned; use download_file_chunked for binary/archive files.")
        clipped = raw[:cap]
        return {
            "dataset": dataset,
            "file": clean_file,
            "content_type": ctype,
            "bytes_returned": len(clipped),
            "truncated": len(raw) > cap,
            "content": clipped.decode("utf-8", errors="replace"),
        }

    def download_dataset_file_to_path(self, dataset: str, file_name: str, dest_path: Path) -> dict[str, Any]:
        owner, slug, ver = parse_dataset_ref(dataset)
        clean_file = file_name.lstrip("/")
        if not clean_file or ".." in clean_file:
            raise KaggleBridgeError(f"Invalid file path: {file_name!r}")
        params = {"filename": clean_file}
        if ver is not None:
            params["datasetVersionNumber"] = str(ver)
        url = f"{KAGGLE_API_V1}/datasets/download/{urllib.parse.quote(owner)}/{urllib.parse.quote(slug)}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers=dict(self._auth_headers), method="GET")
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256()
        total = 0
        with urllib.request.urlopen(req, timeout=max(self._timeout, 300)) as resp, dest_path.open("wb") as out_f:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out_f.write(chunk)
                h.update(chunk)
                total += len(chunk)
        return {
            "dataset": dataset,
            "file": clean_file,
            "local_path": str(dest_path),
            "size_bytes": total,
            "sha256": h.hexdigest(),
        }

    def push_kernel(
        self,
        slug: str,
        title: str,
        script_text: str,
        accelerator: str = "cpu",
        dataset_sources: list[str] | None = None,
        kernel_sources: list[str] | None = None,
        enable_internet: bool = False,
    ) -> Any:
        acc = accelerator.lower().strip()
        if acc not in ("cpu", "gpu"):
            raise KaggleBridgeError("accelerator must be 'cpu' or 'gpu'")
        sources = [s.strip() for s in (dataset_sources or []) if s.strip()]
        ksources = [s.strip() for s in (kernel_sources or []) if s.strip()]
        return self._rpc_json(
            "kernels.KernelsApiService",
            "SaveKernel",
            {
                "slug": slug,
                "newTitle": title,
                "text": script_text,
                "language": "python",
                "kernelType": "script",
                "datasetDataSources": sources,
                "kernelDataSources": ksources,
                "competitionDataSources": [],
                "modelDataSources": [],
                "categoryIds": [],
                "isPrivate": True,
                "enableGpu": acc == "gpu",
                "enableTpu": False,
                "enableInternet": bool(enable_internet),
                "sessionTimeoutSeconds": 3600,
            },
        )

    def get_kernel_status(self, owner: str, slug: str, version_label: str | None = None) -> Any:
        payload: dict[str, Any] = {"userName": owner, "kernelSlug": slug}
        if version_label:
            payload["versionLabel"] = version_label
        return self._rpc_json("kernels.KernelsApiService", "GetKernelSessionStatus", payload)

    def get_kernel_output(self, owner: str, slug: str, page_size: int = 50, page_token: str | None = None) -> Any:
        payload: dict[str, Any] = {"userName": owner, "kernelSlug": slug, "pageSize": max(1, min(100, int(page_size)))}
        if page_token:
            payload["pageToken"] = str(page_token)
        return self._rpc_json("kernels.KernelsApiService", "ListKernelSessionOutput", payload)


def split_file_into_drive_chunks(
    source_path: Path,
    out_dir: Path,
    *,
    chunk_size_bytes: int = DEFAULT_CHUNK_BYTES,
    expected_sha256: str | None = None,
    expected_size_bytes: int | None = None,
) -> dict[str, Any]:
    """Verify source_path and split into <9 MB chunks with a SHA256 manifest for Google Drive download."""
    if not source_path.is_file():
        raise KaggleBridgeError(f"Source file does not exist: {source_path}")
    if chunk_size_bytes <= 0 or chunk_size_bytes > 9_500_000:
        raise KaggleBridgeError("chunk_size_bytes must be between 1 and 9_500_000 (to stay under Drive 10 MB limit)")

    actual_size = source_path.stat().st_size
    if expected_size_bytes is not None and actual_size != expected_size_bytes:
        raise KaggleBridgeError(
            f"Size mismatch for {source_path.name}: expected {expected_size_bytes}, got {actual_size}"
        )

    actual_sha = _sha256_file(source_path)
    if expected_sha256 is not None and actual_sha.lower() != expected_sha256.lower():
        raise KaggleBridgeError(
            f"SHA256 mismatch for {source_path.name}: expected {expected_sha256}, got {actual_sha}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    chunks_meta: list[dict[str, Any]] = []
    with source_path.open("rb") as f:
        idx = 0
        while True:
            buf = f.read(chunk_size_bytes)
            if not buf:
                break
            part_name = f"{source_path.name}.part_{idx:04d}.bin"
            part_path = out_dir / part_name
            part_path.write_bytes(buf)
            chunks_meta.append(
                {
                    "index": idx,
                    "filename": part_name,
                    "size_bytes": len(buf),
                    "sha256": _sha256_bytes(buf),
                }
            )
            idx += 1

    manifest = {
        "schema": "edgelab_drive_chunk_manifest_v1",
        "original_filename": source_path.name,
        "total_size_bytes": actual_size,
        "sha256": actual_sha,
        "chunk_size_bytes": chunk_size_bytes,
        "chunk_count": len(chunks_meta),
        "chunks": chunks_meta,
        "created_at_utc": _utc_now_iso(),
    }
    manifest_path = out_dir / f"{source_path.name}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def reassemble_drive_chunks(manifest_path: Path, dest_path: Path) -> dict[str, Any]:
    """Reassemble chunks described by manifest_path and verify both chunk and full-file SHA256."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "edgelab_drive_chunk_manifest_v1":
        raise KaggleBridgeError("Invalid chunk manifest schema")

    base_dir = manifest_path.parent
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")

    full_hash = hashlib.sha256()
    total_written = 0
    with tmp_path.open("wb") as out_f:
        for chunk in manifest.get("chunks", []):
            part_path = base_dir / Path(chunk["filename"]).name   # sólo el nombre: el manifiesto no puede apuntar fuera de su carpeta
            if not part_path.is_file():
                raise KaggleBridgeError(f"Missing chunk file: {part_path}")
            data = part_path.read_bytes()
            if len(data) != chunk["size_bytes"]:
                raise KaggleBridgeError(f"Chunk size mismatch in {part_path.name}")
            if _sha256_bytes(data) != chunk["sha256"]:
                raise KaggleBridgeError(f"Chunk SHA256 mismatch in {part_path.name}")
            out_f.write(data)
            full_hash.update(data)
            total_written += len(data)

    if total_written != manifest["total_size_bytes"]:
        tmp_path.unlink(missing_ok=True)
        raise KaggleBridgeError("Reassembled total size mismatch")
    if full_hash.hexdigest() != manifest["sha256"]:
        tmp_path.unlink(missing_ok=True)
        raise KaggleBridgeError("Reassembled full-file SHA256 mismatch")

    tmp_path.replace(dest_path)
    return {
        "restored_path": str(dest_path),
        "size_bytes": total_written,
        "sha256": full_hash.hexdigest(),
        "chunk_count": len(manifest.get("chunks", [])),
    }


def lookup_pinned_discovery_entry(discovery_json_path: Path, version_ref: str, relative_path: str) -> dict[str, Any]:
    """Resolve an exact (version_ref, relative_path) pin from edgelab/kaggle/discovery.json."""
    doc = json.loads(discovery_json_path.read_text(encoding="utf-8"))
    for ds in doc.get("datasets", []):
        if ds.get("version_ref") == version_ref:
            for f in ds.get("files", []):
                if f.get("path") == relative_path:
                    return {
                        "version_ref": version_ref,
                        "path": relative_path,
                        "size_bytes": int(f["size_bytes"]),
                        "sha256": str(f["sha256"]),
                        "quarantined": bool(f.get("quarantined", False)),
                    }
    raise KaggleBridgeError(f"File {relative_path!r} under {version_ref!r} not found in discovery.json")


def _check_download_allowed(dataset: str, file_name: str, policy: BridgePolicy) -> None:
    if policy.allow_data_download:
        owner = dataset.split("/")[0]
        if owner not in policy.allowed_source_owners:       # con descarga de datos encendida sólo se baja de owners declarados
            raise KaggleBridgeError(f"descarga de datos: owner {owner!r} no permitido (--allow-source-owner)")
        return
    if not file_name.lower().endswith(tuple(policy.text_suffixes)):
        raise KaggleBridgeError(
            "Descarga de archivos binarios/de datos deshabilitada (los Parquet de ticks tienen licencia que prohíbe redistribuir). "
            "Usar --allow-data-download sólo si Nico lo decidió explícitamente."
        )


def _check_push_allowed(params: Mapping[str, Any], policy: BridgePolicy) -> dict[str, Any]:
    if not policy.allow_push:
        raise KaggleBridgeError("push_kernel deshabilitado (ejecuta código en Kaggle con tu cuenta). Encender con --allow-push.")
    raw_slug = str(params["slug"]).strip()
    if "/" in raw_slug:
        owner, kslug = raw_slug.split("/", 1)
        if not policy.allowed_source_owners or owner not in policy.allowed_source_owners or not _SLUG_RE.match(kslug):
            raise KaggleBridgeError("slug inválido")
        slug = f"{owner}/{kslug}"
    else:
        if not _SLUG_RE.match(raw_slug):
            raise KaggleBridgeError("slug inválido")
        slug = f"{policy.allowed_source_owners[0]}/{raw_slug}" if policy.allowed_source_owners else raw_slug
    if bool(params.get("enable_internet", False)):
        raise KaggleBridgeError("enable_internet=True no está permitido por el puente (evita exfiltrar datos privados)")
    sources = [str(s).strip() for s in (params.get("dataset_sources") or []) if str(s).strip()]
    ksources = [str(s).strip() for s in (params.get("kernel_sources") or []) if str(s).strip()]
    for s in sources + ksources:
        owner = s.split("/")[0]
        if owner not in policy.allowed_source_owners:
            raise KaggleBridgeError(f"source {s!r}: owner no permitido (--allow-source-owner)")
    return dict(slug=slug, title=str(params["title"])[:100], script_text=str(params["script"]),
                accelerator=str(params.get("accelerator", "cpu")), dataset_sources=sources,
                kernel_sources=ksources, enable_internet=False)


def _git(repo: Path, *args: str, timeout: int = 120) -> str:
    """Ejecuta git SIN shell y con argumentos ya validados. Devuelve stdout (texto)."""
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise KaggleBridgeError("git falló: " + (r.stderr or r.stdout).decode("utf-8", errors="replace")[:400])
    return r.stdout.decode("utf-8", errors="replace")


def _resolve_repo(params: Mapping[str, Any], policy: BridgePolicy) -> Path:
    name = str(params.get("repo", ""))
    if name not in policy.repos:
        raise KaggleBridgeError(f"repo {name!r} no registrado; disponibles: {sorted(policy.repos)}")
    return Path(policy.repos[name])


def _check_ref(ref: Any) -> str:
    ref = str(ref)
    if not _REF_RE.match(ref) or ".." in ref:
        raise KaggleBridgeError(f"ref inválida: {ref!r}")
    return ref


def git_head_info(repo: Path) -> dict[str, Any]:
    """Sólo lectura: rama, HEAD, ramas locales, estado (nombres, sin contenido) y últimos commits."""
    status = [l for l in _git(repo, "status", "--porcelain").splitlines() if l.strip()]
    refs = _git(repo, "for-each-ref", "--format=%(refname:short)\t%(objectname:short)", "refs/heads").splitlines()[:50]
    log = _git(repo, "log", "-n", "15", "--date=iso", "--format=%H\t%an\t%ad\t%s").splitlines()
    return {"branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip(), "head": _git(repo, "rev-parse", "HEAD").strip(),
            "dirty": bool(status), "status_count": len(status), "status_sample": status[:50],
            "branches": [r.split("\t") for r in refs], "log": [l.split("\t", 3) for l in log]}


def git_export_delta(repo: Path, base: str, head: str, artifact_dir: Path) -> dict[str, Any]:
    """Exporta los commits base..head como parche (format-patch), sin rutas de datos ni binarios de mercado, con tope de tamaño."""
    base, head = _check_ref(base), _check_ref(head)
    text = _git(repo, "format-patch", "--stdout", f"{base}..{head}", "--", ".", *DELTA_EXCLUDES, timeout=300)
    raw = text.encode("utf-8")
    if len(raw) > MAX_DELTA_BYTES:
        raise KaggleBridgeError(f"delta de {len(raw)} bytes supera el tope de {MAX_DELTA_BYTES}")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    out = artifact_dir / "delta.patch"
    out.write_bytes(raw)
    manifest = split_file_into_drive_chunks(out, artifact_dir / "chunks") if len(raw) > DEFAULT_CHUNK_BYTES else None
    return {"repo_range": f"{base}..{head}", "bytes": len(raw), "sha256": _sha256_bytes(raw), "file": "delta.patch",
            "commits": len([l for l in text.splitlines() if l.startswith("From ")]), "chunk_manifest": manifest}


def check_patch(repo: Path, bridge_dir: Path, name: str) -> dict[str, Any]:
    """`git apply --check` de un parche dejado en patches_for_review/. No aplica ni ejecuta nada."""
    if not _PATCH_NAME_RE.match(str(name)):
        raise KaggleBridgeError("nombre de parche inválido (letras, números, _ . - y extensión .patch/.diff)")
    path = bridge_dir / "patches_for_review" / name
    if not path.is_file():
        raise KaggleBridgeError(f"no existe patches_for_review/{name}")
    if path.stat().st_size > MAX_PATCH_BYTES:
        raise KaggleBridgeError("parche demasiado grande")
    r = subprocess.run(["git", "-C", str(repo), "apply", "--check", "--verbose", "--ignore-space-change", str(path)], capture_output=True, timeout=120)
    return {"patch": name, "sha256": _sha256_file(path), "applies_cleanly": r.returncode == 0,
            "detail": (r.stderr or r.stdout).decode("utf-8", errors="replace")[:1500],
            "note": "NO se aplicó. La revisión del diff y la aplicación son humanas o del agente local tras revisión; nunca automáticas."}


def process_bridge_request(
    request_data: Mapping[str, Any],
    client: KaggleClient,
    bridge_dir: Path,
    discovery_json_path: Path | None = None,
    policy: BridgePolicy | None = None,
) -> dict[str, Any]:
    """Execute a single JSON RPC request and return the response envelope."""
    policy = policy or BridgePolicy()
    req_id = sanitize_request_id(request_data.get("request_id") or f"req_{int(time.time())}")
    action = str(request_data.get("action") or "").strip()
    params = request_data.get("params") or {}
    if not isinstance(params, Mapping):
        raise KaggleBridgeError("params must be an object")

    if action == "ping":
        result: Any = {"status": "ONLINE", "bridge_schema": BRIDGE_SCHEMA}
    elif action == "search_datasets":
        result = client.search_datasets(
            query=str(params["query"]),
            max_results=int(params.get("max_results", 20)),
            sort_by=str(params.get("sort_by", "updated")),
            page=int(params.get("page", 1)),
        )
    elif action == "list_my_datasets":
        result = client.list_my_datasets(
            query=params.get("query"),
            page=int(params.get("page", 1)),
        )
    elif action == "list_dataset_files":
        result = client.list_dataset_files(
            dataset=str(params["dataset"]),
            page_size=int(params.get("page_size", 100)),
            page_token=params.get("page_token"),
        )
    elif action == "inspect_dataset":
        result = client.inspect_dataset(str(params["dataset"]))
    elif action == "read_dataset_file_preview":
        result = client.read_dataset_file_preview(
            dataset=str(params["dataset"]),
            file_name=str(params["file"]),
            max_bytes=int(params.get("max_bytes", 200_000)),
        )
    elif action == "download_file_chunked":
        dataset = str(params["dataset"])
        file_name = str(params["file"])
        _check_download_allowed(dataset, file_name, policy)
        expected_sha = params.get("expected_sha256")
        expected_size = params.get("expected_size_bytes")
        if params.get("require_discovery_pin", False):
            if discovery_json_path is None or not discovery_json_path.is_file():
                raise KaggleBridgeError("discovery.json path required for pinned download")
            pin = lookup_pinned_discovery_entry(discovery_json_path, dataset, file_name)
            expected_sha = pin["sha256"]
            expected_size = pin["size_bytes"]
        artifact_dir = bridge_dir / "artifacts" / req_id
        raw_dir = Path(tempfile.mkdtemp(prefix="edgelab_bridge_"))      # LOCAL, fuera de la carpeta sincronizada con Drive
        try:
            dl = client.download_dataset_file_to_path(dataset, file_name, raw_dir / Path(file_name).name)
            if not policy.allow_data_download and int(dl["size_bytes"]) > policy.max_download_bytes:
                raise KaggleBridgeError(f"archivo de {dl['size_bytes']} bytes supera el tope de {policy.max_download_bytes}")
            manifest = split_file_into_drive_chunks(
                Path(dl["local_path"]),
                artifact_dir,
                chunk_size_bytes=int(params.get("chunk_size_bytes", DEFAULT_CHUNK_BYTES)),
                expected_sha256=expected_sha,
                expected_size_bytes=int(expected_size) if expected_size is not None else None,
            )
        finally:
            shutil.rmtree(raw_dir, ignore_errors=True)
        result = {
            "dataset": dataset,
            "file": file_name,
            "artifact_dir": f"artifacts/{req_id}",
            "manifest": manifest,
        }
    elif action == "push_kernel":
        result = client.push_kernel(**_check_push_allowed(params, policy))
    elif action == "git_head_info":
        result = git_head_info(_resolve_repo(params, policy))
    elif action == "git_export_delta":
        result = git_export_delta(_resolve_repo(params, policy), params.get("base"), params.get("head"), bridge_dir / "artifacts" / req_id)
        result["artifact_dir"] = f"artifacts/{req_id}"
    elif action == "check_patch":
        result = check_patch(_resolve_repo(params, policy), bridge_dir, str(params.get("patch", "")))
    elif action == "get_kernel_status":
        result = client.get_kernel_status(
            owner=str(params["owner"]),
            slug=str(params["slug"]),
            version_label=params.get("version_label"),
        )
    elif action == "get_kernel_output":
        owner = str(params["owner"]).strip()
        slug = str(params["slug"]).strip()
        if not _SLUG_RE.match(slug):
            raise KaggleBridgeError("slug inválido")
        if owner not in policy.allowed_source_owners:                      # sin owners declarados = nadie permitido (no se leen salidas ajenas)
            raise KaggleBridgeError(f"get_kernel_output: owner {owner!r} no permitido (--allow-source-owner)")
        result = client.get_kernel_output(
            owner=owner,
            slug=slug,
            page_size=int(params.get("page_size", 50)),
            page_token=params.get("page_token"),
        )
    else:
        raise KaggleBridgeError(f"Unsupported action: {action!r}")

    return {
        "schema": BRIDGE_SCHEMA,
        "request_id": req_id,
        "action": action,
        "status": "OK",
        "completed_at_utc": _utc_now_iso(),
        "result": result,
    }


def watch_bridge_directory(
    bridge_dir: Path,
    client: KaggleClient,
    discovery_json_path: Path | None = None,
    poll_seconds: float = 2.0,
    max_loops: int | None = None,
    policy: BridgePolicy | None = None,
) -> None:
    """Watch <bridge_dir>/inbox for JSON requests and write responses to <bridge_dir>/outbox."""
    policy = policy or BridgePolicy()
    inbox = bridge_dir / "inbox"
    outbox = bridge_dir / "outbox"
    processed = bridge_dir / "processed"
    artifacts = bridge_dir / "artifacts"
    for d in (inbox, outbox, processed, artifacts, bridge_dir / "patches_for_review"):
        d.mkdir(parents=True, exist_ok=True)

    status_file = bridge_dir / "bridge_status.json"
    actions = ["ping", "search_datasets", "list_my_datasets", "list_dataset_files", "inspect_dataset",
               "read_dataset_file_preview", "download_file_chunked", "get_kernel_status", "get_kernel_output"]
    if policy.repos:
        actions += ["git_head_info", "git_export_delta", "check_patch"]
    if policy.allow_push:
        actions.append("push_kernel")
    status_file.write_text(
        json.dumps(
            {
                "schema": BRIDGE_SCHEMA,
                "status": "READY",
                "started_at_utc": _utc_now_iso(),
                "chunk_limit_bytes": DEFAULT_CHUNK_BYTES,
                "policy": {"allow_push": policy.allow_push, "allow_data_download": policy.allow_data_download,
                           "max_download_bytes": policy.max_download_bytes, "repos": sorted(policy.repos),
                           "allowed_source_owners": list(policy.allowed_source_owners),
                           "patches": "se dejan en patches_for_review/; nunca se aplican ni ejecutan automaticamente"},
                "supported_actions": actions,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    loops = 0
    while max_loops is None or loops < max_loops:
        for req_path in sorted(inbox.glob("*.json")):
            file_id = req_path.stem
            try:
                if req_path.stat().st_size > MAX_REQUEST_BYTES:
                    raise KaggleBridgeError("pedido demasiado grande")
                req_data = json.loads(req_path.read_text(encoding="utf-8"))
                if not isinstance(req_data, dict):
                    raise KaggleBridgeError("el pedido debe ser un objeto JSON")
                req_data["request_id"] = sanitize_request_id(req_data.get("request_id") or file_id)
                resp = process_bridge_request(req_data, client, bridge_dir, discovery_json_path, policy)
            except Exception as exc:
                resp = {
                    "schema": BRIDGE_SCHEMA,
                    "request_id": file_id if _REQ_ID_RE.match(file_id) and ".." not in file_id else "invalid",
                    "status": "ERROR",
                    "error": str(exc)[:500],
                    "completed_at_utc": _utc_now_iso(),
                }
            out_path = outbox / f"{resp['request_id']}.response.json"
            out_path.write_text(json.dumps(resp, indent=2, sort_keys=True), encoding="utf-8")
            shutil.move(str(req_path), str(processed / req_path.name))
        loops += 1
        if max_loops is None or loops < max_loops:
            time.sleep(poll_seconds)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EdgeLab <-> Google Drive <-> Kaggle local bridge.")
    parser.add_argument("--bridge-dir", type=Path, help="Path to synced Google Drive folder (e.g., EdgeLab_Bridge)")
    parser.add_argument("--watch", action="store_true", help="Run continuous watcher on --bridge-dir")
    parser.add_argument("--once", action="store_true", help="Process current inbox once and exit")
    parser.add_argument("--list-my-datasets", action="store_true", help="Test credentials by listing private datasets")
    parser.add_argument("--inspect", type=str, help="Inspect owner/dataset metadata and files")
    parser.add_argument("--chunk-file", type=Path, help="Split a local file into <9 MB Drive chunks")
    parser.add_argument("--out-dir", type=Path, help="Output directory for --chunk-file")
    parser.add_argument("--reassemble", type=Path, help="Path to *.manifest.json to reassemble")
    parser.add_argument("--dest", type=Path, help="Destination file path for --reassemble")
    parser.add_argument("--allow-push", action="store_true", help="Habilita push_kernel (ejecuta código en Kaggle con tu cuenta). Apagado por defecto.")
    parser.add_argument("--allow-source-owner", action="append", default=[], help="Owner de Kaggle permitido como dataset_source en push_kernel (repetible)")
    parser.add_argument("--allow-data-download", action="store_true", help="Habilita descargar archivos binarios/de datos a Drive. Apagado por defecto (licencia CME).")
    parser.add_argument("--repo", action="append", default=[], metavar="NOMBRE=RUTA", help="Registra un repo git local para git_head_info / git_export_delta / check_patch (repetible)")
    args = parser.parse_args(argv)

    if args.chunk_file:
        out = args.out_dir or (args.chunk_file.parent / f"{args.chunk_file.name}_chunks")
        manifest = split_file_into_drive_chunks(args.chunk_file, out)
        print(json.dumps(manifest, indent=2))
        return 0

    if args.reassemble:
        if not args.dest:
            parser.error("--dest is required with --reassemble")
        res = reassemble_drive_chunks(args.reassemble, args.dest)
        print(json.dumps(res, indent=2))
        return 0

    headers = load_kaggle_auth_headers()
    client = KaggleClient(headers)
    default_discovery = Path(__file__).resolve().parent.parent / "edgelab" / "kaggle" / "discovery.json"
    repos = {}
    for item in args.repo:
        name, _, path = item.partition("=")
        if not name or not path or not Path(path, ".git").exists():
            parser.error(f"--repo debe ser NOMBRE=RUTA a un repo git: {item!r}")
        repos[name] = path
    policy = BridgePolicy(allow_push=args.allow_push, allow_data_download=args.allow_data_download,
                          allowed_source_owners=tuple(args.allow_source_owner), repos=repos)

    if args.list_my_datasets:
        print(json.dumps(client.list_my_datasets(), indent=2))
        return 0

    if args.inspect:
        print(json.dumps(client.inspect_dataset(args.inspect), indent=2))
        return 0

    if args.bridge_dir and (args.watch or args.once):
        print(f"Puente activo. push_kernel={'ON' if policy.allow_push else 'OFF'}, descarga de datos={'ON' if policy.allow_data_download else 'OFF'}.")
        watch_bridge_directory(
            args.bridge_dir,
            client,
            discovery_json_path=default_discovery if default_discovery.is_file() else None,
            max_loops=1 if args.once else None,
            policy=policy,
        )
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
