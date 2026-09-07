#!/usr/bin/env python3
"""Reality Check y Test de Falsación para el Filtro EMA de Reversión en Oro (GC).

Audita:
1. Simulación Secuencial Realista (1 solo trade a la vez, AllowSimultaneousTrades=False).
2. Desglose Long vs Short (¿Depende del drift macro alcista del Oro?).
3. Drawdown Máximo Real y Racha Máxima de Pérdidas Consecutivas.
4. Comparativa: Sin Filtro vs Revert EMA 100 vs Revert EMA 200 en 25 Ticks.
"""
from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools"))

from optimize_bigtrap_gc_ema import (
    load_contract_trajectories, BigTrapGCOptimalConfig, evaluate_single_trade
)

data_path = Path("E:/EdgeLab/data/nt8/GC_parquet")
contracts = ["GC 12-25", "GC 02-26", "GC 04-26", "GC 06-26"]
config = BigTrapGCOptimalConfig(ticks_per_bar=25, min_trap_volume=40.0)

print("Cargando trayectorias de los 4 contratos...")
all_trajs = []
for c in contracts:
    f = data_path / f"{c.replace(' ', '_')}_ticks.parquet"
    trajs = load_contract_trajectories(f, c, config)
    all_trajs.extend(trajs)
print(f"Total trayectorias cargadas: {len(all_trajs)}")


def audit_filter(
    trajs: List[Dict[str, Any]],
    filter_name: str,
    sl_m: float,
    tp_p: float,
    be_p: Optional[float]
):
    # Filtrar trayectorias
    if filter_name == "SIN_FILTRO":
        sub = trajs
    elif filter_name == "REVERT_EMA_100":
        sub = [t for t in trajs if t["revert_pass"][100]]
    elif filter_name == "REVERT_EMA_200":
        sub = [t for t in trajs if t["revert_pass"][200]]
    elif filter_name == "TREND_EMA_200":
        sub = [t for t in trajs if t["trend_pass"][200]]
    else:
        sub = trajs

    # 1. Modo Concurrente
    conc_pnls = []
    conc_trades = []
    for tr in sub:
        pnl, reason, dur = evaluate_single_trade(tr, sl_m, tp_p, be_p)
        conc_pnls.append(pnl)
        conc_trades.append({**tr, "pnl_pts": pnl, "pnl_usd": pnl * 100.0, "reason": reason, "duration_ticks": dur})

    # 2. Modo Secuencial Realista (1 trade a la vez)
    # Ordenar cronológicamente
    sub_sorted = sorted(sub, key=lambda x: (x["contract"], x["created_bar"]))
    seq_trades = []
    last_exit_tick_global = -1
    last_contract = ""

    for tr in sub_sorted:
        c = tr["contract"]
        e_tk_idx = tr["entry_tick_idx"]
        if c != last_contract:
            last_exit_tick_global = -1
            last_contract = c

        if e_tk_idx <= last_exit_tick_global:
            continue  # Posición ocupada

        pnl, reason, dur = evaluate_single_trade(tr, sl_m, tp_p, be_p)
        exit_tk_idx = e_tk_idx + dur
        last_exit_tick_global = exit_tk_idx
        seq_trades.append({**tr, "pnl_pts": pnl, "pnl_usd": pnl * 100.0, "reason": reason, "duration_ticks": dur})

    def get_stats(trade_list: List[Dict[str, Any]], label: str):
        n = len(trade_list)
        if n == 0:
            return {"label": label, "trades": 0}
        pnls = np.array([t["pnl_pts"] for t in trade_list], dtype=np.float64)
        usds = np.array([t["pnl_usd"] for t in trade_list], dtype=np.float64)
        wins = int((pnls > 0).sum())
        losses = int((pnls <= 0).sum())
        wr = (wins / n) * 100.0
        tot_usd = float(usds.sum())
        win_usd = float(usds[usds > 0].sum())
        loss_usd = float(abs(usds[usds <= 0].sum()))
        pf = win_usd / max(loss_usd, 1e-4)

        # Drawdown y racha
        cum = np.cumsum(usds)
        peak = np.maximum.accumulate(cum)
        dd = peak - cum
        max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0

        max_loss_streak = 0
        cur_loss_streak = 0
        for p in pnls:
            if p <= 0:
                cur_loss_streak += 1
                if cur_loss_streak > max_loss_streak:
                    max_loss_streak = cur_loss_streak
            else:
                cur_loss_streak = 0

        # Long vs Short
        longs = [t for t in trade_list if t["side"] == "LONG"]
        shorts = [t for t in trade_list if t["side"] == "SHORT"]

        long_usd = sum(t["pnl_usd"] for t in longs)
        short_usd = sum(t["pnl_usd"] for t in shorts)
        long_wr = (sum(1 for t in longs if t["pnl_usd"] > 0) / max(len(longs), 1)) * 100.0
        short_wr = (sum(1 for t in shorts if t["pnl_usd"] > 0) / max(len(shorts), 1)) * 100.0

        # Split In-Sample vs Out-of-Sample
        is_t = [t for t in trade_list if t["contract"] in ["GC 12-25", "GC 02-26"]]
        oos_t = [t for t in trade_list if t["contract"] in ["GC 04-26", "GC 06-26"]]
        is_usd = sum(t["pnl_usd"] for t in is_t)
        oos_usd = sum(t["pnl_usd"] for t in oos_t)
        is_pf = sum(t["pnl_usd"] for t in is_t if t["pnl_usd"] > 0) / max(abs(sum(t["pnl_usd"] for t in is_t if t["pnl_usd"] <= 0)), 1e-4)
        oos_pf = sum(t["pnl_usd"] for t in oos_t if t["pnl_usd"] > 0) / max(abs(sum(t["pnl_usd"] for t in oos_t if t["pnl_usd"] <= 0)), 1e-4)

        return {
            "label": label,
            "trades": n,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wr, 1),
            "total_usd": round(tot_usd, 2),
            "profit_factor": round(pf, 2),
            "max_dd_usd": round(max_dd, 2),
            "max_loss_streak": max_loss_streak,
            "is_trades": len(is_t),
            "is_usd": round(is_usd, 2),
            "is_pf": round(is_pf, 2),
            "oos_trades": len(oos_t),
            "oos_usd": round(oos_usd, 2),
            "oos_pf": round(oos_pf, 2),
            "long_trades": len(longs),
            "long_usd": round(long_usd, 2),
            "long_wr": round(long_wr, 1),
            "short_trades": len(shorts),
            "short_usd": round(short_usd, 2),
            "short_wr": round(short_wr, 1)
        }

    return {
        "concurrent": get_stats(conc_trades, "CONCURRENT"),
        "sequential": get_stats(seq_trades, "SEQUENTIAL_1_TRADE")
    }


