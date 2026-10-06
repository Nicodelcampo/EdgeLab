#!/usr/bin/env python3
r"""AVCL-VOL-2 A+B — etapa 2 (manifiesto docs/research/AVCL_VOL2_AB_MANIFIESTO_20261006.md).
Lee el cache de la etapa 1 (<c>_bars.npz, <c>_blocks.parquet, <c>_zones.parquet) y estima, vectorizado:
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
HS = (10, 50)
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
    for H in HS:                                              # métricas idénticas a VOL-1
        rv_f = cs[b + H] - cs[b]; rv_b = cs[b] - cs[b - H]
        rmax_f = rolling_max(hi, H)[b + H]; rmin_f = rolling_min(lo, H)[b + H]
        rmax_b = rolling_max(hi, H)[b]; rmin_b = rolling_min(lo, H)[b]
        d["y_rv_%d" % H] = np.log((rv_f + 1e-12) / (rv_b + 1e-12))
        d["y_rg_%d" % H] = np.log((rmax_f - rmin_f + 1) / (rmax_b - rmin_b + 1))
        d["rvb_%d" % H] = rv_b
        d["ok_%d" % H] = send[b - H + 1] == send[b + H]
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


def main():
    t0 = time.time()
    cs = sorted({Path(f).name[:-9] for f in files("_bars.npz")})
    print("contratos", cs, flush=True)
    parts, Rs = [], []
    for c in cs:
        d, R = build(c); parts.append(d); Rs.append(R)
        print(c, len(d), "bloques", dict(d.kind.value_counts()), "%.0f s" % (time.time() - t0), flush=True)
    D = pd.concat(parts, ignore_index=True); R = np.vstack(Rs); del parts, Rs
    D["row"] = np.arange(len(D))
    formal, desc = [], []
    for kind in ("AT", "OFF"):
        for H in HS:
            for cname, ctrl in (("A1", D.kind == "CTRL"), ("A2", D.hv)):
                for sess, mask in (("RTH", D.rth), ("ETH", ~D.rth)):
                    d = sample(D[mask], kind, H, ctrl[mask])
                    if d.is_ev.sum() < 30 or (~d.is_ev).sum() < 30:
                        print("sin muestra", kind, H, cname, sess, flush=True); continue
                    ys = np.column_stack([d["y_rg_%d" % H], d["y_rv_%d" % H]])
                    b1, s1, ne, nc, ns = beta(d, ys, True)
                    b0, s0_, *_ = beta(d, ys, False)
                    for k, ch in enumerate(("y_rg", "y_rv")):
                        r = dict(kind=kind, H=H, contraste=cname, sesion=sess, channel=ch, n_events=ne, n_controls=nc,
                                 sessions=ns, beta=float(b1[k]), se=float(s1[k]),
                                 ci95=[float(b1[k] - 1.96 * s1[k]), float(b1[k] + 1.96 * s1[k])],
                                 p=float(1 - norm.cdf(b1[k] / s1[k])), beta_solo_S0=float(b0[k]), se_solo_S0=float(s0_[k]))
                        (formal if (H == 10 and sess == "RTH") else desc).append(r)
                        print(kind, H, cname, sess, ch, round(r["beta"], 4), [round(x, 4) for x in r["ci95"]],
                              "p=%.2g" % r["p"], "| solo S0", round(r["beta_solo_S0"], 4), flush=True)
    ps = [r["p"] for r in formal]; order = np.argsort(ps); mx = 0.0
    for rank, i in enumerate(order):
        mx = max(mx, min(1.0, (len(ps) - rank) * ps[i])); formal[i]["p_holm"] = mx
    # B: curvas de respuesta (RTH), todas las h a la vez
    curves = {}
    Db = D[D.okB & D.rth]
    for nm, ev, ctrl in (("AT", Db.kind == "AT", (Db.kind == "CTRL") & ~Db.hv & (Db.dist > 2 * HB)),
                         ("OFF", Db.kind == "OFF", (Db.kind == "CTRL") & ~Db.hv & (Db.dist > 2 * HB)),
                         ("VOL_ALTO_SIN_ZONA", Db.hv & (Db.dist > 2 * HB), (Db.kind == "CTRL") & ~Db.hv & (Db.dist > 2 * HB)),
                         ("AT_vs_VOL_ALTO", Db.kind == "AT", Db.hv & (Db.dist > 2 * HB))):
        d = Db[ev | ctrl].copy(); d["is_ev"] = ev[ev | ctrl].to_numpy()
        if d.is_ev.sum() < 30 or (~d.is_ev).sum() < 30:
            print("B sin muestra", nm, flush=True); continue
        d["rvdec"] = dec(d["rvb_10"].to_numpy())
        bt, se, ne, nc, ns = beta(d, R[d.row.to_numpy()], True)
        h = np.arange(1, HB + 1); pk = int(np.argmax(bt)); half = None
        after = np.flatnonzero(bt[pk:] <= bt[pk] / 2)
        if len(after): half = int(h[pk + after[0]])
        pos = (h >= h[pk]) & (bt > 0)
        tau = None
        if pos.sum() >= 3:
            k = -np.polyfit(h[pos], np.log(bt[pos]), 1)[0]
            tau = float(np.log(2) / k) if k > 0 else None
        base = float(d[d.is_ev].base_rng.mean())
        exc = np.cumsum((np.exp(bt) - 1) * base)
        curves[nm] = dict(n_events=ne, n_controls=nc, sessions=ns, beta=bt.round(5).tolist(), se=se.round(5).tolist(),
                          peak_h=int(h[pk]), peak=float(bt[pk]), half_life_first_cross=half, half_life_exp_fit=tau,
                          base_bar_range_ticks=base, excess_ticks_cum={str(x): float(exc[x - 1]) for x in (5, 10, 20, 50, 100, 200)})
        print("B", nm, "pico h", h[pk], round(float(bt[pk]), 4), "vida media", half, tau, "exceso ticks 10/50",
              round(float(exc[9]), 2), round(float(exc[49]), 2), flush=True)
    res = dict(campaign="AVCL-VOL-2 A+B", manifest="docs/research/AVCL_VOL2_AB_MANIFIESTO_20261006.md",
               contracts=cs, formal_rth_H10=formal, descriptivo=desc, curvas_B=curves, seconds=round(time.time() - t0))
    (OUT / "AVCL_VOL2_AB_RESULTADOS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("listo en %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
