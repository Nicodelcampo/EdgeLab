"""Kernel: SessionOpenMomentum (celda sin_finde, congelada) en NQ sobre desarrollo + USATECH sellado (holdout o forward). Lo arma tools/som_seguimiento.py."""
import glob, json, os
from dataclasses import replace
import numpy as np, pandas as pd
from edgelab.research import fuentes_ticks as FT
from edgelab.research.quantlab_mt5.indicators import load_ohlc_data
from edgelab.research.quantlab_mt5.session_open_momentum import correr_session_open_momentum
from edgelab.research.quantlab_mt5.contracts import SessionOpenMomentumConfig
ent = os.environ.get("ENTRADA", "/kaggle/input"); DESDE, HASTA = int(os.environ["DESDE"]), int(os.environ["HASTA"]); FR = 1.5455
json.dump(json.loads(os.environ["ACTA_JSON"]), open("ACTA_HOLDOUT.json", "w"))
raiz = os.path.dirname(glob.glob(ent + "/**/SELLADO.txt", recursive=True)[0])
D = load_ohlc_data(sorted(glob.glob(ent + "/**/NQ_M1_dukas*.csv", recursive=True))[0], start="2026-01-01")      # hora del servidor (NY + 7) rotulada UTC
T = pd.concat(list(FT.bloques_spot_sellado("USATECHIDXUSD", 20261001, HASTA, raiz)), ignore_index=True)
tt = pd.to_datetime(T.ts_ns.to_numpy(), utc=True).tz_convert("America/New_York").tz_localize(None) + pd.Timedelta(hours=7)   # → hora del servidor
S = pd.DataFrame(dict(px=T.px.to_numpy(float), vol=T.vol.to_numpy(float)), index=tt).sort_index()
B = S.px.resample("1min").ohlc().join(S.vol.resample("1min").sum()).dropna(subset=["open"])
H = pd.DataFrame(dict(time=B.index.tz_localize("UTC"), open=B.open.values, high=B.high.values, low=B.low.values, close=B.close.values, volume=B.vol.values))
H["ts_ns"] = H.time.astype("datetime64[ns, UTC]").astype("int64"); D["ts_ns"] = pd.to_datetime(D.time, utc=True).astype("datetime64[ns, UTC]").astype("int64")
df = pd.concat([D[D.ts_ns < H.ts_ns.min()], H[D.columns.intersection(H.columns)]], ignore_index=True)
print("velas selladas", len(H), "hasta", H.time.max(), flush=True)
cfg = replace(SessionOpenMomentumConfig(), close_weekend=True)
R = correr_session_open_momentum(df, config=cfg, instrument="USATECH")
R["fecha"] = pd.to_datetime(R.entry_time_utc, unit="ns").dt.strftime("%Y%m%d").astype(int)
R = R[(R.fecha >= DESDE) & (R.fecha <= HASTA)].copy()
R["riesgo"] = (R.entry_price - R.stop_price).abs(); R["neto"] = R.pnl_pts - FR; R["R"] = R.neto / R.riesgo
R.to_csv("SOM_OPS.csv", index=False)
json.dump(dict(desde=DESDE, hasta=HASTA, n=int(len(R)), R=float(R.R.mean()) if len(R) else None, salidas=R.exit_name.value_counts().to_dict()), open("RESUMEN.json", "w"), indent=1)
print("listo", len(R))
