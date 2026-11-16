#!/usr/bin/env python3
"""Cartera con el período nuevo (pre-registro docs/research/cartera_20261116/PREREGISTRO.md, 2026-11-16).

Universo: todas las reglas con holdout ABIERTO (ACTA_HOLDOUT.json vigente, desde 2026-10-01). Reusa el KaggleRunner sellado y la etapa
ANALIZAR_REGLA con operaciones (como tools/holdout_en_r.py y tools/remedir_canasta_causal.py), sin cambiar reglas, cortes ni topes.

  python tools/cartera_nov.py universo                      # lista las reglas y qué tramos les faltan
  python tools/cartera_nov.py lanzar --commit <sha>         # holdout 10-01 → HASTA (sellado) + desarrollo DESC/REP que falte
  python tools/cartera_nov.py traer                         # baja a docs/research/cartera_20261116/ops/<cid>__<tramo>.json
"""
import argparse, glob, json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/cartera_20261116"; OPS = DIR / "ops"; HF = DIR / "handles.json"
ACTA = "docs/research/cartera_20261116/PREREGISTRO.md"; SELLADO = "nicolasbuttaro/edgelab-holdout-sellado"
HASTA = int(os.environ.get("CARTERA_HASTA", 20261113))
DEV_PREVIO = ROOT / "docs/research/canasta_7_20261030/desarrollo_en_r"          # desarrollo en R ya medido (16 reglas, código causal)


def universo() -> list:
    """Reglas con acta de holdout vigente (las ANULADAS no entran): cid, spec de la campaña, regla congelada y cortes."""
    out = []
    actas = sorted(glob.glob(str(ROOT / "docs/research/*/embudo/*/ACTA_HOLDOUT.json"))) + \
        sorted(glob.glob(str(ROOT / "docs/research/regimen_corto_20261106_recomputo/ACTA_HOLDOUT_*.json")))
    for a in actas:
        A = json.loads(Path(a).read_text(encoding="utf-8")); cid = A["cid"]
        est = sorted(glob.glob(str(ROOT / f"docs/research/*/embudo/{cid}/estado.json"))) + sorted(glob.glob(str(ROOT / f"docs/research/*/embudo/{cid}-R/estado.json")))
        st = json.loads(Path(est[0]).read_text(encoding="utf-8"))
        out.append(dict(cid=cid, acta=str(Path(a).relative_to(ROOT)), spec=st["spec"], celda=A["regla"]["celda"], tope=A["regla"].get("tope"),
                        cortes=A.get("cortes") or st.get("cortes"), n_fijo=A.get("n_fijo")))
    return out


def tramos(r) -> dict:
    sp = r["spec"]; t = {"hold": [20261001, HASTA]}
    if not (DEV_PREVIO / f"{r['cid']}__desc.json").exists(): t["desc"] = [int(x) for x in sp["desc"]]
    if not (DEV_PREVIO / f"{r['cid']}__rep.json").exists(): t["rep"] = [int(x) for x in sp["oos"]]
    return t


def lanzar(commit):
    from edgelab.research.embudo_runners import KaggleRunner
    dev, sel = KaggleRunner(raiz=None), KaggleRunner(dataset_sellado=SELLADO, raiz=None); cs = dev.cuentas()
    DIR.mkdir(parents=True, exist_ok=True); hs = json.loads(HF.read_text()) if HF.exists() else {}
    for i, r in enumerate(universo()):
        for tramo, per in tramos(r).items():
            clave = f"{r['cid']}__{tramo}"
            if clave in hs: continue
            sp = dict(r["spec"], cid=f"CN{os.environ.get('CN_SUFIJO', '')}-{r['cid']}-{tramo}"[:30], cuenta_kaggle=("nicolasbuttaro" if tramo == "hold" else cs[(len(hs) + i) % len(cs)]))
            params = dict(cortes=r["cortes"], celdas=[r["celda"]], tope=r["tope"], operaciones=True)
            if tramo == "hold": params["acta"] = dict(tipo="holdout_continuacion_20261116", acta=ACTA, commit=commit, cid=r["cid"], acta_regla=r["acta"])
            try: h = (sel if tramo == "hold" else dev).lanzar(sp, "ANALIZAR_REGLA", params, per)
            except Exception as ex: print("no se lanzó", clave, str(ex)[-300:], flush=True); continue
            hs[clave] = dict(handle=h, periodo=per, ts=time.time()); HF.write_text(json.dumps(hs, indent=1)); print("lanzada", clave, h, flush=True)


def traer():
    from edgelab.research.embudo_runners import KaggleRunner
    dev, sel = KaggleRunner(raiz=None), KaggleRunner(dataset_sellado=SELLADO, raiz=None); hs = json.loads(HF.read_text()); OPS.mkdir(parents=True, exist_ok=True)
    falta = []
    for clave, x in hs.items():
        f = OPS / f"{clave}.json"
        if f.exists(): continue
        run = sel if clave.endswith("__hold") else dev; e = run.estado(x["handle"])
        if e != "complete": falta.append((clave, e)); continue
        f.write_text(json.dumps(run.traer(x["handle"]), indent=1, default=float)); print("traída", clave, flush=True)
    print("faltan", len(falta), falta)
    return falta


def relanzar(commit, tanda=4):
    """Los kernels que Kaggle no arrancó (tope de corridas simultáneas: «no_encontrado» más de 20 min después) se relanzan de a `tanda`,
    sólo cuando hay menos de `tanda` corriendo. Misma regla, mismo período: no cambia nada de lo pre-registrado."""
    falta = traer(); hs = json.loads(HF.read_text())
    corriendo = sum(e == "running" for _, e in falta)
    viejos = [c for c, e in falta if e in ("no_encontrado", "error") and time.time() - hs[c].get("ts", 0) > 1200]
    for c in viejos[:max(0, tanda - corriendo)]: hs.pop(c)
    HF.write_text(json.dumps(hs, indent=1))
    if viejos[:max(0, tanda - corriendo)]: lanzar(commit)
    return len(falta)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("universo", "lanzar", "traer", "relanzar")); ap.add_argument("--commit", default=""); a = ap.parse_args()
    if a.cmd == "universo":
        for r in universo(): print(r["cid"], r["spec"]["sensor"], r["spec"].get("ejecucion"), sorted(tramos(r)))
    elif a.cmd == "relanzar": relanzar(a.commit)
    else: lanzar(a.commit) if a.cmd == "lanzar" else traer()
