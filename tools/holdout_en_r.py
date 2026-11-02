#!/usr/bin/env python3
"""Holdout en R (pedido de Nico, 2026-11-02): las 15 reglas de grilla (12 nominadas + 3 forzadas) y U1-CRUZADO, con su regla congelada,
re-corridas sobre el MISMO sellado (10-01 → 10-30) sólo para obtener el riesgo inicial de cada operación (entrada real a stop).
R = neto / riesgo. Se informa total de R y R medio por operación, por regla y para todas juntas, con todas las sesiones y sólo válidas.
Reusa _cargar (remedir_canasta_causal), REGLAS y validas (holdout_individual).
  python tools/holdout_en_r.py lanzar --commit <sha>
  python tools/holdout_en_r.py traer
"""
import argparse, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from remedir_canasta_causal import _cargar  # noqa: E402
from holdout_individual import REGLAS, validas, fuente  # noqa: E402

SAL = ROOT / "docs/research/canasta_7_20261030/holdout_en_r"; PER = [20261001, 20261030]


def lanzar(commit):
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(dataset_sellado="nicolasbuttaro/edgelab-holdout-sellado", raiz=None); SAL.mkdir(parents=True, exist_ok=True)
    hf = SAL / "handles.json"; hs = json.loads(hf.read_text()) if hf.exists() else {}; cs = ["nicolasbuttaro", "nicobuttaro"]
    acta = dict(tipo="holdout_en_r", acta="docs/research/APERTURA_HOLDOUT_CONJUNTA_20261102.md", commit=commit)
    for i, cid in enumerate(REGLAS + ["U1-CRUZADO"]):
        if cid in hs: continue
        try:
            if cid == "U1-CRUZADO":
                sp = dict(cid="U1-CRUZADO-R", experimento="edgelab.research.u1_cruzado_papel", sensor="DK:USATECHIDXUSD", ejecucion="NQ", cuenta_kaggle=cs[i % 2])
                h = run.lanzar(sp, "OPERAR", dict(acta=dict(acta, cid=cid)), PER)
            else:
                st, a = _cargar(cid); r = a["regla"]; sp = dict(st["spec"], cid=f"{cid}-R", cuenta_kaggle=cs[i % 2])
                h = run.lanzar(sp, "ANALIZAR_REGLA", dict(cortes=a.get("cortes") or st.get("cortes"), celdas=[r["celda"]], tope=r.get("tope"),
                                                          operaciones=True, acta=dict(acta, cid=cid)), PER)
        except Exception as ex: print("no se lanzó", cid, str(ex)[-200:]); continue
        hs[cid] = h; hf.write_text(json.dumps(hs, indent=1)); print("lanzada", cid, h, flush=True)


def traer():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(dataset_sellado="nicolasbuttaro/edgelab-holdout-sellado", raiz=None); hs = json.loads((SAL / "handles.json").read_text())
    filas, todas = [], dict(r=[], rv=[])
    for cid, h in hs.items():
        f = SAL / f"{cid}.json"
        if not f.exists():
            e = run.estado(h); 
            if e != "complete": print(cid, e); continue
            f.write_text(json.dumps(run.traer(h), indent=1, default=float))
        o = json.loads(f.read_text()).get("operaciones") or {}
        ses = np.array(o.get("ses", []), int); x = np.array(o.get("neto", []), float); rk = np.array([np.nan if v is None else v for v in o.get("riesgo", [])], float)
        if cid == "U1-CRUZADO": inst = {"NQ", "USATECHIDXUSD"}
        else: sp = _cargar(cid)[0]["spec"]; inst = {fuente(sp["sensor"]), fuente(sp.get("ejecucion") or sp["sensor"])}
        R = x / rk; ok = np.isfinite(R); v = ok & np.isin(ses, list(validas(inst)))
        fila = dict(regla=cid, n=int(ok.sum()), R_total=float(R[ok].sum()), R_medio=float(R[ok].mean()) if ok.any() else None,
                    riesgo_medio_pts=float(rk[ok].mean()) if ok.any() else None, n_validas=int(v.sum()), R_total_validas=float(R[v].sum()),
                    R_medio_validas=float(R[v].mean()) if v.any() else None, neto_pts=float(x[ok].sum()), acierto=float((x[ok] > 0).mean()) if ok.any() else None)
        filas.append(fila); todas["r"] += R[ok].tolist(); todas["rv"] += R[v].tolist()
    tot = dict(n=len(todas["r"]), R_total=float(np.sum(todas["r"])), R_medio=float(np.mean(todas["r"])) if todas["r"] else None,
               n_validas=len(todas["rv"]), R_total_validas=float(np.sum(todas["rv"])), R_medio_validas=float(np.mean(todas["rv"])) if todas["rv"] else None)
    (SAL / "RESULTADO.json").write_text(json.dumps(dict(por_regla=filas, total=tot), indent=1, default=float)); return filas, tot


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("lanzar", "traer")); ap.add_argument("--commit", default=""); a = ap.parse_args()
    if a.cmd == "lanzar": lanzar(a.commit)
    else:
        f, t = traer(); [print(x) for x in f]; print("TOTAL", t)
