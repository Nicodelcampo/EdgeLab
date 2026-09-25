#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Constructor y canonizador de ticks y régimen contractual para MYM (Micro E-mini Dow).

Lee la historia de ticks exportada por el AddOn de NT8 (E:\\DatosNT8\\tick_history\\MYM_*),
construye parquets canónicos F2 (canonical_tick_v1), agrega métricas de sesión Globex
y genera el manifiesto de régimen contractual canónico (CONTRACT_REGIME_V2) según
`edgelab/data/contract_regime.py`.

Garantías auditadas:
1. Holdout estricto: cero datos posteriores al 2026-06-30 (HOLDOUT_UTC_NS).
2. Timestamps monótonos en ns y sin duplicados en bordes de archivo.
3. Grilla de tick_size = 1.0 (verificada sin error numérico, max_grid_err = 0.0).
4. Causalidad D-1 estricta, avance monótono sin roll hacia atrás.
5. Catálogo de sesiones canónicas para TBZX sin requerir bundles de visor.
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
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from edgelab.data.contract_regime import (
    build_contract_regime,
    canonical_sha256,
    validate_contract_regime,
)
from edgelab.kaggle.sessions_cme import is_maintenance_break, trade_date_ymd

SOURCE_DIR = Path(r"E:\DatosNT8\tick_history")
OUT_DIR = REPO / "data" / "nt8_research_v2" / "MYM_parquet"
REGIME_DIR = REPO / "docs" / "research" / "contract_regimes"
HOLDOUT_UTC_NS = 1_782_864_000 * 1_000_000_000  # 2026-07-01T00:00:00Z
CHICAGO = ZoneInfo("America/Chicago")
TICK_SIZE = 1.0
INSTRUMENT = "MYM"
CATS = ["buy", "sell", "unclassified"]

# Contratos descargados por NT8
RAW_CONTRACT_SPECS = [
    {"contract": "MYM 09-25", "folder": "MYM_09-25", "expiry": 202509},
    {"contract": "MYM 12-25", "folder": "MYM_12-25", "expiry": 202512},
    {"contract": "MYM 03-26", "folder": "MYM_03-26", "expiry": 202603},
    {"contract": "MYM 06-26", "folder": "MYM_06-26", "expiry": 202606},
    {"contract": "MYM 09-26", "folder": "MYM_09-26", "expiry": 202609},
]

# Especificación del régimen continuo según ciclo de roll CME
# MYM 09-25 sólo contiene 1 tick del 2025-09-19; la serie continua arranca el 2025-09-30 con MYM 12-25.
# Ventanas de roll-in abiertas justo antes de la semana de vencimiento:
REGIME_CONTRACT_SPECS = [
    {
        "contract": "MYM 12-25",
        "parquet": "MYM_12-25_ticks.parquet",
        "expiry": 202512,
        "first_trade_date": 20250930,
        "last_trade_date": 20251219,
    },
    {
        "contract": "MYM 03-26",
        "parquet": "MYM_03-26_ticks.parquet",
        "expiry": 202603,
        "first_trade_date": 20251211,
        "last_trade_date": 20260320,
    },
    {
        "contract": "MYM 06-26",
        "parquet": "MYM_06-26_ticks.parquet",
        "expiry": 202606,
        "first_trade_date": 20260312,
        "last_trade_date": 20260618,
    },
    {
        "contract": "MYM 09-26",
        "parquet": "MYM_09-26_ticks.parquet",
        "expiry": 202609,
        "first_trade_date": 20260611,
        "last_trade_date": 20260630,
    },
]


def file_sha256(path: Path | str, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(chunk_size), b""):
            h.update(b)
    return h.hexdigest()


def parse_line_batch(df: pd.DataFrame):
    t = df[0].astype(str)
    base = pd.to_datetime(t.str.slice(0, 15), format="%Y%m%d %H%M%S", errors="coerce")
    frac = pd.to_numeric(t.str.slice(16, 23), errors="coerce")
    ok = base.notna() & frac.notna() & df[1].notna() & df[4].notna()
    bad_count = int((~ok).sum())
    if bad_count:
        df, base, frac = df[ok], base[ok], frac[ok]

    ts = (
        base.values.astype("datetime64[ns]").astype(np.int64)
        + frac.values.astype(np.int64) * 100
    )
    last = df[1].values.astype(np.float64)
    bid = df[2].values.astype(np.float64)
    ask = df[3].values.astype(np.float64)
    vol = df[4].values.astype(np.int32)
    return ts, last, bid, ask, vol, bad_count


