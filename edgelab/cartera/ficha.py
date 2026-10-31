"""Ciclo de vida de cada estrategia de la cartera viva y su libro (JSON con escritura atómica + bitácora).

Niveles y estados (decisión de diseño 2026-10-31, docs/CARTERA_VIVA.md):
  PAPEL      entra RÁPIDO: cualquier regla congelada con pre-registro committeado (confirmada por el embudo, canasta de pistas vivas
             con prueba forward, variante nominada). No arriesga capital: se sigue cada día con el motor de siempre sobre datos nuevos.
             Entrar es abrir su ventana forward en el libro de ventanas (una por familia, `holdout_ventanas`), con e-proceso.
  REAL       habilitada para cuentas con dinero: e-proceso de edge >= 1/alfa_real con al menos `min_ops_real` operaciones forward, o
             confirmada por el embudo con acta. Qué cuentas operan es decisión humana (`cuentas[].habilitada`, CLAUDE.md).
  SUSPENDIDA (por día) el régimen de mañana le da afinidad 0: no opera, pero sigue en papel (no se pierde información).
  RETIRADA   futilidad del e-proceso, cota estructural violada o drawdown forward > dd_max_r × pérdida máxima. Inmediato. La misma
             regla congelada no vuelve sin otra confirmación en datos nuevos.
Asimetría deliberada: retirar es inmediato y automático; sumar riesgo exige evidencia acumulada (e-procesos válidos mirando todos
los días, Ville).
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from edgelab.funnel.secuencial import MonitorCandidato
from edgelab.research import holdout_ventanas as HV

DEFECTOS = dict(alfa_real=0.05, min_ops_real=30, alfa_futilidad=0.10, dd_max_r=8.0)


@dataclass
class Ficha:
    id: str
    familia: str
    cid: str
    instrumento: str
    regla: dict                      # spec (experimento, sensor, ejecucion), celda, cortes, tope: congelado
    preregistro: str
    perdida_max_pts: float
    ganancia_max_pts: float
    margen_hueco_pts: float
    friccion_pts: float
    mu_util: float
    sd_desarrollo: float
    desde: int                       # primera sesión forward (yyyymmdd)
    nivel: str = "PAPEL"             # PAPEL | REAL
    estado: str = "ACTIVA"           # ACTIVA | RETIRADA
    confirmada_por_embudo: bool = False
    motivo: str | None = None
    ops: list = field(default_factory=list)          # [[ses, neto_pts], ...] forward, en orden
    ops_desarrollo: list = field(default_factory=list)   # [[ses, neto_pts]] de DESC/OOS: sólo para la afinidad con el régimen
    alta_ts: float = 0.0

    def monitor(self, alfa_real: float, alfa_futilidad: float) -> MonitorCandidato:
        m = MonitorCandidato.desde_regla(perdida_max_pts=self.perdida_max_pts, ganancia_max_pts=self.ganancia_max_pts,
                                         friccion_pts=self.friccion_pts, margen_hueco_pts=self.margen_hueco_pts, mu_util=self.mu_util,
                                         alfa=alfa_real, alfa_futilidad=alfa_futilidad)
        if self.ops: m.agregar([x for _, x in self.ops])
        return m

    def ultima_ses(self) -> int:
        return int(self.ops[-1][0]) if self.ops else int(self.desde) - 1

    def drawdown(self) -> float:
        eq = pico = dd = 0.0
        for _, x in self.ops:
            eq += x; pico = max(pico, eq); dd = min(dd, eq - pico)
        return dd

    def huella(self) -> str:
        return json.dumps(dict(familia=self.familia, instrumento=self.instrumento, regla=self.regla), sort_keys=True, default=str)


class Cartera:
    def __init__(self, ruta: Path, reglas: dict | None = None, libro_ventanas: Path | None = None, ahora=time.time):
        self.ruta, self.ahora = Path(ruta), ahora
        self.libro_ventanas = Path(libro_ventanas) if libro_ventanas else HV.LIBRO
        d = json.loads(self.ruta.read_text(encoding="utf-8")) if self.ruta.exists() else {}
        self.reglas = {**DEFECTOS, **(d.get("reglas") or {}), **(reglas or {})}
        self.fichas = {k: Ficha(**v) for k, v in (d.get("fichas") or {}).items()}
        self.bitacora = d.get("bitacora", [])

    def guardar(self):
        self.ruta.parent.mkdir(parents=True, exist_ok=True); tmp = self.ruta.with_suffix(".tmp")
        tmp.write_text(json.dumps(dict(reglas=self.reglas, fichas={k: asdict(v) for k, v in self.fichas.items()}, bitacora=self.bitacora),
                                  indent=1, ensure_ascii=False, default=float), encoding="utf-8")
        tmp.replace(self.ruta)

    def _log(self, evento, id_, **datos):
        self.bitacora.append(dict(ts=self.ahora(), evento=evento, id=id_, **datos))

    def activas(self):
        return [f for f in self.fichas.values() if f.estado == "ACTIVA"]

    # --- alta: rápida, sin capital ----------------------------------------------------------------------------------------------
    def alta(self, f: Ficha, repo: Path | None = None) -> Ficha:
        pr = (Path(repo) / f.preregistro) if repo else Path(f.preregistro)
        if not pr.exists(): raise ValueError(f"ALTA rechazada: el pre-registro {f.preregistro} no existe (se escribe y committea antes)")
        if f.id in self.fichas: raise ValueError(f"ALTA rechazada: {f.id} ya existe")
        if any(v.estado == "RETIRADA" and v.huella() == f.huella() for v in self.fichas.values()):
            raise ValueError("ALTA rechazada: esta regla congelada ya fue retirada; necesita otra confirmación en datos nuevos")
        if min(f.perdida_max_pts, f.ganancia_max_pts, f.sd_desarrollo, f.mu_util) <= 0:
            raise ValueError("ALTA rechazada: cotas estructurales, desvío y efecto útil positivos, declarados antes")
        pb = HV.problemas(f.familia, f.desde, f.cid, self.libro_ventanas, estadistico="e_proceso")
        if pb: raise ValueError(f"ALTA rechazada por el libro de ventanas: {pb}")
        HV.registrar_apertura(f.familia, f.cid, f.desde, 0, self.libro_ventanas)
        f.monitor(self.reglas["alfa_real"], self.reglas["alfa_futilidad"])            # valida las cotas
        f.alta_ts, f.estado = self.ahora(), "ACTIVA"
        if f.confirmada_por_embudo: f.nivel = "REAL"
        self.fichas[f.id] = f; self._log("ALTA", f.id, nivel=f.nivel, preregistro=f.preregistro); self.guardar(); return f

    # --- seguimiento -------------------------------------------------------------------------------------------------------------
    def agregar_ops(self, id_: str, filas) -> dict:
        """filas: [(ses, neto_pts)] de sesiones posteriores a la última registrada (idempotente: lo ya visto se ignora)."""
        f = self.fichas[id_]
        if f.estado != "ACTIVA": return dict(id=id_, estado=f.estado)
        nuevas = sorted([(int(s), float(x)) for s, x in filas if int(s) > f.ultima_ses() and int(s) >= f.desde])
        try:
            st = f.monitor(self.reglas["alfa_real"], self.reglas["alfa_futilidad"]).agregar([x for _, x in nuevas]) if nuevas else \
                f.monitor(self.reglas["alfa_real"], self.reglas["alfa_futilidad"]).estado()
        except ValueError as ex:
            f.ops += [list(r) for r in nuevas]; return self.retirar(id_, f"cota estructural violada: {ex}")
        f.ops += [list(r) for r in nuevas]
        if st["estado"] == "REFUTADO_FUTILIDAD":
            return self.retirar(id_, f"futilidad: E[x] < mu_util {f.mu_util} (e {st['e_futilidad']:.1f}, n {st['n']})")
        if f.drawdown() < -self.reglas["dd_max_r"] * f.perdida_max_pts:
            return self.retirar(id_, f"drawdown forward {f.drawdown():.1f} < −{self.reglas['dd_max_r']} × {f.perdida_max_pts}")
        if f.nivel == "PAPEL" and st["estado"] == "EDGE_CONFIRMADO" and st["n"] >= self.reglas["min_ops_real"]:
            f.nivel = "REAL"; self._log("PROMOCION", id_, e=st["e_edge"], n=st["n"])
        self.guardar(); return dict(id=id_, estado=f.estado, nivel=f.nivel, nuevas=len(nuevas), monitor=st)

    def retirar(self, id_: str, motivo: str) -> dict:
        f = self.fichas[id_]; f.estado, f.motivo = "RETIRADA", motivo
        self._log("RETIRO", id_, motivo=motivo, n=len(f.ops), neto=sum(x for _, x in f.ops)); self.guardar()
        return dict(id=id_, estado="RETIRADA", motivo=motivo)
