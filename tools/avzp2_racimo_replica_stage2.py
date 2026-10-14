#!/usr/bin/env python3
"""AVZP2-RACIMO-REPLICA análisis (manifiesto docs/research/AVZP2_RACIMO_REPLICA_ES_NQ_MANIFIESTO_20261014.md).
Por instrumento: O5 en 7 celdas y O1 (con FE de magnitud de tendencia y momentum) en 6; Holm por instrumento; criterio de réplica fijado.
Uso: python tools/avzp2_racimo_replica_stage2.py <dir con *_avzp2racgrid.parquet> <ES|NQ> [salida]"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from avzp2_racimo_stage2 import beta, prep  # noqa: E402

IN, INST = Path(sys.argv[1]), sys.argv[2]
OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else IN
MIN_RAC = 150
O5_CELLS = ["6_500_30"] + ["%d_1000_%d" % (m, a) for m in (4, 5, 6) for a in (30, 45)]
O1_CELLS = O5_CELLS[1:]


def holm(d):
    ks = sorted(d, key=lambda k: d[k]["p"]); mx = 0.0
    for r, k in enumerate(ks):
        mx = max(mx, min(1.0, (len(ks) - r) * d[k]["p"])); d[k]["p_holm"] = mx


def main():
    t = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(IN / ("%s_*_avzp2racgrid.parquet" % INST))))], ignore_index=True)
    print(INST, "contratos", sorted(t.contract.unique()), "filas", len(t))
    res, n_real = {}, {}
    for c in O5_CELLS:
        d = t[t.cell == c]
        n_real[c] = int((d.kind == "real").sum())
        if n_real[c] < 30:
            continue
        P = prep(d)
        res["O5|" + c] = beta(P, P["y_O5"].to_numpy(float))
        if c in O1_CELLS:
            res["O1|" + c] = beta(P, P["y_O1"].to_numpy(float), extra=("trD", "moD"))
            res["O1sin|" + c] = beta(P, P["y_O1"].to_numpy(float))        # descriptivo: sin control (no entra a Holm)
    primarias = {k: v for k, v in res.items() if not k.startswith("O1sin") and n_real[k.split("|")[1]] >= MIN_RAC}
    holm(primarias)
    for k, v in primarias.items():
        v["evaluable"] = True
    rep_o5 = sum(1 for k, v in primarias.items() if k.startswith("O5") and v["beta"] < 0 and v["p_holm"] <= 0.05)
    rep_o1 = sum(1 for k, v in primarias.items() if k.startswith("O1") and v["beta"] > 0 and v["p_holm"] <= 0.05)
    out = dict(instrumento=INST, n_racimos=n_real, min_racimos=MIN_RAC, pruebas=res,
               replica_O5=dict(celdas_ok=rep_o5, requiere=5, replica=bool(rep_o5 >= 5)),
               replica_O1=dict(celdas_ok=rep_o1, requiere=4, replica=bool(rep_o1 >= 4)))
    (OUT / ("AVZP2_RACIMO_REPLICA_%s.json" % INST)).write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    for k, v in res.items():
        c = k.split("|")[1]
        print("%-14s n=%4d beta %+.4f  mde %.4f  p %.4f  holm %s  real %.3f pseudo %.3f" % (
            k, n_real[c], v["beta"], v["mde"], v["p"], ("%.4f" % primarias[k]["p_holm"]) if k in primarias else "n/a",
            v["media_real"], v["media_pseudo"]))
    print("REPLICA O5:", out["replica_O5"], " REPLICA O1:", out["replica_O1"])


if __name__ == "__main__":
    main()
