"""Kernel: operaciones POR DÍA de la reversión/continuación desde la banda del VWAP (edgelab/research/m1_intradia.py::vwap_banda) en
Nasdaq, Dow, S&P y DAX, para el mapa de régimen (docs/research/m1_intradia_20261114/PREREGISTRO_REGIMEN_VWAPB.md). Sin nulo: la familia ya
se midió; acá sólo se guardan las operaciones con su día."""
import glob, json, os, time
import pandas as pd
M = __import__("m1_intradia"); t0 = time.time(); ent = os.environ.get("ENTRADA", "/kaggle/input")
SP = json.load(open(glob.glob(ent + "/**/spreads.json", recursive=True)[0])); partes = []
for s in ("NQ_M1_dukas", "DJ_M1_dukas", "SP_M1_dukas", "DEUIDXEUR"):
    f = glob.glob(ent + f"/**/{s}-M1-*.csv", recursive=True)
    if not f: continue
    V = M.vwap_banda(M.leer_m1(f[0]), SP.get(s, 0.0)); V["activo"] = s; partes.append(V)
    print(f"[{time.time() - t0:6.0f}s] {s} {len(V)}", flush=True)
pd.concat(partes, ignore_index=True).to_csv("VWAPB_OPS.csv.gz", index=False); print("listo")