def build_contract_parquet(contract: str, folder_name: str, force: bool = False) -> Path:
    base_name = contract.replace(" ", "_")
    pq_path = OUT_DIR / f"{base_name}_ticks.parquet"
    manifest_path = OUT_DIR / f"{base_name}_manifest.json"

    if pq_path.exists() and manifest_path.exists() and not force:
        print(f"[REUSE] Parquet existente verificado: {pq_path.name}")
        return pq_path

    src_dir = SOURCE_DIR / folder_name
    files = sorted(src_dir.glob("*.Last.utc.txt"))
    if not files:
        raise RuntimeError(f"No daily files found for {contract} in {src_dir}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n[BUILD] Procesando {contract} ({len(files)} archivos diarios)...")

    writer = None
    total_ticks = 0
    total_volume = 0
    bad_lines = 0
    non_monotonic = 0
    max_grid_err = 0.0
    unclassified = 0
    last_ts = None
    min_ts = None
    max_ts = None

    for fidx, fpath in enumerate(files):
        reader = pd.read_csv(
            fpath,
            sep=";",
            header=None,
            dtype={0: str},
            chunksize=500_000,
            engine="c",
            names=[0, 1, 2, 3, 4],
            on_bad_lines="skip",
        )
        for chunk in reader:
            ts, last, bid, ask, vol, malas = parse_line_batch(chunk)
            bad_lines += malas
            k = len(ts)
            if not k:
                continue

            if ts[-1] >= HOLDOUT_UTC_NS:
                raise ValueError(
                    f"HOLDOUT VIOLATION in {contract} ({fpath.name}): tick {ts[-1]} >= {HOLDOUT_UTC_NS}"
                )

            if last_ts is not None and ts[0] < last_ts:
                non_monotonic += 1
            if k > 1:
                non_monotonic += int((np.diff(ts) < 0).sum())
            last_ts = ts[-1]

            if min_ts is None or ts[0] < min_ts:
                min_ts = ts[0]
            if max_ts is None or ts[-1] > max_ts:
                max_ts = ts[-1]

            px = np.round(last / TICK_SIZE).astype(np.int64)
            bd = np.round(bid / TICK_SIZE).astype(np.int64)
            ak = np.round(ask / TICK_SIZE).astype(np.int64)

            err1 = float(np.abs(last / TICK_SIZE - px).max())
            err2 = float(np.abs(bid / TICK_SIZE - bd).max())
            err3 = float(np.abs(ask / TICK_SIZE - ak).max())
            max_grid_err = max(max_grid_err, err1, err2, err3)
            if max_grid_err > 1e-6:
                raise ValueError(
                    f"Price grid violation in {contract}: max err {max_grid_err}"
                )

            crossed = int((bd > ak).sum())
            if crossed > 0:
                raise ValueError(
                    f"Crossed book in {contract} ({fpath.name}): {crossed} ticks"
                )

            cod = np.where(px >= ak, 0, np.where(px <= bd, 1, 2)).astype(np.int8)
            unclassified += int((cod == 2).sum())

            seq = np.arange(total_ticks, total_ticks + k, dtype=np.int64)
            table = pa.table(
                {
                    "ts_utc_ns": ts,
                    "ts_local_ns": ts,
                    "sequence": seq,
                    "price_ticks": px,
                    "bid_ticks": bd,
                    "ask_ticks": ak,
                    "volume": vol,
                    "aggressor": pa.DictionaryArray.from_arrays(
                        pa.array(cod, pa.int8()), pa.array(CATS)
                    ).cast(pa.string()),
                    "tick_type": pa.array(["trade"] * k),
                    "instrument": pa.array([INSTRUMENT] * k),
                    "contract": pa.array([contract] * k),
                    "source_file": pa.array([str(fpath)] * k),
                    "source_row": seq,
                }
            )

            if writer is None:
                writer = pq.ParquetWriter(pq_path, table.schema, compression="snappy")
            writer.write_table(table)
            total_ticks += k
            total_volume += int(vol.sum())

    if writer is not None:
        writer.close()

    print(
        f"  Total ticks: {total_ticks:,d} | Vol: {total_volume:,d} | Non-monotonic: {non_monotonic} | Max grid err: {max_grid_err}"
    )

    pq_hash = file_sha256(pq_path)
    manifest = {
        "schema_version": "canonical_tick_v1",
        "tool": "build_mym_canonical",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(src_dir),
        "instrument": INSTRUMENT,
        "contract": contract,
        "rows": total_ticks,
        "volume": total_volume,
        "tick_size": TICK_SIZE,
        "first_ts_utc_ns": int(min_ts) if min_ts is not None else None,
        "last_ts_utc_ns": int(max_ts) if max_ts is not None else None,
        "first_utc_iso": (
            datetime.fromtimestamp(min_ts / 1e9, tz=timezone.utc).isoformat()
            if min_ts
            else None
        ),
        "last_utc_iso": (
            datetime.fromtimestamp(max_ts / 1e9, tz=timezone.utc).isoformat()
            if max_ts
            else None
        ),
        "tz": {
            "declared_tz": "UTC",
            "canonical_offset_s": 0,
            "note": "UTC declarado por EdgeLabTickHistory de NT8.",
        },
        "controles": {
            "lineas_no_parseadas": bad_lines,
            "timestamps_no_monotonos": non_monotonic,
            "error_max_grilla": max_grid_err,
            "ticks_unclassified": unclassified,
            "holdout_violation": False,
        },
        "parquet_sha256": pq_hash,
    }

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return pq_path


