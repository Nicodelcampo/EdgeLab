"""ORB0100 V2: variantes alrededor de 1,5R/rango/mercado/VWAP en 8 activos (descubrimiento).
Reglas: docs/research/orb0100_20261021/MANIFIESTO_ORB0100_V2_MULTIACTIVO_20261021.md (no cambiar sin enmienda).
Uso: python tools/orb0100/orb0100_v2.py <out.json>"""
import glob
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

REPO = Path(__file__).resolve().parents[2]; BUN = REPO / "viewer/nt8_bridge/bundles"
FIN_DESC = pd.Timestamp("2026-03-31 17:00", tz="America/Chicago").tz_convert("America/New_York")
# tick, USD por punto, comision RT USD
ACT = {"NQ": (0.25, 2.0, 1.24), "ES": (0.25, 50.0, 4.5), "MYM": (1.0, 0.5, 1.24), "GC": (0.1, 100.0, 4.5), "6E": (0.00005, 125000.0, 4.5),
       "6B": (0.0001, 62500.0, 4.5), "6J": (0.0000005, 12500000.0, 4.5), "MBT": (5.0, 0.1, 1.24)}
NUEVOS = ("ES", "MYM", "GC", "6E", "6B", "6J", "MBT")
TPS = (1.5, 2.0, 2.5); RANGOS = ((100, 115), (100, 130)); FILS = ("vwap", "vwap_ema"); SALIDAS = (1600, 1100)
NB = 2000


def cargar(inst):
    parts = []
    for p in sorted(glob.glob(str(BUN / f"{inst}_*_M1_LUXIMB.json"))):
        if "HOLDOUT" in p: continue
        B = json.load(open(p, encoding="utf-8")); parts.append(pd.DataFrame(B["bar_series"]["time_1m"]["candles"])); del B
    d = pd.concat(parts, ignore_index=True).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    d["et"] = pd.to_datetime(d.time, unit="s", utc=True).dt.tz_convert("America/New_York")
    d = d[d.et < FIN_DESC].reset_index(drop=True)
    d["hm"] = d.et.dt.hour * 100 + d.et.dt.minute; d["fecha"] = d.et.dt.date
    d["sesion"] = (d.et + pd.Timedelta(hours=6)).dt.date
    tp = (d.high + d.low + d.close) / 3; vol = d.volume.clip(lower=1e-9)
    d["vwap"] = (tp * vol).groupby(d.sesion).cumsum() / vol.groupby(d.sesion).cumsum()
    d["b5"] = d.time // 300
    c5 = d.groupby("b5").close.last(); d["ema5"] = d.b5.map(c5.ewm(span=50, adjust=False).mean())
    return d


