#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""estado.py — UN comando que dice dónde estás parado. Correlo al abrir sesión.

## Por qué existe

El 2026-08-05 dos máquinas midieron cosas distintas creyendo mirar lo mismo. La
causa no fue un dato corrupto: `CLAUDE.md` declaraba `foundation/f0b-compatibility-probe`
como rama de trabajo, y 70 commits vivían en `fix/capture-probe-v2-contract`.
Cada lado leyó su rama y las dos lecturas eran internamente coherentes. Nadie
tenía forma barata de descubrir que miraban árboles distintos.

Esto es esa forma barata. Falla ruidoso si:

- estás en una rama que no es la declarada en `CLAUDE.md`;
- tu rama está adelante o atrás del remoto;
- OTRA rama del remoto tiene commits que la tuya no tiene;
- hay archivos sin ignorar dentro de `data/` (por donde se cuela una captura
  del holdout a un `git add -A`).

## Justificación económica

Una medición hecha sobre el árbol equivocado no es un error recuperable: es
trabajo que hay que rehacer, y peor, es trabajo que puede pasar por bueno. El
costo de este chequeo es un segundo; el de no tenerlo ya se pagó una vez.

## Cómo podría refutarse

Si `estado.py` diera verde estando en un árbol desactualizado, el chequeo sería
peor que inútil: daría falsa confianza. Por eso compara contra `origin` recién
fetcheado y no contra refs locales, que son justamente las que se quedan viejas.

Uso:  python tools/estado.py [--sin-fetch]
Sale 0 si todo está alineado, 1 si algo requiere atención.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OK, WARN, BAD = "OK  ", "AVISO", "MAL "


