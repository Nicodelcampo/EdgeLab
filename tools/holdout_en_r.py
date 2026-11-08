#!/usr/bin/env python3
"""Holdout en R (pedido de Nico 2026-11-02): re-corre las 16 reglas congeladas sobre el mismo sellado (10-01 -> 10-30) con el riesgo
inicial por operación y suma R = neto / riesgo, por regla y total. Reusa _cargar (remedir_canasta_causal), validas (holdout_individual)
y el KaggleRunner sellado; no cambia reglas, cortes ni topes.
  python tools/holdout_en_r.py lanzar --commit <sha>
  python tools/holdout_en_r.py traer
"""
import argparse, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from remedir_canasta_causal import _cargar  # noqa: E402
from holdout_individual import REGLAS, validas, fuente  # noqa: E402

import os
SAL = ROOT / os.environ.get("HOLDOUT_R_SALIDA", "docs/research/canasta_7_20261030/holdout_en_r"); ACTA = "docs/research/APERTURA_HOLDOUT_CONJUNTA_20261102.md"


def runner():
    from edgelab.research.embudo_runners import KaggleRunner
    return KaggleRunner(dataset_sellado="nicolasbuttaro/edgelab-holdout-sellado", raiz=None)


def lanzar(commit):
    run = runner(); SAL.mkdir(parents=True, exist_ok=True); hf = SAL / "handles.json"; hs = json.loads(hf.read_text()) if hf.exists() else {}
    for cid in REGLAS + ["U1-CRUZADO"]:
        if cid in hs: continue
        try:
            if cid == "U1-CRUZADO":
                sp = dict(cid="U1-CRUZADO-R", experimento="edgelab.research.u1_cruzado_papel", sensor="DK:USATECHIDXUSD", ejecucion="NQ", cuenta_kaggle="nicobuttaro")
                h = run.lanzar(sp, "OPERAR", dict(acta=dict(tipo="holdout_r", acta=ACTA, commit=commit, cid="U1-CRUZADO")), [20261001, int(os.environ.get("HOLDOUT_HASTA", 20261030))])
            else:
                st, acta = _cargar(cid); r = acta["regla"]
                h = run.lanzar(dict(st["spec"], cid=f"{cid}-R"), "ANALIZAR_REGLA", dict(cortes=acta.get("cortes") or st.get("cortes"), celdas=[r["celda"]],
                               tope=r.get("tope"), operaciones=True, acta=dict(tipo="holdout_r", acta=ACTA, commit=commit, cid=cid)), [20261001, int(os.environ.get("HOLDOUT_HASTA", 20261030))])
        except Exception as ex: print("no se lanzó", cid, str(ex)[-200:]); continue
        hs[cid] = h; hf.write_text(json.dumps(hs, indent=1)); print("lanzada", cid, h, flush=True)


def traer():
    run = runner(); hs = json.loads((SAL / "handles.json").read_text()); filas = []
    for cid, h in hs.items():
        f = SAL / f"{cid}.json"
        if not f.exists():
            e = run.estado(h)
            if e != "complete": print(cid, e); continue
            f.write_text(json.dumps(run.traer(h), indent=1, default=float))
        o = json.loads(f.read_text()).get("operaciones") or {}
        if cid == "U1-CRUZADO": inst = {"NQ", "USATECHIDXUSD"}
        else: sp = _cargar(cid)[0]["spec"]; inst = {fuente(sp["sensor"]), fuente(sp.get("ejecucion") or sp["sensor"])}
        v = validas(inst); ses = np.array(o.get("ses", []), int); neto = np.array(o.get("neto", []), float)
        rg = np.array([np.nan if x is None else x for x in o.get("riesgo", [np.nan] * len(neto))], float); m = np.isin(ses, list(v))
        R = neto[m] / rg[m]
        filas.append(dict(regla=cid, n=int(m.sum()), neto=float(neto[m].sum()), riesgo_medio=float(np.nanmean(rg[m])) if m.any() else None,
                          R_total=float(np.nansum(R)), R_por_op=float(np.nanmean(R)) if m.any() else None, acierto=float((neto[m] > 0).mean()) if m.any() else None))
    tot = sum(f["R_total"] for f in filas); n = sum(f["n"] for f in filas)
    out = dict(reglas=filas, R_total=tot, n_total=n, R_por_op=tot / n if n else None)
    (SAL / "RESULTADO.json").write_text(json.dumps(out, indent=1, default=float)); return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("lanzar", "traer")); ap.add_argument("--commit", default=""); a = ap.parse_args()
    lanzar(a.commit) if a.cmd == "lanzar" else print(json.dumps(traer(), indent=1, default=float))
