#!/usr/bin/env python3
"""Verifica un `.cs` de NinjaScript antes de instalarlo en NT8.

Nace del incidente 2026-07-25: un `.cs` revisado fuera del repo llegó con
terminadores LF y con el bloque `#region NinjaScript generated code` ya adentro.
NT8 no reconoció su propia región (por los LF), **anexó una segunda**, y la
compilación reventó con CS0111/CS0102/CS0121/CS0229.

Uso:  python tools/check_nt8_cs.py nt8/HFTZones2.cs [--version 2.1]
Salida: 0 si todo OK, 1 si hay algún hallazgo bloqueante.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

LINE = re.compile(r"//[^\n]*")
BLOCK = re.compile(r"/\*.*?\*/", re.S)
STR = re.compile(r'"(?:[^"\\]|\\.)*"')
CHR = re.compile(r"'(?:[^'\\]|\\.)*'")
REGION = "#region NinjaScript generated code"


def _strip(src: str) -> str:
    """Quita comentarios y literales para poder contar delimitadores."""
    return STR.sub('""', CHR.sub("' '", BLOCK.sub(" ", LINE.sub(" ", src))))


def check(path: str, version: str | None = None):
    raw = open(path, "rb").read()
    text = raw.decode("utf-8-sig")
    fails, warns = [], []

    # 1) una sola definición de la clase
    clases = re.findall(r"class\s+(\w+)\s*:\s*Indicator\b", text)
    if len(clases) != 1:
        fails.append("define %d clases `: Indicator` (%s); debe ser exactamente 1"
                     % (len(clases), ", ".join(clases) or "ninguna"))

    # 2) la región generada es salida de build: no debe viajar en el fuente
    n_reg = text.count(REGION)
    if n_reg > 1:
        fails.append("%d bloques `%s`: NT8 no compila con dos" % (n_reg, REGION))
    elif n_reg == 1:
        warns.append("trae 1 región generada; la copia canónica debería tener 0 "
                     "(NT8 la regenera al compilar)")

    # 3) terminadores: LF suelto hace que NT8 anexe una región en vez de reemplazarla
    crlf = raw.count(b"\r\n")
    lf_solo = raw.count(b"\n") - crlf
    if lf_solo:
        fails.append("%d saltos LF sin CR: NT8 anexará una región duplicada" % lf_solo)
    if raw.count(b"\r\r\n"):
        fails.append("%d terminadores CR CR LF (doble CR)" % raw.count(b"\r\r\n"))

    # 4) meta de versión
    metas = re.findall(r"meta[ ,]indicator=(\w+),version=([\d.]+)", text)
    if version:
        if not any(v == version for _, v in metas):
            fails.append("no se encontró `version=%s` en la línea meta (hallado: %s)"
                         % (version, metas or "nada"))
    elif not metas:
        warns.append("sin línea `# meta indicator=...,version=...`")

    # 5) delimitadores balanceados
    c = _strip(text)
    if c.count("{") != c.count("}"):
        fails.append("llaves desbalanceadas: %d/%d" % (c.count("{"), c.count("}")))
    if c.count("(") != c.count(")"):
        fails.append("paréntesis desbalanceados: %d/%d" % (c.count("("), c.count(")")))

    return clases, metas, crlf, fails, warns


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verifica un .cs de NinjaScript")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--version", help="versión esperada en la línea meta")
    ap.add_argument("--ulp", action="store_true",
                    help="ademas, correr el barrido ULP en modo gate (regla de "
                         "diseño: ningun umbral de precio se compara en double)")
    a = ap.parse_args(argv)

    rc = 0
    for p in a.paths:
        clases, metas, crlf, fails, warns = check(p, a.version)
        estado = "FAIL" if fails else ("WARN" if warns else "OK")
        print("[%s] %s  (clase=%s, meta=%s, %d líneas CRLF)"
              % (estado, p, clases[0] if clases else "?",
                 ",".join("%s=%s" % m for m in metas) or "-", crlf))
        for f in fails:
            print("   FAIL  " + f)
        for w in warns:
            print("   warn  " + w)
        if fails:
            rc = 1

    if a.ulp:
        # El barrido vive aparte porque MIDE distinto (expresiones, no estructura),
        # pero se puede exigir en la misma pasada. Falla solo ante expresiones que
        # nunca se clasificaron: los 49 candidatos actuales estan sellados.
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import ulp_sweep
        print()
        if ulp_sweep.main(["--baseline"] + list(a.paths)) != 0:
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
