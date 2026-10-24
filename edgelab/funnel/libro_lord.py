"""Libro persistente de LORD++ por familia (2026-10-23). Antes el nivel de cada confirmación se recalculaba a mano en cada
script (error de la revisión del 2026-10-23); ahora cada lote de réplicas, OOS u holdout de una familia consume UN paso del
libro, de forma idempotente por `run_id` (repetir no gasta dos veces) y con escritura atómica.

Decisión del 2026-10-24 (docs/research/revision_20261024/DECISIONES_VALIDACION_20261024.md, aprobada por Nico):
  - RUTA FIJA: hay un solo libro, `RUTA_CANONICA` (versionado en el repo, como HOLDOUT_VENTANAS). Antes el ciclo del Debian
    usaba <root>/libro_lord.json y `tools/embudo_correr.py` el que le pasaran: dos libros = el mismo α gastado dos veces.
    Otra ruta sólo con `permitir_otra_ruta=True` (tests y simulaciones).
  - LOCK: toda lectura-modificación-escritura se hace con un lock exclusivo del sistema operativo y releyendo el disco adentro
    del lock (dos procesos no pueden calcular el mismo nivel ni pisarse el paso).
  - RESERVA POR ACTA: `reservar` consume el paso de la familia en el momento del acta, con su nivel fijo; `resolver` decide
    después, con el p del holdout, a ese nivel. Antes el acta anotaba `nivel()` sin descontarlo, así que dos actas de la misma
    familia (o un OOS entre medio) se adjudicaban el mismo α.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path

from edgelab.funnel.escalera import LordPP, decidir_lote, probar_lote

RUTA_CANONICA = Path(__file__).resolve().parents[2] / "docs/research/LIBRO_LORD.json"


@contextmanager
def _bloqueo(ruta: Path):
    lk = ruta.with_name(ruta.name + ".lock"); lk.parent.mkdir(parents=True, exist_ok=True)
    with open(lk, "a+b") as f:
        if os.name == "nt":                                                            # máquina Windows de Nico
            import msvcrt
            f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            try: yield
            finally: f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        else:                                                                          # Debian
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX)
            try: yield
            finally: fcntl.flock(f, fcntl.LOCK_UN)


class LibroLord:
    def __init__(self, ruta: Path | None = None, alfa: float = 0.05, *, permitir_otra_ruta: bool = False):
        self.ruta = Path(ruta) if ruta is not None else RUTA_CANONICA
        if self.ruta.resolve() != RUTA_CANONICA.resolve() and not permitir_otra_ruta:
            raise ValueError(f"el libro de LORD++ es uno solo ({RUTA_CANONICA}); otra ruta ({self.ruta}) gastaría el mismo α dos veces. "
                             "Para tests: permitir_otra_ruta=True")
        self.alfa = alfa

    @property
    def estado(self) -> dict:
        return json.loads(self.ruta.read_text(encoding="utf-8")) if self.ruta.exists() else dict(familias={}, corridas={}, reservas={})

    def _guardar(self, estado):
        self.ruta.parent.mkdir(parents=True, exist_ok=True); tmp = self.ruta.with_suffix(".tmp")
        tmp.write_text(json.dumps(estado, indent=1, ensure_ascii=False, default=float), encoding="utf-8"); os.replace(tmp, self.ruta)

    def nivel(self, familia: str) -> float:
        return self._lord(self.estado, familia).nivel()

    def _lord(self, estado, familia):
        d = estado["familias"].get(familia)
        return LordPP.from_dict(d) if d else LordPP(self.alfa)

    def probar(self, familia: str, run_id: str, pruebas: list, etiqueta: str = "") -> dict:
        """pruebas: [(nombre, p)]. Un lote = un paso. Idempotente: el mismo run_id devuelve la decisión ya tomada."""
        clave = f"{familia}::{run_id}"
        with _bloqueo(self.ruta):
            est = self.estado
            if clave in est["corridas"]: return est["corridas"][clave]
            L = self._lord(est, familia); r = probar_lote(L, [(n, float(p)) for n, p in pruebas], etiqueta or run_id)
            est["familias"][familia] = L.to_dict(); est["corridas"][clave] = dict(r, familia=familia, run_id=run_id)
            self._guardar(est)
            return est["corridas"][clave]

    def reservar(self, familia: str, reserva_id: str, etiqueta: str = "") -> dict:
        """Consume un paso de la familia AHORA y fija su nivel (lo usa el acta del holdout, antes de mirar). Idempotente."""
        clave = f"{familia}::{reserva_id}"
        with _bloqueo(self.ruta):
            est = self.estado; est.setdefault("reservas", {})
            if clave in est["reservas"]: return est["reservas"][clave]
            L = self._lord(est, familia); r = L.reservar(etiqueta or reserva_id)
            est["familias"][familia] = L.to_dict()
            est["reservas"][clave] = dict(familia=familia, reserva_id=reserva_id, t=r["t"], nivel=r["nivel"], resuelta=False)
            self._guardar(est)
            return est["reservas"][clave]

    def resolver(self, familia: str, reserva_id: str, pruebas: list) -> dict:
        """Decide el lote al nivel reservado (Simes + BH, como `probar`). Idempotente: una reserva se resuelve una sola vez."""
        clave = f"{familia}::{reserva_id}"
        with _bloqueo(self.ruta):
            est = self.estado; res = (est.get("reservas") or {}).get(clave)
            if res is None: raise KeyError(f"no hay reserva {clave}: el acta no reservó α")
            if res["resuelta"]: return res["decision"]
            d = decidir_lote(res["nivel"], [(n, float(p)) for n, p in pruebas])
            L = self._lord(est, familia); L.resolver(res["t"], d["p_simes"] if d["p_simes"] is not None else 1.0)
            d = dict(d, t=res["t"], familia=familia, run_id=reserva_id, reservada=True)
            est["familias"][familia] = L.to_dict(); res.update(resuelta=True, decision=d); est["corridas"][clave] = d
            self._guardar(est)
            return d