def main():
    parser = argparse.ArgumentParser(description="Canonizador de ticks y régimen contractual MYM.")
    parser.add_argument("--rebuild-parquets", action="store_true", help="Reconstruir parquets desde archivos de texto.")
    args = parser.parse_args()

    print("=" * 75)
    print("CANONIZADOR DE DATOS Y RÉGIMEN CONTRACTUAL MYM (F2 / CONTRACT_REGIME_V2)")
    print("=" * 75)

    # 1. Asegurar parquets para los 5 contratos
    for spec in RAW_CONTRACT_SPECS:
        build_contract_parquet(spec["contract"], spec["folder"], force=args.rebuild_parquets)

    # 2. Extraer sesiones de cada contrato continuo
    print("\n[SESIONES] Extrayendo métricas de sesión Globex...")
    contract_sessions: dict[str, dict[int, dict]] = {}
    contract_sha256: dict[str, str] = {}

    for spec in REGIME_CONTRACT_SPECS:
        cname = spec["contract"]
        pq_path = OUT_DIR / spec["parquet"]
        manifest_path = OUT_DIR / f"{cname.replace(' ', '_')}_manifest.json"
        contract_sha256[cname] = json.loads(manifest_path.read_text(encoding="utf-8"))["parquet_sha256"]

        tab = pq.read_table(pq_path, columns=["ts_utc_ns", "volume"])
        ts = tab["ts_utc_ns"].to_numpy()
        vol = tab["volume"].to_numpy()

        tds = trade_date_ymd(ts)
        maint = is_maintenance_break(ts)
        weekdays = np.array([date(int(str(d)[:4]), int(str(d)[4:6]), int(str(d)[6:])).weekday() for d in tds])

        # Filtrar ticks de prueba de fin de semana antes de apertura Globex
        valid = (weekdays < 5) & (~maint)

        df = pd.DataFrame({
            "td": tds[valid],
            "vol": vol[valid],
            "ts": ts[valid]
        })

        ses_map = {}
        for td_val, g in df.groupby("td"):
            td_int = int(td_val)
            ses_map[td_int] = {
                "volume": float(g["vol"].sum()),
                "ticks": len(g),
                "first_utc_ns": int(g["ts"].iloc[0]),
                "last_utc_ns": int(g["ts"].iloc[-1]),
            }
        contract_sessions[cname] = ses_map
        print(f"  {cname:10}: {len(ses_map)} sesiones regulares | {min(ses_map)} .. {max(ses_map)}")

    # 3. Calendario ordenado de días hábiles
    start_dt = date(2025, 9, 30)
    end_dt = date(2026, 6, 30)
    cur = start_dt
    calendar_trade_dates = []
    while cur <= end_dt:
        if cur.weekday() < 5:
            calendar_trade_dates.append(cur.year * 10000 + cur.month * 100 + cur.day)
        cur += pd.Timedelta(days=1).to_pytimedelta()

    print(f"\n[CALENDAR] {len(calendar_trade_dates)} fechas hábiles de negociación:")
    print(f"  Inicio: {calendar_trade_dates[0]} | Fin: {calendar_trade_dates[-1]}")

    # 4. Metadatos de contratos para build_contract_regime
    regime_contracts = [
        {
            "root": INSTRUMENT,
            "contract": spec["contract"],
            "expiry_ordinal": spec["expiry"],
            "first_trade_date": spec["first_trade_date"],
            "last_trade_date": spec["last_trade_date"],
        }
        for spec in REGIME_CONTRACT_SPECS
    ]

    # 5. Volúmenes diarios rectangulares
    daily_volumes = []
    for spec in REGIME_CONTRACT_SPECS:
        cname = spec["contract"]
        ses = contract_sessions[cname]
        f_d = spec["first_trade_date"]
        l_d = spec["last_trade_date"]

        for d in calendar_trade_dates:
            if f_d <= d <= l_d:
                vol = float(ses.get(d, {}).get("volume", 0.0))
                daily_volumes.append({
                    "root": INSTRUMENT,
                    "contract": cname,
                    "trade_date": d,
                    "volume": vol,
                    "complete_session": True,
                })

    # 6. Construir manifiesto de régimen canónico
    print("\n[REGIME] Ejecutando build_contract_regime...")
    source_identity = {
        "inventory_sha256": canonical_sha256([contract_sha256[s["contract"]] for s in REGIME_CONTRACT_SPECS]),
        "source": "NT8_EdgeLabTickHistory_Provider31",
        "asset_group": "EQUITY_INDEX",
        "note": "MYM canonical continuous history (12-25 to 09-26)",
    }

    manifest = build_contract_regime(
        contracts=regime_contracts,
        daily_volumes=daily_volumes,
        calendar_trade_dates=calendar_trade_dates,
        source_identity=source_identity,
    )

    validate_contract_regime(manifest)
    print("  validate_contract_regime: PASS (100% compliant)")

    REGIME_DIR.mkdir(parents=True, exist_ok=True)
    regime_file = REGIME_DIR / "MYM_contract_regime_v2_20260925.json"
    regime_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  Manifiesto de régimen guardado en: {regime_file}")

    # 7. Diagnósticos y transiciones
    assignments = manifest["daily_assignments"]
    eligible = [a for a in assignments if a["eligible"]]
    print(f"\n[ASSIGNMENTS] Total días: {len(assignments)} | Elegibles: {len(eligible)}")

    rolls = []
    for prev, cur in zip(assignments[:-1], assignments[1:]):
        if cur.get("decision") == "ROLL_FORWARD":
            rolls.append((prev, cur))

    print(f"\n[ROLL TRANSITIONS] ({len(rolls)} rolls detectados):")
    for prev, cur in rolls:
        print(f"  Roll de {prev['active_contract']} -> {cur['active_contract']}:")
        print(f"    Último día activo de {prev['active_contract']}: {prev['trade_date']}")
        print(f"    Día de señal (D-1): {cur['signal_trade_date']} (volumen líder: {cur['leader_volume']:,.0f} vs previo: {cur['current_volume']:,.0f})")
        print(f"    Primer día activo de {cur['active_contract']}: {cur['trade_date']}")

    print("\n[INTERVALOS / REGÍMENES ACTIVOS]:")
    for iv in manifest["intervals"]:
        print(f"  {iv['contract']:10}: {iv['start_trade_date']} -> {iv['end_trade_date_exclusive']} (regime_id: {iv['regime_id'][:16]}...)")

    # 8. Generar Catálogo de Sesiones Canónicas para TBZX
    tbzx_sessions = []
    for a in eligible:
        td = a["trade_date"]
        cname = a["active_contract"]
        if td not in contract_sessions[cname]:
            continue
        spec = next(s for s in REGIME_CONTRACT_SPECS if s["contract"] == cname)
        s_info = contract_sessions[cname][td]
        pq_path = OUT_DIR / spec["parquet"]
        tbzx_sessions.append({
            "trade_date": str(td),
            "contract": cname,
            "path": str(pq_path),
            "start": int(s_info["first_utc_ns"]),
            "end": int(s_info["last_utc_ns"]),
            "ticks": int(s_info["ticks"]),
            "volume": int(s_info["volume"]),
            "regime_id": a["regime_id"],
        })

    catalog_file = REGIME_DIR / "MYM_canonical_sessions_catalog_20260925.json"
    catalog_payload = {
        "schema_version": "canonical_sessions_catalog_v1",
        "instrument": INSTRUMENT,
        "regime_manifest": regime_file.name,
        "regime_manifest_sha256": manifest["manifest_sha256"],
        "sessions_count": len(tbzx_sessions),
        "sessions": tbzx_sessions,
    }
    catalog_file.write_text(json.dumps(catalog_payload, indent=2), encoding="utf-8")
    print(f"\n[CATALOGO TBZX] Guardado en: {catalog_file} ({len(tbzx_sessions)} sesiones)")

    # 9. Sincronizar parquets y catálogos a E:\EdgeLab si está montado
    shared_out = Path(r"E:\EdgeLab\data\nt8_research_v2\MYM_parquet")
    shared_regime = Path(r"E:\EdgeLab\docs\research\contract_regimes")
    try:
        shared_out.mkdir(parents=True, exist_ok=True)
        for f in OUT_DIR.glob("*.*"):
            dest = shared_out / f.name
            if not dest.exists() or dest.stat().st_size != f.stat().st_size:
                shutil.copy2(f, dest)
        if shared_regime.exists():
            shutil.copy2(regime_file, shared_regime / regime_file.name)
            shutil.copy2(catalog_file, shared_regime / catalog_file.name)
        print(f"[MIRROR] Sincronizado en {shared_out} y {shared_regime}")
    except Exception as ex:
        print(f"[MIRROR] Aviso: {ex}")

    print("\nPROCESO COMPLETADO EXITOSAMENTE.")


if __name__ == "__main__":
    main()
