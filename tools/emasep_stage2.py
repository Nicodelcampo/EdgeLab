#!/usr/bin/env python3
"""EMA-SEP análisis (manifiesto docs/research/EMASEP_CONTRA_MANIFIESTO_20261007.md + enmienda de agotamiento).
972 celdas = 2 inst x 3 pct x 3 filtros x 3 entradas x 18 salidas. max-T contra dirección al azar (mismo sorteo por
evento, aunque aparezca en varios percentiles). Confirmación: 2 contratos recientes, Holm."""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

IN = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else IN
CONF = {"MNQ": ("MNQ_09-26", "MNQ_12-26"), "MGC": ("MGC_08-26", "MGC_12-26")}
COMM, TICK = {"MNQ": 1.90, "MGC": 1.90}, {"MNQ": 0.50, "MGC": 1.00}
PCTS, FILTS, MODES = (90.0, 95.0, 99.0), ("ninguno", "desaceleracion", "climax_vol"), "ABC"
NDRAW, SEED = 2000, 20261008
import os
INSTS = tuple(os.environ.get("SEP_INSTS", "MNQ,MGC").split(","))


def load(inst, conf):
    M, P = [], []
    for f in sorted(glob.glob(str(IN / "**" / ("%s_*_emasep.npz" % inst)), recursive=True)):
        c = Path(f).name.replace("_emasep.npz", "")
        if (c in CONF[inst]) != conf:
            continue
        z = np.load(f)
        m = pd.read_parquet(Path(f).with_name("%s_emasep_meta.parquet" % c))
        m["contract"] = c
        M.append(m)
        P.append(z["pnl"].astype(np.float64) * TICK[inst] - COMM[inst])
        exits = z["exits"]
    M = pd.concat(M, ignore_index=True)
    P = np.concatenate(P)                                     # (nsig, 3 modos, 18, 2)
    ns, nm, ne, _ = P.shape
    cols, names = [], []
    for p in PCTS:
        for fi in FILTS:
            mask = (M.pct == p).to_numpy() & (np.ones(len(M), bool) if fi == "ninguno" else M[fi].to_numpy())
            for mi in range(nm):
                for e in range(ne):
                    v = np.full((ns, 2), np.nan)
                    v[mask] = P[mask, mi, e]
                    cols.append(v)
                    sl, R, be = exits[e]
                    names.append("%s p%g %s %s SL%d R%g BE%s" % (inst, p, fi, MODES[mi], sl, R, "si" if be else "no"))
    X = np.stack(cols, axis=1)
    ev = pd.factorize(M.contract + "|" + M.bar.astype(str))[0]
    return X, M.session.to_numpy(), ev, names


def stats(P, S, ev, rng):
    p0, p1 = P[:, :, 0], P[:, :, 1]
    ok = np.isfinite(p0)
    n = ok.sum(0)
    a = np.where(ok, p0, 0.0)
    dlt = np.where(ok, p1 - p0, 0.0)
    real = a.sum(0) / np.maximum(n, 1)
    ne = ev.max() + 1
    nulls = np.empty((NDRAW, P.shape[1]))
    for i in range(0, NDRAW, 50):
        k = min(50, NDRAW - i)
        F = (rng.random((k, ne)) < 0.5)[:, ev].astype(np.float64)
        nulls[i:i + k] = (a.sum(0) + F @ dlt) / np.maximum(n, 1)
    mu, sd = nulls.mean(0), nulls.std(0, ddof=1)
    sd = np.where(sd > 0, sd, np.nan)
    us, inv = np.unique(S, return_inverse=True)
    sums = np.zeros((len(us), P.shape[1])); cnt = np.zeros((len(us), P.shape[1]))
    np.add.at(sums, inv, a); np.add.at(cnt, inv, ok)
    bs = np.array([(lambda k: sums[k].sum(0) / np.maximum(cnt[k].sum(0), 1))(rng.integers(0, len(us), len(us))) for _ in range(1000)])
    lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
    return dict(real=real, mu=mu, z=(real - mu) / sd, zn=(nulls - mu) / sd, n=n, lo=lo, hi=hi,
                win=np.where(ok, p0 > 0, False).sum(0) / np.maximum(n, 1))


def main():
    rng = np.random.default_rng(SEED)
    D = {}
    for inst in INSTS:
        X, S, ev, names = load(inst, False)
        D[inst] = (stats(X, S, ev, rng), names)
    maxnull = np.nanmax(np.concatenate([d["zn"] for d, _ in D.values()], axis=1), axis=1)
    out = {"descubrimiento": {}, "confirmacion": {}}
    pasan = []
    for inst, (d, names) in D.items():
        for j, nm in enumerate(names):
            if d["n"][j] < 30:
                continue
            r = dict(neto_usd=float(d["real"][j]), ic95=[float(d["lo"][j]), float(d["hi"][j])], azar_usd=float(d["mu"][j]),
                     z=float(d["z"][j]), p_maxT=float((maxnull >= d["z"][j]).mean()), n=int(d["n"][j]), win=float(d["win"][j]))
            out["descubrimiento"][nm] = r
            if r["p_maxT"] <= 0.05 and r["neto_usd"] > 0:
                pasan.append((inst, j))
    if pasan:
        res = []
        for inst in sorted({i for i, _ in pasan}):
            X, S, ev, names = load(inst, True)
            d = stats(X, S, ev, rng)
            for i2, j in pasan:
                if i2 == inst:
                    res.append((names[j], dict(neto_usd=float(d["real"][j]), ic95=[float(d["lo"][j]), float(d["hi"][j])],
                                azar_usd=float(d["mu"][j]), z=float(d["z"][j]), p=float((d["zn"][:, j] >= d["z"][j]).mean()), n=int(d["n"][j]))))
        res.sort(key=lambda x: x[1]["p"]); mx = 0.0
        for r, (k, v) in enumerate(res):
            mx = max(mx, min(1.0, (len(res) - r) * v["p"])); v["p_holm"] = mx
            v["confirma"] = bool(mx <= 0.05 and v["neto_usd"] > 0)
            out["confirmacion"][k] = v
    (OUT / "EMASEP_RESULTADOS.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    dd = out["descubrimiento"]
    print("celdas", len(dd), "pasan", len(pasan), "neto>0:", sum(v["neto_usd"] > 0 for v in dd.values()))
    for k, v in sorted(dd.items(), key=lambda kv: -kv[1]["z"])[:12]:
        print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()})
    for k, v in out["confirmacion"].items():
        print("CONF", k, v)


if __name__ == "__main__":
    main()
