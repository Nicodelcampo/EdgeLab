"""Registro AUTOMATICO de episodios de medicion desde las herramientas (propuesta 4, 2026-09-23).

Uso tipico en un `tools/*.py`:

    with measurement_episode(ledger, "EP-L2-FASE2-GC-20260923", goal="...", recorded_by="tools/l2_phase2_info.py",
                             inputs={"results": Path("artifacts/l2_phase2/results.json")},
                             prereg_ref="docs/...md@aa080a1") as ep:
        ...                                   # la medicion
        ep.note("output", "ningun rechazo en 6 pruebas")

Registra: episodio (outcomes_inspected=False: el logger no abre holdout ni juzga), un paso con commit, arbol
limpio/sucio y sha256 de cada entrada; al salir, SuccessEvent o FailureEvent con el tipo de error. Nunca promueve
nada: las conclusiones siguen siendo LessonCandidate PROPOSED/LOW registradas aparte.
"""
from __future__ import annotations

import hashlib
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .hippocampus import AnalysisEpisode, FailureEvent, StepExecution, SuccessEvent
from .hippocampus_store import DurableHippocampus


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(repo: Path, *args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return ""


class _Episode:
    """`ep.store` es EL escritor del ledger durante el episodio: no abrir otro DurableHippocampus sobre el mismo
    archivo adentro del `with` (el lock de un solo escritor lo rechaza; paso el 2026-09-23 en la campana)."""

    def __init__(self, store: DurableHippocampus, episode_id: str, step_id: str):
        self.store, self.episode_id, self.step_id, self.notes = store, episode_id, step_id, []

    def note(self, key: str, value: str) -> None:
        self.notes.append(f"{key}={value}")


@contextmanager
def measurement_episode(ledger: str | Path, episode_id: str, *, goal: str, recorded_by: str,
                        inputs: dict[str, Path] | None = None, prereg_ref: str = "", repo: Path | None = None):
    now = datetime.now(timezone.utc).isoformat()
    repo = repo or Path.cwd()
    store = DurableHippocampus(ledger)
    store.register_episode(AnalysisEpisode(episode_id=episode_id, goal=goal, status="RUNNING",
                                           created_at_utc=now, updated_at_utc=now, recorded_by=recorded_by,
                                           outcomes_inspected=False))
    params = {"code_commit": _git(repo, "rev-parse", "HEAD"),
              "tree_dirty": str(bool(_git(repo, "status", "--porcelain"))),
              "prereg_ref": prereg_ref}
    for name, path in (inputs or {}).items():
        params[f"sha256:{name}"] = _sha(path) if Path(path).exists() else "MISSING"
    step_id = f"{episode_id}-S1"
    store.record_step(StepExecution(step_id=step_id, episode_id=episode_id, step_index=0, action="measure",
                                    tool_name=recorded_by, status="RUNNING", input_params=params,
                                    executed_at_utc=now))
    ep = _Episode(store, episode_id, step_id)
    try:
        yield ep
    except BaseException as exc:
        store.record_failure(FailureEvent(failure_id=f"{episode_id}-F1", episode_id=episode_id, step_id=step_id,
                                          error_type=type(exc).__name__, description=str(exc)[:500],
                                          root_cause="UNDIAGNOSED", occurred_at_utc=datetime.now(timezone.utc).isoformat()))
        raise
    else:
        store.record_success(SuccessEvent(success_id=f"{episode_id}-OK", episode_id=episode_id, step_id=step_id,
                                          description="; ".join(ep.notes)[:2000] or "completed",
                                          occurred_at_utc=datetime.now(timezone.utc).isoformat()))
