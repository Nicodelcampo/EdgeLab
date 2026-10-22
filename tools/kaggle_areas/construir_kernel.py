#!/usr/bin/env python3
"""Kernel de AREAS-EXP-1 con el empaquetador genérico (tools/kaggle_grilla/construir_kernel.py).
  python tools/kaggle_areas/construir_kernel.py <salida.py>"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kaggle_grilla"))
from construir_kernel import construir  # noqa: E402

if __name__ == "__main__":
    c, s = construir("tools/kaggle_areas/areas_main.py", sys.argv[1],
                     ["edgelab/research/areas_expansion.py", "edgelab/research/areas_expansion_run.py"])
    print(sys.argv[1], c[:16], {k: v[:12] for k, v in s.items()})
