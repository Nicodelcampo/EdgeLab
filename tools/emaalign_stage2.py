#!/usr/bin/env python3
"""EMA-ALIGN análisis (manifiesto docs/research/EMAALIGN_ESTRATEGIA_MANIFIESTO_20261007.md).
Descubrimiento: contratos viejos, 108 celdas (54 x MNQ/MGC), max-T contra dirección al azar (mismos tiempos y fills).
Confirmación: 2 contratos más recientes por instrumento, sólo celdas que pasan, Holm."""
import glob
import json
import sys
from pathlib import Path

import numpy as np

IN = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else IN
CONF = {"MNQ": ("MNQ_09-26", "MNQ_12-26"), "MGC": ("MGC_08-26", "MGC_12-26")}
COMM = {"MNQ": 1.90, "MGC": 1.90}
TICK = {"MNQ": 0.50, "MGC": 1.00}
NDRAW, SEED = 2000, 20261007
MODES = "ABC"


def load(inst, conf):
    P, S = [], []
    for f in sorted(glob.glob(str(IN / "**" / ("%s_*_emaalign.npz" % inst)), recursive=True)):
        c = Path(f).name.replace("_emaalign.npz", "")
        if (c in CONF[inst]) != conf:
            continue
        z = np.load(f)
        P.append(z["pnl"].astype(np.float64) * TICK[inst] - COMM[inst])   # neto USD; NaN = sin fill
        S.append(z["session"].astype(np.int64))
        cells = z["cells"]
    return np.concatenate(P), np.concatenate(S), cells


def stats(P, S, rng, ndraw=NDRAW):
    """Media neta real por celda, null por dirección al azar (mismo sorteo para todas las celdas)."""
    p0, p1 = P[:, :, 0], P[:, :, 1]
    ok = np.isfinite(p0)
    n = ok.sum(0)
    a = np.where(ok, p0, 0.0)
    dlt = np.where(ok, p1 - p0, 0.0)
    real = a.sum(0) / np.maximum(n, 1)
    nulls = np.empty((ndraw, P.shape[1]))
    for i in range(0, ndraw, 100):
        F = (rng.random((min(100, ndraw - i), len(P))) < 0.5).astype(np.float64)
        nulls[i:i + len(F)] = (a.sum(0) + F @ dlt) / np.maximum(n, 1)
    mu, sd = nulls.mean(0), nulls.std(0, ddof=1)
    z = (real - mu) / np.where(sd > 0, sd, np.nan)
    zn = (nulls - mu) / np.where(sd > 0, sd, np.nan)
    # IC por bootstrap de sesiones de la media real
    us, inv = np.unique(S, return_inverse=True)
    sums = np.zeros((len(us), P.shape[1])); cnt = np.zeros((len(us), P.shape[1]))
    np.add.at(sums, inv, a); np.add.at(cnt, inv, ok)
    bs = []
    for _ in range(1000):
        k = rng.integers(0, len(us), len(us))
        bs.append(sums[k].sum(0) / np.maximum(cnt[k].sum(0), 1))
    lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
    win = np.where(ok, p0 > 0, False).sum(0) / np.maximum(n, 1)
    return dict(real=real, null_mu=mu, z=z, zn=zn, n=n, lo=lo, hi=hi, win=win, n_sess=len(us))


def name(c):
    return "%s SL%d R%g BE%s" % (MODES[int(c[0])], c[1], c[2], "si" if c[3] else "no")


def main():
    rng = np.random.default_rng(SEED)
    out = {"descubrimiento": {}, "confirmacion": {}}
    D = {}
    for inst in ("MNQ", "MGC"):
        P, S, cells = load(inst, False)
        D[inst] = stats(P, S, rng)
        D[inst]["cells"] = cells
    maxnull = np.nanmax(np.concatenate([D[i]["zn"] for i in D], axis=1), axis=1)
    pasan = []
    for inst, d in D.items():
        for j, c in enumerate(d["cells"]):
            p_adj = float((maxnull >= d["z"][j]).mean())
            r = dict(neto_usd=float(d["real"][j]), ic95=[float(d["lo"][j]), float(d["hi"][j])],
                     null_azar_usd=float(d["null_mu"][j]), z=float(d["z"][j]), p_maxT=p_adj, n=int(d["n"][j]),
                     win=float(d["win"][j]))
            out["descubrimiento"]["%s %s" % (inst, name(c))] = r
            if p_adj <= 0.05 and r["neto_usd"] > 0:
                pasan.append((inst, j))
    out["n_sesiones_desc"] = {i: D[i]["n_sess"] for i in D}
    if pasan:
        res = []
        for inst in {i for i, _ in pasan}:
            P, S, cells = load(inst, True)
            d = stats(P, S, rng)
            for i2, j in pasan:
                if i2 != inst:
                    continue
                p1 = float((d["zn"][:, j] >= d["z"][j]).mean())
                res.append(("%s %s" % (inst, name(cells[j])), dict(neto_usd=float(d["real"][j]), ic95=[float(d["lo"][j]), float(d["hi"][j])],
                            null_azar_usd=float(d["null_mu"][j]), z=float(d["z"][j]), p=p1, n=int(d["n"][j]))))
        res.sort(key=lambda x: x[1]["p"]); mx = 0.0
        for r, (k, v) in enumerate(res):
            mx = max(mx, min(1.0, (len(res) - r) * v["p"])); v["p_holm"] = mx
            v["confirma"] = bool(mx <= 0.05 and v["neto_usd"] > 0)
            out["confirmacion"][k] = v
    (OUT / "EMAALIGN_RESULTADOS.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    top = sorted(out["descubrimiento"].items(), key=lambda kv: -kv[1]["neto_usd"])
    print("pasan descubrimiento:", len(pasan))
    for k, v in top[:10] + top[-3:]:
        print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()})
    for k, v in out["confirmacion"].items():
        print("CONF", k, v)


if __name__ == "__main__":
    main()
