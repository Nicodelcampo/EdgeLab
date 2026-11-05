#!/usr/bin/env python3
"""Atlas de ideas transferibles en R (docs/research/atlas_ideas_r_20261102/PREREGISTRO_ATLAS_IDEAS_R.md): etapa MARGINALES con
estadistico R sobre DESC y réplica de cada campaña del relanzamiento en R; meta-análisis de efectos aleatorios (DerSimonian-Laird) por
etiqueta de componente de ejecución entre familias; BH q 0,10 en DESC y confirmación en réplica. Reusa _cargar del embudo vía glob
de estados y el KaggleRunner; idempotente (relanzar completa lo que no entró por cupo).
  python tools/atlas_ideas_r.py lanzar | traer | analizar
"""
import argparse, glob, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
SAL = ROOT / "docs/research/atlas_ideas_r_20261102"; CAMP = ROOT / "docs/research/relanzamiento_R_20261102/CAMPANAS.json"
COMP = ("ejecución.entrada", "ejecución.objetivo", "ejecución.stop", "ejecución.be")


def _estado(cid):
    """Estado de la campaña ORIGINAL (cortes del DESC y ventanas): cid sin el sufijo -R."""
    base = cid[:-2]; f = sorted(glob.glob(str(ROOT / f"docs/research/*/embudo/{base}/estado.json")))
    return json.loads(Path(f[0]).read_text()) if f else None


def lanzar():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); cs = run.cuentas(); SAL.mkdir(parents=True, exist_ok=True); hf = SAL / "handles.json"
    hs = json.loads(hf.read_text()) if hf.exists() else {}
    for cid in json.loads(CAMP.read_text()):
        st = _estado(cid)
        if not st or not st.get("cortes"): continue
        sp = st["spec"]; rep = sp.get("oos") or ((st.get("pistas_replica") or {}).get("ventana"))
        for t, per in (("desc", sp.get("desc")), ("rep", rep)):
            k = f"{cid}/{t}"
            if k in hs or not per: continue
            try: h = run.lanzar(dict(sp, cid=f"{cid}-MG-{t}", estadistico="R", cuenta_kaggle=cs[len(hs) % len(cs)]), "MARGINALES",
                                dict(cortes=st["cortes"]), [int(per[0]), int(per[1])])
            except Exception as ex: print("no se lanzó", k, str(ex)[-160:], flush=True); continue
            hs[k] = dict(handle=h, familia=sp["familia"], sensor=sp["sensor"], ejecucion=sp.get("ejecucion") or sp["sensor"])
            hf.write_text(json.dumps(hs, indent=1)); print("lanzada", k, h, flush=True)


def traer():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); hs = json.loads((SAL / "handles.json").read_text()); pend = 0
    for k, v in hs.items():
        f = SAL / "crudo" / (k.replace("/", "__") + ".json")
        if f.exists(): continue
        e = run.estado(v["handle"])
        if e != "complete": pend += 1; continue
        f.parent.mkdir(parents=True, exist_ok=True); f.write_text(json.dumps(run.traer(v["handle"]), default=float))
    return pend


def _dl(y, v):
    """DerSimonian-Laird: efecto, se, tau2, I2."""
    y, v = np.asarray(y, float), np.asarray(v, float); w = 1 / v; mu = (w * y).sum() / w.sum(); Q = (w * (y - mu) ** 2).sum(); k = len(y)
    tau2 = max(0.0, (Q - (k - 1)) / (w.sum() - (w ** 2).sum() / w.sum())) if k > 1 else 0.0
    ws = 1 / (v + tau2); m = (ws * y).sum() / ws.sum(); se = np.sqrt(1 / ws.sum())
    return float(m), float(se), float(tau2), float(max(0.0, (Q - (k - 1)) / Q)) if Q > 0 else 0.0


def efectos(tramo):
    """{etiqueta: [(familia, efecto, var)]} con el efecto de cada nivel contra la media de su familia, en R."""
    from collections import defaultdict
    hs = json.loads((SAL / "handles.json").read_text()); out = defaultdict(list); fam = {}
    for k, v in hs.items():
        if not k.endswith("/" + tramo): continue
        f = SAL / "crudo" / (k.replace("/", "__") + ".json")
        if not f.exists(): continue
        mg = (json.loads(f.read_text()) or {}).get("marginales_globales") or {}
        tot = mg.get("ejecución") or []
        N = sum(r["n"] for r in tot); S = sum(r["suma"] for r in tot)
        if N < 30: continue
        mu = S / N; fam[k.split("/")[0]] = dict(familia=v["familia"], sensor=v["sensor"], ejecucion=v["ejecucion"], n=N, media_R=mu)
        for comp in COMP:
            et = mg.get(comp + ".etiquetas") or []
            for r in mg.get(comp, []):
                if r["n"] < 30 or r["sesiones"] < 10: continue
                m = r["suma"] / r["n"]; var = max(r["suma2"] / r["n"] - m * m, 1e-12)
                out[f"{comp.split('.')[1]}={et[r['nivel']]}"].append((k.split("/")[0], m - mu, var / r["sesiones"]))
    return out, fam


def analizar():
    from edgelab.funnel.escalera import _N
    res = {}
    for tramo in ("desc", "rep"):
        E, fam = efectos(tramo); filas = []
        for et, xs in E.items():
            if len(xs) < 4: continue
            m, se, tau2, I2 = _dl([x[1] for x in xs], [x[2] for x in xs]); z = m / se if se > 0 else 0.0
            filas.append(dict(etiqueta=et, familias=len(xs), efecto_R=m, ic90=[m - 1.645 * se, m + 1.645 * se], z=z,
                              p_bilateral=float(2 * (1 - _N.cdf(abs(z)))), I2=I2, mismo_signo=float(np.mean(np.sign([x[1] for x in xs]) == np.sign(m)))))
        res[tramo] = dict(etiquetas=sorted(filas, key=lambda r: r["p_bilateral"]), familias=fam)
    d = res["desc"]["etiquetas"]; m = len(d)
    for i, r in enumerate(d): r["bh"] = (r["p_bilateral"] <= 0.10 * (i + 1) / m) if m else False
    k = max([i for i, r in enumerate(d) if r["bh"]], default=-1)
    for i, r in enumerate(d): r["descubierta"] = i <= k
    rep = {r["etiqueta"]: r for r in res["rep"]["etiquetas"]}
    for r in d:
        q = rep.get(r["etiqueta"]); r["replica"] = q
        r["confirmada"] = bool(r["descubierta"] and q and np.sign(q["efecto_R"]) == np.sign(r["efecto_R"]) and q["p_bilateral"] / 2 < 0.05)
    (SAL / "RESULTADO.json").write_text(json.dumps(res, indent=1, default=float)); return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("lanzar", "traer", "analizar")); a = ap.parse_args()
    if a.cmd == "lanzar": lanzar()
    elif a.cmd == "traer": print("pendientes", traer())
    else:
        r = analizar()
        for x in r["desc"]["etiquetas"][:25]: print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in x.items() if k != "replica"})
