"""aVolClusterPOI -- extraccion de coordenadas en formato Event Store, 60 ticks.

Corre la config ganadora del eje A/B (60 ticks, RESEARCH_DEFAULTS -- ver
docs/research/AVOLCLUSTERPOI_RESOLUCION_RESULTADO_2026-08-26.md) sobre UN
contrato completo (todas sus sesiones, orden cronologico, warmup real desde el
primer tick de la cinta) y escribe un Parquet compatible con el esquema del
Event Store existente (E:\\DatosNT8\\event_store_gc_all5\\), para poder sumarse
como 5to indicador MAS ADELANTE, en un paso de merge separado y deliberado.

Por que NO escribe directo en event_store_gc_all5/: esos 5 archivos estan
siendo auditados en paralelo ahora mismo (workflow w07r71vzx) -- escribir ahi
mientras corre esa auditoria es exactamente el patron de "dos escritores en el
mismo directorio" que ya causo un incidente de procedencia en este proyecto.
Este script escribe a una carpeta separada (event_store_gc_avolcluster/); el
merge es un paso aparte, posterior, verificado.

Contrato de columnas (identico al Event Store existente):
  ts_utc_ns, source_row, contract, session_id, indicator, direction,
  price_ticks, fill_ts_utc_ns, fill_source_row, fill_price_ticks, metadata_json

Mapeo de aVolClusterPOI a ese contrato:
  - "senal" = creacion de zona (ZONE_CREATED/OFF_PRICE o AT_PRICE_CREATED),
    ts_utc_ns/source_row = cierre del bloque de 10 barras que crea la zona.
  - direction: OFF_PRICE SHORT -> -1, OFF_PRICE LONG -> +1, AT_PRICE (NEUTRAL) -> 0.
  - price_ticks = lower_tick del centro de la zona? No -- se usa el CENTRO
    ((lower+upper)//2) para tener un solo precio comparable con los otros
    indicadores (que emiten un precio de nivel, no un rango). El rango
    completo (lower/upper) queda en metadata_json, no se pierde.
  - fill: primer tick ESTRICTAMENTE posterior al cierre del bloque de senal
    (mismo contrato que BigTrap2/BigTrap2Absorption en este Event Store,
    aunque conceptualmente una zona no se "llena" como una senal direccional
    -- se adopta la misma convencion por consistencia de esquema entre
    indicadores, no porque aVolClusterPOI la necesite para su propio uso).
  - metadata_json: lower_tick, upper_tick, score, threshold, kind, samples.

Target-free: no calcula MFE/MAE/P&L/outcomes. No abre nada nuevo. Universo
pre-holdout (todas las sesiones de la cinta hasta 2026-06-30 quedan target-free
por construccion del proyecto; no se filtra manualmente aca, pero tampoco se
usa nada del resultado para elegir/medir outcomes).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.bars import build_tick_bars  # noqa: E402
from edgelab.bridge.sessions import session_begin_ns as nominal_session_begin_ns  # noqa: E402
from edgelab.bridge.indicators.avolclusterpoi import (  # noqa: E402
    SessionProfile, detect_block, session_relative_bucket, RESEARCH_DEFAULTS,
)
from tools.bt2_absorption_param_sweep import session_dates_from_ns, file_sha256  # noqa: E402
from tools.sweep_bigtrap2_tickframes import load_canonical_ticks  # noqa: E402
from diag.tasa_senales.avolcluster_plateau_placebo import block_cells_and_meta  # noqa: E402

TICK_SIZE_GC = 0.10
WINDOW_BARS = 10
TICKS_PER_BAR = 60
OUT_DIR = Path(r"E:\DatosNT8\event_store_gc_avolcluster")
INDICATOR_NAME = "aVolClusterPOI"


def direction_of(z: dict[str, Any]) -> int:
    if z["kind"] != "OFF_PRICE":
        return 0
    return 1 if z.get("direction") == 1 else -1


def extract_contract(contract: str, data_dir: Path) -> dict[str, Any]:
    t0 = time.monotonic()
    path = data_dir / f"{contract}.Last.txt"
    if not path.exists():
        raise FileNotFoundError(path)
    input_sha = file_sha256(path)
    ticks, *_ = load_canonical_ticks(path, tick_size=TICK_SIZE_GC, max_ticks=None)
    session_labels = session_dates_from_ns(ticks.ts_ns)
    all_dates = sorted(set(session_labels.tolist()))

    params = dict(RESEARCH_DEFAULTS)
    profile = SessionProfile(lookback_sessions=params["lookback_sessions"])

    rows: list[dict[str, Any]] = []
    n_blocks_total = 0

    for d in all_dates:
        mask = session_labels == d
        global_idx = np.flatnonzero(mask)
        if global_idx.size == 0:
            continue
        sess_ticks_price = ticks.price_ticks[mask]
        sess_ts = ticks.ts_ns[mask]
        sess_vol = ticks.volume[mask]
        # build_tick_bars/block_cells_and_meta necesitan un TickSeries -- se arma
        # uno liviano reusando los mismos arrays ya filtrados.
        from edgelab.bridge.ticks import TickSeries
        sess_ticks_obj = TickSeries(
            ts_ns=sess_ts, price_ticks=sess_ticks_price, volume=sess_vol,
            bid_ticks=ticks.bid_ticks[mask] if ticks.bid_ticks is not None else None,
            ask_ticks=ticks.ask_ticks[mask] if ticks.ask_ticks is not None else None,
            sequence=ticks.sequence[mask], tick_size=ticks.tick_size,
            instrument=ticks.instrument, contract=ticks.contract, source=ticks.source,
        )
        session_begin = nominal_session_begin_ns(int(sess_ts[0]))
        bars = build_tick_bars(sess_ticks_obj, ticks_per_bar=TICKS_PER_BAR)
        cells_by_block, close_by_block, end_ns_by_block = block_cells_and_meta(
            sess_ticks_obj, bars, window_bars=WINDOW_BARS)

        # mapeo bloque -> indice GLOBAL (en la cinta completa del contrato) del
        # ULTIMO tick de la ultima barra del bloque, para poder derivar source_row
        # y el primer tick posterior (fill) usando el array global. Vectorizado:
        # el ultimo tick LOCAL de cada barra es el tick justo antes de que
        # tick_bar_idx cambie (mas el ultimo tick de la sesion para la ultima barra).
        n_full = len(bars) // WINDOW_BARS
        last_bar_of_block = np.arange(WINDOW_BARS - 1, n_full * WINDOW_BARS, WINDOW_BARS)
        n_ticks_session = len(bars.tick_bar_idx)
        bar_change = np.flatnonzero(np.diff(bars.tick_bar_idx))
        last_local_tick_per_bar = np.concatenate((bar_change, [n_ticks_session - 1]))
        block_last_local_idx = last_local_tick_per_bar[last_bar_of_block]
        block_last_global_idx = global_idx[block_last_local_idx]

        for blk in sorted(cells_by_block):
            cells = cells_by_block[blk]
            close_tick = int(close_by_block[blk])
            bucket = session_relative_bucket(int(end_ns_by_block[blk]), session_begin,
                                              params["time_bucket_minutes"])
            hist = profile.history_scores(bucket)
            out = detect_block(cells, hist, params=params, close_tick=close_tick)
            profile.add_block(bucket, out["best_score"])
            n_blocks_total += 1
            for z in out["zones"]:
                sig_global_idx = int(block_last_global_idx[blk])
                sig_ts = int(end_ns_by_block[blk])
                fill_global_idx = sig_global_idx + 1
                if fill_global_idx < len(ticks):
                    fill_ts = int(ticks.ts_ns[fill_global_idx])
                    fill_px = int(ticks.price_ticks[fill_global_idx])
                else:
                    fill_global_idx = sig_global_idx
                    fill_ts = sig_ts
                    fill_px = close_tick
                lo, hi = int(z["lower_tick"]), int(z["upper_tick"])
                rows.append(dict(
                    ts_utc_ns=sig_ts,
                    source_row=sig_global_idx,
                    contract=contract,
                    session_id=d,
                    indicator=INDICATOR_NAME,
                    direction=direction_of(z),
                    price_ticks=(lo + hi) // 2,
                    fill_ts_utc_ns=fill_ts,
                    fill_source_row=fill_global_idx,
                    fill_price_ticks=fill_px,
                    metadata_json=json.dumps(dict(
                        lower_tick=lo, upper_tick=hi,
                        score=float(z["score"]), threshold=float(z["threshold"]) if z["threshold"] is not None else None,
                        kind=z["kind"],
                    )),
                ))
        profile.commit()

    elapsed = time.monotonic() - t0
    return dict(contract=contract, rows=rows, n_blocks=n_blocks_total,
                n_sessions=len(all_dates), input_sha256=input_sha, elapsed_seconds=elapsed)


def write_parquet(contract: str, result: dict[str, Any]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = contract.replace(" ", "_")
    out_path = OUT_DIR / f"{safe_name}_avolcluster_event_store.parquet"
    if result["rows"]:
        table = pa.Table.from_pylist(result["rows"])
    else:
        schema = pa.schema([
            ("ts_utc_ns", pa.int64()), ("source_row", pa.int64()), ("contract", pa.string()),
            ("session_id", pa.string()), ("indicator", pa.string()), ("direction", pa.int64()),
            ("price_ticks", pa.int64()), ("fill_ts_utc_ns", pa.int64()), ("fill_source_row", pa.int64()),
            ("fill_price_ticks", pa.int64()), ("metadata_json", pa.string()),
        ])
        table = pa.Table.from_pylist([], schema=schema)
    pq.write_table(table, out_path)
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--data-dir", type=Path, default=Path(r"E:\DatosNT8"))
    args = ap.parse_args()

    result = extract_contract(args.contract, args.data_dir)
    out_path = write_parquet(args.contract, result)

    manifest_entry = dict(
        contract=args.contract, n_events=len(result["rows"]), n_blocks=result["n_blocks"],
        n_sessions=result["n_sessions"], input_sha256=result["input_sha256"],
        elapsed_seconds=round(result["elapsed_seconds"], 1),
        parquet=str(out_path), indicator=INDICATOR_NAME, tick_size=TICK_SIZE_GC,
        ticks_per_bar=TICKS_PER_BAR, window_bars=WINDOW_BARS,
        target_free=True, outcomes_opened=False,
    )
    side_manifest = OUT_DIR / f"{args.contract.replace(' ', '_')}_manifest.json"
    side_manifest.write_text(json.dumps(manifest_entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(manifest_entry, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
