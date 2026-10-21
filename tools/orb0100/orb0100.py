"""ORB0100: rango 01:00-01:15 NY, ruptura por cierre de vela de 5 min. Grilla del manifiesto
docs/research/orb0100_20261021/MANIFIESTO_ORB0100_20261021.md (no cambiar sin enmienda). Resolucion con velas M1.
Uso: python tools/orb0100/orb0100.py <out.json>"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]; BUN = REPO / "viewer/nt8_bridge/bundles"
TICK = 0.25
COSTOS = {"MNQ": dict(comm=0.62, usd_pt=2.0), "NQ": dict(comm=0.225, usd_pt=20.0), "ES": dict(comm=0.09, usd_pt=50.0)}
TPS = (0.5, 0.75, 1.0, 1.5); SLS = ("rango", "mitad"); ENTS = ("mercado", "limite"); FILS = ("ninguno", "ema50", "vwap")
FIN_DESC = pd.Timestamp("2026-03-31 17:00", tz="America/Chicago")


def cargar(inst):
    parts = []
    for c in ("09-25", "12-25", "03-26", "06-26"):
        B = json.load(open(BUN / f"{inst}_{c}_M1_LUXIMB.json", encoding="utf-8"))
        parts.append(pd.DataFrame(B["bar_series"]["time_1m"]["candles"])); del B
    d = pd.concat(parts, ignore_index=True).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    d["et"] = pd.to_datetime(d.time, unit="s", utc=True).dt.tz_convert("America/New_York")
    d = d[d.et < FIN_DESC.tz_convert("America/New_York")].reset_index(drop=True)
    d["hm"] = d.et.dt.hour * 100 + d.et.dt.minute; d["fecha"] = d.et.dt.date
    ses = d.et + pd.Timedelta(hours=6); d["sesion"] = ses.dt.date                      # sesion CME desde 18:00 ET
    tp = (d.high + d.low + d.close) / 3; d["pv"] = (tp * d.volume).groupby(d.sesion).cumsum(); d["vv"] = d.volume.groupby(d.sesion).cumsum()
    d["vwap"] = d.pv / d.vv.replace(0, np.nan)
    d["b5"] = d.time // 300
    c5 = d.groupby("b5").close.last(); ema = c5.ewm(span=50, adjust=False).mean()          # EMA 50 de 5 min, causal al cierre
    d["ema5"] = d.b5.map(ema)
    return d


def senales(d):
    """Por dia ET: rango 01:00-01:15 y primera ruptura por cierre de 5 min (cierre <= 16:00)."""
    out = []
    for fecha, g in d.groupby("fecha"):
        r = g[(g.hm >= 100) & (g.hm < 115)]
        if len(r) < 10: continue                                                          # rango incompleto
        hi, lo = r.high.max(), r.low.min()
        post = g[(g.hm >= 115) & (g.hm < 1600)]
        if post.empty: continue
        five = post.groupby("b5").agg(close=("close", "last"), last_idx=("close", lambda s: s.index[-1]))
        for b5, row in five.iterrows():
            dirn = 1 if row.close > hi else (-1 if row.close < lo else 0)
            if dirn:
                k = int(row.last_idx)                                                     # ultima M1 de la vela de 5 min
                out.append(dict(fecha=fecha, hi=hi, lo=lo, dir=dirn, k=k, close5=row.close, vwap=d.vwap[k], ema=d.ema5[k],
                                fin=int(g.index[g.hm < 1600][-1])))
                break
    return out


def operar(d, s, tp_r, sl_m, ent, comm):
    h, l, c = d.high.values, d.low.values, d.close.values
    dirn = s["dir"]; k = s["k"]; fin = s["fin"]
    if ent == "mercado":
        E = s["close5"] + dirn * TICK; j0 = k + 1
    else:
        E = s["hi"] if dirn > 0 else s["lo"]; j0 = None
        for j in range(k + 1, fin + 1):
            if (l[j] <= E) if dirn > 0 else (h[j] >= E): j0 = j; break
        if j0 is None: return None
    sl = (s["lo"] if dirn > 0 else s["hi"]) if sl_m == "rango" else (s["hi"] + s["lo"]) / 2
    risk = dirn * (E - sl)
    if risk <= 0: return None
    tp = E + dirn * tp_r * risk
    for j in range(j0, fin + 1):
        if (l[j] <= sl) if dirn > 0 else (h[j] >= sl): return dirn * (sl - dirn * TICK - E) - comm, "SL", risk
        if ent == "limite" and j == j0: continue                                         # en la vela del llenado no se cuenta TP
        if (h[j] >= tp) if dirn > 0 else (l[j] <= tp): return dirn * (tp - E) - comm, "TP", risk
    return dirn * (c[fin] - dirn * TICK - E) - comm, "T", risk


def main():
    rows = []
    for inst in ("NQ", "ES"):
        d = cargar(inst); S = senales(d)
        for s in S:
            per = "ES" if inst == "ES" else ("IS" if pd.Timestamp(s["fecha"]) < pd.Timestamp("2026-01-01") else "OOS")
            for tp_r, sl_m, ent, fil in itertools.product(TPS, SLS, ENTS, FILS):
                if fil == "ema50" and not ((s["close5"] > s["ema"]) if s["dir"] > 0 else (s["close5"] < s["ema"])): continue
                if fil == "vwap" and not ((s["close5"] > s["vwap"]) if s["dir"] > 0 else (s["close5"] < s["vwap"])): continue
                for cm in (("MNQ", "NQ") if inst == "NQ" else ("ES",)):
                    r = operar(d, s, tp_r, sl_m, ent, COSTOS[cm]["comm"])
                    if r is None: continue
                    rows.append(dict(per=per, inst=inst, costo=cm, fecha=str(s["fecha"]), tp=tp_r, sl=sl_m, ent=ent, fil=fil, pts=r[0], why=r[1],
                                     usd=r[0] * COSTOS[cm]["usd_pt"]))
        print(inst, "dias con senal", len(S), flush=True)
    df = pd.DataFrame(rows); df.to_csv(Path(sys.argv[1]).with_suffix(".csv"), index=False)
    rng = np.random.default_rng(20261021); celdas = []
    for key, g in df.groupby(["tp", "sl", "ent", "fil"]):
        rec = dict(tp=key[0], sl=key[1], ent=key[2], fil=key[3])
        for per, cm in (("IS", "MNQ"), ("OOS", "MNQ"), ("IS", "NQ"), ("OOS", "NQ"), ("ES", "ES")):
            x = g[(g.per == per) & (g.costo == cm)].sort_values("fecha")
            if x.empty: continue
            v = x.pts.values; u = x.usd.values; eq = np.cumsum(u)
            bs = [rng.choice(v, len(v)).mean() for _ in range(2000)]
            gp, gl = v[v > 0].sum(), -v[v < 0].sum()
            rec[f"{per}_{cm}"] = dict(n=len(v), acierto=round(float((x.why == "TP").mean()), 3), pts_op=round(float(v.mean()), 3), usd_op=round(float(u.mean()), 2),
                                      usd_total=round(float(u.sum()), 1), pf=round(float(gp / gl), 3) if gl else None,
                                      maxdd_usd=round(float((np.maximum.accumulate(eq) - eq).max()), 1), ic95_pts=[round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)])
        celdas.append(rec)
    elegibles = [c for c in celdas if "IS_MNQ" in c and c["IS_MNQ"]["n"] >= 40 and (c["IS_MNQ"]["pf"] or 0) >= 1.1]
    top = sorted(elegibles, key=lambda c: -c["IS_MNQ"]["pts_op"])[:3]
    for c in top: c["sobrevive"] = bool(c.get("OOS_NQ", {}).get("pts_op", -1) > 0 and c.get("ES_ES", {}).get("pts_op", -1) > 0)
    isv = np.array([c["IS_MNQ"]["pts_op"] for c in celdas]); oov = np.array([c["OOS_MNQ"]["pts_op"] for c in celdas]); esv = np.array([c["ES_ES"]["pts_op"] for c in celdas])
    diag = dict(corr_IS_OOS=round(float(np.corrcoef(isv, oov)[0, 1]), 3), corr_IS_ES=round(float(np.corrcoef(isv, esv)[0, 1]), 3),
                celdas_IS_pos=int((isv > 0).sum()), celdas_OOS_pos=int((oov > 0).sum()), celdas_ES_pos=int((esv > 0).sum()), n_celdas=len(celdas),
                mediana_IS=float(np.median(isv)), mediana_OOS=float(np.median(oov)), mediana_ES=float(np.median(esv)))
    base = next(c for c in celdas if c["tp"] == 0.5 and c["sl"] == "rango" and c["ent"] == "mercado" and c["fil"] == "ninguno")
    out = dict(manifiesto="MANIFIESTO_ORB0100_20261021.md", base=base, top3_IS=top, diagnostico=diag, celdas=celdas)
    json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1, default=str)
    print(json.dumps(dict(base=base, diag=diag, top3=top), indent=1, default=str))


if __name__ == "__main__":
    main()
