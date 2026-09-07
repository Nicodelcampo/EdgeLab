#!/usr/bin/env python3
"""CLI Runner: BigTrapNQ Optimal.

Uso rápido:
    python tools/run_bigtrap_nq.py --contract "NQ 09-25"
    python tools/run_bigtrap_nq.py --contract "NQ 09-25" --date "2025-08-15"
    python tools/run_bigtrap_nq.py --profile scalping
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import load_canonical_parquet
from edgelab.bridge.bars import build_tick_bars, build_footprints, session_ids
from edgelab.bridge.indicators.bigtrap_nq_optimal import (
    BigTrapNQOptimalConfig, detect_nq_zones, NAME, VERSION
)


def format_side(kind: str) -> str:
    if kind == "trapped_buyers":
        return "\033[91m[COMPRADORES ATRAPADOS (RESISTENCIA)]\033[0m"
    return "\033[92m[VENDEDORES ATRAPADOS (SOPORTE)]\033[0m"


def format_state(state: str, end_reason: str | None) -> str:
    if state == "ACTIVE":
        return "\033[96mACTIVA (Sostenida)\033[0m"
    if end_reason in ("close_through", "close_through_gap"):
        return "\033[90mINVALIDADA (Close-Through)\033[0m"
    return f"{state} ({end_reason})"


def run_cli(
    contract: str = "NQ 09-25",
    data_dir: str = "E:/EdgeLab/data/nt8/NQ_parquet",
    filter_date: str | None = None,
    profile: str = "standard",
    max_display: int = 40
):
    pq_file = Path(data_dir) / f"{contract.replace(' ', '_')}_ticks.parquet"
    if not pq_file.exists():
        print(f"Error: archivo no encontrado en {pq_file}")
        sys.exit(1)

    print("=" * 90)
    print(f" BigTrapNQ Optimal v{VERSION} — Detector de Absorción y Trampas Institucionales")
    print(f" Contrato: {contract} | Perfil: {profile.upper()}")
    print("=" * 90)

    # Configuración según perfil
    if profile.lower() == "scalping":
        cfg = BigTrapNQOptimalConfig(
            min_trap_volume=50.0,
            finished_auction_tol=1.0,
            anti_overshoot_buffer_ticks=2
        )
    else:  # standard / swing institucional
        cfg = BigTrapNQOptimalConfig(
            min_trap_volume=60.0,
            finished_auction_tol=1.0,
            anti_overshoot_buffer_ticks=2
        )

    t0 = time.time()
    ticks = load_canonical_parquet(pq_file, contract=contract)
    print(f"Ticks cargados: {len(ticks):,} ({time.time() - t0:.2f}s)")

    print(f"Construyendo barras de {cfg.ticks_per_bar} ticks y Footprints...")
    tb0 = time.time()
    bars = build_tick_bars(ticks, ticks_per_bar=cfg.ticks_per_bar, reiniciar_por_sesion=True)
    fps = build_footprints(ticks, bars)
    print(f"Barras generadas: {len(bars):,} ({time.time() - tb0:.2f}s)")

    print("Detectando zonas institucionales...")
    t_det0 = time.time()
    res = detect_nq_zones(ticks, bars, fps, config=cfg, chart_tz="America/Chicago")
    zones = res["zones"]
    print(f"Zonas detectadas: {len(zones):,} ({time.time() - t_det0:.2f}s)\n")

    if not zones:
        print("No se encontraron zonas con los parámetros especificados.")
        return

    # Convertir timestamps a fechas Chicago
    df_zones = pd.DataFrame(zones)
    df_zones["dt_ct"] = pd.to_datetime(df_zones["created_ms"], unit="ms", utc=True).dt.tz_convert("America/Chicago")
    df_zones["date_str"] = df_zones["dt_ct"].dt.strftime("%Y-%m-%d")
    df_zones["time_str"] = df_zones["dt_ct"].dt.strftime("%H:%M:%S")

    if filter_date:
        df_zones = df_zones[df_zones["date_str"] == filter_date]
        print(f"Filtrando por fecha {filter_date}: {len(df_zones)} zonas encontradas.\n")

    print(f"{'Hora (CT)':<10} | {'Régimen':<11} | {'Tipo de Trampa':<38} | {'Nivel [Top - Bottom]':<22} | {'Vol':<6} | {'Toques':<6} | {'Estado'}")
    print("-" * 115)

    display_df = df_zones.tail(max_display) if len(df_zones) > max_display else df_zones
    for _, z in display_df.iterrows():
        t_str = f"{z['time_str']}"
        reg = f"{z['regime']}"
        tipo = format_side(z['kind'])
        px_range = f"{z['top']:8.2f} - {z['bottom']:8.2f}"
        vol = f"{z['vol']:5.0f}c"
        touches = f"{z['touches']:4d}"
        st = format_state(z['state'], z['end_reason'])
        print(f"{t_str:<10} | {reg:<11} | {tipo:<47} | {px_range:<22} | {vol:<6} | {touches:<6} | {st}")

    if len(df_zones) > max_display:
        print(f"\n... (Mostrando las últimas {max_display} de {len(df_zones)} zonas totales)")

    # Estadísticas resumen
    n_bull = sum(1 for _, z in df_zones.iterrows() if z['kind'] == 'trapped_buyers')
    n_bear = sum(1 for _, z in df_zones.iterrows() if z['kind'] == 'trapped_sellers')
    ratio = n_bull / max(1, n_bear)
    avg_vol = df_zones["vol"].mean()
    rth_zones = sum(1 for _, z in df_zones.iterrows() if z['regime'] in ("RTH_OPEN", "RTH_CORE", "RTH_CLOSE"))

    print("\n" + "=" * 90)
    print(" RESUMEN ESTRUCTURAL:")
    print(f"  • Total Zonas: {len(df_zones)} (RTH: {rth_zones}, Globex: {len(df_zones) - rth_zones})")
    print(f"  • Simetría: {n_bull} Compradores Atrapados / {n_bear} Vendedores Atrapados (Ratio: {ratio:.2f})")
    print(f"  • Volumen Promedio por Trampa: {avg_vol:.1f} contratos")
    print("=" * 90)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ejecutar BigTrapNQ Optimal")
    parser.add_argument("--contract", default="NQ 09-25", help="Nombre del contrato parquet")
    parser.add_argument("--data-dir", default="E:/EdgeLab/data/nt8/NQ_parquet", help="Directorio de datos")
    parser.add_argument("--date", default=None, help="Filtrar por fecha específica (YYYY-MM-DD)")
    parser.add_argument("--profile", default="standard", choices=["standard", "scalping"], help="Perfil: standard (vol=60) o scalping (vol=50)")
    parser.add_argument("--max", type=int, default=30, help="Máximo de zonas a mostrar en pantalla")
    args = parser.parse_args()

    run_cli(contract=args.contract, data_dir=args.data_dir, filter_date=args.date, profile=args.profile, max_display=args.max)
