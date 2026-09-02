"""Kernels Python espejo de los indicadores «paridad primero».

Espejan bit a bit la lógica de `nt8/AVolZonePOI_P.cs` y `nt8/HFTImpulseZones_P.cs`.
Toda decisión usa aritmética entera: ningún float participa de una comparación
que decida. Ver `docs/research/PARITY_FIRST_INDICATOR_CONTRACT_2026-09-02.md`.

La paridad se valida cruzando el CSV que emite cada `.cs` contra la salida de
estas funciones, campo por campo. Como no hay estadísticos continuos ni reloj de
ticks en el medio, la única fuente posible de divergencia es el footprint —y para
`HFTImpulseZones_P` ni siquiera eso, porque sólo usa OHLC de la serie primaria.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

AVOL_DEFAULTS: dict[str, int] = {
    "bars_per_block": 10,
    "top_k_cells": 8,
    "max_gap_ticks": 1,
    "min_cluster_cells": 2,
    "min_share_bps": 1200,
    "min_block_cells": 3,
}

IMPULSE_DEFAULTS: dict[str, int] = {
    "window_bars": 12,
    "min_displacement_ticks": 16,
    "min_efficiency_bps": 6000,
    "min_window_volume": 0,
    "zone_height_ticks": 8,
}


def evaluate_avol_block(cells: Mapping[int, int], close_tick: int,
                        params: Mapping[str, int] | None = None) -> dict[str, Any]:
    """Espejo exacto de `AVolZonePOI_P.EvaluateBlock`.

    `cells` es {tick_de_precio: volumen_entero} del bloque completo.
    Devuelve la misma decisión y geometría que emite el `.cs`.
    """
    p = {**AVOL_DEFAULTS, **(params or {})}
    cells = {int(k): int(v) for k, v in cells.items()}
    block_volume = sum(cells.values())
    out: dict[str, Any] = {
        "decision": "CREATE", "n_cells": len(cells), "block_volume": block_volume,
        "sel_lower_tick": None, "sel_upper_tick": None, "sel_volume": None,
        "sel_cells": None, "share_bps": 0, "close_tick": int(close_tick),
    }

    if len(cells) < p["min_block_cells"]:
        out["decision"] = "ABSTAIN_FEW_CELLS"
        return out

    # ranking top-K: volumen DESC, empate por precio ASC (regla 3 y 4)
    ranked = sorted(cells.keys(), key=lambda t: (-cells[t], t))
    hot = sorted(ranked[: min(p["top_k_cells"], len(ranked))])

    best_lo = best_up = 0
    best_vol = -1
    best_cells = 0
    i = 0
    while i < len(hot):
        j = i
        while j + 1 < len(hot) and hot[j + 1] - hot[j] <= p["max_gap_ticks"] + 1:
            j += 1
        n_cells = j - i + 1
        if n_cells >= p["min_cluster_cells"]:
            total = sum(cells[t] for t in hot[i:j + 1])
            # mejor cluster: mayor volumen; empate -> borde inferior más bajo
            if total > best_vol or (total == best_vol and hot[i] < best_lo):
                best_vol, best_lo, best_up, best_cells = total, hot[i], hot[j], n_cells
        i = j + 1

    if best_vol < 0:
        out["decision"] = "ABSTAIN_NO_CLUSTER"
        return out

    # proporción en basis points ENTEROS: división entera, igual que el .cs (regla 1)
    share_bps = (best_vol * 10000) // block_volume if block_volume > 0 else 0
    out["share_bps"] = share_bps
    if share_bps < p["min_share_bps"]:
        out["decision"] = "ABSTAIN_BELOW_SHARE"
        return out

    out.update(sel_lower_tick=best_lo, sel_upper_tick=best_up,
               sel_volume=best_vol, sel_cells=best_cells)
    return out


def evaluate_impulse_window(close_ticks: Sequence[int], high_ticks: Sequence[int],
                            low_ticks: Sequence[int], volumes: Sequence[int],
                            params: Mapping[str, int] | None = None) -> dict[str, Any]:
    """Espejo exacto de la evaluación de ventana de `HFTImpulseZones_P`.

    Las cuatro secuencias son la ventana completa (largo == window_bars), en
    ticks enteros. No se usa ningún timestamp: el reloj entre ticks está
    prohibido por contrato (regla 2).
    """
    p = {**IMPULSE_DEFAULTS, **(params or {})}
    c = [int(x) for x in close_ticks]
    if len(c) != p["window_bars"]:
        raise ValueError(f"la ventana debe tener {p['window_bars']} barras, tiene {len(c)}")

    start_tick, end_tick = c[0], c[-1]
    displacement = abs(end_tick - start_tick)
    path = sum(abs(c[i] - c[i - 1]) for i in range(1, len(c)))
    window_volume = sum(int(v) for v in volumes)
    eff_bps = (displacement * 10000) // path if path > 0 else 0

    out: dict[str, Any] = {
        "start_close_tick": start_tick, "end_close_tick": end_tick,
        "displacement_ticks": displacement, "path_ticks": path,
        "efficiency_bps": eff_bps, "window_volume": window_volume,
        "decision": "CREATE", "direction": 0,
        "zone_lower_tick": None, "zone_upper_tick": None,
    }

    if window_volume < p["min_window_volume"]:
        out["decision"] = "ABSTAIN_LOW_VOLUME"
        return out
    if displacement < p["min_displacement_ticks"]:
        out["decision"] = "ABSTAIN_SHORT_DISPLACEMENT"
        return out
    if eff_bps < p["min_efficiency_bps"]:
        out["decision"] = "ABSTAIN_LOW_EFFICIENCY"
        return out

    direction = 1 if end_tick > start_tick else -1
    if direction == 1:
        base = min(int(x) for x in low_ticks)
        lower, upper = base, base + p["zone_height_ticks"]
    else:
        base = max(int(x) for x in high_ticks)
        lower, upper = base - p["zone_height_ticks"], base
    out.update(direction=direction, zone_lower_tick=lower, zone_upper_tick=upper)
    return out
