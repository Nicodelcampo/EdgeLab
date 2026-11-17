#!/usr/bin/env python3
"""ORB y pre-rango 08:12 sobre M1 de Dukascopy en Kaggle (edgelab/research/m1_intradia.py).
  python tools/m1_intradia.py lanzar   # kernel con el módulo incrustado; monta edgelab-sqx-m1 (M1, lo sube Antigravity) y edgelab-sqx-barras (spreads)
  python tools/m1_intradia.py traer    # baja RESULTADO.json a docs/research/m1_intradia_20261114/
  python tools/m1_intradia.py lanzar_vida / traer_vida   # paso 1b de urgencia_vs_evidencia_20261117 (agregados mensuales de toda la grilla)
"""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
KS = "nicolasbuttaro/edgelab-m1-intradia"; DS = ("nicolasbuttaro/edgelab-sqx-m1", "nicolasbuttaro/edgelab-sqx-barras")
def lanzar(lote="1"):
    k = ROOT / "data/m1_intradia_kernel.py"; k.parent.mkdir(exist_ok=True)
    pre = "" if lote == "1" else f"import os\nos.environ['LOTE'] = '2'\nos.environ['IDX'] = 'NQ_M1_dukas,SP_M1_dukas,DJ_M1_dukas,DEUIDXEUR'\nos.environ['REPS'] = '20'\n"
    k.write_text(pre + "import sys, types\n_m = types.ModuleType('m1_intradia')\nexec(compile(" + repr((ROOT / "edgelab/research/m1_intradia.py").read_text()) +
                 ", 'm1_intradia.py', 'exec'), _m.__dict__)\nsys.modules['m1_intradia'] = _m\n" + (ROOT / "tools/kaggle_grilla/m1_intradia_main.py").read_text())
    ks = KS if lote == "1" else KS + "-lote2"
    a = [sys.executable, "tools/kaggle_kernel.py", "push", "--slug", ks, "--title", ks.split("/")[1].replace("-", " "), "--script", str(k)]
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


def lanzar_vida():
    """Paso 1b (docs/research/urgencia_vs_evidencia_20261117/PREREGISTRO_PASO1B.md): agregados mensuales de toda la grilla."""
    k = ROOT / "data/m1_vida_kernel.py"; k.parent.mkdir(exist_ok=True); k.write_text(_incrustar("tools/kaggle_grilla/m1_vida_main.py"))
    a = [sys.executable, "tools/kaggle_kernel.py", "push", "--slug", "nicolasbuttaro/edgelab-m1-vida", "--title", "edgelab m1 vida", "--script", str(k)]
    for d in DS: a += ["--dataset", d]
    subprocess.run(a, cwd=ROOT, check=True)


def traer_vida():
    o = ROOT / "docs/research/urgencia_vs_evidencia_20261117"
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "output", "--slug", "nicolasbuttaro/edgelab-m1-vida", "--file", "M1_VIDA.json",
                    "--out", str(o / "M1_VIDA.json")], cwd=ROOT, check=True)


def _incrustar(main: str) -> str:
    """Kernel autocontenido: el paquete edgelab mínimo (holdout, ema_zones, fuentes_ticks) + m1_intradia + el main."""
    pre = "import sys, types\n"
    for nom, ruta in (("edgelab", None), ("edgelab.research", None), ("edgelab.holdout", "edgelab/holdout.py"),
                      ("edgelab.research.ema_zones", "edgelab/research/ema_zones.py"), ("edgelab.research.fuentes_ticks", "edgelab/research/fuentes_ticks.py"),
                      ("m1_intradia", "edgelab/research/m1_intradia.py")):
        pre += f"_m = types.ModuleType({nom!r}); _m.__path__ = []; sys.modules[{nom!r}] = _m\n"
        if ruta: pre += f"exec(compile({(ROOT / ruta).read_text()!r}, {ruta!r}, 'exec'), _m.__dict__)\n"
        if "." in nom: pre += f"setattr(sys.modules[{nom.rsplit('.', 1)[0]!r}], {nom.rsplit('.', 1)[1]!r}, _m)\n"
    return pre + (ROOT / main).read_text()


