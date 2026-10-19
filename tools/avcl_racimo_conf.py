#!/usr/bin/env python3
"""AVCL-RACIMO (manifiesto docs/research/AVCL_RACIMO_MANIFIESTO_20261006.md). Lee caches de zonas/barras
(<c>_<spec>t_bars.npz, <c>_<cell>_zones.parquet, <c>_<cell>_blocks.parquet) para las celdas 'base' (50t) y 't25' (25t)."""
import glob
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.stats import norm

IN = [Path(p) for p in sys.argv[1:]] or [Path("/kaggle/input")]
OUT = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path(os.environ.get("AVCL_OUT", "."))
CELLS = {"base": 50}
HS = (10, 50)
W = 10


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


def beta(d, flag, y):
    ok = np.isfinite(y)
    d, flag, y = d[ok], flag[ok], y[ok]
    if flag.sum() < 30 or (~flag).sum() < 30:
        return np.nan, np.nan, int(flag.sum()), int((~flag).sum())
    groups = [(d.contract + "|" + d.clock.astype(str)).to_numpy(), d.ampT.to_numpy(), d.voldec.to_numpy()]
    Z = absorb(np.column_stack([flag.astype(float), y]), groups)
    e, Y = Z[:, 0], Z[:, 1]
    ee = e @ e; bt = (e @ Y) / ee; U = Y - e * bt
    sid = pd.factorize(d.session.to_numpy())[0]; G = sid.max() + 1
    S = np.bincount(sid, weights=e * U, minlength=G)
    se = np.sqrt((S ** 2).sum() * G / (G - 1)) / ee
    return float(bt), float(se), int(flag.sum()), int((~flag).sum())


def build(c, cell, spec):
    z = np.load(next(f for f in files("_bars.npz") if Path(f).name == "%s_%dt_bars.npz" % (c, spec)))
    zn = pd.read_parquet(next(f for f in files("_zones.parquet") if Path(f).name == "%s_%s_zones.parquet" % (c, cell)))
    blk = pd.read_parquet(next(f for f in files("_blocks.parquet") if Path(f).name == "%s_%s_blocks.parquet" % (c, cell)))
    hi = z["high_t"].astype(float); lo = z["low_t"].astype(float); cl = z["close_t"].astype(float)
    send = z["send"]; sdate = z["sdate"]; appr = z["approved"]; mins = z["mins"].astype(int); n = len(cl)
    end = z["end_ns"]
    zn = zn.sort_values("created_bar").reset_index(drop=True)
    cb = zn.created_bar.to_numpy().astype(np.int64)
    lo_t = zn.lower_tick.to_numpy(); hi_t = zn.upper_tick.to_numpy(); mid = (lo_t + hi_t) / 2.0
    # criterio secundario y primer miembro del racimo (principal: centros a <= 40 ticks en 200 barras)
    dense = np.zeros(len(zn), int); first = cb.copy(); iso = np.ones(len(zn), bool)
    for i in range(len(zn)):
        j0 = np.searchsorted(cb, cb[i] - 120)
        m = (lo_t[j0:i] - 8 <= hi_t[i]) & (hi_t[j0:i] + 8 >= lo_t[i])
        dense[i] = 1 + m.sum()
        j1 = np.searchsorted(cb, cb[i] - 200)
        mp = np.abs(mid[j1:i] - mid[i]) <= 40
        if mp.any():
            first[i] = cb[j1:i][mp].min()
        j2 = np.searchsorted(cb, cb[i] + 200, side="right")
        neigh = np.abs(mid[j1:j2] - mid[i]) <= 40
        iso[i] = neigh.sum() == 1
    bb = blk.bar.to_numpy().astype(np.int64)
    k = np.searchsorted(bb, first)
    bstart = np.where(k > 0, bb[np.maximum(k - 1, 0)] + 1, 0)
    bstart = np.maximum(bstart, first - W + 1)
    d = pd.DataFrame(dict(bar=cb, kind=np.where(zn.kind == "OFF_PRICE", "OFF", "AT"), side=zn.direction.to_numpy(),
                          burst=zn.burst_count.to_numpy(), dense=dense, iso=iso, bs=bstart))
    d = d[(d.bar >= 300) & (d.bar + 60 < n) & (d.bs - 60 >= 0)]
    d = d[appr[d.bar] & ((mins[d.bar] >= 510) & (mins[d.bar] < 900))]
    b = d.bar.to_numpy(); bs = d.bs.to_numpy()
    d["contract"] = c; d["session"] = sdate[b]; d["clock"] = mins[b] // 30
    vb = blk.set_index("bar").vol
    d["voldec"] = pd.qcut(pd.Series(vb.reindex(b).to_numpy()).rank(method="first"), 10, labels=False).to_numpy()
    a50 = (pd.Series(hi).rolling(50).max() - pd.Series(lo).rolling(50).min()).to_numpy()
    d["ampT"] = pd.qcut(pd.Series(a50[b]).rank(method="first"), 3, labels=False).to_numpy()
    for H in HS:
        same = (send[b + H] == send[b]) & (send[np.maximum(bs - H, 0)] == send[b])
        rf = pd.Series(hi).rolling(H).max().to_numpy()[b + H] - pd.Series(lo).rolling(H).min().to_numpy()[b + H]
        rp = pd.Series(hi).rolling(H).max().to_numpy()[bs - 1] - pd.Series(lo).rolling(H).min().to_numpy()[bs - 1]
        U = pd.Series(hi).rolling(H).max().to_numpy()[b + H] - cl[b]
        D = cl[b] - pd.Series(lo).rolling(H).min().to_numpy()[b + H]
        asim = np.where(U + D > 0, (U - D) / np.maximum(U + D, 1e-9), np.nan)
        d["y_pre%d" % H] = np.where(same, np.log((rf + 1) / (rp + 1)), np.nan)
        d["s%d" % H] = np.where(same & (d.side != 0), d.side * asim, np.nan)
        d["tail%d" % H] = np.where(same & (rp > 0), (np.abs(cl[b + H] - cl[b]) >= rp).astype(float), np.nan)
    return d


