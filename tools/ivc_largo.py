#!/usr/bin/env python3
r"""IVC-L: información de horizonte largo con historia de años sobre proxies ETF (manifiesto
docs/research/MANIFIESTO_IVC_LARGO_20260926.md). 8 celdas fijas, nulo por desplazamiento circular, bootstrap por
bloques de un mes, descubrimiento/validación con el signo fijado en descubrimiento.

    python tools/ivc_largo.py --daily <dir con SPY_d.json QQQ_d.json DIA_d.json> --min1 <spy_1min.csv> --out <dir>
    python tools/ivc_largo.py --selftest        # prueba nula sobre un random walk
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

COST_BP, COST_BP_ALT = 1.5, 3.0
N_NULL, N_BOOT, MIN_SHIFT, SEED, Q = 2000, 1000, 20, 20260926, 0.10
SPLIT_D, SPLIT_M = "2012-12-31", "2014-12-31"
END = "2026-03-31"


def spearman(x, y):
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])


def bh(p, q):
    p = np.asarray(p, float); m = len(p); o = np.argsort(p)
    ok = p[o] <= q * np.arange(1, m + 1) / m
    k = np.max(np.nonzero(ok)[0]) + 1 if ok.any() else 0
    r = np.zeros(m, bool); r[o[:k]] = True
    return r


def load_daily(path: Path):
    r = json.loads(path.read_text())["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    d = pd.DataFrame(dict(open=q["open"], close=q["close"]),
                     index=pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("America/New_York").normalize()
                     .tz_localize(None))
    d = d.dropna()
    d = d[d.index <= END]
    divs = {pd.Timestamp(v["date"], unit="s", tz="UTC").tz_convert("America/New_York").normalize().tz_localize(None)
            for v in r.get("events", {}).get("dividends", {}).values()}
    d["gap"] = d.open / d.close.shift(1) - 1
    d["oc"] = d.close / d.open - 1
    d = d[~d.index.isin(divs)].dropna()
    return d


def load_min(path: Path):
    m = pd.read_csv(path, parse_dates=["date"])
    n0 = len(m)
    m = m.drop_duplicates()                                  # 638.054 filas copiadas idénticas (724 días); ver reporte
    if m.date.duplicated().any():
        raise ValueError("minutos repetidos con valores distintos: no se deduplica a ciegas")
    load_min.dups = n0 - len(m)
    m["day"] = m.date.dt.normalize()
    m["hm"] = m.date.dt.hour * 60 + m.date.dt.minute          # reloj de montaña: 7:30 = 9:30 ET
    g = m.groupby("day")
    def at_open(h):   # apertura de la barra que empieza en h (MT)
        return m[m.hm == h].set_index("day").open
    def at_close(h):  # cierre de la barra que termina en h (MT) = barra que empieza en h-1
        return m[m.hm == h - 1].set_index("day").close
    D = pd.DataFrame({"o930": at_open(7 * 60 + 30), "p1000": at_close(8 * 60), "p1530": at_close(13 * 60 + 30),
                      "c1600": at_close(14 * 60)})
    D["prev_close"] = D.c1600.shift(1)
    D = D.dropna()
    D["gap"] = D.o930 / D.prev_close - 1
    D["ap30"] = D.p1000 / D.o930 - 1
    D["mid"] = D.p1530 / D.p1000 - 1
    D["u30"] = D.c1600 / D.p1530 - 1
    D["rest"] = D.c1600 / D.p1000 - 1
    return D


def cell(x, y, dates, split, rng):
    """IC, borde por apuesta en pb (dirección del predictor con el signo de descubrimiento), margen, nulo y bootstrap
    por bloques mensuales, en descubrimiento y validación."""
    disc = dates <= pd.Timestamp(split)
    out = {}
    sgn = None
    for part, msk in (("disc", disc), ("val", ~disc)):
        xx, yy, dd = x[msk], y[msk], dates[msk]
        if len(xx) < 100:
            return None
        ic = spearman(xx, yy)
        if part == "disc":
            sgn = 1.0 if ic >= 0 else -1.0
        pnl = sgn * np.sign(xx) * yy * 1e4                          # pb por día, todos los días
        q1, q4 = np.quantile(xx, [0.2, 0.8]); ext = (xx <= q1) | (xx >= q4)
        pnl_ext = pnl[ext]
        months = pd.PeriodIndex(dd, freq="M"); um, mi = np.unique(months.astype(str), return_inverse=True)
        s = np.bincount(mi, weights=pnl, minlength=len(um)); n = np.bincount(mi, minlength=len(um)).astype(float)
        se_ = np.bincount(mi[ext], weights=pnl_ext, minlength=len(um)); ne = np.bincount(mi[ext], minlength=len(um)).astype(float)
        W = np.stack([np.bincount(rng.integers(0, len(um), len(um)), minlength=len(um)) for _ in range(N_BOOT)]).astype(float)
        bt = (W @ s) / np.maximum(W @ n, 1); bte = (W @ se_) / np.maximum(W @ ne, 1)
        nul = np.array([spearman(np.roll(xx, int(rng.integers(MIN_SHIFT, len(xx) - MIN_SHIFT))), yy) for _ in range(N_NULL)])
        edge = float(pnl.mean()); edge_ext = float(pnl_ext.mean())
        out[part] = dict(n=int(len(xx)), ic=ic, p_null=float((np.abs(nul) >= abs(ic)).mean()),
                         mde_ic=float(1.96 * nul.std()), edge_bp=edge, edge_ext_bp=edge_ext,
                         margin=edge - COST_BP, margin_lo=float(np.quantile(bt, .025)) - COST_BP,
                         margin_ext=edge_ext - COST_BP, margin_ext_lo=float(np.quantile(bte, .025)) - COST_BP,
                         margin_alt=edge - COST_BP_ALT,
                         ic_nd=spearman(np.abs(xx), np.abs(yy)))
    return out


def run(cells, out: Path):
    rng = np.random.default_rng(SEED)
    rows = []
    for name, x, y, dates, split in cells:
        r = cell(np.asarray(x, float), np.asarray(y, float), pd.DatetimeIndex(dates), split, rng)
        if r is None:
            continue
        row = {"celda": name}
        for part in ("disc", "val"):
            for k, v in r[part].items():
                row[f"{k}_{part}"] = v
        # por década (descriptivo)
        dec = pd.DatetimeIndex(dates).year // 10 * 10
        row["ic_por_decada"] = {int(d): round(spearman(np.asarray(x)[dec == d], np.asarray(y)[dec == d]), 4)
                                for d in np.unique(dec) if (dec == d).sum() >= 100}
        rows.append(row)
    R = pd.DataFrame(rows)
    R["fdr"] = bh(R.p_null_disc, Q)
    R["prometedora"] = (R.fdr & (R.margin_lo_disc > 0) & (R.margin_val > 0) & (R.margin_lo_val > 0)
                        & (np.sign(R.ic_val) == np.sign(R.ic_disc)))
    R["prometedora_ext"] = (R.fdr & (R.margin_ext_lo_disc > 0) & (R.margin_ext_val > 0) & (R.margin_ext_lo_val > 0)
                            & (np.sign(R.ic_val) == np.sign(R.ic_disc)))
    out.mkdir(parents=True, exist_ok=True)
    R.to_csv(out / "ivcl_celdas.csv", index=False)
    print(R[["celda", "n_disc", "ic_disc", "p_null_disc", "mde_ic_disc", "edge_bp_disc", "margin_lo_disc", "n_val",
             "ic_val", "edge_bp_val", "margin_lo_val", "edge_ext_bp_disc", "edge_ext_bp_val", "fdr", "prometedora",
             "prometedora_ext"]].round(4).to_string())
    return R


def selftest(out):
    rng = np.random.default_rng(7)
    dates = pd.bdate_range("1995-01-01", "2021-05-01")
    cells = []
    for i in range(8):
        x = rng.standard_normal(len(dates)) * 0.005; y = rng.standard_normal(len(dates)) * 0.01
        cells.append((f"rw{i}", x, y, dates, SPLIT_D if i < 3 else SPLIT_M))
    R = run(cells, out)
    print("prueba nula: fdr", int(R.fdr.sum()), "prometedoras", int(R.prometedora.sum()), int(R.prometedora_ext.sum()))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--daily"); ap.add_argument("--min1"); ap.add_argument("--out", required=True)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest(Path(a.out))
    cells = []
    for t in ("SPY", "QQQ", "DIA"):
        d = load_daily(Path(a.daily) / f"{t}_d.json")
        cells.append((f"{t} gap -> apertura-cierre", d.gap, d.oc, d.index, SPLIT_D))
    m = load_min(Path(a.min1))
    for nm, xc, yc in (("SPY1m primera 1/2h -> ultima 1/2h", "ap30", "u30"), ("SPY1m gap -> ultima 1/2h", "gap", "u30"),
                       ("SPY1m primera 1/2h -> 10:00-15:30", "ap30", "mid"), ("SPY1m gap -> primera 1/2h", "gap", "ap30"),
                       ("SPY1m gap -> 10:00-cierre", "gap", "rest")):
        cells.append((nm, m[xc], m[yc], m.index, SPLIT_M))
    R = run(cells, Path(a.out))
    sha = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in list(Path(a.daily).glob("*_d.json")) + [Path(a.min1)]}
    (Path(a.out) / "ivcl_resumen.json").write_text(json.dumps(dict(
        celdas=int(len(R)), fdr=int(R.fdr.sum()), prometedoras=int(R.prometedora.sum()),
        prometedoras_ext=int(R.prometedora_ext.sum()), fuentes_sha256=sha, dias_min1=int(len(m)), filas_1m_duplicadas_identicas=int(load_min.dups)), indent=1))


if __name__ == "__main__":
    main()
