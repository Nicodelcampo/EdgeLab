#!/usr/bin/env python3
"""AVZP2-REBOTE análisis (manifiesto docs/research/AVZP2_REBOTE_MANIFIESTO_20261007.md).
Rebote al primer regreso: zona real vs pseudo-zona (misma geometría), por familia. Descubrimiento 4 contratos, Holm 4;
confirmación 2 contratos sólo para las que pasan. Más el canal no direccional y AVZP2 - AVCL descriptivo."""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.stats import norm

IN = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else IN
CONF = ("MNQ_09-26", "MNQ_12-26")
import os
PAT = os.environ.get("AVZP2_PAT", "*_avzp2.parquet")   # enmienda 1: "*_avzp2ob.parquet"


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
    Z = absorb(np.column_stack([f.astype(float), y]),
               [(d.contract + "|" + d.clock.astype(str)).to_numpy(), d.ampT.to_numpy(), d.Dd.to_numpy()])
    e, Y = Z[:, 0], Z[:, 1]
    ee = e @ e; b = (e @ Y) / ee; U = Y - e * b
    sid = pd.factorize(d.session.to_numpy())[0]; G = sid.max() + 1
    S = np.bincount(sid, weights=e * U, minlength=G)
    se = float(np.sqrt((S ** 2).sum() * G / (G - 1)) / ee)
    return dict(beta=float(b), se=se, z=float(b / se), p=float(2 * (1 - norm.cdf(abs(b / se)))), mde=2.8 * se,
                tasa_real=float(y[f].mean()), tasa_pseudo=float(y[~f].mean()), n_real=int(f.sum()), n_pseudo=int((~f).sum()),
                n_sesiones=int(G))


def prep(t):
    e = t[t.tt >= 0].copy()
    e["y_reb"] = np.where(e.reb >= 0, (e.reb == 1).astype(float), np.nan)
    e["y_act"] = np.where(e.act >= 0, e.act.astype(float), np.nan)
    e["ampT"] = pd.qcut(e.amp.rank(method="first"), 3, labels=False)
    e["Dd"] = pd.qcut(e.D.rank(method="first"), 10, labels=False, duplicates="drop")
    return e


def fams(e):
    f = {"AVZP2_todas": e[e.fam.isin(["AVZP2_azul", "AVZP2_roja"])], "AVZP2_azul": e[e.fam == "AVZP2_azul"],
         "AVZP2_roja": e[e.fam == "AVZP2_roja"], "AVCL": e[e.fam == "AVCL"]}
    if PAT != "*_avzp2.parquet":
        f = {"AVZP2_roja": f["AVZP2_roja"]}
    return f


def excess_boot(dA, dB, rng, nb=1000):
    """(reb real - reb pseudo) de A menos el de B, sin FE, IC por bootstrap de sesiones."""
    def ex(d):
        g = d[np.isfinite(d.y_reb)].groupby(["session", "kind"]).y_reb.agg(["sum", "count"]).unstack(fill_value=0)
        return g
    gA, gB = ex(dA), ex(dB)
    ss = np.union1d(gA.index, gB.index)
    gA, gB = gA.reindex(ss, fill_value=0), gB.reindex(ss, fill_value=0)
    def stat(ix):
        a, b = gA.iloc[ix].sum(), gB.iloc[ix].sum()
        ea = a[("sum", "real")] / a[("count", "real")] - a[("sum", "pseudo")] / a[("count", "pseudo")]
        eb = b[("sum", "real")] / b[("count", "real")] - b[("sum", "pseudo")] / b[("count", "pseudo")]
        return ea - eb
    full = stat(np.arange(len(ss)))
    bs = [stat(rng.integers(0, len(ss), len(ss))) for _ in range(nb)]
    return dict(dif=float(full), ic95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])


def main():
    t = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(IN / "**" / PAT), recursive=True))], ignore_index=True)
    print("contratos", sorted(t.contract.unique()))
    out = {"descubrimiento": {}, "no_direccional": {}, "confirmacion": {}}
    D = prep(t[~t.contract.isin(CONF)])
    for k, d in fams(D).items():
        out["descubrimiento"][k] = beta(d, d.y_reb.to_numpy())
        out["no_direccional"][k] = beta(d, d.y_act.to_numpy())
    ps = sorted(out["descubrimiento"], key=lambda k: out["descubrimiento"][k]["p"]); mx = 0.0
    for r, k in enumerate(ps):
        mx = max(mx, min(1.0, (len(ps) - r) * out["descubrimiento"][k]["p"])); out["descubrimiento"][k]["p_holm"] = mx
    rng = np.random.default_rng(20261007)
    F = fams(D)
    if "AVCL" in F:
        out["avzp2_menos_avcl_descriptivo"] = excess_boot(F["AVZP2_todas"], F["AVCL"], rng)
        out["roja_menos_azul_descriptivo"] = excess_boot(F["AVZP2_roja"], F["AVZP2_azul"], rng)
    perfil = {}
    for k, d in F.items():
        for kind, g in d.groupby("kind"):
            gg = g[g.reb >= 0]
            perfil["%s_%s" % (k, kind)] = dict(eventos=int(len(g)), ambiguos=int((g.reb == -2).sum()), sin_resultado=int((g.reb == -1).sum()),
                                              barras_mediana=float(gg.nb.median()), D_mediana_ticks=float(g.D.median()))
    out["perfil"] = perfil
    pasan = [k for k, v in out["descubrimiento"].items() if v["p_holm"] <= 0.05 and v["beta"] > 0]
    out["pasan_descubrimiento"] = pasan
    if pasan and t.contract.isin(CONF).any():
        C = fams(prep(t[t.contract.isin(CONF)]))
        res = {k: beta(C[k], C[k].y_reb.to_numpy()) for k in pasan}
        ps = sorted(res, key=lambda k: res[k]["p"]); mx = 0.0
        for r, k in enumerate(ps):
            mx = max(mx, min(1.0, (len(ps) - r) * res[k]["p"])); res[k]["p_holm"] = mx
            res[k]["confirma"] = bool(mx <= 0.05 and res[k]["beta"] > 0)
        out["confirmacion"] = res
    (OUT / ("AVZP2_REBOTE_RESULTADOS.json" if PAT == "*_avzp2.parquet" else "AVZP2_OB_APAREADO_RESULTADOS.json")).write_text(json.dumps(out, indent=1), encoding="utf-8")
    for sec in ("descubrimiento", "no_direccional", "confirmacion"):
        for k, v in out[sec].items():
            print(sec, k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in v.items()})
    print("AVZP2-AVCL", out.get("avzp2_menos_avcl_descriptivo"), "| roja-azul", out.get("roja_menos_azul_descriptivo"))
    print(json.dumps(perfil, indent=0))


if __name__ == "__main__":
    main()
