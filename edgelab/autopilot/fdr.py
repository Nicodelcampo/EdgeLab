"""Control de la tasa de falsos descubrimientos EN LÍNEA entre campañas (alpha-investing, Foster & Stine).
Holm controla dentro de una campaña; esto controla a lo largo de todas: cada campaña «paga» riqueza de alfa y los descubrimientos la recargan.
Es la forma honesta en que las chances de edge mejoran con el tiempo: no se baja el listón, se gasta mejor el presupuesto (se prioriza donde hubo aciertos replicados).
Supuesto: pruebas aproximadamente independientes entre campañas; con dependencia fuerte el control es aproximado."""
from __future__ import annotations

import json
from pathlib import Path


class AlphaInvesting:
    def __init__(self, path: Path, w0: float = 0.05, payout: float = 0.05, spend_fraction: float = 0.5):
        self.path = Path(path); self.payout = payout; self.f = spend_fraction
        self.state = json.loads(self.path.read_text()) if self.path.exists() else dict(wealth=w0, history=[], open={})

    @property
    def wealth(self) -> float:
        return self.state["wealth"]

    def bid(self, campaign_id: str, n_tests: int) -> float:
        """Nivel familiar de la campaña (se reparte con Holm dentro). Es a = f·W/(1+W), de modo que el costo a/(1−a) nunca supera W."""
        if campaign_id in self.state["open"]: return self.state["open"][campaign_id]["alpha"]
        a = self.f * self.wealth / (1 + self.wealth)
        self.state["open"][campaign_id] = dict(alpha=a, n_tests=n_tests); self._save(); return a

    def settle(self, campaign_id: str, rejections: int) -> float:
        b = self.state["open"].pop(campaign_id)                 # KeyError si no hubo apuesta previa: no se liquida lo que no se apostó
        a = b["alpha"]
        self.state["wealth"] += self.payout if rejections > 0 else -a / (1 - a)
        self.state["history"].append(dict(campaign=campaign_id, alpha=a, rejections=rejections, wealth_after=self.wealth))
        self._save(); return self.wealth

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True); self.path.write_text(json.dumps(self.state, indent=1))


def holm_rejections(pvals: list, family_alpha: float, m: int | None = None) -> int:
    """Rechazos de Holm al nivel familiar `family_alpha` sobre `m` pruebas planeadas (m ≥ len(pvals); las no evaluables cuentan en m, no en el ranking)."""
    m = max(m or len(pvals), len(pvals)); o = sorted(pvals); r = 0
    for k, p in enumerate(o):
        if p <= family_alpha / (m - k): r += 1
        else: break
    return r
