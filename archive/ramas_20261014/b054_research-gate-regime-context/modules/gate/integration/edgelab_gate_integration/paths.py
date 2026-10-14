"""
Rutas típicas EdgeLab (Windows del lab + portable).

No asume que existan; el pipeline falla con mensaje claro si faltan.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class EdgeLabPaths:
    """Raíces configurables del worktree EdgeLab."""

    root: Path
    # relativos al root
    events_glob: str = "runs/**/*events*.csv"
    oracle_snapshot: str = "runs/oraculo_espurev2flat_ES_snapshot.sqlite"
    es_parquet_dir: str = "data/nt8/ES_parquet"
    labels_out_dir: str = "runs/gate_labels"
    research_docs: str = "docs/research"

    def resolve(self) -> dict[str, Path]:
        r = self.root.resolve()
        return {
            "root": r,
            "oracle_snapshot": r / self.oracle_snapshot,
            "es_parquet_dir": r / self.es_parquet_dir,
            "labels_out_dir": r / self.labels_out_dir,
            "research_docs": r / self.research_docs,
        }


# Defaults vistos en commits del repo (paths Windows del handoff)
DEFAULT_WINDOWS_HINTS = [
    r"E:\EdgeLab",
    r"E:/EdgeLab",
]


def find_edgelab_root(explicit: str | None = None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_dir() else None
    # sandbox / portable
    candidates = [
        Path("/home/workdir/EdgeLab"),
        Path("/home/workdir/artifacts/EdgeLab"),
        Path.cwd() / "EdgeLab",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return None
