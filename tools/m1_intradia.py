#!/usr/bin/env python3
"""ORB y pre-rango 08:12 sobre M1 de Dukascopy en Kaggle (edgelab/research/m1_intradia.py).
  python tools/m1_intradia.py lanzar   # kernel con el módulo incrustado; monta edgelab-sqx-m1 (M1, lo sube Antigravity) y edgelab-sqx-barras (spreads)
  python tools/m1_intradia.py traer    # baja RESULTADO.json a docs/research/m1_intradia_20261114/
"""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
KS = "nicolasbuttaro/edgelab-m1-intradia"; DS = ("nicolasbuttaro/edgelab-sqx-m1", "nicolasbuttaro/edgelab-sqx-barras")
def lanzar():
    k = ROOT / "data/m1_intradia_kernel.py"; k.parent.mkdir(exist_ok=True)
    k.write_text("import sys, types\n_m = types.ModuleType('m1_intradia')\nexec(compile(" + repr((ROOT / "edgelab/research/m1_intradia.py").read_text()) +
                 ", 'm1_intradia.py', 'exec'), _m.__dict__)\nsys.modules['m1_intradia'] = _m\n" + (ROOT / "tools/kaggle_grilla/m1_intradia_main.py").read_text())
    a = [sys.executable, "tools/kaggle_kernel.py", "push", "--slug", KS, "--title", "edgelab m1 intradia", "--script", str(k)]
    for d in DS: a += ["--dataset", d]
    subprocess.run(a, cwd=ROOT, check=True)
def lanzar_vwapb():
    """Operaciones por día de VWAPB (mapa de régimen)."""
    k = ROOT / "data/vwapb_ops_kernel.py"
    k.write_text("import sys, types\n_m = types.ModuleType('m1_intradia')\nexec(compile(" + repr((ROOT / "edgelab/research/m1_intradia.py").read_text()) +
                 ", 'm1_intradia.py', 'exec'), _m.__dict__)\nsys.modules['m1_intradia'] = _m\n" + (ROOT / "tools/kaggle_grilla/vwapb_ops_main.py").read_text())
    a = [sys.executable, "tools/kaggle_kernel.py", "push", "--slug", "nicolasbuttaro/edgelab-vwapb-ops", "--title", "edgelab vwapb ops", "--script", str(k)]
    for d in DS: a += ["--dataset", d]
    subprocess.run(a, cwd=ROOT, check=True)


def traer_vwapb():
    o = ROOT / "data/vwapb"; o.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "output", "--slug", "nicolasbuttaro/edgelab-vwapb-ops", "--file", "VWAPB_OPS.csv.gz", "--out", str(o / "VWAPB_OPS.csv.gz")], cwd=ROOT, check=True)


def traer():
    o = ROOT / "docs/research/m1_intradia_20261114"; o.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "output", "--slug", KS, "--file", "RESULTADO.json", "--out", str(o / "RESULTADO.json")], cwd=ROOT, check=True)
if __name__ == "__main__": globals()[sys.argv[1]]()
