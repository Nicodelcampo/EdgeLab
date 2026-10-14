#!/usr/bin/env python3
"""Barrido Matricial Target-Free para BigTrapNQ: Resolución de Barra × Estructura del Indicador.

Evalúa simultáneamente:
1. Resoluciones de Barra:
   - tick:25 (rápida / scalping)
   - tick:50 (media / momentum)
   - tick:100 (estructural corta)
   - tick:250 (estructural media)
   - time:1 (benchmark de tiempo 1 min)
2. Geometría de Footprint:
   - ticks_per_row = 1 (0.25 pt)
   - ticks_per_row = 2 (0.50 pt)
   - ticks_per_row = 4 (1.00 pt)
3. Filtro de Persistencia (Dwell-Time):
   - min_dwell_ms = 0 ms (apagado / clásico)
   - min_dwell_ms = 100 ms
   - min_dwell_ms = 250 ms
4. Umbral de Volumen:
   - min_trap_volume = 30.0 vs 50.0

Calcula el Structural Fitness Score objetivo (0 a 100) basado en:
- Cobertura de sesiones (meta >= 80%).
- Densidad en RTH (meta 2.0 a 5.0 zonas/sesión).
- Simetría direccional (meta balance 45%-55%).
- Ancho mediano de zona (meta 1.0 a 3.0 pts en NQ).
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import load_canonical_parquet, TickSeries
from edgelab.bridge.bars import build_time_bars, build_tick_bars, build_footprints, session_ids
from edgelab.bridge.indicators import bigtrap_nq
from edgelab.research.nq_microstructure import (
    CLOCK_RTH_OPEN, CLOCK_RTH_CORE, CLOCK_RTH_CLOSE, CLOCK_GLOBEX
)


def compute_structural_score(
    coverage_pct: float,
    rth_density: float,
    symmetry_ratio: float,
    median_width_pts: float
) -> Tuple[float, Dict[str, float]]:
    """Calcula el score de idoneidad estructural (0 a 100)."""
    # 1. Cobertura (0 a 30 pts, meta >= 80%)
    score_cov = 30.0 * min(coverage_pct / 80.0, 1.0)

    # 2. Densidad RTH (0 a 30 pts, meta 2.0 a 5.0 zonas/sesión)
    if 2.0 <= rth_density <= 5.0:
        score_dens = 30.0
    elif rth_density < 2.0:
        score_dens = 30.0 * max(0.0, rth_density / 2.0)
    else:  # > 5.0
        score_dens = 30.0 * max(0.0, 1.0 - (rth_density - 5.0) / 10.0)

    # 3. Simetría (0 a 20 pts, meta ratio 1.0, tolerancia 0.8 a 1.25)
    sym_dev = abs(symmetry_ratio - 1.0)
    score_sym = 20.0 * max(0.0, 1.0 - sym_dev / 0.35)

    # 4. Ancho mediano (0 a 20 pts, meta 1.0 a 3.0 pts en NQ)
    if 1.0 <= median_width_pts <= 3.0:
        score_width = 20.0
    elif median_width_pts < 1.0:
        score_width = 20.0 * max(0.0, median_width_pts / 1.0)
    else:  # > 3.0
        score_width = 20.0 * max(0.0, 1.0 - (median_width_pts - 3.0) / 5.0)

    total_score = score_cov + score_dens + score_sym + score_width
    components = {
        "score_cov": round(score_cov, 1),
        "score_dens": round(score_dens, 1),
        "score_sym": round(score_sym, 1),
        "score_width": round(score_width, 1),
    }
    return round(total_score, 1), components


def run_matrix_sweep(contract: str = "NQ 09-25", data_dir: str = "E:/EdgeLab/data/nt8/NQ_parquet"):
    pq_path = Path(data_dir) / f"{contract.replace(' ', '_')}_ticks.parquet"
    if not pq_path.exists():
        print(f"ERROR: Archivo no existe: {pq_path}")
        sys.exit(1)

    print("=" * 78)
    print(f"EdgeLab — Barrido Matricial Target-Free sobre {contract}")
    print("=" * 78)

    t0 = time.time()
    ticks = load_canonical_parquet(pq_path, contract=contract)
    print(f"Ticks cargados: {len(ticks):,} ({time.time() - t0:.2f}s)")

    # Calcular sesiones CME totales en el archivo
    ses_arr = session_ids(ticks.ts_ns)
    unique_sessions = np.unique(ses_arr)
    n_total_sessions = len(unique_sessions)
    print(f"Sesiones CME identificadas: {n_total_sessions}")

    # Definir resoluciones de barra
    bar_specs = [
        ("tick_25", "tick", 25),
        ("tick_50", "tick", 50),
        ("tick_100", "tick", 100),
        ("tick_250", "tick", 250),
        ("time_1", "time", 1),
    ]

    # Pre-construir barras y footprints para cada resolución (1 sola vez cada una)
    cached_bars: Dict[str, Any] = {}
    cached_fps: Dict[str, Any] = {}
    cached_ses_by_bar: Dict[str, np.ndarray] = {}

    print("\nPre-construyendo barras y footprints para cada resolución...")
    for b_id, b_kind, b_param in bar_specs:
        tb0 = time.time()
        if b_kind == "tick":
            b_obj = build_tick_bars(ticks, ticks_per_bar=b_param, reiniciar_por_sesion=True)
        else:
            b_obj = build_time_bars(ticks, minutes=b_param)
        fp_obj = build_footprints(ticks, b_obj)
        b_ses = session_ids(b_obj.end_ns)

        cached_bars[b_id] = b_obj
        cached_fps[b_id] = fp_obj
        cached_ses_by_bar[b_id] = b_ses
        print(f"  {b_id:<10}: {len(b_obj):,} barras ({time.time() - tb0:.2f}s)")

    # Definir matriz de configuraciones de indicador
    indicator_configs = [
        # Clásico / Baseline (sin dwell, ticks_per_row=1)
        {"name": "Clasico_1t_NoDwell", "tpr": 1, "dwell": 0.0, "vol": 30.0, "rvol": False},
        {"name": "Clasico_1t_Vol50",   "tpr": 1, "dwell": 0.0, "vol": 50.0, "rvol": False},

        # Agrupación 2 ticks (0.50 pt) con Dwell-Time
        {"name": "Cluster2t_NoDwell",  "tpr": 2, "dwell": 0.0, "vol": 30.0, "rvol": False},
        {"name": "Cluster2t_Dwell100", "tpr": 2, "dwell": 100.0, "vol": 40.0, "rvol": True},
        {"name": "Cluster2t_Dwell250", "tpr": 2, "dwell": 250.0, "vol": 40.0, "rvol": True},

        # Agrupación 4 ticks (1.00 pt) con Dwell-Time
        {"name": "Cluster4t_Dwell100", "tpr": 4, "dwell": 100.0, "vol": 50.0, "rvol": True},
        {"name": "Cluster4t_Dwell250", "tpr": 4, "dwell": 250.0, "vol": 50.0, "rvol": True},
    ]

    total_runs = len(bar_specs) * len(indicator_configs)
    print(f"\nEjecutando matriz: {len(bar_specs)} resoluciones × {len(indicator_configs)} configs = {total_runs} corridas...")

    results = []
    run_idx = 0
    t_matrix0 = time.time()

    for b_id, _, _ in bar_specs:
        bars = cached_bars[b_id]
        fps = cached_fps[b_id]
        b_ses = cached_ses_by_bar[b_id]

        for icfg in indicator_configs:
            run_idx += 1
            p = dict(
                ticks_per_row=icfg["tpr"],
                bracket_pooling_ticks=4,
                imbalance_ratio=2.5,
                min_trap_volume=icfg["vol"],
                use_wick_filter=True,
                wick_zone_pct=35.0,
                use_dwell_filter=(icfg["dwell"] > 0),
                min_dwell_ms=icfg["dwell"],
                max_tape_speed=500.0,
                use_rvol_filter=icfg["rvol"],
                min_rvol=1.1,
                anti_overshoot_buffer_ticks=2,
                invalidation_mode="CloseThrough",
            )

            t_run0 = time.time()
            out = bigtrap_nq.run(ticks, bars, fps, params=p, chart_tz="America/Chicago")
            run_time = time.time() - t_run0

            zones = out["zones"]
            n_zones = len(zones)
            n_buyers = sum(1 for z in zones if z["kind"] == "trapped_buyers")
            n_sellers = sum(1 for z in zones if z["kind"] == "trapped_sellers")
            sym_ratio = n_buyers / max(n_sellers, 1)

            # Sesiones con zonas
            zone_sessions = set()
            rth_zone_count = 0
            widths = []
            for z in zones:
                b_idx = z["created_bar"]
                zone_sessions.add(b_ses[b_idx])
                widths.append(z["top"] - z["bottom"])
                if z.get("regime") in (CLOCK_RTH_OPEN, CLOCK_RTH_CORE, CLOCK_RTH_CLOSE):
                    rth_zone_count += 1

            cov_pct = (len(zone_sessions) / max(n_total_sessions, 1)) * 100.0
            rth_density = rth_zone_count / max(n_total_sessions, 1)
            med_width = float(np.median(widths)) if widths else 0.0

            score, comps = compute_structural_score(cov_pct, rth_density, sym_ratio, med_width)

            res_entry = {
                "bar_type": b_id,
                "config_name": icfg["name"],
                "ticks_per_row": icfg["tpr"],
                "min_dwell_ms": icfg["dwell"],
                "min_vol": icfg["vol"],
                "total_zones": n_zones,
                "rth_zones": rth_zone_count,
                "rth_density": round(rth_density, 2),
                "coverage_pct": round(cov_pct, 1),
                "symmetry_ratio": round(sym_ratio, 2),
                "median_width_pts": round(med_width, 2),
                "fitness_score": score,
                "score_components": comps,
                "run_time_s": round(run_time, 2),
            }
            results.append(res_entry)

    dt_total = time.time() - t_matrix0
    print(f"\nMatriz completada en {dt_total:.2f}s.")

    # Ordenar por Fitness Score descendente
    results.sort(key=lambda x: x["fitness_score"], reverse=True)

    # Guardar resultados
    out_path = REPO_ROOT / "docs" / "research" / "bigtrap_nq_matrix_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "contract": contract,
        "n_sessions": n_total_sessions,
        "total_combinations": total_runs,
        "results": results
    }, indent=2), encoding="utf-8")

    # Mostrar Tabla de Ranking en Terminal
    print("\n" + "=" * 105)
    print(f"RANKING DE IDONEIDAD ESTRUCTURAL (TOP COMBINACIONES NQ)")
    print("=" * 105)
    print(f"{'Rank':<5} | {'Bar Type':<10} | {'Configuracion':<20} | {'Score':<6} | {'Zonas/Ses':<10} | {'Cobertura':<10} | {'Simetria':<9} | {'Ancho Med (Pts)':<15}")
    print("-" * 105)
    for r_idx, r in enumerate(results[:15], 1):
        print(
            f"#{r_idx:<4} | {r['bar_type']:<10} | {r['config_name']:<20} | {r['fitness_score']:<6.1f} | "
            f"{r['rth_density']:<10.2f} | {r['coverage_pct']:<9.1f}% | {r['symmetry_ratio']:<9.2f} | {r['median_width_pts']:<15.2f}"
        )
    print("=" * 105)
    print(f"Detalle completo guardado en: {out_path}\n")


if __name__ == "__main__":
    run_matrix_sweep()
