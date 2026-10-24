"""Replicacion NQ abr-sep 2026 de la celda congelada (preregistro REPLICACION_NQ_ABR_SEP_PREREGISTRO_20261021.md)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orb0100_v2 as V  # noqa: E402

S = "C:/Users/Usuario/AppData/Local/Temp/claude/E--EdgeLab/123b6de9-c4bb-4dda-98d1-f41aa64b2b9f/scratchpad/bundles_full"
FUENTES = [f"{S}/NQ_06-26_M1_LUXIMB.json", str(V.BUN / "NQ_09-26_M1_LUXIMB.json"), f"{S}/NQ_12-26_M1_LUXIMB.json"]


def cargar_rep():
    parts = []
    for p in FUENTES:
        B = json.load(open(p, encoding="utf-8")); parts.append(pd.DataFrame(B["bar_series"]["time_1m"]["candles"])); del B
    d = pd.concat(parts, ignore_index=True).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    d["et"] = pd.to_datetime(d.time, unit="s", utc=True).dt.tz_convert("America/New_York")
    a = pd.Timestamp("2026-03-31 18:00", tz="America/New_York"); b = pd.Timestamp("2026-09-30 17:00", tz="America/New_York")
    d = d[(d.et >= a) & (d.et < b)].reset_index(drop=True)
    d["hm"] = d.et.dt.hour * 100 + d.et.dt.minute; d["fecha"] = d.et.dt.date; d["sesion"] = (d.et + pd.Timedelta(hours=6)).dt.date
    tp = (d.high + d.low + d.close) / 3; vol = d.volume.clip(lower=1e-9)
    d["vwap"] = (tp * vol).groupby(d.sesion).cumsum() / vol.groupby(d.sesion).cumsum()
    d["b5"] = d.time // 300; c5 = d.groupby("b5").close.last(); d["ema5"] = d.b5.map(c5.ewm(span=50, adjust=False).mean())
    return d


def main():
    d = cargar_rep(); res = {}
    for nombre, comm, usd in (("MNQ", 1.24 / 2.0, 2.0), ("NQ", 4.5 / 20.0, 20.0)):
        rows = []
        for s in V.senales(d, 100, 115, 1600):
            if not ((s["c"] > s["vwap"]) if s["dir"] > 0 else (s["c"] < s["vwap"])): continue
            r = V.operar(d, s, 1.5, 0.25, comm)
            if r: rows.append(dict(fecha=str(s["fecha"]), pts=r[0], R=r[1], why=r[2]))
        x = pd.DataFrame(rows); v = x.pts.values; rng = np.random.default_rng(20261021)
        bs = np.array([rng.choice(v, len(v)).mean() for _ in range(10000)]); eq = np.cumsum(v * usd)
        gp, gl = v[v > 0].sum(), -v[v < 0].sum()
        res[nombre] = dict(n=len(v), acierto=round(float((x.why == "TP").mean()), 3), pts_op=round(float(v.mean()), 3), R_op=round(float(x.R.mean()), 3),
                           ic95_pts=[round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)], usd_total=round(float(eq[-1]), 1),
                           pf=round(float(gp / gl), 3), maxdd_usd=round(float((np.maximum.accumulate(eq) - eq).max()), 1),
                           por_mes={m: round(float(g.pts.mean()), 2) for m, g in x.groupby(x.fecha.str[:7])})
    m = res["MNQ"]; res["veredicto"] = "CONFIRMA" if (m["pts_op"] > 0 and m["ic95_pts"][0] > 0) else ("REFUTA" if m["pts_op"] <= 0 else "NO_CONCLUYENTE")
    json.dump(res, open(sys.argv[1], "w", encoding="utf-8"), indent=1); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
