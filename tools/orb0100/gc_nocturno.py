"""GC nocturno en abr-jun 2026 (preregistro PREREGISTRO_GC_NOCTURNO_20261021.md). Uso: gc_nocturno.py <out.json> <bundle>..."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orb_horarios as OH  # noqa: E402

TICK, COMM = 0.1, 4.5 / 100.0
VENT = {"22:30": 270, "23:00": 300, "23:30": 330, "00:00": 360, "00:30": 390, "01:00": 420, "01:30": 450, "02:00": 480, "02:30": 510}
DEST = [("01:00", "R0"), ("23:00", "R1"), ("02:30", "R1"), ("22:30", "R1")]


def cargar(paths):
    parts = []
    for p in paths:
        B = json.load(open(p, encoding="utf-8")); parts.append(pd.DataFrame(B["bar_series"]["time_1m"]["candles"])); del B
    d = pd.concat(parts, ignore_index=True).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    d["et"] = pd.to_datetime(d.time, unit="s", utc=True).dt.tz_convert("America/New_York")
    a = pd.Timestamp("2026-03-31 18:00", tz="America/New_York"); b = pd.Timestamp("2026-06-30 17:00", tz="America/New_York")
    d = d[(d.et >= a) & (d.et < b)].reset_index(drop=True)
    d["sesion"] = (d.et + pd.Timedelta(hours=6)).dt.date; d["sm"] = ((d.et.dt.hour * 60 + d.et.dt.minute) - 1080) % 1440
    tp = (d.high + d.low + d.close) / 3; vol = d.volume.clip(lower=1e-9)
    d["vwap"] = (tp * vol).groupby(d.sesion).cumsum() / vol.groupby(d.sesion).cumsum(); d["b5"] = d.time // 300
    return d


def main():
    d = cargar(sys.argv[2:]); h, l, c = d.high.values, d.low.values, d.close.values; rows = []
    for v, m0 in VENT.items():
        for s in OH.senales_ses(d, m0):
            for rn, (tp_r, uv) in OH.REGLAS.items():
                if uv and not ((s["c"] > s["vwap"]) if s["dir"] > 0 else (s["c"] < s["vwap"])): continue
                E = s["c"] + s["dir"] * TICK; risk = s["dir"] * (E - (s["lo"] if s["dir"] > 0 else s["hi"]))
                if risk <= 0: continue
                rows.append(dict(ventana=v, regla=rn, dia=s["fecha"], R=OH.opera_dir(h, l, c, s["k"], s["fin"], E, s["dir"], risk, tp_r, TICK, COMM)))
    df = pd.DataFrame(rows); rng = np.random.default_rng(20261021)
    def boot(x):
        days = x.dia.unique(); ix = {k: np.flatnonzero(x.dia.values == k) for k in days}; v = x.R.values
        bs = np.array([v[np.concatenate([ix[k] for k in rng.choice(days, len(days))])].mean() for _ in range(10000)])
        return dict(n=len(v), dias=len(days), R_op=round(float(v.mean()), 4), ic95=[round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)])
    h1 = boot(df); h1["veredicto"] = "CONFIRMA" if h1["ic95"][0] > 0 else ("REFUTA" if h1["R_op"] <= 0 else "NO_CONCLUYENTE")
    out = dict(H1_racimo=h1, destacadas={f"{v} {r}": boot(df[(df.ventana == v) & (df.regla == r)]) for v, r in DEST},
               por_celda={f"{v} {r}": round(float(g.R.mean()), 3) for (v, r), g in df.groupby(["ventana", "regla"])},
               por_mes={m: round(float(g.R.mean()), 3) for m, g in df.groupby(df.dia.astype(str).str[:7])})
    json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1, default=str); print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
