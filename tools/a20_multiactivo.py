#!/usr/bin/env python3
"""A20-MULTIACTIVO (2026-11-19): A20 de FundedSync (fábrica + 8 vecinos a un paso) en índices donde nunca se midió (YM, RTY, EMD), con el
mismo motor y la misma medida que NETO-PISTAS (`tools/neto_pistas.py`: `_ms`, `_ops`, `_cfg`, `_nombre`, `GRILLAS`, `FABRICA`).
Pre-registro: docs/research/a20_multiactivo_20261119/PREREGISTRO.md. Sólo se GUARDAN operaciones de meses DESC y REP de A5: las de HOLDOUT y
EMBARGO se descartan al salir del motor sin leerse (quedan para la apertura del holdout).
  python tools/a20_multiactivo.py correr      # -> OPS.csv.gz
  python tools/a20_multiactivo.py leer        # -> RESULTADO.json (lectura pre-registrada, sólo DESC del régimen)
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/a20_multiactivo_20261119"; PRE = DIR / "PREREGISTRO.md"
INSTS = ("YM", "RTY", "EMD")


def variantes():
    from neto_pistas import GRILLAS, FABRICA
    fab = FABRICA["A20"]; vals = list(GRILLAS["A20"].values()); out = [tuple(fab)]
    for i, b in enumerate(fab):
        j = vals[i].index(b)
        for jj in (j - 1, j + 1):
            if 0 <= jj < len(vals[i]): v = list(fab); v[i] = vals[i][jj]; out.append(tuple(v))
    return out


def correr():
    from registro_global import exigir_contada
    from neto_pistas import _ms, _ops, _cfg, _nombre
    from edgelab.holdout import a5_bloque
    exigir_contada(PRE); P = DIR / "parcial"; P.mkdir(exist_ok=True)
    for inst in INSTS:
        F, D, ms = _ms(inst)
        for v in variantes():
            f = P / f"{inst}_{_nombre('A20', v)}.csv"
            if f.exists(): continue
            o = _ops(F, "A20", ms, D, _cfg("A20", v))
            b = pd.to_datetime(o.ses).dt.strftime("%Y%m%d").astype(int).map(a5_bloque)
            o = o[b.isin(["DESC", "REP"]).to_numpy()].assign(bloque=b[b.isin(["DESC", "REP"])].to_numpy(), inst=inst, variante=_nombre("A20", v))
            o.to_csv(f, index=False); print(inst, _nombre("A20", v), len(o), flush=True)
    pd.concat([pd.read_csv(f) for f in sorted(P.glob("*.csv"))]).to_csv(DIR / "OPS.csv.gz", index=False)


def leer():
    from neto_pistas import _nombre, FABRICA
    from edgelab import costos as C
    from edgelab.research.embudo_runners import friccion
    O = pd.read_csv(DIR / "OPS.csv.gz"); O = O[(O.riesgo > 0) & (O.bloque == "DESC")]
    O["fecha"] = pd.to_datetime(O.ses); O = O[(O.fecha >= "2018-01-01") & (O.fecha <= "2025-07-31")]
    with C.estimados_permitidos(str(PRE.relative_to(ROOT))):
        fr = {i: float(friccion(i)[0]) for i in INSTS}
    O["R"] = (O.pnl_pts - O.inst.map(fr)) / O.riesgo; O["mes"] = O.fecha.dt.to_period("M").astype(str)
    fab = _nombre("A20", FABRICA["A20"]); rng = np.random.default_rng(7); res = dict(friccion=fr, instrumentos={})
    for inst in INSTS:
        g = O[O.inst == inst]; cel = {}
        for v, x in g.groupby("variante"):
            s = x.groupby("ses").R.sum(); bs = [s.sample(len(s), replace=True, random_state=int(rng.integers(1e9))).sum() / len(x) for _ in range(1000)]
            cel[v] = dict(n=int(len(x)), R=float(x.R.mean()), p=float(np.mean(np.array(bs) <= 0)), ops_mes=float(len(x) / x.mes.nunique()))
        vec = [v for v in cel if v != fab]
        res["instrumentos"][inst] = dict(fabrica=cel.get(fab), vecinos_positivos=sum(cel[v]["R"] > 0 for v in vec), vecinos=len(vec), celdas=cel)
    f = [res["instrumentos"][i]["fabrica"] for i in INSTS]
    res["positivas_fabrica"] = sum(x is not None and x["R"] > 0 for x in f)
    res["veredicto"] = "TRANSFIERE" if res["positivas_fabrica"] >= 2 and sum(res["instrumentos"][i]["vecinos_positivos"] >= 6 for i in INSTS) >= 2 else "NO_TRANSFIERE"
    (DIR / "RESULTADO.json").write_text(json.dumps(res, indent=1, default=float) + "\n"); print(json.dumps({i: res["instrumentos"][i]["fabrica"] for i in INSTS}), res["veredicto"])


if __name__ == "__main__":
    {"correr": correr, "leer": leer}[sys.argv[1]]()
