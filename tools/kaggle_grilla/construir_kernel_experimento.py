#!/usr/bin/env python3
"""Kernel autocontenido para CUALQUIER experimento de grilla genérica (edgelab/research/grilla_generica.py).
  python tools/kaggle_grilla/construir_kernel_experimento.py <modulo_del_experimento.py> <salida.py> [--extra otro_modulo.py ...]
Embebe el conductor genérico, el simulador, los lectores de ticks y la frontera del holdout. El experimento se elige en el
kernel con EXPERIMENTO (ruta de import del módulo)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from construir_kernel import construir  # noqa: E402

BASE = ["edgelab/holdout.py", "edgelab/research/fuentes_ticks.py", "edgelab/research/areas_expansion.py",
        "edgelab/research/areas_expansion_run.py", "edgelab/research/grilla_generica.py", "edgelab/research/eventos.py",
        "edgelab/research/eventos_datos.py"]


def construir_experimento(modulo, out, extra=()):
    return construir("tools/kaggle_grilla/grilla_main.py", out, BASE + list(extra) + [modulo])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("modulo"); ap.add_argument("out"); ap.add_argument("--extra", action="append", default=[])
    a = ap.parse_args(); c, s = construir_experimento(a.modulo, a.out, a.extra); print(a.out, c[:16], len(s), "módulos")
