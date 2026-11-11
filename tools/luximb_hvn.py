#!/usr/bin/env python3
"""LUXIMB-HVN (docs/research/luximb_hvn_20261111/PREREGISTRO.md): construir, lanzar y traer las tablas de Kaggle.
  python tools/luximb_hvn.py construir
  python tools/luximb_hvn.py lanzar <NQ|USATECH> <DESDE> <HASTA>      # sólo ventanas de desarrollo (los lectores rechazan el holdout)
  python tools/luximb_hvn.py traer <NQ|USATECH> <DESDE> <HASTA>
El análisis es aparte (tools/luximb_hvn_analisis.py) y no corre dentro del kernel (K19)."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools/kaggle_grilla"))
DIR = ROOT / "docs/research/luximb_hvn_20261111"
KERNEL = ROOT / "tools/kaggle_grilla/kernel_luximb_hvn.py"
MODULOS = ["edgelab/holdout.py", "edgelab/research/fuentes_ticks.py", "edgelab/research/areas_expansion.py", "edgelab/research/areas_expansion_run.py",
           "edgelab/research/grilla_masiva.py", "edgelab/research/grilla_generica.py", "edgelab/regimes/state.py", "edgelab/research/agente/regimen.py",
           "edgelab/bridge/indicators/espejo_impulsos.py", "edgelab/research/luximb_grilla.py", "edgelab/research/sintetico.py",
           "edgelab/research/luximb_hvn.py"]
FUENTE = {"NQ": "NQ", "USATECH": "DK:USATECHIDXUSD"}


def construir() -> Path:
    from construir_kernel import construir as K
    c, s = K("tools/kaggle_grilla/luximb_hvn_main.py", str(KERNEL), MODULOS); print("construido", KERNEL.relative_to(ROOT), c[:12]); return KERNEL


def slug(f, d0, d1):
    return f"nicolasbuttaro/luximb-hvn-{f.lower()}-{d0}-{d1}"


def lanzar(f, d0, d1):
    from edgelab.research.embudo_runners import datasets
    construir(); needs, extra = datasets(FUENTE[f], int(d0), int(d1))
    a = [sys.executable, str(ROOT / "tools/kaggle_launch.py"), "--slug", slug(f, d0, d1), "--script", str(KERNEL), "--title", f"luximb hvn {f} {d0} {d1}",
         "--env", f"FUENTE={FUENTE[f]}", "--env", f"DESDE={d0}", "--env", f"HASTA={d1}"]
    for n in needs: a += ["--need", n]
    for e in extra: a += ["--extra-dataset", e]
    r = subprocess.run(a, capture_output=True, text=True); print((r.stdout + r.stderr)[-600:])
    if r.returncode or '"hasError":true' in r.stdout: raise SystemExit(f"FALLÓ el lanzamiento de {slug(f, d0, d1)}")


def traer(f, d0, d1):
    nom = f"LXH_{FUENTE[f].replace('DK:', '')}_{d0}_{d1}"; DIR.mkdir(parents=True, exist_ok=True); (DIR / "tablas").mkdir(parents=True, exist_ok=True)
    for ext in ("json", "csv.gz"):
        r = subprocess.run([sys.executable, str(ROOT / "tools/kaggle_kernel.py"), "output", "--slug", slug(f, d0, d1), "--file", f"{nom}.{ext}",
                            "--out", str(DIR / "tablas" / f"{nom}.{ext}")], capture_output=True, text=True); print(r.stdout.strip()[-200:])
    from edgelab.research.preflight import codigo_vigente
    js = DIR / "tablas" / f"{nom}.json"
    if js.exists():
        viejo = codigo_vigente(json.loads(js.read_text()), ROOT)
        if viejo: raise SystemExit(f"NO VIGENTE: la tabla corrió con otra versión de {viejo}; no se interpreta")


if __name__ == "__main__":
    a = sys.argv[1:]
    {"construir": lambda: construir(), "lanzar": lambda: lanzar(*a[1:4]), "traer": lambda: traer(*a[1:4])}[a[0]]()
