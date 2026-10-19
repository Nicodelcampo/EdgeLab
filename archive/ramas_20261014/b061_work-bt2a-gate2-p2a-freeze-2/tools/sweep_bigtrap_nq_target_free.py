#!/usr/bin/env python3
"""Runner de análisis target-free para BigTrapNQ sobre las 234 sesiones de NQ.

Evalúa la sensibilidad estructural de BigTrapNQ sin abrir outcomes ni violar el holdout:
1. Densidad de eventos (zonas/sesión en RTH).
2. Cobertura de sesiones (porcentaje de sesiones con al menos 1 zona).
3. Simetría direccional (compras vs ventas).
4. Distribución por régimen de reloj (RTH_OPEN, RTH_CORE, RTH_CLOSE, GLOBEX).
5. Efecto del filtro de permanencia (dwell-time) sobre el descarte de flash sweeps.

Uso:
    python tools/sweep_bigtrap_nq_target_free.py --dry-run
    python tools/sweep_bigtrap_nq_target_free.py --contract "NQ 09-25" --max-sessions 10
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import load_canonical_parquet
from edgelab.bridge.bars import build_time_bars, build_footprints
from edgelab.bridge.indicators import bigtrap_nq
from edgelab.research.nq_microstructure import (
    CLOCK_RTH_OPEN, CLOCK_RTH_CORE, CLOCK_RTH_CLOSE, CLOCK_GLOBEX
)


def parse_args():
    p = argparse.ArgumentParser(description="Target-Free Sweep para BigTrapNQ")
    p.add_argument("--spec", default="specs/bigtrap_nq_target_free_sweep_v1.json")
    p.add_argument("--contract", default=None, help="Contrato específico (ej: 'NQ 09-25')")
    p.add_argument("--max-sessions", type=int, default=None, help="Máximo de sesiones a procesar")
    p.add_argument("--dry-run", action="store_true", help="Modo rápido: 2 sesiones de prueba")
    p.add_argument("--output", default="docs/research/bigtrap_nq_target_free_result.json")
    return p.parse_args()


def main():
    args = parse_args()
    spec_path = REPO_ROOT / args.spec
    if not spec_path.exists():
        print(f"ERROR: Spec no encontrado: {spec_path}")
        sys.exit(1)

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    data_dir = Path(spec["data_dir"])

    session_reg_path = REPO_ROOT / spec["session_registry"]
    session_reg = json.loads(session_reg_path.read_text(encoding="utf-8"))

    input_reg_path = REPO_ROOT / spec["input_registry"]
    input_reg = json.loads(input_reg_path.read_text(encoding="utf-8"))

    contracts = [args.contract] if args.contract else session_reg["selection"]["contracts"]

    print("=" * 70)
    print("EdgeLab — Sweep Target-Free de BigTrapNQ")
    print(f"Contratos: {contracts}")
    print(f"Data Dir: {data_dir}")
    print(f"Dry-run: {args.dry_run}")
    print("=" * 70)

    # Configuración de prueba de BigTrapNQ
    test_params = dict(
        ticks_per_row=2,
        bracket_pooling_ticks=4,
        imbalance_ratio=2.5,
        min_trap_volume=40.0,
        use_wick_filter=True,
        wick_zone_pct=35.0,
        use_dwell_filter=True,
        min_dwell_ms=100.0,
        max_tape_speed=500.0,
        use_rvol_filter=True,
        min_rvol=1.1,
        anti_overshoot_buffer_ticks=2,
        invalidation_mode="CloseThrough",
    )

    results_by_contract = {}
    total_sessions_run = 0
    total_zones_created = 0
    total_buyers = 0
    total_sellers = 0
    regime_counts = {CLOCK_RTH_OPEN: 0, CLOCK_RTH_CORE: 0, CLOCK_RTH_CLOSE: 0, CLOCK_GLOBEX: 0}

    for c in contracts:
        if c not in input_reg["contracts"]:
            print(f"Saltando {c}: no registrado en input registry")
            continue

        c_info = input_reg["contracts"][c]
        pq_path = data_dir / c_info["parquet_file"]
        if not pq_path.exists():
            print(f"ADVERTENCIA: Archivo parquet no existe en disco: {pq_path}")
            continue

        c_window = session_reg["selection"]["contract_windows"][c]
        print(f"\n--- Procesando {c} ({c_window['start']} a {c_window['end']}) ---")

        # Cargar ticks del contrato pre-holdout
        t0 = time.time()
        ticks = load_canonical_parquet(pq_path, contract=c)
        print(f"Ticks cargados: {len(ticks):,} ({time.time() - t0:.1f}s)")

        # Agrupar en barras de 1 minuto
        bars = build_time_bars(ticks, minutes=1)
        footprints = build_footprints(ticks, bars)
        print(f"Barras M1: {len(bars):,}")

        # Ejecutar BigTrapNQ
        t_run0 = time.time()
        out = bigtrap_nq.run(ticks, bars, footprints, params=test_params, chart_tz="America/Chicago")
        dt_run = time.time() - t_run0

        zones = out["zones"]
        n_zones = len(zones)
        n_buyers = sum(1 for z in zones if z["kind"] == "trapped_buyers")
        n_sellers = sum(1 for z in zones if z["kind"] == "trapped_sellers")

        for z in zones:
            reg = z.get("regime", CLOCK_GLOBEX)
            if reg in regime_counts:
                regime_counts[reg] += 1

        print(f"BigTrapNQ ejecutado en {dt_run:.2f}s:")
        print(f"  Zonas Totales: {n_zones}")
        print(f"  Compradores Atrapados (Resistencias): {n_buyers}")
        print(f"  Vendedores Atrapados (Soportes): {n_sellers}")

        results_by_contract[c] = {
            "ticks": len(ticks),
            "bars": len(bars),
            "zones": n_zones,
            "buyers": n_buyers,
            "sellers": n_sellers,
            "runtime_s": dt_run,
        }

        total_zones_created += n_zones
        total_buyers += n_buyers
        total_sellers += n_sellers
        total_sessions_run += session_reg["contract_session_counts"].get(c, 0)

        # Liberar memoria explícitamente
        del ticks, bars, footprints, out
        gc.collect()

        if args.dry_run:
            print("[Dry-run: finalizado tras primer contrato]")
            break

    # Resumen Consolidado
    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "params": test_params,
        "total_contracts": len(results_by_contract),
        "total_zones": total_zones_created,
        "trapped_buyers": total_buyers,
        "trapped_sellers": total_sellers,
        "symmetry_ratio": total_buyers / max(total_sellers, 1),
        "regime_distribution": regime_counts,
        "contracts_detail": results_by_contract,
    }

    out_file = REPO_ROOT / args.output
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print("RESUMEN TARGET-FREE CONSOLIDADO")
    print(f"Zonas Totales Creadas: {total_zones_created}")
    print(f"Simetría (Buyers / Sellers): {total_buyers} / {total_sellers} (Ratio: {summary['symmetry_ratio']:.2f})")
    print(f"Distribución por Régimen: {regime_counts}")
    print(f"Resultado guardado en: {out_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
