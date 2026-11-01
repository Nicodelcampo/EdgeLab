#!/usr/bin/env python3
"""Variante τ de las reglas con acta (2026-10-31): mismas entradas congeladas, salida por tiempo de parada, sobre el DESC de cada regla.

Pre-registro: docs/research/paquete_20261031/PREREGISTRO_VARIANTE_TAU_ACTAS.md. Reutiliza el runner y la etapa ANALIZAR_REGLA
(como `tools/analizar_embudo.py`), con `operaciones=True` para comparar por sesión. Sólo período DESC (desarrollo); nada del OOS
ni del holdout.

  python tools/variante_tau_actas.py plan
  python tools/variante_tau_actas.py lanzar      # un kernel por regla, guarda los handles
  python tools/variante_tau_actas.py traer       # baja los resultados y escribe la comparación pareada + BH q 0,10
"""
import argparse
import glob
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
SALIDA = ROOT / "docs/research/paquete_20261031/variante_tau"
ENVOLTORIO = {"edgelab.research.corredor_vol_gaps": "edgelab.research.vtau_cvgap", "edgelab.research.u1_cfd": "edgelab.research.vtau_u1cfd",
              "edgelab.research.u1_racimos_grilla": "edgelab.research.vtau_racimos", "edgelab.research.u1_zonas_avcl": "edgelab.research.vtau_avcl",
              "edgelab.research.u1_zonas_bt2": "edgelab.research.vtau_bt2", "edgelab.research.u1_zonas": "edgelab.research.vtau_zonas"}
Q = 0.10


def plan() -> list:
    from edgelab.research.variante_tau import VARIANTES, celda_variante
    filas = []
    for f in sorted(glob.glob(str(ROOT / "docs/research/*/embudo/*/ACTA_HOLDOUT.json"))):
        acta = json.loads(Path(f).read_text()); st = json.loads((Path(f).parent / "estado.json").read_text()); spec = st["spec"]
        if spec["experimento"] not in ENVOLTORIO or (spec.get("ejecucion") or spec["sensor"]) != spec["sensor"]: continue
        celda = acta["regla"]["celda"]
        filas.append(dict(cid=spec["cid"], spec=dict(spec, cid=spec["cid"] + "-VTAU", experimento=ENVOLTORIO[spec["experimento"]], cuenta_kaggle="auto"),
                          cortes=st["cortes"], tope=acta["regla"]["tope"], celdas=[celda_variante(celda, j) for j in range(len(VARIANTES))],
                          periodo=[int(spec["desc"][0]), int(spec["desc"][1])]))
    return filas


def comparar(ops: dict, n_var: int, n_boot: int = 4000, seed: int = 0) -> list:
    """Diferencia por sesión (variante τ − original) del neto sumado; p unilateral por bootstrap de sesiones."""
    import pandas as pd
    o = pd.DataFrame(ops)
    if not len(o): return []
    g = o.groupby(["ses", "celda"]).neto.sum().unstack().reindex(columns=range(n_var)).fillna(0.0)
    rng = np.random.default_rng(seed); out = []
    for j in range(1, n_var):
        d = (g[j] - g[0]).to_numpy(float); n = len(d)
        b = rng.integers(0, n, (n_boot, n)); mb = d[b].mean(1)
        w = o[o.celda == j].neto; w0 = o[o.celda == 0].neto
        wl = lambda x: float(x[x > 0].mean() / -x[x < 0].mean()) if (x > 0).any() and (x < 0).any() else None
        out.append(dict(variante=j, sesiones=n, dif_media=float(d.mean()), ic90=[float(np.quantile(mb, .05)), float(np.quantile(mb, .95))],
                        p=float(((mb - d.mean()) >= d.mean()).mean()), media_original=float(w0.mean()), media_tau=float(w.mean()),
                        wl_original=wl(w0), wl_tau=wl(w), n_original=int(len(w0)), n_tau=int(len(w))))
    return out


def bh(ps, q=Q) -> list:
    ps = np.asarray(ps, float); m = len(ps); o = np.argsort(ps); ok = np.zeros(m, bool)
    k = np.flatnonzero(ps[o] <= q * np.arange(1, m + 1) / m)
    if len(k): ok[o[:k[-1] + 1]] = True
    return ok.tolist()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("plan", "lanzar", "traer")); a = ap.parse_args()
    SALIDA.mkdir(parents=True, exist_ok=True); hf = SALIDA / "handles.json"
    if a.cmd == "plan":
        for p in plan(): print(p["cid"], p["spec"]["experimento"], p["celdas"], p["periodo"], p["tope"])
        return
    from edgelab.research.embudo_runners import KaggleRunner
    from edgelab.research.variante_tau import VARIANTES
    run = KaggleRunner(raiz=None)
    if a.cmd == "lanzar":
        from edgelab.funnel.multiplicity import TrialRegistry
        reg = TrialRegistry(ROOT / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl"); hs = json.loads(hf.read_text()) if hf.exists() else {}
        for p in plan():
            if p["cid"] in hs: continue
            reg.ensure(f"variante_tau/{p['cid']}/{p['periodo'][0]}-{p['periodo'][1]}", "VARIANTE_TAU_ACTAS", len(VARIANTES) - 1,
                       f"salida τ (pivotes 3/5/8) contra la salida original de {p['cid']}, DESC, comparación pareada")
            params = dict(cortes=p["cortes"], celdas=p["celdas"], tope=p["tope"], operaciones=True)
            cuentas = run.cuentas(); spec = dict(p["spec"]); h = None
            for i in range(len(cuentas)):                                   # tope de kernels simultáneos por cuenta: alternar
                spec["cuenta_kaggle"] = cuentas[(len(hs) + i) % len(cuentas)]
                try: h = run.lanzar(spec, "ANALIZAR_REGLA", params, p["periodo"]); break
                except RuntimeError as e: print("no se lanzó", p["cid"], spec["cuenta_kaggle"], str(e)[-160:])
            if h is None: continue
            hs[p["cid"]] = dict(handle=h, periodo=p["periodo"], ts=time.time()); hf.write_text(json.dumps(hs, indent=1)); print("lanzada", p["cid"], h)
        return
    hs = json.loads(hf.read_text()); filas = []
    for cid, h in list(hs.items()):
        e = run.estado(h["handle"])
        if e == "no_encontrado" and time.time() - h.get("ts", 0) > 3600:      # rechazo silencioso de Kaggle: se relanza con `lanzar`
            print(cid, "no encontrado: se borra el handle"); hs.pop(cid); hf.write_text(json.dumps(hs, indent=1)); continue
        if e != "complete": print(cid, e); continue
        r = run.traer(h["handle"]); (SALIDA / f"{cid}.json").write_text(json.dumps(r, indent=1, default=float))
        for x in comparar(r.get("operaciones") or {}, len(VARIANTES)): filas.append(dict(cid=cid, orden=VARIANTES[x["variante"]], **x))
    if not filas: return
    for f, ok in zip(filas, bh([f["p"] for f in filas])): f["nominada_bh"] = bool(ok and f["dif_media"] > 0)
    (SALIDA / "COMPARACION.json").write_text(json.dumps(dict(q=Q, m=len(filas), filas=filas), indent=1)); print(len(filas), "comparaciones")


if __name__ == "__main__":
    main()
