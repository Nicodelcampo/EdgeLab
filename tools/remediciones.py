#!/usr/bin/env python3
"""Re-mediciones candidatas: cruza los cambios de medición (docs/research/CAMBIOS_DE_MEDICION.jsonl) con el índice de familias y con
el código, y lista qué corridas anteriores darían otro resultado con la forma de medir de hoy. Módulo: edgelab/research/remedicion.py.
  python tools/remediciones.py            # imprime
  python tools/remediciones.py --write    # regenera docs/research/REMEDICIONES_CANDIDATAS.md
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab.research import remedicion as RM  # noqa: E402
import familias  # noqa: E402

SALIDA = ROOT / "docs/research/REMEDICIONES_CANDIDATAS.md"


def markdown() -> str:
    C = RM.cargar(); return RM.markdown(RM.candidatas(familias.tabla(), C), C, RM.patrones_codigo(C))


if __name__ == "__main__":
    if "--write" in sys.argv: SALIDA.write_text(markdown(), encoding="utf-8"); print("escrito", SALIDA.relative_to(ROOT))
    else: print(markdown())
