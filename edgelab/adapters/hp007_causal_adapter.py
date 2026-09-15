# -*- coding: utf-8 -*-
"""
edgelab/adapters/hp007_causal_adapter.py
=========================================
Adapter causal point-in-time para la campaña formal de HP-007 (Corredores de Vacío).

Convierte ticks y zonas de absorción as-of al esquema JSONL consumible por:
tools/measure_liquidity_corridors.py

Requisitos estrictos de integridad:
1. Trabaja internamente en ticks enteros (price_tick: int), no floats.
2. Garantiza created_ns <= available_ns <= decision_ns.
3. Memoria as-of: toques, invalidaciones y desgaste calculados estrictamente con
   eventos ocurridos hasta t (cero look-ahead futuro).
4. Entrada en el primer tick ejecutable estrictamente posterior a decision_ns.
5. Trayectorias acotadas a la misma sesión, contrato y régimen (cero cruces).
6. Firewalls de holdout activos: rechaza fechas >= 2026-07-01.
"""
from __future__ import annotations

import math
import hashlib
import json
import datetime
from dataclasses import dataclass, asdict
from typing import Sequence, Iterable, Mapping, Any
import numpy as np

from edgelab.research.liquidity_corridors import (
    CorridorSignal, TradeTick, CorridorContractError
)
from edgelab.research.holdout_guard import HOLDOUT_START_ISO

HOLDOUT_CUTOFF_DATE = datetime.date.fromisoformat(HOLDOUT_START_ISO[:10])


def get_cme_trade_date(dt_utc: datetime.datetime) -> str:
    """Calcula el CME trade date causal.
    Sesión regular CME Globex inicia 17:00 CT (22:00/23:00 UTC) del día anterior.
    """
    # Si la hora UTC es >= 22:00, pertenece a la sesión del día siguiente
    if dt_utc.hour >= 22:
        td = dt_utc.date() + datetime.timedelta(days=1)
    else:
        td = dt_utc.date()
    # Si cae en sábado, pertenece al lunes
    if td.weekday() == 5:
        td += datetime.timedelta(days=2)
    return td.isoformat()


def get_time_bucket(hour_utc: int) -> str:
    """Clasifica el horario en buckets estándar CME FX (6E)."""
    # RTH Londres/NY: ~07:00 a 16:00 CT -> 12:00 a 21:00 UTC
    if 12 <= hour_utc < 15:
        return "RTH_OPEN"
    elif 15 <= hour_utc < 19:
        return "RTH_MID"
    elif 19 <= hour_utc < 21:
        return "RTH_CLOSE"
    else:
        return "ETH_OVERNIGHT"


@dataclass(frozen=True)
class CausalZoneSnapshot:
    """Zona de absorción con historia causal congelada hasta t."""
    zone_id: str
    top_tick: int
    bottom_tick: int
    created_ns: int
    kind: str  # "ABSORB_BULL" o "ABSORB_BEAR"
    vol: float
    touches_as_of: int
    is_invalidated_as_of: bool


def compute_as_of_zone_weight(
    z: CausalZoneSnapshot,
    t_ref_ns: int,
    half_life_hours: float = 12.0,
    maturation_hours: float = 1.0,
    wear_coeff: float = 0.50
) -> float:
    """Calcula el peso microestructural de una zona estrictamente as-of t_ref_ns."""
    dt_sec = max(0, (t_ref_ns - z.created_ns) / 1e9)
    dt_hours = dt_sec / 3600.0

    # 1. Función de maduración bimodal
    if dt_hours < maturation_hours:
        f_mat = 0.35 + 0.65 * (dt_hours / max(0.001, maturation_hours))
    else:
        f_mat = 1.0

    # 2. Decaimiento lento post-maduración (a partir de 4 horas)
    if dt_hours <= 4.0:
        f_decay = 1.0
    else:
        f_decay = math.exp(-0.69314718 * (dt_hours - 4.0) / half_life_hours)

    # 3. Desgaste por toques acaecidos hasta t
    f_wear = (1.0 / (1.0 + wear_coeff * z.touches_as_of)) ** 0.60

    # 4. Ponderación por volumen
    s0 = min(3.0, max(0.3, z.vol / 20.0))
    f_vol = s0 ** 0.25

    # 5. Penalización por invalidación histórica
    penalty = 0.35 if z.is_invalidated_as_of else 1.0

    return f_vol * f_mat * f_decay * f_wear * penalty


