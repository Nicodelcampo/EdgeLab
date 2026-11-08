#!/usr/bin/env python3
"""CANASTA-GLOBAL en tandas paralelas (docs/research/canasta_global_20261108/PREREGISTRO.md).

  python tools/canasta_global.py avanzar     # lanza las tandas pendientes si hay cupo, baja las terminadas y combina lo que haya
                                             # (parcial: canasta observada sin p; completa: con el nulo de la selección)
"""
import json, pickle, subprocess, sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import os
VAR = os.environ.get("CANASTA_VARIANTE", "global")          # "global" o "frecuente" (2026-11-08)
DIR = ROOT / ("docs/research/canasta_global_20261108" if VAR == "global" else "docs/research/canasta_global_frecuente_20261108")
CACHE = ROOT / f"data/canasta_{VAR}"
CUENTA, DATASET = "nicolasbuttaro", "nicolasbuttaro/edgelab-cubos-regimen"


def _k(*a):
    return subprocess.run([sys.executable, str(ROOT / "tools/kaggle_kernel.py"), *a], capture_output=True, text=True, timeout=600).stdout


def avanzar():
    from edgelab.research import canasta_global as CG
    T = json.loads((DIR / "TANDAS.json").read_text()); CACHE.mkdir(parents=True, exist_ok=True); partes, estado = [], {}
    for k in range(len(T["tandas"])):
        slug = f"{CUENTA}/canasta-{VAR}-t{k}-20261108"; f = CACHE / f"parte{k}.pkl"
        if not f.exists():
            st = _k("status", "--slug", slug)
            if '"complete"' in st:
                _k("output", "--slug", slug, "--file", "CANASTA_PARTE.pkl", "--out", str(f))
            elif '"running"' not in st and '"queued"' not in st:
                r = _k("push", "--slug", slug, "--title", f"canasta {VAR} t{k} 20261108", "--script",
                       str(ROOT / f"tools/kaggle_grilla/canasta_{VAR}_tanda{k}_main.py"), "--dataset", DATASET)
                st = "relanzada" if '"url"' in r else "sin cupo"
        estado[k] = "lista" if f.exists() else ("corriendo" if '"running"' in st or '"queued"' in st else st[:40])
        if f.exists(): partes += pickle.loads(f.read_bytes())
    completo = all(v == "lista" for v in estado.values())
    if VAR == "frecuente": CG.OPS_SESION_REGLA, CG.OPS_SESION_CANASTA = 0.5, 3.0
    r = CG.combinar(partes, np.array(T["dias"]), completo=completo) if partes else {}
    nombre = "RESULTADO_CANASTA_GLOBAL.json" if completo else "PARCIAL_CANASTA_GLOBAL.json"
    if r: (DIR / nombre).write_text(json.dumps({k: v for k, v in r.items() if k != "serie_canasta"}, indent=1, default=float))
    print(json.dumps(dict(tandas=estado, cubos=r.get("cubos"), reglas=len(r.get("reglas", [])), t=r.get("t_canasta"),
                          p=r.get("p_seleccion"), media_diaria=r.get("media_diaria_canasta"))))


if __name__ == "__main__":
    avanzar()
