"""Kernel del paso 1b de docs/research/urgencia_vs_evidencia_20261117 (PREREGISTRO_PASO1B.md): la grilla COMPLETA de M1 intradía
(ORB, pre-rango, banda del VWAP; 8 índices; edgelab/research/m1_intradia.familia, el mismo motor) agregada por mes y por variante:
n, suma y suma de cuadrados del R neto y bruto recortado a [−3, 5]. No elige nada; el ajuste del modelo es local
(tools/vida_ventaja_medir.py m1). Lo arma tools/m1_intradia.py lanzar_vida."""
import glob, json, os, time
import numpy as np, pandas as pd
M = __import__("m1_intradia"); t0 = time.time(); ent = os.environ.get("ENTRADA", "/kaggle/input")
IDX = ("SP_M1_dukas", "NQ_M1_dukas", "DJ_M1_dukas", "USSC2000IDXUSD", "DEUIDXEUR", "JPNIDXJPY", "GBRIDXGBP", "EUSIDXEUR")
SP = json.load(open(glob.glob(ent + "/**/spreads.json", recursive=True)[0])); DD = {}
for s in IDX:
    f = glob.glob(ent + f"/**/{s}-M1-*.csv", recursive=True)
    if f: DD[s] = M.leer_m1(f[0]); print(f"[{time.time() - t0:6.0f}s] {s} {len(DD[s])}", flush=True)
F = M.familia(DD, SP); out = {}
for k, v in F.items():
    if "INFO" in k or k.startswith("CANASTA"): continue
    v = v[pd.to_datetime(v.dia) < "2026-09-30"]
    if not len(v): continue
    mes = pd.to_datetime(v.dia).dt.strftime("%Y-%m"); fila = {"n": v.groupby(mes).size()}
    for c in ("neto", "bruto"):
        r = np.clip(v[f"r_{c}"].astype(float), -3.0, 5.0); fila["s_" + c] = r.groupby(mes).sum(); fila["q_" + c] = (r ** 2).groupby(mes).sum()
    idx = fila["n"].index
    out[k] = dict(mes=list(idx), **{a: [float(x) for x in b.reindex(idx).values] for a, b in fila.items()})
json.dump(dict(series=out, activos=sorted(DD), segundos=round(time.time() - t0)), open("M1_VIDA.json", "w"))
print("listo", len(out), "series")
