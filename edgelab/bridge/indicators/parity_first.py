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
    # --- racha de ráfagas: la señal ---
    "min_bursts_for_signal": 3,
    "max_bars_between_bursts": 40,
    "min_burst_displacement_ticks": 48,
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


def detect_burst_signals(bar_closes, bar_highs, bar_lows, bar_volumes,
                         session_ids=None, params=None):
    """Espejo de la lógica de racha de `HFTImpulseZones_P`: ráfagas → señal.

    Una sola ventana con impulso es un evento chico y frecuente. La señal es la
    **acumulación**: varias ráfagas seguidas en la misma dirección.

    ## Las dos decisiones de diseño que hacen que el número signifique algo

    1. **Sólo cuentan ráfagas NO SOLAPADAS.** La ventana es deslizante, así que
       durante un mismo movimiento disparan muchas barras consecutivas. Contarlas
       todas inflaría la racha sin que haya más mercado: una racha de 12 sería
       sólo el mismo impulso visto doce veces. Una ráfaga nueva cuenta sólo si
       empieza después de que terminó la anterior (`>= window_bars`).
    2. **Una señal por racha.** Se emite la primera vez que la racha cruza los dos
       umbrales. Si después sigue creciendo, eso queda registrado pero no genera
       una señal nueva: una racha es un evento, no varios. Sin esto, la población
       quedaría dominada por las rachas largas y cada una contaría muchas veces.

    La racha se corta por cambio de dirección, por exceder
    `max_bars_between_bursts`, o en la frontera de sesión — no cruza sesiones.

    ## Qué devuelve

    Una lista de señales, cada una con la barra donde se emitió, la dirección, el
    conteo de ráfagas, el desplazamiento acumulado y la zona de la ráfaga que la
    disparó. **Es una población de eventos, no una predicción.** Si tiene valor
    económico se mide aparte, con manifiesto y bajo el STOP del proyecto; esta
    función no mira retornos.

    ## Cómo podría refutarse su utilidad

    Si la distribución de señales es indistinguible de la que produce un nulo que
    respeta la misma tasa y el mismo agrupamiento temporal, la racha no aporta
    información sobre el estado del mercado y sólo está contando volatilidad.
    """
    p = {**IMPULSE_DEFAULTS, **(params or {})}
    w = int(p["window_bars"])
    n = len(bar_closes)
    señales = []
    burst_dir = 0
    burst_count = 0
    burst_disp = 0
    burst_first_bar = None
    last_burst_bar = None
    emitida = False
    sesion_prev = None

    for i in range(n):
        ses = None if session_ids is None else session_ids[i]
        if sesion_prev is not None and ses != sesion_prev:
            burst_dir = burst_count = burst_disp = 0
            last_burst_bar = None
            emitida = False
        sesion_prev = ses
        if i + 1 < w:
            continue
        s0 = i - w + 1
        # la ventana no puede cruzar la frontera de sesión
        if session_ids is not None and session_ids[s0] != ses:
            continue
        r = evaluate_impulse_window(bar_closes[s0:i + 1], bar_highs[s0:i + 1],
                                    bar_lows[s0:i + 1], bar_volumes[s0:i + 1], p)
        if r["decision"] != "CREATE":
            continue

        if last_burst_bar is not None and i - last_burst_bar < w:
            continue                      # solapada con la ráfaga ya contada

        sigue = (burst_dir == r["direction"] and last_burst_bar is not None
                 and i - last_burst_bar <= int(p["max_bars_between_bursts"]))
        if sigue:
            burst_count += 1
            burst_disp += r["displacement_ticks"]
        else:
            burst_dir = r["direction"]
            burst_count = 1
            burst_disp = r["displacement_ticks"]
            burst_first_bar = s0
            emitida = False
        last_burst_bar = i

        if (not emitida
                and burst_count >= int(p["min_bursts_for_signal"])
                and burst_disp >= int(p["min_burst_displacement_ticks"])):
            emitida = True
            señales.append(dict(
                bar=i, session=ses, direction=burst_dir,
                burst_count=burst_count, burst_displacement_ticks=burst_disp,
                burst_first_bar=burst_first_bar,
                zone_lower_tick=r["zone_lower_tick"],
                zone_upper_tick=r["zone_upper_tick"],
                efficiency_bps=r["efficiency_bps"],
            ))
    return señales
