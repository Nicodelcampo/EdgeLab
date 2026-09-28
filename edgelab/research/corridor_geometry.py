"""Caracterización de corredores sobre el campo de densidad canónico HP-007.

**Target-free.** Sin retornos, sin P&L, sin entradas ni salidas: solo geometría del campo.

## Por qué existe

`density_field.detect_density_intervals` devuelve dos listas de tramos de precio: los de
densidad baja (**corredores**) y los de densidad alta (**murallas**). Lo que el visor ya
dibujaba antes de unificar —y lo que HP-007 midió como efecto «Backstop»— agrega dos cosas
encima de eso:

1. **Dirección.** Un corredor con una muralla *compradora* debajo (suelo) es alcista con
   respaldo (`BULL`); con una muralla *vendedora* arriba (techo), bajista (`BEAR`); con ambas,
   `DUAL`; sin ninguna, `STRUCTURAL`.
2. **Nacimiento causal.** Un corredor solo existe desde que existen las murallas que lo
   delimitan: `t_birth_ns` = la disponibilidad más tardía entre las zonas de esas murallas.

Antes de esta unificación esa lógica vivía **solo dentro de `index.html`**, calculada con una
definición de muralla propia (agrupar zonas a ≤ 3 ticks). Ahora la muralla es la región de
densidad alta del campo canónico, y esta función es la única implementación; el visor tiene un
puerto en `viewer/nt8_bridge/density_field.js` verificado contra vectores dorados generados
desde acá (`tools/generate_density_field_golden_vectors.py`).

## Lo que NO está certificado

La caracterización direccional es una **capa explícita encima del campo**, no parte de la
definición del campo. Su paridad contra los scripts que produjeron la medición de HP-007
(`tools/test_corredores_vacio.py`) **no está validada**: hoy se declara `CHARACTERIZATION_UNCERTIFIED`.
Es el primer punto a validar en la fase «mejorar la lógica de los corredores».

## Decisiones de diseño (todas heredadas del visor, ahora explícitas)

- `wall_tolerance_ticks = 3`: una zona pertenece a una muralla si la toca con hasta 3 ticks de holgura
  (era `clusterTol = 3 * tick`).
- La **muralla de suelo** es la región alta más cercana por debajo del corredor; la de **techo**, la más
  cercana por encima. Un corredor sin muralla de un lado se marca `bounded_below/above = False` y no
  puede ser `BULL`/`BEAR` por ese lado.
- El lado de una zona sale de `kind` (`BUY`/`BULL` → compra, `SELL`/`BEAR` → venta); si falta, del signo de
  `direction` (bundles certificados). Una zona sin lado no aporta a la dirección pero sí al nacimiento.
"""
from __future__ import annotations

from edgelab.research.density_field import extract_zone_available_ns, price_to_tick

WALL_TOLERANCE_TICKS = 3
CHARACTERIZATION_STATUS = "CHARACTERIZATION_UNCERTIFIED"


def zone_side(z: dict) -> str | None:
    """`BUY`, `SELL` o `None`. `kind` manda; `direction` es el respaldo."""
    kind = str(z.get("kind", "")).upper()
    if "BUY" in kind or "BULL" in kind:
        return "BUY"
    if "SELL" in kind or "BEAR" in kind:
        return "SELL"
    d = z.get("direction")
    if d is not None:
        try:
            d = float(d)
        except (TypeError, ValueError):
            return None
        if d > 0:
            return "BUY"
        if d < 0:
            return "SELL"
    return None


def _zone_ticks(z: dict, tick_size: float) -> tuple[int, int]:
    lo = float(z.get("lo", z.get("bottom", 0.0)))
    hi = float(z.get("hi", z.get("top", 0.0)))
    a, b = price_to_tick(lo, tick_size), price_to_tick(hi, tick_size)
    return (a, b) if a <= b else (b, a)


def _members(wall: dict, zones: list[dict], tol: int) -> list[dict]:
    return [z for z in zones
            if z["hi"] >= wall["tick_start"] - tol and z["lo"] <= wall["tick_end"] + tol]


def characterize_corridors(
    intervals: dict,
    zones: list[dict],
    active_zone_ids: list[str],
    tick_size: float,
    t_ref_ns: int,
    wall_tolerance_ticks: int = WALL_TOLERANCE_TICKS,
) -> list[dict]:
    """Etiqueta cada corredor con su dirección, sus murallas y su nacimiento causal.

    `intervals` es la salida de `detect_density_intervals`; `zones` las zonas de entrada del
    campo y `active_zone_ids` las que `compute_field` declaró activas (solo esas cuentan).
    """
    activos = set(active_zone_ids)
    zs: list[dict] = []
    for z in zones:
        zid = str(z.get("id", z.get("zone_id", "")))
        if zid not in activos:
            continue
        lo, hi = _zone_ticks(z, tick_size)
        avail, _ = extract_zone_available_ns(z)
        zs.append({"id": zid, "lo": lo, "hi": hi, "side": zone_side(z), "avail_ns": avail})

    walls = sorted(intervals["high_density_regions"], key=lambda w: w["tick_start"])
    out: list[dict] = []
    for c in sorted(intervals["low_density_intervals"], key=lambda c: c["tick_start"]):
        floor = None
        for w in walls:
            if w["tick_end"] < c["tick_start"]:
                floor = w
        ceil = None
        for w in walls:
            if w["tick_start"] > c["tick_end"]:
                ceil = w
                break

        m_floor = _members(floor, zs, wall_tolerance_ticks) if floor else []
        m_ceil = _members(ceil, zs, wall_tolerance_ticks) if ceil else []
        has_buy_floor = any(m["side"] == "BUY" for m in m_floor)
        has_sell_ceil = any(m["side"] == "SELL" for m in m_ceil)

        if has_buy_floor and has_sell_ceil:
            direction = "DUAL"
        elif has_buy_floor:
            direction = "BULL"
        elif has_sell_ceil:
            direction = "BEAR"
        else:
            direction = "STRUCTURAL"

        avails = [m["avail_ns"] for m in m_floor + m_ceil]
        out.append({
            "id": f"CORR_{c['tick_start']}_{c['tick_end']}",
            "tick_start": c["tick_start"],
            "tick_end": c["tick_end"],
            "gap_ticks": c["tick_count"],
            "price_min": c["price_min"],
            "price_max": c["price_max"],
            "avg_density": c["avg_density"],
            "direction": direction,
            "bounded_below": floor is not None,
            "bounded_above": ceil is not None,
            "floor_wall": [floor["tick_start"], floor["tick_end"]] if floor else None,
            "ceil_wall": [ceil["tick_start"], ceil["tick_end"]] if ceil else None,
            "t_birth_ns": max(avails) if avails else int(t_ref_ns),
        })
    return out
