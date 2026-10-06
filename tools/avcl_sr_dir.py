#!/usr/bin/env python3
r"""AVCL-SR-DIR (manifiesto docs/research/AVCL_SR_DIR_MANIFIESTO_20261006.md). Lee el cache de AVCL-VOL-2.
D1: dirección del desplazamiento tras la creación (β con FE, SE por sesión, bilateral).
D2: primer toque, respeta/rompe, zona real vs espejo (bootstrap de sesiones, bilateral). Holm 5."""
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
H1 = (10, 50, 200)
XS = (8, 16, 32)
KT, KR = 500, 200
NBOOT, SEED = 2000, 20261006


def files(suffix):
    out = []
    for r in IN:
        out += glob.glob(str(r / "**" / ("*" + suffix)), recursive=True)
    return sorted(set(out))


def dec(x, q=10):
    return pd.qcut(pd.Series(x).rank(method="first"), q, labels=False).to_numpy()


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


def beta(df, y, groups):
    Z = absorb(np.column_stack([df.is_ev.to_numpy().astype(float), y]), groups)
    e, Y = Z[:, 0], Z[:, 1]
    ee = e @ e; bt = (e @ Y) / ee; U = Y - e * bt
    sid = pd.factorize(df.session.to_numpy())[0]; G = sid.max() + 1
    S = np.bincount(sid, weights=e * U, minlength=G)
    se = np.sqrt((S ** 2).sum() * G / (G - 1)) / ee
    return float(bt), float(se)


def first_true(mask2d):
    """índice de la primera columna True por fila; -1 si no hay."""
    any_ = mask2d.any(1)
    return np.where(any_, mask2d.argmax(1), -1)


def race(hi, lo, send, t, near, far, sgn, X):
    """Desde la barra de toque t: respeta si el precio vuelve X más allá del borde cercano hacia el origen;
    rompe si pasa X más allá del borde lejano. sgn=+1: zona debajo del precio (soporte: origen arriba)."""
    idx = t[:, None] + np.arange(0, KR + 1)[None, :]
    idx = np.minimum(idx, len(hi) - 1)
    same = send[idx] == send[t][:, None]
    H, L = hi[idx], lo[idx]
    if True:
        resp = np.where(sgn[:, None] > 0, H >= near[:, None] + X, L <= near[:, None] - X) & same
        brk = np.where(sgn[:, None] > 0, L <= far[:, None] - X, H >= far[:, None] + X) & same
    resp[:, 0] = False                                         # el respeto se cuenta desde la barra siguiente
    fr, fb = first_true(resp), first_true(brk)
    out = np.full(len(t), np.nan)
    out[(fr >= 0) & ((fb < 0) | (fr < fb))] = 1.0
    out[(fb >= 0) & ((fr < 0) | (fb < fr))] = 0.0
    return out                                                 # NaN = empate o sin resolver


def touch(hi, lo, send, b, edge, sgn):
    """Primera barra en (b, b+KT] de la misma sesión cuyo rango alcanza 'edge' (sgn>0: desde arriba)."""
    idx = np.minimum(b[:, None] + np.arange(1, KT + 1)[None, :], len(hi) - 1)
    same = send[idx] == send[b][:, None]
    m = np.where(sgn[:, None] > 0, lo[idx] <= edge[:, None], hi[idx] >= edge[:, None]) & same
    f = first_true(m)
    return np.where(f >= 0, b + 1 + f, -1)


