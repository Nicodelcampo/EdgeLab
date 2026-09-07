#!/usr/bin/env python3
"""Optimizador Causal y Auditoría Forense de Ejecución para BigTrapGC en Barras de 10 Ticks.

Metodología Científica EdgeLab:
- Resolución: 10-Tick Bars (COMEX Gold, tick_size = 0.10, $100/pt).
- Modo de Entrada: BarClose (al cierre de la vela de absorción).
- Ejecución Realista: Secuencial Estricta (1 sola posición abierta a la vez).
- Fricciones Reales: $4.50 USD comisión CME + 1 tick slippage adverso en Stop Losses.
- Partición Anti-Overfitting:
  * In-Sample (Descubrimiento): GC 12-25 + GC 02-26 (~20M ticks, ~200 sesiones)
  * Out-of-Sample (Validación Ciega): GC 04-26 + GC 06-26 (~15M ticks, ~140 sesiones)
  * Holdout: GC 08-26 (SELLADO)
- Métricas de Falsación: Max Losing Streak, Max Drawdown, Desglose por Contrato, Long vs Short.
"""
from __future__ import annotations

import gc
import json
import math
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

COMMISSION_PTS = 0.045  # $4.50 USD / contrato
SLIPPAGE_TICKS = 1      # 1 tick adverso en SL (0.10 pt = $10.00 USD)
USD_PER_PT = 100.0


def get_process_ram_mb() -> float:
    return psutil.Process().memory_info().rss / (1024.0 * 1024.0)


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
    session_idx: int,
    max_ticks_forward: int = 5000
) -> List[Dict[str, Any]]:
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
    for z in zones:
        b_created = z["created_bar"]
        is_bull = (z["kind"] == "trapped_buyers")  # True = SHORT, False = LONG
        side = "SHORT" if is_bull else "LONG"

        z_top_tk = int(round(z["top"] / tick_size))
        z_bot_tk = int(round(z["bottom"] / tick_size))
        zone_height_ticks = max(1, z_top_tk - z_bot_tk)

        # Entrada BarClose: al cierre de la vela de señal
        entry_bar = b_created
        entry_tick = int(bars.close_t[b_created])
        entry_tick_idx = int(bar_ends[b_created]) - 1
        if entry_tick_idx < 0:
            entry_tick_idx = 0

        if not is_bull:  # LONG
            risk_base_tk = max(1, entry_tick - (z_bot_tk - 1))
        else:  # SHORT
            risk_base_tk = max(1, (z_top_tk + 1) - entry_tick)

        future_px_slice = ticks.price_ticks[entry_tick_idx + 1 : entry_tick_idx + 1 + max_ticks_forward]
        if len(future_px_slice) < 5:
            continue

        future_px = np.ascontiguousarray(future_px_slice, dtype=np.int32)

        trajectories.append({
            "contract": contract_name,
            "session": session_idx,
            "side": side,
            "is_bull": is_bull,
            "entry_bar": entry_bar,
            "entry_tick_idx": entry_tick_idx,
            "entry_tick": entry_tick,
            "entry_px": entry_tick * tick_size,
            "risk_base_tk": risk_base_tk,
            "future_ticks": future_px,
        })

    return trajectories


