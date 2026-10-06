#!/usr/bin/env python3
r"""AVCL-VOL-2 A+B — etapa 2 (manifiesto docs/research/AVCL_VOL2_AB_MANIFIESTO_20261006.md).
AVCL-PRE (manifiesto docs/research/AVCL_PRE_MANIFIESTO_20261006.md): ventana previa FUERA del bloque creador. Lee el cache de la etapa 1 (<c>_bars.npz, <c>_blocks.parquet, <c>_zones.parquet) y estima, vectorizado:
A) β de evento con FE (S0, int10, int50, vol20, vpk), SE clusterizado por sesión, A1 (controles comunes) y A2
   (controles = volumen alto sin zona), Holm 8. B) curva de respuesta h=1..200 (descriptiva)."""
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
HS = (10, 50, 200)
HB = 200
NBASE = 20


def files(suffix):
    out = []
    for r in IN:
        out += glob.glob(str(r / "**" / ("*" + suffix)), recursive=True)
    return sorted(set(out))


def dec(x, q=10):
    return pd.qcut(pd.Series(x).rank(method="first"), q, labels=False).to_numpy()


def rolling_max(a, w):
    return pd.Series(a).rolling(w).max().to_numpy()


def rolling_min(a, w):
    return pd.Series(a).rolling(w).min().to_numpy()


def load_contract(c, cell, spec):
    z = np.load(next(f for f in files("_bars.npz") if Path(f).name == "%s_%dt_bars.npz" % (c, spec)))
    blk = pd.read_parquet(next(f for f in files("_blocks.parquet") if Path(f).name == "%s_%s_blocks.parquet" % (c, cell)))
    zn = pd.read_parquet(next(f for f in files("_zones.parquet") if Path(f).name == "%s_%s_zones.parquet" % (c, cell)))
    return z, blk, zn


