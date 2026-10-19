#!/usr/bin/env python3
"""VTD-VELA — prueba única pre-registrada (docs/research/VTD_VELA_PREREGISTRO_20261006.md, commit 074b8461).
s = signo(close − open) de la barra marcada VTD (150t); asim_adj = asim_10 − media de asim_10 de barras al azar de la misma
sesión. Estadístico: media de s × asim_adj (RTH, pooled ES/YM/RTY/MGC). Nulo: signo por sesión, 20.000, semilla
20261007, unilateral."""
import glob
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

IN = [Path(p) for p in sys.argv[1:]] or [Path("/kaggle/input")]
OUT = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path(os.environ.get("AVCL_OUT", "."))
NPERM, SEED = 20000, 20261007
INSTS = ("ES", "YM", "RTY", "MGC")


def files(suffix):
    out = []
    for r in IN:
        out += glob.glob(str(r / "**" / ("*" + suffix)), recursive=True)
    return sorted(set(out))


def prep(d, H):
    tot = d["U%d" % H] + d["D%d" % H]
    d["asim%d" % H] = np.where(tot > 0, (d["U%d" % H] - d["D%d" % H]) / tot, np.nan)
    # controles: barras al azar (bar % 7 == 0) a más de 100 barras de una marca
    marks = d.loc[d.vtd, ["contract", "bar"]]
    far = np.ones(len(d), bool)
    for c, g in d.groupby("contract"):
        mb = np.sort(marks[marks.contract == c].bar.to_numpy())
        if len(mb) == 0:
            continue
        b = g.bar.to_numpy(); j = np.searchsorted(mb, b)
        dist = np.minimum(np.abs(b - mb[np.clip(j, 0, len(mb) - 1)]), np.abs(b - mb[np.clip(j - 1, 0, len(mb) - 1)]))
        far[g.index.to_numpy()] = dist > 100
    ctrl = (~d.vtd) & far & d.rth
    key = d.contract + "|" + d.session.astype(str)
    drift = d[ctrl].groupby(key[ctrl])["asim%d" % H].mean()
    d["drift%d" % H] = key.map(drift)
    d["asim_adj%d" % H] = d["asim%d" % H] - d["drift%d" % H]
    return d


def test(E, col, rng, nperm=NPERM):
    s = np.sign(E.close - E.open).to_numpy()
    y = s * E[col].to_numpy()
    ok = (s != 0) & np.isfinite(y)
    y = y[ok]; ses = (E.contract + "|" + E.session.astype(str)).to_numpy()[ok]
    u, inv = np.unique(ses, return_inverse=True)
    S = np.bincount(inv, weights=y, minlength=len(u)); n = len(y)
    obs = y.mean()
    W = rng.choice([-1.0, 1.0], size=(nperm, len(u)))
    nul = (W @ S) / n
    G = len(u); m = obs; cnt = np.bincount(inv, minlength=G)
    se = float(np.sqrt(((S - m * cnt) ** 2).sum() * G / (G - 1)) / n)
    hit = float(np.mean(y > 0))
    return dict(media=float(obs), se=se, mde=2.5 * se, n=int(n), sesiones=int(G),
                p_unilateral=float((1 + (nul >= obs).sum()) / (1 + nperm)), frac_pos=hit)


def main():
    d = pd.concat([pd.read_parquet(f) for f in files("_dir150.parquet")], ignore_index=True)
    d["inst"] = d.contract.str.split("_").str[0]
    d = d[d.inst.isin(INSTS)].reset_index(drop=True)
    for H in (10, 50):
        d = prep(d, H)
    E = d[d.vtd & d.rth].reset_index(drop=True)
    rng = np.random.default_rng(SEED)
    formal = test(E, "asim_adj10", rng)
    formal["decision"] = "CONFIRMA" if (formal["p_unilateral"] <= 0.05 and formal["media"] > 0) else "DESCARTADA"
    print("FORMAL", formal, flush=True)
    desc = {}
    for inst in INSTS:
        Ei = E[E.inst == inst]
        if len(Ei) > 30:
            desc["inst_" + inst] = test(Ei, "asim_adj10", rng, 2000)
    desc["H50_adj"] = test(E, "asim_adj50", rng, 2000)
    desc["H10_sin_deriva"] = test(E, "asim10", rng, 2000)
    tr = pd.qcut(E.amp_rel.rank(method="first"), 3, labels=["comprimido", "medio", "expandido"])
    for lab in ("comprimido", "medio", "expandido"):
        desc["reg_" + lab] = test(E[(tr == lab).to_numpy()], "asim_adj10", rng, 2000)
    s = np.sign(E.close - E.open)
    desc["acierto_lado_H10"] = float(((np.sign(E.U10 - E.D10) == s) & (s != 0)).sum() / max(((s != 0) & (E.U10 != E.D10)).sum(), 1))
    for k, v in desc.items():
        print("DESC", k, v, flush=True)
    res = dict(campaign="VTD-VELA", preregistro="docs/research/VTD_VELA_PREREGISTRO_20261006.md (074b8461)",
               contratos=sorted(d.contract.unique()), marcas=int(len(E)), formal=formal, descriptivo=desc)
    (OUT / "VTD_VELA_RESULTADOS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
