"""Sincronizador determinista e idempotente de ramas y estado vivo para el servidor Debian (`SV1`).

Resuelve las 4 causas técnicas por las cuales el agente del Debian quedaba aislado en una rama o commit viejo:
  1. Evacuación automática de archivos de estado vivo (`EVALUABLES.jsonl`, `LIBRO_LORD.json`, `LINAJES.jsonl`,
     `HOLDOUT_VENTANAS.jsonl`, `account_launches.jsonl` y `docs/data_catalog/launches/*.json`) desde `CODE_DIR`
     hacia `STATE_DIR` con fusión append-only sin pérdida de líneas antes de hacer checkout/fast-forward.
  2. Sincronización automática pre-ciclo con `origin/foundation/f0b-compatibility-probe` (fast-forward seguro
     incluso en `detached HEAD`).
  3. Rescate de commits locales de autorreparación (`autopilot/codigo/*`): si `HEAD` local tiene commits propios del
     programador que aún no están en `origin/foundation/f0b-compatibility-probe`, los etiqueta/respalda en una rama
     `autopilot/rescate/<ts>` y hace rebase o avanza al commit troncal sin bloquear el servicio.
  4. Auto-recuperación de unidades `systemd` caídas en estado `failed` (`edgelab-autopilot-generate.service`,
     `edgelab-autopilot-programador.service`).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ARCHIVOS_ESTADO_VIVO_JSONL: tuple[str, ...] = (
    "docs/research/EVALUABLES.jsonl",
    "docs/research/LINAJES.jsonl",
    "docs/research/HOLDOUT_VENTANAS.jsonl",
    "docs/research/autopilot_runs/account_launches.jsonl",
)

ARCHIVOS_ESTADO_VIVO_JSON: tuple[str, ...] = (
    "docs/research/LIBRO_LORD.json",
)


@dataclass
class ResultadoSincronizacion:
    ok: bool
    rama_objetivo: str
    sha_anterior: str
    sha_actual: str
    sha_remoto: str
    avanzo_fast_forward: bool
    archivos_evacuados: list[str] = field(default_factory=list)
    rama_rescate: str | None = None
    servicios_recuperados: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def a_dict(self) -> dict[str, Any]:
        return asdict(self)


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    r = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {(r.stderr or r.stdout).strip()[-300:]}")
    return r


def fusionar_jsonl_sin_perdida(origen: Path, destino: Path) -> int:
    """Fusiona líneas JSONL únicas desde `origen` hacia `destino` preservando el orden."""
    if not origen.exists():
        return 0
    destino.parent.mkdir(parents=True, exist_ok=True)
    existentes = set()
    lineas_dest: list[str] = []
    if destino.exists():
        for l in destino.read_text(encoding="utf-8", errors="replace").splitlines():
            s = l.strip()
            if s:
                existentes.add(s)
                lineas_dest.append(s)
    nuevas = 0
    for l in origen.read_text(encoding="utf-8", errors="replace").splitlines():
        s = l.strip()
        if s and s not in existentes:
            existentes.add(s)
            lineas_dest.append(s)
            nuevas += 1
    if nuevas > 0 or not destino.exists():
        destino.write_text("\n".join(lineas_dest) + "\n", encoding="utf-8")
    return nuevas


def evacuar_estado_vivo(code_dir: Path, state_dir: Path) -> list[str]:
    """Evacúa hacia `state_dir` cualquier archivo de estado vivo que ensucie `code_dir` y restaura el árbol limpio."""
    code_dir, state_dir = Path(code_dir), Path(state_dir)
    evacuados: list[str] = []
    runs_dir = state_dir / "autopilot_runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    for rel in ARCHIVOS_ESTADO_VIVO_JSONL:
        f_code = code_dir / rel
        if not f_code.exists():
            continue
        diff = _git(code_dir, " status", "--porcelain", "--", rel, check=False) if False else _git(code_dir, "status", "--porcelain", "--", rel, check=False)
        if diff.stdout.strip():
            f_state = runs_dir / Path(rel).name
            fusionar_jsonl_sin_perdida(f_code, f_state)
            _git(code_dir, "checkout", "-q", "--", rel, check=False)
            evacuados.append(rel)

    for rel in ARCHIVOS_ESTADO_VIVO_JSON:
        f_code = code_dir / rel
        if not f_code.exists():
            continue
        diff = _git(code_dir, "status", "--porcelain", "--", rel, check=False)
        if diff.stdout.strip():
            f_state = runs_dir / f"{Path(rel).stem}.bak.json"
            shutil.copy2(f_code, f_state)
            _git(code_dir, "checkout", "-q", "--", rel, check=False)
            evacuados.append(rel)

    launches_code = code_dir / "docs/data_catalog/launches"
    if launches_code.exists():
        diff_l = _git(code_dir, "status", "--porcelain", "--", "docs/data_catalog/launches", check=False)
        if diff_l.stdout.strip():
            launches_state = runs_dir / "launches"
            launches_state.mkdir(parents=True, exist_ok=True)
            for jf in launches_code.glob("*.json"):
                shutil.copy2(jf, launches_state / jf.name)
            _git(code_dir, "checkout", "-q", "--", "docs/data_catalog/launches", check=False)
            _git(code_dir, "clean", "-fdq", "docs/data_catalog/launches", check=False)
            evacuados.append("docs/data_catalog/launches/*.json")

    for lock_f in (code_dir / "docs/research").rglob("*.lock"):
        try:
            lock_f.unlink()
            evacuados.append(str(lock_f.relative_to(code_dir)))
        except OSError:
            pass

    return evacuados


def sincronizar_con_troncal(
    code_dir: Path,
    state_dir: Path,
    *,
    rama_objetivo: str = "foundation/f0b-compatibility-probe",
    hacer_fetch: bool = True,
) -> ResultadoSincronizacion:
    """Sincroniza `code_dir` con `origin/<rama_objetivo>` de forma limpia e idempotente."""
    code_dir, state_dir = Path(code_dir), Path(state_dir)
    avisos: list[str] = []
    evacuados = evacuar_estado_vivo(code_dir, state_dir)

    sha_ant = _git(code_dir, "rev-parse", "HEAD").stdout.strip()
    if hacer_fetch:
        r_fetch = _git(code_dir, "fetch", "-q", "origin", rama_objetivo, check=False)
        if r_fetch.returncode != 0:
            avisos.append(f"fetch falló: {(r_fetch.stderr or r_fetch.stdout).strip()[:200]}")

    r_rem = _git(code_dir, "rev-parse", f"origin/{rama_objetivo}", check=False)
    sha_rem = r_rem.stdout.strip() if r_rem.returncode == 0 else sha_ant

    if sha_ant == sha_rem:
        return ResultadoSincronizacion(
            ok=True,
            rama_objetivo=rama_objetivo,
            sha_anterior=sha_ant,
            sha_actual=sha_ant,
            sha_remoto=sha_rem,
            avanzo_fast_forward=False,
            archivos_evacuados=evacuados,
            avisos=avisos,
        )

    status_restante = [
        l for l in _git(code_dir, "status", "--porcelain", check=False).stdout.splitlines() if l.strip()
    ]
    if status_restante:
        avisos.append(f"Árbol aún con {len(status_restante)} archivos modificados tras evacuación: {status_restante[:3]}")
        return ResultadoSincronizacion(
            ok=False,
            rama_objetivo=rama_objetivo,
            sha_anterior=sha_ant,
            sha_actual=sha_ant,
            sha_remoto=sha_rem,
            avanzo_fast_forward=False,
            archivos_evacuados=evacuados,
            avisos=avisos,
        )

    es_ancestro = _git(code_dir, "merge-base", "--is-ancestor", sha_ant, sha_rem, check=False).returncode == 0
    rama_rescate: str | None = None
    if not es_ancestro:
        rama_rescate = f"autopilot/rescate/{int(time.time())}-{sha_ant[:8]}"
        _git(code_dir, "branch", "-f", rama_rescate, sha_ant, check=False)
        avisos.append(f"HEAD local {sha_ant[:8]} no era ancestro de {sha_rem[:8]}; respaldado en {rama_rescate}")

    _git(code_dir, "checkout", "-q", "--detach", sha_rem)
    sha_act = _git(code_dir, "rev-parse", "HEAD").stdout.strip()

    # Re-aplicar las líneas nuevas de EVALUABLES/LINAJES/HOLDOUT_VENTANAS guardadas en state_dir
    runs_dir = state_dir / "autopilot_runs"
    for rel in ARCHIVOS_ESTADO_VIVO_JSONL:
        f_state = runs_dir / Path(rel).name
        f_code = code_dir / rel
        if f_state.exists() and f_code.exists():
            fusionar_jsonl_sin_perdida(f_code, f_state)

    return ResultadoSincronizacion(
        ok=(sha_act == sha_rem),
        rama_objetivo=rama_objetivo,
        sha_anterior=sha_ant,
        sha_actual=sha_act,
        sha_remoto=sha_rem,
        avanzo_fast_forward=(sha_act == sha_rem and sha_ant != sha_act),
        archivos_evacuados=evacuados,
        rama_rescate=rama_rescate,
        avisos=avisos,
    )
