#!/usr/bin/env python3
"""Registro de factores con ventaja (edgelab/research/factores.py).
  python tools/factores.py                      # imprime el registro
  python tools/factores.py --write              # regenera docs/research/FACTORES_CON_VENTAJA.md
  python tools/factores.py agregar entrada.json # agrega una entrada (JSON con id, fecha, estado, factor, efecto, donde, evidencia, siguiente)
  python tools/factores.py meta <dir_embudo> <llm_calls.sqlite>   # meta-analista sobre las campañas cerradas pendientes (ciclo del Debian)
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.research import factores as F  # noqa: E402


def main():
    a = sys.argv[1:]
    if a[:1] == ["agregar"]:
        F.registrar(**json.loads(Path(a[1]).read_text(encoding="utf-8"))); F.escribir(); print("agregado y regenerado")
    elif a[:1] == ["meta"]:
        from edgelab.autopilot import meta_analisis as M
        from edgelab.autopilot.roles import RoleRunner
        print(json.dumps(M.procesar(RoleRunner(Path(a[2])), Path(a[1])), ensure_ascii=False))
    elif "--write" in a: F.escribir(); print("escrito", F.SALIDA.relative_to(ROOT))
    else: print(F.markdown())


if __name__ == "__main__":
    main()
