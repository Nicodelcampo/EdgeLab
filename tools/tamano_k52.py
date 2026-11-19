#!/usr/bin/env python3
"""TAMANO-K52: tamaño ∝ 1/ATR20 (W1) o intermedio (W2) contra riesgo constante (S0) en RQ5, RQ6, SOM y Franklin
(pre-registro docs/research/tamano_k52_20261119/PREREGISTRO.md).

Reusa las operaciones ya calculadas (FRICCION-RQ `esc1`, SOM_OPS `sin_finde`, FRANKLIN_OPS), `m1_largo.atr20` (ATR20 de las 20 sesiones previas),
`holdout.a5_bloque`, `a5.bh`, `a5.sf` y `libro_lord`. Potencia de REP en días antes de leer (K49).

  python tools/tamano_k52.py desc     # elección en DESC → DESC.json (commitear antes de rep)
  python tools/tamano_k52.py rep      # una lectura de REP por nominada con potencia ≥ 0,8 → REP.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/tamano_k52_20261119"; PRE = "docs/research/tamano_k52_20261119/PREREGISTRO.md"
M1L = ROOT / "docs/research/m1_largo_20261117"; FRQ = ROOT / "docs/research/friccion_rq_20261119/OPS.csv.gz"; FIN = 20250731
FAM = {"RQ5": "ROBOQUANT_A5", "RQ6": "ROBOQUANT_A5", "SOM": "SOM", "FRANKLIN": "FRANKLIN"}


def _ops():
    from datos import ruta
    from m1_largo import cargar, atr20
    from edgelab.holdout import a5_bloque
    q = pd.read_csv(FRQ); q = q[(q.celda == "esc1") & q.regla.isin(["RQ5", "RQ6"])]
    rq = pd.DataFrame(dict(estrategia=q.regla, inst=q.inst, fecha=q.ses.astype(int), riesgo=q.riesgo, Rn=q.R - q.fricR))
    som = pd.concat([pd.read_csv(M1L / f"SOM_OPS_{i}.csv.gz").assign(inst=i) for i in ("NQ", "ES", "YM")]); som = som[som.celda == "sin_finde"]
    fr = pd.concat([pd.read_csv(M1L / f"FRANKLIN_OPS_{i}.csv.gz").assign(inst=i) for i in ("NQ", "ES")])
    sf = pd.concat([pd.DataFrame(dict(estrategia=n, inst=x.inst, fecha=x.fecha.astype(int), riesgo=x.riesgo, Rn=x.R)) for n, x in (("SOM", som), ("FRANKLIN", fr))])
    T = pd.concat([rq, sf], ignore_index=True); T = T[T.riesgo > 0]
    atr = {}
    for inst in T.inst.unique():
        a = atr20(cargar(inst, ruta("M1NT8"))); atr[inst] = a
    T["atr20"] = [float(atr[i].get(pd.Timestamp(str(f)), np.nan)) for i, f in zip(T.inst, T.fecha)]
    T = T[np.isfinite(T.atr20) & (T.atr20 > 0)].copy()
    T["bloque"] = [a5_bloque(int(x)) for x in T.fecha]; return T[(T.fecha <= FIN) & T.bloque.isin(["DESC", "REP"])]


def _peso(g, s):
    x = (g.riesgo / g.atr20).to_numpy(float)
    # pesos sobre los PUNTOS de cada operación (R del esquema = Σ peso·puntos / Σ peso·riesgo):
    # S0 riesgo constante (1/riesgo); W1 contratos ∝ 1/ATR20 (peso en R ∝ riesgo/ATR20); W2 peso en R ∝ √(riesgo/ATR20)
    return {"S0": 1.0 / g.riesgo.to_numpy(float), "W1": 1.0 / g.atr20.to_numpy(float), "W2": np.sqrt(x) / g.riesgo.to_numpy(float)}[s]


def _ratio(g, s):
    w = _peso(g, s); pts = g.Rn.to_numpy(float) * g.riesgo.to_numpy(float)
    return float((w * pts).sum() / (w * g.riesgo.to_numpy(float)).sum())


def _contraste(g, s, B=2000, seed=7):
    from edgelab.research.a5 import sf
    u, inv = np.unique(g.fecha.to_numpy(), return_inverse=True); pts = g.Rn.to_numpy(float) * g.riesgo.to_numpy(float); rg = g.riesgo.to_numpy(float)
    wa, w0 = _peso(g, s), _peso(g, "S0")
    A = np.c_[np.bincount(inv, wa * pts), np.bincount(inv, wa * rg)]; Z = np.c_[np.bincount(inv, w0 * pts), np.bincount(inv, w0 * rg)]
    obs = A[:, 0].sum() / A[:, 1].sum() - Z[:, 0].sum() / Z[:, 1].sum(); rng = np.random.default_rng(seed); bs = []
    for _ in range(B):
        ix = rng.integers(0, len(u), len(u)); a, z = A[ix].sum(0), Z[ix].sum(0); bs.append(a[0] / a[1] - z[0] / z[1])
    se = float(np.std(bs, ddof=1)); return float(obs), se, float(sf(obs / se)) if se > 0 else 1.0, int(len(u))


def desc():
    from registro_global import exigir_contada
    from edgelab.research.a5 import bh
    exigir_contada(PRE)
    T = _ops(); T.to_csv(DIR / "OPS.csv.gz", index=False); res = {}
    for est in FAM:
        g = T[(T.estrategia == est) & (T.bloque == "DESC")]
        r = {s: _ratio(g, s) for s in ("S0", "W1", "W2")}; mejor = max(("W1", "W2"), key=lambda s: r[s])
        d, se, p, nd = _contraste(g, mejor)
        res[est] = dict(R=r, mejor=mejor, dif=d, se=se, p=p, n_dias_desc=nd, n=int(len(g)))
    k = list(res); rech = bh([res[x]["p"] for x in k], 0.10)
    for x, b in zip(k, rech): res[x]["bh"] = bool(b and res[x]["p"] < 0.05 and res[x]["dif"] > 0)
    (DIR / "DESC.json").write_text(json.dumps(dict(preregistro=PRE, resultados=res, nominadas=[x for x in k if res[x]["bh"]]), indent=1, default=float))
    for x in k: print(x, {y: (round(v, 4) if isinstance(v, float) else v) for y, v in res[x].items() if y != "R"}, {s: round(v, 4) for s, v in res[x]["R"].items()})


def rep():
    from statistics import NormalDist
    norm = NormalDist()
    from a5_campana import _commiteado
    from edgelab.funnel.libro_lord import LibroLord
    if not _commiteado(DIR / "DESC.json"): raise SystemExit("DESC.json sin commitear")
    D = json.loads((DIR / "DESC.json").read_text()); T = pd.read_csv(DIR / "OPS.csv.gz"); out = {}
    for est in D["nominadas"]:
        d = D["resultados"][est]; n_rep = int(T[(T.estrategia == est) & (T.bloque == "REP")].fecha.nunique())      # sólo cuenta sesiones
        se_rep = d["se"] * np.sqrt(d["n_dias_desc"] / max(n_rep, 1)); a = LibroLord().nivel(FAM[est])
        pot = float(1 - norm.cdf(norm.inv_cdf(1 - a) - 0.5 * d["dif"] / se_rep)); out[est] = dict(potencia=pot, n_dias_rep=n_rep, alfa=a)
        if pot < 0.8: out[est]["estado"] = "SIN_POTENCIA_PREVIA"; continue
        g = T[(T.estrategia == est) & (T.bloque == "REP")]; dif, se, p, _ = _contraste(g, d["mejor"])
        dec = LibroLord().probar(FAM[est], f"REP_TAMANO_K52_{est}", [(est, p)])
        out[est].update(dif=dif, se=se, p=p, R_rep=_ratio(g, d["mejor"]), lord=dec, confirmada=est in (dec.get("confirmadas") or []) and _ratio(g, d["mejor"]) > 0)
    (DIR / "REP.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps(out, default=float)[:1500])


if __name__ == "__main__":
    {"desc": desc, "rep": rep}[sys.argv[1]]()
