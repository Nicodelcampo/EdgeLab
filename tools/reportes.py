#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Índice de los reportes del repo — generado del disco, nunca escrito a mano.

## Qué problema resuelve

Hay 61 documentos en `docs/`. Encontrar «el reporte de la curva» o «qué está
esperando una decisión» exige saber de antemano cómo se llamó el archivo, y los
nombres no siguen una sola convención: conviven `REPORTE_INVESTIGACION_*d..l`
—nueve archivos distinguidos por una letra— con `ENTREGA_*`, `ESPEC_*`, `D2_*`.

**Y hay colisiones de verdad:** `ITERATION_3_OPUS_2026-08-04.md` y
`ITERATION_3_KIMI_2026-08-05.md` son dos «iteración 3» distintas, de días
distintos y de agentes distintos. Pedir «la iteración 3» es ambiguo y nada lo
avisa.

Un índice escrito a mano resuelve eso **hasta que alguien agrega un documento y
no lo actualiza** — que es el mismo modo de falla que este repo persigue en
todas partes: un número publicado cuya derivación nadie puede reconstruir. Por
eso esto se genera: si el archivo está en disco, aparece.

## Qué NO hace

No clasifica por importancia ni decide qué es «el reporte vigente»: para eso
hace falta leerlos. Ordena, fecha y agrupa.

Uso:
    python tools/reportes.py                # indice completo
    python tools/reportes.py --pendientes   # solo lo que espera decision
    python tools/reportes.py --buscar curva
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAICES = ("docs",)

#: La CARPETA manda. `docs/incidents/`, `docs/amendments/`, etc. ya son una
#: clasificación deliberada; adivinarla otra vez desde el nombre del archivo
#: sería tirar información que alguien ya puso.
TEMAS_POR_CARPETA = {
    "docs/incidents": "incidente (acta)",
    "docs/amendments": "enmienda de pre-registro",
    "docs/campaigns": "campaña",
    "docs/predictions": "predicción registrada",
    "docs/parity_coverage": "cobertura de paridad",
    "docs/validation": "validación de gate",
    "docs/spike_in": "spike-in / MDE",
    "docs/referencias": "referencia externa",
    "docs/bridge": "puente NT8",
    "docs/research": "iteración de research",
}

#: Sólo para lo que está suelto en `docs/`. El primero que matchea gana, así que
#: van de lo más específico a lo más general.
TEMAS_POR_NOMBRE = (
    ("contrato / norma",  r"NORTH_STAR|_contract|CONTRATO|ESPEC_|EXPORT_REQ|kernel_|promotion_|event_identity|execution_sim"),
    ("decisión pendiente", r"^D\d_|DECISION|HIPOTESIS_PENDIENTES|SCOPING"),
    ("entrega / resultado", r"ENTREGA|REPORTE_|RESULTADO|CENSO|inventory"),
    ("incidente / aviso",  r"AVISO|INCIDENTE|REVISION|PREFLIGHT|holdout_access|N1_"),
    ("estado / traspaso",  r"ESTADO|HANDOFF|MIGRACION|SESION_"),
)


def imprimible(s):
    """La consola de Windows es cp1252 y se rompe con `→`, `≥`, guiones largos.

    Reventar el índice entero por un carácter del contenido sería absurdo: se
    transliteran los que aparecen de verdad y el resto cae a `?`.
    """
    if s is None:
        return ""
    for a, b in (("→", "->"), ("←", "<-"), ("≥", ">="),
                 ("≤", "<="), ("—", "--"), ("–", "-"),
                 ("…", "..."), ("“", '"'), ("”", '"'),
                 ("‘", "'"), ("’", "'"), ("·", "-")):
        s = s.replace(a, b)
    cod = sys.stdout.encoding or "utf-8"
    return s.encode(cod, "replace").decode(cod)

#: Marcas de que un documento espera algo de una persona. Es una BÚSQUEDA DE
#: TEXTO, no un campo declarado: encuentra lo que está escrito con estas
#: palabras y **se pierde lo que se escribió de otra forma**. Se reporta como
#: búsqueda, no como inventario.
MARCAS_PENDIENTE = (
    r"decisi[óo]n de Nico", r"le toca a Nico", r"es de Nico",
    r"espera(r)? aprobaci[óo]n", r"NO EST[ÁA] TOMADA", r"queda pendiente",
    r"pendiente de decisi[óo]n", r"lo decide Nico", r"no lo decido yo",
)


