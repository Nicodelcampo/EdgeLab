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
COMMISSIONS_PER_SIDE_USD: dict[str, float] = {
    "6E": 2.40,
    "ES": 2.40,
    "NQ": 2.40,
    "YM": 2.40,
    "ZB": 2.40,
}
COMMISSION_PER_SIDE_USD = 2.40

#: Valor que la spec SELLADA del simulador declara para sus golden tests
#: (`execution_simulator_spec.md` §9: "6E … comisión $2.20/pata (RT $4.40)").
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


def get_scenario(name: str, instrument: str = "6E") -> CostScenario:
    if name not in SCENARIOS:
        raise KeyError("escenario desconocido: %r (validos: %s)"
                       % (name, sorted(SCENARIOS)))
    sc = SCENARIOS[name]
    comm = COMMISSIONS_PER_SIDE_USD.get(instrument, COMMISSION_PER_SIDE_USD) if name != "ideal" else 0.0
    return CostScenario(
        name=sc.name,
        slip_entry=sc.slip_entry,
        slip_target=sc.slip_target,
        slip_stop=sc.slip_stop,
        slip_exit=sc.slip_exit,
        commission_per_side_usd=comm,
    )


# --- FUENTE UNICA de la friccion round-turn -------------------------------
#: 6E: 1 tick = $6,25. El escenario `base` cobra 1 tick de slippage por pata.
TICK_VALUE_USD_6E = 6.25
TICK_VALUES_USD: dict[str, float] = {
    "6E": 6.25,
    "ES": 12.50,
    "NQ": 5.00,
    "YM": 5.00,
    "ZB": 31.25,
}


def friccion_rt_ticks(scenario="base", tick_value_usd=None, instrument="6E") -> float:
    """Friccion round-turn en TICKS: comision + slippage de entrada y salida."""
    sc = get_scenario(scenario, instrument=instrument) if isinstance(scenario, str) else scenario
    tk_val = tick_value_usd or TICK_VALUES_USD.get(instrument, TICK_VALUE_USD_6E)
    comision_rt = 2 * sc.commission_per_side_usd
    slippage_rt_ticks = sc.slip_entry + sc.slip_exit
    return comision_rt / tk_val + slippage_rt_ticks


def friccion_rt_usd(scenario="base", instrument="6E") -> float:
    """Friccion round-turn total en USD (comision + slippage)."""
    sc = get_scenario(scenario, instrument=instrument) if isinstance(scenario, str) else scenario
    tk_val = TICK_VALUES_USD.get(instrument, TICK_VALUE_USD_6E)
    comision_rt = 2 * sc.commission_per_side_usd
    slippage_usd = (sc.slip_entry + sc.slip_exit) * tk_val
    return comision_rt + slippage_usd