def git(*args, check=False):
    r = subprocess.run(["git", "-C", str(REPO), *args],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(" ".join(args) + ": " + r.stderr.strip())
    return r.stdout.strip()


def rama_declarada():
    """La rama que `CLAUDE.md` declara. Es la fuente de verdad, no el checkout."""
    txt = (REPO / "CLAUDE.md").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"Branch de trabajo:\s*\n?`([^`]+)`", txt)
    return m.group(1) if m else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sin-fetch", action="store_true",
                    help="no consulta el remoto (más rápido, MENOS confiable)")
    a = ap.parse_args(argv)

    problemas = []
    print("EdgeLab — estado del árbol\n" + "=" * 60)
    print("clon        %s" % REPO)

    if not a.sin_fetch:
        git("fetch", "--quiet", "origin")

    rama = git("rev-parse", "--abbrev-ref", "HEAD")
    decl = rama_declarada()
    tip = git("rev-parse", "--short", "HEAD")
    print("rama        %s   tip %s" % (rama, tip))
    print("declarada   %s  (CLAUDE.md)" % decl)

    if decl and rama != decl:
        problemas.append("estás en %r y CLAUDE.md declara %r. Todo lo que midas "
                         "acá puede no ser el estado del proyecto." % (rama, decl))
        print("%s rama distinta de la declarada" % BAD)
    else:
        print("%s rama = declarada" % OK)

    # --- sincronía con el remoto -------------------------------------------
    up = "origin/" + rama
    if git("rev-parse", "--verify", "--quiet", up):
        det = git("rev-list", "--left-right", "--count", "%s...HEAD" % up)
        atras, adelante = (int(x) for x in det.split())
        if atras or adelante:
            problemas.append("tu rama está %d atrás y %d adelante de %s"
                             % (atras, adelante, up))
            print("%s %d atrás / %d adelante de %s" % (BAD, atras, adelante, up))
        else:
            print("%s sincronizado con %s" % (OK, up))
    else:
        problemas.append("la rama no existe en el remoto: nadie más la ve")
        print("%s %s no existe en el remoto" % (BAD, up))

    # --- LA comprobación que faltaba el 2026-08-05 --------------------------
    print("-" * 60)
    print("otras ramas del remoto (commits que ESTA rama no tiene):")
    hay_divergencia = False
    for ref in git("for-each-ref", "--format=%(refname:short)",
                   "refs/remotes/origin").splitlines():
        if ref in ("origin/HEAD", up):
            continue
        n = git("rev-list", "--count", "HEAD..%s" % ref)
        if n and int(n) > 0:
            # Ramas que divergen A PROPOSITO: `main` es el baseline original
            # sellado, y backup/* y preserve/* existen justamente para conservar
            # estados anteriores. Marcarlas como problema seria ruido, y un
            # chequeo que grita siempre deja de leerse.
            corto = ref.split("/", 1)[1]
            esperada = (corto == "main" or corto.startswith("backup/")
                        or corto.startswith("preserve/"))
            etiqueta = "  (divergencia esperada)" if esperada else ""
            print("  %s %-52s %4s%s"
                  % (WARN if etiqueta else BAD, ref, n, etiqueta))
            if not etiqueta:
                hay_divergencia = True
    if hay_divergencia:
        problemas.append("hay ramas con trabajo que esta rama NO tiene. Es "
                         "exactamente la falla del 2026-08-05.")
    else:
        print("  %s ninguna rama de trabajo tiene commits que esta no tenga" % OK)

    # --- el agujero por donde se cuela el holdout ---------------------------
    print("-" * 60)
    sueltos = [l for l in git("status", "--porcelain", "--untracked-files=all",
                              "data/").splitlines() if l.strip()]
    if sueltos:
        problemas.append("hay %d archivo(s) sin ignorar dentro de data/: un "
                         "`git add -A` los commitearía" % len(sueltos))
        print("%s data/ tiene %d archivo(s) SIN IGNORAR:" % (BAD, len(sueltos)))
        for l in sueltos[:5]:
            print("      %s" % l)
    else:
        print("%s data/ enteramente ignorado" % OK)

    sucio = [l for l in git("status", "--porcelain").splitlines() if l.strip()]
    print("%s working tree: %s" % (OK if not sucio else WARN,
                                   "limpio" if not sucio else
                                   "%d archivo(s) sin commitear" % len(sucio)))

    # --- huellas de los artefactos que la gente compara ---------------------
    print("-" * 60)
    print("artefactos:")
    cs = REPO / "nt8" / "BigTrap2.cs"
    if cs.exists():
        import hashlib
        b = cs.read_bytes()
        v = re.search(rb"version=([0-9.]+)", b)
        print("  BigTrap2.cs        v%-6s sha256 %s"
              % (v.group(1).decode() if v else "?", hashlib.sha256(b).hexdigest()[:16]))
    censo = REPO / "diag" / "tasa_senales" / "post_sepmin.json"
    if censo.exists():
        d = json.loads(censo.read_text(encoding="utf-8"))
        ses = sum(len(v.get("fechas", [])) for v in d.values())
        ind = len({i for v in d.values() for i in v.get("ind", {})})
        print("  censo creaciones   %d sesiones, %d indicadores" % (ses, ind))
    # La huella se pide a la PUERTA UNICA, que es duena de la ruta Y de la
    # lectura. Este archivo no nombra el manifiesto ni lo abre:
    # `test_nadie_lee_el_manifiesto_por_fuera_de_la_puerta` caza a cualquier
    # consumidor nuevo, y tiene razon -filtrar por fuera es el patron que dejo
    # entrar 10 dias del holdout el 2026-07-27-.
    sys.path.insert(0, str(REPO))
    try:
        from edgelab.research.universo_estudio import (huella_del_universo,
                                                       ruta_por_defecto)
        if ruta_por_defecto().exists():
            h = huella_del_universo()
            print("  universo           %d dias  generado %s  sha256 %s"
                  % (h["n_dias"], (h["generado_utc"] or "?")[:10], h["sha256"][:16]))
    except Exception as exc:
        print("  universo           no evaluable: %s" % exc)
    an = REPO / "tools" / "pred004_analyze.py"
    if an.exists():
        sys.path.insert(0, str(REPO / "tools"))
        try:
            import pred004_analyze as P
            print("  contrato PRED-004  %s" % P.contrato_sha()[:16])
        except Exception as exc:
            print("  contrato PRED-004  no evaluable: %s" % exc)

    print("=" * 60)
    if problemas:
        print("REQUIERE ATENCIÓN:")
        for p in problemas:
            print("  - %s" % p)
        return 1
    print("Todo alineado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
