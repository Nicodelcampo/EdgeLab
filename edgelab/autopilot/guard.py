"""Guardas duras. Si una falla, la corrida NO se lanza. Ninguna se puede desactivar desde un RunSpec."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from . import HOLDOUT_FIRST_TRADE_DATE
from .spec import RunSpec

REPO = Path(__file__).resolve().parents[2]


def _git(*a, cwd=REPO):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True).stdout.strip()


def check_holdout(spec: RunSpec) -> list:
    bad = []
    for n in spec.needs:
        parts = n.split(":")
        if len(parts) != 3: bad.append(f"need mal formado: {n}"); continue
        if parts[2] >= HOLDOUT_FIRST_TRADE_DATE or parts[1] >= HOLDOUT_FIRST_TRADE_DATE:
            bad.append(f"holdout: {n} llega a {HOLDOUT_FIRST_TRADE_DATE} o después")
    return bad


def check_prereg_committed(spec: RunSpec, repo: Path = REPO) -> list:
    """El pre-registro debe estar committeado, sin cambios locales, y su commit debe ser anterior al lanzamiento (siempre lo es si ya existe)."""
    p = repo / spec.prereg
    if not p.exists(): return [f"pre-registro inexistente: {spec.prereg}"]
    if not _git("log", "-1", "--format=%H", "--", spec.prereg, cwd=repo): return [f"pre-registro sin commit: {spec.prereg}"]
    if _git("status", "--porcelain", "--", spec.prereg, cwd=repo): return [f"pre-registro con cambios sin commitear: {spec.prereg}"]
    return []


def check_script_committed(spec: RunSpec, repo: Path = REPO) -> list:
    if not (repo / spec.script).exists(): return [f"script inexistente: {spec.script}"]
    if _git("status", "--porcelain", "--", spec.script, cwd=repo): return [f"script con cambios sin commitear: {spec.script} (el código lanzado debe quedar atado a un commit)"]
    return []


def check_internet(spec: RunSpec, allow: set) -> list:
    return [] if (not spec.internet or spec.script in allow) else [f"internet no permitido para {spec.script} (lista blanca vacía para él)"]


def snapshot_protected(paths: list, repo: Path = REPO) -> dict:
    return {p: hashlib.sha256((repo / p).read_bytes()).hexdigest() for p in paths}


def check_protected(manifest_path: Path, repo: Path = REPO) -> list:
    """Compara contra un manifiesto de hashes (gates, holdout, registro, pre-registros pasados). Cualquier diferencia detiene el ciclo hasta revisión humana."""
    m = json.loads(Path(manifest_path).read_text())
    bad = []
    for p, h in m.items():
        f = repo / p
        if not f.exists(): bad.append(f"protegido ausente: {p}")
        elif hashlib.sha256(f.read_bytes()).hexdigest() != h: bad.append(f"protegido modificado: {p}")
    return bad


def all_checks(spec: RunSpec, allow_internet: set = frozenset(), repo: Path = REPO, protected: Path | None = None) -> list:
    e = spec.validate_shape() + check_holdout(spec) + check_prereg_committed(spec, repo) + check_script_committed(spec, repo) + check_internet(spec, set(allow_internet))
    if protected: e += check_protected(protected, repo)
    return e
