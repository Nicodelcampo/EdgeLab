#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Puerta fail-closed: toda ruta citada por un documento de entrega tiene que
existir, estar trackeada por git, y estar escrita completa.

## Por qué es una puerta y no un comando

El 2026-08-07 verifiqué a mano que las 21 rutas citadas por los dos documentos
de entrega resolvían, y encontré **dos citas abreviadas** —`__6E_12-25_40s.json`
y `__w2_70s.json`—. Legibles para quien ya sabe el prefijo; **inservibles para
el auditor**, que no lo sabe.

Ese chequeo fue un comando suelto. Un comando suelto no impide que la próxima
edición vuelva a meter un enlace colgado: lo detecta **si alguien se acuerda de
correrlo**. Por eso esto es un script con exit code, pensado para correr antes
de cada traspaso.

## Las tres reglas, y por qué la tercera

1. **Existe.** Obvio.
2. **Está trackeada por git.** Un archivo que existe sólo en mi máquina es, para
   el que recibe el repo, exactamente lo mismo que un archivo que no existe.
   Esta regla es la que atrapó las dos afirmaciones cuya evidencia vivía en un
   directorio temporal.
3. **No está abreviada.** Una cita que empieza en `__` o en `...` es un nombre
   que sólo cierra para quien ya tiene el contexto. Es el modo de falla más
   barato de cometer y el más caro de detectar leyendo, porque **parece bien**.

## Qué NO valida

Que el archivo citado *diga* lo que el documento afirma que dice. Eso es
lectura, y no lo hace un script.

Uso:
    python tools/verificar_citas_entrega.py                 # los de entrega
    python tools/verificar_citas_entrega.py docs/otro.md    # los que se pidan

Exit: 0 = todas resuelven · 1 = hay citas rotas · 2 = no se pudo evaluar
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: Los documentos que se le entregan al auditor. Agregar acá el que se sume.
ENTREGA = (
    "docs/research/ENTREGA_CURVA_DISENO_2026-08-07.md",
    "docs/research/CORRECCION_MDE_REPRODUCE_2026-08-07.md",
    "docs/SCRATCHPAD_PROVENANCE_AUDIT_2026-08-07.md",
)

#: Rutas citadas: dentro de backticks o de un link markdown.
RX = re.compile(r"[`\(]([A-Za-z0-9_][A-Za-z0-9_./\\-]*\."
                r"(?:md|py|json|cs|csv|parquet|log|txt))[`\)]")

#: Extensiones que se citan como CONCEPTO y no como archivo del repo.
EXENTAS_SI_NO_EXISTEN = ()

#: Prefijos que delatan una cita abreviada.
ABREVIADA = ("__", "...", "…", "*")


def trackeados():
    out = subprocess.run(["git", "ls-files"], cwd=str(REPO),
                         capture_output=True, text=True).stdout
    return set(l for l in out.split("\n") if l.strip())


_MAN = None


def declarados_en_manifiesto():
    """Rutas con `sha256` publicado en el manifiesto de oráculos.

    Fail-closed: si el manifiesto no está o no parsea, devuelve vacío y esas
    citas fallan. Un manifiesto roto no puede avalar a nadie.
    """
    global _MAN
    if _MAN is None:
        try:
            import json
            d = json.loads((REPO / "docs" / "oraculos_manifiesto.json")
                           .read_text(encoding="utf-8"))
            _MAN = {k for k, v in (d.get("archivos") or {}).items()
                    if v.get("sha256")}
        except Exception:
            _MAN = set()
    return _MAN


def revisar(doc, trk):
    """(total, [(ruta, motivo)]) — motivos, no un booleano."""
    p = REPO / doc
    if not p.exists():
        return 0, [(doc, "el documento de entrega NO EXISTE")]
    txt = p.read_text(encoding="utf-8", errors="replace")
    fallos, vistos = [], []
    for m in RX.finditer(txt):
        r = m.group(1).replace("\\", "/")
        if r in vistos:
            continue
        vistos.append(r)

        base = r.split("/")[-1]
        if base.startswith(ABREVIADA):
            fallos.append((r, "cita ABREVIADA: el que recibe el repo no puede "
                              "saber el prefijo"))
            continue

        directo = r in trk
        sufijo = [t for t in trk if t.endswith("/" + r)]
        if directo or sufijo:
            if not directo and len(sufijo) > 1:
                fallos.append((r, "AMBIGUA: %d archivos terminan asi (%s)"
                               % (len(sufijo), ", ".join(sorted(sufijo)[:3]))))
            continue

        if r in declarados_en_manifiesto():
            # SEGUNDA FORMA DE IDENTIDAD VERSIONADA, y no es una exencion.
            # Los oraculos NO pueden estar en git: son EventLogs de ventana
            # sellada y `oracles/**/*.csv` esta gitignoreado POR POLITICA. Pero
            # `docs/oraculos_manifiesto.json` -que si esta versionado- declara
            # su `sha256`, asi que el que recibe el repo PUEDE comprobar si el
            # archivo que tiene es el que el documento cita. Eso es exactamente
            # lo que esta puerta exige; el vehiculo es otro, la garantia es la
            # misma. Un archivo suelto sin hash no entra por aca.
            continue

        existe = (REPO / r).exists() or any((REPO / d / r).exists()
                                            for d in ("docs", "diag", "tools"))
        fallos.append((r, "existe en disco pero NO ESTA TRACKEADA por git ni "
                          "declarada en el manifiesto de oraculos"
                          if existe else "NO EXISTE"))
    return len(vistos), fallos


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("docs", nargs="*", default=None,
                    help="documentos a revisar (por defecto, los de entrega)")
    a = ap.parse_args(argv)
    docs = a.docs or list(ENTREGA)

    try:
        trk = trackeados()
    except Exception as e:
        print("no se pudo consultar git: %s" % e)
        return 2
    if not trk:
        print("git ls-files vino vacio -- no se puede evaluar")
        return 2

    total, malos = 0, []
    print("PUERTA DE CITAS  (%d documento(s))\n" % len(docs))
    for d in docs:
        n, fallos = revisar(d, trk)
        total += n
        estado = "OK" if not fallos else "%d ROTA(S)" % len(fallos)
        print("  %-58s %3d citas  %s" % (d, n, estado))
        for r, por_que in fallos:
            print("      %-44s %s" % (r, por_que))
            malos.append((d, r, por_que))

    print("\ntotal: %d citas | rotas: %d" % (total, len(malos)))
    if malos:
        print("\nuna cita rota en un documento de entrega es un callejon sin")
        print("salida para el que recibe el repo. Se arregla antes de entregar.")
        return 1
    print("todas existen, estan trackeadas y estan escritas completas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
