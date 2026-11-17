"""Kernel: TURTLES-ORO (base congelada) sobre XAUUSD de desarrollo + sellado (holdout o forward). Lo arma tools/turtles_oro_seguimiento.py."""
import glob, json, os
import numpy as np, pandas as pd
from edgelab.research import fuentes_ticks as FT, sqx_catalogo as S
ent = os.environ.get("ENTRADA", "/kaggle/input"); DESDE, HASTA = int(os.environ["DESDE"]), int(os.environ["HASTA"]); FR = float(os.environ["FR"])
json.dump(json.loads(os.environ["ACTA_JSON"]), open("ACTA_HOLDOUT.json", "w"))
raiz = os.path.dirname(glob.glob(ent + "/**/SELLADO.txt", recursive=True)[0])
X = pd.read_csv(sorted(glob.glob(ent + "/**/XAUUSD_M1_dukas*.csv", recursive=True))[0]); X.columns = [c.strip().lower() for c in X.columns]
t = pd.to_datetime(X["date"].astype(str) + " " + X["time"].astype(str), format="%Y%m%d %H:%M:%S") - pd.Timedelta(hours=7)   # servidor → NY
D = pd.DataFrame(dict(o=X.open.to_numpy(float), h=X.high.to_numpy(float), l=X.low.to_numpy(float), c=X.close.to_numpy(float), v=X.volume.to_numpy(float)), index=t)
D = D[D.index < "2026-09-30"]
T = pd.concat(list(FT.bloques_spot_sellado("XAUUSD", 20261001, HASTA, raiz)), ignore_index=True)
tt = pd.to_datetime(T.ts_ns.to_numpy(), utc=True).tz_convert("America/New_York").tz_localize(None)
P = pd.DataFrame(dict(px=T.px.to_numpy(float), vol=T.vol.to_numpy(float)), index=tt).sort_index()
H = P.px.resample("1min").ohlc().join(P.vol.resample("1min").sum()).dropna(subset=["open"])
H = pd.DataFrame(dict(o=H.open.values, h=H.high.values, l=H.low.values, c=H.close.values, v=H.vol.values), index=H.index)
M = pd.concat([D[D.index < H.index.min()], H]); print("M1 sellado", len(H), H.index.min(), "→", H.index.max(), flush=True)
B = S.barras_desde_m1(M, "D1"); m1 = S.indices_m1(B, M, "D1")
R = S.simular(B, S.turtle_v()(B, {}), viernes=True, m1=m1)
R = R[(R.fecha >= DESDE) & (R.fecha <= HASTA)].copy()
R["riesgo"] = (R.entrada - R.stop0).abs(); R["bruto"] = R.lado * (R.salida_px - R.entrada); R["neto"] = R.bruto - FR; R["R"] = R.neto / R.riesgo
R.to_csv("TURTLES_OPS.csv", index=False)
cerradas = R[R.motivo != "FIN"]
json.dump(dict(desde=DESDE, hasta=HASTA, ultima_barra=int(B.fecha.max()), n=int(len(cerradas)), abierta=bool((R.motivo == "FIN").any()),
               R=float(cerradas.R.mean()) if len(cerradas) else None, salidas=R.motivo.value_counts().to_dict()), open("RESUMEN.json", "w"), indent=1)
print("listo", len(R))
