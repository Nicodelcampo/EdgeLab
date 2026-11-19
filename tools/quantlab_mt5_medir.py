#!/usr/bin/env python3
"""SessionOpenMomentum (traducción QuantLab MT5) en NQ/ES/YM con costos canónicos y en R (docs/research/quantlab_mt5_eas_20261116/PREREGISTRO_MEDICION.md).

  python tools/quantlab_mt5_medir.py <carpeta M1>   # -> docs/research/quantlab_mt5_eas_20261116/RESULTADO_SOM.json
Reusa quantlab_mt5 (motor y cargador), reels_20261116.tramo (estadística por tramo); riesgo = |entrada − stop inicial| y fundedsync_tanda2._bh.
"""
import json, sys
from dataclasses import replace
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from reels_20261116 import tramo, A, B, REC  # noqa: E402
from fundedsync_tanda2 import _bh  # noqa: E402
OUT = ROOT / "docs/research/quantlab_mt5_eas_20261116"
FUENTES = {"NQ": ("NQ_M1_dukas", "USATECH"), "ES": ("SP_M1_dukas", "USA500"), "YM": ("DJ_M1_dukas", "USA500")}          # YM: preset de redondeo de USA500 (sólo afecta USD y redondeo a 0,01)


def ops_som(df, cfg, spec, fr) -> pd.DataFrame:
    """Operaciones de SOM en R (riesgo = |entrada − stop inicial|, neto = bruto − fricción canónica en puntos)."""
    from edgelab.research.quantlab_mt5 import correr_session_open_momentum
    T = correr_session_open_momentum(df, config=cfg, instrument=spec)
    rg = (T.entry_price - T.stop_price).abs().to_numpy(float)                 # stop_price = stop inicial (1 R) en el motor
    g = pd.DataFrame(dict(fecha=pd.to_datetime(T.entry_time_utc, unit="ns").dt.strftime("%Y%m%d").astype(int), riesgo=rg, bruto=T.pnl_pts.to_numpy(float),
                          salida=T.exit_name.values, horas=(T.exit_time_utc - T.entry_time_utc).to_numpy(float) / 3.6e12,
                          lado=T.side.values))                                   # 2026-11-19 (MEJORA-SF): lado, para filtros por dirección
    g = g[g.riesgo > 0]; g["dia"] = pd.to_datetime(g.fecha.astype(str)); g["neto"] = g.bruto - fr; g["R"] = g.neto / g.riesgo; g["Rb"] = g.bruto / g.riesgo; g["fricR"] = fr / g.riesgo
    return g


def main(carpeta):
    from edgelab.research.quantlab_mt5 import load_ohlc_data
    from edgelab.research.quantlab_mt5.contracts import SessionOpenMomentumConfig
    from edgelab.research.embudo_runners import friccion
    res = dict(preregistro="docs/research/quantlab_mt5_eas_20261116/PREREGISTRO_MEDICION.md", pruebas={}); claves = []
    for inst, (arch, spec) in FUENTES.items():
        df = load_ohlc_data(Path(carpeta) / f"{arch}.csv", start="2012-01-20"); fr = friccion(inst)[0]
        for celda, cfg in (("sin_eod", SessionOpenMomentumConfig()), ("eod", replace(SessionOpenMomentumConfig(), close_eod=True)),
                           ("sin_finde", replace(SessionOpenMomentumConfig(), close_weekend=True))):                    # enmienda 2
            g = ops_som(df, cfg, spec, fr)
            k = f"SOM|{celda}|{inst}"; claves.append(k)
            if inst == "NQ": g.assign(celda=celda).to_csv(OUT / f"SOM_OPS_NQ_{celda}.csv.gz", index=False)
            res["pruebas"][k] = dict(A=tramo(g, *A), B=tramo(g, *B), reciente=tramo(g, *REC), n=int(len(g)), horas_mediana=float(g.horas.median()),
                                     salidas=g.salida.value_counts().to_dict(), cruza_finde=float((g.horas > 60).mean()))
            r = res["pruebas"][k]; print(k, {t: (r[t]["n"], r[t].get("R") and round(r[t]["R"], 3), r[t].get("p") and round(r[t]["p"], 3), r[t].get("fric_med") and round(r[t]["fric_med"], 3)) for t in ("A", "B", "reciente")}, flush=True)
    orig = [k for k in claves if "sin_finde" not in k]; bh = dict(zip(orig, _bh([res["pruebas"][k]["B"].get("p", 1.0) for k in orig])))
    for k in claves:
        b = bh.get(k, res["pruebas"][k]["B"].get("p", 1.0) < 0.10)                # sin_finde: prueba única (enmienda 2)
        r = res["pruebas"][k]; ok = lambda t: t.get("R") is not None and t["R"] > 0 and not t.get("no_evaluable")
        r.update(nominada_bh=bool(b), pasa=bool(b and ok(r["A"]) and ok(r["B"]) and r["B"].get("fric_med", 9) <= 0.08), regimen_reciente=bool(ok(r["B"]) and not ok(r["A"])))
    (OUT / "RESULTADO_SOM.json").write_text(json.dumps(res, indent=1, default=float)); print({k: (v["pasa"], v["regimen_reciente"]) for k, v in res["pruebas"].items()})


if __name__ == "__main__":
    main(sys.argv[1])