def fechas_de_git():
    """Última fecha de commit por archivo, en UNA sola pasada.

    Un `git log` por archivo serían 61 subprocesos. Esto es uno.
    """
    fechas = {}
    try:
        out = subprocess.run(
            ["git", "log", "--date=short", "--format=@%ad", "--name-only"],
            cwd=str(REPO), capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return fechas
    actual = None
    for linea in out.splitlines():
        if linea.startswith("@"):
            actual = linea[1:].strip()
        elif linea.strip() and actual:
            fechas.setdefault(linea.strip(), actual)
    return fechas


def titulo_y_proposito(p):
    """Primer `# ` y la primera línea de prosa que le sigue."""
    titulo, proposito = None, None
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            for linea in fh:
                l = linea.rstrip()
                if titulo is None:
                    if l.startswith("# "):
                        titulo = l[2:].strip()
                    continue
                if not l or l.startswith(("#", "|", "```", "---", ">")):
                    continue
                if l.startswith("**") and l.count("**") >= 2 and ":" in l:
                    continue          # bloque de metadatos (Fecha:, Para:, ...)
                proposito = re.sub(r"[*`\[\]]", "", l).strip()
                break
    except Exception:
        pass
    return titulo, proposito


def tema_de(rel):
    carpeta = os.path.dirname(rel)
    if carpeta in TEMAS_POR_CARPETA:
        return TEMAS_POR_CARPETA[carpeta]
    base = os.path.basename(rel)
    for nombre, patron in TEMAS_POR_NOMBRE:
        if re.search(patron, base):
            return nombre
    return "suelto en docs/"


def escanear():
    fechas = fechas_de_git()
    docs = []
    for raiz in RAICES:
        for p in sorted((REPO / raiz).rglob("*.md")):
            rel = p.relative_to(REPO).as_posix()
            t, prop = titulo_y_proposito(p)
            m = re.search(r"(\d{4}-\d{2}-\d{2})", p.name)
            docs.append(dict(
                rel=rel, titulo=t or p.stem, proposito=prop,
                fecha_nombre=m.group(1) if m else None,
                fecha_git=fechas.get(rel), tema=tema_de(rel),
                kb=p.stat().st_size / 1024))
    return docs


#: Nombres cuya repetición es la CONVENCIÓN, no una colisión: un `acta.md` por
#: carpeta de incidente es el diseño correcto, y la carpeta ya desambigua.
#: Marcarlos sería ruido que enseña a ignorar la sección entera.
GENERICOS_POR_CARPETA = {"acta.md", "index.md", "readme.md", "notas.md"}


def colisiones(docs):
    """Nombres que compiten por el mismo referente. Pedir «la iteración 3» tiene
    que ser ambiguo EN VOZ ALTA, no en silencio."""
    por_clave = defaultdict(list)
    for d in docs:
        base = os.path.basename(d["rel"])
        if base.lower() in GENERICOS_POR_CARPETA:
            continue
        # la fecha y el sufijo de una letra se sacan JUNTOS: separados, el
        # `[a-z]?\.md$` suelto convertía `acta.md` en `act.md` y fabricaba una
        # colisión que no existía.
        clave = re.sub(r"_(19|20)\d\d-\d\d-\d\d[a-z]?", "", base)
        clave = re.sub(r"_(OPUS|GPT|KIMI|GROK|CLAUDE|NICO)", "", clave, flags=re.I)
        por_clave[clave].append(d["rel"])
    return {k: sorted(v) for k, v in por_clave.items() if len(v) > 1}


def pendientes(docs):
    rx = re.compile("|".join(MARCAS_PENDIENTE), re.I)
    salida = []
    for d in docs:
        try:
            txt = (REPO / d["rel"]).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        hits = []
        for i, linea in enumerate(txt.splitlines(), 1):
            if rx.search(linea):
                hits.append((i, re.sub(r"\s+", " ", linea.strip())[:150]))
        if hits:
            salida.append((d, hits))
    salida.sort(key=lambda kv: kv[0]["fecha_git"] or "", reverse=True)
    return salida


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pendientes", action="store_true",
                    help="solo los documentos que esperan una decision")
    ap.add_argument("--buscar", metavar="TXT",
                    help="filtra por nombre, titulo o proposito")
    a = ap.parse_args(argv)

    docs = escanear()
    if a.buscar:
        q = a.buscar.lower()
        docs = [d for d in docs
                if q in d["rel"].lower() or q in (d["titulo"] or "").lower()
                or q in (d["proposito"] or "").lower()]

    if a.pendientes:
        pend = pendientes(docs)
        print("DOCUMENTOS QUE ESPERAN UNA DECISION  (%d)" % len(pend))
        print("busqueda de texto sobre %d marcas -- encuentra lo que esta escrito"
              % len(MARCAS_PENDIENTE))
        print("asi, y SE PIERDE lo que se escribio de otra forma.\n")
        for d, hits in pend:
            print("%s  %s" % (d["fecha_git"] or "??????????", imprimible(d["rel"])))
            for i, l in hits[:3]:
                print("    :%-4d %s" % (i, imprimible(l)))
            if len(hits) > 3:
                print("    ... %d mas" % (len(hits) - 3))
            print()
        return 0

    por_tema = defaultdict(list)
    for d in docs:
        por_tema[d["tema"]].append(d)
    orden = ([n for _, n in sorted(TEMAS_POR_CARPETA.items())]
             + [n for n, _ in TEMAS_POR_NOMBRE] + ["suelto en docs/"])
    orden = list(dict.fromkeys(orden))

    print("REPORTES DEL REPO  (%d documentos en %s)"
          % (len(docs), ", ".join(RAICES)))
    print("fecha = ultimo commit que lo toco\n")
    for tema in orden:
        grupo = sorted(por_tema.get(tema, []),
                       key=lambda d: (d["fecha_git"] or "", d["rel"]), reverse=True)
        if not grupo:
            continue
        print("== %s (%d)" % (imprimible(tema).upper(), len(grupo)))
        for d in grupo:
            print("  %s  %-58s %5.0f KB" % (d["fecha_git"] or "??????????",
                                            imprimible(d["rel"]), d["kb"]))
            if d["proposito"]:
                print("              %s" % imprimible(d["proposito"])[:98])
        print()

    col = colisiones(docs)
    if col:
        print("== NOMBRES QUE COLISIONAN")
        print("   pedir uno de estos por nombre corto es AMBIGUO:\n")
        for k, v in sorted(col.items()):
            print("  %s" % imprimible(k))
            for r in v:
                print("      %s" % imprimible(r))
        print()
    print("  --pendientes  lo que espera una decision")
    print("  --buscar TXT  filtra")
    return 0


if __name__ == "__main__":
    sys.exit(main())