def senales(d, r0, r1, salida):
    out = []
    for fecha, g in d.groupby("fecha"):
        r = g[(g.hm >= r0) & (g.hm < r1)]
        if len(r) < 0.6 * ((r1 // 100 * 60 + r1 % 100) - (r0 // 100 * 60 + r0 % 100)): continue
        hi, lo = r.high.max(), r.low.min()
        post = g[(g.hm >= r1) & (g.hm < salida)]
        if post.empty or hi <= lo: continue
        five = post.groupby("b5").agg(close=("close", "last"), k=("close", lambda s: s.index[-1]))
        for _, row in five.iterrows():
            dirn = 1 if row.close > hi else (-1 if row.close < lo else 0)
            if dirn:
                k = int(row.k)
                out.append(dict(fecha=fecha, hi=hi, lo=lo, dir=dirn, k=k, c=row.close, vwap=d.vwap[k], ema=d.ema5[k], fin=int(post.index[-1])))
                break
    return out


def operar(d, s, tp_r, tick, comm_pts):
    h, l, c = d.high.values, d.low.values, d.close.values
    dirn = s["dir"]; E = s["c"] + dirn * tick; sl = s["lo"] if dirn > 0 else s["hi"]; risk = dirn * (E - sl)
    if risk <= 0: return None
    tp = E + dirn * tp_r * risk
    for j in range(s["k"] + 1, s["fin"] + 1):
        if (l[j] <= sl) if dirn > 0 else (h[j] >= sl): pts = dirn * (sl - dirn * tick - E) - comm_pts; return pts, pts / risk, "SL"
        if (h[j] >= tp) if dirn > 0 else (l[j] <= tp): pts = dirn * (tp - E) - comm_pts; return pts, pts / risk, "TP"
    pts = dirn * (c[s["fin"]] - dirn * tick - E) - comm_pts
    return pts, pts / risk, "T"


def main():
    rows = []
    for inst, (tick, usd_pt, comm) in ACT.items():
        d = cargar(inst); cp = comm / usd_pt
        for (r0, r1), sal in itertools.product(RANGOS, SALIDAS):
            for s in senales(d, r0, r1, sal):
                okv = (s["c"] > s["vwap"]) if s["dir"] > 0 else (s["c"] < s["vwap"]); oke = (s["c"] > s["ema"]) if s["dir"] > 0 else (s["c"] < s["ema"])
                for fil in FILS:
                    if not okv or (fil == "vwap_ema" and not oke): continue
                    for tp_r in TPS:
                        r = operar(d, s, tp_r, tick, cp)
                        if r: rows.append(dict(inst=inst, fecha=str(s["fecha"]), rango=f"{r0:04d}-{r1:04d}", salida=sal, fil=fil, tp=tp_r, pts=r[0], R=r[1], why=r[2], usd=r[0] * usd_pt))
        print(inst, len(d), flush=True)
    df = pd.DataFrame(rows); df.to_csv(Path(sys.argv[1]).with_suffix(".csv"), index=False)
    rng = np.random.default_rng(20261021); celdas = []
    for key, g in df.groupby(["tp", "rango", "fil", "salida"]):
        rec = dict(tp=key[0], rango=key[1], fil=key[2], salida=key[3], activos={})
        ests, ses = [], []
        for inst in ACT:
            x = g[g.inst == inst]
            if len(x) < 10: continue
            v = x.R.values; bs = np.array([rng.choice(v, len(v)).mean() for _ in range(NB)]); eq = np.cumsum(x.sort_values("fecha").usd.values)
            gp, gl = x.pts[x.pts > 0].sum(), -x.pts[x.pts < 0].sum()
            rec["activos"][inst] = dict(n=len(x), acierto=round(float((x.why == "TP").mean()), 3), R_op=round(float(v.mean()), 3), se=round(float(bs.std()), 4),
                                        usd_op=round(float(x.usd.mean()), 1), pf=round(float(gp / gl), 2) if gl else None, maxdd_usd=round(float((np.maximum.accumulate(eq) - eq).max()), 0),
                                        R_2025=round(float(x[x.fecha < "2026"].R.mean()), 3) if (x.fecha < "2026").any() else None,
                                        R_2026=round(float(x[x.fecha >= "2026"].R.mean()), 3) if (x.fecha >= "2026").any() else None)
            if inst in NUEVOS: ests.append(v.mean()); ses.append(bs.std())
        w = 1 / np.array(ses) ** 2; est = float((w * np.array(ests)).sum() / w.sum()); se = float(np.sqrt(1 / w.sum()))
        rec["combinado_7"] = dict(R_op=round(est, 4), se=round(se, 4), ic95=[round(est - 1.96 * se, 4), round(est + 1.96 * se, 4)], p=float(2 * norm.sf(abs(est / se))),
                                  positivos=int(sum(e > 0 for e in ests)), activos=len(ests))
        celdas.append(rec)
    order = sorted(range(len(celdas)), key=lambda i: celdas[i]["combinado_7"]["p"]); run = 0.0
    for k, i in enumerate(order):
        run = max(run, min(1.0, (len(order) - k) * celdas[i]["combinado_7"]["p"])); c = celdas[i]
        c["combinado_7"]["holm"] = round(run, 4); c["transporta"] = bool(run < 0.05 and c["combinado_7"]["R_op"] > 0 and c["combinado_7"]["positivos"] >= 5)
    out = dict(manifiesto="MANIFIESTO_ORB0100_V2_MULTIACTIVO_20261021.md", celdas=sorted(celdas, key=lambda c: -c["combinado_7"]["R_op"]))
    json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1, default=str)
    for c in out["celdas"]:
        print(c["tp"], c["rango"], c["fil"], c["salida"], "comb", c["combinado_7"]["R_op"], c["combinado_7"]["ic95"], "pos", c["combinado_7"]["positivos"], "holm", c["combinado_7"]["holm"],
              "|", " ".join(f"{a}:{v['R_op']:+.2f}" for a, v in c["activos"].items()))


if __name__ == "__main__":
    main()