def build(c):
    z = np.load(next(f for f in files("_bars.npz") if Path(f).name == c + "_bars.npz"))
    blk = pd.read_parquet(next(f for f in files("_blocks.parquet") if Path(f).name == c + "_blocks.parquet"))
    zn = pd.read_parquet(next(f for f in files("_zones.parquet") if Path(f).name == c + "_zones.parquet"))
    hi = z["high_t"].astype(np.int64); lo = z["low_t"].astype(np.int64); cl = z["close_t"].astype(np.int64)
    n = len(hi); send = z["send"]; sdate = z["sdate"]; appr = z["approved"]; mins = z["mins"].astype(int)
    st, en = z["start_ns"], z["end_ns"]
    rth_all = (mins >= 510) & (mins < 900)
    # ---- D1
    kind = dict(zip(zn.created_bar.astype(int), np.where(zn.kind == "OFF_PRICE", "OFF", "AT")))
    side = dict(zip(zn.created_bar.astype(int), zn.direction.astype(int)))
    cbar = np.array(sorted(kind), dtype=np.int64)
    b = blk.bar.to_numpy().astype(np.int64)
    b = b[(b >= 60) & (b + max(H1) + 1 < n)]; b = b[appr[b]]
    bv = blk.set_index("bar").vol.reindex(b).to_numpy()
    d = pd.DataFrame(dict(bar=b, vol=bv)); d["kind"] = d.bar.map(kind).fillna("CTRL")
    d["side"] = d.bar.map(side).fillna(0).astype(int)
    r10 = cl[b] - cl[b - 10]
    d["pseudo"] = np.sign(r10).astype(int)
    d["contract"] = c; d["session"] = sdate[b]; d["clock"] = mins[b] // 30; d["rth"] = rth_all[b]
    d["voldec"] = dec(bv); d["vol20"] = dec(bv, 20); d["int10"] = dec((en[b] - st[b - 9]) / 1e9)
    d["absr10"] = dec(np.abs(r10) + np.random.default_rng(0).random(len(b)) * 1e-6)
    j = np.searchsorted(cbar, b)
    d["dist"] = np.minimum(np.abs(b - cbar[np.clip(j, 0, len(cbar) - 1)]), np.abs(b - cbar[np.clip(j - 1, 0, len(cbar) - 1)]))
    for H in H1:
        d["fwd_%d" % H] = (cl[b + H] - cl[b]).astype(float)
        d["ok_%d" % H] = send[b] == send[b + H]
    # ---- D2
    o = zn[(zn.kind == "OFF_PRICE") & zn.direction.isin([1, -1])].copy()
    o = o[(o.created_bar >= 1) & (o.created_bar + 2 < n)]
    zb = o.created_bar.to_numpy().astype(np.int64); o = o[appr[zb]]; zb = o.created_bar.to_numpy().astype(np.int64)
    sg = o.direction.to_numpy().astype(int); lw = o.lower_tick.to_numpy().astype(np.int64); up = o.upper_tick.to_numpy().astype(np.int64)
    c0 = cl[zb]; w = up - lw
    near_r = np.where(sg > 0, up, lw); far_r = np.where(sg > 0, lw, up)
    dist = np.abs(c0 - near_r)
    near_m = np.where(sg > 0, c0 + dist, c0 - dist); far_m = np.where(sg > 0, near_m + w, near_m - w)
    rows = []
    for nm, near, far, s in (("real", near_r, far_r, sg), ("espejo", near_m, far_m, -sg)):
        t = touch(hi, lo, send, zb, near, s)
        ok = t >= 0
        rec = pd.DataFrame(dict(zone=np.arange(len(zb)), tipo=nm, side=sg, session=sdate[zb], rth=rth_all[zb],
                                touched=ok, lag=np.where(ok, t - zb, -1), dist=dist, width=w))
        for X in XS:
            res = np.full(len(zb), np.nan)
            if ok.any():
                res[ok] = race(hi, lo, send, t[ok], near[ok], far[ok], s[ok], X)
            rec["resp_%d" % X] = res
        rec["contract"] = c
        rows.append(rec)
    return d, pd.concat(rows, ignore_index=True)


def boot_diff(r, col, rng):
    """Δ = P(respeta|real) − P(respeta|espejo) con bootstrap de sesiones."""
    g = r.dropna(subset=[col]).groupby(["session", "tipo"])[col].agg(["sum", "count"]).unstack(fill_value=0)
    S = g.index.size
    sr, nr = g[("sum", "real")].to_numpy(), g[("count", "real")].to_numpy()
    se_, ne = g[("sum", "espejo")].to_numpy(), g[("count", "espejo")].to_numpy()
    obs = sr.sum() / nr.sum() - se_.sum() / ne.sum()
    W = rng.multinomial(S, np.ones(S) / S, size=NBOOT)
    bs = (W @ sr) / (W @ nr) - (W @ se_) / (W @ ne)
    return float(obs), float(bs.std()), [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], \
        float(sr.sum() / nr.sum()), float(se_.sum() / ne.sum()), int(nr.sum()), int(ne.sum())


