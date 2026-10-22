"""Regla de decisión `escalera_v1` del ciclo autónomo (auditoría del embudo, 2026-10-22). Se enciende con
`"decision": "escalera_v1"` en /etc/edgelab/autopilot.json; sin esa clave el ciclo sigue con Holm + alpha-investing (fdr.py, intacto).

Por qué: con alpha-investing (w0 = payout = 0,05) la riqueza quedó en 0,0025 tras 8 campañas, y cada campaña nueva se prueba con
Holm a ~0,001: el sistema ya no puede confirmar edges aunque existan (simulación: confirma 2 % de los edges reales moderados;
`docs/research/auditoria_embudo_20261022/SIMULACION_POTENCIA.json`). Reemplazo, con el mismo cuidado contra falsos positivos:
  - pruebas de DESCUBRIMIENTO (sin '/rep/'): tamiz FDR (BH-Storey, q = 0,10) sobre las planeadas -> NOMINADAS. No son acierto: abren
    pistas nuevas (WEAK_LEAD) que el generador puede llevar a réplica. Las no evaluables cuentan como p = 1 (no se omiten).
  - pruebas de RÉPLICA ('/rep/'): cada una con el nivel LORD++ que le toca en la secuencia global de confirmaciones del proyecto
    (FDR en línea, 0,05). Acierto = al menos una réplica confirmada. Igual que hoy, pasar sólo el descubrimiento no es acierto.
Idempotente por run_id: la decisión se guarda antes de que el ciclo escriba el libro; reintentar devuelve la misma decisión y no
gasta otra posición de la secuencia. Un solo escritor por directorio de estado (el lock del ciclo); escritura atómica.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from edgelab.funnel.escalera import LordPP, Q_TAMIZ, tamiz_fdr

from .analyze import records, valid_p

ARCHIVO = "confirmaciones_lordpp.json"


class Confirmacion:
    def __init__(self, root: Path, alfa: float = 0.05, q: float = Q_TAMIZ):
        self.path = Path(root) / ARCHIVO; self.q = q
        self.state = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else dict(lord=LordPP(alfa).to_dict(), corridas={})

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True); tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(self.state, indent=1, ensure_ascii=False), encoding="utf-8"); os.replace(tmp, self.path)

    def nivel_siguiente(self) -> float:
        return LordPP.from_dict(self.state["lord"]).nivel()

    def decidir(self, run_id: str, result: dict, n_planned: int) -> dict:
        if run_id in self.state["corridas"]:
            return self.state["corridas"][run_id]
        allrec = [r for r in records(result) if r["evaluable"] and r["p"] is not None]
        invalid = sorted(r["test"] for r in allrec if not valid_p(r["p"])); rec = [r for r in allrec if valid_p(r["p"])]
        disc = [r for r in rec if "/rep/" not in r["test"]]; rep = sorted((r for r in rec if "/rep/" in r["test"]), key=lambda r: r["test"])
        n_disc = max(n_planned - len(rep), len(disc))
        nominadas = []
        if disc:
            t = tamiz_fdr([r["p"] for r in disc] + [1.0] * (n_disc - len(disc)), self.q, "storey")
            nominadas = [disc[i]["test"] for i in t["nominadas"] if i < len(disc)]
        L = LordPP.from_dict(self.state["lord"]); conf = []
        for r in rep:                                          # orden determinista (nombre) para que el nivel no dependa del p
            x = L.probar(float(r["p"]), f"{run_id}:{r['test']}")
            if x["rechazo"]: conf.append(dict(test=r["test"], p=r["p"], nivel=x["nivel"]))
        d = dict(regla="escalera_v1", hit=bool(conf), rejections=len(conf), confirmadas=conf, nominadas=nominadas, n_evaluable=len(rec),
                 invalid_p_tests=invalid, n_planned=n_planned, q_tamiz=self.q, lord_t=L.t, family_alpha=None,
                 escalera=result.get("escalera"),          # veredicto de la escalera del embudo si el estudio lo produjo (lo exige la apertura del holdout)
                 top=sorted(rec, key=lambda r: r["p"])[:5], tier_hint="C (información) hasta que exista P&L neto, estabilidad y diversificación (mandato)",
                 note="nominar no es evidencia; confirmar en réplica tampoco es edge útil: falta la escalera económica (edgelab/funnel/escalera.py)")
        self.state["lord"] = L.to_dict(); self.state["corridas"][run_id] = d; self._save()
        return d


def registrar_nominadas(path: Path, spec, decision: dict) -> list:
    """Las nominadas del tamiz abren pistas nuevas en la evidencia viva (mismo formato que evidence.record_outcome)."""
    import time
    out = []; Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a", encoding="utf-8") as f:
        for t in decision.get("nominadas", []):
            row = dict(ts=time.time(), evidence_id=f"{spec.run_id}:{t}", run_id=spec.run_id, prev_status=None, status="WEAK_LEAD", consumed=[], hit=False,
                       rejected=[t], new_entry=dict(indicator=spec.family, asset=t, tier="C",
                                                    note=f"nominada por el tamiz FDR (q={decision.get('q_tamiz')}) en {spec.run_id}; necesita réplica pre-registrada en muestra no mirada",
                                                    unused_samples=["new_data_after_holdout"], sources=[spec.prereg]))
            f.write(json.dumps(row, ensure_ascii=False) + "\n"); out.append(row)
    return out
