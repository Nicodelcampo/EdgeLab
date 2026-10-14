#!/usr/bin/env python3
r"""Exporta un snapshot de CÓDIGO del commit HEAD como un .tar.gz chico, para que un auditor externo lo descargue de una vez y corra los tests.

Por qué existe: `git archive` crudo arrastra todo lo versionado (wheels, bundles del visor con series de precios, archivos de `archive/` y `diag/`,
CSV/JSONL de eventos). Esos archivos pueden contener datos de mercado derivados de CME y no se entregan a terceros. Acá se usa LISTA BLANCA:
sólo código y documentación, con tope de tamaño por archivo. Todo lo demás queda afuera aunque esté versionado.

Qué entra: .py .md .cs .toml .yml .yaml .cfg .ini .sh .ps1 .bat, `requirements*.txt`, LICENSE*, y .json <= 300 KB que NO estén en carpetas de datos.
Qué no entra: .git, data/, oracles/, runs/, archive/, diag/, viewer/**/bundles/, *.csv, *.jsonl, *.parquet, *.whl, *.svg, *.js, *.html, *.txt (salvo requirements),
cualquier archivo > 1 MB, y nombres con pinta de credencial.

Uso: python tools/export_head_snapshot.py --repo E:\EdgeLab-gex --out "G:\Mi unidad\EdgeLab_Bridge"
Escribe edgelab_HEAD.tar.gz y edgelab_HEAD.json (commit, rama, SHA-256, conteos, reglas).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

CODE_EXT = {".py", ".md", ".cs", ".toml", ".yml", ".yaml", ".cfg", ".ini", ".sh", ".ps1", ".bat"}
MAX_FILE = 1_000_000
MAX_JSON = 300_000
DENY_DIRS = {".git", "data", "oracles", "runs", "archive", "diag", "bundles", "node_modules", "__pycache__", ".venv", "venv", ".claude"}
SENSITIVE = re.compile(r"(\.env$|credential|access_token|kaggle\.json$|id_rsa|\.pem$|\.key$|secret)", re.I)


def allowed(name: str, size: int) -> tuple[bool, str]:
    """name: ruta dentro del archivo (sin el prefijo). Devuelve (entra, motivo)."""
    p = PurePosixPath(name)
    parts = {x.lower() for x in p.parts[:-1]}
    if parts & DENY_DIRS:
        return False, "carpeta excluida"
    if SENSITIVE.search(p.name):
        return False, "nombre sensible"
    if size > MAX_FILE:
        return False, "mayor que 1 MB"
    ext = p.suffix.lower()
    if ext in CODE_EXT:
        return True, "código/documentación"
    if ext == ".json":
        return (True, "json chico") if size <= MAX_JSON else (False, "json mayor que 300 KB")
    in_req = "requirements" in {x.lower() for x in p.parts[:-1]}
    if ext in {".txt", ".lock"} and (in_req or p.name.lower().startswith("requirements") or p.name.upper().startswith("LICENSE")):
        return True, "requisitos/licencia"
    if p.name.upper().startswith(("LICENSE", "README", "CLAUDE")) and ext == "":
        return True, "texto sin extensión"
    return False, "extensión fuera de la lista blanca"


def export(repo: Path, out_dir: Path, prefix: str = "edgelab/") -> dict:
    git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True).stdout.strip()
    commit, branch = git("rev-parse", "HEAD"), git("rev-parse", "--abbrev-ref", "HEAD")
    dirty = bool(git("status", "--porcelain"))
    out_dir.mkdir(parents=True, exist_ok=True)
    tar_path, meta_path = out_dir / "edgelab_HEAD.tar.gz", out_dir / "edgelab_HEAD.json"
    proc = subprocess.Popen(["git", "-C", str(repo), "archive", "--format=tar", "--prefix=" + prefix, "HEAD"], stdout=subprocess.PIPE)
    kept, skipped, reasons, total = 0, 0, {}, 0
    tmp = tar_path.with_suffix(".tmp")
    with tarfile.open(fileobj=proc.stdout, mode="r|") as src, tarfile.open(tmp, "w:gz", compresslevel=9) as dst:
        for m in src:
            if not m.isfile():
                continue
            rel = m.name[len(prefix):] if m.name.startswith(prefix) else m.name
            ok, why = allowed(rel, m.size)
            if not ok:
                skipped += 1
                reasons[why] = reasons.get(why, 0) + 1
                continue
            data = src.extractfile(m).read()
            m.mode = 0o644
            dst.addfile(m, io.BytesIO(data))
            kept += 1
            total += m.size
    if proc.wait() != 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("git archive falló")
    tmp.replace(tar_path)
    sha = hashlib.sha256(tar_path.read_bytes()).hexdigest()
    meta = dict(schema="edgelab_head_snapshot_v1", commit=commit, branch=branch, tree_dirty_ignored=dirty,
                note="snapshot del COMMIT (no del árbol de trabajo); sin .git, sin datos, sin credenciales; lista blanca", generated_utc=datetime.now(timezone.utc).isoformat(),
                archivo="edgelab_HEAD.tar.gz", bytes=tar_path.stat().st_size, sha256=sha, files_kept=kept, files_skipped=skipped,
                uncompressed_bytes=total, skipped_by_reason=reasons, prefix=prefix)
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    print(json.dumps(export(Path(a.repo), Path(a.out)), indent=2, ensure_ascii=False))
