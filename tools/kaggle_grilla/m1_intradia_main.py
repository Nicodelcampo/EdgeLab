"""Kernel: ORB y pre-rango 08:12–09:12 sobre M1 de Dukascopy (edgelab/research/m1_intradia.py), con nulo intradía (minuto del día de
otro día al azar). Lo arma tools/m1_intradia.py (módulo incrustado)."""
import glob, json, os, time
import numpy as np, pandas as pd
M = __import__("m1_intradia"); t0 = time.time(); ent = os.environ.get("ENTRADA", "/kaggle/input")
IDX = tuple(os.environ["IDX"].split(",")) if os.environ.get("IDX") else ("SP_M1_dukas", "NQ_M1_dukas", "DJ_M1_dukas", "USSC2000IDXUSD", "DEUIDXEUR", "JPNIDXJPY", "GBRIDXGBP", "EUSIDXEUR")
SP = json.load(open(glob.glob(ent + "/**/spreads.json", recursive=True)[0]))
DD = {}
for s in IDX:
    f = glob.glob(ent + f"/**/{s}-M1-*.csv", recursive=True)
    if f: DD[s] = M.leer_m1(f[0]); print(f"[{time.time() - t0:6.0f}s] {s} {len(DD[s])}", flush=True)
def resumen(F):
    out = {}
    for k, v in F.items():
        if k.startswith("PRERANGO_INFO") or "PRERANGO_INFO" in k: continue
        d = pd.to_datetime(v.dia); out[k] = dict(bruto=M.por_periodo(d, v.r_bruto), neto=M.por_periodo(d, v.r_neto))
    return out
F = (M.familia2 if os.environ.get("LOTE") == "2" else M.familia)(DD, SP); R = resumen(F)
info = {k: v.toques.value_counts().to_dict() for k, v in F.items() if k.startswith("PRERANGO_INFO")}
nulo = []
for s in range(int(os.environ.get("REPS", "30"))):
    Fs = (M.familia2 if os.environ.get("LOTE") == "2" else M.familia)({k: M.sintetica_m1(v, 3000 + s) for k, v in DD.items()}, SP); Rs = resumen(Fs)
    nulo.append(max((x["neto"]["DESC"]["t"] for x in Rs.values() if x["neto"]["DESC"]["t"] is not None), default=float("nan")))
    print(f"[{time.time() - t0:6.0f}s] nulo {s} tmax {nulo[-1]:.2f}", flush=True)
json.dump(dict(variantes=R, prerango_info=info, nulo_tmax_desc_neto=nulo, umbral_p95=float(np.nanpercentile(nulo, 95)) if nulo else None,
               activos=sorted(DD), segundos=round(time.time() - t0)), open("RESULTADO.json", "w"), indent=1, default=float)
print("listo", len(R), "variantes")
