# -*- coding: utf-8 -*-
"""L2 Book Depth and L1 Quotes Parser for EdgeLab.

Parses unified CME Market-By-Price feed events del dump NRD->CSV de NT8:

    L2;side;timestamp;microsecond;operation;level;;price;size
    L1;side;timestamp;microsecond;price;size

SEMANTICA DE `side` EN L1 -- CORREGIDA 2026-08-21
=================================================
El acta de intake (INTAKE_L2_ES_NRD_2026-08-21.md) tenia mal tres de los cuatro codigos.
El mapeo verificado, que coincide con el enum MarketDataType de NT8:

    0 -> ASK    (BestAsk quote)      size = profundidad en el toque
    1 -> BID    (BestBid quote)      size = profundidad en el toque
    2 -> LAST   (trade ejecutado)    size = tamano del trade
    5 -> DAILY_VOLUME                price = 0, size = volumen acumulado

Evidencia en docs/research/CORRECCION_ESQUEMA_L1_ES_SEP26_2026-08-21.md: reconstruccion
sobre 2.000.000 de eventos consecutivos da 0,044% de violaciones ask<=bid bajo 0=Ask
contra 99,998% bajo 1=Ask.

`source_row` -- POR QUE ES OBLIGATORIO
======================================
El dump tiene ~80% de empates en microsegundo. Sin el numero de linea del CSV, el orden
de los eventos dentro de un mismo timestamp NO es recuperable, y eso rompe cualquier
reconstruccion del libro evento a evento, clasificacion de agresor contra el quote
vigente, u OFI.

`source_row` es el indice de linea en el CSV ORIGINAL (0-based, contando L1 y L2 juntas),
asi que ademas preserva el INTERCALADO entre los dos flujos: un evento L2 y uno L1 con el
mismo timestamp quedan ordenables entre si.

RELOJ
=====
`ts_us` es el reloj de pared tal como lo escribio NT8, interpretado como si fuera UTC.
Su referencia absoluta NO esta establecida: contra el export de ticks `.Last.txt` el
desfase optimo es de 3 h menos 8 s y el acuerdo de precios llega solo al 45%, o sea que
NO son un offset constante. Ver la correccion citada arriba.

Consecuencia practica: L1 y L2 comparten UN SOLO reloj entre si, asi que todo analisis
interno del libro es valido. Unir esto con otra fuente exige resolver la referencia
primero -- nunca por cercania de timestamp.
"""
from __future__ import annotations

import hashlib
import os
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

L2_SCHEMA = "NT8_MBP10_REPLAY_V1"          # distingue esta fuente (Market Replay MBP-10) de TAPE_LONG_HORIZON_V1
                                            # (.Last.txt) -- no se mezclan bajo un mismo nombre "ticks" (auditor).
PRICE_ROUNDTRIP_TOLERANCE = 1e-6           # residuo maximo tolerado en `price - price_tick*tick_size`. El
                                            # residuo de punto flotante puro observado en datos reales (GC,
                                            # tick=0.1) es ~1e-12; esta tolerancia es ~1e6 veces mas laxa que eso
                                            # y sigue siendo ~4 ordenes de magnitud mas chica que el tick mas fino
                                            # en uso (6E, 0.00005) -- separa ruido de punto flotante de un precio
                                            # genuinamente fuera de grilla.

# Rango epoch plausible en MICROSEGUNDOS: 2001-09-09 .. 2065. Sirve de asercion dura
# contra el bug de unidades descripto abajo.
_US_MIN, _US_MAX = 1_000_000_000_000_000, 3_000_000_000_000_000


