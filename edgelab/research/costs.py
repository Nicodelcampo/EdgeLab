"""Escenarios de costos — FUENTE ÚNICA en código (F3c).

Refleja `docs/edge_validation_contract.md` §G3 (tabla de escenarios) y
`docs/campaigns/CAMP-001_gaps2_discovery.md` §7 (componentes de comisión).
El simulador NO define números propios: recibe un `CostScenario` de acá.

| Escenario | Slippage (ticks/pata) | Comisión |
|---|---|---|
| ideal (SOLO diagnóstico) | 0 | 0 |
| base | 1 (stops 1) | plena |
| adverso | 2 (stops 2) | plena |
| severo | 3 (stops 3) | plena |
"""
from __future__ import annotations

from dataclasses import dataclass

# Comisión por pata ejecutada, 6E (Euro FX Futures, CME).
#
# CONFIRMADA 2026-08-06 en la fuente oficial: LucidTrading, "Approved Products
# and Commissions" (artículo del 2026-02-09),
# https://support.lucidtrading.com/en/articles/11508978-approved-products-and-commissions
# Tabla: `6E · Euro FX Futures · Commission (Per Side) 2.40 · CME`.
#
# Esto cierra el «dato faltante #1» del manifiesto de CAMP-001, que llevaba
# **$2,20 PRE-REGISTRADA COMO ESTIMACIÓN**. El valor real es **$2,40**: la
# estimación subestimaba la fricción en $0,40 por round turn.
#
# LIMITACIÓN DECLARADA, no disimulada: `edge_validation_contract.md` §G3 pide el
# modelo de costos **desglosado** (broker + exchange/clearing + NFA). Lucid
# publica **un solo número all-in por pata** y no lo desglosa. Así que G3 puede
# usar el total real, pero el desglose por componente NO es acreditable desde
# esta fuente. Inventar un reparto sería peor que no tenerlo.
COMMISSION_PER_SIDE_USD = 2.40

#: Valor que la spec SELLADA del simulador declara para sus golden tests
#: (`execution_simulator_spec.md` §9: "6E … comisión $2.20/pata (RT $4.40)").
#: Vive acá y NO se mezcla con el de producción: los golden prueban la
#: ARITMÉTICA del simulador, no cuánto cobra el broker hoy. Estaban leyendo
#: `COMMISSION_PER_SIDE_USD`, así que un hecho de mercado podía romper un
#: contrato sellado — acoplamiento accidental, no decisión.
GOLDEN_SPEC_COMMISSION_PER_SIDE_USD = 2.20


@dataclass(frozen=True)
class CostScenario:
    """Slippage en TICKS por pata, comisión en USD por pata."""
    name: str
    slip_entry: int
    slip_target: int
    slip_stop: int
    slip_exit: int          # salidas market (time stop, session close, data edge)
    commission_per_side_usd: float


SCENARIOS = {
    "ideal":   CostScenario("ideal", 0, 0, 0, 0, 0.0),
    "base":    CostScenario("base", 1, 1, 1, 1, COMMISSION_PER_SIDE_USD),
    "adverso": CostScenario("adverso", 2, 2, 2, 2, COMMISSION_PER_SIDE_USD),
    "severo":  CostScenario("severo", 3, 3, 3, 3, COMMISSION_PER_SIDE_USD),
}


def get_scenario(name):
    if name not in SCENARIOS:
        raise KeyError("escenario desconocido: %r (validos: %s)"
                       % (name, sorted(SCENARIOS)))
    return SCENARIOS[name]
