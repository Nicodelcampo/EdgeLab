#!/usr/bin/env python3
"""Barrido Estructural Target-Free para BigTrapNQ:
Evaluación del impacto de Finished Auction, Delta Exhaustion y POC en Mecha sobre NQ.

Objetivo:
Determinar cuantitativamente si los filtros de Auction Market Theory (Finished Auction,
Delta Exhaustion, POC en Mecha) depuran el ruido de sobreoperación y mejoran la simetría
y estabilidad estructural sobre barras de tick (tick:25 y tick:50).
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
from edgelab.bridge.bars import build_tick_bars, build_footprints, session_ids
from edgelab.bridge.indicators import bigtrap_nq
from edgelab.research.nq_microstructure import (
    CLOCK_RTH_OPEN, CLOCK_RTH_CORE, CLOCK_RTH_CLOSE, CLOCK_GLOBEX
)


def compute_structural_score(
    coverage_pct: float,
    rth_density: float,
    symmetry_ratio: float,
    median_width_pts: float,
    held_pct: float
) -> Tuple[float, Dict[str, float]]:
    """Calcula el score de idoneidad estructural extendido (0 a 100)."""
    # 1. Cobertura (0 a 25 pts, meta >= 80%)
    score_cov = 25.0 * min(coverage_pct / 80.0, 1.0)

    # 2. Densidad RTH (0 a 25 pts, meta 2.0 a 5.0 zonas/sesión)
    if 2.0 <= rth_density <= 5.0:
        score_dens = 25.0
    elif rth_density < 2.0:
        score_dens = 25.0 * max(0.0, rth_density / 2.0)
    else:  # > 5.0
        score_dens = 25.0 * max(0.0, 1.0 - (rth_density - 5.0) / 10.0)

    # 3. Simetría (0 a 20 pts, meta ratio 1.0, tolerancia 0.8 a 1.25)
    sym_dev = abs(symmetry_ratio - 1.0)
    score_sym = 20.0 * max(0.0, 1.0 - sym_dev / 0.35)

    # 4. Ancho mediano (0 a 15 pts, meta 0.75 a 2.5 pts en NQ)
    if 0.75 <= median_width_pts <= 2.5:
        score_width = 15.0
    elif median_width_pts < 0.75:
        score_width = 15.0 * max(0.0, median_width_pts / 0.75)
    else:
        score_width = 15.0 * max(0.0, 1.0 - (median_width_pts - 2.5) / 4.0)

    # 5. Respeto estructural (% zonas que no son atravesadas de inmediato, 0 a 15 pts)
    # meta >= 50% sostenidas
    score_held = 15.0 * min(held_pct / 50.0, 1.0)

    total_score = score_cov + score_dens + score_sym + score_width + score_held
    components = {
        "score_cov": round(score_cov, 1),
        "score_dens": round(score_dens, 1),
        "score_sym": round(score_sym, 1),
        "score_width": round(score_width, 1),
        "score_held": round(score_held, 1),
    }
    return round(total_score, 1), components


def run_structural_sweep(
    contract: str = "NQ 09-25",
    data_dir: str = "E:/EdgeLab/data/nt8/NQ_parquet",
    output_file: str = "docs/research/bigtrap_nq_structural_results.json"
):
    pq_path = Path(data_dir) / f"{contract.replace(' ', '_')}_ticks.parquet"
    if not pq_path.exists():
        print(f"ERROR: Archivo no existe: {pq_path}")
        sys.exit(1)

    print("=" * 80)
    print(f"EdgeLab — Barrido Estructural Auction Market para BigTrapNQ sobre {contract}")
    print("=" * 80)

    t0 = time.time()
    ticks = load_canonical_parquet(pq_path, contract=contract)
    print(f"Ticks cargados: {len(ticks):,} ({time.time() - t0:.2f}s)")

    ses_arr = session_ids(ticks.ts_ns)
    unique_sessions = np.unique(ses_arr)
    n_total_sessions = len(unique_sessions)
    print(f"Sesiones CME identificadas: {n_total_sessions}")

    # Evaluamos principalmente tick:25 y tick:50
    resolutions = [
        ("tick_25", 25),
        ("tick_50", 50)
    ]

    # Pre-construcción
    cached_bars: Dict[str, Any] = {}
    cached_fps: Dict[str, Any] = {}
    cached_ses: Dict[str, np.ndarray] = {}

    print("\nPre-construyendo barras tick y footprints...")
    for r_id, r_ticks in resolutions:
        tb0 = time.time()
        b_obj = build_tick_bars(ticks, ticks_per_bar=r_ticks, reiniciar_por_sesion=True)
        fp_obj = build_footprints(ticks, b_obj)
        s_obj = session_ids(b_obj.end_ns)

        cached_bars[r_id] = b_obj
        cached_fps[r_id] = fp_obj
        cached_ses[r_id] = s_obj
        print(f"  {r_id:<10}: {len(b_obj):,} barras ({time.time() - tb0:.2f}s)")

    # Definir configuraciones estructurales a contrastar
    structural_configs = [
        # 1. Baseline clásico 1t (ganador del sweep matricial anterior)
        {
            "name": "Clasico_1t_Vol50_Base",
            "tpr": 1, "vol": 50.0, "dwell": 0.0, "rvol": False,
            "fin_auc": False, "delta_exh": False, "poc_wick": False
        },
        # 2. Clásico 1t + Finished Auction estricto
        {
            "name": "Clasico_1t_FinAuc",
            "tpr": 1, "vol": 50.0, "dwell": 0.0, "rvol": False,
            "fin_auc": True, "fin_tol": 0.0, "delta_exh": False, "poc_wick": False
        },
        # 3. Clásico 1t + Delta Exhaustion
        {
            "name": "Clasico_1t_DeltaExh",
            "tpr": 1, "vol": 50.0, "dwell": 0.0, "rvol": False,
            "fin_auc": False, "delta_exh": True, "poc_wick": False
        },
        # 4. Clásico 1t + POC en Mecha
        {
            "name": "Clasico_1t_PocInWick",
            "tpr": 1, "vol": 50.0, "dwell": 0.0, "rvol": False,
            "fin_auc": False, "delta_exh": False, "poc_wick": True
        },
        # 5. Clásico 1t + Finished Auction + Delta Exhaustion
        {
            "name": "Clasico_1t_FinAuc_DeltaExh",
            "tpr": 1, "vol": 50.0, "dwell": 0.0, "rvol": False,
            "fin_auc": True, "fin_tol": 0.0, "delta_exh": True, "poc_wick": False
        },
        # 6. Cluster 2t + Dwell 100ms Base
        {
            "name": "Cluster2t_Dwell100_Base",
            "tpr": 2, "vol": 40.0, "dwell": 100.0, "rvol": True,
            "fin_auc": False, "delta_exh": False, "poc_wick": False
        },
        # 7. Cluster 2t + Dwell 100ms + Finished Auction
        {
            "name": "Cluster2t_Dwell100_FinAuc",
            "tpr": 2, "vol": 40.0, "dwell": 100.0, "rvol": True,
            "fin_auc": True, "fin_tol": 0.0, "delta_exh": False, "poc_wick": False
        },
        # 8. Cluster 2t + Dwell 100ms + Delta Exhaustion
        {
            "name": "Cluster2t_Dwell100_DeltaExh",
            "tpr": 2, "vol": 40.0, "dwell": 100.0, "rvol": True,
            "fin_auc": False, "delta_exh": True, "poc_wick": False
        },
        # 9. Cluster 2t + Dwell 100ms + Finished Auction + Delta Exhaustion
        {
            "name": "Cluster2t_Dwell100_FinAuc_DeltaExh",
            "tpr": 2, "vol": 40.0, "dwell": 100.0, "rvol": True,
            "fin_auc": True, "fin_tol": 0.0, "delta_exh": True, "poc_wick": False
        },
        # 10. Cluster 2t + Dwell 100ms + Triple Filtro (FinAuc + DeltaExh + PocInWick)
        {
            "name": "Cluster2t_Dwell100_TripleAuction",
            "tpr": 2, "vol": 40.0, "dwell": 100.0, "rvol": True,
            "fin_auc": True, "fin_tol": 0.0, "delta_exh": True, "poc_wick": True
        }
    ]

    total_runs = len(resolutions) * len(structural_configs)
    print(f"\nIniciando corridas: {len(resolutions)} resoluciones × {len(structural_configs)} configs = {total_runs} combinaciones...")

    results = []
    run_idx = 0
    t_start_sweep = time.time()

    for r_id, r_ticks in resolutions:
        bars = cached_bars[r_id]
        fps = cached_fps[r_id]
        b_ses = cached_ses[r_id]

        for scfg in structural_configs:
            run_idx += 1
            t_run0 = time.time()
            p = dict(
                ticks_per_row=scfg["tpr"],
                min_trap_volume=scfg["vol"],
                use_dwell_filter=(scfg["dwell"] > 0),
                min_dwell_ms=scfg["dwell"],
                max_tape_speed=150.0,
                use_rvol_filter=scfg["rvol"],
                min_rvol=1.2,
                anti_overshoot_buffer_ticks=2,
                require_finished_auction=scfg["fin_auc"],
                finished_auction_tol=scfg.get("fin_tol", 0.0),
                require_delta_exhaustion=scfg["delta_exh"],
                require_poc_in_wick=scfg["poc_wick"],
                invalidation_mode="CloseThrough"
            )

            res = bigtrap_nq.run(ticks, bars, fps, params=p, chart_tz="America/Chicago")
            zones = res["zones"]
            n_zones = len(zones)

            if n_zones > 0:
                created_bars = np.array([z["created_bar"] for z in zones], dtype=np.int64)
                zone_ses = b_ses[created_bars]
                unique_active_ses = np.unique(zone_ses)
                n_active_ses = len(unique_active_ses)
                coverage_pct = round(100.0 * n_active_ses / n_total_sessions, 1)

                rth_mask = np.array([
                    z.get("regime") in (CLOCK_RTH_OPEN, CLOCK_RTH_CORE, CLOCK_RTH_CLOSE)
                    for z in zones
                ])
                n_rth = int(rth_mask.sum())
                n_globex = n_zones - n_rth
                rth_density = round(n_rth / max(1, n_active_ses), 2)
                globex_density = round(n_globex / max(1, n_active_ses), 2)

                n_bull = sum(1 for z in zones if z.get("kind") == "trapped_buyers")
                n_bear = sum(1 for z in zones if z.get("kind") == "trapped_sellers")
                symmetry_ratio = round(n_bull / max(1, n_bear), 2)

                widths = [z["top"] - z["bottom"] for z in zones]
                med_width = round(float(np.median(widths)), 2)

                # Respeto estructural: % que no terminaron con close_through rápido
                held_count = sum(1 for z in zones if z.get("state") == "ACTIVE" or z.get("end_reason") == "session_close")
                held_pct = round(100.0 * held_count / n_zones, 1)
            else:
                coverage_pct = 0.0
                rth_density = 0.0
                globex_density = 0.0
                symmetry_ratio = 1.0
                med_width = 0.0
                held_pct = 0.0
                n_rth = 0
                n_globex = 0
                n_bull = 0
                n_bear = 0

            score, comps = compute_structural_score(
                coverage_pct, rth_density, symmetry_ratio, med_width, held_pct
            )
            elapsed = time.time() - t_run0

            rec = {
                "resolution": r_id,
                "config_name": scfg["name"],
                "structural_score": score,
                "score_components": comps,
                "total_zones": n_zones,
                "coverage_pct": coverage_pct,
                "rth_zones": n_rth,
                "globex_zones": n_globex,
                "rth_density": rth_density,
                "globex_density": globex_density,
                "bull_zones": n_bull,
                "bear_zones": n_bear,
                "symmetry_ratio": symmetry_ratio,
                "median_width_pts": med_width,
                "held_pct": held_pct,
                "params": p,
                "elapsed_sec": round(elapsed, 2)
            }
            results.append(rec)
            print(f"[{run_idx:02d}/{total_runs:02d}] {r_id:<8} | {scfg['name']:<32} | Score: {score:5.1f} | Z/Ses: {rth_density:4.2f} | Cov: {coverage_pct:4.1f}% | Sym: {symmetry_ratio:4.2f} | Held: {held_pct:4.1f}% ({elapsed:.1f}s)")

    # Ordenar por score descendente
    results.sort(key=lambda x: x["structural_score"], reverse=True)

    out_p = REPO_ROOT / output_file
    out_p.parent.mkdir(parents=True, exist_ok=True)
    summary_data = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "contract": contract,
        "total_cme_sessions": n_total_sessions,
        "total_ticks": len(ticks),
        "results": results
    }
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print("\n" + "=" * 80)
    print(f"BARRIDO ESTRUCTURAL COMPLETADO en {time.time() - t_start_sweep:.1f}s")
    print(f"Resultados guardados en: {out_p}")
    print("=" * 80)

    print("\nTOP 5 CONFIGURACIONES ESTRUCTURALES:")
    print(f"{'Rank':<4} | {'Resolución':<8} | {'Config':<32} | {'Score':<5} | {'Z/Ses':<5} | {'Cov%':<5} | {'Sym':<5} | {'Width':<5} | {'Held%':<5}")
    print("-" * 88)
    for rank, r in enumerate(results[:5], 1):
        print(f"{rank:<4} | {r['resolution']:<8} | {r['config_name']:<32} | {r['structural_score']:5.1f} | {r['rth_density']:5.2f} | {r['coverage_pct']:5.1f} | {r['symmetry_ratio']:5.2f} | {r['median_width_pts']:5.2f} | {r['held_pct']:5.1f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sweep Estructural BigTrapNQ")
    parser.add_argument("--contract", default="NQ 09-25", help="Contrato a analizar")
    parser.add_argument("--data-dir", default="E:/EdgeLab/data/nt8/NQ_parquet", help="Directorio de parquets")
    parser.add_argument("--out", default="docs/research/bigtrap_nq_structural_results.json", help="Ruta salida")
    args = parser.parse_args()

    run_structural_sweep(contract=args.contract, data_dir=args.data_dir, output_file=args.out)
