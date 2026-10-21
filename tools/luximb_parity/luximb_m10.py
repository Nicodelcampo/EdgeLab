"""M10 — transporte de H1 (M9-H_m), H2 (M5) y H3 (M8-A1 vida 200) a MYM, GC, 6E, 6B, 6J, MBT (descubrimiento).
Reglas: docs/research/luximb_parity_20261020/MANIFIESTO_M10_MULTIACTIVO_LUXIMB_20261020.md (no cambiar sin enmienda).
Uso: python tools/luximb_parity/luximb_m10.py <out.json>   (lee bundles y desc_m10/ generados por m10_construir.sh)
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import luximb_m9 as M9  # noqa: E402
from luximb_outcomes import REP_START, carrera  # noqa: E402

REPO = HERE.parents[1]; BUN = REPO / "viewer/nt8_bridge/bundles"; DESC = REPO / "docs/research/luximb_parity_20261020/desc_m10"
ACTIVOS = ("MYM", "GC", "6E", "6B", "6J", "MBT"); NB = 5000
M9.NB = NB; M9.COMM = {a: 0.0 for a in ACTIVOS}                       # P&L no es parte de M10 (solo probabilidades)


def boot_dif(d, ycol, gcol, rng):
    """P(y) grupo 1 - grupo 0 ponderado por estratos 'estr'; bootstrap por dia."""
    d = d[d[gcol].isin([0, 1])]
    if d.empty or d[gcol].nunique() < 2: return None

    def fn(x):
        tot = acc = 0.0
        for _, g in x.groupby("estr"):
            g1, g0 = g[g[gcol] == 1], g[g[gcol] == 0]
            if len(g1) and len(g0):
                w = len(g1) + len(g0); acc += w * (g1[ycol].mean() - g0[ycol].mean()); tot += w
        return acc / tot if tot else np.nan
    days = d.dia.unique(); ix = {k: np.flatnonzero(d.dia.values == k) for k in days}
    full = fn(d); bs = np.array([fn(d.iloc[np.concatenate([ix[k] for k in rng.choice(days, len(days))])]) for _ in range(NB)])
    if not np.isfinite(full) or np.isnan(bs).mean() > 0.5: return None
    return dict(est=round(float(full), 4), se=float(np.nanstd(bs)), ic95=[round(float(np.nanpercentile(bs, 2.5)), 4), round(float(np.nanpercentile(bs, 97.5)), 4)],
                n1=int((d[gcol] == 1).sum()), n0=int((d[gcol] == 0).sum()), dias=int(len(days)))


def estr(d, cols_q):
    out = pd.Series("", index=d.index)
    for col, q in cols_q:
        out = out + pd.Series(np.digitize(d[col], np.quantile(d[col], q)).astype(str), index=d.index)
    return out


def h2_eventos(a, ids):
    rows = []
    for id_ in ids:
        B = json.load(open(BUN / f"{id_}.json", encoding="utf-8")); I = json.load(open(DESC / f"impB_{id_}.json", encoding="utf-8"))
        cl = np.array([c["close"] for c in B["bar_series"]["time_1m"]["candles"]]); T = B["bar_series"]["tick_25"]["candles"]
        t25 = np.array([c["time"] for c in T]); h25 = np.array([c["high"] for c in T]); l25 = np.array([c["low"] for c in T]); c25 = np.array([c["close"] for c in T])
        del B, T
        for g, evs in (("T", I["impulsos"]), ("C", I["control"])):
            for ev in evs:
                if ev["tc"] >= REP_START: raise SystemExit("fuera de descubrimiento")
                r = carrera(ev, t25, h25, l25, c25, cl, (1,), tg_frac=0.75)
                a25 = int(np.searchsorted(t25, ev["tc"], "left")); p25 = int(np.searchsorted(t25, ev["tc"] - 3600, "left"))
                if a25 <= p25: continue
                rows.append(dict(dia=str(pd.Timestamp(ev["tc"], unit="s", tz="UTC").tz_convert("America/New_York").date()), g=int(g == "T"),
                                 y=int(r["res"] == "Tg"), R=ev["rango"], vol_pre=float(h25[p25:a25].max() - l25[p25:a25].min())))
    return pd.DataFrame(rows)


def main():
    import luximb_m8_features as F                                     # noqa: F401  (se invoca por subproceso abajo)
    import subprocess
    rng = np.random.default_rng(20261028); res = {a: {} for a in ACTIVOS}; desc = {}
    for a in ACTIVOS:
        ids = sorted(Path(p).stem.replace("impA_", "") for p in glob.glob(str(DESC / f"impA_{a}_*.json")))
        if not ids: continue
        # H3: variables M8 (vida 200)
        fcsv = DESC / f"feat_{a}.csv"
        if not fcsv.exists():
            subprocess.run([sys.executable, "-X", "utf8", str(HERE / "luximb_m8_features.py"), str(fcsv)] +
                           [f"{a}:{BUN / (i + '.json')}:{DESC / ('impA_' + i + '.json')}" for i in ids], check=True)
        f = pd.read_csv(fcsv); f = f[f.vol_pre.notna()].copy()
        lo, hi = np.quantile(f.D_200, [.2, .8])
        f["g"] = np.where(f.D_200 >= max(hi, 1e-9), 1, np.where(f.D_200 <= min(lo, -1e-9), 0, -1))
        f["estr"] = estr(f, [("vol_pre", [.2, .4, .6, .8]), ("R", [1 / 3, 2 / 3])]) + f.cash.map({True: "c", False: "r"})
        res[a]["H3"] = boot_dif(f, "y1_tg", "g", rng)
        # H1: eventos M9 (vuelta 25 % rapida, m restantes)
        ev = []
        for i in ids:
            ev += M9.eventos(a, str(BUN / f"{i}.json"), str(DESC / f"impA_{i}.json"))
        e = pd.DataFrame(ev); e = e[e.vol_pre.notna() & (e.d == 0.25) & e.rapido].copy()
        m33, m67 = np.quantile(e.m_restantes, [1 / 3, 2 / 3])
        if m67 <= m33: m67 = m33 + 1
        e["g"] = np.where(e.m_restantes <= m33, 1, np.where(e.m_restantes >= m67, 0, -1))
        e["estr"] = estr(e, [("vol_pre", [1 / 3, 2 / 3]), ("R", [1 / 3, 2 / 3])])
        res[a]["H1"] = boot_dif(e, "yA", "g", rng)
        # H2: inicio cargado vs control de amplitud
        h = h2_eventos(a, ids); h["estr"] = estr(h, [("vol_pre", [1 / 3, 2 / 3]), ("R", [1 / 3, 2 / 3])])
        res[a]["H2"] = boot_dif(h, "y", "g", rng)
        desc[a] = dict(contratos=ids, n_H3=int((f.g >= 0).sum()), n_H1=int((e.g >= 0).sum()), n_H2_T=int(h.g.sum()), n_H2_C=int((h.g == 0).sum()),
                       P_base_H3=round(float(f.y1_tg.mean()), 4), P_base_H1=round(float(e.yA.mean()), 4), P_base_H2=round(float(h.y.mean()), 4))
        print(a, {k: (v["est"], v["ic95"]) if v else None for k, v in res[a].items()}, flush=True)
    comb = {}; signo_nq = {"H1": 1, "H2": 1, "H3": 1}
    for hk in ("H1", "H2", "H3"):
        xs = [(a, res[a][hk]) for a in ACTIVOS if res[a].get(hk) and res[a][hk]["se"] > 0]
        w = np.array([1 / r["se"] ** 2 for _, r in xs]); e_ = np.array([r["est"] for _, r in xs])
        est = float((w * e_).sum() / w.sum()); se = float(np.sqrt(1 / w.sum())); z = est / se
        comb[hk] = dict(est=round(est, 4), se=round(se, 4), ic95=[round(est - 1.96 * se, 4), round(est + 1.96 * se, 4)], p=float(2 * norm.sf(abs(z))),
                        activos=len(xs), mismo_signo_que_NQ=int(sum(np.sign(r["est"]) == signo_nq[hk] for _, r in xs)),
                        heterogeneidad_Q=round(float((w * (e_ - est) ** 2).sum()), 2))
    order = sorted(comb, key=lambda k: comb[k]["p"]); run = 0.0
    for k, n in enumerate(order):
        run = max(run, min(1.0, (len(order) - k) * comb[n]["p"])); comb[n]["holm"] = round(run, 4)
        comb[n]["transporta"] = bool(comb[n]["holm"] < 0.05 and comb[n]["mismo_signo_que_NQ"] >= 4)
    out = dict(manifiesto="MANIFIESTO_M10_MULTIACTIVO_LUXIMB_20261020.md", por_activo=res, descriptivo=desc, combinado=comb,
               MDE80_pp={a: {h: round(280 * v["se"], 1) for h, v in res[a].items() if v} for a in ACTIVOS})
    json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps(comb, indent=1))


if __name__ == "__main__":
    main()