def _a_microsegundos(serie_ts_str, serie_usec):
    """Epoch en MICROSEGUNDOS, independiente de la version de pandas.

    BUG QUE ESTO ARREGLA (2026-08-21). La version anterior hacia:

        pd.to_datetime(...).astype("int64") // 1000 + usec

    y eso depende de la resolucion que devuelva `to_datetime`:
      - pandas 2.x  -> datetime64[ns] -> astype int64 = ns -> //1000 = us   CORRECTO
      - pandas 3.0.3 -> datetime64[us] -> astype int64 = us -> //1000 = ms  MAL, 1000x

    O sea que el MISMO codigo producia unidades distintas segun la maquina. Los parquets
    del sandbox salieron bien y los de esta maquina salian en milisegundos, con el campo
    de microsegundos sumado encima. Se convierte a [us] EXPLICITAMENTE y se verifica.
    """
    dt = pd.to_datetime(serie_ts_str.astype(str), format="%Y%m%d%H%M%S", errors="coerce")
    us = dt.values.astype("datetime64[us]").astype(np.int64) + serie_usec.astype(np.int64)
    if len(us):
        lo, hi = int(np.min(us)), int(np.max(us))
        if not (_US_MIN <= lo and hi <= _US_MAX):
            raise ValueError(
                "ts_us fuera del rango epoch plausible en microsegundos: [%d, %d]. "
                "Casi seguro un problema de unidades." % (lo, hi))
    return us


SUBSEC_US, SUBSEC_100NS = "microseconds", "100ns_ticks"


def _detect_subsecond_unit(fields: np.ndarray) -> str:
    """Unidad de la columna de fraccion de segundo del CSV de NT8.

    BUG QUE ESTO ARREGLA (2026-09-23; ya corregido el 2026-08-25 en `b3b2a43b`, rama
    `work/futures-l2-context-foundation-20260825`, que nunca se integro a esta linea). NT8
    (`MarketReplay.DumpMarketDepth`, la misma llamada que usan NRDToCSV y el Replay Downloader)
    escribe la fraccion en TICKS de .NET = 100 ns (7 digitos, 0..9.999.999). Sumarla como
    microsegundos multiplica la fraccion por 10: hasta +9,99 s de error y decenas de miles de
    inversiones de reloj por sesion. Medido en GC 08-26 20260625: 7.183.327 filas, 0 inversiones
    con /10, error de hasta 8,964 s sin /10.

    Regla: si algun valor supera 999.999 la columna NO puede ser microsegundos -> 100 ns. Si
    ninguno lo supera se asume microsegundos (formato de los fixtures y de conversores viejos). La
    unidad detectada queda escrita en el manifest (`conversion.subsecond_unit`)."""
    if len(fields) == 0:
        return SUBSEC_US
    mx = int(np.max(fields))
    if mx > 9_999_999 or int(np.min(fields)) < 0:
        raise ValueError(f"fraccion de segundo fuera de rango para cualquier unidad conocida: [{int(np.min(fields))}, {mx}]")
    return SUBSEC_100NS if mx > 999_999 else SUBSEC_US


# Tipos fijos del CSV de NT8 (`L2;side;yyyyMMddHHmmss;frac;op;level;;price;size` y `L1;side;ts;frac;price;size`).
# Se fijan para que la lectura por bloques no infiera tipos distintos en cada bloque. float64 es exacto para todos
# los enteros en juego (ts de 14 digitos < 2^53) y usa el MISMO parser de read_csv que la inferencia vieja.
_RAW_DTYPES = {0: str, **{i: np.float64 for i in range(1, 9)}}
STREAM_CHUNK_ROWS = 2_000_000       # ~40 M filas por dia en NQ: leer entero pedia decenas de GB (crash 2026-09-24)


def _read_raw(csv_path: Path, **kw):
    return pd.read_csv(csv_path, sep=";", header=None, names=list(range(9)), dtype=_RAW_DTYPES, **kw)


