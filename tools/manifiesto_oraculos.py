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
ORACLES = REPO / "oracles"
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
                    help="reescribe el manifiesto con lo que hay en disco")
    a = ap.parse_args(argv)

    if not ORACLES.exists():
        print("no existe %s" % ORACLES)
        return 2
    actual = escanear()

    if a.emitir:
        MANIFIESTO.parent.mkdir(parents=True, exist_ok=True)
        MANIFIESTO.write_text(json.dumps(
            {"schema_version": "oraculos_manifiesto_v1",
             "que_es": "identidad de los oraculos: nombre, bytes, sha256 y la "
                       "linea `# meta`. NO contiene una sola fila de eventos.",
             "por_que": "oracles/ no esta versionado; sin esto dos maquinas "
                        "pueden tener archivos distintos con el mismo nombre y "
                        "nadie se entera. T3a se contesta con un hash.",
             "outcomes_accessed": False,
             "n_archivos": len(actual),
             "archivos": actual},
            indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        print("emitido: %s  (%d archivos)" % (MANIFIESTO.name, len(actual)))
        return 0

    if not MANIFIESTO.exists():
        print("no existe %s — correr con --emitir" % MANIFIESTO.name)
        return 2
    esperado = json.loads(MANIFIESTO.read_text(encoding="utf-8"))["archivos"]

    faltan = sorted(set(esperado) - set(actual))
    sobran = sorted(set(actual) - set(esperado))
    distintos = sorted(k for k in set(esperado) & set(actual)
                       if esperado[k]["sha256"] != actual[k]["sha256"])

    print("manifiesto: %d archivos | en disco: %d" % (len(esperado), len(actual)))
    for k in faltan:
        print("  FALTA      %s  (sha %s…)" % (k, esperado[k]["sha256"][:16]))
    for k in sobran:
        print("  SIN DECLARAR %s  (sha %s…)" % (k, actual[k]["sha256"][:16]))
    for k in distintos:
        print("  DIFIERE    %s\n    manifiesto %s…\n    en disco   %s…"
              % (k, esperado[k]["sha256"][:16], actual[k]["sha256"][:16]))
    if not (faltan or sobran or distintos):
        print("  todo coincide")
        return 0
    # `sobran` no es un error: alguien capturo algo nuevo y todavia no lo
    # declaro. `FALTA` y `DIFIERE` si lo son.
    return 1 if (faltan or distintos) else 0


if __name__ == "__main__":
    sys.exit(main())
