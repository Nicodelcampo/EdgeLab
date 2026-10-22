"""Costos de ejecución CANÓNICOS: una sola fuente para spread, comisión y slippage (pedido de Nico, 2026-10-22).

Los números viven en `config/costos/costos_canonicos.json` (citado a `docs/research/REFERENCIA_COSTOS_PROPS_BROKERS_20261014.md`);
este módulo sólo los lee y compone. Antes había ~20 tablas locales en scripts que daban para NQ entre 0,9 y 6,18 ticks por viaje.

    from edgelab import costos
    costos.friccion_rt_ticks("NQ")                        # 6,18: spread + comisión máx. + 2 ticks (escenario base)
    costos.friccion_rt_ticks("NQ", "adverso")             # slippage 2 ticks por pata
    costos.friccion_rt_ticks("NQ", incluye_spread=False)  # para simuladores que ya llenan contra bid/ask
    costos.friccion_rt_puntos("NQ")                       # lo mismo en puntos de precio
    costos.desglose("NQ")                                 # componentes, rango min-max y fuentes

Regla dura: un instrumento sin un componente medido NO recibe el de otro (CostoNoMedido).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

RUTA = Path(__file__).resolve().parents[1] / "config" / "costos" / "costos_canonicos.json"
ESCENARIOS = ("ideal", "base", "adverso", "severo")


class CostoNoMedido(KeyError):
    """Falta un componente medido para ese instrumento: no se transporta de otro."""


@lru_cache(maxsize=1)
def tabla() -> dict:
    return json.loads(RUTA.read_text(encoding="utf-8"))


def _inst(instrumento: str) -> dict:
    t = tabla()["instrumentos"]; k = str(instrumento).upper()
    if k not in t:
        raise CostoNoMedido(f"{instrumento}: sin costos canónicos (agregarlo a {RUTA.name} con su fuente; no se presta de otro)")
    return t[k]


def comision_rt_usd(instrumento: str, criterio: str = "max") -> float:
    """Comisión ida y vuelta por contrato. criterio: 'max' (techo, el de decisión) o 'min', sobre las firmas que admiten algoritmos."""
    c = _inst(instrumento)["comision_rt_usd"]; ok = set(tabla()["firmas_que_admiten_algoritmos"])
    v = [x for f, x in c.items() if f in ok]
    if not v:
        raise CostoNoMedido(f"{instrumento}: ninguna firma que admita algoritmos publica su comisión")
    return float(max(v) if criterio == "max" else min(v))


def tick_value_usd(instrumento: str) -> float:
    return float(_inst(instrumento)["tick_value_usd"])


def tick_size(instrumento: str) -> float:
    return float(_inst(instrumento)["tick_size"])


def spread_ticks(instrumento: str) -> float:
    s = _inst(instrumento)["spread_ticks"]
    if s is None:
        raise CostoNoMedido(f"{instrumento}: spread sin medir; medirlo antes (no se presta de otro instrumento)")
    return float(s)


def slippage_rt_ticks(escenario: str = "base") -> float:
    if escenario not in ESCENARIOS:
        raise ValueError(f"escenario {escenario!r}: válidos {ESCENARIOS}")
    return 2.0 * tabla()["escenarios_slippage_ticks_por_pata"][escenario]


def friccion_rt_ticks(instrumento: str, escenario: str = "base", incluye_spread: bool = True, criterio: str = "max") -> float:
    """Fricción por viaje redondo en ticks = spread (si corresponde) + comisión + slippage del escenario. 'ideal' es 0 (sólo diagnóstico)."""
    if escenario == "ideal":
        return 0.0
    com = comision_rt_usd(instrumento, criterio) / tick_value_usd(instrumento)
    return (spread_ticks(instrumento) if incluye_spread else 0.0) + com + slippage_rt_ticks(escenario)


def friccion_rt_puntos(instrumento: str, escenario: str = "base", incluye_spread: bool = True, criterio: str = "max") -> float:
    return friccion_rt_ticks(instrumento, escenario, incluye_spread, criterio) * tick_size(instrumento)


def friccion_rt_usd(instrumento: str, escenario: str = "base", incluye_spread: bool = True, criterio: str = "max") -> float:
    return friccion_rt_ticks(instrumento, escenario, incluye_spread, criterio) * tick_value_usd(instrumento)


def desglose(instrumento: str) -> dict:
    """Todo lo que hace falta para citar el costo en un manifiesto."""
    d = dict(instrumento=str(instrumento).upper(), tick_size=tick_size(instrumento), tick_value_usd=tick_value_usd(instrumento),
             comision_rt_ticks=dict(min=comision_rt_usd(instrumento, "min") / tick_value_usd(instrumento),
                                    max=comision_rt_usd(instrumento, "max") / tick_value_usd(instrumento)),
             fuentes=tabla()["fuentes"], schema=tabla()["schema"])
    try:
        d["spread_ticks"] = spread_ticks(instrumento)
        d["friccion_rt_ticks"] = {e: friccion_rt_ticks(instrumento, e) for e in ESCENARIOS}
        d["friccion_rt_ticks_min_comision"] = friccion_rt_ticks(instrumento, "base", criterio="min")
    except CostoNoMedido as e:
        d["spread_ticks"] = None; d["friccion_rt_ticks"] = None; d["falta"] = str(e)
    return d
