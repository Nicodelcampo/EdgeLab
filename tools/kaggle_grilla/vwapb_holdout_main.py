"""Kernel: holdout de la banda 3 del VWAP (reversión, objetivo VWAP, stop extremo; edgelab/research/m1_intradia.py::vwap_banda) sobre los
ticks SELLADOS de futuros (NQ, YM; ES como control) desde 2026-10-01. Acta: docs/research/m1_intradia_20261114/ACTA_HOLDOUT_VWAPB3.md.
Lo arma tools/m1_intradia.py lanzar_vwapb_holdout (módulos incrustados). Sólo se guarda la variante congelada."""
import glob, json, os, time
import numpy as np, pandas as pd
M = __import__("m1_intradia"); from edgelab.research import fuentes_ticks as F
t0 = time.time(); ent = os.environ.get("ENTRADA", "/kaggle/input")
ACTA = json.loads(os.environ["ACTA_JSON"]); acta = os.path.abspath("ACTA_HOLDOUT.json"); json.dump(ACTA, open(acta, "w"))
FRIC = json.loads(os.environ["FRICCION_JSON"]); D0, D1 = int(os.environ["DESDE"]), int(os.environ["HASTA"])
raiz = os.path.dirname(glob.glob(ent + "/**/SELLADO.txt", recursive=True)[0]); out = {}
def m1(bloques):
    T = pd.concat(list(bloques), ignore_index=True)
    t = pd.to_datetime(T.ts_ns.to_numpy(), utc=True).tz_convert("America/New_York").tz_localize(None)
    S = pd.DataFrame(dict(px=T.px.to_numpy(float), vol=T.vol.to_numpy(float)), index=t).sort_index()
    B = S.px.resample("1min").ohlc().join(S.vol.resample("1min").sum()).dropna(subset=["open"])
    return pd.DataFrame(dict(o=B.open, h=B.high, l=B.low, c=B.close, v=B.vol), index=B.index), sorted(T.sesion.unique().tolist())
for inst in ("NQ", "YM", "ES"):
    rutas = sorted(glob.glob(raiz + f"/**/{inst}_*ticks.parquet", recursive=True))
    D, ses = m1(F.bloques_nq_sellado(D0, D1, rutas, acta, F.TICK_FUTURO[inst]))
    V = M.vwap_banda(D, FRIC[inst]); V = V[(V.k == 3) & (V.modo == "REV") & (V.obj == "VWAP") & (V.stop == "EXT")]
    out[inst] = dict(sesiones=[int(s) for s in ses], ops=[[str(d.date()), float(b), float(n)] for d, b, n in zip(V.dia, V.r_bruto, V.r_neto)])
    print(f"[{time.time() - t0:5.0f}s] {inst}: {len(ses)} sesiones, {len(V)} operaciones", flush=True)
json.dump(dict(acta=ACTA, friccion=FRIC, desde=D0, hasta=D1, resultado=out), open("RESULTADO.json", "w"), indent=1)
print("listo")
