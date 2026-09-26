#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconstruye el parquet canónico F2 desde el `.Last.txt` de NT8.

## Por qué hay que reescribir esta herramienta

El manifiesto de los parquets dice `tool = build_nt8_ticks` y
`source_file = C:\\ProyectosQuant\\EdgeLab\\TickData\\...` — se corrió en otra
máquina y nunca entró al repo. Un pipeline cuya primera etapa no es reproducible
no es un pipeline: es un archivo con historia oral.

## Por qué hay que reconstruir los parquets (2026-07-27)

Los exports de NT8 del **21-jul** traían el defecto de duplicación de bloque. Se
demostró comparando fuente contra parquet día por día: **diferencia cero en 19
días** — el parquet reproduce el archivo exacto, así que el defecto venía de
arriba. Los exports nuevos del **27-jul** están limpios:

| | export 21-jul | export 27-jul |
|---|---|---|
| 6E 09-26 · 2026-06-19 | 50.906 ticks, 9.615 bloques duplicados | **41.036, cero** |
| 6E 06-26 · 2026-05-27 | 77.209 ticks | **74.701, cero** |

Los 9.870 ticks que desaparecieron del 06-19 son exactamente la separación del
bloque duplicado detectado. Coincide, no se parece.

## El contrato de transformación — copiado del manifiesto original

No se inventa ninguna regla nueva: la semántica de F2 está validada contra 7
oráculos de paridad y cambiarla rompería todo lo sellado.

1. Parseo `.Last.txt`: `yyyyMMdd HHmmss fffffff;last;bid;ask;vol`, fracción en
   unidades de **100 ns** (7 dígitos).
2. `ts_utc_ns = ts_local_ns`, offset 0 — UTC verificado en el manifiesto
   original por ajuste de calendario CME consciente de DST.
3. Precios a **ticks enteros** con `round(p / tick_size)`.
4. `sequence` y `source_row` = orden estable del archivo. **Sin dedup, sin
   reordenar**: si el archivo trae dos ticks idénticos, van los dos. Deduplicar
   acá escondería justo la clase de defecto que el censo busca.
5. **Sin empalme ni ajuste de precios.**
6. `aggressor`: `buy` si `price_ticks >= ask_ticks`, `sell` si
   `price_ticks <= bid_ticks`. Verificado sobre el parquet original: 2.085.208
   ticks, cero casos intermedios.

Uso:
  .venv/Scripts/python tools/build_nt8_ticks.py \
      --source "data/nt8/6E/6E 09-26.Last.txt" \
      --instrument 6E --contract "6E 09-26" --tick-size 0.00005 \
      --out data/nt8/6E_v2
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

EPOCH = np.datetime64("1970-01-01T00:00:00", "ns")


def sha256(path, bloque=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(bloque), b""):
            h.update(b)
    return h.hexdigest()


def parsear_lote(df):
    """Un lote crudo -> arrays canónicos. Todo vectorizado, sin bucles de Python.

    El parseo por línea con `float()` y `np.datetime64()` uno por uno funcionaba
    con los 5 M de ticks de 6E, pero un contrato de ES trae ~80 M en 3,4 GB: las
    listas de Python son ~32 bytes por objeto, o sea del orden de 16 GB sólo en
    overhead antes de convertir a numpy. Con 16 GB de RAM y un atlas corriendo,
    eso no termina.
    """
    t = df[0].astype(str)
    # 'yyyyMMdd HHmmss fffffff' -> ns UTC. La fraccion son unidades de 100 ns:
    # 7 digitos, no microsegundos.
    base = pd.to_datetime(t.str.slice(0, 15), format="%Y%m%d %H%M%S", errors="coerce")
    frac = pd.to_numeric(t.str.slice(16, 23), errors="coerce")
    ok = base.notna() & frac.notna() & df[1].notna() & df[4].notna()
    malas = int((~ok).sum())
    if malas:
        df, base, frac = df[ok], base[ok], frac[ok]
    ts = base.values.astype("datetime64[ns]").astype(np.int64) + frac.values.astype(np.int64) * 100
    return (ts, df[1].values.astype(np.float64), df[2].values.astype(np.float64),
            df[3].values.astype(np.float64), df[4].values.astype(np.int32), malas)


CATS = ["buy", "sell", "unclassified"]


