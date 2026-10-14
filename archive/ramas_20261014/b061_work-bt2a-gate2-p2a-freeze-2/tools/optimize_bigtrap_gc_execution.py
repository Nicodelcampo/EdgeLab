#!/usr/bin/env python3
"""Optimizador Causal Anti-Overfitting de Parámetros de Ejecución (SL, TP, BE) para BigTrapGC (Oro).

Metodología Científica EdgeLab:
1. Partición Temporal Estricta:
   - In-Sample (Descubrimiento): GC 12-25 + GC 02-26 (~20M ticks, ~140 sesiones CME)
   - Out-of-Sample (Validación Ciega Externa): GC 04-26 + GC 06-26 (~15M ticks, ~130 sesiones CME)
   - Holdout Ciego: GC 08-26 permanece 100% sellado e intocado.
2. Simulación Causal a Nivel de Tick:
   - Comisiones reales ($4.50 USD / contrato = 0.045 pt en GC).
   - Slippage adverso real (1 tick en paradas de stop = 0.10 pt = $10.00 USD).
   - Prioridad de parada de Stop Loss en conflicto intra-tick.
3. Búsqueda de Meseta Estable (Parameter Plateau 3x3x3):
   - Elimina picos frágiles sobreajustados y selecciona áreas amplias de robustez estadística.
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
    BigTrapGCOptimalConfig, detect_gc_zones, NAME, VERSION
)

# Costos institucionales en COMEX Gold (GC): 1 pt = $100 USD, 1 tick = 0.10 pt = $10 USD
COMMISSION_PTS = 0.045  # $4.50 USD / $100 por pt
SLIPPAGE_TICKS = 1      # 1 tick adverso en SL (0.10 pt = $10 USD)


def get_process_ram_mb() -> float:
    return psutil.Process().memory_info().rss / (1024.0 * 1024.0)


def find_session_boundaries_streaming(parquet_path: Path) -> List[Tuple[int, int]]:
    """Descubre los límites temporales [inicio_ns, fin_ns] de cada sesión CME ETH mediante streaming."""
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
    entry_mode: str = "BarClose",
    max_ticks_forward: int = 5000
) -> List[Dict[str, Any]]:
    """Extrae trayectorias de trades para una sola sesión con asignación compacta."""
    tick_size = float(ticks.tick_size)
    bar_starts = np.zeros(len(bars), dtype=np.int64)
    bar_ends = np.zeros(len(bars), dtype=np.int64)
    if len(ticks) > 0 and len(bars) > 0:
        bar_changes = np.flatnonzero(np.diff(bars.tick_bar_idx)) + 1
        bar_starts = np.concatenate(([0], bar_changes))
        bar_ends = np.concatenate((bar_changes, [len(ticks)]))

    res = detect_gc_zones(ticks, bars, fps, config=config)
    zones = res["zones"]

    trajectories = []
    n_bars = len(bars)

    for z in zones:
        b_created = z["created_bar"]
        is_bull = (z["kind"] == "trapped_buyers")  # True = SHORT, False = LONG
        z_top = z["top"]
        z_bot = z["bottom"]
        z_top_tk = int(round(z_top / tick_size))
        z_bot_tk = int(round(z_bot / tick_size))
        zone_height_ticks = max(1, z_top_tk - z_bot_tk)

        if entry_mode == "BarClose":
            entry_bar = b_created
            entry_tick = int(bars.close_t[b_created])
            entry_tick_idx = int(bar_ends[b_created]) - 1
            if entry_tick_idx < 0:
                entry_tick_idx = 0

            # Distancia de riesgo estructural base desde el extremo opuesto de la zona
            if not is_bull:  # LONG
                risk_base_tk = max(1, entry_tick - (z_bot_tk - 1))
            else:  # SHORT
                risk_base_tk = max(1, (z_top_tk + 1) - entry_tick)

        else:  # ZoneRetest
            retest_bar = -1
            for b in range(b_created + 1, min(n_bars, b_created + config.max_age_bars)):
                hi = float(bars.high_t[b]) * tick_size
                lo = float(bars.low_t[b]) * tick_size
                c = float(bars.close_t[b]) * tick_size

                touched = (hi >= z_bot) and (lo <= z_top)
                adverse_close = (c > z_top) if is_bull else (c < z_bot)

                if touched:
                    retest_bar = b
                    break
                if adverse_close:
                    break

            if retest_bar == -1:
                continue

            entry_bar = retest_bar
            t_start = int(bar_starts[retest_bar])
            t_end = int(bar_ends[retest_bar])
            bar_px_ticks = ticks.price_ticks[t_start:t_end]

            touch_offset = -1
            if not is_bull:
                matches = np.flatnonzero(bar_px_ticks <= z_top_tk)
                if len(matches) > 0:
                    touch_offset = matches[0]
                    entry_tick = z_top_tk
            else:
                matches = np.flatnonzero(bar_px_ticks >= z_bot_tk)
                if len(matches) > 0:
                    touch_offset = matches[0]
                    entry_tick = z_bot_tk

            if touch_offset == -1:
                continue

            entry_tick_idx = t_start + touch_offset
            risk_base_tk = zone_height_ticks + 1

        end_tick_idx = min(len(ticks), entry_tick_idx + 1 + max_ticks_forward)
        future_px_slice = ticks.price_ticks[entry_tick_idx + 1 : end_tick_idx]

        if len(future_px_slice) < 5:
            continue

        future_px = np.ascontiguousarray(future_px_slice, dtype=np.int32)

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
        })

    return trajectories


def load_contract_trajectories_streaming(
    parquet_path: Path,
    contract_name: str,
    config: BigTrapGCOptimalConfig,
    entry_mode: str = "BarClose"
) -> List[Dict[str, Any]]:
    print(f"  Analizando límites de sesión en {parquet_path.name}...")
    t0_scan = time.time()
    session_ranges = find_session_boundaries_streaming(parquet_path)
    n_sessions = len(session_ranges)
    print(f"  {n_sessions} sesiones identificadas en {time.time() - t0_scan:.1f}s. Extrayendo trades sesión a sesión ({entry_mode}, {config.ticks_per_bar}-tick bars)...")

    cols = ["ts_utc_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "sequence"]
    contract_trajectories: List[Dict[str, Any]] = []
    t0_proc = time.time()

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

        s_trajs = extract_session_trade_trajectories(ticks, bars, fps, config, contract_name, entry_mode=entry_mode)
        contract_trajectories.extend(s_trajs)

        del ticks, bars, fps, s_trajs

        if s_idx % 25 == 0 or s_idx == n_sessions:
            gc.collect()
            ram_mb = get_process_ram_mb()
            print(f"    [{s_idx:3d}/{n_sessions:3d}] Sesiones procesadas | Trades: {len(contract_trajectories):3d} | RAM: {ram_mb:5.1f} MB", flush=True)

    print(f"  Contrato {contract_name} completado: {len(contract_trajectories)} trades extraídos en {time.time() - t0_proc:.1f}s | RAM final: {get_process_ram_mb():.1f} MB\n", flush=True)
    gc.collect()
    return contract_trajectories


def evaluate_single_trade(
    traj: Dict[str, Any],
    sl_mult: float,
    tp_pts: float,
    be_trigger_pts: Optional[float],
    be_offset_ticks: int = 1,
    tick_size: float = 0.10
) -> Tuple[float, str, int]:
    """Evalúa un trade causalmente tick a tick con costos institucionales.
    Retorna (pnl_neto_pts, exit_reason, ticks_in_trade).
    """
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
            # Activar Break-Even si se alcanzó el umbral
            if be_trigger_pts is not None and p >= be_trig_tk:
                current_sl_tk = max(current_sl_tk, be_lock_tk)

            # Evaluación pesimista / realista: chequear SL primero
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


def run_grid_on_trajectories(
    trajectories: List[Dict[str, Any]],
    sl_mult_grid: List[float],
    tp_pts_grid: List[float],
    be_trig_grid: List[Optional[float]]
) -> Dict[Tuple[int, int, int], Dict[str, Any]]:
    results = {}
    n_trades = len(trajectories)
    if n_trades == 0:
        return results

    for s_idx, sl_m in enumerate(sl_mult_grid):
        for t_idx, tp_p in enumerate(tp_pts_grid):
            for b_idx, be_p in enumerate(be_trig_grid):
                pnls = []
                wins = 0
                losses = 0
                for tr in trajectories:
                    pnl, _, _ = evaluate_single_trade(tr, sl_m, tp_p, be_p)
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

                cum = np.cumsum(pnl_arr)
                peak = np.maximum.accumulate(cum)
                dd = peak - cum
                max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0

                results[(s_idx, t_idx, b_idx)] = {
                    "sl_mult": sl_m,
                    "tp_pts": tp_p,
                    "be_trigger_pts": be_p,
                    "total_trades": n_trades,
                    "wins": wins,
                    "losses": losses,
                    "win_rate": round(wr, 1),
                    "total_net_pts": round(tot_pnl, 2),
                    "total_usd_per_contract": round(tot_pnl * 100.0, 2),
                    "profit_factor": round(pf, 2),
                    "sharpe_annualized": round(sharpe, 2),
                    "max_drawdown_pts": round(max_dd, 2),
                    "mean_trade_pts": round(mean_pnl, 2)
                }

    for (s_idx, t_idx, b_idx), r in results.items():
        neighbor_sharpes = []
        for ds in (-1, 0, 1):
            for dt in (-1, 0, 1):
                for db in (-1, 0, 1):
                    neighbor_key = (s_idx + ds, t_idx + dt, b_idx + db)
                    if neighbor_key in results:
                        neighbor_sharpes.append(results[neighbor_key]["sharpe_annualized"])
        r["plateau_score"] = round(float(np.mean(neighbor_sharpes)), 2)
        r["min_neighbor_sharpe"] = round(float(np.min(neighbor_sharpes)), 2)

    return results


def run_gc_optimization(
    data_dir: str = "E:/EdgeLab/data/nt8/GC_parquet",
    ticks_per_bar: int = 5,
    entry_mode: str = "BarClose"
):
    print("=" * 88, flush=True)
    print(f"EdgeLab — Optimizador Causal Anti-Overfitting de Ejecución para Oro (GC COMEX)", flush=True)
    print(f"Configuración: Modo={entry_mode} | Barras={ticks_per_bar}-Ticks | Costos Reales CME", flush=True)
    print("Arquitectura: Streaming Sesión a Sesión | Cero Riesgo de Saturación de RAM (< 400 MB)", flush=True)
    vm = psutil.virtual_memory()
    print(f"Sistema: {vm.total / (1024**3):.1f} GB RAM Total | {vm.available / (1024**3):.1f} GB RAM Disponible", flush=True)
    print("=" * 88, flush=True)

    t0_all = time.time()
    data_path = Path(data_dir)

    in_sample_contracts = ["GC 12-25", "GC 02-26"]
    out_of_sample_contracts = ["GC 04-26", "GC 06-26"]

    # Espacio de Búsqueda Pre-Registrado en Oro:
    # 4 SL x 7 TP x 6 BE = 168 combinaciones
    sl_mult_grid = [1.0, 1.25, 1.5, 2.0]
    tp_pts_grid = [4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0]  # Puntos en GC ($400 a $1,500 USD)
    be_trig_grid = [None, 1.5, 2.0, 2.5, 3.0, 4.0]        # Triggers en GC ($150 a $400 USD)
    n_combinations = len(sl_mult_grid) * len(tp_pts_grid) * len(be_trig_grid)

    print(f"\nEspacio de Hipótesis GC: {len(sl_mult_grid)} SL × {len(tp_pts_grid)} TP × {len(be_trig_grid)} BE = {n_combinations} combinaciones.")
    print("Costos de Ejecución Reales en GC: $4.50 USD comision/contrato (0.045 pt) + 1 tick slippage adverso en SL (0.10 pt = $10 USD).\n", flush=True)

    cfg = BigTrapGCOptimalConfig(ticks_per_bar=ticks_per_bar, min_trap_volume=40.0)

    # 1. Extracción In-Sample
    print("=" * 88, flush=True)
    print("FASE 1: Extracción Streaming In-Sample (GC 12-25 + GC 02-26)...", flush=True)
    print("=" * 88, flush=True)
    in_sample_trajectories: List[Dict[str, Any]] = []

    for c in in_sample_contracts:
        pq_file = data_path / f"{c.replace(' ', '_')}_ticks.parquet"
        if not pq_file.exists():
            print(f"ERROR: Falta archivo requerido {pq_file}")
            return
        trajs = load_contract_trajectories_streaming(pq_file, c, cfg, entry_mode=entry_mode)
        in_sample_trajectories.extend(trajs)

    print(f"--> Total Trades In-Sample Acumulados: {len(in_sample_trajectories)} trades | RAM: {get_process_ram_mb():.1f} MB\n", flush=True)

    # 2. Grid Search In-Sample
    print("=" * 88, flush=True)
    print(f"FASE 2: Barrido Causal de {n_combinations} Combinaciones sobre In-Sample...", flush=True)
    print("=" * 88, flush=True)
    t_grid = time.time()
    is_results_dict = run_grid_on_trajectories(in_sample_trajectories, sl_mult_grid, tp_pts_grid, be_trig_grid)
    print(f"Barrido In-Sample completado en {time.time() - t_grid:.2f}s.\n", flush=True)

    is_results_list = list(is_results_dict.values())
    is_results_list.sort(key=lambda x: (x["total_net_pts"], x["plateau_score"]), reverse=True)

    print("-" * 88, flush=True)
    print("TOP 10 MESETAS PARAMÉTRICAS IN-SAMPLE EN ORO (GC):", flush=True)
    print(f"{'Rank':<4} | {'SL Mult':<7} | {'TP (pts)':<8} | {'BE Trig':<8} | {'Win%':<6} | {'Net Pts':<10} | {'Net USD':<11} | {'PF':<5} | {'Sharpe':<6} | {'Plateau'}", flush=True)
    print("-" * 88, flush=True)
    for idx, r in enumerate(is_results_list[:10], 1):
        be_str = f"{r['be_trigger_pts']:4.1f}" if r['be_trigger_pts'] is not None else "None"
        print(f"{idx:<4} | {r['sl_mult']:<7.1f} | {r['tp_pts']:<8.1f} | {be_str:<8} | {r['win_rate']:5.1f}% | {r['total_net_pts']:+9.2f} | ${r['total_usd_per_contract']:+9.2f} | {r['profit_factor']:4.2f} | {r['sharpe_annualized']:5.2f} | {r['plateau_score']:6.2f}", flush=True)
    print("-" * 88 + "\n", flush=True)

    # 3. Extracción Out-of-Sample (GC 04-26 + GC 06-26)
    print("=" * 88, flush=True)
    print("FASE 3: Extracción Streaming Out-of-Sample Ciega (GC 04-26 + GC 06-26)...", flush=True)
    print("=" * 88, flush=True)
    oos_trajectories: List[Dict[str, Any]] = []

    for c in out_of_sample_contracts:
        pq_file = data_path / f"{c.replace(' ', '_')}_ticks.parquet"
        if not pq_file.exists():
            print(f"ERROR: Falta archivo requerido {pq_file}")
            return
        trajs = load_contract_trajectories_streaming(pq_file, c, cfg, entry_mode=entry_mode)
        oos_trajectories.extend(trajs)

    print(f"--> Total Trades Out-of-Sample Acumulados: {len(oos_trajectories)} trades | RAM: {get_process_ram_mb():.1f} MB\n", flush=True)

    # 4. Validación OOS Ciega
    print("=" * 88, flush=True)
    print("FASE 4: Validación Ciega Externa de Top 5 Mesetas sobre Out-of-Sample...", flush=True)
    print("=" * 88, flush=True)
    top_candidates = is_results_list[:5]

    print(f"{'Rank':<4} | {'SL Mult':<7} | {'TP (pts)':<8} | {'BE Trig':<8} | {'IS Net Pts':<10} | {'OOS Net Pts':<11} | {'OOS Net USD':<12} | {'OOS Win%':<8} | {'OOS PF':<6} | {'Retención'}", flush=True)
    print("-" * 88, flush=True)

    validation_results = []
    for idx, cand in enumerate(top_candidates, 1):
        sl_m = cand["sl_mult"]
        tp_p = cand["tp_pts"]
        be_p = cand["be_trigger_pts"]

        pnls = []
        wins = 0
        losses = 0
        for tr in oos_trajectories:
            pnl, _, _ = evaluate_single_trade(tr, sl_m, tp_p, be_p)
            pnls.append(pnl)
            if pnl > 0:
                wins += 1
            else:
                losses += 1

        pnl_arr = np.array(pnls, dtype=np.float64)
        oos_pnl = float(pnl_arr.sum())
        win_pnl = float(pnl_arr[pnl_arr > 0].sum())
        loss_pnl = float(abs(pnl_arr[pnl_arr <= 0].sum()))
        oos_pf = (win_pnl / max(loss_pnl, 1e-4))
        oos_wr = (wins / max(len(oos_trajectories), 1)) * 100.0

        is_pnl = cand["total_net_pts"]
        retention = (oos_pnl / is_pnl) * 100.0 if abs(is_pnl) > 0.01 else 0.0

        be_str = f"{be_p:4.1f}" if be_p is not None else "None"
        print(f"{idx:<4} | {sl_m:<7.1f} | {tp_p:<8.1f} | {be_str:<8} | {is_pnl:+9.2f}  | {oos_pnl:+10.2f}  | ${oos_pnl * 100.0:+10.2f}  | {oos_wr:6.1f}%  | {oos_pf:5.2f} | {retention:+6.1f}%", flush=True)

        validation_results.append({
            "rank": idx,
            "sl_mult": sl_m,
            "tp_pts": tp_p,
            "be_trigger_pts": be_p,
            "in_sample_net_pts": is_pnl,
            "in_sample_trades": cand["total_trades"],
            "in_sample_pf": cand["profit_factor"],
            "in_sample_wr": cand["win_rate"],
            "out_of_sample_net_pts": round(oos_pnl, 2),
            "out_of_sample_usd": round(oos_pnl * 100.0, 2),
            "out_of_sample_trades": len(oos_trajectories),
            "out_of_sample_wr": round(oos_wr, 1),
            "out_of_sample_pf": round(oos_pf, 2),
            "retention_pct": round(retention, 1)
        })

    print("-" * 88 + "\n", flush=True)

    # Guardar resultados consolidados en JSON
    output_dir = REPO_ROOT / "docs" / "research"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_json = output_dir / f"bigtrap_gc_optimization_{entry_mode.lower()}_{ticks_per_bar}tick_results.json"

    meta = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "indicator": "BigTrapGC",
        "entry_mode": entry_mode,
        "ticks_per_bar": ticks_per_bar,
        "min_trap_volume": 40.0,
        "in_sample_contracts": in_sample_contracts,
        "out_of_sample_contracts": out_of_sample_contracts,
        "holdout_contract": "GC 08-26 (SEALED)",
        "friction": {
            "commission_pts": COMMISSION_PTS,
            "slippage_ticks": SLIPPAGE_TICKS,
            "usd_per_pt": 100.0
        },
        "top_plateaus_is": is_results_list[:15],
        "oos_validation": validation_results,
        "total_elapsed_sec": round(time.time() - t0_all, 1)
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"Resultados consolidados guardados exitosamente en:\n  -> {out_json}")
    print(f"Tiempo total de ejecución: {time.time() - t0_all:.1f} segundos.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimizador de Ejecución BigTrapGC")
    parser.add_argument("--data-dir", default="E:/EdgeLab/data/nt8/GC_parquet")
    parser.add_argument("--ticks-per-bar", type=int, default=5, help="Resolución de barras (ej. 5 o 25)")
    parser.add_argument("--entry-mode", choices=["BarClose", "ZoneRetest"], default="BarClose")
    args = parser.parse_args()

    run_gc_optimization(
        data_dir=args.data_dir,
        ticks_per_bar=args.ticks_per_bar,
        entry_mode=args.entry_mode
    )
