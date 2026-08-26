#!/usr/bin/env python3
"""Build canonical Event Store coordinates for GC all 5 contracts.

Processes BigTrap2Absorption, BigTrap2, HFTZones2, VolTicksPOC2 over the 5 GC Parquets.
Output: Parquet tables by contract in E:\\DatosNT8\\event_store_gc_all5
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import load_canonical_parquet
from edgelab.bridge.indicators import (
    bigtrap2absorption,
    bigtrap2,
    hftzones2,
    voltickspoc2,
)
from edgelab.bridge.bars import build_footprints, build_tick_bars


def cme_session_dates(ts_ns: np.ndarray) -> np.ndarray:
    sec = ts_ns // 1_000_000_000
    dt = pd.to_datetime(sec, unit="s", utc=True).tz_convert("America/Chicago")
    is_after_17 = dt.hour >= 17
    trade_dt = dt + pd.to_timedelta(np.where(is_after_17, 1, 0), unit="D")
    return trade_dt.strftime("%Y%m%d").to_numpy()

DATA_DIR = Path(r"E:\DatosNT8\gc_gate1_parquets_20260825")
OUT_DIR = Path(r"E:\DatosNT8\event_store_gc_all5")
CONTRACTS = ["GC 12-25", "GC 02-26", "GC 04-26", "GC 06-26", "GC 08-26"]


def process_contract(contract: str, parquet_path: Path) -> pd.DataFrame:
    print(f"\n--- Procesando Event Store para {contract} ({parquet_path.name}) ---")
    ticks = load_canonical_parquet(parquet_path, contract=contract, instrument="GC")
    sessions = cme_session_dates(ticks.ts_ns)
    n_ticks = len(ticks.ts_ns)
    print(f"  Ticks cargados: {n_ticks:,} | Sesiones: {len(np.unique(sessions))}")

    events = []

    # 1. BigTrap2Absorption
    print("  [1/4] Ejecutando BigTrap2Absorption...")
    res_abs = bigtrap2absorption.run(ticks, params=bigtrap2absorption.DEFAULTS)
    for z in res_abs.get("zones", []):
        idx = int(z["sig_idx"])
        fill_idx = min(idx + 1, n_ticks - 1)
        direction = 1 if z["dir"] == "long" else -1
        events.append({
            "ts_utc_ns": int(z["sig_ts"]),
            "source_row": int(ticks.sequence[idx]),
            "contract": contract,
            "session_id": str(sessions[idx]),
            "indicator": "BigTrap2Absorption",
            "direction": direction,
            "price_ticks": int(ticks.price_ticks[idx]),
            "fill_ts_utc_ns": int(ticks.ts_ns[fill_idx]),
            "fill_source_row": int(ticks.sequence[fill_idx]),
            "fill_price_ticks": int(ticks.price_ticks[fill_idx]),
            "metadata_json": json.dumps({
                "score": float(z.get("score", 0.0)),
                "absorption_vol": float(z.get("absorbed_vol", 0.0)),
                "trap_vol": float(z.get("trap_vol", 0.0)),
            }, separators=(",", ":")),
        })
    print(f"    -> {len(res_abs.get('zones', [])):,} eventos de absorción.")

    # 2. BigTrap2
    print("  [2/4] Ejecutando BigTrap2...")
    bars25 = build_tick_bars(ticks, 25, reiniciar_por_sesion=True)
    fps25 = build_footprints(ticks, bars25)
    res_bt2 = bigtrap2.run(ticks, bars25, fps25, params=bigtrap2.DEFAULTS)
    changes = np.flatnonzero(np.diff(bars25.tick_bar_idx)) + 1
    stops = np.concatenate((changes, [n_ticks]))
    for z in res_bt2.get("zones", []):
        bar = int(z["created_bar"])
        if bar < len(stops):
            idx = int(stops[bar] - 1)
            fill_idx = min(idx + 1, n_ticks - 1)
            direction = 1 if z["kind"] == "trapped_sellers" else -1
            events.append({
                "ts_utc_ns": int(ticks.ts_ns[idx]),
                "source_row": int(ticks.sequence[idx]),
                "contract": contract,
                "session_id": str(sessions[idx]),
                "indicator": "BigTrap2",
                "direction": direction,
                "price_ticks": int(ticks.price_ticks[idx]),
                "fill_ts_utc_ns": int(ticks.ts_ns[fill_idx]),
                "fill_source_row": int(ticks.sequence[fill_idx]),
                "fill_price_ticks": int(ticks.price_ticks[fill_idx]),
                "metadata_json": json.dumps({
                    "kind": str(z.get("kind")),
                    "trap_vol": float(z.get("trap_volume", 0.0)),
                }, separators=(",", ":")),
            })
    print(f"    -> {len(res_bt2.get('zones', [])):,} eventos BigTrap2.")

    # 3. HFTZones2
    print("  [3/4] Ejecutando HFTZones2...")
    try:
        res_hft = hftzones2.run(ticks, bars25, params=hftzones2.DEFAULTS)
        for z in res_hft.get("zones", []):
            bar = int(z.get("created_bar", z.get("bar_idx", 0)))
            idx = int(stops[bar] - 1) if bar < len(stops) else n_ticks - 1
            fill_idx = min(idx + 1, n_ticks - 1)
            direction = 1 if z.get("dir", z.get("direction", "long")) in ("long", 1) else -1
            events.append({
                "ts_utc_ns": int(ticks.ts_ns[idx]),
                "source_row": int(ticks.sequence[idx]),
                "contract": contract,
                "session_id": str(sessions[idx]),
                "indicator": "HFTZones2",
                "direction": direction,
                "price_ticks": int(ticks.price_ticks[idx]),
                "fill_ts_utc_ns": int(ticks.ts_ns[fill_idx]),
                "fill_source_row": int(ticks.sequence[fill_idx]),
                "fill_price_ticks": int(ticks.price_ticks[fill_idx]),
                "metadata_json": json.dumps({
                    "zone_width": int(z.get("zone_width", 0)),
                }, separators=(",", ":")),
            })
        print(f"    -> {len(res_hft.get('zones', [])):,} eventos HFTZones2.")
    except Exception as e:
        print(f"    -> HFTZones2 error: {e}")

    # 4. VolTicksPOC2
    print("  [4/4] Ejecutando VolTicksPOC2...")
    try:
        res_poc = voltickspoc2.run(ticks, bars25, fps25, params=voltickspoc2.DEFAULTS)
        for z in res_poc.get("zones", []):
            bar = int(z.get("created_bar", z.get("bar_idx", 0)))
            idx = int(stops[bar] - 1) if bar < len(stops) else n_ticks - 1
            fill_idx = min(idx + 1, n_ticks - 1)
            direction = 1 if z.get("kind", "bullish") == "bullish" else -1
            events.append({
                "ts_utc_ns": int(ticks.ts_ns[idx]),
                "source_row": int(ticks.sequence[idx]),
                "contract": contract,
                "session_id": str(sessions[idx]),
                "indicator": "VolTicksPOC2",
                "direction": direction,
                "price_ticks": int(ticks.price_ticks[idx]),
                "fill_ts_utc_ns": int(ticks.ts_ns[fill_idx]),
                "fill_source_row": int(ticks.sequence[fill_idx]),
                "fill_price_ticks": int(ticks.price_ticks[fill_idx]),
                "metadata_json": json.dumps({
                    "poc_vol": float(z.get("poc_volume", z.get("poc_vol", 0.0))),
                }, separators=(",", ":")),
            })
        print(f"    -> {len(res_poc.get('zones', [])):,} eventos VolTicksPOC2.")
    except Exception as e:
        print(f"    -> VolTicksPOC2 error: {e}")

    df = pd.DataFrame(events)
    if not df.empty:
        df = df.sort_values(by=["ts_utc_ns", "source_row"]).reset_index(drop=True)
    return df


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {}
    total_events = 0

    for c in CONTRACTS:
        fn = f"{c.replace(' ', '_')}_ticks.parquet"
        pq_in = DATA_DIR / fn
        if not pq_in.is_file():
            print(f"Omitiendo {c}: no existe {pq_in}")
            continue

        df = process_contract(c, pq_in)
        out_fn = f"{c.replace(' ', '_')}_event_store.parquet"
        out_pq = OUT_DIR / out_fn
        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, out_pq, compression="zstd")

        counts_by_ind = df["indicator"].value_counts().to_dict() if not df.empty else {}
        summary[c] = {
            "total_events": len(df),
            "by_indicator": counts_by_ind,
            "parquet_file": out_fn,
            "size_bytes": out_pq.stat().st_size,
        }
        total_events += len(df)
        print(f"Guardado {out_fn} ({len(df):,} eventos, {out_pq.stat().st_size / 1e3:.1f} KB)")

    manifest = {
        "schema": "event_store_gc_all5_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "total_events_across_contracts": total_events,
        "contracts": summary,
    }
    (OUT_DIR / "event_store_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n=======================================================")
    print(f"EVENT STORE ALL5 COMPLETADO: {total_events:,} eventos totales.")
    print(f"Manifiesto guardado en: {OUT_DIR / 'event_store_manifest.json'}")
    print(f"=======================================================")


if __name__ == "__main__":
    main()
