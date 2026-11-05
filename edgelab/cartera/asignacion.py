"""Riesgo y contratos por cuenta para el día (prop firms, Axi Select, capital propio).

Presupuesto de riesgo del día de una cuenta = min(fraccion_dia × límite de pérdida diaria, fraccion_dd × distancia al piso de
drawdown). Si TODAS las posiciones del día pierden su máximo, la cuenta pierde a lo sumo ese presupuesto: el piso de la prop firm no se
toca en un solo día. Pesos entre estrategias: riesgo igual (1/desvío) × multiplicador de régimen, con los topes por estrategia e
instrumento de `funnel.canasta.Canasta.pesos` (reutilizado). Contratos = piso(presupuesto × peso / riesgo por contrato), donde riesgo
por contrato = pérdida máxima estructural en puntos × USD por punto del contrato que usa la cuenta (micro por defecto).
Las cuentas reales sólo reciben estrategias de nivel REAL y sólo si una persona las habilitó (`habilitada`, CLAUDE.md: operar con
dinero real es decisión humana). Una cuenta DEMO recibe todas las ACTIVAS: es el banco de prueba de ejecución.
"""
from __future__ import annotations

import math
from pathlib import Path

from edgelab.funnel.canasta import Canasta, Estrategia

USD_POR_PUNTO = {"MNQ": 2.0, "NQ": 20.0, "MES": 5.0, "ES": 50.0, "MYM": 0.5, "YM": 5.0, "MGC": 10.0, "GC": 100.0}
MICRO = {"NQ": "MNQ", "ES": "MES", "YM": "MYM", "GC": "MGC"}


def presupuesto_usd(cuenta: dict, reglas_firma=None) -> float:
    if reglas_firma is not None:
        dll = reglas_firma.daily_loss_limit or reglas_firma.max_loss / 2
        dd = cuenta.get("distancia_piso_usd") or reglas_firma.max_loss
    else:
        dll, dd = cuenta["perdida_dia_max_usd"], cuenta["drawdown_max_usd"]
    return max(0.0, min(cuenta.get("fraccion_dia", 0.5) * dll, cuenta.get("fraccion_dd", 0.25) * dd))


def pesos(fichas, multiplicadores: dict, peso_max=0.25, peso_max_instrumento=0.5) -> dict:
    c = Canasta(Path("/nonexistent/cartera_pesos.json"), reglas=dict(peso_max=peso_max, peso_max_instrumento=peso_max_instrumento))
    for f in fichas:
        m = multiplicadores.get(f.id, 1.0)
        if m <= 0: continue
        sd = f.sd_desarrollo
        if len(f.ops) >= 30:
            xs = [x for _, x in f.ops]; mu = sum(xs) / len(xs); sd = math.sqrt(sum((x - mu) ** 2 for x in xs) / (len(xs) - 1)) or sd
        c.estrategias[f.id] = Estrategia(id=f.id, familia=f.familia, instrumento=f.instrumento, regla=f.regla, acta=f.preregistro,
                                         perdida_max_pts=f.perdida_max_pts, ganancia_max_pts=f.ganancia_max_pts, margen_hueco_pts=f.margen_hueco_pts,
                                         friccion_pts=f.friccion_pts, mu_util=f.mu_util, sd_desarrollo=sd / m)
    return c.pesos()


def asignar(cuenta: dict, fichas, multiplicadores: dict, reglas_firma=None, peso_max=0.25, peso_max_instrumento=0.5) -> dict:
    tipo = cuenta.get("tipo", "demo")
    if tipo != "demo" and not cuenta.get("habilitada"):
        return dict(cuenta=cuenta["id"], tipo=tipo, operar=False, motivo="cuenta real sin habilitar por una persona", posiciones=[])
    if reglas_firma is not None and str(getattr(reglas_firma, "algo_policy", "") or "").lower().startswith("prohib") and not cuenta.get("ejecucion_manual"):
        return dict(cuenta=cuenta["id"], tipo=tipo, operar=False, motivo=f"{reglas_firma.firm} prohíbe algoritmos", posiciones=[])
    inst_ok = set(cuenta.get("instrumentos") or [])
    eleg = [f for f in fichas if f.estado == "ACTIVA" and (tipo == "demo" or f.nivel == "REAL") and (not inst_ok or f.instrumento in inst_ok)]
    w = pesos(eleg, multiplicadores, peso_max, peso_max_instrumento)
    pres = presupuesto_usd(cuenta, reglas_firma); filas = []; usado = 0.0
    maxc = getattr(reglas_firma, "max_contracts", None) if reglas_firma is not None else cuenta.get("max_contratos")
    for f in eleg:
        contrato = cuenta.get("contrato", {}).get(f.instrumento) or MICRO.get(f.instrumento, f.instrumento)
        rpc = f.perdida_max_pts * USD_POR_PUNTO.get(contrato, cuenta.get("usd_por_punto", {}).get(contrato, float("nan")))
        n = int(math.floor(pres * w.get(f.id, 0.0) / rpc)) if rpc and rpc == rpc and rpc > 0 else 0
        if maxc: n = min(n, int(maxc))
        usado += n * (rpc if rpc == rpc else 0.0)
        filas.append(dict(estrategia=f.id, instrumento=f.instrumento, contrato=contrato, contratos=n, peso=round(w.get(f.id, 0.0), 4),
                          multiplicador_regimen=round(multiplicadores.get(f.id, 1.0), 3), riesgo_usd=round(n * rpc, 2) if rpc == rpc else None,
                          nivel=f.nivel))
    return dict(cuenta=cuenta["id"], tipo=tipo, operar=True, presupuesto_usd=round(pres, 2), riesgo_asignado_usd=round(usado, 2),
                stop_dia_usd=round(pres, 2), posiciones=filas)
