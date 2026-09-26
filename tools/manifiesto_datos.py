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
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools._manifiesto_comun import (  # noqa: E402
    declarado_en_git, emitir, informar, sha_de,
)

RAIZ = REPO / "data" / "nt8"
CABECERA = dict(
    schema_version="datos_manifiesto_v2",
    que_es="identidad de los parquets de ticks: ruta, bytes y sha256. NO "
           "contiene una sola fila de datos.",
    por_que="data/ esta gitignoreado por politica, asi que los parquets no "
            "viajan con el repo. Sin esto dos maquinas pueden tener archivos "
            "distintos con el mismo nombre y nadie se entera.",
    v2="--emitir FUSIONA en vez de reemplazar. La v1 reescribia el manifiesto "
       "entero con lo que hubiera en disco, asi que una maquina parcial "
       "BORRABA las declaraciones de la otra: el 2026-08-09 cayo de 31 a 11 y "
       "ES/NQ -- los de la replicacion -- dejaron de estar declarados.",
    no_transporta="los datos hay que copiarlos por fuera de git. Esto solo da "
                  "la certeza de estar copiando los mismos.",
    outcomes_accessed=False)

MANIFIESTO = REPO / "docs" / "datos_manifiesto.json"


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
                    help="FUSIONA lo que hay en disco con lo ya declarado. "
                         "Nunca borra una declaracion en silencio.")
    ap.add_argument("--exigir-completo", action="store_true",
                    help="que FALTA tambien falle: para cuando SI hace falta el "
                         "conjunto entero en esta maquina")
    ap.add_argument("--retirar", nargs="*", default=[],
                    help="retirar declaraciones POR RUTA, explicito y a proposito")
    a = ap.parse_args(argv)

    if not RAIZ.exists():
        print("no existe %s -- esta maquina no tiene archivos" % RAIZ)
        return 2
    actual = escanear()

    previo = {}
    if MANIFIESTO.exists():
        try:
            previo = json.loads(MANIFIESTO.read_text(encoding="utf-8"))["archivos"]
        except Exception:
            previo = {}

    if a.emitir:
        MANIFIESTO.parent.mkdir(parents=True, exist_ok=True)
        fus, solo_previo, cambiados, retirados = emitir(
            MANIFIESTO, CABECERA, actual, previo, a.retirar)
        print("emitido: %s  (%d declarados)" % (MANIFIESTO.name, len(fus)))
        print("  en este disco        %d" % len(actual))
        if cambiados:
            print("  ACTUALIZADOS -- mismo nombre, otros bytes: %d" % len(cambiados))
            for k in cambiados[:10]:
                print("     %s" % k)
        if solo_previo:
            print("  CONSERVADOS de la declaracion previa -- no estan en este")
            print("  disco, casi seguro los tiene la otra maquina: %d" % len(solo_previo))
            for k in solo_previo[:10]:
                print("     %s" % k)
            print("  (para sacarlos de verdad: --retirar <ruta>)")
        if retirados:
            print("  RETIRADOS explicitamente: %s" % retirados)
        return 0

    if not previo:
        print("no existe %s -- correr con --emitir" % MANIFIESTO.name)
        return 2

    # CONTROL DE ANGOSTAMIENTO: comparar contra la version COMMITEADA. Comparar
    # solo contra el disco no alcanza -- una maquina parcial se ve identica a un
    # conjunto que encogio.
    rel = "docs/datos_manifiesto.json"
    en_git = declarado_en_git(REPO, rel)
    perdidas = sorted(set(en_git) - set(previo))
    return informar(previo, actual, "archivos", perdidas,
                    exigir_completo=a.exigir_completo)


if __name__ == "__main__":
    sys.exit(main())