def _frames_from_raw(df_raw: pd.DataFrame, tick_size: float, div: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bloque crudo (con `source_row` ya asignado) -> (l2, l1). Unica implementacion de la transformacion: la usan
    la lectura entera (`parse_l2_raw_csv`) y la de a bloques (`convert_l2_session`), asi no pueden divergir."""
    df_raw = df_raw.copy()
    df_raw[2] = df_raw[2].astype(np.int64)          # ts yyyyMMddHHmmss: entero antes de pasarlo a texto

    # 1. L2 Depth Book updates
    m_l2 = df_raw[0] == "L2"
    df_l2 = df_raw[m_l2][[1, 2, 3, 4, 5, 7, 8, "source_row"]].copy()
    df_l2.columns = ["side", "ts_str", "usec", "operation", "level", "price", "size",
                     "source_row"]
    df_l2["side"] = df_l2["side"].astype(np.int8)
    df_l2["operation"] = df_l2["operation"].astype(np.int8)
    df_l2["level"] = df_l2["level"].astype(np.int8)
    df_l2["price"] = df_l2["price"].astype(np.float64)
    df_l2["size"] = df_l2["size"].astype(np.int32)
    
    df_l2["ts_us"] = _a_microsegundos(df_l2["ts_str"], df_l2["usec"].astype(np.int64) // div)
    df_l2["price_tick"] = np.round(df_l2["price"] / tick_size).astype(np.int32)
    df_l2.drop(columns=["ts_str", "usec"], inplace=True)
    
    # 2. L1 Quotes / Top of Book
    m_l1 = df_raw[0] == "L1"
    df_l1 = df_raw[m_l1][[1, 2, 3, 4, 5, "source_row"]].copy()
    df_l1.columns = ["side", "ts_str", "usec", "price", "size", "source_row"]
    df_l1["side"] = df_l1["side"].astype(np.int8)
    df_l1["price"] = df_l1["price"].astype(np.float64)
    df_l1["size"] = df_l1["size"].astype(np.int32)
    
    df_l1["ts_us"] = _a_microsegundos(df_l1["ts_str"], df_l1["usec"].astype(np.int64) // div)
    df_l1["price_tick"] = np.round(df_l1["price"] / tick_size).astype(np.int32)
    df_l1.drop(columns=["ts_str", "usec"], inplace=True)
    return df_l2, df_l1


def parse_l2_raw_csv(csv_path: str | Path, tick_size: float = 0.00005) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse raw CSV into (df_l2_depth, df_l1_quotes) LEYENDO EL ARCHIVO ENTERO (tests y archivos chicos; para
    sesiones reales usar `convert_l2_session`, que va por bloques). La unidad de la fraccion de segundo se detecta
    sobre L1+L2 juntos (ver `_detect_subsecond_unit`) y queda en `df.attrs["subsecond_unit"]`."""
    csv_path = Path(csv_path)
    df_raw = _read_raw(csv_path)
    # Indice de linea del CSV ORIGINAL, antes de separar L1 de L2: preserva el orden
    # dentro del mismo microsegundo Y el intercalado entre los dos flujos.
    df_raw["source_row"] = np.arange(len(df_raw), dtype=np.int64)
    m_any = df_raw[0].isin(["L1", "L2"])
    unit = _detect_subsecond_unit(df_raw.loc[m_any, 3].astype(np.int64).to_numpy())
    df_l2, df_l1 = _frames_from_raw(df_raw, tick_size, 10 if unit == SUBSEC_100NS else 1)
    df_l2.attrs["subsecond_unit"] = df_l1.attrs["subsecond_unit"] = unit
    return df_l2, df_l1


def _scan_subsecond_unit(csv_path: Path, chunk_rows: int) -> str:
    """Primera pasada, solo columnas 0 y 3: la unidad depende del maximo de TODO el archivo."""
    mn, mx = None, None
    for ch in _read_raw(csv_path, chunksize=chunk_rows):       # sin usecols: falla si el archivo tiene solo L1
        v = ch.loc[ch[0].isin(["L1", "L2"]), 3].to_numpy()
        if len(v):
            mn = v.min() if mn is None else min(mn, v.min())
            mx = v.max() if mx is None else max(mx, v.max())
    if mn is None:
        return _detect_subsecond_unit(np.array([], dtype=np.int64))
    return _detect_subsecond_unit(np.array([mn, mx]).astype(np.int64))


def _clock_inversions(df: pd.DataFrame) -> int:
    """Eventos cuyo ts_us es menor que el del evento anterior en orden de `source_row`."""
    if len(df) < 2:
        return 0
    ts = df.sort_values("source_row", kind="stable")["ts_us"].to_numpy()
    return int(np.sum(np.diff(ts) < 0))


class PriceRoundtripError(Exception):
    """`price` no reconstruye de forma fiable desde `price_tick * tick_size` dentro de la tolerancia -- la fila
    original no estaba en grilla (dato corrupto/off-tick), no es solo ruido de punto flotante. Fail-closed: no
    se escribe ningun parquet si esto ocurre (ver PRICE_ROUNDTRIP_TOLERANCE)."""


def _validate_price_roundtrip(df: pd.DataFrame, tick_size: float, tolerance: float = PRICE_ROUNDTRIP_TOLERANCE) -> dict:
    """abs(price - price_tick*tick_size) por fila. NO es un chequeo trivial: `price_tick` se computa con
    `np.round`, asi que un residuo grande significa que `price` no caia en la grilla del tick para empezar
    (dato malo), no que el redondeo "fallo". La tolerancia separa eso del piso de precision de float64."""
    if len(df) == 0:
        return dict(tolerance=tolerance, max_error=0.0, violations=0, rows_checked=0)
    reconstructed = df["price_tick"].to_numpy(dtype=np.float64) * tick_size
    err = np.abs(df["price"].to_numpy(dtype=np.float64) - reconstructed)
    max_err = float(err.max())
    violations = int((err > tolerance).sum())
    return dict(tolerance=tolerance, max_error=max_err, violations=violations, rows_checked=len(df))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def convert_l2_session(csv_path: str | Path, out_dir: str | Path, tick_size: float = 0.00005,
                       chunk_rows: int = STREAM_CHUNK_ROWS) -> tuple[Path, Path]:
    """Convert an L2 raw CSV into compressed L2 and L1 Parquet files.

    `price` (float64, redundante con `price_tick`+`tick_size`) se valida fila a fila contra su reconstruccion
    ANTES de eliminarla -- ver `_validate_price_roundtrip` -- y solo se elimina si pasa. Si no pasa, la
    conversion ABORTA (`PriceRoundtripError`) sin escribir ningun parquet: fail-closed, igual criterio que el
    resto del pipeline L2 (auditoria 2026-09-21). Escribe ademas `<out_dir>/manifests/<session>.manifest.json`
    con procedencia, resultado de la validacion y schema version (`L2_SCHEMA`).
    """
    csv_path = Path(csv_path)
    out_dir = Path(out_dir)
    session_name = csv_path.stem

    dir_l2 = out_dir / "l2_depth"
    dir_l1 = out_dir / "l1_quotes"
    dir_man = out_dir / "manifests"
    dir_l2.mkdir(parents=True, exist_ok=True)
    dir_l1.mkdir(parents=True, exist_ok=True)
    dir_man.mkdir(parents=True, exist_ok=True)

    # POR BLOQUES (2026-09-24): una sesion de NQ son ~40 M filas; leerla entera colgo la maquina (16 GB). Dos
    # pasadas: (1) unidad de la fraccion de segundo sobre todo el archivo; (2) transformar y escribir por bloques a
    # `.partial`. Fail-closed igual que antes: si algun bloque tiene precio fuera de grilla se borran los parciales
    # y no queda ningun parquet. Solo con todo validado se renombran (atomico) y despues se escribe el manifest.
    subsecond_unit = _scan_subsecond_unit(csv_path, chunk_rows)
    div = 10 if subsecond_unit == SUBSEC_100NS else 1

    p_l2 = dir_l2 / f"{session_name}.parquet"
    p_l1 = dir_l1 / f"{session_name}.parquet"
    p_man = dir_man / f"{session_name}.manifest.json"
    part = {"l2": p_l2.with_name(p_l2.name + ".partial"), "l1": p_l1.with_name(p_l1.name + ".partial")}
    writers: dict = {}
    rt = {k: dict(tolerance=PRICE_ROUNDTRIP_TOLERANCE, max_error=0.0, violations=0, rows_checked=0) for k in part}
    inversions = {"l2": 0, "l1": 0}
    last_ts: dict = {"l2": None, "l1": None}
    rows = {"l2": 0, "l1": 0}
    offset = 0
    try:
        for df_raw in _read_raw(csv_path, chunksize=chunk_rows):
            df_raw["source_row"] = np.arange(offset, offset + len(df_raw), dtype=np.int64)
            offset += len(df_raw)
            frames = dict(zip(("l2", "l1"), _frames_from_raw(df_raw, tick_size, div)))
            for k, df in frames.items():
                v = _validate_price_roundtrip(df, tick_size)
                rt[k]["violations"] += v["violations"]
                rt[k]["rows_checked"] += v["rows_checked"]
                rt[k]["max_error"] = max(rt[k]["max_error"], v["max_error"])
                if v["violations"]:
                    raise PriceRoundtripError(
                        f"{session_name}: price fuera de grilla mas alla de tolerancia={PRICE_ROUNDTRIP_TOLERANCE} -- "
                        f"{k.upper()} {v['violations']} filas en el bloque que empieza en la fila "
                        f"{offset - len(df_raw)} (max_error={v['max_error']:.3g})")
                if len(df):
                    ts = df["ts_us"].to_numpy()      # el bloque ya viene en orden de source_row
                    inversions[k] += int(np.sum(np.diff(ts) < 0))
                    if last_ts[k] is not None and ts[0] < last_ts[k]:
                        inversions[k] += 1
                    last_ts[k] = int(ts[-1])
                    t = pa.Table.from_pandas(df.drop(columns=["price"]), preserve_index=False)
                    if k not in writers:
                        writers[k] = pq.ParquetWriter(part[k], t.schema, compression="zstd", compression_level=7)
                    writers[k].write_table(t.cast(writers[k].schema))
                    rows[k] += len(df)
        for w in writers.values():
            w.close()
        writers = {}
        if offset == 0:
            raise ValueError(f"{session_name}: CSV vacio")
        for k, final in (("l2", p_l2), ("l1", p_l1)):
            if not part[k].exists():                  # ese flujo no tuvo filas: tabla vacia con el mismo esquema
                empty = _frames_from_raw(pd.DataFrame({i: pd.Series(dtype=_RAW_DTYPES[i]) for i in range(9)})
                                         .assign(source_row=pd.Series(dtype=np.int64)), tick_size, div)
                df0 = empty[0] if k == "l2" else empty[1]
                pq.write_table(pa.Table.from_pandas(df0.drop(columns=["price"]), preserve_index=False), part[k],
                               compression="zstd", compression_level=7)
            os.replace(part[k], final)
    except BaseException:
        for w in writers.values():
            w.close()
        for f in part.values():
            f.unlink(missing_ok=True)
        raise
    rt_l2, rt_l1 = rt["l2"], rt["l1"]

    manifest = dict(
        schema=L2_SCHEMA, manifest_schema="edgelab_l2_conversion_manifest_v4", session_name=session_name,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        source=dict(path=str(csv_path), bytes=csv_path.stat().st_size, sha256=_sha256_file(csv_path)),
        conversion=dict(
            tick_size=tick_size, tick_size_repr=repr(tick_size),
            subsecond_unit=subsecond_unit, clock_inversions_in_source_order=inversions,
            rounding_policy="numpy.round (round-half-to-even) sobre price/tick_size -> price_tick int32",
            price_roundtrip=dict(
                tolerance=PRICE_ROUNDTRIP_TOLERANCE,
                l2=rt_l2, l1=rt_l1,
                price_column_dropped=True)),
        outputs=dict(
            l2_depth=dict(path=str(p_l2), bytes=p_l2.stat().st_size, rows=rows["l2"], sha256=_sha256_file(p_l2)),
            l1_quotes=dict(path=str(p_l1), bytes=p_l1.stat().st_size, rows=rows["l1"], sha256=_sha256_file(p_l1))),
        reading=dict(mode="chunked", chunk_rows=chunk_rows))
    p_man.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return p_l2, p_l1
