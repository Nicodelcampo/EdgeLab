#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manifiesto de identidad de `oracles/` — hashes versionados, contenido afuera.

## Qué problema resuelve

`oracles/*.csv` no está versionado, así que en un clon limpio **T3a no se puede
verificar**: no hay contra qué comparar. Y peor —el problema que muerde de
verdad— **dos máquinas pueden tener archivos distintos con el mismo nombre y
nadie se entera**. Eso ya pasó con `runs/censo/manifiesto_universo.json`: dos
clones de la misma máquina daban veredictos OPUESTOS sobre si el estudio podía
empezar, y no había hash que lo delatara.

## Qué lee, y qué NO

**Lee:** los bytes para el `sha256`, el tamaño, y la línea `# meta` — que es
configuración del indicador, no mercado.

**NO lee una sola fila de eventos.** Ni timestamps, ni zonas, ni precios.

Eso es deliberado: **T3a es una pregunta de IDENTIDAD**, y la contesta un hash.
La ventana temporal sería lindo tenerla, pero exigiría leer filas de archivos
cuya ventana está sellada — y no hace falta para el propósito. Menos lectura
para el mismo resultado.

> **Hashear bytes no es leer contenido.** El hash no distingue un EventLog de
> ruido; sólo dice si dos archivos son el mismo. Por eso este manifiesto se
> puede versionar sin meter material del holdout al repo.

## Qué NO resuelve

P5 sigue necesitando el archivo en la máquina. Pero eso ya era cierto y ya está
gateado: su ventana cae dentro del sello, así que exige la fila en
`docs/holdout_access_log.md`. Este manifiesto no cambia ese gate — hace que
«¿tengo el archivo correcto?» se pueda contestar **antes** de pedirlo.

Uso:
    python tools/manifiesto_oraculos.py --emitir     # escribe el manifiesto
    python tools/manifiesto_oraculos.py              # verifica contra él

Exit: 0 = todo coincide · 1 = hay discrepancias · 2 = no se pudo evaluar
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools._manifiesto_comun import (  # noqa: E402
    declarado_en_git, emitir, informar, sha_de,
)

ORACLES = REPO / "oracles"
CABECERA = dict(
    schema_version="oraculos_manifiesto_v2",
    que_es="identidad de los oraculos: nombre, bytes, sha256 y la linea "
           "`# meta`. NO contiene una sola fila de eventos.",
    por_que="oracles/ no esta versionado; sin esto dos maquinas pueden tener "
            "archivos distintos con el mismo nombre y nadie se entera.",
    v2="--emitir FUSIONA en vez de reemplazar. La v1 reescribia el manifiesto "
       "entero, asi que una maquina parcial BORRABA las declaraciones de la "
       "otra: el 2026-08-09 cayo de 28 a 19.",
    outcomes_accessed=False)

MANIFIESTO = REPO / "docs" / "oraculos_manifiesto.json"
EXTS = (".csv", ".txt")


def meta_de(path):
    """Primera línea `# meta` del archivo. Configuración, no mercado.

    Se lee sólo el arranque: si no hay `# meta` en las primeras líneas, se
    devuelve None en vez de seguir buscando dentro del cuerpo del log.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for _ in range(3):
                l = fh.readline()
                if not l:
                    break
                if l.startswith("# meta"):
                    return l.strip()
    except Exception:
        pass
    return None


def escanear():
    filas = {}
    for p in sorted(ORACLES.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in EXTS:
            continue
        b = p.read_bytes()
        rel = p.relative_to(REPO).as_posix()
        filas[rel] = dict(bytes=len(b),
                          sha256=hashlib.sha256(b).hexdigest(),
                          meta=meta_de(p))
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

    if not ORACLES.exists():
        print("no existe %s -- esta maquina no tiene archivos" % ORACLES)
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
    rel = "docs/oraculos_manifiesto.json"
    en_git = declarado_en_git(REPO, rel)
    perdidas = sorted(set(en_git) - set(previo))
    return informar(previo, actual, "archivos", perdidas,
                    exigir_completo=a.exigir_completo)


if __name__ == "__main__":
    sys.exit(main())
