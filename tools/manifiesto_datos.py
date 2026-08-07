#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Identidad de los parquets de `data/` — hashes versionados, contenido afuera.

## Qué problema resuelve

`data/` está gitignoreado entero por política, así que **los 494 MB de ticks no
viajan con el repo**. Eso está bien y no se discute: son datos de mercado, no
código.

Pero deja un agujero que ya mordió antes en otra forma: **dos máquinas pueden
tener archivos distintos con el mismo nombre y nadie se entera.** Pasó con
`runs/censo/manifiesto_universo.json` —dos clones daban veredictos OPUESTOS
sobre si el estudio podía empezar— y la única razón por la que no volvió a pasar
con los oráculos es que se les hizo un manifiesto.

Los parquets de ticks son **la entrada de toda medición**. La sonda ya publica
`input_parquet_sha256`, así que dos corridas sobre datos distintos se detectan
**después** de gastar el cómputo. Esto permite detectarlo **antes**.

## Qué lee, y qué NO

**Lee:** los bytes para el `sha256` y el tamaño. **NO lee una sola fila.** Ni
precios, ni timestamps, ni volumen.

> **Hashear bytes no es leer contenido.** El hash no distingue un parquet de
> ruido; sólo dice si dos archivos son el mismo. Por eso este manifiesto se
> puede versionar sin meter datos de mercado al repo, y sin tocar el firewall
> del holdout — que gobierna qué VENTANAS se pueden mirar, no si dos archivos
> son idénticos.

## Qué NO resuelve

No transporta los datos. Si la otra máquina no los tiene, hay que copiarlos por
fuera de git. Lo que esto da es la certeza de estar copiando **los mismos**.

Uso:
    python tools/manifiesto_datos.py --emitir     # escribe el manifiesto
    python tools/manifiesto_datos.py              # verifica contra el

Exit: 0 = todo coincide · 1 = hay discrepancias · 2 = no se pudo evaluar
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAIZ = REPO / "data" / "nt8"
MANIFIESTO = REPO / "docs" / "datos_manifiesto.json"


def sha_de(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 22), b""):
            h.update(bloque)
    return h.hexdigest()


def escanear():
    filas = {}
    if not RAIZ.is_dir():
        return filas
    for p in sorted(RAIZ.rglob("*.parquet")):
        filas[p.relative_to(REPO).as_posix()] = dict(
            bytes=p.stat().st_size, sha256=sha_de(p))
    return filas


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--emitir", action="store_true",
                    help="reescribe el manifiesto con lo que hay en disco")
    a = ap.parse_args(argv)

    if not RAIZ.is_dir():
        print("no existe %s -- esta maquina no tiene los datos" % RAIZ)
        return 2
    actual = escanear()

    if a.emitir:
        MANIFIESTO.parent.mkdir(parents=True, exist_ok=True)
        MANIFIESTO.write_text(json.dumps(
            {"schema_version": "datos_manifiesto_v1",
             "que_es": "identidad de los parquets de ticks: ruta, bytes y "
                       "sha256. NO contiene una sola fila de datos.",
             "por_que": "data/ esta gitignoreado por politica, asi que los "
                        "parquets no viajan con el repo. Sin esto, dos maquinas "
                        "pueden tener archivos distintos con el mismo nombre y "
                        "nadie se entera -- que es la falla que ya produjo dos "
                        "veredictos opuestos con el manifiesto de universo.",
             "no_transporta": "los datos hay que copiarlos por fuera de git. "
                              "Esto solo da la certeza de estar copiando los "
                              "mismos.",
             "outcomes_accessed": False,
             "n_archivos": len(actual),
             "bytes_totales": sum(v["bytes"] for v in actual.values()),
             "archivos": actual},
            indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        print("emitido: %s  (%d archivos, %.1f MB)"
              % (MANIFIESTO.name, len(actual),
                 sum(v["bytes"] for v in actual.values()) / 1e6))
        return 0

    if not MANIFIESTO.exists():
        print("no existe %s -- correr con --emitir" % MANIFIESTO.name)
        return 2
    esperado = json.loads(MANIFIESTO.read_text(encoding="utf-8"))["archivos"]

    faltan = sorted(set(esperado) - set(actual))
    sobran = sorted(set(actual) - set(esperado))
    distintos = sorted(k for k in set(esperado) & set(actual)
                       if esperado[k]["sha256"] != actual[k]["sha256"])

    print("manifiesto: %d archivos | en disco: %d" % (len(esperado), len(actual)))
    for k in faltan:
        print("  FALTA        %s  (sha %s...)" % (k, esperado[k]["sha256"][:16]))
    for k in sobran:
        print("  SIN DECLARAR %s  (sha %s...)" % (k, actual[k]["sha256"][:16]))
    for k in distintos:
        print("  DIFIERE      %s\n    manifiesto %s...\n    en disco   %s..."
              % (k, esperado[k]["sha256"][:16], actual[k]["sha256"][:16]))
    if not (faltan or sobran or distintos):
        print("  todo coincide -- esta maquina tiene los MISMOS datos")
        return 0
    # `sobran` no es error: alguien capturo un contrato nuevo y no lo declaro.
    # `FALTA` y `DIFIERE` si lo son: la medicion no seria comparable.
    return 1 if (faltan or distintos) else 0


if __name__ == "__main__":
    sys.exit(main())
