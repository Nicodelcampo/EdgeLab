"""Convierte EdgeLab Tick History (<yyyyMMdd>.Last.utc.txt: 'yyyyMMdd HHmmss fffffff;last;bid;ask;volume', UTC) al formato
de ticks del release (ts_utc_ns, price_ticks, volume, contract, trade_date de sesion CME). Target-free.
trade_date = fecha de la sesion CME (abre 17:00 America/Chicago del dia anterior).
Uso: python tools/luximb_parity/convertir_tick_history.py <carpeta_contrato> "<CONTRATO>" <tick> <out.parquet>"""
import glob
import sys

import numpy as np
import pandas as pd

src, contrato, tick, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
parts = []
for f in sorted(glob.glob(f"{src}/*.Last.utc.txt")):
    d = pd.read_csv(f, sep=";", header=None, names=["ts", "last", "bid", "ask", "volume"], dtype={"ts": str})
    parts.append(d)
d = pd.concat(parts, ignore_index=True)
ts = pd.to_datetime(d.ts.str.slice(0, 15), format="%Y%m%d %H%M%S", utc=True) + pd.to_timedelta(d.ts.str.slice(16, 23).astype(np.int64) * 100, unit="ns")
ct = ts.dt.tz_convert("America/Chicago")
td = (ct + pd.Timedelta(hours=7)).dt.strftime("%Y%m%d").astype(np.int32)          # 17:00 CT -> sesion del dia siguiente
o = pd.DataFrame({"ts_utc_ns": ts.astype("int64"), "price_ticks": np.round(d["last"] / tick).astype(np.int64), "volume": d.volume.astype(np.int64),
                  "contract": contrato, "trade_date": td}).sort_values("ts_utc_ns", kind="stable")
assert np.allclose(o.price_ticks * tick, d.loc[o.index, "last"]), "precios fuera de la grilla de tick"
o.to_parquet(out, index=False)
print(len(o), "ticks;", o.trade_date.nunique(), "sesiones:", sorted(o.trade_date.unique().tolist()))
