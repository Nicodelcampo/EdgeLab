"""RunSpec: descripción declarativa de una corrida. Es lo único que el autopilot sabe lanzar."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

KINDS = ("scan", "study", "replication", "benchmark")


@dataclass
class RunSpec:
    run_id: str
    kind: str                                   # uno de KINDS
    family: str                                 # etiqueta para el selector (p. ej. "OU1_REVERSION", "GEX", "F5_MEDIAS")
    group: str                                  # activo/grupo (p. ej. "GC", "IDX", "ZB")
    script: str                                 # ruta repo-relativa, bajo tools/
    prereg: str                                 # pre-registro committeado (ruta repo-relativa)
    n_trials: int                               # pruebas que esta corrida agrega al contador global
    needs: list = field(default_factory=list)   # ["MES:2025-07-01:2026-09-30", ...]
    extra_datasets: list = field(default_factory=list)
    internet: bool = False
    gpu: bool = False
    env: dict = field(default_factory=dict)
    est_seconds: int = 1800
    est_gb: float = 8.0
    decision_rule: str = "holm"                # cómo se interpreta el resultado; identificador que entiende analyze.py
    notes: str = ""
    n_tests_holm: int | None = None             # nº de pruebas REPORTADAS para Holm (None = n_trials); n_trials cuenta las celdas escaneadas en el contador global
    origin: dict = field(default_factory=dict)  # {evidence_id: muestra consumida}: qué pista originó la corrida y qué muestra independiente gasta

    def spec_hash(self) -> str:
        d = asdict(self); d.pop("run_id"); d.pop("notes")
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()

    def validate_shape(self) -> list:
        e = []
        if self.kind not in KINDS: e.append(f"kind {self.kind!r} no está en {KINDS}")
        if not self.script.startswith("tools/") or ".." in self.script: e.append("script debe estar bajo tools/")
        if self.kind != "benchmark" and self.n_trials < 1: e.append("n_trials ≥ 1 (toda corrida de hipótesis cuenta en el contador global)")
        if not self.prereg: e.append("falta pre-registro")
        if not self.needs and self.kind != "benchmark": e.append("falta `needs` (sin datos declarados no se puede comprobar el holdout)")
        return e

    @staticmethod
    def from_dict(d: dict) -> "RunSpec":
        return RunSpec(**d)
