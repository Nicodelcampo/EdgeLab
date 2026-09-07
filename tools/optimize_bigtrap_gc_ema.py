#!/usr/bin/env python3
"""Optimizador Causal de Filtro EMA para BigTrapGC (Oro COMEX).

Evalúa el impacto de filtrar entradas de BigTrap2 con medias móviles exponenciales (EMA):
- Hipótesis Tendencial (Usuario):
  * COMPRA (Trapped Sellers) solo si Close >= EMA
  * VENTA (Trapped Buyers) solo si Close <= EMA
- Hipótesis Reversión a la Media:
  * COMPRA solo si Close < EMA
  * VENTA solo si Close > EMA
- Períodos Evaluados: EMA 20, EMA 50, EMA 100, EMA 200, EMA 500 vs Control (Sin Filtro).
- Metodología Científica: In-Sample (12-25 + 02-26) vs Out-of-Sample (04-26 + 06-26).
- Fricciones Reales CME: $4.50 USD comision RT + 1 tick slippage adverso en paradas ($10 USD).
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import psutil
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import TickSeries
from edgelab.bridge.bars import build_tick_bars, build_footprints
from edgelab.bridge.indicators.bigtrap_gc_optimal import (
    BigTrapGCOptimalConfig, detect_gc_zones
)

COMMISSION_PTS = 0.045  # $4.50 USD / $100 por pt en GC
SLIPPAGE_TICKS = 1      # 1 tick adverso en SL (0.10 pt = $10 USD)
EMA_PERIODS = [20, 50, 100, 200, 500]


def get_process_ram_mb() -> float:
    return psutil.Process().memory_info().rss / (1024.0 * 1024.0)


def calc_ema_series(closes: np.ndarray, period: int) -> np.ndarray:
    """Calcula la EMA idéntica a NinjaTrader 8: EMA[0] = (Input[0]*k) + (EMA[1]*(1-k))."""
    n = len(closes)
    ema = np.empty(n, dtype=np.float64)
    if n == 0:
        return ema
    k = 2.0 / (period + 1.0)
    current = float(closes[0])
    for i in range(n):
        current = (float(closes[i]) * k) + (current * (1.0 - k))
        ema[i] = current
    return ema


def find_session_boundaries_streaming(parquet_path: Path) -> List[Tuple[int, int]]:
    pf = pq.ParquetFile(parquet_path)
    session_ranges: List[Tuple[int, int]] = []
    current_start: Optional[int] = None
    prev_ts: Optional[int] = None
    prev_ses = None

    for batch in pf.iter_batches(batch_size=2_000_000, columns=["ts_utc_ns"]):
        ts = batch.column("ts_utc_ns").to_numpy(zero_copy_only=False)
        idx = pd.to_datetime(ts, unit="ns", utc=True).tz_convert("America/Chicago")
        dias = np.asarray(idx.normalize().view("int64")) // 86_400_000_000_000
        ses = dias + (np.asarray(idx.hour) >= 17).astype(np.int64)

        if prev_ses is not None and ses[0] != prev_ses:
            session_ranges.append((current_start, prev_ts))
            current_start = int(ts[0])

        change = np.flatnonzero(np.diff(ses)) + 1
        if len(change) == 0:
            if current_start is None:
                current_start = int(ts[0])
            prev_ts = int(ts[-1])
            prev_ses = ses[-1]
            continue

        first_ch = change[0]
        if current_start is None:
            current_start = int(ts[0])
        session_ranges.append((current_start, int(ts[first_ch - 1])))

        for i in range(len(change) - 1):
            session_ranges.append((int(ts[change[i]]), int(ts[change[i + 1] - 1])))

        current_start = int(ts[change[-1]])
        prev_ts = int(ts[-1])
        prev_ses = ses[-1]

    if current_start is not None and prev_ts is not None:
        session_ranges.append((current_start, prev_ts))

    return session_ranges


def extract_session_trade_trajectories(
    ticks: TickSeries,
    bars: Any,
    fps: Any,
    config: BigTrapGCOptimalConfig,
    contract_name: str,
    max_ticks_forward: int = 5000
) -> List[Dict[str, Any]]:
    tick_size = float(ticks.tick_size)
    bar_starts = np.zeros(len(bars), dtype=np.int64)
    bar_ends = np.zeros(len(bars), dtype=np.int64)
    if len(ticks) > 0 and len(bars) > 0:
        bar_changes = np.flatnonzero(np.diff(bars.tick_bar_idx)) + 1
        bar_starts = np.concatenate(([0], bar_changes))
        bar_ends = np.concatenate((bar_changes, [len(ticks)]))

    # Calcular EMAs sobre los cierres de las barras primarias
    closes_t = bars.close_t
    ema_dict = {p: calc_ema_series(closes_t, p) for p in EMA_PERIODS}

    res = detect_gc_zones(ticks, bars, fps, config=config)
    zones = res["zones"]

    trajectories = []
    n_bars = len(bars)

    for z in zones:
        b_created = z["created_bar"]
        is_bull = (z["kind"] == "trapped_buyers")  # True = SHORT, False = LONG
        z_top_tk = int(round(z["top"] / tick_size))
        z_bot_tk = int(round(z["bottom"] / tick_size))
        zone_height_ticks = max(1, z_top_tk - z_bot_tk)

        entry_bar = b_created
        entry_tick = int(bars.close_t[b_created])
        entry_tick_idx = int(bar_ends[b_created]) - 1
        if entry_tick_idx < 0:
            entry_tick_idx = 0

        if not is_bull:  # LONG
            risk_base_tk = max(1, entry_tick - (z_bot_tk - 1))
        else:  # SHORT
            risk_base_tk = max(1, (z_top_tk + 1) - entry_tick)

        end_tick_idx = min(len(ticks), entry_tick_idx + 1 + max_ticks_forward)
        future_px_slice = ticks.price_ticks[entry_tick_idx + 1 : end_tick_idx]

        if len(future_px_slice) < 5:
            continue

        future_px = np.ascontiguousarray(future_px_slice, dtype=np.int32)

        # Evaluaciones de filtro EMA en la barra de entrada
        c_val = float(closes_t[b_created])
        trend_pass = {}
        revert_pass = {}
        ema_dist = {}

        for p in EMA_PERIODS:
            ema_val = ema_dict[p][b_created]
            # Hipótesis tendencial (Usuario): Long arriba de EMA, Short abajo de EMA
            if not is_bull:  # LONG
                trend_pass[p] = bool(c_val >= ema_val)
                revert_pass[p] = bool(c_val < ema_val)
                ema_dist[p] = (c_val - ema_val) * tick_size
            else:  # SHORT
                trend_pass[p] = bool(c_val <= ema_val)
                revert_pass[p] = bool(c_val > ema_val)
                ema_dist[p] = (ema_val - c_val) * tick_size

        trajectories.append({
            "contract": contract_name,
            "zone_id": z["id"],
            "side": "SHORT" if is_bull else "LONG",
            "is_bull": is_bull,
            "created_bar": b_created,
            "entry_bar": entry_bar,
            "entry_tick_idx": entry_tick_idx,
            "entry_tick": entry_tick,
            "entry_px": entry_tick * tick_size,
            "zone_top_tk": z_top_tk,
            "zone_bot_tk": z_bot_tk,
            "zone_height_ticks": zone_height_ticks,
            "risk_base_tk": risk_base_tk,
            "future_ticks": future_px,
            "trend_pass": trend_pass,
            "revert_pass": revert_pass,
            "ema_dist": ema_dist
        })

    return trajectories


def load_contract_trajectories(
    parquet_path: Path,
    contract_name: str,
    config: BigTrapGCOptimalConfig
) -> List[Dict[str, Any]]:
    session_ranges = find_session_boundaries_streaming(parquet_path)
    n_sessions = len(session_ranges)
    cols = ["ts_utc_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "sequence"]
    contract_trajectories: List[Dict[str, Any]] = []

    for s_idx, (t_start, t_end) in enumerate(session_ranges, 1):
        tbl = pq.read_table(
            parquet_path,
            filters=[("ts_utc_ns", ">=", t_start), ("ts_utc_ns", "<=", t_end)],
            columns=cols
        )
        if tbl.num_rows < 50:
            del tbl
            continue

        ticks = TickSeries(
            ts_ns=tbl.column("ts_utc_ns").to_numpy(zero_copy_only=False).astype(np.int64),
            price_ticks=tbl.column("price_ticks").to_numpy(zero_copy_only=False).astype(np.int64),
            volume=tbl.column("volume").to_numpy(zero_copy_only=False).astype(np.float64),
            bid_ticks=tbl.column("bid_ticks").to_numpy(zero_copy_only=False).astype(np.int64),
            ask_ticks=tbl.column("ask_ticks").to_numpy(zero_copy_only=False).astype(np.int64),
            sequence=tbl.column("sequence").to_numpy(zero_copy_only=False).astype(np.int64),
            tick_size=0.10,
            instrument="GC",
            contract=contract_name
        )
        del tbl

        bars = build_tick_bars(ticks, ticks_per_bar=config.ticks_per_bar, reiniciar_por_sesion=True)
        fps = build_footprints(ticks, bars)

        s_trajs = extract_session_trade_trajectories(ticks, bars, fps, config, contract_name)
        contract_trajectories.extend(s_trajs)

        del ticks, bars, fps, s_trajs

    return contract_trajectories


def evaluate_single_trade(
    traj: Dict[str, Any],
    sl_mult: float,
    tp_pts: float,
    be_trigger_pts: Optional[float],
    be_offset_ticks: int = 1,
    tick_size: float = 0.10
) -> Tuple[float, str, int]:
    entry_tk = traj["entry_tick"]
    side = traj["side"]
    future = traj["future_ticks"]
    risk_base_tk = traj["risk_base_tk"]

    sl_dist_tk = max(1, int(round(risk_base_tk * sl_mult)))
    tp_dist_tk = max(2, int(round(tp_pts / tick_size)))
    be_trig_dist_tk = int(round(be_trigger_pts / tick_size)) if be_trigger_pts is not None else None

    if side == "LONG":
        initial_sl_tk = entry_tk - sl_dist_tk
        current_sl_tk = initial_sl_tk
        tp_target_tk = entry_tk + tp_dist_tk
        be_trig_tk = entry_tk + be_trig_dist_tk if be_trig_dist_tk is not None else 999999999
        be_lock_tk = entry_tk + be_offset_ticks

        for i, p in enumerate(future):
            if be_trigger_pts is not None and p >= be_trig_tk:
                current_sl_tk = max(current_sl_tk, be_lock_tk)

            if p <= current_sl_tk:
                loss_tk = entry_tk - current_sl_tk
                loss_pts = loss_tk * tick_size + (SLIPPAGE_TICKS * tick_size) + COMMISSION_PTS
                return -loss_pts, "SL", i + 1

            if p >= tp_target_tk:
                pnl_pts = tp_pts - COMMISSION_PTS
                return pnl_pts, "TP", i + 1

        exit_p = future[-1]
        pnl_pts = (exit_p - entry_tk) * tick_size - COMMISSION_PTS
        return pnl_pts, "CLOSE", len(future)

    else:  # SHORT
        initial_sl_tk = entry_tk + sl_dist_tk
        current_sl_tk = initial_sl_tk
        tp_target_tk = entry_tk - tp_dist_tk
        be_trig_tk = entry_tk - be_trig_dist_tk if be_trig_dist_tk is not None else -999999999
        be_lock_tk = entry_tk - be_offset_ticks

        for i, p in enumerate(future):
            if be_trigger_pts is not None and p <= be_trig_tk:
                current_sl_tk = min(current_sl_tk, be_lock_tk)

            if p >= current_sl_tk:
                loss_tk = current_sl_tk - entry_tk
                loss_pts = loss_tk * tick_size + (SLIPPAGE_TICKS * tick_size) + COMMISSION_PTS
                return -loss_pts, "SL", i + 1

            if p <= tp_target_tk:
                pnl_pts = tp_pts - COMMISSION_PTS
                return pnl_pts, "TP", i + 1

        exit_p = future[-1]
        pnl_pts = (entry_tk - exit_p) * tick_size - COMMISSION_PTS
        return pnl_pts, "CLOSE", len(future)


def evaluate_trajectories_set(
    trajectories: List[Dict[str, Any]],
    sl_mult: float,
    tp_pts: float,
    be_trigger_pts: Optional[float]
) -> Dict[str, Any]:
    n_trades = len(trajectories)
    if n_trades == 0:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
            "total_net_pts": 0.0, "total_usd": 0.0, "profit_factor": 0.0, "sharpe": 0.0
        }

    pnls = []
    wins = 0
    losses = 0
    for tr in trajectories:
        pnl, _, _ = evaluate_single_trade(tr, sl_mult, tp_pts, be_trigger_pts)
        pnls.append(pnl)
        if pnl > 0:
            wins += 1
        else:
            losses += 1

    pnl_arr = np.array(pnls, dtype=np.float64)
    tot_pnl = float(pnl_arr.sum())
    win_pnl = float(pnl_arr[pnl_arr > 0].sum())
    loss_pnl = float(abs(pnl_arr[pnl_arr <= 0].sum()))
    pf = (win_pnl / max(loss_pnl, 1e-4))
    wr = (wins / max(n_trades, 1)) * 100.0
    mean_pnl = float(pnl_arr.mean())
    std_pnl = float(pnl_arr.std())
    sharpe = (mean_pnl / max(std_pnl, 1e-4)) * math.sqrt(252 * 2.0) if std_pnl > 0 else 0.0

    return {
        "total_trades": n_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wr, 1),
        "total_net_pts": round(tot_pnl, 2),
        "total_usd": round(tot_pnl * 100.0, 2),
        "profit_factor": round(pf, 2),
        "sharpe": round(sharpe, 2),
        "mean_pts": round(mean_pnl, 2)
    }


def run_experiment(ticks_per_bar: int = 25):
    print("=" * 90)
    print(f"EdgeLab — Experimento Causal: Filtro EMA sobre BigTrap en Oro (GC COMEX)")
    print(f"Resolución: {ticks_per_bar}-Tick Bars | Períodos: {EMA_PERIODS}")
    print(f"Costos CME: $4.50 RT + 1 tick slippage adverso en paradas ($10 USD)")
    print("=" * 90)

    data_path = Path("E:/EdgeLab/data/nt8/GC_parquet")
    in_sample_contracts = ["GC 12-25", "GC 02-26"]
    out_of_sample_contracts = ["GC 04-26", "GC 06-26"]

    config = BigTrapGCOptimalConfig(ticks_per_bar=ticks_per_bar, min_trap_volume=40.0)

    # 1. Cargar In-Sample
    print("\n[1/4] Extrayendo trades In-Sample (GC 12-25 + GC 02-26)...")
    t0 = time.time()
    is_trajs = []
    for c in in_sample_contracts:
        f = data_path / f"{c.replace(' ', '_')}_ticks.parquet"
        trajs = load_contract_trajectories(f, c, config)
        is_trajs.extend(trajs)
        print(f"  {c}: {len(trajs)} trades extraídos.")
    print(f"Total In-Sample: {len(is_trajs)} trades en {time.time() - t0:.1f}s.")

    # 2. Cargar Out-of-Sample
    print("\n[2/4] Extrayendo trades Out-of-Sample (GC 04-26 + GC 06-26)...")
    t0 = time.time()
    oos_trajs = []
    for c in out_of_sample_contracts:
        f = data_path / f"{c.replace(' ', '_')}_ticks.parquet"
        trajs = load_contract_trajectories(f, c, config)
        oos_trajs.extend(trajs)
        print(f"  {c}: {len(trajs)} trades extraídos.")
    print(f"Total Out-of-Sample: {len(oos_trajs)} trades en {time.time() - t0:.1f}s.")

    # 3. Conjuntos de Filtros
    # Evaluamos:
    # - "SIN_FILTRO"
    # - "TREND_EMA_{P}" (Buy >= EMA, Sell <= EMA - Hipótesis Usuario)
    # - "REVERT_EMA_{P}" (Buy < EMA, Sell > EMA - Reversión a la media)
    filter_keys = ["SIN_FILTRO"]
    for p in EMA_PERIODS:
        filter_keys.append(f"TREND_EMA_{p}")
        filter_keys.append(f"REVERT_EMA_{p}")

    def filter_trajs(trajs: List[Dict[str, Any]], f_key: str) -> List[Dict[str, Any]]:
        if f_key == "SIN_FILTRO":
            return trajs
        if f_key.startswith("TREND_EMA_"):
            p = int(f_key.replace("TREND_EMA_", ""))
            return [t for t in trajs if t["trend_pass"][p]]
        if f_key.startswith("REVERT_EMA_"):
            p = int(f_key.replace("REVERT_EMA_", ""))
            return [t for t in trajs if t["revert_pass"][p]]
        return trajs

    # 4. Evaluaciones de Ejecución
    # Probamos las 3 configuraciones cardinales de ejecución validadas en el informe previo:
    # 1. Asimétrica Máxima: SL 1.0x, TP 12.0 pt, Sin BE
    # 2. Equilibrada: SL 1.5x, TP 6.0 pt, Sin BE
    # 3. Alto Win Rate: SL 1.5x, TP 4.0 pt, Sin BE
    # 4. Con Break-Even: SL 1.5x, TP 6.0 pt, BE 2.5 pt
    exec_profiles = [
        {"name": "Asimétrica (TP 12.0 pt / SL 1.0x / No BE)", "sl_m": 1.0, "tp_p": 12.0, "be_p": None},
        {"name": "Equilibrada (TP 6.0 pt / SL 1.5x / No BE)", "sl_m": 1.5, "tp_p": 6.0, "be_p": None},
        {"name": "Alto Win Rate (TP 4.0 pt / SL 1.5x / No BE)", "sl_m": 1.5, "tp_p": 4.0, "be_p": None},
        {"name": "Con BE (TP 6.0 pt / SL 1.5x / BE 2.5 pt)", "sl_m": 1.5, "tp_p": 6.0, "be_p": 2.5},
    ]

    all_results = {}

    print("\n[3/4] Evaluando Cuadrícula de Filtros EMA × Perfiles de Ejecución...")

    for prof in exec_profiles:
        p_name = prof["name"]
        sl_m = prof["sl_m"]
        tp_p = prof["tp_p"]
        be_p = prof["be_p"]
        all_results[p_name] = {}

        print(f"\n" + "=" * 90)
        print(f"PERFIL: {p_name}")
        print("=" * 90)
        print(f"{'Filtro':<18} | {'IS Trades':<9} {'IS Win%':<8} {'IS Net USD':<12} {'IS PF':<6} | {'OOS Trades':<10} {'OOS Win%':<9} {'OOS Net USD':<13} {'OOS PF':<6}")
        print("-" * 90)

        for f_key in filter_keys:
            is_sub = filter_trajs(is_trajs, f_key)
            oos_sub = filter_trajs(oos_trajs, f_key)

            is_res = evaluate_trajectories_set(is_sub, sl_m, tp_p, be_p)
            oos_res = evaluate_trajectories_set(oos_sub, sl_m, tp_p, be_p)

            all_results[p_name][f_key] = {
                "in_sample": is_res,
                "out_of_sample": oos_res
            }

            is_usd_str = f"${is_res['total_usd']:>10,.0f}"
            oos_usd_str = f"${oos_res['total_usd']:>11,.0f}"
            print(f"{f_key:<18} | {is_res['total_trades']:<9} {is_res['win_rate']:<7.1f}% {is_usd_str} {is_res['profit_factor']:<6.2f} | "
                  f"{oos_res['total_trades']:<10} {oos_res['win_rate']:<8.1f}% {oos_usd_str} {oos_res['profit_factor']:<6.2f}")

    # Guardar resultados
    out_file = Path(f"docs/research/bigtrap_gc_ema_{ticks_per_bar}tick_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ticks_per_bar": ticks_per_bar,
            "ema_periods": EMA_PERIODS,
            "friction": {"commission_rt_usd": 4.50, "slippage_stops_ticks": 1},
            "results": all_results
        }, f, indent=2)

    print(f"\n[4/4] Resultados exportados a {out_file.as_posix()}")
    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimizador Causal de Filtro EMA para BigTrapGC")
    parser.add_argument("--ticks-per-bar", type=int, default=25, help="Resolución de barras de ticks (default 25)")
    args = parser.parse_args()
    run_experiment(ticks_per_bar=args.ticks_per_bar)