def construir(source, instrument, contract, tick_size, out_dir, filas_por_lote=2_000_000):
    """Streaming: lote -> parquet, sin tener el archivo entero en memoria."""
    import pyarrow as pa
    import pyarrow.parquet as pq_

    os.makedirs(out_dir, exist_ok=True)
    base = contract.replace(" ", "_")
    pq_path = os.path.join(out_dir, "%s_ticks.parquet" % base)
    src_abs = os.path.abspath(source)

    n = malas = n_medio = desorden = 0
    max_err = 0.0
    ultimo_ts = None
    escritor = None
    lector = pd.read_csv(source, sep=";", header=None, dtype={0: str},
                         chunksize=filas_por_lote, engine="c",
                         names=list(range(5)), on_bad_lines="skip")
    try:
        for lote in lector:
            ts, last, bid, ask, vol, m = parsear_lote(lote)
            malas += m
            k = len(ts)
            if not k:
                continue

            def a_ticks(x):
                t = np.round(x / tick_size)
                return t.astype(np.int64), float(np.abs(x / tick_size - t).max())

            px, e1 = a_ticks(last)
            bd, e2 = a_ticks(bid)
            ak, e3 = a_ticks(ask)
            max_err = max(max_err, e1, e2, e3)
            # FAIL-LOUD: si un precio no cae en la grilla, el tick_size esta mal
            # y todo lo que siga seria basura silenciosa.
            if max_err > 1e-6:
                raise SystemExit("FAIL: precio fuera de la grilla de %s (error max "
                                 "%.3e). tick_size equivocado?" % (tick_size, max_err))
            cruzado = int((bd > ak).sum())
            if cruzado:
                raise SystemExit("FAIL: %d ticks con bid > ask. Eso no es un libro "
                                 "posible: el archivo esta corrupto." % cruzado)

            # Regla del constructor ORIGINAL, verificada sobre los 5 parquets
            # viejos: dentro del spread NO se adivina, se marca `unclassified`.
            # La primera version abortaba ante el caso porque el unico parquet
            # inspeccionado (6E 09-26) era justo el que no tenia ninguno.
            cod = np.where(px >= ak, 0, np.where(px <= bd, 1, 2)).astype(np.int8)
            n_medio += int((cod == 2).sum())

            if ultimo_ts is not None and ts[0] < ultimo_ts:
                desorden += 1
            desorden += int((np.diff(ts) < 0).sum())
            ultimo_ts = ts[-1]

            seq = np.arange(n, n + k, dtype=np.int64)
            tabla = pa.table({
                "ts_utc_ns": ts, "ts_local_ns": ts, "sequence": seq,
                "price_ticks": px, "bid_ticks": bd, "ask_ticks": ak,
                "volume": vol,
                "aggressor": pa.DictionaryArray.from_arrays(
                    pa.array(cod, pa.int8()), pa.array(CATS)).cast(pa.string()),
                "tick_type": pa.array(["trade"] * k),
                "instrument": pa.array([instrument] * k),
                "contract": pa.array([contract] * k),
                "source_file": pa.array([src_abs] * k),
                "source_row": seq})
            if escritor is None:
                escritor = pq_.ParquetWriter(pq_path, tabla.schema, compression="snappy")
            escritor.write_table(tabla)
            n += k
    finally:
        if escritor is not None:
            escritor.close()
    if not n:
        raise SystemExit("FAIL: el archivo no tiene ticks parseables")
    man = dict(
        schema_version="canonical_tick_v1", tool="build_nt8_ticks",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        source_file=os.path.abspath(source), source_sha256=sha256(source),
        instrument=instrument, contract=contract, rows=int(n),
        tick_size=tick_size,
        tz=dict(declared_tz="UTC", canonical_offset_s=0,
                note=("offset 0 heredado del manifiesto original, donde se "
                      "verifico por ajuste de calendario CME DST-aware. NO se "
                      "re-verifica aca: cambiar el offset moveria la semantica "
                      "de F2 y rompe 7 oraculos de paridad sellados.")),
        transformations=[
            "parseo .Last.txt (yyyyMMdd HHmmss fffffff;last;bid;ask;vol), frac 100ns",
            "ts_utc_ns = ts_local_ns (offset 0)",
            "precios -> ticks enteros (round(p/%s)), error max %.3e" % (tick_size, max_err),
            "sequence/source_row = orden estable del archivo (sin dedup, sin reorden)",
            "aggressor: buy si px>=ask, sell si px<=bid, unclassified en medio",
            "SIN empalme ni ajuste de precios (por contrato)"],
        controles=dict(lineas_no_parseadas=int(malas),
                       timestamps_no_monotonos=desorden,
                       error_max_grilla=max_err,
                       ticks_unclassified=n_medio),
        parquet_sha256=sha256(pq_path))
    with open(os.path.join(out_dir, "%s_manifest.json" % base), "w",
              encoding="utf-8") as fh:
        json.dump(man, fh, indent=1, ensure_ascii=False)
    return pq_path, man


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--instrument", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--tick-size", type=float, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    p, man = construir(a.source, a.instrument, a.contract, a.tick_size, a.out)
    print("%-14s %9d ticks  no_parseadas=%d  desorden=%d  unclassified=%d  -> %s"
          % (a.contract, man["rows"], man["controles"]["lineas_no_parseadas"],
             man["controles"]["timestamps_no_monotonos"],
             man["controles"]["ticks_unclassified"], os.path.basename(p)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
