#!/usr/bin/env python3
r"""AVCL-VOL-2 A+B — etapa 2 (manifiesto docs/research/AVCL_VOL2_AB_MANIFIESTO_20261006.md).
AVCL-DIST (manifiesto docs/research/AVCL_DIST_MANIFIESTO_20261006.md). Lee el cache de la etapa 1 (<c>_bars.npz, <c>_blocks.parquet, <c>_zones.parquet) y estima, vectorizado:
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


def load_contract(c):
    z = np.load(next(f for f in files("_bars.npz") if Path(f).name == c + "_bars.npz"))
    blk = pd.read_parquet(next(f for f in files("_blocks.parquet") if Path(f).name == c + "_blocks.parquet"))
    zn = pd.read_parquet(next(f for f in files("_zones.parquet") if Path(f).name == c + "_zones.parquet"))
    return z, blk, zn


def build(c):
    z, blk, zn = load_contract(c)
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
    for k in ("anomaly_ratio", "cluster_share", "density", "quality_score", "burst_count", "distance_ticks"):
        d[k] = d.bar.map(za[k]).astype(float)
    d["width"] = d.bar.map(za.upper_tick - za.lower_tick + 1).astype(float)
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


def main():
    t0 = time.time()
    cs = sorted({Path(f).name[:-9] for f in files("_bars.npz")})
    parts = []
    for c in cs:
        d, _R = build(c); del _R; parts.append(d)
        print(c, len(d), "%.0f s" % (time.time() - t0), flush=True)
    D = pd.concat(parts, ignore_index=True); del parts
    rng = np.random.default_rng(20261006)
    formal, desc = [], []

    def prep(kind, H, sess_mask, use_pseudo):
        ctrl = (D.kind == "CTRL")
        if use_pseudo:
            ctrl = ctrl & (D.pseudo != 0)
        d = sample(D[sess_mask], kind, H, ctrl[sess_mask])
        d = d[d["rgb_%d" % H] > 0]
        lado = np.where(d.is_ev, d.side, d.pseudo) if use_pseudo else np.ones(len(d))
        s = lado * d["fwd_%d" % H].to_numpy() / d["rgb_%d" % H].to_numpy()
        return d, s

    for H in (10, 50, 200):
        d, s = prep("OFF", H, D.rth, True)
        for nm, k in (("alejamiento", 1.0), ("regreso", -1.0)):
            for thr in (1.0, 0.5, 2.0):
                y = (s >= thr).astype(float) if k > 0 else (s <= -thr).astype(float)
                b, se = lpm(d, y)
                base = float(y[~d.is_ev.to_numpy()].mean())
                r = dict(nombre="cola " + nm, kind="OFF", H=H, umbral_R=thr, beta=b, se=se, ci95=[b - 1.96 * se, b + 1.96 * se],
                         p=(float(2 * (1 - norm.cdf(abs(b / se)))) if se > 0 else 1.0), mde=2.8 * se, tasa_control=base, n_ev=int(d.is_ev.sum()))
                (formal if (H in (10, 50) and thr == 1.0) else desc).append(r)
        # cuantiles descriptivos de s (eventos vs controles), crudo
        qs = np.arange(1, 100)
        qe = np.percentile(s[d.is_ev.to_numpy()], qs); qc = np.percentile(s[~d.is_ev.to_numpy()], qs)
        desc.append(dict(nombre="cuantiles s/R OFF", H=H, q=qs.tolist(), eventos=qe.round(4).tolist(), controles=qc.round(4).tolist()))
        # por dosis y ancho
        ev = d.is_ev.to_numpy()
        for nm2, m in (("Q5 anomaly", d.anomaly_ratio >= d.anomaly_ratio[ev].quantile(0.8)),
                       ("Q1 anomaly", d.anomaly_ratio <= d.anomaly_ratio[ev].quantile(0.2)),
                       ("angosta", d.width <= d.width[ev].quantile(0.2)), ("ancha", d.width >= d.width[ev].quantile(0.8))):
            dd = d[(~d.is_ev) | m.fillna(False)]; ss = s[((~d.is_ev) | m.fillna(False)).to_numpy()]
            for nm, k in (("alejamiento", 1), ("regreso", -1)):
                y = (ss >= 1).astype(float) if k > 0 else (ss <= -1).astype(float)
                b, se = lpm(dd, y)
                desc.append(dict(nombre="cola " + nm + " | " + nm2, kind="OFF", H=H, beta=b, se=se, n_ev=int(dd.is_ev.sum())))
    for kind in ("AT", "OFF"):
        for H in (10, 50):
            d, s = prep(kind, H, D.rth, False)
            for thr in (1.0, 0.5, 2.0):
                y = (np.abs(s) >= thr).astype(float)
                b, se = lpm(d, y)
                r = dict(nombre="cola sin signo", kind=kind, H=H, umbral_R=thr, beta=b, se=se, ci95=[b - 1.96 * se, b + 1.96 * se],
                         p=(float(2 * (1 - norm.cdf(abs(b / se)))) if se > 0 else 1.0), mde=2.8 * se, tasa_control=float(y[~d.is_ev.to_numpy()].mean()))
                (formal if (H == 10 and thr == 1.0) else desc).append(r)
            qs = np.arange(1, 100)
            desc.append(dict(nombre="cuantiles |mov|/R", kind=kind, H=H, q=qs.tolist(),
                             eventos=np.percentile(np.abs(s[d.is_ev.to_numpy()]), qs).round(4).tolist(),
                             controles=np.percentile(np.abs(s[~d.is_ev.to_numpy()]), qs).round(4).tolist()))
    ps = [r["p"] for r in formal]; order = np.argsort(ps); mx = 0.0
    for rank, i in enumerate(order):
        mx = max(mx, min(1.0, (len(ps) - rank) * ps[i])); formal[i]["p_holm"] = mx
    for r in formal + [x for x in desc if "q" not in x]:
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k != "ci95"}, flush=True)
    res = dict(campaign="AVCL-DIST", manifest="docs/research/AVCL_DIST_MANIFIESTO_20261006.md", contracts=cs,
               formal=formal, descriptivo=desc, seconds=round(time.time() - t0))
    (OUT / "AVCL_DIST_RESULTADOS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("listo en %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
