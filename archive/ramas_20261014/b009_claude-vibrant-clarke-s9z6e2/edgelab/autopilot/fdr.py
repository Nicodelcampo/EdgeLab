"""Control de la tasa de falsos descubrimientos EN LÍNEA entre campañas (alpha-investing, Foster & Stine).
Holm controla dentro de una campaña; esto controla a lo largo de todas: cada campaña «paga» riqueza de alfa y los descubrimientos la recargan.
Es la forma honesta en que las chances de edge mejoran con el tiempo: no se baja el listón, se gasta mejor el presupuesto (se prioriza donde hubo aciertos replicados).
Supuesto: pruebas aproximadamente independientes entre campañas; con dependencia fuerte el control es aproximado."""
from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from pathlib import Path


class AlphaInvesting:
    def __init__(self, path: Path, w0: float = 0.05, payout: float = 0.05, spend_fraction: float = 0.5):
        self.path = Path(path); self.payout = payout; self.f = spend_fraction
        self.w0 = w0; self.state = self._load()

    def _load(self) -> dict:
        return json.loads(self.path.read_text()) if self.path.exists() else dict(wealth=self.w0, history=[], open={})

    @contextmanager
    def _tx(self):
        """Transacción: bloqueo exclusivo del archivo + recarga del estado vigente (otro proceso pudo haber apostado) + escritura atómica al salir sin error."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(self.path) + ".lock", "a") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX); self.state = self._load()
            yield
            self._save()

    @property
    def wealth(self) -> float:
        return self.state["wealth"]

    def bid(self, campaign_id: str, n_tests: int) -> float:
        """Nivel familiar de la campaña (se reparte con Holm dentro). Es a = f·A/(1+A) con A = riqueza − costo ya comprometido por campañas abiertas, de modo que la suma de costos posibles nunca supera W aunque corran varias a la vez."""
        with self._tx():
            if campaign_id in self.state["open"]: return self.state["open"][campaign_id]["alpha"]
            committed = sum(b["alpha"] / (1 - b["alpha"]) for b in self.state["open"].values())      # costo máximo ya comprometido por campañas abiertas
            avail = max(self.wealth - committed, 0.0)
            a = self.f * avail / (1 + avail)
            self.state["open"][campaign_id] = dict(alpha=a, n_tests=n_tests); return a

    def settle(self, campaign_id: str, rejections: int) -> float:
        with self._tx():
            b = self.state["open"].pop(campaign_id)             # KeyError si no hubo apuesta previa: no se liquida lo que no se apostó (y no se escribe nada)
            a = b["alpha"]
            self.state["wealth"] += self.payout if rejections > 0 else -a / (1 - a)
            self.state["history"].append(dict(campaign=campaign_id, alpha=a, rejections=rejections, wealth_after=self.wealth))
            return self.wealth

    def open_bid(self, campaign_id: str):
        with self._tx():
            return self.state["open"].get(campaign_id)

    def release(self, campaign_id: str, reason: str = "") -> bool:
        """Devuelve la apuesta de una campaña que NO llegó a producir pruebas (falló antes de medir): no gasta riqueza ni recarga. Si hubo resultados parciales visibles no se debe usar."""
        with self._tx():
            b = self.state["open"].pop(campaign_id, None)
            if b is None: return False
            self.state["history"].append(dict(campaign=campaign_id, alpha=b["alpha"], rejections=0, released=True, reason=reason, wealth_after=self.wealth))
            return True

    def _save(self):
        tmp = Path(str(self.path) + ".tmp"); tmp.write_text(json.dumps(self.state, indent=1)); os.replace(tmp, self.path)


def holm_rejections(pvals: list, family_alpha: float, m: int | None = None) -> int:
    """Rechazos de Holm al nivel familiar `family_alpha` sobre `m` pruebas planeadas (m ≥ len(pvals); las no evaluables cuentan en m, no en el ranking)."""
    import math
    pvals = [p for p in pvals if isinstance(p, (int, float)) and math.isfinite(p) and 0.0 <= p <= 1.0]       # un p no finito o fuera de [0,1] no es evidencia: se descarta y el denominador planeado se mantiene
    m = max(m or len(pvals), len(pvals)); o = sorted(pvals); r = 0
    for k, p in enumerate(o):
        if p <= family_alpha / (m - k): r += 1
        else: break
    return r