def main():
    t0 = time.time()
    cs = sorted({Path(f).name[:-9] for f in files("_bars.npz")})
    parts, races = [], []
    for c in cs:
        d, r = build(c); parts.append(d); races.append(r)
        print(c, len(d), "bloques", len(r) // 2, "zonas OFF", "%.0f s" % (time.time() - t0), flush=True)
    D = pd.concat(parts, ignore_index=True); R = pd.concat(races, ignore_index=True)
    rng = np.random.default_rng(SEED)
    formal, desc = [], []
    # D1
    for H in H1:
        for sname, smask in (("RTH", D.rth), ("ETH", ~D.rth)):
            for lado, evm in (("ambos", D.kind == "OFF"), ("soporte", (D.kind == "OFF") & (D.side == 1)),
                              ("resistencia", (D.kind == "OFF") & (D.side == -1))):
                m = smask & D["ok_%d" % H] & (evm | ((D.kind == "CTRL") & (D.dist > 2 * H) & (D.pseudo != 0)))
                d = D[m].copy(); d["is_ev"] = evm[m].to_numpy()
                sgn = np.where(d.is_ev, d.side, d.pseudo)
                y = sgn * d["fwd_%d" % H].to_numpy()
                s0 = (d.contract + "|" + d.clock.astype(str) + "|" + d.voldec.astype(str)).to_numpy()
                bt, se = beta(d, y, [s0, d.int10.to_numpy(), d.vol20.to_numpy(), d.absr10.to_numpy()])
                ev = d[d.is_ev]; raw = float((sgn[d.is_ev.to_numpy()] * ev["fwd_%d" % H]).mean())
                r = dict(prueba="D1", H=H, sesion=sname, lado=lado, n_events=int(d.is_ev.sum()), beta_ticks=bt, se=se,
                         ci95=[bt - 1.96 * se, bt + 1.96 * se], p=float(2 * (1 - norm.cdf(abs(bt / se)))),
                         mde=2.8 * se, crudo_evento_ticks=raw)
                (formal if (sname == "RTH" and lado == "ambos" and H in (10, 50)) else desc).append(r)
                print("D1", H, sname, lado, round(bt, 3), "±", round(1.96 * se, 3), "crudo", round(raw, 3), flush=True)
    # AT crudo (descriptivo)
    for H in H1:
        a = D[(D.kind == "AT") & D.rth & D["ok_%d" % H]]
        desc.append(dict(prueba="AT_crudo", H=H, n=len(a), media_fwd_ticks=float(a["fwd_%d" % H].mean()),
                         media_abs_fwd_ticks=float(a["fwd_%d" % H].abs().mean())))
    # D2
    for sname, smask in (("RTH", R.rth), ("ETH", ~R.rth)):
        for lado, lm in (("ambos", R.side != 0), ("soporte", R.side == 1), ("resistencia", R.side == -1)):
            sub = R[smask & lm]
            for X in XS:
                obs, se, ci, pr, pm, nr, nm = boot_diff(sub, "resp_%d" % X, rng)
                r = dict(prueba="D2", X=X, sesion=sname, lado=lado, delta=obs, se=se, ci95=ci,
                         p=float(2 * (1 - norm.cdf(abs(obs / se)))), mde=2.8 * se, p_respeta_real=pr, p_respeta_espejo=pm,
                         n_real=nr, n_espejo=nm)
                (formal if (sname == "RTH" and lado == "ambos") else desc).append(r)
                print("D2", sname, lado, X, "real %.3f espejo %.3f D %.3f +-%.3f" % (pr, pm, obs, 1.96 * se), nr, nm, flush=True)
    for tipo in ("real", "espejo"):
        s = R[(R.tipo == tipo) & R.rth]
        desc.append(dict(prueba="D2_toque", tipo=tipo, n=len(s), tasa_toque=float(s.touched.mean()),
                         demora_mediana=float(s[s.touched].lag.median()),
                         sin_resolver_16=float(s[s.touched]["resp_16"].isna().mean())))
    ps = [r["p"] for r in formal]; order = np.argsort(ps); mx = 0.0
    for rank, i in enumerate(order):
        mx = max(mx, min(1.0, (len(ps) - rank) * ps[i])); formal[i]["p_holm"] = mx
    res = dict(campaign="AVCL-SR-DIR", manifest="docs/research/AVCL_SR_DIR_MANIFIESTO_20261006.md", contracts=cs,
               formal=formal, descriptivo=desc, seconds=round(time.time() - t0))
    (OUT / "AVCL_SR_DIR_RESULTADOS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    for r in formal:
        print("FORMAL", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k != "ci95"})
    print("listo en %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