def build(c, cell="base", spec=50):
    z, blk, zn = load_contract(c, cell, spec)
    hi = z["high_t"].astype(float); lo = z["low_t"].astype(float); n = len(hi)
    lc = np.log(z["close_t"].astype(float)); ret2 = np.r_[0.0, np.diff(lc) ** 2]; cs = np.cumsum(ret2)
    send = z["send"]; sdate = z["sdate"]; appr = z["approved"]; mins = z["mins"].astype(int)
    st, en = z["start_ns"], z["end_ns"]; vol = z["volume"].astype(float)
    kind = dict(zip(zn.created_bar.astype(int), np.where(zn.kind == "OFF_PRICE", "OFF", "AT")))
    side = dict(zip(zn.created_bar.astype(int), zn.direction.astype(int)))
    cbar = np.array(sorted(kind), dtype=np.int64)
    b = blk.bar.to_numpy().astype(np.int64)
    keep = (b >= 60) & (b + HB + 1 < n)
    b = b[keep]; bv = blk.vol.to_numpy()[keep]
    a = appr[b]; b, bv = b[a], bv[a]
    d = pd.DataFrame(dict(bar=b, vol=bv))
    d["kind"] = d.bar.map(kind).fillna("CTRL"); d["side"] = d.bar.map(side).fillna(0).astype(int)
    d["contract"] = c; d["session"] = sdate[b]; d["clock"] = mins[b] // 30
    d["rth"] = (mins[b] >= 510) & (mins[b] < 900)
    d["voldec"] = dec(bv); d["vol20"] = dec(bv, 20)
    d["int10"] = dec((en[b] - st[b - 9]) / 1e9); d["int50"] = dec((en[b] - st[b - 49]) / 1e9)
    d["vpk"] = dec(rolling_max(vol, 10)[b])
    p95 = d.groupby("clock").vol.transform(lambda v: v.quantile(0.95))
    d["hv"] = (d.kind == "CTRL") & (d.vol >= p95)
    if len(cbar):
        j = np.searchsorted(cbar, b)
        dist = np.minimum(np.abs(b - cbar[np.clip(j, 0, len(cbar) - 1)]), np.abs(b - cbar[np.clip(j - 1, 0, len(cbar) - 1)]))
    else:
        dist = np.full(len(b), 10 ** 9)
    d["dist"] = dist
    cl_ = z["close_t"].astype(float)
    d["pseudo"] = np.sign(cl_[b] - cl_[b - 10]).astype(int)
    za = zn.set_index(zn.created_bar.astype(int))
    for k in ("anomaly_ratio", "cluster_share", "density", "quality_score", "burst_count", "distance_ticks", "delta", "band_vol"):
        d[k] = d.bar.map(za[k]).astype(float)
    d["width"] = d.bar.map(za.upper_tick - za.lower_tick + 1).astype(float)
    # inicio del bloque creador/candidato: AVCL = barra siguiente al bloque anterior (o inicio de sesión); VTD = la barra
    BB = np.sort(blk.bar.to_numpy().astype(np.int64))
    if cell.startswith("vtd"):
        bs = b.copy()
    else:
        j = np.searchsorted(BB, b)
        prev = np.where(j > 0, BB[np.maximum(j - 1, 0)] + 1, 0)
        sfirst = np.r_[0, np.flatnonzero(np.diff(send)) + 1]
        s0 = sfirst[np.searchsorted(sfirst, b, side="right") - 1]
        bs = np.maximum(prev, s0)
    d["blen"] = b - bs + 1
    for H in (10, 50):
        okp = bs - H >= 0
        bsx = np.maximum(bs - 1, H - 1)
        rmax_p = rolling_max(hi, H)[bsx]; rmin_p = rolling_min(lo, H)[bsx]
        rmax_f = rolling_max(hi, H)[b + H]; rmin_f = rolling_min(lo, H)[b + H]
        d["y_rgp_%d" % H] = np.log((rmax_f - rmin_f + 1) / (rmax_p - rmin_p + 1))
        d["rgp_%d" % H] = rmax_p - rmin_p
        d["okp_%d" % H] = okp & (send[np.maximum(bs - H, 0)] == send[b + H])
    for H in HS:                                              # métricas idénticas a VOL-1
        rv_f = cs[b + H] - cs[b]; rv_b = cs[b] - cs[b - H]
        rmax_f = rolling_max(hi, H)[b + H]; rmin_f = rolling_min(lo, H)[b + H]
        rmax_b = rolling_max(hi, H)[b]; rmin_b = rolling_min(lo, H)[b]
        d["y_rv_%d" % H] = np.log((rv_f + 1e-12) / (rv_b + 1e-12))
        d["y_rg_%d" % H] = np.log((rmax_f - rmin_f + 1) / (rmax_b - rmin_b + 1))
        d["rvb_%d" % H] = rv_b
        d["rgb_%d" % H] = rmax_b - rmin_b
        d["ok_%d" % H] = send[b - H + 1] == send[b + H]
        d["fwd_%d" % H] = (z["close_t"][b + H].astype(float) - z["close_t"][b].astype(float))
    lr = np.log(hi - lo + 1)
    base = pd.Series(lr).rolling(NBASE).mean().to_numpy()[b]
    R = lr[b[:, None] + np.arange(1, HB + 1)[None, :]] - base[:, None]
    d["okB"] = (send[b - NBASE + 1] == send[b + HB])
    d["base_rng"] = np.exp(base) - 1
    return d, R.astype(np.float32)


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


