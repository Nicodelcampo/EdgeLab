#!/usr/bin/env python3
"""Holdout exploratorio de CANASTA-GLOBAL (pre-registro docs/research/canasta_global_20261108/PREREGISTRO_HOLDOUT.md).
Reusa el KaggleRunner sellado y la etapa ANALIZAR_REGLA como `tools/holdout_en_r.py`.
  python tools/holdout_canasta_global.py lanzar --commit <sha>
  python tools/holdout_canasta_global.py traer
"""
import argparse, json, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/canasta_global_20261108"; SAL = DIR / "holdout"; ACTA = "docs/research/canasta_global_20261108/PREREGISTRO_HOLDOUT.md"
P_SEL, HASTA = 0.0099, 20261107


def reglas():
    from edgelab.research import grilla_masiva as GM
    r = json.loads((DIR / "RESULTADO_CANASTA_GLOBAL.json").read_text()); out = []
    for i, x in enumerate(r["reglas"]):
        c = json.loads((ROOT / "data/cubos" / f"{x['cubo']}.json").read_text())["cubo"]
        forma = [{"grupo": k, "ge": k, "le": k, "eq_any": k + 1, "extremos": 3}[m] for _, k, m in c["perillas"]]
        out.append((f"{x['cubo']}#{i}", x["cubo"], [int(v) for v in np.unravel_index(x["celda_plana"], forma)]))
    return out


def lanzar(commit):
    from atlas_contexto_r import _todas_las_campanas_r
    from edgelab.research.embudo_runners import KaggleRunner
    camp = dict(_todas_las_campanas_r()); run = KaggleRunner(dataset_sellado="nicolasbuttaro/edgelab-holdout-sellado", raiz=None)
    SAL.mkdir(parents=True, exist_ok=True); hf = SAL / "handles.json"; hs = json.loads(hf.read_text()) if hf.exists() else {}
    for clave, cubo, celda in reglas():
        if clave in hs: continue
        st = camp[cubo]; sp = dict(st["spec"], cid=f"CG-{clave.replace('#', '-')}")
        try:
            h = run.lanzar(sp, "ANALIZAR_REGLA", dict(cortes=st["cortes"], celdas=[celda], operaciones=True,
                           acta=dict(tipo="holdout_canasta_global", acta=ACTA, commit=commit, cid=clave)), [20261001, HASTA])
        except Exception as ex: print("no se lanzó", clave, str(ex)[-200:]); continue
        hs[clave] = h; hf.write_text(json.dumps(hs, indent=1)); print("lanzada", clave, h, flush=True)


def traer():
    from edgelab.holdout import sesion_excluida
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(dataset_sellado="nicolasbuttaro/edgelab-holdout-sellado", raiz=None); hs = json.loads((SAL / "handles.json").read_text())
    por, faltan = {}, []
    for clave, h in hs.items():
        f = SAL / f"{clave.replace('#', '-')}.json"
        if not f.exists():
            e = run.estado(h)
            if e != "complete": faltan.append((clave, e)); continue
            f.write_text(json.dumps(run.traer(h), indent=1, default=float))
        o = json.loads(f.read_text()).get("operaciones") or {}
        por[clave] = (np.array(o.get("ses", []), int), np.array(o.get("neto", []), float))
    if faltan: print("faltan", faltan); return
    dias = sorted({int(d) for s, _ in por.values() for d in s})
    X = np.zeros((len(dias), len(por))); pos = {d: i for i, d in enumerate(dias)}
    for j, (s, r) in enumerate(por.values()):
        for d, v in zip(s, r):
            if np.isfinite(v): X[pos[int(d)], j] += v
    c = X.mean(1); rng = np.random.default_rng(20261108)
    Z = (rng.choice((-1.0, 1.0), size=(10000, len(c))) * c).mean(1); p = float((1 + (Z >= c.mean()).sum()) / 10001)
    from scipy.stats import chi2
    pf = float(chi2.sf(-2 * (math.log(P_SEL) + math.log(p)), 4))
    out = dict(sesiones=len(dias), dias=dias, media_r_sesion=float(c.mean()), r_total=float(c.sum()), p_holdout=p, p_seleccion=P_SEL,
               p_fisher=pf, por_regla={k: dict(n=int(len(s)), r_medio=float(np.nanmean(r)) if len(r) else None) for k, (s, r) in por.items()})
    (SAL / "RESULTADO_HOLDOUT.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps({k: out[k] for k in ("sesiones", "media_r_sesion", "p_holdout", "p_fisher")}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["lanzar", "traer"]); ap.add_argument("--commit", default=""); a = ap.parse_args()
    lanzar(a.commit) if a.cmd == "lanzar" else traer()
