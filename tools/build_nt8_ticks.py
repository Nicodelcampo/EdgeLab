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


def parsear(path):
    """`.Last.txt` -> arrays. Una sola pasada, sin cargar el texto entero."""
    ts, last, bid, ask, vol = [], [], [], [], []
    malas = 0
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for linea in fh:
            p = linea.rstrip("\r\n").split(";")
            if len(p) < 5 or len(p[0]) < 16:
                malas += 1
                continue
            t = p[0]
            try:
                # 'yyyyMMdd HHmmss fffffff' -> ns UTC. La fraccion son unidades
                # de 100 ns: 7 digitos, no microsegundos.
                ns = (int(np.datetime64("%s-%s-%sT%s:%s:%s" % (
                    t[0:4], t[4:6], t[6:8], t[9:11], t[11:13], t[13:15]), "ns")
                    .astype("int64")) + int(t[16:23].ljust(7, "0")) * 100)
                ts.append(ns); last.append(float(p[1])); bid.append(float(p[2]))
                ask.append(float(p[3])); vol.append(int(p[4]))
            except (ValueError, IndexError):
                malas += 1
    return (np.array(ts, dtype=np.int64), np.array(last), np.array(bid),
            np.array(ask), np.array(vol, dtype=np.int32), malas)


def construir(source, instrument, contract, tick_size, out_dir):
    ts, last, bid, ask, vol, malas = parsear(source)
    n = len(ts)
    if not n:
        raise SystemExit("FAIL: el archivo no tiene ticks parseables")

    def a_ticks(x):
        t = np.round(x / tick_size)
        err = np.abs(x / tick_size - t)
        return t.astype(np.int64), float(err.max())

    px, e1 = a_ticks(last)
    bd, e2 = a_ticks(bid)
    ak, e3 = a_ticks(ask)
    max_err = max(e1, e2, e3)
    # FAIL-LOUD: si un precio no cae en la grilla, el tick_size esta mal y todo
    # lo que siga seria basura silenciosa.
    if max_err > 1e-6:
        raise SystemExit("FAIL: precio fuera de la grilla de %s (error max %.3e). "
                         "tick_size equivocado?" % (tick_size, max_err))

    # Regla del constructor ORIGINAL, verificada sobre los 5 parquets viejos:
    # dentro del spread NO se adivina, se marca `unclassified`. En 6E 09-26 no
    # habia ninguno; en los otros cuatro hay entre 10 y 70 sobre millones. La
    # primera version de esto abortaba ante el caso porque el unico parquet que
    # se habia inspeccionado era el que no lo tenia.
    agresor = np.where(px >= ak, "buy", np.where(px <= bd, "sell", "unclassified"))
    n_medio = int((agresor == "unclassified").sum())
    cruzado = int((bd > ak).sum())
    if cruzado:
        raise SystemExit("FAIL: %d ticks con bid > ask. Eso no es un libro "
                         "posible: el archivo esta corrupto." % cruzado)

    seq = np.arange(n, dtype=np.int64)
    df = pd.DataFrame(dict(
        ts_utc_ns=ts, ts_local_ns=ts, sequence=seq,
        price_ticks=px, bid_ticks=bd, ask_ticks=ak,
        volume=vol, aggressor=agresor, tick_type="trade",
        instrument=instrument, contract=contract,
        source_file=os.path.abspath(source), source_row=seq))

    os.makedirs(out_dir, exist_ok=True)
    base = contract.replace(" ", "_")
    pq_path = os.path.join(out_dir, "%s_ticks.parquet" % base)
    df.to_parquet(pq_path, index=False)

    desorden = int((np.diff(ts) < 0).sum())
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