def beta(df, y, extra=True):
    """β de 'is_ev' sobre Y (n×k) con FE; SE clusterizado por sesión. Devuelve arrays de largo k."""
    s0 = (df.contract + "|" + df.clock.astype(str) + "|" + df.voldec.astype(str) + "|" + df.rvdec.astype(str)).to_numpy()
    groups = [s0] + ([df.int10.to_numpy(), df.int50.to_numpy(), df.vol20.to_numpy(), df.vpk.to_numpy()] if extra else [])
    Z = absorb(np.column_stack([df.is_ev.to_numpy().astype(float), y]), groups)
    e, Y = Z[:, 0], Z[:, 1:]
    ee = e @ e
    bt = (e @ Y) / ee
    U = Y - e[:, None] * bt[None, :]
    sid = pd.factorize(df.session.to_numpy())[0]; G = sid.max() + 1
    S = np.zeros((G, Y.shape[1])); np.add.at(S, sid, e[:, None] * U)
    se = np.sqrt((S ** 2).sum(0) * G / (G - 1)) / ee
    return bt, se, int(df.is_ev.sum()), int((~df.is_ev).sum()), int(df[df.is_ev].session.nunique())


def sample(D, kind, H, ctrl):
    d = D[D["ok_%d" % H] & ((D.kind == kind) | (ctrl & (D.dist > 2 * H)))].copy()
    d["is_ev"] = (d.kind == kind).to_numpy()
    d["rvdec"] = dec(d["rvb_%d" % H].to_numpy())
    return d



def ols_fe(df, X, y, groups, cluster):
    """FWL: absorbe FE en [X, y]; OLS de y~ sobre X~; SE clusterizado."""
    Z = absorb(np.column_stack([X, y]), groups)
    Xt, yt = Z[:, :-1], Z[:, -1]
    XtX = Xt.T @ Xt; b = np.linalg.solve(XtX, Xt.T @ yt); u = yt - Xt @ b
    cid = pd.factorize(cluster)[0]; G = cid.max() + 1
    S = np.zeros((G, Xt.shape[1])); np.add.at(S, cid, Xt * u[:, None])
    inv = np.linalg.inv(XtX); V = inv @ (S.T @ S) @ inv * G / (G - 1)
    return b, np.sqrt(np.diag(V))


def groups_of(d, extra=True):
    s0 = (d.contract + "|" + d.clock.astype(str) + "|" + d.voldec.astype(str) + "|" + d.rvdec.astype(str)).to_numpy()
    return [s0] + ([d.int10.to_numpy(), d.int50.to_numpy(), d.vol20.to_numpy(), d.vpk.to_numpy()] if extra else [])


def b1(d, ch, cluster=None):
    bt, se = ols_fe(d, d.is_ev.to_numpy(float)[:, None], d[ch].to_numpy(), groups_of(d),
                    d.session.to_numpy() if cluster is None else cluster)
    return float(bt[0]), float(se[0])


def rec(name, b, se, **kw):
    return dict(nombre=name, beta=b, se=se, ci95=[b - 1.96 * se, b + 1.96 * se], p=(float(2 * (1 - norm.cdf(abs(b / se)))) if se > 0 else 1.0), **kw)



def lpm(d, y):
    bt, se = ols_fe(d, d.is_ev.to_numpy(float)[:, None], y, groups_of(d), d.session.to_numpy())
    return float(bt[0]), float(se[0])



CELLS = {"base": 50, "p90": 50, "p98": 50, "W5": 50, "W20": 50, "k15": 50, "k30": 50, "m4": 50, "t200": 200,
         "p90W5": 50, "p90W20": 50, "p98W5": 50, "p98W20": 50, "vtd150": 150, "vtd50": 50}


def pz(b, se):
    return float(2 * (1 - norm.cdf(abs(b / se)))) if se > 0 else 1.0


def rec(name, b, se, **kw):
    return dict(nombre=name, beta=b, se=se, ci95=[b - 1.96 * se, b + 1.96 * se], p=pz(b, se), mde=2.8 * se, **kw)


def samplep(D, kind, H, ctrl):
    d = D[D["okp_%d" % H] & D["ok_%d" % H] & ((D.kind == kind) | (ctrl & (D.dist > 2 * H)))].copy()
    d["is_ev"] = (d.kind == kind).to_numpy()
    d["rvdec"] = dec(d["rvb_%d" % H].to_numpy())
    return d


