#!/usr/bin/env python3
"""ADAPTAR-PRESENTE 1 (2026-11-26): T y F de FundedSync con el tope en puntos escalado por el precio (escala_precio_ref = mediana del
cierre de NQ 2022-01 → 2025-08) contra la versión del vendedor. Pre-registro: docs/research/adaptar_presente_20261126/PREREGISTRO.md.
Reusa el kernel de tools/m1_largo.py (_kernel_fs, cargar, atr20) como correr_t2008, con los overrides del pre-registro.

  python tools/adaptar_presente.py correr     # operaciones base y variante -> OPS_T_F.csv.gz
  python tools/adaptar_presente.py leer       # lectura pre-registrada -> RESULTADO.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/adaptar_presente_20261126"
P_REF = 15757.875
TOPE = {"T": ("stop_max_points", 100.0), "F": ("max_initial_risk_points", 125.0)}


def correr():
    from registro_global import exigir_contada
    exigir_contada(DIR / "PREREGISTRO.md")
    from edgelab.research import fundedsyncstack as F
    from edgelab.research.embudo_runners import friccion
    from m1_largo import cargar, _kernel_fs
    from datos import ruta
    D = cargar("NQ", ruta("M1NT8")); partes = []
    for variante, ref in (("base", 0.0), ("escala", P_REF)):
        ns = _kernel_fs(friccion("NQ")[0])
        ns["F"] = SimpleNamespace(MODULOS={k: F.MODULOS[k] for k in ("T", "F")}, build_multi_series=F.build_multi_series,
                                  load_m1_data=F.load_m1_data,
                                  correr_modulo=lambda k, ms, _r=ref, **kw: F.correr_modulo(k, ms, **{**kw, "escala_precio_ref": _r}))
        ops = ns["operaciones"](D)
        for k, v in ops.items():
            if v is not None and len(v): partes.append(v.assign(modulo=k, variante=variante))
        print(variante, {k: (len(v) if v is not None else 0) for k, v in ops.items()}, flush=True)
    pd.concat(partes).to_csv(DIR / "OPS_T_F.csv.gz", index=False)


def leer():
    from edgelab.research.embudo_runners import friccion
    O = pd.read_csv(DIR / "OPS_T_F.csv.gz", parse_dates=["dia"]); fr_nq, fr_m = float(friccion("NQ")[0]), float(friccion("MNQ")[0])
    O = O[(O.dia >= "2012-01-01") & (O.dia <= "2026-09-30")]
    O["usd"] = (O.neto + fr_nq - fr_m) * 2.0; O["R"] = np.where(O.riesgo > 0, O.neto / O.riesgo, np.nan); O["y"] = O.dia.dt.year
    res = {}
    for mod, (campo, tope) in TOPE.items():
        r = {}
        for var, g in O[O.modulo == mod].groupby("variante"):
            m = g.groupby(g.dia.dt.to_period("M")).usd.sum(); a = g.groupby("y").usd.sum()
            esc = (g.dia.dt.year.map(lambda y: 1.0)) if var == "base" else None
            reciente = g[g.dia >= "2022-01-01"]; mr = reciente.groupby(reciente.dia.dt.to_period("M")).usd.sum()
            r[var] = dict(n=int(len(g)), usd_mes=float(m.mean()), sharpe=float(m.mean() / m.std() * np.sqrt(12)), pct_anios_pos=float((a > 0).mean()),
                          R_op=float(g.R.mean()), sharpe_2022=float(mr.mean() / mr.std() * np.sqrt(12)), usd_mes_2022=float(mr.mean()),
                          ops_por_anio={int(k): int(v) for k, v in g.groupby("y").size().items()},
                          riesgo_mediano_por_anio={int(k): float(v) for k, v in g.groupby("y").riesgo.median().items()})
        b, v = r["base"], r["escala"]
        r["adopta"] = bool(v["sharpe"] >= b["sharpe"] - 0.1 and v["pct_anios_pos"] >= b["pct_anios_pos"])
        res[mod] = r
    (DIR / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    for mod, r in res.items():
        print(mod, "adopta", r["adopta"])
        for var in ("base", "escala"):
            x = r[var]; print(" ", var, {k: (round(x[k], 3) if isinstance(x[k], float) else x[k]) for k in ("n", "usd_mes", "sharpe", "pct_anios_pos", "R_op", "sharpe_2022", "usd_mes_2022")})
            print("    ops/año", x["ops_por_anio"]); print("    riesgo mediano", {k: round(v_) for k, v_ in x["riesgo_mediano_por_anio"].items()})


if __name__ == "__main__":
    {"correr": correr, "leer": leer}[sys.argv[1]]()
