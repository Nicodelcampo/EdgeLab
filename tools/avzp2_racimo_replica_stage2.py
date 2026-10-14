#!/usr/bin/env python3
"""AVZP2-RACIMO-REPLICA análisis (manifiesto docs/research/AVZP2_RACIMO_REPLICA_ES_NQ_MANIFIESTO_20261014.md + enmienda de la auditoría externa).
Por instrumento: O5 en 7 celdas y O1 (con FE de magnitud de tendencia y momentum) en 6; Holm por instrumento; criterio de réplica fijado.
Variantes (todas se publican; la PRIMARIA es nulo espejado + ranking 'average'):
  - nulo 'mirror'  : pseudo-racimos con geometría espejada según el signo de la tendencia (H-03).  'legacy': el de las actas del 14-oct.
  - ranking 'average' (H-09, no depende del orden de filas)  vs  'first' (el de las actas).
Además de O5 y O1: O5t0 (denominador rng200[t0], H-06) y O6rev (reversión al centro vs continuación a igual distancia, solo descriptivos, fuera de Holm).
Uso: python tools/avzp2_racimo_replica_stage2.py <dir con *_avzp2racgrid.parquet> <ES|NQ|MES|MNQ> [salida]"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from avzp2_racimo_stage2 import beta, prep  # noqa: E402

MIN_RAC = 150
O5_CELLS = ["6_500_30"] + ["%d_1000_%d" % (m, a) for m in (4, 5, 6) for a in (30, 45)]
O1_CELLS = O5_CELLS[1:]


def holm(d):
    ks = sorted(d, key=lambda k: d[k]["p"]); mx = 0.0
    for r, k in enumerate(ks):
        mx = max(mx, min(1.0, (len(ks) - r) * d[k]["p"])); d[k]["p_holm"] = mx


def analyze(t, inst, rank_method="average", nulo="mirror"):
    """t: filas de stage1 (kind in real/pseudo/pseudo_legacy). nulo: 'mirror' (kind=pseudo) o 'legacy' (kind=pseudo_legacy)."""
    if nulo == "legacy":
        t = t[t.kind.isin(["real", "pseudo_legacy"])].copy()
        t["kind"] = t["kind"].replace("pseudo_legacy", "pseudo")
    else:
        t = t[t.kind.isin(["real", "pseudo"])]
    res, n_real = {}, {}
    for c in O5_CELLS:
        d = t[t.cell == c]
        n_real[c] = int((d.kind == "real").sum())
        if n_real[c] < 30 or (d.kind == "pseudo").sum() < 30:
            continue
        P = prep(d, rank_method)
        res["O5|" + c] = beta(P, P["y_O5"].to_numpy(float))
        if "o5_t0" in P.columns:
            res["O5t0|" + c] = beta(P, P["o5_t0"].to_numpy(float))
        if "o6_rev" in P.columns:
            y_o6 = np.where(P["o6_rev"].isin([0, 1]), P["o6_rev"].to_numpy(float), np.nan)
            res["O6rev|" + c] = beta(P, y_o6)
        if c in O1_CELLS:
            res["O1|" + c] = beta(P, P["y_O1"].to_numpy(float), extra=("trD", "moD"))
            res["O1sin|" + c] = beta(P, P["y_O1"].to_numpy(float))        # descriptivo: sin control (no entra a Holm)
    primarias = {k: v for k, v in res.items() if k.startswith(("O5|", "O1|")) and n_real[k.split("|")[1]] >= MIN_RAC}
    holm(primarias)
    for k, v in primarias.items():
        v["evaluable"] = True
    rep_o5 = sum(1 for k, v in primarias.items() if k.startswith("O5") and v["beta"] < 0 and v["p_holm"] <= 0.05)
    rep_o1 = sum(1 for k, v in primarias.items() if k.startswith("O1") and v["beta"] > 0 and v["p_holm"] <= 0.05)
    return dict(instrumento=inst, variante=dict(nulo=nulo, ranking=rank_method), n_racimos=n_real, min_racimos=MIN_RAC, pruebas=res,
                replica_O5=dict(celdas_ok=rep_o5, requiere=5, replica=bool(rep_o5 >= 5)),
                replica_O1=dict(celdas_ok=rep_o1, requiere=4, replica=bool(rep_o1 >= 4)))


def analyze_all(t, inst):
    """Todas las variantes. PRIMARIA = nulo espejado + ranking 'average'. Si los datos son anteriores a la auditoría (sin pseudo_legacy) se
    analiza sólo el nulo único que traen, con ranking 'first' (reproduce las actas)."""
    if "pseudo_legacy" not in set(t.kind):
        return dict(instrumento=inst, primaria="legacy_actas|first", variantes={"legacy_actas|first": analyze(t, inst, "first", "mirror")})
    variantes = {}
    for nulo in ("mirror", "legacy"):
        for rk in ("average", "first"):
            variantes["%s|%s" % (nulo, rk)] = analyze(t, inst, rk, nulo)
    return dict(instrumento=inst, primaria="mirror|average", variantes=variantes)


def main():
    IN, INST = Path(sys.argv[1]), sys.argv[2]
    OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else IN
    t = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(IN / ("%s_*_avzp2racgrid.parquet" % INST))))], ignore_index=True)
    print(INST, "contratos", sorted(t.contract.unique()), "filas", len(t))
    out = analyze_all(t, INST)
    (OUT / ("AVZP2_RACIMO_REPLICA_V2_%s.json" % INST)).write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    for name, v in out["variantes"].items():
        print("\n== variante %s%s" % (name, "  (PRIMARIA)" if name == out["primaria"] else ""))
        for k, r in v["pruebas"].items():
            c = k.split("|")[1]
            print("%-14s n=%4d beta %+.4f  mde %.4f  p %.4f  real %.3f pseudo %.3f" % (k, v["n_racimos"][c], r["beta"], r["mde"], r["p"], r["media_real"], r["media_pseudo"]))
        print("REPLICA O5:", v["replica_O5"], " REPLICA O1:", v["replica_O1"])


if __name__ == "__main__":
    main()
