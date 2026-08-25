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

from pathlib import Path
import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

# Rango epoch plausible en MICROSEGUNDOS: 2001-09-09 .. 2065. Sirve de asercion dura
# contra el bug de unidades descripto abajo.
_US_MIN, _US_MAX = 1_000_000_000_000_000, 3_000_000_000_000_000


def _a_microsegundos(serie_ts_str, serie_usec):
    """Epoch en MICROSEGUNDOS como ndarray, independiente de pandas 2/3.

    BUG QUE ESTO ARREGLA (2026-08-21). La version anterior hacia:

        pd.to_datetime(...).astype("int64") // 1000 + usec

    y eso depende de la resolucion que devuelva `to_datetime`:
      - pandas 2.x  -> datetime64[ns] -> astype int64 = ns -> //1000 = us   CORRECTO
      - pandas 3.0.3 -> datetime64[us] -> astype int64 = us -> //1000 = ms  MAL, 1000x

    O sea que el MISMO codigo producia unidades distintas segun la maquina. Los parquets
    del sandbox salieron bien y los de esta maquina salian en milisegundos, con el campo
    de microsegundos sumado encima. Se convierte a [us] EXPLICITAMENTE y se verifica.

    El retorno se fuerza a ``np.ndarray``. Sumar un ndarray y una ``pd.Series`` puede
    devolver una Series; entonces ``ts_us[-1]`` se interpreta como etiqueta -1 y falla
    con RangeIndex. El contrato posicional es necesario para el conversor por chunks.
    """
    dt = pd.to_datetime(serie_ts_str.astype(str), format="%Y%m%d%H%M%S", errors="coerce")
    base_us = dt.values.astype("datetime64[us]").astype(np.int64)
    extra_us = np.asarray(serie_usec, dtype=np.int64)
    us = np.asarray(base_us + extra_us, dtype=np.int64)
    if len(us):
        lo, hi = int(np.min(us)), int(np.max(us))
        if not (_US_MIN <= lo and hi <= _US_MAX):
            raise ValueError(
                "ts_us fuera del rango epoch plausible en microsegundos: [%d, %d]. "
                "Casi seguro un problema de unidades." % (lo, hi))
    return us


def parse_l2_raw_csv(csv_path: str | Path, tick_size: float = 0.00005) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse raw CSV into (df_l2_depth, df_l1_quotes)."""
    csv_path = Path(csv_path)
    df_raw = pd.read_csv(csv_path, sep=";", header=None, names=list(range(9)), low_memory=False)
    # Indice de linea del CSV ORIGINAL, antes de separar L1 de L2: preserva el orden
    # dentro del mismo microsegundo Y el intercalado entre los dos flujos.
    df_raw["source_row"] = np.arange(len(df_raw), dtype=np.int64)

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
    df_l2["usec"] = df_l2["usec"].astype(np.int64)
    if (df_l2["usec"] > 999_999).any():
        df_l2["usec"] = df_l2["usec"] // 10

    df_l2["ts_us"] = _a_microsegundos(df_l2["ts_str"], df_l2["usec"])
    df_l2["price_tick"] = np.round(df_l2["price"] / tick_size).astype(np.int32)
    df_l2.drop(columns=["ts_str", "usec"], inplace=True)

    # 2. L1 Quotes / Top of Book
    m_l1 = df_raw[0] == "L1"
    df_l1 = df_raw[m_l1][[1, 2, 3, 4, 5, "source_row"]].copy()
    df_l1.columns = ["side", "ts_str", "usec", "price", "size", "source_row"]
    df_l1["side"] = df_l1["side"].astype(np.int8)
    df_l1["price"] = df_l1["price"].astype(np.float64)
    df_l1["size"] = df_l1["size"].astype(np.int32)
    df_l1["usec"] = df_l1["usec"].astype(np.int64)
    if (df_l1["usec"] > 999_999).any():
        df_l1["usec"] = df_l1["usec"] // 10

    df_l1["ts_us"] = _a_microsegundos(df_l1["ts_str"], df_l1["usec"])
    df_l1["price_tick"] = np.round(df_l1["price"] / tick_size).astype(np.int32)
    df_l1.drop(columns=["ts_str", "usec"], inplace=True)

    return df_l2, df_l1


def convert_l2_session(csv_path: str | Path, out_dir: str | Path, tick_size: float = 0.00005) -> tuple[Path, Path]:
    """Convert an L2 raw CSV into compressed L2 and L1 Parquet files."""
    csv_path = Path(csv_path)
    out_dir = Path(out_dir)
    session_name = csv_path.stem

    dir_l2 = out_dir / "l2_depth"
    dir_l1 = out_dir / "l1_quotes"
    dir_l2.mkdir(parents=True, exist_ok=True)
    dir_l1.mkdir(parents=True, exist_ok=True)

    df_l2, df_l1 = parse_l2_raw_csv(csv_path, tick_size=tick_size)

    p_l2 = dir_l2 / f"{session_name}.parquet"
    p_l1 = dir_l1 / f"{session_name}.parquet"

    t_l2 = pa.Table.from_pandas(df_l2, preserve_index=False)
    pq.write_table(t_l2, p_l2, compression="zstd", compression_level=7)

    t_l1 = pa.Table.from_pandas(df_l1, preserve_index=False)
    pq.write_table(t_l1, p_l1, compression="zstd", compression_level=7)

    return p_l2, p_l1