def lanzar_vwapb_holdout(acta_json, desde="20261001", hasta="20261231"):
    """Holdout de VWAPB-3 (ACTA_HOLDOUT_VWAPB3.md): sólo después de registrar la apertura. Fricción canónica de cada futuro (edgelab/costos.py)."""
    import json, os
    sys.path.insert(0, str(ROOT)); from edgelab.research.embudo_runners import friccion
    fr = {i: friccion(i)[0] for i in ("NQ", "YM", "ES")}
    k = ROOT / "data/vwapb_holdout_kernel.py"; k.parent.mkdir(exist_ok=True)
    env = dict(ACTA_JSON=acta_json, FRICCION_JSON=json.dumps(fr), DESDE=desde, HASTA=hasta)
    k.write_text("import os\n" + "".join(f"os.environ[{a!r}] = {b!r}\n" for a, b in env.items()) + _incrustar("tools/kaggle_grilla/vwapb_holdout_main.py"))
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "push", "--slug", "nicolasbuttaro/edgelab-vwapb3-holdout", "--title", "edgelab vwapb3 holdout",
                    "--script", str(k), "--dataset", "nicolasbuttaro/edgelab-holdout-sellado"], cwd=ROOT, check=True)


def traer_vwapb_holdout():
    o = ROOT / "docs/research/m1_intradia_20261114"
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "output", "--slug", "nicolasbuttaro/edgelab-vwapb3-holdout", "--file", "RESULTADO.json",
                    "--out", str(o / "RESULTADO_HOLDOUT_VWAPB3.json")], cwd=ROOT, check=True)


def relanzar_tz():
    """Auditoría 2026-11-16: re-corre con la zona horaria corregida SÓLO los índices que venían en UTC (lote 1: los 5; lote 2: DAX; VWAPB: todos)."""
    for ks, env, main in ((KS + "-tz", "import os\nos.environ.update(IDX='USSC2000IDXUSD,DEUIDXEUR,JPNIDXJPY,GBRIDXGBP,EUSIDXEUR', REPS='10')\n", "m1_intradia_main.py"),
                          (KS + "-lote2-tz", "import os\nos.environ.update(LOTE='2', IDX='DEUIDXEUR', REPS='10')\n", "m1_intradia_main.py"),
                          ("nicolasbuttaro/edgelab-vwapb-ops-tz", "", "vwapb_ops_main.py")):
        k = ROOT / f"data/{ks.split('/')[1]}.py"; k.write_text(env + _incrustar(f"tools/kaggle_grilla/{main}"))     # paquete edgelab mínimo incluido
        a = [sys.executable, "tools/kaggle_kernel.py", "push", "--slug", ks, "--title", ks.split("/")[1].replace("-", " "), "--script", str(k)]
        for d in DS: a += ["--dataset", d]
        subprocess.run(a, cwd=ROOT, check=True)


def traer_tz():
    o = ROOT / "docs/research/auditoria_corridas_20261116"; o.mkdir(parents=True, exist_ok=True)
    for ks, f, out in ((KS + "-tz", "RESULTADO.json", "M1_INTRADIA_LOTE1_TZ.json"), (KS + "-lote2-tz", "RESULTADO.json", "M1_INTRADIA_LOTE2_TZ.json"),
                       ("nicolasbuttaro/edgelab-vwapb-ops-tz", "VWAPB_OPS.csv.gz", "VWAPB_OPS_TZ.csv.gz")):
        subprocess.run([sys.executable, "tools/kaggle_kernel.py", "output", "--slug", ks, "--file", f, "--out", str(o / out)], cwd=ROOT, check=True)


def traer_vwapb():
    o = ROOT / "data/vwapb"; o.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "output", "--slug", "nicolasbuttaro/edgelab-vwapb-ops", "--file", "VWAPB_OPS.csv.gz", "--out", str(o / "VWAPB_OPS.csv.gz")], cwd=ROOT, check=True)


def traer(lote="1"):
    o = ROOT / "docs/research/m1_intradia_20261114"; o.mkdir(parents=True, exist_ok=True)
    ks, f = (KS, "RESULTADO.json") if lote == "1" else (KS + "-lote2", "RESULTADO_LOTE2.json")
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "output", "--slug", ks, "--file", "RESULTADO.json", "--out", str(o / f)], cwd=ROOT, check=True)
if __name__ == "__main__": globals()[sys.argv[1]](*sys.argv[2:])
