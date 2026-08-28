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
como señal para revisión humana.

**Sobre `working_tree_clean` — leer antes de interpretarlo como prueba de
integridad.** `git diff HEAD -- <archivo>` vacío sólo demuestra que el
árbol de trabajo ACTUAL coincide con lo que HEAD tiene registrado ahora. NO
demuestra que ese commit nunca se reescribió (`commit --amend`, rebase,
force-push) entre su creación y hoy — este repo no hace eso como práctica,
pero el comando en sí no lo descarta. `unico_commit_en_su_historia` (via
`git log --follow`) es una segunda señal, independiente, de que el archivo
tiene un solo punto de entrada en el historial — más fuerte que
`working_tree_clean` sola, pero tampoco es una prueba criptográfica de
inmutabilidad pre-commit. La conclusión defendible con estas dos señales es:
**"no se detectó mutación posterior al commit; la procedencia exacta
pre-commit no es reconstruible desde acá"** — nunca "no hubo tampereo".
(Corrección del auditor, 2026-08-11, sobre la v1 de este script.)

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


def working_tree_clean(ruta_relativa):
    """Arbol de trabajo == HEAD para esta ruta. NO prueba inmutabilidad
    pre-commit -- ver el caveat en el docstring del modulo."""
    return sh("diff", "HEAD", "--", ruta_relativa) == ""


def unico_commit_en_su_historia(ruta_relativa):
    """Cuantos commits tocaron esta ruta alguna vez (--follow, renames
    incluidos). Senal independiente de working_tree_clean: un archivo con
    un solo commit en su historia y arbol limpio es mas dificil de explicar
    por una reescritura silenciosa que uno con muchos commits."""
    log = sh("log", "--oneline", "--follow", "--", ruta_relativa)
    lineas = [l for l in log.splitlines() if l.strip()]
    return len(lineas)


def calcular_hash(data, ensure_ascii):
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=ensure_ascii, default=str)
        .encode()).hexdigest()


def clasificar_hash(data, declarado):
    """Funcion pura, testeable sin filesystem/git: dado un payload SIN
    `payload_sha256` y el hash declarado, devuelve (hash, serialization|None,
    recalculado_canonico). No toca disco ni git -- eso lo hace `verificar()`
    solo para el caso MISMATCH, donde SI importa la procedencia."""
    recalc_canonico = calcular_hash(data, ensure_ascii=False)
    if declarado is None:
        return "SIN_PAYLOAD_SHA256", None, recalc_canonico
    if declarado == recalc_canonico:
        return "OK", "json_sort_keys_ensure_ascii_false", recalc_canonico
    recalc_legacy = calcular_hash(data, ensure_ascii=True)
    if declarado == recalc_legacy:
        return "OK_LEGACY", "json_sort_keys_ensure_ascii_true", recalc_canonico
    return "MISMATCH", None, recalc_canonico


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
            # distinto -- ver docs/P2_SEIS_HASHES_ADJUDICACION_2026-08-11.md.
            # CANONICO (convencion vigente desde el 2026-08-10): ensure_ascii=False.
            # LEGACY (E-R1 y anterior, entorno vacio en el payload): ensure_ascii=True.
            # Se reporta CUAL convencion hizo match -- un OK indiferenciado
            # esconde justamente el dato que motivo la revision. (Correccion
            # del auditor sobre la v1 de este script, que devolvia OK liso.)
            clasif, serial, recalc_canonico = clasificar_hash(data, declarado)
            fila["hash"] = clasif
            if serial:
                fila["serialization"] = serial
            elif clasif == "MISMATCH":
                fila["declarado"] = declarado[:16]
                fila["recalculado"] = recalc_canonico[:16]
                fila["working_tree_clean"] = working_tree_clean(rel)
                fila["commits_en_su_historia"] = unico_commit_en_su_historia(rel)

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
    legacy = [f for f in filas if f.get("hash") == "OK_LEGACY"]
    mismatch = [f for f in filas if f.get("hash") == "MISMATCH"]
    commit_falso = [f for f in filas if f.get("code_commit_real") is False]

    print("Artefactos citados en REGISTRO %s1 MEDIDO: %d" % (chr(167), len(filas)))
    print("  limpios (existen, trackeados, hash OK canonico donde aplica): %d"
          % (len(filas) - len(faltan) - len(mismatch) - len(legacy)))

    if faltan:
        print("\nFALTAN / NO TRACKEADOS / NO PARSEAN (%d):" % len(faltan))
        for f in faltan:
            print("  - %-55s %s %s" % (f["nombre"], f["estado"], f.get("detalle", "")))
    if sin_hash:
        print("\nSIN payload_sha256 -- predatan la convencion, no es corrupcion (%d):"
              % len(sin_hash))
        for f in sin_hash:
            print("  - %s" % f["nombre"])
    if legacy:
        print("\nOK_LEGACY -- hash valido bajo serializacion no-canonica (%d):" % len(legacy))
        for f in legacy:
            print("  - %-55s serialization=%s" % (f["nombre"], f["serialization"]))
    if mismatch:
        print("\nHASH NO COINCIDE (%d) -- 'working_tree_clean' NO prueba ausencia de"
              % len(mismatch))
        print("tampereo, solo que el arbol actual coincide con HEAD (ver docstring):")
        for f in mismatch:
            if f["working_tree_clean"]:
                senal = ("arbol==HEAD, %d commit(s) en su historia -- procedencia "
                        "pre-commit no reconstruible desde aca" % f["commits_en_su_historia"])
            else:
                senal = "*** ARBOL DE TRABAJO != HEAD -- revisar antes que nada ***"
            print("  - %-55s decl=%s recalc=%s  %s"
                  % (f["nombre"], f["declarado"], f["recalculado"], senal))
    if commit_falso:
        print("\nCODE_COMMIT NO ES UN COMMIT REAL (%d):" % len(commit_falso))
        for f in commit_falso:
            print("  - %s" % f["nombre"])

    if a.json:
        Path(a.json).write_text(json.dumps(filas, indent=1, ensure_ascii=False) + "\n",
                                encoding="utf-8")
        print("\n-> %s" % a.json)

    critico = [f for f in mismatch if not f.get("working_tree_clean")] + \
        [f for f in faltan if f["estado"] == "NO_TRACKEADO"] + commit_falso
    return 1 if critico else 0


if __name__ == "__main__":
    sys.exit(main())