def compute_as_of_directional_density(
    price_tick: int,
    t_ref_ns: int,
    zones: Sequence[CausalZoneSnapshot],
    direction: int,
    n_ticks_span: int = 10,
    sigma_ticks: float = 1.2
) -> tuple[float, float, int]:
    """Calcula densidad hacia adelante (forward) y hacia atrás (backstop) en ticks enteros.
    
    Retorna:
        (forward_density, backstop_density, width_to_wall_ticks)
    """
    two_sig_sq = 2.0 * sigma_ticks * sigma_ticks

    # Precios evaluados hacia adelante y hacia atrás en ticks enteros
    fwd_ticks = [price_tick + direction * k for k in range(1, n_ticks_span + 1)]
    bsp_ticks = [price_tick - direction * k for k in range(0, 4)]

    d_fwd = np.zeros(len(fwd_ticks), dtype=float)
    d_bsp = np.zeros(len(bsp_ticks), dtype=float)

    wall_width = n_ticks_span  # default si no hay pared dentro del span

    for z in zones:
        if z.created_ns > t_ref_ns:
            continue  # zona futura no existe todavía

        w = compute_as_of_zone_weight(z, t_ref_ns)
        if w < 0.005:
            continue

        z_mid = 0.5 * (z.top_tick + z.bottom_tick)
        is_bear = ("BEAR" in z.kind)
        is_bull = ("BULL" in z.kind)

        # Hacia adelante:
        # En compras (dir=1), la resistencia adelante son techos BEAR
        # En ventas (dir=-1), la resistencia adelante son suelos BULL
        applies_fwd = (direction == 1 and is_bear) or (direction == -1 and is_bull)
        # Hacia atrás (backstop):
        # En compras, el suelo protector a la espalda son suelos BULL
        # En ventas, el techo protector a la espalda son techos BEAR
        applies_bsp = (direction == 1 and is_bull) or (direction == -1 and is_bear)

        if applies_fwd:
            for idx, pt in enumerate(fwd_ticks):
                dist = abs(pt - z_mid)
                d_fwd[idx] += w * math.exp(-(dist ** 2) / two_sig_sq)

        if applies_bsp:
            for idx, pt in enumerate(bsp_ticks):
                dist = abs(pt - z_mid)
                d_bsp[idx] += w * math.exp(-(dist ** 2) / two_sig_sq)

    # Normalización sigmoidal [0, 1]
    norm_fwd = 1.0 - np.exp(-d_fwd)
    norm_bsp = 1.0 - np.exp(-d_bsp)

    forward_mean = float(np.mean(norm_fwd))
    backstop_max = float(np.max(norm_bsp)) if len(norm_bsp) > 0 else 0.0

    # Buscar primera pared D >= 0.70 hacia adelante
    for idx, d_val in enumerate(norm_fwd):
        if d_val >= 0.70:
            wall_width = idx + 1
            break

    return forward_mean, backstop_max, wall_width


