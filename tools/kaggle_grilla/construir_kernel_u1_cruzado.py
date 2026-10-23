#!/usr/bin/env python3
"""python tools/kaggle_grilla/construir_kernel_u1_cruzado.py tools/kaggle_grilla/kernel_u1_cruzado.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from construir_kernel import construir  # noqa: E402
from construir_kernel_experimento import BASE  # noqa: E402

if __name__ == "__main__":
    c, s = construir("tools/kaggle_grilla/u1_cruzado_main.py", sys.argv[1], BASE + ["edgelab/research/u1_indaga.py", "edgelab/research/u1_cruzado.py"])
    print(sys.argv[1], c[:16], len(s), "módulos")
