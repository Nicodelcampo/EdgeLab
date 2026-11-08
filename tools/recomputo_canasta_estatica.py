#!/usr/bin/env python3
"""Recomputo contra ticks de la canasta estática del régimen corto (PREAPERTURA-ES, PREAPERTURA-NQ, DRC-YM-4) con los cortes congelados
de sus campañas en R (estado.json del embudo) y la etapa ANALIZAR_REGLA. Compara con series_diarias_regimen_20261106.json.
  python tools/recomputo_canasta_estatica.py lanzar | traer"""
import glob, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
SAL = ROOT / "docs/research/regimen_corto_20261106_recomputo"
REGLAS = {"PREAPERTURA-ES": ("PREAPERTURA-ES-R", [2, 0, 1, 0, 0, 5]), "PREAPERTURA-NQ": ("PREAPERTURA-NQ-R", [2, 0, 0, 0, 1, 5]),
          "DRC-YM-4": ("DRC-YM-R", [0, 1, 3, 0, 2, 0, 2, 0, 2, 2, 4])}

def _st(cid): return json.loads(Path(glob.glob(str(ROOT / f"docs/research/*/embudo/{cid}/estado.json"))[0]).read_text())

def lanzar():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); cs = run.cuentas(); hf = SAL / "handles.json"; hs = json.loads(hf.read_text()) if hf.exists() else {}
    for regla, (cid, celda) in REGLAS.items():
        st = _st(cid); sp = st["spec"]
        for tramo, per in (("desc", sp["desc"]), ("oos", sp["oos"])):
            k = f"{regla}/{tramo}"
            if k in hs: continue
            h = run.lanzar(dict(sp, cid=f"{regla}-REC-{tramo}", cuenta_kaggle=cs[len(hs) % len(cs)]), "ANALIZAR_REGLA",
                           dict(cortes=st["cortes"], celdas=[celda], operaciones=True), [int(per[0]), int(per[1])])
            hs[k] = dict(handle=h, ts=time.time()); hf.write_text(json.dumps(hs, indent=1)); print("lanzada", k, h)

def traer():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); hs = json.loads((SAL / "handles.json").read_text()); pend = 0
    for k, h in hs.items():
        f = SAL / (k.replace("/", "__") + ".json")
        if f.exists(): continue
        if run.estado(h["handle"]) != "complete": pend += 1; continue
        f.write_text(json.dumps(run.traer(h["handle"]), default=float))
    print("pendientes", pend)

if __name__ == "__main__":
    lanzar() if sys.argv[1] == "lanzar" else traer()
