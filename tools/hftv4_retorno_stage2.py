#!/usr/bin/env python3
"""HFTV4-RETORNO análisis (manifiesto docs/research/HFTV4_RETORNO_MANIFIESTO_20261006.md).
Real (flecha, sin V) contra pseudo-zona (misma regla): P(retorno al borde cercano) y P(relleno) en T barras de 50t."""
import glob
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.stats import norm

IN = [Path(p) for p in sys.argv[1:]] or [Path("/kaggle/input")]
OUT = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path(os.environ.get("AVCL_OUT", "."))


def files(suffix):
    out = []
    for r in IN:
        out += glob.glob(str(r / "**" / ("*" + suffix)), recursive=True)
    return sorted(set(out))


def onehot(codes):
    u, inv = np.unique(codes, return_inverse=True)
    return sp.csr_matrix((np.ones(len(inv)), (np.arange(len(inv)), inv)), shape=(len(inv), len(u)))


def absorb(X, groups, tol=1e-9, maxit=200):
    X = np.array(X, dtype=float, copy=True)
    G = [onehot(g) for g in groups]; cnt = [np.asarray(g.sum(0)).ravel() for g in G]
    for _ in range(maxit):
        old = X.copy()
        for g, n in zip(G, cnt):
            X -= g @ ((g.T @ X) / n[:, None])
        if np.max(np.abs(X - old)) < tol:
            break
    return X


def beta(d, y):
    ok = np.isfinite(y)
    d, y = d[ok], y[ok]
    f = (d.kind == "real").to_numpy()
    groups = [(d.contract + "|" + d.clock.astype(str)).to_numpy(), d.ampT.to_numpy(), d.distD.to_numpy()]
    Z = absorb(np.column_stack([f.astype(float), y]), groups)
    e, Y = Z[:, 0], Z[:, 1]
    ee = e @ e; b = (e @ Y) / ee; U = Y - e * b
    sid = pd.factorize(d.session.to_numpy())[0]; G = sid.max() + 1
    S = np.bincount(sid, weights=e * U, minlength=G)
    se = float(np.sqrt((S ** 2).sum() * G / (G - 1)) / ee)
    return dict(beta=float(b), se=se, z=float(b / se), p=float(2 * (1 - norm.cdf(abs(b / se)))), mde=2.8 * se,
                tasa_real=float(y[f].mean()), tasa_pseudo=float(y[~f].mean()), n_real=int(f.sum()), n_pseudo=int((~f).sum()))


def main():
    t = pd.concat([pd.read_parquet(f) for f in files("_hftret.parquet")], ignore_index=True)
    ev = t[t.arrow & ~t.vshape].copy()
    ev["ampT"] = pd.qcut(ev.amp.rank(method="first"), 3, labels=False)
    ev["distD"] = pd.qcut(ev.dist_ticks.rank(method="first"), 10, labels=False)
    print("flechas reales", int((ev.kind == "real").sum()), "pseudo", int((ev.kind == "pseudo").sum()),
          "| V excluidas", int(((t.kind == "real") & t.vshape).sum()), "| reales sin flecha", int(((t.kind == "real") & ~t.arrow).sum()), flush=True)
    formal = {}
    for y in ("ret200", "ret1000", "fill200", "fill1000"):
        formal[y] = beta(ev, ev[y].to_numpy(float))
    ps = sorted(formal, key=lambda k: formal[k]["p"]); mx = 0.0
    for r, k in enumerate(ps):
        mx = max(mx, min(1.0, (len(ps) - r) * formal[k]["p"])); formal[k]["p_holm"] = mx
    desc = {"ret50": beta(ev, ev.ret50.to_numpy(float)), "fill50": beta(ev, ev.fill50.to_numpy(float))}
    for bk in ("Predator", "Ultra", "Fast", "Absorb"):
        sub = ev[(ev.kind == "pseudo") | (ev.bucket == bk)]
        if (sub.kind == "real").sum() > 100:
            desc["ret200_" + bk] = beta(sub, sub.ret200.to_numpy(float))
    for nm, g in (("real", ev[ev.kind == "real"]), ("pseudo", ev[ev.kind == "pseudo"])):
        desc["perfil_" + nm] = dict(t_ret_mediana=float(g.t_ret.median()), t_ret_p75=float(g.t_ret.quantile(0.75)),
                                    mae_h_mediana=float(g.mae_h.median()), mae_h_p75=float(g.mae_h.quantile(0.75)),
                                    mae_h_p90=float(g.mae_h.quantile(0.9)), dist_ticks_mediana=float(g.dist_ticks.median()),
                                    altura_mediana=float(g.height.median()))
    for k, v in list(formal.items()) + list(desc.items()):
        print(k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in v.items()}, flush=True)
    (OUT / "HFTV4_RETORNO_RESULTADOS.json").write_text(json.dumps(dict(formal=formal, descriptivo=desc), indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
