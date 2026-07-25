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

# CAMP-001 §7: comisión broker + exchange/clearing + NFA por pata ejecutada.
# PRE-REGISTRADA COMO ESTIMACIÓN — pendiente de confirmar con estados de cuenta
# reales de Nico (dato faltante #1 del manifiesto). Bloquea G3, no el sellado.
COMMISSION_PER_SIDE_USD = 2.20


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
