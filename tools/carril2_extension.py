#!/usr/bin/env python3
"""CARRIL2-EXTENSION (2026-11-26): las definiciones de Carril 2 (lotes 1 y 2) hasta 2026-09-30 con `tools/carril2.py::correr` sin
cambios de regla (sólo FIN y carpeta de salida). Pre-registro: docs/research/carril2_extension_20261126/PREREGISTRO.md.

  python tools/carril2_extension.py correr
  python tools/carril2_extension.py leer
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/carril2_extension_20261126"; PRE = "docs/research/carril2_extension_20261126/PREREGISTRO.md"


def correr():
    import carril2 as C
    for lote in (1, 2):
        if lote == 2: C._lote2()
        C.PRE = PRE; C.DIR = DIR; C.FIN = 20260930; C.LOTE = dict(C.LOTE, ops=f"OPS_LOTE{lote}.csv.gz")
        C.correr()


def leer():
    out = {}
    for lote in (1, 2):
        T = pd.read_csv(DIR / f"OPS_LOTE{lote}.csv.gz")
        for (d, inst), g in T.groupby(["definicion", "inst"]):
            a, b = g[g.fecha_salida <= 20250731], g[g.fecha_salida > 20250731]
            f = lambda x: dict(n=int(len(x)), R=float(x.R.mean()) if len(x) else None,
                               t=float(x.R.mean() / (x.R.std() / np.sqrt(len(x)))) if len(x) > 2 and x.R.std() > 0 else None)
            out[f"{d}_{inst}"] = dict(hasta_2025_07=f(a), desde_2025_08=f(b))
    (DIR / "RESULTADO.json").write_text(json.dumps(out, indent=1))
    for k, v in sorted(out.items()): print(k, v)


if __name__ == "__main__":
    {"correr": correr, "leer": leer}[sys.argv[1]]()
