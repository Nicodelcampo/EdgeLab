#!/usr/bin/env python3
r"""AVCL-VOL-2 A+B — etapa 2 (manifiesto docs/research/AVCL_VOL2_AB_MANIFIESTO_20261006.md).
AVCL-EXIT (manifiesto docs/research/AVCL_EXIT_MANIFIESTO_20261006.md): salida de la zona vs pseudo-zonas. Lee el cache de la etapa 1 (<c>_bars.npz, <c>_blocks.parquet, <c>_zones.parquet) y estima, vectorizado:
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



KS = (4, 8, 16)
KT = 500
NPSEUDO = 3


def first_exit(hi, lo, cl, send, b, lower, upper, k):
    """Primera barra en (b, b+KT] de la misma sesión cuyo close queda >= k ticks fuera de [lower, upper]."""
    n = len(cl)
    idx = np.minimum(b[:, None] + np.arange(1, KT + 1)[None, :], n - 1)
    same = send[idx] == send[b][:, None]
    C = cl[idx]
    up = (C >= upper[:, None] + k) & same
    dn = (C <= lower[:, None] - k) & same
    ex = up | dn
    has = ex.any(1)
    f = ex.argmax(1)
    e = np.where(has, b + 1 + f, -1)
    direction = np.where(has, np.where(up[np.arange(len(b)), f], 1, -1), 0)
    inside = ((C >= lower[:, None]) & (C <= upper[:, None]) & same)
    cons = np.array([inside[i, :f[i]].sum() if has[i] else 0 for i in range(len(b))])
    return e, direction, cons


def build_exit(c, rng):
    z = np.load(next(f for f in files("_bars.npz") if Path(f).name == "%s_50t_bars.npz" % c))
    blk = pd.read_parquet(next(f for f in files("_blocks.parquet") if Path(f).name == "%s_base_blocks.parquet" % c))
    zn = pd.read_parquet(next(f for f in files("_zones.parquet") if Path(f).name == "%s_base_zones.parquet" % c))
    hi = z["high_t"].astype(np.int64); lo = z["low_t"].astype(np.int64); cl = z["close_t"].astype(np.int64)
    n = len(cl); send = z["send"]; sdate = z["sdate"]; appr = z["approved"]; mins = z["mins"].astype(int)
    st, en = z["start_ns"], z["end_ns"]; vol = z["volume"].astype(float)
    zn = zn[(zn.created_bar >= 60) & (zn.created_bar + KT + 210 < n)]
    zn = zn[appr[zn.created_bar.astype(int)]]
    zb = zn.created_bar.to_numpy().astype(np.int64)
    real = pd.DataFrame(dict(b=zb, kind=np.where(zn.kind == "OFF_PRICE", "OFF", "AT"), side=zn.direction.to_numpy().astype(int),
                             lower=zn.lower_tick.to_numpy().astype(np.int64), upper=zn.upper_tick.to_numpy().astype(np.int64),
                             anomaly=zn.anomaly_ratio.to_numpy(), is_ev=True))
    real["olo"] = real.lower - cl[real.b]; real["ohi"] = real.upper - cl[real.b]
    real["clock"] = mins[real.b] // 30
    # pseudo-zonas: bloques sin zona lejos de creaciones, geometría de una zona real del mismo tipo y franja
    bb = blk.bar.to_numpy().astype(np.int64)
    bb = bb[(bb >= 60) & (bb + KT + 210 < n)]
    bb = bb[appr[bb]]
    j = np.searchsorted(zb, bb)
    dist = np.minimum(np.abs(bb - zb[np.clip(j, 0, len(zb) - 1)]), np.abs(bb - zb[np.clip(j - 1, 0, len(zb) - 1)]))
    bb = bb[dist > 20]
    pool = pd.DataFrame(dict(b=bb, clock=mins[bb] // 30))
    ps = []
    for (kind, clk), g in real.groupby(["kind", "clock"]):
        cand = pool[pool.clock == clk]
        if len(cand) == 0:
            continue
        m = min(len(cand), NPSEUDO * len(g))
        pick = cand.sample(m, random_state=int(rng.integers(1 << 31)))
        geo = g.sample(m, replace=True, random_state=int(rng.integers(1 << 31)))
        ps.append(pd.DataFrame(dict(b=pick.b.to_numpy(), kind=kind, side=geo.side.to_numpy(),
                                    lower=cl[pick.b.to_numpy()] + geo.olo.to_numpy(), upper=cl[pick.b.to_numpy()] + geo.ohi.to_numpy(),
                                    anomaly=np.nan, is_ev=False, olo=geo.olo.to_numpy(), ohi=geo.ohi.to_numpy(), clock=clk)))
    allz = pd.concat([real] + ps, ignore_index=True)
    out = []
    for k in KS:
        e, dirn, cons = first_exit(hi, lo, cl, send, allz.b.to_numpy(), allz.lower.to_numpy(), allz.upper.to_numpy(), k)
        d = allz.copy()
        d["k"] = k; d["e"] = e; d["dir"] = dirn; d["cons"] = cons; d["lag"] = np.where(e >= 0, e - d.b, -1)
        d = d[d.e >= 0].copy()
        ee = d.e.to_numpy()
        ok = ee + 210 < n
        d, ee = d[ok].copy(), ee[ok]
        d["rth"] = (mins[ee] >= 510) & (mins[ee] < 900)
        d["session"] = sdate[ee]; d["contract"] = c; d["eclock"] = mins[ee] // 30
        d["voldec"] = dec(vol[ee]); d["int10"] = dec((en[ee] - st[ee - 9]) / 1e9)
        d["absr10"] = dec(np.abs(cl[ee] - cl[ee - 10]) + rng.random(len(ee)) * 1e-6)
        # ruptura (OFF): sale por el lado opuesto al origen. side +1 = precio arriba de la zona -> salir por abajo = ruptura
        d["ruptura"] = (d.kind == "OFF") & (d.dir == -d.side)
        for H in (10, 50, 200):
            same = send[ee + H] == send[ee]
            d["c_%d" % H] = np.where(same, d.dir * (cl[ee + H] - cl[ee]), np.nan)
            Rp = pd.Series(hi).rolling(H).max().to_numpy()[ee - 1] - pd.Series(lo).rolling(H).min().to_numpy()[ee - 1]
            Rf = pd.Series(hi).rolling(H).max().to_numpy()[ee + H] - pd.Series(lo).rolling(H).min().to_numpy()[ee + H]
            d["R_%d" % H] = Rp
            d["yrg_%d" % H] = np.where(same, np.log((Rf + 1) / (Rp + 1)), np.nan)
        out.append(d)
    return pd.concat(out, ignore_index=True)


def fe_beta(d, y):
    m = np.isfinite(y)
    d, y = d[m], y[m]
    s0 = (d.contract + "|" + d.eclock.astype(str) + "|" + d.voldec.astype(str)).to_numpy()
    groups = [s0, d.int10.to_numpy(), d.absr10.to_numpy()]
    Z = absorb(np.column_stack([d.is_ev.to_numpy().astype(float), y]), groups)
    e, Y = Z[:, 0], Z[:, 1]
    ee = e @ e
    bt = (e @ Y) / ee
    U = Y - e * bt
    sid = pd.factorize(d.session.to_numpy())[0]
    G = sid.max() + 1
    S = np.bincount(sid, weights=e * U, minlength=G)
    se = np.sqrt((S ** 2).sum() * G / (G - 1)) / ee
    return float(bt), float(se), int(d.is_ev.sum()), int((~d.is_ev).sum())


def rec(name, b, se, ne, nc, **kw):
    p = float(2 * (1 - norm.cdf(abs(b / se)))) if se > 0 else 1.0
    return dict(nombre=name, beta=b, se=se, ci95=[b - 1.96 * se, b + 1.96 * se], p=p, mde=2.8 * se, n_real=ne, n_pseudo=nc, **kw)


def analyze(D, label_mask, tag):
    out = []
    for k in KS:
        d = D[(D.k == k) & label_mask]
        for H in (10, 50):
            b, se, ne, nc = fe_beta(d, d["c_%d" % H].to_numpy(float))
            out.append(rec("continuacion media c_%d (ticks)" % H, b, se, ne, nc, k=k, grupo=tag))
        b, se, ne, nc = fe_beta(d, d["yrg_10"].to_numpy(float))
        out.append(rec("y_rg_10 en la salida", b, se, ne, nc, k=k, grupo=tag))
        for H in (10, 50):
            R = d["R_%d" % H].to_numpy(float)
            cc = d["c_%d" % H].to_numpy(float)
            ok = np.isfinite(cc) & (R > 0)
            for nm, y in (("cola continuacion", (cc >= R).astype(float)), ("cola falla", (cc <= -R).astype(float))):
                y = np.where(ok, y, np.nan)
                b, se, ne, nc = fe_beta(d, y)
                out.append(rec("%s H%d" % (nm, H), b, se, ne, nc, k=k, grupo=tag,
                               tasa_pseudo=float(np.nanmean(y[~d.is_ev.to_numpy()]))))
        b, se, ne, nc = fe_beta(d, d["c_200"].to_numpy(float))
        out.append(rec("continuacion media c_200 (ticks)", b, se, ne, nc, k=k, grupo=tag))
    return out


def main():
    t0 = time.time()
    cs = sorted({"_".join(Path(f).name.split("_")[:2]) for f in files("_base_zones.parquet")})
    print("contratos", cs, flush=True)
    rng = np.random.default_rng(20261006)
    D = pd.concat([build_exit(c, rng) for c in cs], ignore_index=True)
    print("salidas", len(D), "%.0f s" % (time.time() - t0), flush=True)
    R = D[D.rth]
    formal, desc = [], []
    for r in analyze(R, np.ones(len(R), bool), "todas"):
        if r["nombre"] in ("continuacion media c_10 (ticks)", "continuacion media c_50 (ticks)", "y_rg_10 en la salida"):
            formal.append(r)
        else:
            desc.append(r)
    for tag, m in (("AT", R.kind == "AT"), ("OFF", R.kind == "OFF"),
                   ("OFF ruptura", (R.kind == "OFF") & R.ruptura), ("OFF rechazo", (R.kind == "OFF") & ~R.ruptura),
                   ("salida inmediata lag<=10", R.lag <= 10), ("salida tras consolidar cons>=5", R.cons >= 5)):
        desc += analyze(R, m.to_numpy(), tag)
    q = R[R.is_ev].anomaly.quantile(0.8)
    desc += analyze(R, ((~R.is_ev) | (R.anomaly >= q)).to_numpy(), "Q5 anomalia")
    E = D[D.is_ev]
    P = D[~D.is_ev]
    for k in KS:
        desc.append(dict(nombre="perfil salidas", k=k, n_real=int((E.k == k).sum()), n_pseudo=int((P.k == k).sum()),
                         lag_mediana_real=float(E[E.k == k].lag.median()), lag_mediana_pseudo=float(P[P.k == k].lag.median()),
                         frac_ruptura_OFF_real=float(E[(E.k == k) & (E.kind == "OFF")].ruptura.mean()),
                         frac_ruptura_OFF_pseudo=float(P[(P.k == k) & (P.kind == "OFF")].ruptura.mean()),
                         cons_mediana_real=float(E[E.k == k].cons.median())))
    desc += [dict(r, sesion="ETH") for r in analyze(D[~D.rth], np.ones(int((~D.rth).sum()), bool), "todas")]
    ps = [r["p"] for r in formal]
    order = np.argsort(ps)
    mx = 0.0
    for rank, i in enumerate(order):
        mx = max(mx, min(1.0, (len(ps) - rank) * ps[i]))
        formal[i]["p_holm"] = mx
    for r in formal + desc:
        print({kk: (round(v, 4) if isinstance(v, float) else v) for kk, v in r.items() if kk not in ("ci95", "se")}, flush=True)
    res = dict(campaign="AVCL-EXIT", manifest="docs/research/AVCL_EXIT_MANIFIESTO_20261006.md", contracts=cs,
               formal=formal, descriptivo=desc, seconds=round(time.time() - t0))
    (OUT / "AVCL_EXIT_RESULTADOS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("listo en %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
