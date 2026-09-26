# -*- coding: utf-8 -*-
"""Cross-Asset Comparative Analysis for Pre-Range Sweep Phenomenon (ES vs NQ vs YM)."""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np


def analyze_asset(name: str, csv_path: str, point_val: float) -> dict:
    df = pd.read_csv(csv_path)
    df = df[df["range_pts"] > 0].copy()
    df["session_date"] = pd.to_datetime(df["session_date"])
    df["day_of_week"] = df["session_date"].dt.day_name()
    
    n = len(df)
    both = df[df["second_sweep_occurred"] == True]
    p_both = len(both) / n if n > 0 else 0
    
    high_first = df[df["first_sweep_side"] == "HIGH"]
    p_high_first = len(high_first) / n if n > 0 else 0
    
    mean_range = df["range_pts"].mean()
    median_range = df["range_pts"].median()
    
    # Stratification by median range
    comp = df[df["range_pts"] <= median_range]
    p_comp = comp["second_sweep_occurred"].mean() if len(comp) > 0 else 0
    
    exp = df[df["range_pts"] > median_range]
    p_exp = exp["second_sweep_occurred"].mean() if len(exp) > 0 else 0
    
    # Days
    tues = df[df["day_of_week"] == "Tuesday"]
    p_tues = tues["second_sweep_occurred"].mean() if len(tues) > 0 else 0
    
    fri = df[df["day_of_week"] == "Friday"]
    p_fri = fri["second_sweep_occurred"].mean() if len(fri) > 0 else 0
    
    return {
        "asset": name,
        "n": n,
        "p_both": p_both,
        "mean_range_pts": mean_range,
        "median_range_pts": median_range,
        "mean_range_usd": mean_range * point_val,
        "p_comp": p_comp,
        "p_exp": p_exp,
        "p_tues": p_tues,
        "p_fri": p_fri,
        "df": df.set_index("session_date")
    }


def main():
    assets = [
        ("YM (Dow Jones)", r"C:\EdgeLab\ym_prerange_events.csv", 5.0),
        ("ES (S&P 500)", r"C:\EdgeLab\es_prerange_events.csv", 50.0),
        ("NQ (Nasdaq)", r"C:\EdgeLab\nq_prerange_events.csv", 20.0),
    ]
    
    results = [analyze_asset(name, path, pval) for name, path, pval in assets]
    
    print("=" * 85)
    print("ESTUDIO COMPARATIVO MULTIACTIVO — CROSS-ASSET (YM vs ES vs NQ)")
    print("=" * 85)
    
    print(f"{'Activo':<16} {'Sesiones':<10} {'Doble Sweep':<14} {'Rango Mediano':<16} {'Rango USD ($)':<14} {'Martes':<10} {'Viernes':<10}")
    print("-" * 85)
    for r in results:
        print(f"{r['asset']:<16} {r['n']:<10} {r['p_both']*100:<13.1f}% {r['median_range_pts']:<7.2f} pts    ${r['mean_range_usd']:<13.0f} {r['p_tues']*100:<9.1f}% {r['p_fri']*100:<9.1f}%")
        
    print("\n" + "=" * 85)
    print("FILTRO POR RÉGIMEN DE COMPRESIÓN:")
    for r in results:
        delta = (r['p_comp'] - r['p_exp']) * 100
        print(f"  * {r['asset']:<16}: Rango Comprimido={r['p_comp']*100:.1f}% vs Expandido={r['p_exp']*100:.1f}% (Delta = +{delta:.1f}%)")

    # Co-occurrence analysis on common dates
    df_ym = results[0]["df"]["second_sweep_occurred"].rename("YM")
    df_es = results[1]["df"]["second_sweep_occurred"].rename("ES")
    df_nq = results[2]["df"]["second_sweep_occurred"].rename("NQ")
    
    merged = pd.concat([df_ym, df_es, df_nq], axis=1, join="inner")
    n_common = len(merged)
    
    all_three = (merged["YM"] & merged["ES"] & merged["NQ"]).sum()
    none_three = (~merged["YM"] & ~merged["ES"] & ~merged["NQ"]).sum()
    at_least_two = ((merged.sum(axis=1)) >= 2).sum()
    
    print("\n" + "=" * 85)
    print(f"SINCRONIZACIÓN SISTÉMICA ENTRE ÍNDICES (Muestra común: {n_common} sesiones):")
    print(f"  * Los 3 índices hicieron Doble Barrido el mismo día:  {all_three} días ({all_three/n_common*100:.1f}%)")
    print(f"  * Al menos 2 índices hicieron Doble Barrido:          {at_least_two} días ({at_least_two/n_common*100:.1f}%)")
    print(f"  * Ninguno hizo Doble Barrido (Día Tendencial Global): {none_three} días ({none_three/n_common*100:.1f}%)")
    print("=" * 85)


if __name__ == "__main__":
    main()
