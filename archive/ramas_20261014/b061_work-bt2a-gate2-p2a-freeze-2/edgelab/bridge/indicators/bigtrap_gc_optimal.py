"""BigTrapGC Optimal: Indicador de Absorción y Trampas Institucionales para Oro (GC / MGC).

Configuración congelada derivada de microestructura empírica de GC COMEX:
- Resolución nativa recomendada: 25 ticks (tick:25) o 15 ticks (tick:15)
- Agrupación por fila: 1 tick (0.10 pt)
- Volumen mínimo de absorción: 35.0 contratos (calibrado a la profundidad de GC)
- Subasta terminada (Finished Auction): True (tol <= 1.0 contrato)
- Ratio de desbalance diagonal: >= 3.0 (300%)
- Buffer anti-overshoot adverso: 2 ticks (0.20 pt)
- Filtro de mecha: 40% extremo de la barra
- Invalidation mode: CloseThrough
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np

from edgelab.bridge.bars import BarSeries, Footprints, build_tick_bars, build_footprints
from edgelab.bridge.ticks import TickSeries

NAME = "BigTrapGC_Optimal"
VERSION = "1.0.0"


@dataclass(frozen=True)
class BigTrapGCOptimalConfig:
    """Configuración ideal para Oro (GC / MGC)."""
    ticks_per_bar: int = 25
    ticks_per_row: int = 1
    min_trap_volume: float = 35.0
    imbalance_ratio: float = 3.0
    require_finished_auction: bool = True
    finished_auction_tol: float = 1.0
    anti_overshoot_buffer_ticks: int = 2
    use_wick_filter: bool = True
    wick_zone_pct: float = 40.0
    invalidation_mode: str = "CloseThrough"  # "CloseThrough" | "FirstTouch"
    max_age_bars: int = 300


def detect_gc_zones(
    ticks: TickSeries,
    bars: BarSeries,
    footprints: Footprints,
    config: Optional[BigTrapGCOptimalConfig] = None
) -> Dict[str, Any]:
    """Ejecuta la detección de trampas óptimas en Oro (GC)."""
    if config is None:
        config = BigTrapGCOptimalConfig()

    tick_size = float(ticks.tick_size)
    active_zones: List[Dict[str, Any]] = []
    all_zones: List[Dict[str, Any]] = []

    def update_active_zones(b: int, t_ns: int):
        if not active_zones:
            return
        hi = float(bars.high_t[b]) * tick_size
        lo = float(bars.low_t[b]) * tick_size
        close = float(bars.close_t[b]) * tick_size

        for z in list(active_zones):
            # Expiración por edad
            if config.max_age_bars > 0 and (b - z["created_bar"]) > config.max_age_bars:
                z.update(state="EXPIRED", ended_bar=b, ended_ms=int(t_ns // 1e6), end_reason="max_age")
                active_zones.remove(z)
                continue

            touched = (hi >= z["bottom"]) and (lo <= z["top"])
            if touched:
                z["touches"] += 1

            adverse_close = (close > z["top"]) if z["is_bull"] else (close < z["bottom"])
            reason = None
            if config.invalidation_mode == "FirstTouch" and touched:
                reason = "first_touch"
            elif config.invalidation_mode == "CloseThrough" and adverse_close:
                reason = "close_through" if touched else "close_through_gap"

            if reason is not None:
                z.update(state="INVALIDATED", ended_bar=b, ended_ms=int(t_ns // 1e6), end_reason=reason)
                active_zones.remove(z)

    # Procesar barra por barra
    for b in range(1, len(bars)):
        t_ns = int(bars.end_ns[b])
        update_active_zones(b, t_ns)

        ask_map = footprints.ask[b]
        bid_map = footprints.bid[b]
        if not ask_map and not bid_map:
            continue

        close = float(bars.close_t[b]) * tick_size
        lo = float(bars.low_t[b]) * tick_size
        hi = float(bars.high_t[b]) * tick_size
        rng = hi - lo
        wick_hi_floor = hi - rng * (config.wick_zone_pct / 100.0)
        wick_lo_ceil = lo + rng * (config.wick_zone_pct / 100.0)

        hi_bar_tk = int(bars.high_t[b])
        lo_bar_tk = int(bars.low_t[b])

        # Finished Auction check
        is_finished_hi = (bid_map.get(hi_bar_tk, 0.0) <= config.finished_auction_tol)
        is_finished_lo = (ask_map.get(lo_bar_tk, 0.0) <= config.finished_auction_tol)

        # 1. Trapped Buyers en el techo (Resistencia -> SHORT)
        buy_imbalances = []
        for tk, a in ask_map.items():
            bv = bid_map.get(tk - 1, 0.0)
            ratio = a / max(bv, 1.0)
            px = tk * tick_size
            if a >= 1.0 and ratio >= config.imbalance_ratio and px > close:
                if not config.use_wick_filter or (rng > 0 and px >= wick_hi_floor):
                    buy_imbalances.append((tk, a, bv, ratio, px))

        if buy_imbalances and (not config.require_finished_auction or is_finished_hi):
            pool_vol = sum(x[1] for x in buy_imbalances)
            if pool_vol >= config.min_trap_volume:
                min_tk = min(x[0] for x in buy_imbalances)
                max_tk = max(x[0] for x in buy_imbalances)
                buffer_pts = config.anti_overshoot_buffer_ticks * tick_size
                z_bottom = min_tk * tick_size - tick_size / 2.0
                z_top = max_tk * tick_size + tick_size / 2.0 + buffer_pts

                z = dict(
                    id=f"{b}_TB",
                    indicator=NAME,
                    kind="trapped_buyers",
                    side="SHORT",
                    is_bull=True,
                    top=round(z_top, 2),
                    bottom=round(z_bottom, 2),
                    vol=round(pool_vol, 1),
                    created_bar=b,
                    created_ms=int(t_ns // 1e6),
                    state="ACTIVE",
                    touches=0,
                    ended_bar=None,
                    ended_ms=None,
                    end_reason=None
                )
                active_zones.append(z)
                all_zones.append(z)

        # 2. Trapped Sellers en el suelo (Soporte -> LONG)
        sell_imbalances = []
        for tk, bv in bid_map.items():
            a = ask_map.get(tk + 1, 0.0)
            ratio = bv / max(a, 1.0)
            px = tk * tick_size
            if bv >= 1.0 and ratio >= config.imbalance_ratio and px < close:
                if not config.use_wick_filter or (rng > 0 and px <= wick_lo_ceil):
                    sell_imbalances.append((tk, bv, a, ratio, px))

        if sell_imbalances and (not config.require_finished_auction or is_finished_lo):
            pool_vol = sum(x[1] for x in sell_imbalances)
            if pool_vol >= config.min_trap_volume:
                min_tk = min(x[0] for x in sell_imbalances)
                max_tk = max(x[0] for x in sell_imbalances)
                buffer_pts = config.anti_overshoot_buffer_ticks * tick_size
                z_top = max_tk * tick_size + tick_size / 2.0
                z_bottom = min_tk * tick_size - tick_size / 2.0 - buffer_pts

                z = dict(
                    id=f"{b}_TS",
                    indicator=NAME,
                    kind="trapped_sellers",
                    side="LONG",
                    is_bull=False,
                    top=round(z_top, 2),
                    bottom=round(z_bottom, 2),
                    vol=round(pool_vol, 1),
                    created_bar=b,
                    created_ms=int(t_ns // 1e6),
                    state="ACTIVE",
                    touches=0,
                    ended_bar=None,
                    ended_ms=None,
                    end_reason=None
                )
                active_zones.append(z)
                all_zones.append(z)

    return {
        "indicator": NAME,
        "version": VERSION,
        "config": config.__dict__,
        "total_zones": len(all_zones),
        "zones": all_zones
    }
