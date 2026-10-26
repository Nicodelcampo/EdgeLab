#!/usr/bin/env python3
"""Reconstruye TODOS los kernels commiteados con los módulos actuales (error O6 de
docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md: tocar un módulo embebido —grilla_generica, etapas, escalera, eventos…— deja
los kernels desactualizados y el CI rojo). Correrlo antes de commitear cualquier cambio en edgelab/; los tests `*_al_dia` lo verifican.
  python tools/reconstruir_kernels.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "tools" / "kaggle_grilla"))
from construir_kernel import construir  # noqa: E402
from construir_kernel_experimento import BASE, construir_experimento  # noqa: E402

KERNELS = [  # (salida, función) — los mismos que verifican tests/research/test_kernel_areas_al_dia.py y test_luximb_grilla.py
    ("tools/kaggle_areas/kernel_areas.py", lambda o: construir("tools/kaggle_areas/areas_main.py", o,
                                                                ["edgelab/research/areas_expansion.py", "edgelab/research/areas_expansion_run.py"])),
    ("tools/kaggle_grilla/kernel_u1_indaga.py", lambda o: construir_experimento("edgelab/research/u1_indaga.py", o)),
    ("tools/kaggle_grilla/kernel_u1_cruzado.py", lambda o: construir("tools/kaggle_grilla/u1_cruzado_main.py", o,
                                                                     BASE + ["edgelab/research/u1_indaga.py", "edgelab/research/u1_cruzado.py"])),
    ("tools/kaggle_grilla/kernel_luximb_grilla.py", lambda o: construir_experimento(
        "edgelab/research/luximb_grilla.py", o, ["edgelab/research/agente/regimen.py", "edgelab/regimes/state.py",
                                                 "edgelab/bridge/indicators/espejo_impulsos.py"])),
]


def main():
    for out, f in KERNELS:
        antes = (ROOT / out).read_bytes() if (ROOT / out).exists() else b""
        f(str(ROOT / out)); print(("actualizado " if (ROOT / out).read_bytes() != antes else "al día      ") + out)


if __name__ == "__main__":
    main()
