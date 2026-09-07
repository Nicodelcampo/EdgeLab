#!/usr/bin/env python3
"""Auditoría Forense y Protocolo de Falsación Causal para BigTrapGC (Oro).

Preguntas Críticas de Falsación:
1. ¿El resultado proviene del edge de absorción o es un artefacto de la tendencia alcista macro del Oro?
   - Desglose estricto: Longs vs Shorts.
   - Comparación contra Baseline Aleatorio (Random Entry Benchmark) en la misma ventana.
2. ¿Qué pasa cuando se ejecuta de forma realista con 1 sola posición a la vez (Single Trade, AllowSimultaneousTrades=False)?
   - En simulación concurrente, un rally alcista puede multiplicar artificialmente el PnL abriendo múltiples posiciones simultáneas.
3. ¿Cuántos trades salieron por TP vs SL vs CLOSE (Fin de sesión CME)?
   - Si muchos trades quedan truncados al cierre de la sesión, ¿genera un sesgo de mark-to-market?
4. ¿Cuál es el riesgo de ruina real?
   - Racha máxima de pérdidas consecutivas (Max Losing Streak).
   - Drawdown máximo real en USD.
"""
from __future__ import annotations

import json
import math
import sys
import time
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
SLIPPAGE_TICKS = 1      # 1 tick adverso en SL (0.10 pt = $10 USD)
USD_PER_PT = 100.0


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


def evaluate_trade_causal(
    entry_tk: int,
    side: str,
    risk_base_tk: int,
    future_ticks: np.ndarray,
    sl_mult: float,
    tp_pts: float,
    be_trigger_pts: Optional[float] = None,
    tick_size: float = 0.10
) -> Tuple[float, str, int]:
    sl_dist_tk = max(1, int(round(risk_base_tk * sl_mult)))
    tp_dist_tk = max(2, int(round(tp_pts / tick_size)))
    be_trig_tk = int(round(be_trigger_pts / tick_size)) if be_trigger_pts is not None else None

    if side == "LONG":
        current_sl_tk = entry_tk - sl_dist_tk
        tp_target_tk = entry_tk + tp_dist_tk
        be_thresh_tk = entry_tk + be_trig_tk if be_trig_tk is not None else 999999999
        be_lock_tk = entry_tk + 1

        for i, p in enumerate(future_ticks):
            if be_trig_tk is not None and p >= be_thresh_tk:
                current_sl_tk = max(current_sl_tk, be_lock_tk)

            if p <= current_sl_tk:
                loss_tk = entry_tk - current_sl_tk
                loss_pts = loss_tk * tick_size + (SLIPPAGE_TICKS * tick_size) + COMMISSION_PTS
                return -loss_pts, "SL", i + 1

            if p >= tp_target_tk:
                pnl_pts = tp_pts - COMMISSION_PTS
                return pnl_pts, "TP", i + 1

        exit_p = future_ticks[-1]
        pnl_pts = (exit_p - entry_tk) * tick_size - COMMISSION_PTS
        return pnl_pts, "CLOSE", len(future_ticks)

    else:  # SHORT
        current_sl_tk = entry_tk + sl_dist_tk
        tp_target_tk = entry_tk - tp_dist_tk
        be_thresh_tk = entry_tk - be_trig_tk if be_trig_tk is not None else -999999999
        be_lock_tk = entry_tk - 1

        for i, p in enumerate(future_ticks):
            if be_trig_tk is not None and p <= be_thresh_tk:
                current_sl_tk = min(current_sl_tk, be_lock_tk)

            if p >= current_sl_tk:
                loss_tk = current_sl_tk - entry_tk
                loss_pts = loss_tk * tick_size + (SLIPPAGE_TICKS * tick_size) + COMMISSION_PTS
                return -loss_pts, "SL", i + 1

            if p <= tp_target_tk:
                pnl_pts = tp_pts - COMMISSION_PTS
                return pnl_pts, "TP", i + 1

        exit_p = future_ticks[-1]
        pnl_pts = (entry_tk - exit_p) * tick_size - COMMISSION_PTS
        return pnl_pts, "CLOSE", len(future_ticks)


