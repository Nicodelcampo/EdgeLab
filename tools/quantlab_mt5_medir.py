#!/usr/bin/env python3
"""SessionOpenMomentum (traducción QuantLab MT5) en NQ/ES/YM con costos canónicos y en R (docs/research/quantlab_mt5_eas_20261116/PREREGISTRO_MEDICION.md).

  python tools/quantlab_mt5_medir.py <carpeta M1>   # -> docs/research/quantlab_mt5_eas_20261116/RESULTADO_SOM.json
Reusa quantlab_mt5 (motor y cargador), reels_20261116.tramo (estadística por tramo) y fundedsync_tanda2._bh.
"""
import json, sys
from dataclasses import replace
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from reels_20261116 import tramo, A, B, REC  # noqa: E402
from fundedsync_tanda2 import _bh  # noqa: E402
OUT = ROOT / "docs/research/quantlab_mt5_eas_20261116"
FUENTES = {"NQ": ("NQ_M1_dukas", "USATECH"), "ES": ("SP_M1_dukas", "USA500"), "YM": ("DJ_M1_dukas", "USA30")}


def riesgo_inicial(df, T, cfg):
    """8 × ATR14 M5 de la vela de señal (la anterior a la entrada), con los mismos indicadores del motor."""
    from edgelab.research.quantlab_mt5.indicators import mql5_atr, resample_ohlc
    m5 = resample_ohlc(df, 5); atr = mql5_atr(m5.high.to_numpy(float), m5.low.to_numpy(float), m5.close.to_numpy(float), cfg.atr_period)
    k = np.searchsorted(m5.ts_ns.to_numpy(np.int64), T.entry_time_utc.to_numpy(np.int64), side="left") - 1
    return cfg.sl_atr_mult * atr[np.clip(k, 0, len(atr) - 1)]


def main(carpeta):
    from edgelab.research.quantlab_mt5 import load_ohlc_data, correr_session_open_momentum
    from edgelab.research.quantlab_mt5.contracts import SessionOpenMomentumConfig
    from edgelab.research.embudo_runners import friccion
    res = dict(preregistro="docs/research/quantlab_mt5_eas_20261116/PREREGISTRO_MEDICION.md", pruebas={}); claves = []
    for inst, (arch, spec) in FUENTES.items():
        df = load_ohlc_data(Path(carpeta) / f"{arch}.csv", start="2012-01-20"); fr = friccion(inst)[0]
        for celda, cfg in (("sin_eod", SessionOpenMomentumConfig()), ("eod", replace(SessionOpenMomentumConfig(), close_eod=True))):
            T = correr_session_open_momentum(df, config=cfg, instrument=spec)
            rg = riesgo_inicial(df, T, cfg)
            g = pd.DataFrame(dict(fecha=pd.to_datetime(T.entry_time_utc, unit="ns").dt.strftime("%Y%m%d").astype(int), riesgo=rg, bruto=T.pnl_pts.to_numpy(float),
                                  salida=T.exit_name.values, horas=(T.exit_time_utc - T.entry_time_utc).to_numpy(float) / 3.6e12))
            g = g[g.riesgo > 0]; g["dia"] = pd.to_datetime(g.fecha.astype(str)); g["neto"] = g.bruto - fr; g["R"] = g.neto / g.riesgo; g["Rb"] = g.bruto / g.riesgo; g["fricR"] = fr / g.riesgo
            k = f"SOM|{celda}|{inst}"; claves.append(k)
            res["pruebas"][k] = dict(A=tramo(g, *A), B=tramo(g, *B), reciente=tramo(g, *REC), n=int(len(g)), horas_mediana=float(g.horas.median()),
                                     salidas=g.salida.value_counts().to_dict(), cruza_finde=float((g.horas > 60).mean()))
            r = res["pruebas"][k]; print(k, {t: (r[t]["n"], r[t].get("R") and round(r[t]["R"], 3), r[t].get("p") and round(r[t]["p"], 3), r[t].get("fric_med") and round(r[t]["fric_med"], 3)) for t in ("A", "B", "reciente")}, flush=True)
    bh = _bh([res["pruebas"][k]["B"].get("p", 1.0) for k in claves])
    for k, b in zip(claves, bh):
        r = res["pruebas"][k]; ok = lambda t: t.get("R") is not None and t["R"] > 0 and not t.get("no_evaluable")
        r.update(nominada_bh=bool(b), pasa=bool(b and ok(r["A"]) and ok(r["B"]) and r["B"].get("fric_med", 9) <= 0.08), regimen_reciente=bool(ok(r["B"]) and not ok(r["A"])))
    (OUT / "RESULTADO_SOM.json").write_text(json.dumps(res, indent=1, default=float)); print({k: (v["pasa"], v["regimen_reciente"]) for k, v in res["pruebas"].items()})


if __name__ == "__main__":
    main(sys.argv[1])
