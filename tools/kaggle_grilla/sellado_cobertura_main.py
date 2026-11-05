# Integridad target-free del sellado: por archivo y sesión CME, ticks, primer y último tick (UTC) y horas con datos. Sin precios ni P&L.
import glob
import json

import pandas as pd


def main():
    from edgelab.research import fuentes_ticks as F
    out = {}
    for f in sorted(glob.glob("/kaggle/input/**/*_ticks.parquet", recursive=True)):
        n = f.split("/")[-1].replace("_ticks.parquet", "")
        if n.split("_")[0] not in ("NQ", "ES", "YM", "GC"): continue
        cols = pd.read_parquet(f, columns=None).columns
        tcol = "ts_utc_ns" if "ts_utc_ns" in cols else "time_utc_ns"
        t = pd.read_parquet(f, columns=[tcol] + (["trade_date"] if "trade_date" in cols else []))
        td = t.trade_date.to_numpy() if "trade_date" in t else F._td(t[tcol].to_numpy())
        d = pd.DataFrame(dict(td=td, ts=pd.to_datetime(t[tcol], utc=True)))
        d = d[(d.td >= 20261026)]
        g = d.groupby("td").ts.agg(["count", "min", "max"])
        horas = d.assign(h=d.ts.dt.floor("h")).groupby("td").h.nunique()
        out[n] = {int(k): dict(ticks=int(r["count"]), primero=str(r["min"]), ultimo=str(r["max"]), horas=int(horas[k])) for k, r in g.iterrows()}
    json.dump(out, open("SELLADO_COBERTURA.json", "w"), indent=1); print(json.dumps(out, indent=1))


main()
