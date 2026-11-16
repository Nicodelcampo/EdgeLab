#!/usr/bin/env python3
"""FUNDEDSYNCSTACK por la cadena (pre-registro docs/research/fundedsyncstack_20261115/PREREGISTRO_CADENA.md).
  python tools/fundedsync_cadena.py lanzar      # kernel en Kaggle (M1 Nasdaq 2012 → 2026-09, costos NQ, nulo intradía ×20)
  python tools/fundedsync_cadena.py traer       # RESULTADO.json y operaciones a docs/research/fundedsyncstack_20261115/cadena/
Incrusta el paquete como tools/m1_intradia.py::_incrustar (módulos por nombre en sys.modules, en orden de dependencias).
"""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
KS = "nicolasbuttaro/edgelab-fundedsync-cadena"; OUT = ROOT / "docs/research/fundedsyncstack_20261115/cadena"
PKG = "edgelab.research.fundedsyncstack"
ORDEN = ("contracts", "base_series", "modulos_a1_a20_f_s", "modulos_p_c_v_o", "modulos_r_z_e_q", "modulos_w_n_t", "motor_cartera", "__init__")


def construir() -> Path:
    pre = "import sys, types\n"
    for nom, ruta in (("edgelab", None), ("edgelab.research", None), ("edgelab.holdout", "edgelab/holdout.py"),
                      ("edgelab.research.ema_zones", "edgelab/research/ema_zones.py"), ("edgelab.research.fuentes_ticks", "edgelab/research/fuentes_ticks.py"),
                      ("m1_intradia", "edgelab/research/m1_intradia.py")):
        pre += f"_m = types.ModuleType({nom!r}); _m.__path__ = []; sys.modules[{nom!r}] = _m\n"
        if ruta: pre += f"exec(compile({(ROOT / ruta).read_text()!r}, {ruta!r}, 'exec'), _m.__dict__)\n"
        if "." in nom: pre += f"setattr(sys.modules[{nom.rsplit('.', 1)[0]!r}], {nom.rsplit('.', 1)[1]!r}, _m)\n"
    pre += f"_p = types.ModuleType({PKG!r}); _p.__path__ = []; _p.__package__ = {PKG!r}; sys.modules[{PKG!r}] = _p; sys.modules['edgelab.research'].fundedsyncstack = _p\n"
    for m in ORDEN:
        src = (ROOT / f"edgelab/research/fundedsyncstack/{m}.py").read_text(encoding="utf-8")
        if m == "__init__":
            pre += f"_p.__dict__['__name__'] = {PKG!r}\nexec(compile({src!r}, '{PKG}/__init__.py', 'exec'), _p.__dict__)\n"
        else:
            pre += (f"_s = types.ModuleType('{PKG}.{m}'); _s.__package__ = {PKG!r}; sys.modules['{PKG}.{m}'] = _s\n"
                    f"exec(compile({src!r}, '{PKG}/{m}.py', 'exec'), _s.__dict__); setattr(_p, {m!r}, _s)\n")
    k = ROOT / "data/fundedsync_kernel.py"; k.parent.mkdir(exist_ok=True)
    k.write_text(pre + (ROOT / "tools/kaggle_grilla/fundedsync_main.py").read_text(encoding="utf-8"), encoding="utf-8"); return k


def lanzar():
    k = construir(); print("kernel", k.stat().st_size, "bytes")
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "push", "--slug", KS, "--title", "edgelab fundedsync cadena", "--script", str(k),
                    "--dataset", "nicolasbuttaro/edgelab-sqx-m1"], cwd=ROOT, check=True)


def holdout(commit):
    """Apertura única (ACTA_HOLDOUT.md): registra la ventana y lanza T, Z y R sobre desarrollo + USATECH sellado."""
    import json, os
    sys.path.insert(0, str(ROOT)); from edgelab.research import holdout_ventanas as HV
    cid = "FUNDEDSYNC::holdout_TZR_20261116"
    if (pr := HV.problemas("FUNDEDSYNC", 20261001, cid)): raise SystemExit("no se abre: " + "; ".join(pr))
    HV.registrar_apertura("FUNDEDSYNC", cid, 20261001, n_fijo=0)
    acta = dict(acta="docs/research/fundedsyncstack_20261115/ACTA_HOLDOUT.md", commit=commit, familia="FUNDEDSYNC", cid=cid)
    k = construir(); txt = k.read_text(encoding="utf-8")
    k.write_text("import os\nos.environ.update(SELLADO='1', HASTA='20261113', ACTA_JSON=" + repr(json.dumps(acta)) + ")\n" + txt, encoding="utf-8")
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "push", "--slug", KS + "-h", "--title", "edgelab fundedsync cadena h", "--script", str(k),
                    "--dataset", "nicolasbuttaro/edgelab-sqx-m1", "--dataset", "nicolasbuttaro/edgelab-holdout-sellado"], cwd=ROOT, check=True)


def traer_holdout():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in ("RESULTADO_HOLDOUT.json", "FUNDEDSYNC_HOLDOUT_OPS.csv"):
        subprocess.run([sys.executable, "tools/kaggle_kernel.py", "output", "--slug", KS + "-h", "--file", f, "--out", str(OUT / f)], cwd=ROOT, check=True)


def traer():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in ("RESULTADO.json", "FUNDEDSYNC_OPS.csv.gz"):
        subprocess.run([sys.executable, "tools/kaggle_kernel.py", "output", "--slug", KS, "--file", f, "--out", str(OUT / f)], cwd=ROOT, check=True)


if __name__ == "__main__":
    globals()[sys.argv[1]](*sys.argv[2:])
