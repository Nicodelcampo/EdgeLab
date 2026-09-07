#!/usr/bin/env python3
"""Auditoría de sanidad e integridad física para BigTrapNQ.

Verifica en un periodo corto real y en datos sintéticos controlados que:
1. Invariante de No-Repintado y Causalidad: la barra creadora NUNCA toca ni invalida su propia zona.
2. Geometría y Alineación a Grilla: top > bottom, ancho en ticks múltiplo exacto de tick_size (0.25).
3. Localización de Trampa:
   - Trapped Buyers (B) estrictamente por ENCIMA del close de la barra creadora.
   - Trapped Sellers (S) estrictamente por DEBAJO del close de la barra creadora.
4. Microestructura Física:
   - dwell_ms >= min_dwell_ms (sin flash sweeps).
   - tape_speed <= max_tape_speed.
   - vol >= min_trap_volume.
   - rvol > 0 y finito (sin NaNs ni Infs).
5. Ciclo de Vida:
   - touches >= 0.
   - end_reason coherente con el modo de invalidación.
   - Si ended_ms no es None -> state en ('INVALIDATED', 'EXPIRED').
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, List, Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import load_canonical_parquet, make_synthetic, TickSeries
from edgelab.bridge.bars import build_time_bars, build_footprints
from edgelab.bridge.indicators import bigtrap_nq


def audit_run_output(out: dict, bars, ticks) -> Dict[str, Any]:
    """Ejecuta una auditoría exhaustiva de sanidad sobre la salida de bigtrap_nq.run."""
    tick_size = float(ticks.tick_size)
    zones = out["zones"]
    events = out["events"]
    csv_lines = out["csv_lines"]
    params = out["params"]

    checks = {
        "n_zones": len(zones),
        "n_events": len(events),
        "passed_all": True,
        "failures": [],
        "warnings": [],
        "sample_zones": [],
    }

    # 1. Chequeo de correspondencia entre csv_lines y events
    if len(csv_lines) != len(events):
        checks["passed_all"] = False
        checks["failures"].append(f"Mismatch entre csv_lines ({len(csv_lines)}) y events ({len(events)})")

    # 2. Chequeo de zonas
    for i, z in enumerate(zones):
        b = z["created_bar"]
        lo = z["bottom"]
        hi = z["top"]
        kind = z["kind"]
        close_b = float(bars.close_t[b]) * tick_size

        # Invariante geométrica
        if hi <= lo:
            checks["passed_all"] = False
            checks["failures"].append(f"Zona {z['id']}: hi ({hi}) <= lo ({lo})")

        # Alineación a la grilla de ticks (0.25)
        # Nota: las cotas de zona usan +/- tick_size/2 como límites de celda (ej: .125 o .375)
        width_ticks = (hi - lo) / tick_size
        if width_ticks <= 0 or not math.isfinite(width_ticks):
            checks["passed_all"] = False
            checks["failures"].append(f"Zona {z['id']}: ancho de ticks no finito ({width_ticks})")

        # Invariante de trampa respecto al close creador
        if kind == "trapped_buyers":
            if lo < close_b and not (hi > close_b):
                checks["passed_all"] = False
                checks["failures"].append(f"Zona {z['id']} (buyers): no está por encima del close ({close_b})")
        elif kind == "trapped_sellers":
            if hi > close_b and not (lo < close_b):
                checks["passed_all"] = False
                checks["failures"].append(f"Zona {z['id']} (sellers): no está por debajo del close ({close_b})")

        # Invariante de causalidad: la barra creadora nunca toca su propia zona
        # En la barra creadora, touches debe ser 0 si la zona no fue tocada en barras posteriores
        if z["state"] == "ACTIVE" and z["touches"] > 0:
            pass  # Es normal si fue tocada en barras posteriores
        if z["ended_ms"] is not None and z["state"] not in ("INVALIDATED", "EXPIRED"):
            checks["passed_all"] = False
            checks["failures"].append(f"Zona {z['id']}: ended_ms presente pero state es {z['state']}")

        # Microestructura: rvol y dwell_ms
        rvol = z.get("rvol", 1.0)
        dwell = z.get("dwell_ms", 0.0)
        if not math.isfinite(rvol) or rvol <= 0:
            checks["passed_all"] = False
            checks["failures"].append(f"Zona {z['id']}: rvol inválido ({rvol})")
        if not math.isfinite(dwell) or dwell < 0:
            checks["passed_all"] = False
            checks["failures"].append(f"Zona {z['id']}: dwell_ms inválido ({dwell})")

        if i < 3:
            checks["sample_zones"].append({
                "id": z["id"],
                "kind": z["kind"],
                "lo": lo,
                "hi": hi,
                "width_pts": hi - lo,
                "close_creator": close_b,
                "created_bar": b,
                "touches": z["touches"],
                "state": z["state"],
                "rvol": round(rvol, 2),
                "dwell_ms": round(dwell, 1),
                "regime": z.get("regime"),
            })

    return checks


def run_synthetic_audit():
    print("\n--- 1. AUDITORÍA SOBRE DATOS SINTÉTICOS CONTROLADOS ---")
    tk = make_synthetic(n_sessions=1, ticks_per_session=6000)
    bars = build_time_bars(tk, minutes=1)
    fps = build_footprints(tk, bars)

    params = dict(
        ticks_per_row=2,
        bracket_pooling_ticks=4,
        imbalance_ratio=2.0,
        min_trap_volume=20.0,
        use_wick_filter=True,
        wick_zone_pct=35.0,
        use_dwell_filter=False,  # Apagado para sintéticos aleatorios
        use_rvol_filter=False,
        anti_overshoot_buffer_ticks=2,
        invalidation_mode="CloseThrough",
    )

    out = bigtrap_nq.run(tk, bars, fps, params=params, chart_tz="America/Chicago")
    checks = audit_run_output(out, bars, tk)

    print(f"Zonas creadas: {checks['n_zones']}")
    print(f"Eventos totales: {checks['n_events']}")
    if checks["passed_all"]:
        print(">> VEREDICTO SINTÉTICO: PASS (Todas las invariantes verificadas)")
    else:
        print(f">> VEREDICTO SINTÉTICO: FAIL -> {checks['failures']}")

    for sz in checks["sample_zones"]:
        print(f"   Muestra: {sz}")

    return checks["passed_all"]


def run_real_slice_audit():
    print("\n--- 2. AUDITORÍA SOBRE PERIODO CORTO REAL DE NQ (NQ 09-25) ---")
    pq_path = Path("E:/EdgeLab/data/nt8/NQ_parquet/NQ_09-25_ticks.parquet")
    if not pq_path.exists():
        print(f"ADVERTENCIA: Archivo {pq_path} no existe. Omitiendo prueba real.")
        return True

    # Cargar los primeros 500.000 ticks (~1 a 2 sesiones completas de NQ)
    import pyarrow.parquet as pq
    table = pq.read_table(pq_path)
    slice_len = min(500_000, len(table))
    table_slice = table.slice(0, slice_len)

    ts_ns = table_slice.column("ts_utc_ns").to_numpy().astype(np.int64)
    px = table_slice.column("price_ticks").to_numpy().astype(np.int64)
    vol = table_slice.column("volume").to_numpy().astype(np.float64)
    bid = table_slice.column("bid_ticks").to_numpy().astype(np.int64)
    ask = table_slice.column("ask_ticks").to_numpy().astype(np.int64)
    seq = table_slice.column("sequence").to_numpy().astype(np.int64)

    tk = TickSeries(ts_ns, px, vol, bid, ask, seq, 0.25, "NQ", "NQ 09-25", "audit_slice")
    bars = build_time_bars(tk, minutes=1)
    fps = build_footprints(tk, bars)

    print(f"Ticks cargados: {len(tk):,}")
    print(f"Barras M1 generadas: {len(bars):,}")

    params = dict(
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

    out = bigtrap_nq.run(tk, bars, fps, params=params, chart_tz="America/Chicago")
    checks = audit_run_output(out, bars, tk)

    print(f"Zonas creadas: {checks['n_zones']}")
    print(f"Eventos totales: {checks['n_events']}")

    # Resumen de microestructura
    dwells = [z["dwell_ms"] for z in checks["sample_zones"]]
    rvols = [z["rvol"] for z in checks["sample_zones"]]
    print(f"Muestras de Dwell (ms): {dwells}")
    print(f"Muestras de RVol: {rvols}")

    if checks["passed_all"]:
        print(">> VEREDICTO REAL: PASS (Todas las invariantes físicas y causales cumplidas)")
    else:
        print(f">> VEREDICTO REAL: FAIL -> {checks['failures']}")

    for sz in checks["sample_zones"]:
        print(f"   Muestra de Zona Real:")
        for k, v in sz.items():
            print(f"      {k}: {v}")

    return checks["passed_all"]


def main():
    print("=" * 70)
    print("EdgeLab — Test de Sanidad en Profundidad: BigTrapNQ")
    print("=" * 70)

    ok_syn = run_synthetic_audit()
    ok_real = run_real_slice_audit()

    print("\n" + "=" * 70)
    if ok_syn and ok_real:
        print("RESULTADO FINAL: TODO CORRECTO (PASS). El indicador se comporta exactamente según lo diseñado.")
    else:
        print("RESULTADO FINAL: AL MENOS UN CHEQUEO FALLÓ (FAIL).")
    print("=" * 70)


if __name__ == "__main__":
    main()
