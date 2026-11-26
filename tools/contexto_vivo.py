#!/usr/bin/env python3
"""Genera o verifica `docs/ESTADO_VIVO.md`, el snapshot compacto de contexto (<= 150 lineas).

Uso:
  python tools/contexto_vivo.py --write
  python tools/contexto_vivo.py --check
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edgelab.research.contexto_vivo import (  # noqa: E402
    SALIDA,
    escribir_estado_vivo,
    verificar_estado_vivo,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Genera o valida docs/ESTADO_VIVO.md")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true", help="Regenera docs/ESTADO_VIVO.md")
    g.add_argument("--check", action="store_true", help="Valida sincronia y tope de lineas")
    args = ap.parse_args(argv)

    if args.write:
        dest = escribir_estado_vivo(ROOT)
        n = len(dest.read_text(encoding="utf-8").splitlines())
        print(f"escrito {dest.relative_to(ROOT).as_posix()} ({n} lineas)")
        return 0

    errs = verificar_estado_vivo(ROOT, SALIDA)
    for e in errs:
        print("FALLA:", e)
    if not errs:
        print("OK: docs/ESTADO_VIVO.md vigente")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
