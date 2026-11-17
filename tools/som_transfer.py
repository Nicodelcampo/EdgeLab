#!/usr/bin/env python3
"""SOM en la apertura propia de otros mercados (docs/research/som_transfer_20261117/PREREGISTRO.md): RTY 09:30, GC 08:20, 6E 03:00 NY.

  python tools/som_transfer.py <carpeta M1>   # -> docs/research/som_transfer_20261117/RESULTADO.json
Reusa quantlab_mt5 (motor), m1_intradia.leer_m1 (zona horaria declarada), reels_20261116.tramo y fundedsync_tanda2._bh.
"""
import json, sys
from dataclasses import replace
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from reels_20261116 import tramo, REC  # noqa: E402
OUT = ROOT / "docs/research/som_transfer_20261117"
PRUEBAS = {"RTY": ("USSC2000IDXUSD", "09:30", "USA500"), "GC": ("XAUUSD_M1_dukas", "08:20", "XAUUSD"), "6E": ("EURUSD_M1_dukas", "03:00", "EURUSD")}
A, B = ("2012-01-01", "2019-12-31"), ("2020-01-01", "2026-09-29")


def df_servidor(path):
    """M1 → hora del servidor (NY + 7) rotulada UTC, que es lo que espera el motor de SOM (OpenNY en hora del servidor)."""
    from edgelab.research import m1_intradia as M
    D = M.leer_m1(path); D = D[(D.index >= "2011-12-01") & (D.index < "2026-09-30")]; t = (D.index + pd.Timedelta(hours=7)).tz_localize("UTC")
    return pd.DataFrame(dict(time=t, ts_ns=np.asarray((t - pd.Timestamp(0, tz="UTC")) // pd.Timedelta("1ns"), dtype=np.int64),
                             open=D.o.values, high=D.h.values, low=D.l.values, close=D.c.values, volume=D.v.values))


def main(carpeta):
    from edgelab.research.quantlab_mt5 import correr_session_open_momentum
    from edgelab.research.quantlab_mt5.contracts import SessionOpenMomentumConfig
    from edgelab.research.embudo_runners import friccion
    from fundedsync_tanda2 import _bh
    res = dict(preregistro="docs/research/som_transfer_20261117/PREREGISTRO.md", pruebas={}); claves = []
    som = pd.read_csv(ROOT / "docs/research/quantlab_mt5_eas_20261116/SOM_OPS_NQ_sin_finde.csv.gz").groupby("fecha").R.sum()
    for inst, (arch, hora, spec) in PRUEBAS.items():
        df = df_servidor(Path(carpeta) / f"{arch}.csv"); fr = friccion(inst)[0]
        sh, sm = map(int, hora.split(":")); srv = f"{(sh + 7) % 24:02d}:{sm:02d}"
        T = correr_session_open_momentum(df, config=replace(SessionOpenMomentumConfig(), close_weekend=True, open_ny=srv), instrument=spec)
        f = (pd.to_datetime(T.entry_time_utc, unit="ns") - pd.Timedelta(hours=7))
        g = pd.DataFrame(dict(fecha=f.dt.strftime("%Y%m%d").astype(int).values, riesgo=(T.entry_price - T.stop_price).abs().values, bruto=T.pnl_pts.values.astype(float)))
        g = g[g.riesgo > 0]; g["dia"] = pd.to_datetime(g.fecha.astype(str)); g["R"] = (g.bruto - fr) / g.riesgo; g["Rb"] = g.bruto / g.riesgo
        g["neto"] = g.bruto - fr; g["fricR"] = fr / g.riesgo
        yr = g.groupby(g.dia.dt.year).R.sum(); d = g.groupby("fecha").R.sum(); comun = d.index.intersection(som.index)
        r = dict(A=tramo(g, *A), B=tramo(g, *B), reciente=tramo(g, *REC), n=int(len(g)), anios_pos=int((yr > 0).sum()), anios=int(len(yr)),
                 corr_diaria_SOM_NQ=float(np.corrcoef(d.reindex(som.index, fill_value=0), som)[0, 1]))
        res["pruebas"][inst] = r; claves.append(inst); g.to_csv(OUT / f"OPS_{inst}.csv.gz", index=False)
        print(inst, hora, {k: (r[k]["n"], r[k].get("R") and round(r[k]["R"], 3), r[k].get("p") and round(r[k]["p"], 3), r[k].get("fric_med") and round(r[k]["fric_med"], 3)) for k in ("A", "B", "reciente")},
              "años+", r["anios_pos"], "/", r["anios"], "corr SOM", round(r["corr_diaria_SOM_NQ"], 2), flush=True)
    for k, b in zip(claves, _bh([res["pruebas"][k]["B"].get("p", 1.0) for k in claves])):
        r = res["pruebas"][k]; okA = r["A"].get("no_evaluable") or (r["A"].get("R") or -1) > 0
        r.update(nominada_bh=bool(b), pasa=bool(b and okA and (r["B"].get("R") or -1) > 0 and r["B"].get("fric_med", 9) <= 0.08))
    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1, default=float)); print({k: v["pasa"] for k, v in res["pruebas"].items()})


if __name__ == "__main__":
    main(sys.argv[1])
