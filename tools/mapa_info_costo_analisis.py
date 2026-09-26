#!/usr/bin/env python3
r"""IVC: mapa de información contra costo (manifiesto docs/research/MANIFIESTO_MAPA_INFO_COSTO_20260926.md §5-6).

    python tools/mapa_info_costo_analisis.py --grid <dir con ivc_<INST>.parquet> --out <dir>
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

VARS = ["mom5", "mom15", "mom60", "mom240", "vwap", "ofi5", "ofi60", "zona", "gap", "vol30"]
NONDIR = {"vol30"}
HS = {"h1": 60, "h5": 300, "h15": 900, "h60": 3600, "h240": 14400, "cierre": None}
SPLIT = "20251130"
RTH_OPEN, RTH_CLOSE = 9 * 3600 + 30 * 60, 16 * 3600
PASSIVE = {"ES": 0.12, "NQ": 0.43}          # ahorro EXEC-QI por lado (pesimista, sin QI en ES)
N_BOOT, N_NULL, SEED, Q = 1000, 200, 20260926, 0.10
MIN_SES = 20                                  # con menos, el nulo entre sesiones es degenerado (prueba nula)


def spearman(x, y):
    if len(x) < 30:
        return np.nan
    rx, ry = rankdata(x), rankdata(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def bh(p, q):
    p = np.asarray(p, float); m = len(p)
    ok = np.isfinite(p); res = np.zeros(m, bool)
    if not ok.any():
        return res
    idx = np.nonzero(ok)[0]; pp = p[idx]; o = np.argsort(pp); mm = len(pp)
    pas = pp[o] <= q * np.arange(1, mm + 1) / mm
    k = np.max(np.nonzero(pas)[0]) + 1 if pas.any() else 0
    res[idx[o[:k]]] = True
    return res


def cell_stats(x, y, cost, ses, rng, sign=None):
    """Borde bruto por apuesta = (media Q5 − media Q1)/2 con el signo del IC; margen = borde − costo; bootstrap
    por sesión."""
    ic = spearman(x, y)
    q1, q4 = np.nanquantile(x, [0.2, 0.8])
    top, bot = x >= q4, x <= q1
    sgn = sign if sign is not None else (1.0 if ic >= 0 else -1.0)   # validación: signo de descubrimiento
    us = np.unique(ses); si = np.searchsorted(us, ses)
    def sums(mask):
        return (np.bincount(si[mask], weights=y[mask], minlength=len(us)),
                np.bincount(si[mask], minlength=len(us)).astype(float))
    st, nt = sums(top); sb, nb = sums(bot)
    sc = np.bincount(si, weights=cost, minlength=len(us)); nc = np.bincount(si, minlength=len(us)).astype(float)
    W = np.stack([np.bincount(rng.integers(0, len(us), len(us)), minlength=len(us)) for _ in range(N_BOOT)]).astype(float)
    edge = sgn * (st.sum() / max(nt.sum(), 1) - sb.sum() / max(nb.sum(), 1)) / 2
    edge_b = sgn * ((W @ st) / np.maximum(W @ nt, 1) - (W @ sb) / np.maximum(W @ nb, 1)) / 2
    cost_pt = sc.sum() / max(nc.sum(), 1); cost_b = (W @ sc) / np.maximum(W @ nc, 1)
    marg_b = edge_b - cost_b
    return dict(ic=ic, edge=float(edge), cost=float(cost_pt), margin=float(edge - cost_pt),
                margin_lo=float(np.quantile(marg_b, .025)), margin_hi=float(np.quantile(marg_b, .975)),
                edge_lo=float(np.quantile(edge_b, .025)), n=int(len(x)), sesiones=int(len(us)))


def null_ic(D, var, fcol, rng):
    """Nulo: la variable desplazada circularmente entre sesiones, emparejando la hora del día."""
    piv = D.pivot_table(index="td", columns="tod", values=var, aggfunc="first")
    tgt = D.pivot_table(index="td", columns="tod", values=fcol, aggfunc="first").reindex(index=piv.index, columns=piv.columns)
    X = piv.to_numpy(); Y = tgt.to_numpy(); S = X.shape[0]
    out = []
    for _ in range(N_NULL):
        sh = int(rng.integers(1, S)) if S > 1 else 0
        Xs = np.roll(X, sh, axis=0)
        m = np.isfinite(Xs) & np.isfinite(Y)
        out.append(spearman(Xs[m], Y[m]))
    return np.array(out, float)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    rows = []
    for f in sorted(glob.glob(str(Path(a.grid) / "ivc_*.parquet"))):
        G = pd.read_parquet(f)
        inst = str(G.inst.iloc[0]); comm = float(G.comm_side.iloc[0])
        G["rth"] = (G.tod >= RTH_OPEN) & (G.tod < RTH_CLOSE)
        for sub, gm in (("todo", np.ones(len(G), bool)), ("rth", G.rth.to_numpy()), ("eth", ~G.rth.to_numpy())):
            for var in VARS:
                for h in HS:
                    if var == "gap" and h != "cierre":
                        continue
                    fcol, scol = f"fwd_{h}", f"sp_{h}"
                    base = gm & G[var].notna().to_numpy() & G[fcol].notna().to_numpy()
                    if base.sum() < 30:
                        continue
                    y_all = G[fcol].to_numpy(float)
                    if var in NONDIR:
                        y_all = np.abs(y_all)
                    cost_all = G.spread.to_numpy(float) + G[scol].to_numpy(float) + 2 * comm
                    sgn_disc = None
                    for part, pm in (("disc", G.td.astype(str).to_numpy() <= SPLIT),
                                     ("val", G.td.astype(str).to_numpy() > SPLIT)):
                        m = base & pm
                        if m.sum() < 30 or G.td[m].nunique() < MIN_SES:
                            continue
                        st = cell_stats(G[var].to_numpy(float)[m], y_all[m], cost_all[m], G.td.to_numpy()[m], rng,
                                        sign=sgn_disc if part == "val" else None)
                        if part == "disc":
                            sgn_disc = 1.0 if (st["ic"] >= 0 or not np.isfinite(st["ic"])) else -1.0
                        elif sgn_disc is None:
                            continue                                  # sin descubrimiento no hay validación
                        nul = null_ic(G[m], var, fcol if var not in NONDIR else fcol, rng) if var not in NONDIR else None
                        if nul is not None and np.isfinite(st["ic"]):
                            ok = np.isfinite(nul)
                            st["p_null"] = float((np.abs(nul[ok]) >= abs(st["ic"])).mean()) if ok.any() else np.nan
                            st["mde_ic"] = float(1.96 * np.nanstd(nul))
                        st.update(inst=inst, sub=sub, var=var, h=h, part=part,
                                  margin_pasivo=st["margin"] + 2 * PASSIVE.get(inst, 0),
                                  canal="no_direccional" if var in NONDIR else "direccional")
                        rows.append(st)
    R = pd.DataFrame(rows)
    D = R[R.part == "disc"].set_index(["inst", "sub", "var", "h"])
    V = R[R.part == "val"].set_index(["inst", "sub", "var", "h"])
    M = D.join(V, rsuffix="_val", how="left")
    dirm = M.canal == "direccional"
    M["fdr"] = False
    M.loc[dirm, "fdr"] = bh(M.loc[dirm, "p_null"], Q)
    M["prometedora"] = (M.fdr & (M.margin_lo > 0) & (M.margin_val > 0) & (np.sign(M.ic_val) == np.sign(M.ic))
                        & (M.margin_lo_val > 0))
    M["prometedora_pasiva"] = (M.fdr & (M.margin_pasivo > 0) & (M.margin_pasivo_val > 0)
                               & (np.sign(M.ic_val) == np.sign(M.ic)))
    M = M.reset_index()
    M.to_csv(out / "ivc_mapa.csv", index=False)
    top = M.sort_values("margin", ascending=False)
    summ = dict(celdas=int(len(M)), fdr=int(M.fdr.sum()), prometedoras=int(M.prometedora.sum()),
                prometedoras_pasiva=int(M.prometedora_pasiva.sum()),
                margen_max_por_h={h: float(M[M.h == h].margin.max()) for h in HS if (M.h == h).any()},
                top15=top.head(15)[["inst", "sub", "var", "h", "ic", "edge", "cost", "margin", "margin_lo", "p_null",
                                    "fdr", "ic_val", "margin_val", "prometedora"]].to_dict("records"))
    (out / "ivc_resumen.json").write_text(json.dumps(summ, indent=1, default=float))
    print(json.dumps({k: v for k, v in summ.items() if k != "top15"}, indent=1))


if __name__ == "__main__":
    main()
