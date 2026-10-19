#!/usr/bin/env python3
"""VTD-BRACKET análisis (manifiesto docs/research/VTD_BRACKET_MANIFIESTO_20261006.md).
Por instrumento × celda (k, R): expectativa neta USD por trade de las marcas; contraste = marcas − pool reponderado por
estrato (franja 30 min × tercil de amplitud). Nulo: 2.000 conjuntos de pseudo-marcas extraídos del pool con la misma
composición por estrato; z = (obs − media nula)/sd nula; max-T sobre las 8 celdas de descubrimiento (MNQ, ES).
Confirmación: las celdas que pasan, una vez, en YM, RTY, MGC (Holm)."""
import glob
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

IN = [Path(p) for p in sys.argv[1:]] or [Path("/kaggle/input")]
OUT = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path(os.environ.get("AVCL_OUT", "."))
DISC, CONF = ("MNQ", "ES"), ("YM", "RTY", "MGC")
NPERM, SEED = 2000, 20261008


def files(suffix):
    out = []
    for r in IN:
        out += glob.glob(str(r / "**" / ("*" + suffix)), recursive=True)
    return sorted(set(out))


def load():
    t = pd.concat([pd.read_parquet(f) for f in files("_bracket.parquet")], ignore_index=True)
    t["inst"] = t.contract.str.split("_").str[0]
    t = t[t.entered == 1].copy()
    t["ampT"] = pd.qcut(t.amp_rel.rank(method="first"), 3, labels=False) if t.amp_rel.notna().any() else 0
    t["ampT"] = t["ampT"].fillna(-1)
    t["stratum"] = t.clock.astype(str) + "|" + t.ampT.astype(str)
    return t


def cell_stats(g, rng):
    m, p = g[g.kind == "mark"], g[g.kind == "pool"]
    obs = float(m.net_usd.mean())
    # pool reponderado a la composición por estrato de las marcas
    comp = m.stratum.value_counts()
    pools = {s: p[p.stratum == s].net_usd.to_numpy() for s in comp.index}
    comp = comp[[len(pools[s]) > 0 for s in comp.index]]
    base = float(sum(comp[s] * pools[s].mean() for s in comp.index) / comp.sum())
    nul = np.empty(NPERM)
    for i in range(NPERM):
        tot, cnt = 0.0, 0
        for s, k in comp.items():
            x = pools[s][rng.integers(0, len(pools[s]), k)]
            tot += x.sum(); cnt += k
        nul[i] = tot / cnt
    sd = float(nul.std())
    # IC de la expectativa de las marcas por bootstrap de sesiones
    ss = m.groupby(m.contract + "|" + m.session.astype(str)).net_usd.agg(["sum", "count"])
    W = rng.multinomial(len(ss), np.ones(len(ss)) / len(ss), size=2000)
    bs = (W @ ss["sum"].to_numpy()) / (W @ ss["count"].to_numpy())
    return dict(n_marcas=len(m), n_pool=len(p), exp_marcas_usd=obs, exp_pool_usd=base, dif_usd=obs - base,
                z=(obs - nul.mean()) / sd if sd > 0 else 0.0, nul=nul, sd_nula=sd,
                ic95_marcas=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                win_marcas=float((m.pnl_ticks > 0).mean()), payoff_ticks=float(m.pnl_ticks.mean()))


def main():
    t0 = time.time()
    t = load()
    print("trades", len(t), dict(t.groupby(["inst", "kind"]).size()), flush=True)
    rng = np.random.default_rng(SEED)
    disc = []
    for inst in DISC:
        for (k, R), g in t[t.inst == inst].groupby(["k", "R"]):
            r = cell_stats(g, rng); r.update(inst=inst, k=k, R=R); disc.append(r)
    # max-T sobre z (dos colas: se busca dif > 0, pero el máximo se toma sobre z positivos)
    Z = np.vstack([(r["nul"] - r["nul"].mean()) / r["sd_nula"] for r in disc])
    mx = Z.max(0)
    for r in disc:
        r["p_maxT"] = float((1 + (mx >= r["z"]).sum()) / (1 + NPERM))
        r["pasa"] = bool(r["p_maxT"] <= 0.05 and r["exp_marcas_usd"] > 0)
    passed = [(r["k"], r["R"]) for r in disc if r["pasa"]]
    conf = []
    for (k, R) in sorted(set(passed)):
        for inst in CONF:
            g = t[(t.inst == inst) & (t.k == k) & (t.R == R)]
            if len(g):
                r = cell_stats(g, rng); r.update(inst=inst, k=k, R=R)
                r["p"] = float((1 + (r["nul"] >= r["exp_marcas_usd"]).sum()) / (1 + NPERM)); conf.append(r)
    if conf:
        ps = [r["p"] for r in conf]; order = np.argsort(ps); mxh = 0.0
        for rank, i in enumerate(order):
            mxh = max(mxh, min(1.0, (len(ps) - rank) * ps[i])); conf[i]["p_holm"] = mxh
    # concentración (descriptivo) para las celdas de descubrimiento
    for r in disc:
        g = t[(t.inst == r["inst"]) & (t.k == r["k"]) & (t.R == r["R"]) & (t.kind == "mark")]
        mon = g.groupby(g.session // 100).net_usd.sum()
        day = g.groupby("session").net_usd.sum().sort_values()
        r["neto_total_usd"] = float(g.net_usd.sum())
        r["sin_mejor_mes"] = float(g.net_usd.sum() - mon.max()) if len(mon) else 0.0
        r["sin_5_mejores_dias"] = float(g.net_usd.sum() - day.tail(5).sum()) if len(day) else 0.0
    out = dict(campaign="VTD-BRACKET", manifest="docs/research/VTD_BRACKET_MANIFIESTO_20261006.md",
               descubrimiento=[{k: v for k, v in r.items() if k != "nul"} for r in disc],
               confirmacion=[{k: v for k, v in r.items() if k != "nul"} for r in conf], seconds=round(time.time() - t0))
    for r in out["descubrimiento"] + out["confirmacion"]:
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    (OUT / "VTD_BRACKET_RESULTADOS.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
