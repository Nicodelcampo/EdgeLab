#!/usr/bin/env python3
"""AVZP2-RACIMO-GRILLA análisis (manifiesto docs/research/AVZP2_RACIMO_GRILLA_MANIFIESTO_20261008.md).
Por celda: O5 (primaria, Holm sobre celdas evaluables) y O1/O2/O3b (secundarias, Holm sobre celdas x 3). Evaluable si
>= 300 racimos en descubrimiento. Confirmación una sola vez en lo que pase."""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from avzp2_racimo_stage2 import beta, prep  # noqa: E402

IN = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else IN
CONF = ("MNQ_09-26", "MNQ_12-26")
MIN_RAC = 300


def holm(d):
    ks = sorted(d, key=lambda k: d[k]["p"]); mx = 0.0
    for r, k in enumerate(ks):
        mx = max(mx, min(1.0, (len(ks) - r) * d[k]["p"])); d[k]["p_holm"] = mx


def main():
    t = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(IN / "**" / "*_avzp2racgrid.parquet"), recursive=True))], ignore_index=True)
    D, C = t[~t.contract.isin(CONF)], t[t.contract.isin(CONF)]
    nreal = D[D.kind == "real"].groupby("cell").size()
    cells = sorted(t.cell.unique(), key=lambda c: tuple(int(x) for x in c.split("_")))
    ev = [c for c in cells if nreal.get(c, 0) >= MIN_RAC]
    out = {"n_racimos_desc": {c: int(nreal.get(c, 0)) for c in cells}, "evaluables": ev, "no_evaluables": [c for c in cells if c not in ev],
           "O5": {}, "secundarias": {}, "descriptivo_no_evaluables": {}}
    P = {c: prep(D[D.cell == c]) for c in cells if nreal.get(c, 0) >= 30}
    for c in ev:
        out["O5"][c] = beta(P[c], P[c]["y_O5"].to_numpy(float))
        for k in ("O1", "O2", "O3b"):
            out["secundarias"]["%s|%s" % (c, k)] = beta(P[c], P[c]["y_" + k].to_numpy(float))
    for c in cells:
        if c not in ev and c in P:
            out["descriptivo_no_evaluables"][c] = {k: beta(P[c], P[c]["y_" + k].to_numpy(float)) for k in ("O5", "O2")}
    holm(out["O5"]); holm(out["secundarias"])
    pasan = [("O5", c) for c, v in out["O5"].items() if v["p_holm"] <= 0.05] + \
            [(k.split("|")[1], k.split("|")[0]) for k, v in out["secundarias"].items() if v["p_holm"] <= 0.05]
    out["pasan"] = pasan
    if pasan and len(C):
        res = {}
        for o, c in pasan:
            cc = prep(C[C.cell == c])
            res["%s|%s" % (c, o)] = beta(cc, cc["y_" + o].to_numpy(float))
        holm(res)
        for k, v in res.items():
            c, o = k.split("|")
            ref = out["O5"][c]["beta"] if o == "O5" else out["secundarias"][k]["beta"]
            v["confirma"] = bool(v["p_holm"] <= 0.05 and np.sign(v["beta"]) == np.sign(ref))
        out["confirmacion"] = res
    (OUT / "AVZP2_RACIMO_GRILLA_RESULTADOS.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("evaluables", len(ev), "de", len(cells))
    for c in ev:
        v = out["O5"][c]
        s = " ".join("%s %+.3f(%.2f)" % (k, out["secundarias"]["%s|%s" % (c, k)]["beta"], out["secundarias"]["%s|%s" % (c, k)]["p_holm"]) for k in ("O1", "O2", "O3b"))
        print("%-10s n=%4d  O5 %+.3f mde %.3f pholm %.4f | %s" % (c, nreal[c], v["beta"], v["mde"], v["p_holm"], s))
    for k, v in out.get("confirmacion", {}).items():
        print("CONF", k, round(v["beta"], 4), "p_holm", round(v["p_holm"], 4), "confirma", v["confirma"])


if __name__ == "__main__":
    main()
