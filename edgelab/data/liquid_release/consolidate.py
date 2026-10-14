"""Escritor de la release: un Parquet de ticks por activo, por streaming, con row groups delimitados por sesión.

Esquema `liquid_tick_v1` (extiende `canonical_tick_v1`; NO se confunde con la secuencia del exchange):
  ts_utc_ns       int64   sello UTC verificado = sello crudo - offset de la fuente
  price_ticks     int64   precio / tick_size (la grilla se valida antes de redondear; ver `grid_ok`)
  bid_ticks       int64   -1 si no hay quote válido
  ask_ticks       int64   -1 si no hay quote válido
  volume          int64
  aggressor       int8    +1 compra (px>=ask), -1 venta (px<=bid), 0 sin clasificar (regla de quotes v1)
  contract        dict    contrato REAL de la fila (p. ej. 'ES 12-25')
  regime_id       int16   contador de contrato líder del activo (cambia en cada roll)
  trade_date      int32   fecha de trading CME (yyyymmdd) = fecha en que cierra la sesión
  outside_regular bool    tick dentro de la pausa 16:00-17:00 CT o fin de semana: se conserva marcado, no se borra
  source_id       int16   índice en `sources` del manifiesto del activo
  source_row      int64   número de fila (0-based) dentro del archivo fuente
  release_row     int64   orden consolidado (NO es secuencia del exchange)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from edgelab.data.liquid_release.nt8_text import iter_decoded

NS_H = 3_600_000_000_000
ROW_GROUP_MAX = 2_000_000


def schema() -> pa.Schema:
    return pa.schema([
        ("ts_utc_ns", pa.int64()), ("price_ticks", pa.int64()), ("bid_ticks", pa.int64()), ("ask_ticks", pa.int64()),
        ("volume", pa.int64()), ("aggressor", pa.int8()), ("contract", pa.dictionary(pa.int8(), pa.string())),
        ("regime_id", pa.int16()), ("trade_date", pa.int32()), ("outside_regular", pa.bool_()),
        ("source_id", pa.int16()), ("source_row", pa.int64()), ("release_row", pa.int64())])


@dataclass
class SourceFile:
    path: str
    source_id: int
    offset_h: int                     # sello UTC = crudo - offset_h horas
    kind: str                         # 'A' o 'B'
    cutoff_prefix: bytes | None = None


@dataclass
class Segment:
    contract: str
    regime_id: int
    files: list                       # list[SourceFile]
    trade_dates: set                  # fechas de trading seleccionadas para este contrato
    lookup: dict = field(default_factory=dict)   # key (raw_date*24+raw_hour) -> (trade_date, outside_regular)


def aggressor(last, bid, ask):
    """Regla de quotes v1. Book locked/cruzado o ausente -> 0 (sin clasificar): no se inventa agresor (D13)."""
    a = np.zeros(len(last), dtype=np.int8)
    ok = (bid > 0) & (ask > 0) & (ask > bid)
    a[ok & (last >= ask)] = 1
    a[ok & (last <= bid)] = -1
    return a


def write_asset(out_path, segments: list, tick_size: float, tick_check_tol=1e-6):
    """Escribe el activo. Devuelve estadísticas por segmento. STOP (ValueError) si una fila seleccionada no cae en la grilla."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".parquet.tmp")
    writer = pq.ParquetWriter(tmp, schema(), compression="zstd", compression_level=3)
    release_row = 0
    stats = []
    for seg in segments:
        keys = np.array(sorted(seg.lookup), dtype=np.int64)
        td_arr = np.array([seg.lookup[k][0] for k in keys], dtype=np.int32)
        ob_arr = np.array([seg.lookup[k][1] for k in keys], dtype=bool)
        sel = np.array(sorted(seg.trade_dates), dtype=np.int32)
        rows_seg = 0
        for sf in seg.files:
            it, st = iter_decoded(sf.path, chunk_bytes=32 << 20, cutoff_prefix=sf.cutoff_prefix, compute_sha=False)
            base = 0
            for b in it:
                n = len(b["date"])
                row_idx = np.arange(base, base + n, dtype=np.int64)
                base += n
                k = b["date"].astype(np.int64) * 24 + b["hour"]
                pos = np.searchsorted(keys, k)
                pos = np.clip(pos, 0, len(keys) - 1)
                found = keys[pos] == k
                td = np.where(found, td_arr[pos], 0)
                ob = np.where(found, ob_arr[pos], True)
                keep = found & np.isin(td, sel)
                if not keep.any():
                    continue
                last, bid, ask = b["last"][keep], b["bid"][keep], b["ask"][keep]
                gl = last / tick_size
                if (np.abs(gl - np.rint(gl)) > tick_check_tol).any():
                    raise ValueError(f"precio fuera de la grilla de {tick_size} en {sf.path} (contrato {seg.contract})")
                qok = (bid > 0) & (ask > 0)
                bt = np.where(qok, np.rint(bid / tick_size), -1).astype(np.int64)
                at = np.where(qok, np.rint(ask / tick_size), -1).astype(np.int64)
                m = int(keep.sum())
                tdk = td[keep]
                tbl = pa.table({
                    "ts_utc_ns": b["ts_raw_ns"][keep] - sf.offset_h * NS_H,
                    "price_ticks": np.rint(gl).astype(np.int64), "bid_ticks": bt, "ask_ticks": at,
                    "volume": b["vol"][keep].astype(np.int64), "aggressor": aggressor(last, bid, ask),
                    "contract": pa.array([seg.contract] * m).dictionary_encode().cast(pa.dictionary(pa.int8(), pa.string())),
                    "regime_id": np.full(m, seg.regime_id, dtype=np.int16), "trade_date": tdk,
                    "outside_regular": ob[keep], "source_id": np.full(m, sf.source_id, dtype=np.int16),
                    "source_row": row_idx[keep], "release_row": np.arange(release_row, release_row + m, dtype=np.int64)})
                # un row group por tramo contiguo de la misma fecha de trading (estadísticas min=max)
                cuts = np.flatnonzero(np.diff(tdk) != 0) + 1
                for part in np.split(np.arange(m), cuts):
                    for s in range(0, len(part), ROW_GROUP_MAX):
                        sl = part[s:s + ROW_GROUP_MAX]
                        writer.write_table(tbl.take(pa.array(sl)), row_group_size=ROW_GROUP_MAX)
                release_row += m
                rows_seg += m
        stats.append(dict(contract=seg.contract, regime_id=seg.regime_id, rows=rows_seg, sessions=len(seg.trade_dates)))
    writer.close()
    tmp.replace(out_path)
    return stats, release_row