def rec(name, b, se, nr, ni, **kw):
    p = float(2 * (1 - norm.cdf(abs(b / se)))) if np.isfinite(se) and se > 0 else 1.0
    return dict(nombre=name, beta=b, se=se, ci95=[b - 1.96 * se, b + 1.96 * se], p=p, mde=2.8 * se, n_racimo=nr, n_aislada=ni, **kw)


def battery(D, flagcol, label, formal=False):
    out = []
    for kind in ("AT", "OFF"):
        x = D[(D.kind == kind) & (D[flagcol] | D.iso)]
        f = x[flagcol].to_numpy()
        for H in HS:
            out.append(rec("y_pre H%d" % H, *beta(x, f, x["y_pre%d" % H].to_numpy()), kind=kind, criterio=label))
        out.append(rec("cola sin signo H10", *beta(x, f, x["tail10"].to_numpy()), kind=kind, criterio=label))
        if kind == "OFF":
            for H in HS:
                out.append(rec("s (lado x asim) H%d" % H, *beta(x, f, x["s%d" % H].to_numpy()), kind=kind, criterio=label))
    return out



def main():
    from scipy.stats import norm as _n
    cs = sorted({Path(f).name.replace("_base_zones.parquet", "") for f in files("_base_zones.parquet")})
    parts, vacios = [], []
    for c in cs:
        zf = next(f for f in files("_zones.parquet") if Path(f).name == "%s_base_zones.parquet" % c)
        if len(pd.read_parquet(zf)) == 0 or "created_bar" not in pd.read_parquet(zf).columns:
            vacios.append(c); continue                      # contrato sin zonas (sin historia para el umbral)
        parts.append(build(c, "base", 50))
    print("contratos sin zonas (excluidos):", vacios, flush=True)
    D = pd.concat(parts, ignore_index=True)
    D["inst"] = D.contract.str.split("_").str[0]
    D = D[D.inst.isin(["ES", "YM", "RTY", "MGC"])].reset_index(drop=True)
    D["prin"] = D.burst >= 3; D["sec"] = D.dense >= 3
    x = D[(D.kind == "OFF") & (D.prin | D.iso)]
    b, se, nr, ni = beta(x, x.prin.to_numpy(), x["s50"].to_numpy())
    p = float(_n.cdf(b / se))
    formal = dict(beta=b, se=se, mde=2.5 * se, n_racimo=nr, n_aislada=ni, p_unilateral=p,
                  decision="CONFIRMA" if p <= 0.05 else "DESCARTADA")
    print("FORMAL", formal, flush=True)
    desc = {}
    for inst in ("ES", "YM", "RTY", "MGC"):
        xi = x[x.inst == inst]
        desc["s50_" + inst] = beta(xi, xi.prin.to_numpy(), xi["s50"].to_numpy())
    desc["s10"] = beta(x, x.prin.to_numpy(), x["s10"].to_numpy())
    xs = D[(D.kind == "OFF") & (D.sec | D.iso)]
    desc["s50_denso"] = beta(xs, xs.sec.to_numpy(), xs["s50"].to_numpy())
    for k in ("AT", "OFF"):
        xk = D[(D.kind == k) & (D.prin | D.iso)]
        desc["y_pre50_" + k] = beta(xk, xk.prin.to_numpy(), xk["y_pre50"].to_numpy())
    for k_, v_ in desc.items():
        print("DESC", k_, [round(q, 4) if isinstance(q, float) else q for q in v_], flush=True)
    res = dict(campaign="AVCL-RACIMO-CONF", preregistro="docs/research/AVCL_RACIMO_PREREGISTRO_20261006.md (a578a7a1)",
               contratos=cs, formal=formal, descriptivo={k_: list(v_) for k_, v_ in desc.items()})
    (OUT / "AVCL_RACIMO_CONF_RESULTADOS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
