#!/usr/bin/env python3
"""EXTERNAS-28, fase 0 (EF2, sin retornos): fricción en R de cada una de las 114 variantes (pre-registro
docs/research/externas_a5_20261118/PREREGISTRO.md §3).

Reusa `externas_a5.VARIANTES` (las `senales()` del catálogo, sin cambios), `a5_campana._ctx` (M1 verificado de `tools/datos.py`),
`holdout.a5_bloque` y la fricción canónica de `embudo_runners.friccion`. Sólo mira el riesgo inicial de cada señal (`stop_pts`) en las
sesiones DESC; ningún desenlace.

  python tools/externas_a5.py fase0 <INST>     # por instrumento -> FASE0_<INST>.json (se pueden correr en paralelo)
  python tools/externas_a5.py juntar           # mediana agrupada por variante, regla ≤ 0,08 R y ≥ 30 sesiones -> FASE0.json
"""
import json, os, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/externas_a5_20261118"
INST = ("NQ", "ES", "YM", "GC")
UMBRAL, MIN_SES = 0.08, 30
CRUDO = ROOT / "data/externas_a5_fase0"     # fricción por señal (millones de valores; data/ no se versiona) y avance por variante: reanudable


def fase0(inst):
    from a5_campana import _ctx, _cfg, _fric
    from edgelab.holdout import a5_bloque
    from edgelab.research import externas_a5 as X
    cfg = _cfg(DIR); ctx = _ctx(inst, None, *cfg["ventana"]); f = _fric(inst)
    t = np.asarray(ctx["t"], float); ts = (t * 1000).astype(np.int64); ses = np.asarray(ctx["ses"])
    B = pd.DataFrame(dict(ts=ts, o=ctx["o"], h=ctx["h"], l=ctx["l"], c=ctx["c"], v=ctx["v"], ses=ses))
    blo = {int(s): a5_bloque(int(s)) for s in np.unique(ses)}; out, crudo = {}, {}
    CRUDO.mkdir(parents=True, exist_ok=True)
    pares = list(zip(X.DEFINICIONES, X.VARIANTES))
    if os.environ.get("EXTERNAS_REVERSO") == "1": pares = pares[::-1]     # segundo proceso desde el final (sólo cambia el orden; resultados idénticos)
    for d, (m, p) in pares:
        hecho = CRUDO / f"{inst}_{d}.json"
        if hecho.exists():                                   # reanudar tras un reinicio del contenedor
            out[d] = json.loads(hecho.read_text()); crudo[d] = np.load(CRUDO / f"{inst}_{d}.npy"); continue
        S = m.senales(B, **p)
        if not S:
            out[d] = dict(n=0, sesiones=0); crudo[d] = np.zeros(0, np.float32)
            np.save(CRUDO / f"{inst}_{d}.npy", crudo[d]); hecho.write_text(json.dumps(out[d])); continue
        k = np.searchsorted(ts, np.array([s["available_at"] for s in S], np.int64), side="right") - 1
        sl = np.array([s["stop_pts"] for s in S], float); ok = (k >= 0) & (sl > 0); k, sl = k[ok], sl[ok]
        des = np.array([blo[int(x)] == "DESC" for x in ses[k]], bool)
        fr = f / sl[des]
        out[d] = dict(n=int(des.sum()), sesiones=int(len(np.unique(ses[k][des]))), mediana=float(np.median(fr)) if len(fr) else None,
                      cuantiles=[float(x) for x in np.quantile(fr, [0.1, 0.25, 0.5, 0.75, 0.9])] if len(fr) else [],
                      ); crudo[d] = fr.astype(np.float32)
        np.save(CRUDO / f"{inst}_{d}.npy", crudo[d]); hecho.write_text(json.dumps(out[d]))
        print(inst, d, m.NOMBRE, out[d]["n"], out[d]["mediana"], flush=True)
    np.savez_compressed(CRUDO / f"FR_{inst}.npz", **crudo)
    (DIR / f"FASE0_{inst}.json").write_text(json.dumps(dict(instrumento=inst, friccion_pts=f, variantes=out), indent=1))


def juntar():
    from edgelab.research import externas_a5 as X
    P = {i: json.loads((DIR / f"FASE0_{i}.json").read_text())["variantes"] for i in INST}
    F = {i: np.load(CRUDO / f"FR_{i}.npz") for i in INST}
    res = {}
    for d, info in zip(X.DEFINICIONES, X.mapa()):
        fr = np.concatenate([F[i][d].astype(float) for i in INST]); ses = sum(P[i][d]["sesiones"] for i in INST)
        med = float(np.median(fr)) if len(fr) else None
        res[d] = dict(estrategia=info["estrategia"], parametros=info["parametros"], n_desc=int(len(fr)), sesiones_desc=int(ses),
                      friccion_R_mediana=med, por_instrumento={i: P[i][d]["mediana"] for i in INST},
                      pasa=bool(med is not None and med <= UMBRAL and ses >= MIN_SES))
    pasan = [d for d in X.DEFINICIONES if res[d]["pasa"]]
    out = dict(preregistro="docs/research/externas_a5_20261118/PREREGISTRO.md", regla=f"mediana fricción/riesgo ≤ {UMBRAL} R y ≥ {MIN_SES} sesiones DESC",
               pasan=pasan, n_pasan=len(pasan), variantes=res)
    (DIR / "FASE0.json").write_text(json.dumps(out, indent=1, ensure_ascii=False)); print(len(pasan), "pasan:", pasan)


if __name__ == "__main__":
    {"fase0": lambda: fase0(sys.argv[2]), "juntar": juntar}[sys.argv[1]]()