def load_contract_trajectories(
    parquet_path: Path,
    contract_name: str,
    ticks_per_bar: int = 10
) -> List[Dict[str, Any]]:
    print(f"  Analizando límites de sesión en {parquet_path.name}...")
    session_ranges = find_session_boundaries_streaming(parquet_path)
    n_sessions = len(session_ranges)
    print(f"  {n_sessions} sesiones CME ETH identificadas. Extrayendo trades (BarClose, {ticks_per_bar}-ticks)...")

    cfg = BigTrapGCOptimalConfig(ticks_per_bar=ticks_per_bar, min_trap_volume=40.0)
    cols = ["ts_utc_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "sequence"]
    contract_trajectories: List[Dict[str, Any]] = []
    t0_proc = time.time()

    for s_idx, (t_start, t_end) in enumerate(session_ranges, 1):
        tbl = pq.read_table(
            parquet_path,
            filters=[("ts_utc_ns", ">=", t_start), ("ts_utc_ns", "<=", t_end)],
            columns=cols
        )
        if tbl.num_rows < 100:
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

        bars = build_tick_bars(ticks, ticks_per_bar=ticks_per_bar, reiniciar_por_sesion=True)
        fps = build_footprints(ticks, bars)

        s_trajs = extract_session_trade_trajectories(ticks, bars, fps, cfg, contract_name, s_idx)
        contract_trajectories.extend(s_trajs)

        del ticks, bars, fps, s_trajs

        if s_idx % 30 == 0 or s_idx == n_sessions:
            gc.collect()
            print(f"    [{s_idx:3d}/{n_sessions:3d}] Sesiones | Trades acumulados: {len(contract_trajectories):4d} | RAM: {get_process_ram_mb():5.1f} MB", flush=True)

    print(f"  Contrato {contract_name} finalizado: {len(contract_trajectories)} trades en {time.time() - t0_proc:.1f}s | RAM: {get_process_ram_mb():.1f} MB\n", flush=True)
    gc.collect()
    return contract_trajectories


def evaluate_trade_causal(
    traj: Dict[str, Any],
    sl_mult: float,
    tp_pts: float,
    be_trigger_pts: Optional[float] = None,
    tick_size: float = 0.10
) -> Tuple[float, str, int]:
    """Evalúa causalmente el trade tick por tick con prioridad conservadora de Stop Loss."""
    entry_tk = traj["entry_tick"]
    side = traj["side"]
    future = traj["future_ticks"]
    risk_base_tk = traj["risk_base_tk"]

    sl_dist_tk = max(1, int(round(risk_base_tk * sl_mult)))
    tp_dist_tk = max(2, int(round(tp_pts / tick_size)))
    be_trig_dist_tk = int(round(be_trigger_pts / tick_size)) if be_trigger_pts is not None else None

    if side == "LONG":
        current_sl_tk = entry_tk - sl_dist_tk
        tp_target_tk = entry_tk + tp_dist_tk
        be_thresh_tk = entry_tk + be_trig_dist_tk if be_trig_dist_tk is not None else 999999999
        be_lock_tk = entry_tk + 1  # Lock +1 tick ($10 USD)

        for i, p in enumerate(future):
            # Activar BE si alcanzó el umbral
            if be_trig_dist_tk is not None and p >= be_thresh_tk:
                current_sl_tk = max(current_sl_tk, be_lock_tk)

            # Prioridad de SL en ambigüedad
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
        current_sl_tk = entry_tk + sl_dist_tk
        tp_target_tk = entry_tk - tp_dist_tk
        be_thresh_tk = entry_tk - be_trig_dist_tk if be_trig_dist_tk is not None else -999999999
        be_lock_tk = entry_tk - 1

        for i, p in enumerate(future):
            if be_trig_dist_tk is not None and p <= be_thresh_tk:
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


def simulate_sequential_trades(
    trajectories: List[Dict[str, Any]],
    sl_mult: float,
    tp_pts: float,
    be_trigger_pts: Optional[float]
) -> List[Dict[str, Any]]:
    """Simula ejecución realista de 1 sola posición activa a la vez por sesión."""
    sequential = []
    current_session = None
    last_exit_tick_idx = -1

    for tr in trajectories:
        ses = tr["session"]
        if ses != current_session:
            current_session = ses
            last_exit_tick_idx = -1

        entry_idx = tr["entry_tick_idx"]
        if entry_idx > last_exit_tick_idx:
            pnl, reason, dur = evaluate_trade_causal(tr, sl_mult, tp_pts, be_trigger_pts)
            sequential.append({
                "contract": tr["contract"],
                "session": ses,
                "side": tr["side"],
                "pnl_pts": pnl,
                "pnl_usd": pnl * USD_PER_PT,
                "reason": reason,
                "duration_ticks": dur
            })
            last_exit_tick_idx = entry_idx + dur

    return sequential


def run_10tick_optimization():
    print("=" * 88)
    print("EdgeLab — Optimización y Falsación Causal en 10 Ticks (GC COMEX)")
    print("Configuración: Modo=BarClose | 10-Tick Bars | 1 Sola Posición Realista | Costos CME")
    vm = psutil.virtual_memory()
    print(f"Sistema: {vm.total / (1024**3):.1f} GB RAM Total | {vm.available / (1024**3):.1f} GB Disponible")
    print("=" * 88)

    t0 = time.time()
    data_dir = Path("E:/EdgeLab/data/nt8/GC_parquet")
    in_sample_contracts = ["GC 12-25", "GC 02-26"]
    out_of_sample_contracts = ["GC 04-26", "GC 06-26"]

    # Espacio de Búsqueda Pre-Registrado:
    # 4 SL x 8 TP x 6 BE = 192 combinaciones
    sl_mult_grid = [1.0, 1.25, 1.5, 2.0]
    tp_pts_grid = [2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0]  # Puntos ($250 a $1,000 USD)
    be_trig_grid = [None, 1.0, 1.5, 2.0, 2.5, 3.0]            # Gatillos de BE en puntos
    n_combinations = len(sl_mult_grid) * len(tp_pts_grid) * len(be_trig_grid)

    print(f"\nEspacio de Hipótesis: {len(sl_mult_grid)} SL × {len(tp_pts_grid)} TP × {len(be_trig_grid)} BE = {n_combinations} combinaciones.\n")

    # 1. Extracción In-Sample
    print("=" * 88)
    print("FASE 1: Extracción Streaming In-Sample (GC 12-25 + GC 02-26)...")
    print("=" * 88)
    is_trajs = []
    for c in in_sample_contracts:
        f = data_dir / f"{c.replace(' ', '_')}_ticks.parquet"
        is_trajs.extend(load_contract_trajectories(f, c, ticks_per_bar=10))

    print(f"--> Total Trades In-Sample Extraídos: {len(is_trajs)} trades | RAM: {get_process_ram_mb():.1f} MB\n")

    # 2. Extracción Out-of-Sample
    print("=" * 88)
    print("FASE 2: Extracción Streaming Out-of-Sample Ciega (GC 04-26 + GC 06-26)...")
    print("=" * 88)
    oos_trajs = []
    for c in out_of_sample_contracts:
        f = data_dir / f"{c.replace(' ', '_')}_ticks.parquet"
        oos_trajs.extend(load_contract_trajectories(f, c, ticks_per_bar=10))

    print(f"--> Total Trades Out-of-Sample Extraídos: {len(oos_trajs)} trades | RAM: {get_process_ram_mb():.1f} MB\n")

    # 3. Barrido Secuencial Realista In-Sample
    print("=" * 88)
    print(f"FASE 3: Barrido Secuencial Realista (1 posición activa) de {n_combinations} Combinaciones...")
    print("=" * 88)

    is_results = []
    t_grid = time.time()

    for sl_m in sl_mult_grid:
        for tp_p in tp_pts_grid:
            for be_p in be_trig_grid:
                seq_trades = simulate_sequential_trades(is_trajs, sl_m, tp_p, be_p)
                if not seq_trades:
                    continue

                pnls = np.array([t["pnl_pts"] for t in seq_trades], dtype=np.float64)
                usds = np.array([t["pnl_usd"] for t in seq_trades], dtype=np.float64)
                n = len(seq_trades)
                wins = int((pnls > 0).sum())
                losses = int((pnls <= 0).sum())
                wr = (wins / n) * 100.0

                tot_pnl_usd = float(usds.sum())
                tot_pnl_pts = float(pnls.sum())
                gw = float(pnls[pnls > 0].sum())
                gl = float(abs(pnls[pnls <= 0].sum()))
                pf = (gw / max(gl, 1e-4))

                cum = np.cumsum(usds)
                peak = np.maximum.accumulate(cum)
                dd = peak - cum
                max_dd_usd = float(np.max(dd)) if len(dd) > 0 else 0.0

                # Max Losing streak
                max_streak = 0
                cur_streak = 0
                for p in pnls:
                    if p <= 0:
                        cur_streak += 1
                        if cur_streak > max_streak:
                            max_streak = cur_streak
                    else:
                        cur_streak = 0

                is_results.append({
                    "sl_mult": sl_m,
                    "tp_pts": tp_p,
                    "be_trigger_pts": be_p,
                    "is_trades": n,
                    "is_win_rate": round(wr, 1),
                    "is_pnl_pts": round(tot_pnl_pts, 2),
                    "is_pnl_usd": round(tot_pnl_usd, 2),
                    "is_pf": round(pf, 2),
                    "is_max_dd_usd": round(max_dd_usd, 2),
                    "is_max_streak": max_streak
                })

    print(f"Barrido In-Sample completado en {time.time() - t_grid:.2f}s.\n")

    # Ordenar por PnL Neto y Profit Factor
    is_results.sort(key=lambda x: (x["is_pnl_usd"], x["is_pf"]), reverse=True)

    print("-" * 88)
    print("TOP 10 CONFIGURACIONES IN-SAMPLE EN 10 TICKS (SECUENCIAL REALISTA):")
    print(f"{'Rank':<4} | {'SL Mult':<7} | {'TP (pts)':<8} | {'BE Trig':<8} | {'Win%':<6} | {'Net USD':<12} | {'PF':<5} | {'Max DD ($)':<11} | {'Max Streak'}")
    print("-" * 88)
    for idx, r in enumerate(is_results[:10], 1):
        be_str = f"{r['be_trigger_pts']:4.1f}" if r['be_trigger_pts'] is not None else "None"
        print(f"{idx:<4} | {r['sl_mult']:<7.1f} | {r['tp_pts']:<8.1f} | {be_str:<8} | {r['is_win_rate']:5.1f}% | ${r['is_pnl_usd']:+10.2f} | {r['is_pf']:4.2f} | ${r['is_max_dd_usd']:9.2f} | {r['is_max_streak']:3d} pérdidas", flush=True)
    print("-" * 88 + "\n")

    # 4. Validación Out-of-Sample Ciega de las Top 5
    print("=" * 88)
    print("FASE 4: Validación Ciega Out-of-Sample de las Mejores Mesetas...")
    print("=" * 88)
    top_candidates = is_results[:8]

    print(f"{'Rank':<4} | {'SL':<4} | {'TP':<4} | {'BE':<5} | {'IS Net USD':<12} | {'OOS Net USD':<13} | {'OOS Win%':<8} | {'OOS PF':<6} | {'OOS Max DD':<11} | {'OOS Streak'}")
    print("-" * 88)

    final_validation = []
    for idx, cand in enumerate(top_candidates, 1):
        sl_m = cand["sl_mult"]
        tp_p = cand["tp_pts"]
        be_p = cand["be_trigger_pts"]

        oos_seq = simulate_sequential_trades(oos_trajs, sl_m, tp_p, be_p)
        pnls = np.array([t["pnl_pts"] for t in oos_seq], dtype=np.float64)
        usds = np.array([t["pnl_usd"] for t in oos_seq], dtype=np.float64)
        n = len(oos_seq)
        wins = int((pnls > 0).sum())
        losses = int((pnls <= 0).sum())
        wr = (wins / n) * 100.0 if n > 0 else 0.0

        tot_usd = float(usds.sum()) if n > 0 else 0.0
        gw = float(pnls[pnls > 0].sum()) if n > 0 else 0.0
        gl = float(abs(pnls[pnls <= 0].sum())) if n > 0 else 0.0
        pf = (gw / max(gl, 1e-4))

        cum = np.cumsum(usds) if n > 0 else np.array([0])
        peak = np.maximum.accumulate(cum)
        dd = peak - cum
        max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0

        max_streak = 0
        cur_streak = 0
        for p in pnls:
            if p <= 0:
                cur_streak += 1
                if cur_streak > max_streak:
                    max_streak = cur_streak
            else:
                cur_streak = 0

        # Desglose por contrato OOS
        c4_trades = [t for t in oos_seq if t["contract"] == "GC 04-26"]
        c6_trades = [t for t in oos_seq if t["contract"] == "GC 06-26"]
        c4_pnl = sum(t["pnl_usd"] for t in c4_trades)
        c6_pnl = sum(t["pnl_usd"] for t in c6_trades)

        be_str = f"{be_p:4.1f}" if be_p is not None else "None"
        print(f"{idx:<4} | {sl_m:<4.1f} | {tp_p:<4.1f} | {be_str:<5} | ${cand['is_pnl_usd']:+10.2f} | ${tot_usd:+11.2f} | {wr:6.1f}%  | {pf:5.2f} | ${max_dd:9.2f} | {max_streak:3d} pérdidas", flush=True)

        final_validation.append({
            "rank": idx,
            "sl_mult": sl_m,
            "tp_pts": tp_p,
            "be_trigger_pts": be_p,
            "in_sample": cand,
            "out_of_sample": {
                "trades": n,
                "win_rate": round(wr, 1),
                "net_usd": round(tot_usd, 2),
                "profit_factor": round(pf, 2),
                "max_drawdown_usd": round(max_dd, 2),
                "max_losing_streak": max_streak,
                "contract_breakdown": {
                    "GC_04-26_usd": round(c4_pnl, 2),
                    "GC_06-26_usd": round(c6_pnl, 2)
                }
            }
        })

    print("-" * 88 + "\n")

    # Guardar resultados
    out_file = REPO_ROOT / "docs" / "research" / "bigtrap_gc_10tick_optimization_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ticks_per_bar": 10,
            "entry_mode": "BarClose",
            "execution_mode": "Sequential Single-Position",
            "friction": {"commission_usd": 4.50, "slippage_ticks": 1},
            "top_in_sample": is_results[:15],
            "validation_oos": final_validation,
            "total_elapsed_sec": round(time.time() - t0, 1)
        }, f, indent=2)

    print(f"Resultados consolidados guardados en:\n  -> {out_file}")
    print(f"Tiempo total: {time.time() - t0:.1f} segundos.\n")


if __name__ == "__main__":
    run_10tick_optimization()