# Probar los 2 perfiles principales:
# 1. Asimétrica: TP 12.0 pt, SL 1.0x
# 2. Alto Win Rate: TP 4.0 pt, SL 1.5x
for prof_name, sl_m, tp_p, be_p in [
    ("Asimétrica (TP 12.0 pt / SL 1.0x)", 1.0, 12.0, None),
    ("Alto Win Rate (TP 4.0 pt / SL 1.5x)", 1.5, 4.0, None)
]:
    print("\n" + "=" * 90)
    print(f"AUDITORÍA REALISTA: {prof_name}")
    print("=" * 90)

    for f_name in ["SIN_FILTRO", "REVERT_EMA_100", "REVERT_EMA_200", "TREND_EMA_200"]:
        res = audit_filter(all_trajs, f_name, sl_m, tp_p, be_p)
        s = res["sequential"]
        c = res["concurrent"]
        print(f"\n--- Filtro: {f_name} ---")
        print(f"  [SECUENCIAL 1-TRADE] Trades: {s['trades']} | WR: {s['win_rate']}% | PF Global: {s['profit_factor']}")
        print(f"    In-Sample ({s['is_trades']} tr): ${s['is_usd']:+,.0f} (PF {s['is_pf']:.2f})")
        print(f"    Out-of-Sample ({s['oos_trades']} tr): ${s['oos_usd']:+,.0f} (PF {s['oos_pf']:.2f})")
        print(f"    LONGS ({s['long_trades']} tr, {s['long_wr']}% WR): ${s['long_usd']:+,.0f}")
        print(f"    SHORTS ({s['short_trades']} tr, {s['short_wr']}% WR): ${s['short_usd']:+,.0f}")
        print(f"    Max Drawdown: ${s['max_dd_usd']:,.0f} | Max Racha Pérdidas: {s['max_loss_streak']} consecutivas")
        print(f"  [CONCURRENTE COMPARATIVA] Trades: {c['trades']} | USD: ${c['total_usd']:+,.0f} | PF: {c['profit_factor']}")