def cell_battery(D, mask, label, kinds):
    out = []
    for kind in kinds:
        for cname, ctrl in (("A1", D.kind == "CTRL"), ("A2", D.hv)):
            d = samplep(D[mask], kind, 10, ctrl[mask])
            if d.is_ev.sum() < 30 or (~d.is_ev).sum() < 30:
                continue
            bp, sep = lpm(d, d["y_rgp_10"].to_numpy())
            bo, seo = lpm(d, d["y_rg_10"].to_numpy())          # métrica vieja sobre la MISMA muestra
            out.append(rec("y_rg_pre H10 " + cname, bp, sep, kind=kind, celda=label, n_ev=int(d.is_ev.sum()),
                           beta_metrica_vieja=bo, blen_mediana=float(d[d.is_ev].blen.median())))
        d = samplep(D[mask], kind, 10, (D.kind == "CTRL")[mask])
        d = d[d["rgp_10"] > 0]
        y = (np.abs(d["fwd_10"].to_numpy()) / d["rgp_10"].to_numpy() >= 1).astype(float)
        b2, se2 = lpm(d, y)
        out.append(rec("cola sin signo pre H10", b2, se2, kind=kind, celda=label, tasa_control=float(y[~d.is_ev.to_numpy()].mean())))
        d = samplep(D[mask], kind, 50, (D.kind == "CTRL")[mask])
        b3, se3 = lpm(d, d["y_rgp_50"].to_numpy())
        out.append(rec("y_rg_pre H50 A1", b3, se3, kind=kind, celda=label))
    return out


FORMAL = {("base", "AT", "y_rg_pre H10 A1"), ("base", "AT", "y_rg_pre H10 A2"), ("base", "OFF", "y_rg_pre H10 A1"),
          ("base", "OFF", "y_rg_pre H10 A2"), ("W20", "AT", "y_rg_pre H10 A1"), ("W20", "OFF", "y_rg_pre H10 A1"),
          ("vtd150", "AT", "y_rg_pre H10 A1"), ("vtd50", "AT", "y_rg_pre H10 A1")}


def main():
    t0 = time.time()
    cs = sorted({"_".join(Path(f).name.split("_")[:2]) for f in files("_bars.npz")})
    print("contratos", cs, flush=True)
    formal, desc = [], []
    for cell, spec in CELLS.items():
        parts = []
        for c in cs:
            d, _R = build(c, cell, spec)
            del _R
            parts.append(d)
        D = pd.concat(parts, ignore_index=True)
        del parts
        kinds = ("AT",) if cell.startswith("vtd") else ("AT", "OFF")
        res = cell_battery(D, D.rth, cell, kinds)
        for r in res:
            (formal if (r["celda"], r["kind"], r["nombre"]) in FORMAL else desc).append(r)
            print(cell, r["kind"], r["nombre"], "pre %.4f" % r["beta"], "+-%.4f" % (1.96 * r["se"]),
                  ("vieja %.4f" % r["beta_metrica_vieja"]) if "beta_metrica_vieja" in r else "", flush=True)
        desc += [dict(r, sesion="ETH") for r in cell_battery(D, ~D.rth, cell, kinds) if r["nombre"].startswith("y_rg_pre H10 A1")]
        del D
        print(cell, "%.0f s" % (time.time() - t0), flush=True)
    ps = [r["p"] for r in formal]
    order = np.argsort(ps)
    mx = 0.0
    for rank, i in enumerate(order):
        mx = max(mx, min(1.0, (len(ps) - rank) * ps[i]))
        formal[i]["p_holm"] = mx
    res = dict(campaign="AVCL-PRE", manifest="docs/research/AVCL_PRE_MANIFIESTO_20261006.md", contracts=cs,
               formal=formal, descriptivo=desc, seconds=round(time.time() - t0))
    (OUT / "AVCL_PRE_RESULTADOS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("listo en %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
