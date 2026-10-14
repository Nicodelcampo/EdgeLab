"""Lector vectorizado de exports NT8 de texto (`yyyyMMdd HHmmss fffffff;last;bid;ask;volume`) con corte de holdout.

Garantías de diseño:
- El corte de holdout se aplica sobre los BYTES crudos, antes de decodificar columnas: de un chunk que contiene el
  cutoff sólo se parsean las líneas anteriores (D14). Las líneas posteriores se leen del disco como bytes, nunca se
  convierten a precio/volumen.
- No se asume huso: `ts_raw_ns` es el sello crudo interpretado como UTC-naive. El huso se decide aparte, con evidencia.
- Cada línea inválida (campos ≠ 5, sello ≠ 23 caracteres, número no parseable) se cuenta; nada se imputa.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pcsv

TS_LEN = 23                      # 'yyyyMMdd HHmmss fffffff'
PREFIX_LEN = 15                  # 'yyyyMMdd HHmmss'
COLS = ["ts", "last", "bid", "ask", "vol"]
_CONVERT = pcsv.ConvertOptions(column_types={"ts": pa.string(), "last": pa.float64(), "bid": pa.float64(),
                                             "ask": pa.float64(), "vol": pa.int64()})


@dataclass
class ReadStats:
    bytes_read: int = 0
    rows_ok: int = 0
    rows_invalid_shape: int = 0
    rows_invalid_ts: int = 0
    rows_unparseable: int = 0
    invalid_samples: list = field(default_factory=list)
    sha256: str | None = None
    sha256_complete: bool = True          # False si se cortó por holdout (no se leyó el archivo entero)
    truncated_at_cutoff: bool = False
    cutoff_hit_row: int | None = None


def iter_chunks(path, chunk_bytes: int, cutoff_prefix: bytes | None, stats: ReadStats, hasher=None):
    """Genera bloques de líneas completas. Si `cutoff_prefix` (15 bytes 'yyyyMMdd HHmmss') no es None, corta en la primera
    línea cuyo prefijo sea >= cutoff y no entrega nada de ahí en adelante."""
    carry = b""
    with open(path, "rb") as f:
        while True:
            blk = f.read(chunk_bytes)
            if not blk:
                if carry:
                    yield carry
                return
            stats.bytes_read += len(blk)
            if hasher is not None:
                hasher.update(blk)
            buf = carry + blk
            cut = buf.rfind(b"\n") + 1
            if cut == 0:
                carry = buf
                continue
            data, carry = buf[:cut], buf[cut:]
            if cutoff_prefix is not None:
                arr = np.frombuffer(data, dtype=np.uint8)
                nl = np.flatnonzero(arr == 10)
                starts = np.r_[0, nl[:-1] + 1]
                ok = (nl - starts) >= PREFIX_LEN
                keys = np.ascontiguousarray(arr[starts[ok][:, None] + np.arange(PREFIX_LEN)]).view(f"S{PREFIX_LEN}").ravel()
                ge = keys >= cutoff_prefix
                if ge.any():
                    first = int(np.argmax(ge))
                    stats.truncated_at_cutoff = True
                    stats.sha256_complete = False
                    stats.cutoff_hit_row = stats.rows_ok + stats.rows_invalid_shape + first
                    yield data[:starts[ok][first]]
                    return
            yield data


def _digits(ts, a, b):
    return pc.cast(pc.utf8_slice_codeunits(ts, a, b), pa.int64()).to_numpy(zero_copy_only=False)


def decode_chunk(data: bytes, stats: ReadStats):
    """Bytes -> dict de arrays numpy (sólo filas válidas). Descarta y cuenta las inválidas."""
    shape_bad = []

    def _handler(row):
        shape_bad.append(row.number)
        if len(stats.invalid_samples) < 20:
            stats.invalid_samples.append(("shape", row.number, row.text[:80]))
        return "skip"

    po = pcsv.ParseOptions(delimiter=";", invalid_row_handler=_handler)
    ro = pcsv.ReadOptions(column_names=COLS, use_threads=True)
    try:
        tbl = pcsv.read_csv(pa.BufferReader(data), read_options=ro, parse_options=po, convert_options=_CONVERT)
    except pa.ArrowInvalid:
        # número no parseable en algún campo: camino lento, todo string y coerción explícita
        cv = pcsv.ConvertOptions(column_types={c: pa.string() for c in COLS})
        tbl = pcsv.read_csv(pa.BufferReader(data), read_options=ro, parse_options=po, convert_options=cv)
        import pandas as pd
        df = tbl.to_pandas()
        for c in ("last", "bid", "ask", "vol"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        bad = df[["last", "bid", "ask", "vol"]].isna().any(axis=1).to_numpy()
        stats.rows_unparseable += int(bad.sum())
        if bad.any() and len(stats.invalid_samples) < 20:
            for i in np.flatnonzero(bad)[:5]:
                stats.invalid_samples.append(("number", int(i), str(df["ts"].iloc[i])))
        df = df[~bad]
        tbl = pa.table({"ts": pa.array(df["ts"]), "last": pa.array(df["last"].astype("float64")),
                        "bid": pa.array(df["bid"].astype("float64")), "ask": pa.array(df["ask"].astype("float64")),
                        "vol": pa.array(df["vol"].astype("int64"))})
    stats.rows_invalid_shape += len(shape_bad)
    ts = tbl.column("ts").combine_chunks()
    good_len = pc.equal(pc.utf8_length(ts), TS_LEN).to_numpy(zero_copy_only=False)
    if not good_len.all():
        stats.rows_invalid_ts += int((~good_len).sum())
        tbl = tbl.filter(pa.array(good_len))
        ts = tbl.column("ts").combine_chunks()
    date = _digits(ts, 0, 8)
    hh, mm, ss, fr = _digits(ts, 9, 11), _digits(ts, 11, 13), _digits(ts, 13, 15), _digits(ts, 16, 23)
    y, mo, d = date // 10000, (date // 100) % 100, date % 100
    days = ((y - 1970) * 12 + (mo - 1)).astype("datetime64[M]").astype("datetime64[D]") + (d - 1).astype("timedelta64[D]")
    ts_ns = days.astype("int64") * 86_400_000_000_000 + (hh * 3600 + mm * 60 + ss) * 1_000_000_000 + fr * 100
    stats.rows_ok += len(date)
    return dict(ts_raw_ns=ts_ns, date=date, hour=hh,
                last=tbl.column("last").to_numpy(zero_copy_only=False), bid=tbl.column("bid").to_numpy(zero_copy_only=False),
                ask=tbl.column("ask").to_numpy(zero_copy_only=False), vol=tbl.column("vol").to_numpy(zero_copy_only=False))


def iter_decoded(path, *, chunk_bytes=64 << 20, cutoff_prefix: bytes | None = None, compute_sha=True):
    """Itera dicts de arrays; `stats` se devuelve como último valor del generador vía atributo del iterador."""
    stats = ReadStats()
    hasher = hashlib.sha256() if compute_sha else None

    def gen():
        for data in iter_chunks(path, chunk_bytes, cutoff_prefix, stats, hasher):
            if len(data):
                yield decode_chunk(data, stats)
        if hasher is not None and stats.sha256_complete:
            stats.sha256 = hasher.hexdigest()
    return gen(), stats
