"""Selección de la próxima corrida: Thompson sampling Beta-Bernoulli por (familia, grupo), ajustado por costo, con piso de exploración y sin repetir specs.
«Acierto» = la corrida terminó con un hallazgo que sobrevivió a su regla de decisión PRE-REGISTRADA (analyze.hit). La selección usa solo el historial de aciertos,
no resultados de pruebas futuras; cada corrida elegida sigue pagando su multiplicidad (contador global + alpha-investing), así que priorizar no regala significancia."""
from __future__ import annotations

import numpy as np


def rank(candidates: list, outcomes: list, ledger, seed: int, explore_floor: float = 0.15, prior=(1.0, 4.0)) -> list:
    """candidates: RunSpec. outcomes: [(family, group, hit)]. Devuelve [(score, spec, razón)] de mayor a menor. Determinista dado `seed` (queda registrado)."""
    rng = np.random.default_rng(seed); tally = {}
    for fam, grp, hit in outcomes:
        h, n = tally.get((fam, grp), (0, 0)); tally[(fam, grp)] = (h + hit, n + 1)
    out = []
    for c in candidates:
        if ledger.seen(c.spec_hash(), c.run_id if hasattr(c, "run_id") else None): continue                       # nunca repetir lo ya corrido
        h, n = tally.get((c.family, c.group), (0, 0))
        draw = rng.beta(prior[0] + h, prior[1] + n - h)
        explore = n == 0 and rng.random() < explore_floor            # grupos nunca probados reciben una chance mínima
        score = (max(draw, 0.5) if explore else draw) / np.sqrt(max(c.est_seconds, 60) / 600.0)
        out.append((float(score), c, f"{h}/{n} aciertos previos; sorteo {draw:.3f}" + ("; exploración" if explore else "")))
    return sorted(out, key=lambda x: -x[0])
