#!/usr/bin/env python3
"""Cierre de un turno de trabajo en UN comando (AUTOMATIZACION_PROCESOS_20261111 C3): regenera todos los archivos generados y
corre los tests que los vigilan, para que ningún commit deje el CI rojo por un índice viejo (pasó dos veces el 2026-11-11).
  python tools/cierre.py            # regenera y prueba; sale 1 si algo falla
  python tools/cierre.py --rapido   # sólo regenera
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGENERAR = [["tools/docs_index.py", "--write"], ["tools/existente.py", "catalogo", "--write"], ["tools/familias.py", "--write"],
             ["tools/factores.py", "--write"], ["tools/remediciones.py", "--write"], ["tools/agentes.py", "--write"],
             ["tools/check_modules.py", "--write"]]
TESTS = ["tests/test_existente.py", "tests/test_verify_indices.py", "tests/research/test_factores.py", "tests/test_holdout_unico.py",
         "tests/test_dependencias_lock.py", "tests/test_parametros_por_defecto.py", "tests/test_cadena_accesible.py"]


def main() -> int:
    mal = 0
    for c in REGENERAR:
        r = subprocess.run([sys.executable, *c], cwd=ROOT, capture_output=True, text=True)
        print(("ok   " if not r.returncode else "FALLA"), " ".join(c)); mal += bool(r.returncode)
        if r.returncode: print((r.stdout + r.stderr)[-600:])
    if "--rapido" not in sys.argv:
        r = subprocess.run([sys.executable, "-m", "pytest", *[t for t in TESTS if (ROOT / t).exists()], "-q", "-p", "no:cacheprovider"],
                           cwd=ROOT, capture_output=True, text=True)
        print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-600:]); mal += bool(r.returncode)
        if r.returncode: print(r.stdout[-2500:])
    st = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True).stdout
    print("archivos cambiados:\n" + (st or "  (ninguno)"))
    return 1 if mal else 0


if __name__ == "__main__":
    sys.exit(main())
