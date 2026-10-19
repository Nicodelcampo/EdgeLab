"""Puente al Edge Brain: cada corrida analizada queda como episodio en el hipocampo (append-only); aciertos y fallos se conservan por igual.
Las lecciones se registran solo PROPOSED/LOW: aprender «qué funcionó» no autoriza nada sin revisión humana."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def brain_sink(ledger_path: Path):
    from edgelab.edge_brain import DurableHippocampus
    from edgelab.edge_brain.hippocampus import AnalysisEpisode, FailureEvent, SuccessEvent

    def sink(spec, decision):
        h = DurableHippocampus(Path(ledger_path)); ep = f"AUTOPILOT-{spec.run_id}"; now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if ep in h.memory.episodes: return
        h.register_episode(AnalysisEpisode(episode_id=ep, goal=f"{spec.family}/{spec.group}: {spec.notes or spec.script}", created_at_utc=now, updated_at_utc=now, recorded_by="edgelab-autopilot"))
        top = "; ".join(f"{t['test']} p={t['p']:.4g}" for t in decision["top"][:3]) or "sin pruebas evaluables"
        if decision["hit"]:
            h.record_success(SuccessEvent("OK1", ep, "S1", f"{decision['rejections']} rechazos de Holm a nivel {decision['family_alpha']:.4f} sobre {decision['n_planned']} pruebas planeadas: {top}",
                                          ["hallazgo exploratorio; requiere réplica pre-registrada", spec.prereg], occurred_at_utc=now))
        else:
            h.record_failure(FailureEvent("F1", ep, "S1", "NO_FINDING", f"ninguna prueba pasa Holm a nivel {decision['family_alpha']:.4f}", f"mejores: {top}", occurred_at_utc=now))
    return sink
