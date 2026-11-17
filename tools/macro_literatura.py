#!/usr/bin/env python3
"""Ideas de la literatura en Kaggle (edgelab/research/macro_literatura.py).
  python tools/macro_literatura.py dataset   # sube data/sqx_barras (+ spreads.json) al dataset privado nicolasbuttaro/edgelab-sqx-barras
  python tools/macro_literatura.py lanzar    # arma el kernel (módulo incrustado + main) y lo lanza montando ese dataset
  python tools/macro_literatura.py traer     # baja RESULTADO.json a docs/research/macro_literatura_20261114/
"""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "tools"))
DS, KS = "nicolasbuttaro/edgelab-sqx-barras", "nicolasbuttaro/edgelab-macro-literatura"
DIR = ROOT / "data/sqx_barras"; OUT = ROOT / "docs/research/macro_literatura_20261114"

def _py(*a): return subprocess.run([sys.executable, *a], cwd=ROOT, check=True)

def dataset():
    import mcp_cliente as MC
    c = MC.Cliente("sqx"); sp = {}
    for x in c.llamar("list_data", {"detail": True}).get("data", []):
        if x["symbol"].startswith(("NULO_", "PRUEBA_")): continue
        sp[x["symbol"]] = float(x.get("spread", 0)) * float(x.get("tickSize", 0) or 0)          # spread en precio (puntos × tamaño de tick)
    # Correcciones de unidad (2026-11-15): el tamaño de tick del catálogo de SQX no corresponde en estos símbolos (plata 98 pb, índice dólar
    # 495 pb) y los bonos venían en 0; se usan spreads típicos de Dukascopy. Ver docs/research/macro_literatura_20261114/RESULTADO.md.
    sp.update({"XAGUSD": 0.025, "DOLLARIDXUSD": 0.03, "USTBONDTRUSD": 0.02, "BUNDTREUR": 0.02, "UKGILTTRGBP": 0.03})
    (DIR / "spreads.json").write_text(json.dumps(sp, indent=1))
    hay = subprocess.run([sys.executable, "tools/kaggle_kernel.py", "status", "--slug", KS], cwd=ROOT, capture_output=True, text=True)
    cmd = "version" if "edgelab-sqx-barras" in subprocess.run(["curl", "-sS", f"https://www.kaggle.com/api/v1/datasets/view/{DS}"], capture_output=True, text=True).stdout else "create"
    _py("tools/kaggle_dataset.py", cmd, "--slug", DS, "--dir", str(DIR), *(["--title", "edgelab sqx barras"] if cmd == "create" else ["--notes", "barras D1/H1 hasta 2026-09-29"]))

def lanzar(sufijo=""):
    k = ROOT / "data/macro_literatura_kernel.py"
    k.write_text("import sys, types\n_m = types.ModuleType('macro_literatura')\nexec(compile(" + repr((ROOT / "edgelab/research/macro_literatura.py").read_text()) +
                 ", 'macro_literatura.py', 'exec'), _m.__dict__)\nsys.modules['macro_literatura'] = _m\n" + (ROOT / "tools/kaggle_grilla/macro_literatura_main.py").read_text())
    _py("tools/kaggle_kernel.py", "push", "--slug", KS + sufijo, "--title", "edgelab macro literatura" + sufijo.replace("-", " "), "--script", str(k), "--dataset", DS)

def traer(sufijo=""):          # sufijo "-tz": re-corrida con la zona horaria corregida (auditoría 2026-11-16)
    OUT.mkdir(parents=True, exist_ok=True)
    _py("tools/kaggle_kernel.py", "output", "--slug", KS + sufijo, "--file", "RESULTADO.json", "--out", str(OUT / f"RESULTADO{sufijo.replace('-', '_').upper()}.json"))

if __name__ == "__main__": globals()[sys.argv[1]](*sys.argv[2:])
