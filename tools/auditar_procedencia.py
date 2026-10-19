#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Barre un directorio temporal y busca evidencia que sostenga afirmaciones vivas.

## Por qué existe

Preparando un traspaso se encontró que **dos afirmaciones publicadas dentro de
un artefacto versionado** —la equivalencia de workers y el 99 %/97 % del reloj—
tenían su evidencia en un directorio temporal que se borra solo. Las dos se
recuperaron **por casualidad**, porque quedaban archivos en disco.

Un barrido parcial que encuentra dos ya justifica el barrido completo: eleva la
probabilidad de que haya más, no la baja.

## Qué hace, y qué NO

**Hace la parte mecánica**: hashea, clasifica por forma —script de parche,
salida de corrida, borrador— y busca, para cada archivo, si el repo lo menciona
o si alguna cifra suya aparece publicada.

**No decide.** La clasificación A/B/C/D/E es un juicio y lo firma una persona:
un archivo puede sostener una afirmación sin compartir un solo número literal
con ella. Este script produce las **señales**; el veredicto va al acta.

## Las señales que emite

`escribe_en_repo`   el `.py` escribe dentro del repo -> es un PARCHE, y su
                    resultado ya está versionado. El script es un medio.
`mencionado`        el nombre del archivo aparece en el repo.
`cifras_publicadas` números distintivos del archivo que aparecen en `docs/`.
`gemelo_versionado` un archivo versionado con el mismo `sha256`.
`schema`            para JSON, el `schema_version` -> con qué script se hizo.

Uso:
    python tools/auditar_procedencia.py <dir_temporal>
    python tools/auditar_procedencia.py <dir_temporal> --json salida.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
#: Dónde se buscan menciones y cifras. `docs/` y el código; no `data/`.
BUSCAR_EN = ("docs", "diag", "tools", "edgelab", "tests", "runs")


def versionados():
    out = subprocess.run(["git", "ls-files"], cwd=str(REPO),
                         capture_output=True, text=True).stdout
    return [l for l in out.split("\n") if l.strip()]


def sha_de(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def texto_del_repo():
    """Todo el texto buscable del repo, una sola vez."""
    trozos = []
    for base in BUSCAR_EN:
        d = REPO / base
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in (
                    ".md", ".py", ".json", ".txt", ".cs"):
                continue
            if "__pycache__" in p.parts:
                continue
            try:
                trozos.append(p.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                pass
    return "\n".join(trozos)


def cifras_distintivas(p, limite=12):
    """Números poco comunes del archivo — los que servirían para rastrearlo.

    Se descartan los chicos (< 1.000): un `12` o un `0,5` aparecen en cualquier
    lado y producirían coincidencias que no significan nada.
    """
    try:
        txt = Path(p).read_text(encoding="utf-8", errors="replace")[:400_000]
    except Exception:
        return []
    vistos, fuera = [], set()
    for m in re.finditer(r"\b\d{4,}\b", txt):
        v = m.group(0)
        if v in fuera or v.startswith(("19", "20")):   # años y fechas: ruido
            continue
        fuera.add(v)
        vistos.append(v)
        if len(vistos) >= limite * 6:
            break
    return vistos[:limite * 6]


def auditar(dtemp):
    d = Path(dtemp)
    if not d.is_dir():
        print("no existe el directorio %s" % d)
        return None
    trk = versionados()
    por_sha = {}
    for r in trk:
        f = REPO / r
        if f.is_file() and f.stat().st_size < 8_000_000:
            try:
                por_sha.setdefault(sha_de(f), []).append(r)
            except Exception:
                pass
    texto = texto_del_repo()

    filas = []
    for p in sorted(d.iterdir()):
        if not p.is_file():
            continue
        b = p.read_bytes()
        h = hashlib.sha256(b).hexdigest()
        try:
            txt = b.decode("utf-8", "replace")
        except Exception:
            txt = ""
        fila = dict(nombre=p.name, bytes=len(b), sha256=h,
                    mencionado=p.name in texto,
                    gemelo_versionado=por_sha.get(h, []),
                    escribe_en_repo=bool(re.search(
                        r'(io\.open|open|write_text|Path)\s*\(?\s*r?["\'][^"\']*'
                        r'E:[\\/]{1,2}EdgeLab', txt)) if p.suffix == ".py" else False)
        if p.suffix == ".json":
            try:
                j = json.loads(b)
                fila["schema"] = (j.get("schema_version")
                                  if isinstance(j, dict) else None)
                if isinstance(j, dict):
                    fila["claves"] = sorted(j)[:8]
            except Exception:
                fila["schema"] = "(no parsea)"
        # cifras del archivo que aparecen publicadas en el repo
        pub = [v for v in cifras_distintivas(p) if v in texto]
        fila["cifras_publicadas"] = sorted(set(pub))[:10]
        filas.append(fila)
    return filas


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dir_temporal")
    ap.add_argument("--json", help="escribe el inventario crudo a un archivo")
    a = ap.parse_args(argv)

    filas = auditar(a.dir_temporal)
    if filas is None:
        return 2

    parches = [f for f in filas if f.get("escribe_en_repo")]
    gemelos = [f for f in filas if f["gemelo_versionado"]]
    con_cifras = [f for f in filas if f["cifras_publicadas"]
                  and not f.get("escribe_en_repo")]
    mencionados = [f for f in filas if f["mencionado"]]

    print("INVENTARIO  %d archivos en %s\n" % (len(filas), a.dir_temporal))
    print("  %-40s %s" % ("escriben en el repo (son PARCHES)", len(parches)))
    print("  %-40s %s" % ("tienen gemelo versionado (mismo sha)", len(gemelos)))
    print("  %-40s %s" % ("mencionados por nombre en el repo", len(mencionados)))
    print("  %-40s %s" % ("con cifras que aparecen publicadas", len(con_cifras)))

    print("\n== CANDIDATOS A REVISAR A MANO (cifras publicadas, no son parches)")
    print("   son SENALES, no veredictos: un archivo puede sostener una")
    print("   afirmacion sin compartir un numero literal con ella.\n")
    for f in sorted(con_cifras, key=lambda f: -len(f["cifras_publicadas"])):
        print("  %-30s %8d b  sha %s" % (f["nombre"], f["bytes"], f["sha256"][:12]))
        print("      cifras: %s" % ", ".join(f["cifras_publicadas"][:8]))
        if f.get("schema"):
            print("      schema: %s" % f["schema"])

    if gemelos:
        print("\n== YA VERSIONADOS (mismo sha256, no hay nada que rescatar)")
        for f in gemelos:
            print("  %-30s -> %s" % (f["nombre"], ", ".join(f["gemelo_versionado"])))

    if a.json:
        Path(a.json).write_text(json.dumps(filas, indent=1, ensure_ascii=False)
                                + "\n", encoding="utf-8")
        print("\n-> %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
