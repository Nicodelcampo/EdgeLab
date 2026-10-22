"""Registro común de lanzamientos de la CUENTA de Kaggle (autopilot, humano, otros agentes que usen tools/kaggle_launch.py).
Append-only (JSONL con flock). El tope diario de cuenta se aplica sobre TODO lo registrado, no solo sobre las corridas del libro del autopilot.
No ve lanzamientos hechos por fuera de kaggle_launch.py (Kaggle UI/API directa): por eso es un tope de prudencia, no una garantía de cuota."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[2] / "docs/research/autopilot_runs/account_launches.jsonl"


def log_path() -> Path:
    return Path(os.environ.get("EDGELAB_ACCOUNT_LOG", DEFAULT))


def record(slug: str, source: str | None = None, path: Path | None = None) -> dict:
    p = Path(path or log_path()); p.parent.mkdir(parents=True, exist_ok=True)
    rec = dict(ts=time.time(), slug=slug, source=source or os.environ.get("EDGELAB_LAUNCH_SOURCE", "manual"), pid=os.getpid())
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        try:                                                     # Debian: candado exclusivo; Windows: msvcrt (bloqueo real)
            import fcntl; fcntl.flock(f, fcntl.LOCK_EX)
        except ImportError:
            import msvcrt; f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1); f.seek(0, 2)
        f.write(json.dumps(rec) + "\n")
    return rec


def read(path: Path | None = None) -> list:
    p = Path(path or log_path())
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def count_since(t: float, path: Path | None = None) -> int:
    return sum(1 for r in read(path) if r["ts"] >= t)
