"""ORB0100 NQ + franjas OG/VI. Reglas: docs/research/orb0100_20261021/MANIFIESTO_ORB0100_FRANJAS_OGVI_20261021.md"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orb0100_v2 as V  # noqa: E402
import orb0100_replica as RP  # noqa: E402

COMM = 1.24 / 2.0; TICK = 0.25; NB = 10000


def zonas(paths):
    Z = []
    for p in paths:
        if "HOLDOUT" in p: continue
        B = json.load(open(p, encoding="utf-8")); Z += [(z["available_ts"], z["t1"], z["bottom"], z["top"]) for z in B["runs"][0]["zones"]]; del B
    return np.array(Z)


def operaciones(d, Z, tramo):
    rows = []; h, l, c, t = d.high.values, d.low.values, d.close.values, d.time.values
    for s in V.senales(d, 100, 115, 1600):
        if not ((s["c"] > s["vwap"]) if s["dir"] > 0 else (s["c"] < s["vwap"])): continue
        r = V.operar(d, s, 1.5, TICK, COMM)
        if not r: continue
        dirn = s["dir"]; E = s["c"] + dirn * TICK; sl = s["lo"] if dirn > 0 else s["hi"]; risk = dirn * (E - sl); tp = E + dirn * 1.5 * risk
        te = t[s["k"]] + 60; viva = (Z[:, 0] <= te) & (Z[:, 1] > te)
        def solapa(a, b): lo_, hi_ = min(a, b), max(a, b); return int((viva & (Z[:, 2] <= hi_) & (Z[:, 3] >= lo_)).sum())
        cam, res = solapa(E, tp), solapa(sl, E)
        k = s["k"]; w = np.flatnonzero((t >= t[k] - 3600) & (t <= t[k])); vol = float(h[w].max() - l[w].min())
        rows.append(dict(tramo=tramo, fecha=str(s["fecha"]), R=r[1], pts=r[0], camino=cam, respaldo=res, D=(res - cam) / (res + cam + 1), vol_pre=vol))
    return rows


def dif(x, g, rng):
    x = x.copy(); x["t"] = pd.qcut(x.vol_pre, 3, labels=False, duplicates="drop"); x["g"] = g
    def fn(y):
        tot = acc = 0.0
        for _, z in y.groupby("t"):
            a, b = z[z.g == 1], z[z.g == 0]
            if len(a) and len(b): w = len(z); acc += w * (a.R.mean() - b.R.mean()); tot += w
        return acc / tot if tot else np.nan
    days = x.fecha.unique(); ix = {k: np.flatnonzero(x.fecha.values == k) for k in days}
    full = fn(x); bs = np.array([fn(x.iloc[np.concatenate([ix[k] for k in rng.choice(days, len(days))])]) for _ in range(NB)])
    return dict(est=round(float(full), 3), ic95=[round(float(np.nanpercentile(bs, 2.5)), 3), round(float(np.nanpercentile(bs, 97.5)), 3)],
                p_bilateral=float(min(1, 2 * min(np.nanmean(bs <= 0), np.nanmean(bs >= 0)))), se=float(np.nanstd(bs)), n1=int((g == 1).sum()), n0=int((g == 0).sum()),
                R_g1=round(float(x.R[g == 1].mean()), 3), R_g0=round(float(x.R[g == 0].mean()), 3))


def main():
    disc = operaciones(V.cargar("NQ"), zonas(sorted(glob.glob(str(V.BUN / "NQ_*_M1_LUXIMB.json")))), "desc")
    rep = operaciones(RP.cargar_rep(), zonas(RP.FUENTES), "rep")
    df = pd.DataFrame(disc + rep); df.to_csv(Path(sys.argv[1]).with_suffix(".csv"), index=False)
    rng = np.random.default_rng(20261021); res = {}
    for tramo in ("desc", "rep"):
        x = df[df.tramo == tramo].reset_index(drop=True)
        res[tramo] = dict(n=len(x), R_op=round(float(x.R.mean()), 3), camino_p50=float(x.camino.median()), respaldo_p50=float(x.respaldo.median()),
                          H1_camino=dif(x, (x.camino >= 1).astype(int).values, rng), H2_respaldo=dif(x, (x.respaldo >= 1).astype(int).values, rng),
                          H3_desbalance=dif(x[x.D != 0].reset_index(drop=True), (x[x.D != 0].D > 0).astype(int).values, rng))
    ps = {h: res["desc"][h]["p_bilateral"] for h in ("H1_camino", "H2_respaldo", "H3_desbalance")}
    order = sorted(ps, key=ps.get); run = 0.0; holm = {}
    for k, h in enumerate(order): run = max(run, min(1.0, (3 - k) * ps[h])); holm[h] = round(run, 4)
    for h in ps:
        e1, e2 = res["desc"][h]["est"], res["rep"][h]["est"]
        res.setdefault("veredicto", {})[h] = dict(holm_desc=holm[h], signo_desc=np.sign(e1), signo_rep=np.sign(e2), suma_o_resta=bool(holm[h] < 0.05 and np.sign(e1) == np.sign(e2)),
                                                  MDE80_R=round(2.8 * res["desc"][h]["se"], 3))
    json.dump(res, open(sys.argv[1], "w", encoding="utf-8"), indent=1, default=str); print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
