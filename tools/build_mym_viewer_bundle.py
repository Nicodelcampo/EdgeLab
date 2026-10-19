#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generador del bundle de visor para MYM (Micro E-mini Dow).

Convierte ticks de MYM 03-26 en velas de 25 ticks (tick_25) y ejecuta:
1. HFTZonesNQPureV4 (motor HFTZonesUniversal, perfil SCALED_FUNNEL_V1 calibrado para MYM).
2. BigTrap2Absorption (Headline v1.1.1 canónico).

Salida:
- viewer/nt8_bridge/bundles/MYM_03-26_202601_25T_HFT.json
- viewer/nt8_bridge/bundles/MYM_03-26_202601_25T_HFT.manifest.json
- Copia/alias MYM_03-26_25T.json
- Entrada en bundles/manifest.js para integración transparente en el selector de activos.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from edgelab.bridge.bars import build_tick_bars
from edgelab.bridge.indicators import bigtrap2absorption as bt2a
from edgelab.bridge.indicators import hftzones_universal as hft
from edgelab.bridge.ticks import load_canonical_parquet
from edgelab.kaggle.sessions_cme import is_maintenance_break, trade_date_ymd

DEFAULT_HOLDOUT_NS = 1782856800000000000


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def candles_of(bars, tick_size):
    return [
        {
            "time": int(bars.end_ns[i] // 1_000_000_000),
            "open": float(bars.open_t[i]) * tick_size,
            "high": float(bars.high_t[i]) * tick_size,
            "low": float(bars.low_t[i]) * tick_size,
            "close": float(bars.close_t[i]) * tick_size,
            "volume": float(bars.volume[i]),
        }
        for i in range(len(bars))
    ]


def hft_zone_of(z, *, instrument, contract, trade_date, seq, tick_size):
    start_ns = int(z["ts_start"])
    end_ns = int(z["ts_end"])
    avail_ns = int(z["ts_avail"])
    if not (start_ns <= end_ns <= avail_ns):
        raise ValueError("zone violates origin <= end <= available")
    return {
        "id": f"{instrument}:{contract}:{trade_date}:{seq}",
        "source": "HFTZonesUniversal",
        "kind": ("HFT_BUY" if int(z["direction"]) > 0 else "HFT_SELL"),
        "top": float(z["upper"]),
        "bottom": float(z["lower"]),
        "t0": start_ns // 1_000_000_000,
        "t1": end_ns // 1_000_000_000,
        "origin_ts_ns": start_ns,
        "end_ts_ns": end_ns,
        "available_ts": avail_ns // 1_000_000_000,
        "available_ns": avail_ns,
        "termination_reason": z["termination_reason"],
        "pasos": int(z["pasos"]),
        "valid_steps": int(z["valid_steps"]),
        "height_ticks": float(z["height_ticks"]),
        "total_ms": float(z["total_ms"]),
        "avg_ms": float(z["avg_ms"]),
        "total_vol": float(z["total_vol"]),
        "vol_rate": float(z["vol_rate"]),
        "max_retro_ticks": float(z["max_retro_ticks"]),
        "bucket": z["bucket"],
        "instrument": instrument,
        "contract": contract,
        "session_id": str(trade_date),
        "tick_size": tick_size,
        "state": "ACTIVE",
    }


def bt2a_zone_of(z, *, instrument, contract, trade_date, seq, tick_size):
    t0_s = int(z["formation_start_ns"] // 1_000_000_000)
    if z.get("ended_ms"):
        t1_s = max(t0_s, int(z["ended_ms"] // 1000))
    else:
        t1_s = t0_s + 3600
    is_bear = z["dir"] == "short" or z.get("side") == "trapped_buyers"
    return {
        "id": f"BT2A_{z['id']}",
        "source": "BigTrap2Absorption",
        "kind": "ABSORB BEAR" if is_bear else "ABSORB BULL",
        "top": float(z["hi"]),
        "bottom": float(z["lo"]),
        "t0": t0_s,
        "t1": t1_s,
        "origin_ts_ns": int(z["formation_start_ns"]),
        "end_ts_ns": int(z["formation_end_ns"]),
        "available_ts": int(z["available_at_ns"] // 1_000_000_000),
        "available_ns": int(z["available_at_ns"]),
        "state": "ACTIVE" if z.get("state") == "ACTIVE" else "INVALIDATED",
        "end_reason": z.get("end_reason"),
        "vol": float(z.get("vol", 0.0)),
        "nrows": int(z.get("nrows", 1)),
        "touches": int(z.get("touches", 0)),
        "a_score": float(z.get("a_score", 0.0)),
        "a_thr": float(z.get("a_thr", 0.0)),
        "instrument": instrument,
        "contract": contract,
        "session_id": str(trade_date),
        "tick_size": tick_size,
        "match": "EXACT",
    }


def update_manifest_js(manifest_js_path: Path, new_entries: list[dict]):
    """Registra de forma segura las nuevas entradas en bundles/manifest.js si no están presentes."""
    if not manifest_js_path.exists():
        return
    text = manifest_js_path.read_text(encoding="utf-8")
    if "window.ASSET_CATALOG" not in text:
        return

    json_str = text.split("window.ASSET_CATALOG =")[1].strip().rstrip(";")
    catalog = json.loads(json_str)

    existing_ids = {item["id"] for item in catalog}
    added = False
    for entry in new_entries:
        if entry["id"] not in existing_ids:
            catalog.append(entry)
            existing_ids.add(entry["id"])
            added = True

    if added:
        new_text = "window.ASSET_CATALOG = " + json.dumps(catalog, indent=2) + ";\n"
        manifest_js_path.write_text(new_text, encoding="utf-8")
        print(f"  [MANIFEST.JS] Actualizado {manifest_js_path.name} con {len(new_entries)} entradas.")


def main():
    parser = argparse.ArgumentParser(description="Construir bundle de visor para MYM 25T.")
    parser.add_argument("--month", default="202601", help="Mes de fragmento (ej: 202601)")
    args = parser.parse_args()

    instrument = "MYM"
    contract = "MYM 03-26"
    tick_size = 1.0
    asset_id = f"MYM_03-26_{args.month}_25T_HFT"
    pq_path = REPO / "data" / "nt8_research_v2" / "MYM_parquet" / "MYM_03-26_ticks.parquet"

    if not pq_path.exists():
        raise FileNotFoundError(f"Parquet no encontrado: {pq_path}")

    source_hash = sha256_file(pq_path)

    # 1. Identificar sesiones del mes solicitado en el parquet
    print(f"\n[MYM VISOR BUNDLE] Construyendo {asset_id} desde {pq_path.name}...")
    tab = pq.read_table(pq_path, columns=["ts_utc_ns", "volume"])
    ts_all = tab["ts_utc_ns"].to_numpy()
    vol_all = tab["volume"].to_numpy()

    tds = trade_date_ymd(ts_all)
    maint = is_maintenance_break(ts_all)
    weekdays = np.array([date(int(str(d)[:4]), int(str(d)[4:6]), int(str(d)[6:])).weekday() for d in tds])

    # Filtrar sólo el mes solicitado (días hábiles regulares)
    target_ym = int(args.month)
    ym_arr = tds // 100
    m_mask = (ym_arr == target_ym) & (weekdays < 5) & (~maint)
    m_indices = np.where(m_mask)[0]

    if len(m_indices) == 0:
        raise ValueError(f"No se encontraron ticks para el mes {target_ym}")

    unique_tds = sorted(np.unique(tds[m_mask]))
    print(f"  Fechas de negociación encontradas ({len(unique_tds)} sesiones): {unique_tds[0]} .. {unique_tds[-1]}")
    print(f"  Total ticks en el período: {len(m_indices):,d}")

    # Procesar sesión por sesión para mantener cortes Globex exactos
    all_candles = []
    all_hft_zones = []
    all_bt2a_zones = []
    session_reports = []
    hft_seq = 0
    bt2a_seq = 0
    carry = None

    profile_name = "SCALED_FUNNEL_V1"
    hft_thresholds = hft.profile(profile_name, instrument)

    for td in unique_tds:
        ses_mask = (tds == td) & (weekdays < 5) & (~maint)
        idx_ses = np.where(ses_mask)[0]
        if len(idx_ses) < 25:
            continue

        start_ns = int(ts_all[idx_ses[0]])
        end_ns = int(ts_all[idx_ses[-1]]) + 1

        tk = load_canonical_parquet(
            pq_path,
            contract=contract,
            instrument=instrument,
            start_utc_ns=start_ns,
            end_utc_ns=end_ns,
        )

        bars = build_tick_bars(tk, 25, reiniciar_por_sesion=True)
        ses_candles = candles_of(bars, tick_size)
        all_candles.extend(ses_candles)

        # A) HFTZonesNQPureV4 (HFTZonesUniversal)
        candidates = hft.detect_candidates(
            tk.ts_ns, tk.price_ticks, tk.volume, prev_session_close_ticks=carry
        )
        zones_hft, rejected = hft.accept_all(candidates, hft_thresholds, tick_size)
        for z in zones_hft:
            all_hft_zones.append(
                hft_zone_of(z, instrument=instrument, contract=contract, trade_date=td, seq=hft_seq, tick_size=tick_size)
            )
            hft_seq += 1

        # B) BigTrap2Absorption (Headline v1.1.1)
        bt2a_res = bt2a.run(tk)
        for z in bt2a_res["zones"]:
            all_bt2a_zones.append(
                bt2a_zone_of(z, instrument=instrument, contract=contract, trade_date=td, seq=bt2a_seq, tick_size=tick_size)
            )
            bt2a_seq += 1

        session_reports.append({
            "trade_date": int(td),
            "start_utc_ns": start_ns,
            "end_utc_ns": end_ns,
            "ticks": len(tk),
            "tick25_bars": len(bars),
            "hft_candidates": len(candidates),
            "hft_zones": len(zones_hft),
            "bt2a_zones": len(bt2a_res["zones"]),
        })

        carry = int(tk.price_ticks[-1])

    print(f"  Velas 25T generadas: {len(all_candles):,d}")
    print(f"  Zonas HFTZonesNQPureV4: {len(all_hft_zones):,d}")
    print(f"  Zonas BigTrap2Absorption: {len(all_bt2a_zones):,d}")

    # Estructura del bundle para el visor
    run_hft = {
        "id": "hftzones_nq_pure_v4",
        "name": f"HFTZonesNQPureV4 · SCALED_FUNNEL_V1",
        "indicator": "HFTZonesNQPureV4",
        "engine": "HFTZonesUniversal",
        "bar_key": "tick_25",
        "params": hft_thresholds,
        "zones": all_hft_zones,
        "parity": {"status": "PARITY_ABSTAIN", "gate": "PARITY_ABSTAIN"},
    }

    run_bt2a = {
        "id": "bigtrap2_absorption",
        "name": f"BigTrap2Absorption (Headline v1.1.1)",
        "indicator": "BigTrap2Absorption",
        "engine": "BigTrap2Absorption",
        "bar_key": "tick_25",
        "params": dict(bt2a.DEFAULTS),
        "zones": all_bt2a_zones,
        "parity": {"status": "PARITY_ABSTAIN", "gate": "PARITY_ABSTAIN"},
    }

    bundle = {
        "meta": {
            "id": asset_id,
            "instrument": instrument,
            "contract": contract,
            "tick_size": tick_size,
            "precision": 0,
            "n_zones": len(all_hft_zones) + len(all_bt2a_zones),
            "source_sha256": source_hash,
            "holdout_boundary_ns": DEFAULT_HOLDOUT_NS,
            "outcome_firewall": "ENFORCED",
        },
        "bar_series": {
            "tick_25": {
                "kind": "tick_25",
                "name": "25 Tick",
                "candles": all_candles,
            }
        },
        "runs": [run_hft, run_bt2a],
    }

    manifest = {
        "asset_id": asset_id,
        "instrument": instrument,
        "contract": contract,
        "source_path": str(pq_path),
        "source_sha256": source_hash,
        "holdout_boundary_ns": DEFAULT_HOLDOUT_NS,
        "tick25_bars": len(all_candles),
        "hft_zones": len(all_hft_zones),
        "bt2a_zones": len(all_bt2a_zones),
        "total_zones": len(all_hft_zones) + len(all_bt2a_zones),
        "profile": profile_name,
        "engine_status": "ENGINE_PORTABLE",
        "parameter_status": "SCALED_FUNNEL_V1_TARGET_FREE",
        "parity_status": "PARITY_ABSTAIN",
        "sessions": session_reports,
    }

    # Destinos de bundle (local y unified viewer)
    out_dirs = [
        REPO / "viewer" / "nt8_bridge" / "bundles",
        Path(r"E:\EdgeLab-unified-viewer\viewer\nt8_bridge\bundles"),
    ]

    new_catalog_entries = [
        {
            "id": asset_id,
            "name": f"MYM 03-26 {args.month} (25 Tick · HFT & BT2A)",
            "group": f"MYM MYM 03-26 (Fragmentos Mensuales)",
            "instrument": "MYM",
            "contract": contract,
            "tick_size": tick_size,
            "precision": 0,
            "candles": len(all_candles),
            "zones": len(all_hft_zones) + len(all_bt2a_zones),
            "rolls": 0,
            "parity_status": "PARITY_ABSTAIN",
            "profile": profile_name,
        },
        {
            "id": "MYM_03-26_25T",
            "name": "MYM 03-26 (25 Tick · HFT & BT2A)",
            "group": "Contratos Individuales MYM",
            "instrument": "MYM",
            "contract": contract,
            "tick_size": tick_size,
            "precision": 0,
            "candles": len(all_candles),
            "zones": len(all_hft_zones) + len(all_bt2a_zones),
            "rolls": 0,
            "parity_status": "PARITY_ABSTAIN",
            "profile": profile_name,
        },
    ]

    for bdir in out_dirs:
        if not bdir.exists():
            continue
        print(f"\n[DESTINO] Escribiendo bundle en {bdir}...")
        main_json = bdir / f"{asset_id}.json"
        main_man = bdir / f"{asset_id}.manifest.json"
        alias_json = bdir / "MYM_03-26_25T.json"
        alias_man = bdir / "MYM_03-26_25T.manifest.json"

        # Escribir json de forma atómica
        tmp_json = main_json.with_suffix(".json.tmp")
        tmp_json.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        tmp_json.replace(main_json)

        main_man.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        shutil.copy2(main_json, alias_json)
        shutil.copy2(main_man, alias_man)

        # Actualizar manifest.js
        update_manifest_js(bdir / "manifest.js", new_catalog_entries)

    print("\n[ÉXITO] Bundle de MYM listo para navegar en el visor.")
    print(f"  URL directa: http://localhost:8089/?asset={asset_id}")
    print(f"  Alias URL:   http://localhost:8089/?asset=MYM_03-26_25T")


if __name__ == "__main__":
    main()