def build_causal_signals_and_trajectories(
    tick_records: Any,
    raw_zones: Sequence[Mapping[str, Any]],
    *,
    contract: str,
    root: str = "6E",
    regime_id: str = "STANDALONE_CONTRACT_IS",
    tick_size: float = 0.00005,
    bar_size_ticks: int = 25,
    horizon_ns: int = 3600_000_000_000,  # 1 hora
    cooldown_ns: int = 60_000_000_000,   # 1 minuto
    min_bar_history: int = 20,
    stride_bars: int = 4,
    include_ticks: bool = True
) -> list[dict[str, Any]]:
    """Construye señales causales point-in-time y asocia sus trayectorias futuras de ticks.

    Retorna una lista de diccionarios, cada uno con:
    {"signal": CorridorSignal, "ticks": [TradeTick, ...]}
    """
    if tick_records is None:
        return []

    # Extraer arrays numpy según el tipo de entrada
    if hasattr(tick_records, "ts_ns") and hasattr(tick_records, "price_ticks"):
        all_ts_ns = np.asarray(tick_records.ts_ns, dtype=np.int64)
        all_price_ticks = np.asarray(tick_records.price_ticks, dtype=np.int64)
        n_total = len(all_ts_ns)
        if hasattr(tick_records, "sequence") and tick_records.sequence is not None:
            all_seq = np.asarray(tick_records.sequence, dtype=np.int64)
        else:
            all_seq = np.arange(n_total, dtype=np.int64)
        if hasattr(tick_records, "volume") and tick_records.volume is not None:
            all_vol = np.asarray(tick_records.volume, dtype=np.int32)
        else:
            all_vol = np.ones(n_total, dtype=np.int32)
    elif isinstance(tick_records, (list, tuple)):
        if len(tick_records) == 0:
            return []
        n_total = len(tick_records)
        first = tick_records[0]
        if isinstance(first, dict):
            all_ts_ns = np.array([int(t["ts_ns"]) for t in tick_records], dtype=np.int64)
            all_price_ticks = np.array([int(round(t["price_tick"])) for t in tick_records], dtype=np.int64)
            all_seq = np.array([int(t.get("sequence", i)) for i, t in enumerate(tick_records)], dtype=np.int64)
            all_vol = np.array([int(t.get("volume", 1)) for t in tick_records], dtype=np.int32)
        else:
            all_ts_ns = np.array([int(getattr(t, "ts_ns")) for t in tick_records], dtype=np.int64)
            all_price_ticks = np.array([int(round(getattr(t, "price_tick"))) for t in tick_records], dtype=np.int64)
            all_seq = np.array([int(getattr(t, "sequence", i)) for i, t in enumerate(tick_records)], dtype=np.int64)
            all_vol = np.array([int(getattr(t, "volume", 1)) for t in tick_records], dtype=np.int32)
    else:
        return []

    if n_total == 0:
        return []

    # Validar orden estricto de ticks
    check_len = min(1000, n_total)
    diffs = np.diff(all_ts_ns[:check_len])
    if np.any(diffs < 0):
        idx_err = int(np.where(diffs < 0)[0][0])
        raise CorridorContractError(f"Ticks are not monotonically sorted: {all_ts_ns[idx_err+1]} < {all_ts_ns[idx_err]}")
    tied_idxs = np.where(diffs == 0)[0]
    for idx in tied_idxs:
        if all_seq[idx + 1] <= all_seq[idx]:
            raise CorridorContractError(f"Tied timestamps without strictly increasing sequence: {all_ts_ns[idx]}")

    # Agrupar ticks en barras sintéticas de actividad de forma vectorizada
    n_bars = n_total // bar_size_ticks
    if n_bars < min_bar_history + 5:
        return []

    bars = []
    for b_idx in range(n_bars):
        start_idx = b_idx * bar_size_ticks
        end_idx = (b_idx + 1) * bar_size_ticks - 1
        p_slice = all_price_ticks[start_idx:end_idx + 1]
        bars.append({
            "bar_index": b_idx,
            "open_tick": int(p_slice[0]),
            "high_tick": int(np.max(p_slice)),
            "low_tick": int(np.min(p_slice)),
            "close_tick": int(p_slice[-1]),
            "volume": int(np.sum(all_vol[start_idx:end_idx + 1])),
            "close_ts_ns": int(all_ts_ns[end_idx]),
            "first_tick_idx": start_idx,
            "last_tick_idx": end_idx
        })

    # Pre-indexar zonas con su historial de eventos
    parsed_zones = []
    for rz in raw_zones:
        top_val = rz.get("top", rz.get("hi"))
        bot_val = rz.get("bottom", rz.get("lo"))
        z_top = round(top_val / tick_size)
        z_bot = round(bot_val / tick_size)

        if "t0_ns" in rz:
            t0_ns = int(rz["t0_ns"])
        elif "fill_ts" in rz:
            t0_ns = int(rz["fill_ts"])
        elif "sig_ts" in rz:
            t0_ns = int(rz["sig_ts"])
        else:
            t0_val = rz.get("t0", 0)
            t0_ns = int(t0_val * 1e9 if t0_val < 1e11 else t0_val)

        if "t1_ns" in rz:
            t1_ns = int(rz["t1_ns"])
        elif "ended_ms" in rz and rz["ended_ms"]:
            t1_ns = int(rz["ended_ms"] * 1_000_000)
        elif "t1" in rz and rz["t1"] is not None:
            t1_val = rz["t1"]
            t1_ns = int(t1_val * 1e9 if t1_val < 1e11 else t1_val)
        else:
            t1_ns = int(2e18)

        kind_val = rz.get("kind")
        if not kind_val:
            kind_val = "ABSORB_BULL" if rz.get("is_bull", rz.get("dir") == "long") else "ABSORB_BEAR"

        parsed_zones.append({
            "zone_id": str(rz.get("id", f"Z_{t0_ns}")),
            "top_tick": max(z_top, z_bot),
            "bottom_tick": min(z_top, z_bot),
            "created_ns": t0_ns,
            "invalidated_ns": t1_ns,
            "kind": kind_val,
            "vol": float(rz.get("vol", 20.0)),
            "touch_timestamps_ns": rz.get("touch_timestamps_ns", [])
        })

    parsed_zones.sort(key=lambda z: z["created_ns"])
    zone_created_arr = np.array([z["created_ns"] for z in parsed_zones], dtype=np.int64) if parsed_zones else np.array([], dtype=np.int64)

    records_out = []
    last_decision_by_dir: dict[int, int] = {-1: 0, 1: 0}
    max_age_ns = 172800 * 1_000_000_000  # 48 horas

    bar_close_times = np.array([b["close_ts_ns"] for b in bars], dtype=np.int64)
    b_idx = min_bar_history
    max_future_ticks = 1000

    # Recorrer barras desde min_bar_history avanzando eficientemente
    while b_idx < len(bars) - 2:
        bar = bars[b_idx]
        decision_ns = bar["close_ts_ns"]
        available_ns = decision_ns
        created_ns = bar["close_ts_ns"]

        # Filtro temprano de cooldown con salto vectorizado
        if (decision_ns - last_decision_by_dir[1] < cooldown_ns) and (decision_ns - last_decision_by_dir[-1] < cooldown_ns):
            next_eligible = min(last_decision_by_dir[1], last_decision_by_dir[-1]) + cooldown_ns
            next_idx = int(np.searchsorted(bar_close_times, next_eligible, side='left'))
            b_idx = max(next_idx, b_idx + stride_bars)
            continue

        dt_utc = datetime.datetime.fromtimestamp(decision_ns / 1e9, datetime.timezone.utc)
        trade_date = get_cme_trade_date(dt_utc)
        td_obj = datetime.date.fromisoformat(trade_date)

        # FIREWALL CANÓNICO DE HOLDOUT
        if td_obj >= HOLDOUT_CUTOFF_DATE:
            b_idx += stride_bars
            continue

        session_id = f"{contract}_{trade_date}"
        time_bucket = get_time_bucket(dt_utc.hour)

        # Volatilidad en las últimas 15 barras
        ranges = [b["high_tick"] - b["low_tick"] for b in bars[max(0, b_idx - 15):b_idx]]
        avg_range = float(np.mean(ranges)) if ranges else 2.0
        if avg_range <= 3.0:
            volatility_bin = "V1"
        elif avg_range <= 6.0:
            volatility_bin = "V2"
        else:
            volatility_bin = "V3"

        # Impulso de la barra actual
        delta_p = bar["close_tick"] - bar["open_tick"]
        if delta_p > 0:
            impulse_bin = "I_UP"
        elif delta_p < 0:
            impulse_bin = "I_DOWN"
        else:
            impulse_bin = "I_NEUT"

        # Construir snapshots causales de zonas as-of decision_ns
        active_snapshots = []
        if len(zone_created_arr) > 0:
            z_end_idx = int(np.searchsorted(zone_created_arr, decision_ns, side='right'))
            z_start_idx = int(np.searchsorted(zone_created_arr, decision_ns - max_age_ns, side='left'))
            for zi in range(z_start_idx, z_end_idx):
                pz = parsed_zones[zi]
                touches_as_of = sum(1 for ts_touch in pz["touch_timestamps_ns"] if ts_touch <= decision_ns)
                is_inv_as_of = (decision_ns >= pz["invalidated_ns"])
                active_snapshots.append(CausalZoneSnapshot(
                    zone_id=pz["zone_id"],
                    top_tick=pz["top_tick"],
                    bottom_tick=pz["bottom_tick"],
                    created_ns=pz["created_ns"],
                    kind=pz["kind"],
                    vol=pz["vol"],
                    touches_as_of=touches_as_of,
                    is_invalidated_as_of=is_inv_as_of
                ))

        # Slicing rápido de ticks futuros acotados a horizon_ns y fin de sesión
        start_tick_idx = bar["last_tick_idx"] + 1
        max_ts = decision_ns + horizon_ns
        session_end_dt = datetime.datetime(td_obj.year, td_obj.month, td_obj.day, 21, 59, 59, tzinfo=datetime.timezone.utc)
        session_end_ns = int(session_end_dt.timestamp() * 1e9)
        effective_max_ts = min(max_ts, session_end_ns)
        end_tick_idx = int(np.searchsorted(all_ts_ns, effective_max_ts, side='right'))

        fut_ts = all_ts_ns[start_tick_idx:end_tick_idx][:max_future_ticks]
        fut_px = all_price_ticks[start_tick_idx:end_tick_idx][:max_future_ticks]
        fut_sq = all_seq[start_tick_idx:end_tick_idx][:max_future_ticks]

        # Evaluar en ambas direcciones
        for direction in (1, -1):
            if decision_ns - last_decision_by_dir[direction] < cooldown_ns:
                continue

            ref_tick = bar["close_tick"]
            fwd_d, bsp_d, width_t = compute_as_of_directional_density(
                ref_tick, decision_ns, active_snapshots, direction
            )

            event_id = f"HP007_{contract.replace(' ', '_')}_{trade_date}_{direction}_{decision_ns}"

            signal = CorridorSignal(
                event_id=event_id,
                root=root,
                contract=contract,
                trade_date=trade_date,
                regime_id=regime_id,
                session_id=session_id,
                direction=direction,
                created_ns=created_ns,
                available_ns=available_ns,
                decision_ns=decision_ns,
                reference_tick=ref_tick,
                forward_density=round(fwd_d, 4),
                backstop_density=round(bsp_d, 4),
                width_ticks=int(width_t),
                time_bucket=time_bucket,
                volatility_bin=volatility_bin,
                impulse_bin=impulse_bin
            )

            # Construir ticks
            if include_ticks:
                future_ticks = [
                    {
                        "ts_ns": int(fut_ts[tk_i]),
                        "price_tick": int(fut_px[tk_i]),
                        "contract": contract,
                        "trade_date": trade_date,
                        "regime_id": regime_id,
                        "sequence": int(fut_sq[tk_i])
                    }
                    for tk_i in range(len(fut_ts))
                ]
            else:
                future_ticks = []

            records_out.append({
                "signal": asdict(signal),
                "ticks": future_ticks,
                "start_tick_idx": start_tick_idx,
                "end_tick_idx": end_tick_idx
            })

            last_decision_by_dir[direction] = decision_ns

        b_idx += stride_bars

    return records_out
