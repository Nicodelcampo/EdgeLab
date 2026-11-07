#!/usr/bin/env python3
"""Cubos de operaciones para buscar regímenes offline (`edgelab/research/regimen_offline.py`).

  python tools/cubos_regimen.py lanzar [CID ...]      # etapa CUBO en Kaggle sobre DESC + réplica (todas las campañas en R si no se nombra)
  python tools/cubos_regimen.py traer                 # baja los terminados a data/cubos/ (caché local, no va al repo)
  python tools/cubos_regimen.py buscar --W 3 --k 3 [--min-ops 20 --min-dias 10 --min-pos 0 --nulo 50] [--solo CID ...]

Los handles quedan en docs/research/regimen_cubos/handles.json (en el repo): cualquier sesión vuelve a bajar los cubos. El universo
de campañas es el del atlas (`atlas_contexto_r._todas_las_campanas_r`, cortes congelados de cada estado.json). Nunca toca el holdout:
el período es [inicio de DESC, fin de la réplica] de cada campaña.
"""
import argparse, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
REG = ROOT / "docs/research/regimen_cubos"; CACHE = ROOT / "data/cubos"


def _campanas():
    from atlas_contexto_r import _todas_las_campanas_r
    return dict(_todas_las_campanas_r())


def lanzar(cids=None):
    from edgelab.holdout import HOLDOUT_PRIMERA_SESION_INT as FH
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); cs = run.cuentas(); REG.mkdir(parents=True, exist_ok=True); hf = REG / "handles.json"
    hs = json.loads(hf.read_text()) if hf.exists() else {}; camp = _campanas()
    for cid in (cids or sorted(camp)):
        if cid in hs or cid not in camp: continue
        st = camp[cid]; sp = st["spec"]; rep = sp.get("oos") or (st.get("pistas_replica") or {}).get("ventana")
        if not rep: continue
        per = [int(sp["desc"][0]), int(rep[1])]
        if per[1] >= FH: per[1] = 20260930                                    # nunca el holdout
        try:
            h = run.lanzar(dict(sp, cid=f"{cid}-CUBO", estadistico="R", cuenta_kaggle=cs[len(hs) % len(cs)]), "CUBO",
                           dict(cortes=st["cortes"], estadistico="R"), per)
        except Exception as ex:
            print("no se lanzó", cid, str(ex)[-160:], flush=True); continue
        hs[cid] = dict(handle=h, periodo=per, experimento=sp["experimento"], sensor=sp["sensor"], ejecucion=sp.get("ejecucion") or sp["sensor"],
                       familia=sp.get("familia"), ts=time.time())
        hf.write_text(json.dumps(hs, indent=1)); print("lanzada", cid, h, flush=True)


def traer():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None); hs = json.loads((REG / "handles.json").read_text()); CACHE.mkdir(parents=True, exist_ok=True); pend = 0
    for cid, h in hs.items():
        f = CACHE / f"{cid}.json"
        if f.exists(): continue
        e = run.estado(h["handle"])
        if e != "complete": pend += 1; continue
        f.write_text(json.dumps(run.traer(h["handle"]), default=float))
    print("pendientes", pend, "en caché", len(list(CACHE.glob("*.json"))))


def buscar(W, k, min_ops, min_dias, min_pos, nulo, solo=None, cada_mes_pos=False, min_dias_mes=4):
    from edgelab.research import regimen_offline as RO
    D = []
    for f in sorted(CACHE.glob("*.json")):
        if solo and f.stem not in solo: continue
        c = (json.loads(f.read_text()) or {}).get("cubo")
        if c and c.get("n"): D.append(RO.series_diarias(RO.decodificar(c, f.stem), min_ops=30))
    kw = dict(W=W, k=k, min_ops=min_ops, min_dias=min_dias, min_pos=min_pos, cada_mes_pos=cada_mes_pos, min_dias_mes=min_dias_mes)
    r = RO.nulo_signo(D, B=nulo, **kw) if nulo else dict(observado=RO.walk_forward(D, **kw))
    o = r["observado"]
    print(f"{len(D)} cubos · W={W} k={k} · ventanas {o['n_ventanas']} · Δ azar {o['delta_azar']:+.3f} (t {o['t_azar']:.2f}) · "
          f"Δ estática {o['delta_estatica']:+.3f} (t {o['t_estatica']:.2f})" + (f" · p nulo {r['p_nulo']:.3f}" if nulo else ""))
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("lanzar", "traer", "buscar")); ap.add_argument("cids", nargs="*")
    ap.add_argument("--W", type=int, default=3); ap.add_argument("--k", type=int, default=3); ap.add_argument("--min-ops", type=int, default=20)
    ap.add_argument("--min-dias", type=int, default=10); ap.add_argument("--min-pos", type=float, default=0.0); ap.add_argument("--nulo", type=int, default=0)
    ap.add_argument("--solo", nargs="*"); ap.add_argument("--cada-mes-pos", action="store_true"); ap.add_argument("--min-dias-mes", type=int, default=4); a = ap.parse_args()
    if a.cmd == "lanzar": lanzar(a.cids or None)
    elif a.cmd == "traer": traer()
    else: buscar(a.W, a.k, a.min_ops, a.min_dias, a.min_pos, a.nulo, a.solo, a.cada_mes_pos, a.min_dias_mes)