def audit_contract_causal(
    parquet_path: Path,
    contract_name: str,
    ticks_per_bar: int = 25,
    sl_mult: float = 1.0,
    tp_pts: float = 12.0,
    be_trigger_pts: Optional[float] = None
) -> Dict[str, Any]:
    print(f"\n--- AUDITANDO {contract_name} ({parquet_path.name}) ---", flush=True)
    session_ranges = find_session_boundaries_streaming(parquet_path)
    cfg = BigTrapGCOptimalConfig(ticks_per_bar=ticks_per_bar, min_trap_volume=40.0)
    cols = ["ts_utc_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "sequence"]

    all_concurrent_trades = []
    all_sequential_trades = []
    session_pnl_list = []

    # Métricas de drift macro del contrato
    first_price_tk = None
    last_price_tk = None

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

        if first_price_tk is None and len(ticks) > 0:
            first_price_tk = int(ticks.price_ticks[0])
        if len(ticks) > 0:
            last_price_tk = int(ticks.price_ticks[-1])

        bars = build_tick_bars(ticks, ticks_per_bar=cfg.ticks_per_bar, reiniciar_por_sesion=True)
        fps = build_footprints(ticks, bars)

        res = detect_gc_zones(ticks, bars, fps, config=cfg)
        zones = res["zones"]

        bar_changes = np.flatnonzero(np.diff(bars.tick_bar_idx)) + 1
        bar_starts = np.concatenate(([0], bar_changes))
        bar_ends = np.concatenate((bar_changes, [len(ticks)]))

        session_concurrent = []
        last_exit_tick_idx = -1

        for z in zones:
            b_created = z["created_bar"]
            is_bull = (z["kind"] == "trapped_buyers")
            side = "SHORT" if is_bull else "LONG"
            entry_tk = int(bars.close_t[b_created])
            entry_tick_idx = int(bar_ends[b_created]) - 1

            z_top_tk = int(round(z["top"] / 0.10))
            z_bot_tk = int(round(z["bottom"] / 0.10))

            if not is_bull:
                risk_base_tk = max(1, entry_tk - (z_bot_tk - 1))
            else:
                risk_base_tk = max(1, (z_top_tk + 1) - entry_tk)

            future_ticks = ticks.price_ticks[entry_tick_idx + 1 :]
            if len(future_ticks) < 5:
                continue

            pnl, reason, dur_ticks = evaluate_trade_causal(
                entry_tk, side, risk_base_tk, future_ticks, sl_mult, tp_pts, be_trigger_pts
            )

            trade_record = {
                "session": s_idx,
                "created_bar": b_created,
                "entry_tick_idx": entry_tick_idx,
                "exit_tick_idx": entry_tick_idx + dur_ticks,
                "side": side,
                "entry_px": entry_tk * 0.10,
                "risk_pts": risk_base_tk * 0.10 * sl_mult,
                "pnl_pts": pnl,
                "pnl_usd": pnl * USD_PER_PT,
                "reason": reason,
                "duration_ticks": dur_ticks
            }

            all_concurrent_trades.append(trade_record)
            session_concurrent.append(trade_record)

            # Control Estricto: Single Position Execution (1 trade a la vez)
            if entry_tick_idx > last_exit_tick_idx:
                all_sequential_trades.append(trade_record)
                last_exit_tick_idx = entry_tick_idx + dur_ticks

        ses_pnl = sum(t["pnl_usd"] for t in session_concurrent)
        session_pnl_list.append(ses_pnl)

        del ticks, bars, fps

    drift_pts = (last_price_tk - first_price_tk) * 0.10 if first_price_tk and last_price_tk else 0.0
    return {
        "contract": contract_name,
        "market_drift_pts": round(drift_pts, 2),
        "market_drift_usd": round(drift_pts * USD_PER_PT, 2),
        "concurrent_trades": all_concurrent_trades,
        "sequential_trades": all_sequential_trades,
        "session_pnls": session_pnl_list
    }


def analyze_trade_set(trades: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
    if not trades:
        return {"label": label, "count": 0}

    pnls = np.array([t["pnl_pts"] for t in trades], dtype=np.float64)
    usds = np.array([t["pnl_usd"] for t in trades], dtype=np.float64)
    sides = [t["side"] for t in trades]
    reasons = [t["reason"] for t in trades]

    n = len(trades)
    wins = int((pnls > 0).sum())
    losses = int((pnls <= 0).sum())
    wr = (wins / n) * 100.0

    tot_pnl_pts = float(pnls.sum())
    tot_pnl_usd = float(usds.sum())
    gross_win = float(pnls[pnls > 0].sum())
    gross_loss = float(abs(pnls[pnls <= 0].sum()))
    pf = (gross_win / max(gross_loss, 1e-4))

    # Long vs Short
    long_idx = [i for i, s in enumerate(sides) if s == "LONG"]
    short_idx = [i for i, s in enumerate(sides) if s == "SHORT"]

    long_pnl_usd = float(usds[long_idx].sum()) if long_idx else 0.0
    short_pnl_usd = float(usds[short_idx].sum()) if short_idx else 0.0
    long_wr = float((pnls[long_idx] > 0).mean() * 100.0) if long_idx else 0.0
    short_wr = float((pnls[short_idx] > 0).mean() * 100.0) if short_idx else 0.0

    # Razones de salida
    n_tp = reasons.count("TP")
    n_sl = reasons.count("SL")
    n_close = reasons.count("CLOSE")

    # Drawdown y rachas
    cum = np.cumsum(usds)
    peak = np.maximum.accumulate(cum)
    dd = peak - cum
    max_dd_usd = float(np.max(dd)) if len(dd) > 0 else 0.0

    # Racha de pérdidas consecutivas
    max_consec_losses = 0
    cur_consec_losses = 0
    for p in pnls:
        if p <= 0:
            cur_consec_losses += 1
            if cur_consec_losses > max_consec_losses:
                max_consec_losses = cur_consec_losses
        else:
            cur_consec_losses = 0

    return {
        "label": label,
        "trades": n,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wr, 1),
        "total_pnl_pts": round(tot_pnl_pts, 2),
        "total_pnl_usd": round(tot_pnl_usd, 2),
        "profit_factor": round(pf, 2),
        "max_drawdown_usd": round(max_dd_usd, 2),
        "max_losing_streak": max_consec_losses,
        "exits": {"TP": n_tp, "SL": n_sl, "CLOSE": n_close},
        "long_trades": len(long_idx),
        "long_pnl_usd": round(long_pnl_usd, 2),
        "long_win_rate": round(long_wr, 1),
        "short_trades": len(short_idx),
        "short_pnl_usd": round(short_pnl_usd, 2),
        "short_win_rate": round(short_wr, 1)
    }


def main():
    print("=" * 88)
    print("EdgeLab — Protocolo de Auditoría Forense y Falsación Causal para BigTrapGC")
    print("Objetivo: Poner a prueba de destrucción los resultados de TP=12.0, SL=1.0x en 25-Ticks")
    print("=" * 88)

    data_dir = Path("E:/EdgeLab/data/nt8/GC_parquet")
    contracts = ["GC 12-25", "GC 02-26", "GC 04-26", "GC 06-26"]

    all_contract_results = []
    for c in contracts:
        f = data_dir / f"{c.replace(' ', '_')}_ticks.parquet"
        res = audit_contract_causal(f, c, ticks_per_bar=25, sl_mult=1.0, tp_pts=12.0)
        all_contract_results.append(res)

    print("\n" + "=" * 88)
    print("RESUMEN FORENSE POR CONTRATO (DRIFT MACRO VS DESEMPEÑO)")
    print("=" * 88)
    print(f"{'Contrato':<10} | {'Drift Mercado':<15} | {'Trades Conc':<12} | {'PnL Conc (USD)':<15} | {'Trades Seq':<11} | {'PnL Seq (USD)':<14}")
    print("-" * 88)

    total_conc_all = []
    total_seq_all = []

    for cr in all_contract_results:
        c_name = cr["contract"]
        drift_str = f"{cr['market_drift_pts']:+7.1f} pt (${cr['market_drift_usd']:+8.0f})"
        c_conc = cr["concurrent_trades"]
        c_seq = cr["sequential_trades"]

        total_conc_all.extend(c_conc)
        total_seq_all.extend(c_seq)

        pnl_c = sum(t["pnl_usd"] for t in c_conc)
        pnl_s = sum(t["pnl_usd"] for t in c_seq)

        print(f"{c_name:<10} | {drift_str:<15} | {len(c_conc):<12} | ${pnl_c:+13.2f} | {len(c_seq):<11} | ${pnl_s:+12.2f}")

    print("-" * 88 + "\n")

    # Comparativa Concurrente vs Secuencial
    conc_stats = analyze_trade_set(total_conc_all, "CONCURRENTE (Múltiples posiciones simultáneas)")
    seq_stats = analyze_trade_set(total_seq_all, "SECUENCIAL REALISTA (1 sola posición activa a la vez)")

    print("=" * 88)
    print("TEST DE FALSACIÓN 1: SIMULACIÓN CONCURRENTE VS 1 SOLA POSICIÓN REALISTA")
    print("=" * 88)
    for s in [conc_stats, seq_stats]:
        print(f"Modo: {s['label']}")
        print(f"  Trades: {s['trades']} | Win%: {s['win_rate']}% (W: {s['wins']}, L: {s['losses']}) | PF: {s['profit_factor']}")
        print(f"  PnL Total: {s['total_pnl_pts']:+0.1f} pts (${s['total_pnl_usd']:+0.2f} USD)")
        print(f"  Max Drawdown: ${s['max_drawdown_usd']:.2f} USD | Max Racha de Pérdidas: {s['max_losing_streak']} consecutivas")
        print(f"  Salidas: TP={s['exits']['TP']}, SL={s['exits']['SL']}, Fin Sesión (CLOSE)={s['exits']['CLOSE']}")
        print(f"  LONGS:  {s['long_trades']:4d} trades | Win%: {s['long_win_rate']:5.1f}% | PnL: ${s['long_pnl_usd']:+10.2f}")
        print(f"  SHORTS: {s['short_trades']:4d} trades | Win%: {s['short_win_rate']:5.1f}% | PnL: ${s['short_pnl_usd']:+10.2f}\n")

    # Guardar en archivo JSON
    out_audit = REPO_ROOT / "docs" / "research" / "audit_gc_falsification_results.json"
    with open(out_audit, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.time(),
            "contracts": [cr["contract"] for cr in all_contract_results],
            "concurrent_stats": conc_stats,
            "sequential_stats": seq_stats
        }, f, indent=2)
    print(f"Auditoría forense guardada en:\n  -> {out_audit}")


if __name__ == "__main__":
    main()
