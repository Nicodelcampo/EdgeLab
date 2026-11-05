# Integridad target-free del dataset sellado: ticks por sesión CME de cada futuro y cada spot (sin precios ni P&L).
import glob
import json

import numpy as np
import pandas as pd


def main():
    from edgelab.research import fuentes_ticks as F
    ent = "/kaggle/input"; out = {}
    for f in sorted(glob.glob(f"{ent}/**/*_ticks.parquet", recursive=True)):
        nombre = f.split("/")[-1].replace("_ticks.parquet", "")
        cols = ["trade_date"] if "_" in nombre and nombre.split("_")[0].isupper() and not nombre.endswith("USD") else ["time_utc_ns"]
        try: t = pd.read_parquet(f, columns=cols)
        except Exception: t = pd.read_parquet(f, columns=["time_utc_ns"]); cols = ["time_utc_ns"]
        td = t.trade_date.to_numpy() if cols == ["trade_date"] else F._td(t.time_utc_ns.to_numpy())
        out[nombre] = {int(k): int(v) for k, v in pd.Series(td).value_counts().sort_index().items()}
    json.dump(out, open("SELLADO_CONTEO.json", "w"), indent=1); print({k: len(v) for k, v in out.items()})


main()
