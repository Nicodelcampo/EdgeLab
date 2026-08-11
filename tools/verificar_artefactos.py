# -*- coding: utf-8 -*-
"""Revisión read-only de procedencia: cada artefacto citado en
`docs/REGISTRO_NO_MEDIDO_2026-08-10.md` §1 MEDIDO existe, está trackeado en
git, y (para JSON) su `payload_sha256` declarado coincide con una
recomputación fresca, y su `code_commit`/`head_start` es un commit real.

## Por qué existe

Nace de la revisión pedida el 2026-08-10 tras descubrir ramas paralelas del
auditor: antes de confiar en cualquier cosa que este repo afirma haber
medido, verificar que el artefacto que lo respalda sigue siendo lo que dice
ser. Encontró de entrada una cita real: `REGISTRO...md` M13 apuntaba al
artefacto PRE-corrección de F1.1 (`ac9d001dc815`), no al corregido
(`260757be9e71`) que sostiene los números publicados.

## Qué NO hace

No corrige nada solo. No decide si un hash-mismatch importa — lo publica
como señal para revisión humana. Un `payload_sha256` que no verifica pero
con `git diff` vacío desde su único commit no es evidencia de tampereo (no
cambió desde que se generó); es evidencia de que el hash declarado nunca
coincidió con su propio contenido, algo distinto y anterior al commit.

Uso:
    ./.venv/Scripts/python.exe tools/verificar_artefactos.py
    ./.venv/Scripts/python.exe tools/verificar_artefactos.py --json salida.json
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
REGISTRO = REPO / "docs" / "REGISTRO_NO_MEDIDO_2026-08-10.md"


def sh(*args):
    return subprocess.run(["git", "-C", str(REPO), *args],
                          capture_output=True, text=True).stdout.strip()


def es_commit_real(h):
    r = subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", h + "^{commit}"],
                       capture_output=True, text=True)
    return r.returncode == 0


def diff_vacio(ruta_relativa):
    return sh("diff", "HEAD", "--", ruta_relativa) == ""


def artefactos_citados():
    texto = REGISTRO.read_text(encoding="utf-8")
    m = re.search(r"## 1\. MEDIDO.*?(?=\n## 2\.)", texto, re.S)
    seccion1 = m.group(0) if m else texto
    return sorted(set(re.findall(r"`([A-Za-z0-9_.\-/]+\.(?:json|md))`", seccion1)))


def verificar():
    tracked = set(sh("ls-files").splitlines())
    nombres = artefactos_citados()
    filas = []
    for nombre in nombres:
        candidatos = [p for p in REPO.rglob(nombre) if ".git" not in p.parts]
        if not candidatos:
            filas.append(dict(nombre=nombre, estado="FALTA_EN_DISCO"))
            continue
        p = candidatos[0]
        rel = str(p.relative_to(REPO)).replace("\\", "/")
        if rel not in tracked:
            filas.append(dict(nombre=nombre, ruta=rel, estado="NO_TRACKEADO"))
            continue

        fila = dict(nombre=nombre, ruta=rel, estado="OK")
        if nombre.endswith(".json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                filas.append(dict(nombre=nombre, ruta=rel, estado="NO_PARSEA",
                                  detalle=str(e)))
                continue
            declarado = data.pop("payload_sha256", None)
            # P2 (2026-08-11): scripts de eras distintas usaron ensure_ascii
            # distinto (la convencion ensure_ascii=False no siempre fue la
            # norma -- ver docs/P2_SEIS_HASHES_ADJUDICACION_2026-08-11.md).
            # Probar ambas variantes antes de declarar MISMATCH evita un
            # falso positivo determinista que este script tenia.
            recalcs = {
                ea: hashlib.sha256(
                    json.dumps(data, sort_keys=True, ensure_ascii=ea, default=str)
                    .encode()).hexdigest()
                for ea in (False, True)
            }
            if declarado is None:
                fila["hash"] = "SIN_PAYLOAD_SHA256"
            elif declarado in recalcs.values():
                fila["hash"] = "OK"
            else:
                fila["hash"] = "MISMATCH"
                fila["declarado"] = declarado[:16]
                fila["recalculado"] = recalcs[False][:16]
                fila["estable_desde_commit"] = diff_vacio(rel)

            commit = data.get("code_commit") or data.get("head_start")
            if commit:
                fila["code_commit_real"] = es_commit_real(commit)
        filas.append(fila)
    return filas


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", help="escribe el detalle crudo a un archivo")
    a = ap.parse_args(argv)

    filas = verificar()
    faltan = [f for f in filas if f["estado"] in ("FALTA_EN_DISCO", "NO_TRACKEADO", "NO_PARSEA")]
    sin_hash = [f for f in filas if f.get("hash") == "SIN_PAYLOAD_SHA256"]
    mismatch = [f for f in filas if f.get("hash") == "MISMATCH"]
    commit_falso = [f for f in filas if f.get("code_commit_real") is False]

    print("Artefactos citados en REGISTRO %s1 MEDIDO: %d" % (chr(167), len(filas)))
    print("  limpios (existen, trackeados, hash OK donde aplica): %d"
          % (len(filas) - len(faltan) - len(mismatch)))

    if faltan:
        print("\nFALTAN / NO TRACKEADOS / NO PARSEAN (%d):" % len(faltan))
        for f in faltan:
            print("  - %-55s %s %s" % (f["nombre"], f["estado"], f.get("detalle", "")))
    if sin_hash:
        print("\nSIN payload_sha256 -- predatan la convencion, no es corrupcion (%d):"
              % len(sin_hash))
        for f in sin_hash:
            print("  - %s" % f["nombre"])
    if mismatch:
        print("\nHASH NO COINCIDE (%d) -- ver 'estable_desde_commit':" % len(mismatch))
        for f in mismatch:
            estable = "estable desde su commit (no tamperado)" if f["estable_desde_commit"] \
                else "*** CAMBIO DESPUES DEL COMMIT -- revisar ***"
            print("  - %-55s decl=%s recalc=%s  %s"
                  % (f["nombre"], f["declarado"], f["recalculado"], estable))
    if commit_falso:
        print("\nCODE_COMMIT NO ES UN COMMIT REAL (%d):" % len(commit_falso))
        for f in commit_falso:
            print("  - %s" % f["nombre"])

    if a.json:
        Path(a.json).write_text(json.dumps(filas, indent=1, ensure_ascii=False) + "\n",
                                encoding="utf-8")
        print("\n-> %s" % a.json)

    critico = [f for f in mismatch if not f.get("estable_desde_commit")] + \
        [f for f in faltan if f["estado"] == "NO_TRACKEADO"] + commit_falso
    return 1 if critico else 0


if __name__ == "__main__":
    sys.exit(main())
