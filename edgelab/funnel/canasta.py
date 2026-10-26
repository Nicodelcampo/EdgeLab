"""Canasta de estrategias de régimen (2026-10-26, tesis de Nico): el valor está en renovar rápido — sumar lo que confirma en lo más
reciente, ponderar, retirar lo que deja de funcionar. Esta capa va ARRIBA del embudo; no descubre ni confirma nada por sí misma.

Reglas (declaradas acá, antes de que haya ninguna estrategia adentro):
  ALTA      sólo una regla CONGELADA que terminó el embudo en CONFIRMADA (holdout a N fijo o e-proceso, con su acta) y declara cotas
            estructurales (pérdida y ganancia máximas por operación, margen de hueco) y su efecto útil `mu_util`. Una regla retirada no
            vuelve a entrar con la misma configuración: necesita otra confirmación en datos nuevos (nunca se «resucita» mirando).
  SEGUIMIENTO cada operación forward (paper o real) entra a un `MonitorCandidato` (e-procesos, válidos mirando en cualquier momento) y a
            la curva de la estrategia.
  RETIRO    (a) futilidad: el e-proceso demuestra E[x] < mu_util (el edge, si queda, ya no es útil); (b) drawdown forward mayor que
            `dd_max_r` veces la pérdida máxima por operación; (c) retiro manual con motivo. El retiro es inmediato y queda registrado.
  PESO      riesgo igual: peso ∝ 1 / desvío por operación (de desarrollo hasta tener `min_ops_peso` operaciones forward; después el
            forward), con tope `peso_max` por estrategia y `peso_max_instrumento` por instrumento; se renormaliza sobre las activas. Si los topes no dejan llegar a 1, el resto queda sin asignar (no se concentra para «llenar»).
Operar con dinero real sigue siendo decisión humana (CLAUDE.md): la canasta propone pesos, no ejecuta.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from edgelab.funnel.secuencial import MonitorCandidato

DEFECTOS = dict(peso_max=0.25, peso_max_instrumento=0.5, dd_max_r=8.0, min_ops_peso=30, alfa_futilidad=0.10)


@dataclass
class Estrategia:
    id: str
    familia: str
    instrumento: str
    regla: dict                      # celda, tope, cortes, experimento: lo que la define, congelado
    acta: str                        # ruta del acta/estado del embudo que la confirmó
    perdida_max_pts: float
    ganancia_max_pts: float
    margen_hueco_pts: float
    friccion_pts: float
    mu_util: float
    sd_desarrollo: float
    alta_ts: float = 0.0
    estado: str = "ACTIVA"           # ACTIVA | RETIRADA
    motivo_retiro: str | None = None
    ops: list = field(default_factory=list)

    def monitor(self, alfa_futilidad: float) -> MonitorCandidato:
        m = MonitorCandidato.desde_regla(perdida_max_pts=self.perdida_max_pts, ganancia_max_pts=self.ganancia_max_pts,
                                         friccion_pts=self.friccion_pts, margen_hueco_pts=self.margen_hueco_pts, mu_util=self.mu_util,
                                         alfa_futilidad=alfa_futilidad)
        if self.ops: m.agregar(self.ops)
        return m

    def drawdown(self) -> float:
        eq = pico = dd = 0.0
        for x in self.ops:
            eq += x; pico = max(pico, eq); dd = min(dd, eq - pico)
        return dd

    def huella(self) -> str:
        return json.dumps(dict(familia=self.familia, instrumento=self.instrumento, regla=self.regla), sort_keys=True, default=str)


class Canasta:
    def __init__(self, ruta: Path, reglas: dict | None = None, ahora=time.time):
        self.ruta, self.ahora = Path(ruta), ahora
        d = json.loads(self.ruta.read_text(encoding="utf-8")) if self.ruta.exists() else {}
        self.reglas = {**DEFECTOS, **(d.get("reglas") or {}), **(reglas or {})}
        self.estrategias = {k: Estrategia(**v) for k, v in (d.get("estrategias") or {}).items()}
        self.bitacora = d.get("bitacora", [])

    def _guardar(self):
        self.ruta.parent.mkdir(parents=True, exist_ok=True); tmp = self.ruta.with_suffix(".tmp")
        tmp.write_text(json.dumps(dict(reglas=self.reglas, estrategias={k: asdict(v) for k, v in self.estrategias.items()},
                                       bitacora=self.bitacora), indent=1, ensure_ascii=False, default=float), encoding="utf-8")
        tmp.replace(self.ruta)

    def _log(self, evento, id_, **datos):
        self.bitacora.append(dict(ts=self.ahora(), evento=evento, id=id_, **datos))

    # --- alta -----------------------------------------------------------------------------------------------------------
    def alta(self, e: Estrategia, estado_embudo: dict) -> Estrategia:
        if estado_embudo.get("fase") != "CONFIRMADA":
            raise ValueError(f"ALTA rechazada: el embudo no la confirmó (fase {estado_embudo.get('fase')!r})")
        if e.id in self.estrategias: raise ValueError(f"ALTA rechazada: {e.id} ya existe")
        if any(v.estado == "RETIRADA" and v.huella() == e.huella() for v in self.estrategias.values()):
            raise ValueError("ALTA rechazada: la misma regla congelada ya fue retirada; hace falta otra confirmación en datos nuevos")
        if min(e.perdida_max_pts, e.ganancia_max_pts, e.sd_desarrollo, e.mu_util) <= 0:
            raise ValueError("ALTA rechazada: cotas estructurales, desvío y efecto útil positivos, declarados antes")
        e.alta_ts, e.estado, e.ops = self.ahora(), "ACTIVA", []
        e.monitor(self.reglas["alfa_futilidad"])                                  # valida las cotas
        self.estrategias[e.id] = e; self._log("ALTA", e.id, acta=e.acta); self._guardar(); return e

    # --- seguimiento y retiro ------------------------------------------------------------------------------------------------
    def operaciones(self, id_: str, xs) -> dict:
        e = self.estrategias[id_]
        if e.estado != "ACTIVA": raise ValueError(f"{id_} está {e.estado}: no recibe operaciones")
        nuevas = [float(x) for x in ([xs] if isinstance(xs, (int, float)) else xs)]
        try:
            m = e.monitor(self.reglas["alfa_futilidad"]); st = m.agregar(nuevas)
        except ValueError as ex:                                                   # LIMITE_VIOLADO: la regla rompió su cota
            e.ops += nuevas; return self.retirar(id_, f"cota estructural violada: {ex}")
        e.ops += nuevas
        if st["estado"] == "REFUTADO_FUTILIDAD":
            return self.retirar(id_, f"futilidad: E[x] < mu_util {e.mu_util} con e {st['e_futilidad']:.1f} (n {st['n']})")
        dd = e.drawdown()
        if dd < -self.reglas["dd_max_r"] * e.perdida_max_pts:
            return self.retirar(id_, f"drawdown forward {dd:.2f} < −{self.reglas['dd_max_r']} × pérdida máxima {e.perdida_max_pts}")
        self._guardar(); return dict(id=id_, estado="ACTIVA", monitor=st, drawdown=dd)

    def retirar(self, id_: str, motivo: str) -> dict:
        e = self.estrategias[id_]; e.estado, e.motivo_retiro = "RETIRADA", motivo
        self._log("RETIRO", id_, motivo=motivo, n=len(e.ops), neto=sum(e.ops)); self._guardar()
        return dict(id=id_, estado="RETIRADA", motivo=motivo)

    # --- pesos y reporte -----------------------------------------------------------------------------------------------------
    def pesos(self) -> dict:
        act = [e for e in self.estrategias.values() if e.estado == "ACTIVA"]
        if not act: return {}
        def sd(e):
            if len(e.ops) >= self.reglas["min_ops_peso"]:
                m = sum(e.ops) / len(e.ops); return math.sqrt(sum((x - m) ** 2 for x in e.ops) / (len(e.ops) - 1)) or e.sd_desarrollo
            return e.sd_desarrollo
        raw = {e.id: 1 / sd(e) for e in act}; inst = {e.id: e.instrumento for e in act}
        fijos: dict = {}                                                           # llenado por niveles: lo que toca un tope queda fijo
        for _ in range(4 * len(act) + 4):
            libres = [k for k in raw if k not in fijos]; resto = 1.0 - sum(fijos.values())
            if not libres or resto <= 0: break
            tot = sum(raw[k] for k in libres); w = {**fijos, **{k: resto * raw[k] / tot for k in libres}}
            viol = [k for k in libres if w[k] > self.reglas["peso_max"] + 1e-12]
            if viol:
                for k in viol: fijos[k] = self.reglas["peso_max"]
                continue
            grupos = {}
            for k in raw: grupos.setdefault(inst[k], []).append(k)
            excedido = next((g for g in grupos.values() if sum(w[k] for k in g) > self.reglas["peso_max_instrumento"] + 1e-12
                             and any(k not in fijos for k in g)), None)
            if excedido is None: return w
            s_ = sum(w[k] for k in excedido)
            for k in excedido: fijos[k] = w[k] * self.reglas["peso_max_instrumento"] / s_
        w = {**{k: 0.0 for k in raw}, **fijos}
        return w

    def reporte(self) -> dict:
        w = self.pesos(); filas = []
        for e in self.estrategias.values():
            st = e.monitor(self.reglas["alfa_futilidad"]).estado() if e.estado == "ACTIVA" else None
            filas.append(dict(id=e.id, familia=e.familia, instrumento=e.instrumento, estado=e.estado, motivo_retiro=e.motivo_retiro,
                              n_forward=len(e.ops), neto_forward=sum(e.ops), drawdown=e.drawdown(), peso=w.get(e.id, 0.0),
                              monitor=st))
        nota = None if any(f["peso"] for f in filas) else "sin pesos asignados: la canasta propone pesos cuando hay estrategias ACTIVAS"
        return dict(reglas=self.reglas, estrategias=filas, activas=sum(f["estado"] == "ACTIVA" for f in filas), nota=nota)
