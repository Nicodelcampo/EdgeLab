#!/usr/bin/env python3
"""Seguimiento forward bajo demanda (cuando Nico sube datos sellados nuevos): cartera v2/v3, cartera B (T+Z+R), Franklin, PREAPERTURA-ES, SOM. (TURTLES-ORO salió el 2026-11-17: 0,4 operaciones por mes, no pasa K27; su seguimiento queda a mano en tools/turtles_oro_seguimiento.py.)

  python tools/seguimiento_forward.py <HASTA AAAAMMDD> [commit]   # lanza los tres kernels, espera, trae y resume
Orquesta, sin lógica propia: tools/cartera_v2_forward.py, tools/fundedsync_cadena.py (forward, traer_forward, cartera_b) y
tools/franklin_seguimiento.py. Pre-registros: cartera_20261116/PREREGISTRO_FORWARD_V2.md, fundedsyncstack_20261115/PREREGISTRO_CARTERA_B.md,
reels_20261116/ACTA_HOLDOUT_FRANKLIN.md, cartera_20261116/PREREGISTRO_TANDA5.md.
"""
import json, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; PY = sys.executable


def _run(*a, check=True):
    print("$", " ".join(a), flush=True); return subprocess.run([PY, *a], cwd=ROOT, check=check, capture_output=True, text=True)


def _esperar(slug, max_min=90):
    for _ in range(max_min * 2):
        s = _run("tools/kaggle_kernel.py", "status", "--slug", slug, check=False).stdout
        if any(k in s.lower() for k in ("complete", "error", "cancel")): return s.strip().splitlines()[-1]
        time.sleep(30)
    return "timeout"


def main(hasta, commit=""):
    _run("tools/cartera_v2_forward.py", "lanzar", "--hasta", hasta, "--commit", commit)
    _run("tools/fundedsync_cadena.py", "forward", hasta, commit)
    _run("tools/franklin_seguimiento.py", "forward", hasta, commit)
    _run("tools/som_seguimiento.py", "forward", hasta, commit)
    print("fundedsync:", _esperar(f"nicolasbuttaro/edgelab-fundedsync-cadena-fw{hasta}")); print("franklin:", _esperar(f"nicolasbuttaro/edgelab-franklin-seg-fw{hasta}"))
    print("som:", _esperar(f"nicolasbuttaro/edgelab-som-seg-fw{hasta}"))
    for _ in range(180):                                                       # la cartera v2/v3 son varios kernels: traer hasta que no falte nada
        r = _run("tools/cartera_v2_forward.py", "traer", "--hasta", hasta, check=False)
        if "faltan" not in r.stdout: print(r.stdout[-1500:]); break
        time.sleep(30)
    _run("tools/fundedsync_cadena.py", "traer_forward", hasta)
    print(_run("tools/fundedsync_cadena.py", "cartera_b", hasta).stdout)
    print(_run("tools/franklin_seguimiento.py", "traer_forward", hasta).stdout)
    print(_run("tools/som_seguimiento.py", "traer_forward", hasta).stdout)
    print(_run("tools/regimen_forward.py", hasta, check=False).stdout)      # REGIMEN-FORWARD (2026-11-19): canasta T+R, SOM y Franklin como regímenes


if __name__ == "__main__":
    main(*sys.argv[1:])
