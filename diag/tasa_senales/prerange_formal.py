# -*- coding: utf-8 -*-
"""Formal statistical analysis engine for YM-PRERANGE (08:12-09:12 / 09:12-10:12) sweep phenomenon.

Computes:
1. Empirical Double Sweep rate vs Brownian Reflection Null (H-SWEEP-1a).
2. Tradable Fade Strategy vs Gambler's Ruin Null across Stop levels (H-SWEEP-1b).
3. Maximum Adverse Excursion (MAE) survival and optimal stop placement.
4. Day-of-Week and Volatility Compression vs Expansion Stratification.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import numpy as np
import pandas as pd


def norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def run_prerange_analysis(csv_path: str | Path, point_value_usd: float = 5.0, cost_points: float = 3.0) -> dict:
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)
    
    # Filter valid sessions
    df = df[df["range_pts"] > 0].copy()
    n_total = len(df)
    if n_total == 0:
        raise ValueError("No valid sessions found in CSV")

    df["session_date"] = pd.to_datetime(df["session_date"])
    df["day_of_week"] = df["session_date"].dt.day_name()
    
    # 1. Base Rates
    both_swept = df[df["second_sweep_occurred"] == True]
    n_both = len(both_swept)
    p_both = n_both / n_total
    
    # Wilson Score 95% CI
    margin = 1.96 * np.sqrt(p_both * (1.0 - p_both) / n_total)
    ci_low = max(0.0, p_both - margin)
    ci_high = min(1.0, p_both + margin)
    
    # Brownian Reflection Null baseline:
    # Range duration T = 60 min, remaining session ~ 408 min
    # sigma_hat = mean_range / (1.596 * sqrt(60))
    mean_range = float(df["range_pts"].mean())
    median_range = float(df["range_pts"].median())
    sigma_hat = mean_range / (1.596 * math.sqrt(60))
    
    # Post-open volatility multiplier typically 1.5x - 2.0x
    z_brownian = -mean_range / (sigma_hat * 1.5 * math.sqrt(408))
    p_null_brownian = 2.0 * norm_cdf(z_brownian)
    
    # Z-test vs Brownian null
    se_null = math.sqrt(p_null_brownian * (1.0 - p_null_brownian) / n_total)
    z_stat = (p_both - p_null_brownian) / se_null if se_null > 0 else 0.0
    p_val_brownian = 1.0 - norm_cdf(z_stat)
    
    # 2. Tradable Strategy Simulation (Fade the 1st Sweep)
    stops = [15, 25, 35, 50, 75, 100, 125, 150, 200]
    strategy_results = []
    
    for s in stops:
        # A trade is a WIN if second_sweep == True AND max_ext_first_pts <= s
        wins = df[(df["second_sweep_occurred"] == True) & (df["max_ext_first_pts"] <= s)]
        losses = df[~((df["second_sweep_occurred"] == True) & (df["max_ext_first_pts"] <= s))]
        
        n_wins = len(wins)
        win_rate = n_wins / n_total
        
        # Gambler's ruin theoretical baseline: s / (R + s)
        p_ruin_null = s / (mean_range + s)
        excess_winrate = win_rate - p_ruin_null
        
        # Financial Expectancy per trade in USD (Target = range_pts - cost, Loss = s + cost)
        gain_pts = wins["range_pts"].sum() - (n_wins * cost_points)
        loss_pts = len(losses) * (s + cost_points)
        net_pts = gain_pts - loss_pts
        ev_pts = net_pts / n_total
        ev_usd = ev_pts * point_value_usd
        
        # Profit Factor
        gross_profit = (wins["range_pts"] - cost_points).sum() * point_value_usd
        gross_loss = (len(losses) * (s + cost_points)) * point_value_usd
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.nan
        
        strategy_results.append({
            "stop_pts": s,
            "stop_usd": s * point_value_usd,
            "win_rate": win_rate,
            "null_win_rate": p_ruin_null,
            "edge_delta": excess_winrate,
            "profit_factor": profit_factor,
            "ev_pts_per_trade": ev_pts,
            "ev_usd_per_trade": ev_usd,
            "net_total_usd": net_pts * point_value_usd,
        })
        
    df_strat = pd.DataFrame(strategy_results)
    
    # 3. Stratification by Range Regime (Compressed vs Expanded)
    df["range_regime"] = np.where(df["range_pts"] <= median_range, "Comprimido (<= Mediana)", "Expandido (> Mediana)")
    regime_breakdown = df.groupby("range_regime").agg(
        n=("second_sweep_occurred", "count"),
        double_sweep_rate=("second_sweep_occurred", "mean"),
        mean_range=("range_pts", "mean"),
        mean_mae=("max_ext_first_pts", "mean"),
        median_mae=("max_ext_first_pts", "median"),
    ).reset_index()
    
    # 4. Stratification by Day of Week
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    day_breakdown = df.groupby("day_of_week").agg(
        n=("second_sweep_occurred", "count"),
        double_sweep_rate=("second_sweep_occurred", "mean"),
        mean_range=("range_pts", "mean"),
    ).reindex(day_order).reset_index()
    
    # 5. First Sweep Direction Breakdown
    side_breakdown = df.groupby("first_sweep_side").agg(
        n=("second_sweep_occurred", "count"),
        double_sweep_rate=("second_sweep_occurred", "mean"),
        mean_range=("range_pts", "mean"),
        mean_mae=("max_ext_first_pts", "mean"),
    ).reset_index()
    
    return {
        "n_sessions": n_total,
        "date_min": str(df["session_date"].min().date()),
        "date_max": str(df["session_date"].max().date()),
        "p_both_swept": p_both,
        "ci95": (ci_low, ci_high),
        "p_null_brownian": p_null_brownian,
        "z_stat": z_stat,
        "p_val_brownian": p_val_brownian,
        "mean_range": mean_range,
        "median_range": median_range,
        "strategy_table": df_strat,
        "regime_table": regime_breakdown,
        "day_table": day_breakdown,
        "side_table": side_breakdown,
        "raw_df": df
    }


def print_report(res: dict):
    print("=" * 80)
    print("INFORME ESTADÍSTICO FORMAL — FAMILIA YM-PRERANGE")
    print(f"Muestra: {res['n_sessions']} sesiones | Período: {res['date_min']} a {res['date_max']}")
    print("=" * 80)
    
    print(f"\n1. TASA BASE GLOBAL:")
    print(f"  * Tasa Observada de Doble Barrido: {res['p_both_swept']*100:.2f}%")
    print(f"  * Intervalo de Confianza 95%:      [{res['ci95'][0]*100:.2f}%, {res['ci95'][1]*100:.2f}%]")
    print(f"  * Nulo Browniano Teórico:          {res['p_null_brownian']*100:.2f}%")
    print(f"  * Exceso vs Azar Difusivo:         +{(res['p_both_swept'] - res['p_null_brownian'])*100:.2f}%")
    print(f"  * Z-Score / p-valor:               Z = {res['z_stat']:.2f} (p = {res['p_val_brownian']:.4e})")
    
    print(f"\n2. SIMULACIÓN DE LA ESTRATEGIA OPERABLE (FADE TRAS 1er BARRIDO):")
    print(f"{'Stop (pts)':<10} {'Stop ($)':<10} {'WinRate':<10} {'Nulo Ruina':<12} {'Edge Delta':<12} {'ProfitFact':<12} {'EV/Trade ($)':<14} {'Total PnL ($)':<14}")
    print("-" * 94)
    for _, row in res["strategy_table"].iterrows():
        print(f"{row['stop_pts']:<10.0f} ${row['stop_usd']:<9.0f} {row['win_rate']*100:<9.1f}% {row['null_win_rate']*100:<11.1f}% +{row['edge_delta']*100:<11.1f}% {row['profit_factor']:<11.2f} ${row['ev_usd_per_trade']:<13.2f} ${row['net_total_usd']:<13.0f}")

    print(f"\n3. ESTRATIFICACIÓN POR RÉGIMEN DE RANGO (COMPRESIÓN vs EXPANSIÓN):")
    for _, row in res["regime_table"].iterrows():
        print(f"  * {row['range_regime']}: N={row['n']}, Tasa Doble Barrido={row['double_sweep_rate']*100:.1f}%, Rango Medio={row['mean_range']:.1f} pts, Mediana MAE={row['median_mae']:.1f} pts")

    print(f"\n4. ESTRATIFICACIÓN POR DÍA DE LA SEMANA:")
    for _, row in res["day_table"].iterrows():
        if pd.notna(row['n']):
            print(f"  * {row['day_of_week']:<10}: N={int(row['n'])}, Tasa Doble Barrido={row['double_sweep_rate']*100:.1f}%, Rango Medio={row['mean_range']:.1f} pts")

    print(f"\n5. ASIMETRÍA DIRECCIONAL DEL 1er BARRIDO:")
    for _, row in res["side_table"].iterrows():
        print(f"  * 1er Barrido {row['first_sweep_side']:<8}: N={row['n']}, Tasa Doble Barrido={row['double_sweep_rate']*100:.1f}%, MAE Medio={row['mean_mae']:.1f} pts")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=r"C:\EdgeLab\ym_prerange_events.csv")
    parser.add_argument("--point-value", type=float, default=5.0)
    parser.add_argument("--cost-pts", type=float, default=3.0)
    args = parser.parse_args()
    
    res = run_prerange_analysis(args.csv, point_value_usd=args.point_value, cost_points=args.cost_pts)
    print_report(res)
