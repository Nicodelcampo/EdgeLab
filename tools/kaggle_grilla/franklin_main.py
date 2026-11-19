"""Kernel: FRANKLIN (regla congelada) sobre desarrollo + spot sellado de Dukascopy (USATECH → NQ, USA500 → ES), más el sesgo por minuto de NQ
(filtro de T) y el tercil de noche por día (veto de PREAPERTURA-ES). Lo arma tools/franklin_seguimiento.py (apertura del holdout o forward)."""
import glob, json, os
import numpy as np, pandas as pd
M = __import__("m1_intradia"); FM = __import__("fundedsync_mecanismos")
from edgelab.research import estrategias_scrapeadas as X
from edgelab.research import fuentes_ticks as FT
ent = os.environ.get("ENTRADA", "/kaggle/input"); DESDE, HASTA = int(os.environ["DESDE"]), int(os.environ["HASTA"])
CELDA = tuple(json.loads(os.environ["CELDA"])); json.dump(json.loads(os.environ["ACTA_JSON"]), open("ACTA_HOLDOUT.json", "w"))
raiz = os.path.dirname(glob.glob(ent + "/**/SELLADO.txt", recursive=True)[0])
INST = {"NQ": ("NQ_M1_dukas", "USATECHIDXUSD", 1.5455), "ES": ("SP_M1_dukas", "USA500IDXUSD", 0.8877)}


def m1_sellado(sim):
    T = pd.concat(list(FT.bloques_spot_sellado(sim, 20261001, HASTA, raiz)), ignore_index=True)
    tt = pd.to_datetime(T.ts_ns.to_numpy(), utc=True).tz_convert("America/New_York").tz_localize(None)
    S = pd.DataFrame(dict(px=T.px.to_numpy(float), vol=T.vol.to_numpy(float)), index=tt).sort_index()
    B = S.px.resample("1min").ohlc().join(S.vol.resample("1min").sum()).dropna(subset=["open"])
    return pd.DataFrame(dict(o=B.open, h=B.high, l=B.low, c=B.close, v=B.vol), index=B.index)


ops, noche, res = [], [], {}
for inst, (dev, sim, fr) in INST.items():
    D = M.leer_m1(sorted(glob.glob(ent + f"/**/{dev}*.csv", recursive=True))[0]); D = D[(D.index >= "2024-01-01") & (D.index < "2026-09-30")]
    H = m1_sellado(sim); D = pd.concat([D[D.index < H.index.min()], H]); ctx = X.ctx_de_m1(D)
    print(inst, "velas selladas", len(H), "hasta", H.index.max(), flush=True)
    R = X.franklin_variantes(ctx, celdas=[CELDA]); R = R[(R.fecha >= DESDE) & (R.fecha <= HASTA)].copy()
    R["inst"] = inst; R["neto"] = R.bruto - fr; R["R"] = R.neto / R.riesgo; ops.append(R.drop(columns=["celda"]))
    V = FM.contexto(D); V = V[(V.index >= pd.Timestamp(str(DESDE))) & (V.index <= pd.Timestamp(str(HASTA)))]
    noche.append(pd.DataFrame(dict(inst=inst, fecha=V.index.strftime("%Y%m%d").astype(int), noche=V.noche.values)))
    if inst == "NQ":                                                           # sesgo por minuto (09:30–16:00) para el filtro de T
        vw, lh, ll = X._sesgo_franklin(ctx); m, f, _ = X._hora(ctx, "America/New_York"); c = ctx["c"]
        k = (f >= DESDE) & (f <= HASTA) & (m >= 570) & (m < 960)
        s = np.where((c > lh) & (c > vw), 1, np.where((c < ll) & (c < vw), -1, 0))
        pd.DataFrame(dict(fecha=f[k], minuto=m[k], sesgo=s[k])).to_csv("SESGO_NQ.csv", index=False)
    res[inst] = dict(n=int(len(R)), R=float(R.R.mean()) if len(R) else None, sesiones=int(R.fecha.nunique()))
pd.concat(ops).to_csv("FRANKLIN_OPS.csv", index=False); pd.concat(noche).to_csv("NOCHE.csv", index=False)
json.dump(dict(celda=CELDA, desde=DESDE, hasta=HASTA, resumen=res), open("RESUMEN.json", "w"), indent=1); print("listo", res)
