"""Libro persistente de LORD++ por familia (2026-10-23). Antes el nivel de cada confirmación se recalculaba a mano en cada
script (error de la revisión del 2026-10-23); ahora cada lote de réplicas, OOS u holdout de una familia consume UN paso del
libro, de forma idempotente por `run_id` (repetir no gasta dos veces) y con escritura atómica."""
from __future__ import annotations

import json
import os
from pathlib import Path

from edgelab.funnel.escalera import LordPP, probar_lote


class LibroLord:
    def __init__(self, ruta: Path, alfa: float = 0.05):
        self.ruta, self.alfa = Path(ruta), alfa
        self.estado = json.loads(self.ruta.read_text(encoding="utf-8")) if self.ruta.exists() else dict(familias={}, corridas={})

    def _guardar(self):
        self.ruta.parent.mkdir(parents=True, exist_ok=True); tmp = self.ruta.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.estado, indent=1, ensure_ascii=False, default=float), encoding="utf-8"); os.replace(tmp, self.ruta)

    def nivel(self, familia: str) -> float:
        return self._lord(familia).nivel()

    def _lord(self, familia):
        d = self.estado["familias"].get(familia)
        return LordPP.from_dict(d) if d else LordPP(self.alfa)

    def probar(self, familia: str, run_id: str, pruebas: list, etiqueta: str = "") -> dict:
        """pruebas: [(nombre, p)]. Un lote = un paso. Idempotente: el mismo run_id devuelve la decisión ya tomada."""
        clave = f"{familia}::{run_id}"
        if clave in self.estado["corridas"]: return self.estado["corridas"][clave]
        L = self._lord(familia); r = probar_lote(L, [(n, float(p)) for n, p in pruebas], etiqueta or run_id)
        self.estado["familias"][familia] = L.to_dict(); self.estado["corridas"][clave] = dict(r, familia=familia, run_id=run_id)
        self._guardar()
        return self.estado["corridas"][clave]
