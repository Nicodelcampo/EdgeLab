"""Matriz diaria de P&L por estrategia y activo, 1 micro, costos canónicos de micros (pre-registro
`docs/research/cartera_nt8_20261125/PREREGISTRO_MULTIACTIVO_Y_GESTION.md`).

Fuente: operaciones del motor EdgeLabCartera en modo broker (tools/nt8_cartera_paridad.py), carpetas
docs/research/cartera_nt8_20261125/{paridad_intradia,paridad_interdia,multiactivo}/broker_<RAIZ>.csv.
P&L de una operación en micros = (pnl_pts - fricción del micro en puntos) x valor del punto del micro; se imputa a la sesión de la
salida (cuentas con drawdown de fin de día). Las de varios días (C2_VZ, SOM sin_finde) se imputan al cierre: aproximación declarada.

  python tools/cartera_matriz_diaria.py   # -> docs/research/cartera_nt8_20261125/MATRIZ_DIARIA_1MICRO.csv(.gz) y PARTE_A_MULTIACTIVO.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab import costos  # noqa: E402

D = ROOT / "docs" / "research" / "cartera_nt8_20261125"
MICRO = {"NQ": "MNQ", "ES": "MES", "YM": "MYM", "RTY": "M2K", "GC": "MGC"}
CORTO = {"T_stop100_BE15R_calFalse": "T", "R_osc30_end660_ATR50": "R", "Z_b15_e20_eff40_ATR50": "Z", "V_nm25_noCap_mae30": "V",
         "SOM_sin_finde": "SOMSF", "RQ5": "RQ5", "FRANKLIN": "FR", "ES5N": "ES5N", "C2_VZ": "C2VZ"}
FUENTES = [("paridad_intradia", None), ("paridad_interdia", {"SOM_sin_finde", "C2_VZ"}), ("multiactivo", None)]
BASE = ["T_NQ", "R_NQ", "Z_NQ", "V_NQ", "RQ5_NQ", "FR_NQ", "RQ5_ES", "ES5N_ES"]
NUEVAS = ["RQ5_YM", "RQ5_RTY", "RQ5_GC", "FR_ES", "FR_YM", "FR_RTY", "FR_GC", "ES5N_NQ", "ES5N_YM", "ES5N_RTY", "ES5N_GC", "T_ES", "R_ES"]
DESDE, HASTA = "2019-07-01", "2026-09-29"


def operaciones() -> pd.DataFrame:
    partes = []
    with costos.estimados_permitidos("docs/research/cartera_nt8_20261125/PREREGISTRO_MULTIACTIVO_Y_GESTION.md (M2K estimado)"):
        fr = {m: costos.friccion_rt_puntos(m, "base") for m in MICRO.values()}
    for carpeta, solo in FUENTES:
        for f in sorted((D / carpeta).glob("broker_*.csv*")):
            raiz = f.name.split("_", 1)[1].split(".")[0]
            o = pd.read_csv(f)
            if solo: o = o[o.modulo.isin(solo)]
            mic = MICRO[raiz]; pv = costos.tick_value_usd(mic) / costos.tick_size(mic)
            o = o.assign(serie=o.modulo.map(CORTO) + "_" + raiz, usd=(o.pnl_pts - fr[mic]) * pv,
                         R=(o.pnl_pts - fr[mic]) / o.riesgo_pts, stop_usd=o.riesgo_pts * pv,
                         dia=pd.to_datetime(o.ex_ny).dt.normalize())
            partes.append(o)
    o = pd.concat(partes, ignore_index=True)
    o = o.drop_duplicates(subset=["serie", "en_ny"])
    return o[(o.dia >= DESDE) & (o.dia <= HASTA)]


def main() -> int:
    o = operaciones()
    dias = pd.bdate_range(DESDE, HASTA)
    M = o.pivot_table(index="dia", columns="serie", values="usd", aggfunc="sum").reindex(dias).fillna(0.0)
    M.index.name = "dia"
    M.round(2).to_csv(D / "MATRIZ_DIARIA_1MICRO.csv.gz")
    base = M[BASE].sum(axis=1)
    mb = base.groupby(base.index.to_period("M")).sum()
    res = {"series": {}}
    for s in sorted(M.columns):
        g = o[o.serie == s]; x = M[s]; ms = x.groupby(x.index.to_period("M")).sum()
        res["series"][s] = dict(ops=len(g), ops_mes=round(len(g) / (len(dias) / 21), 2), R_op=round(float(g.R.mean()), 4),
                               usd_dia=round(float(x.mean()), 2), sd_dia=round(float(x.std()), 1), stop_usd_mediano=round(float(g.stop_usd.median()), 1),
                               corr_diaria_base=round(float(np.corrcoef(x, base)[0, 1]), 3) if s not in BASE else None,
                               corr_mensual_base=round(float(np.corrcoef(ms, mb)[0, 1]), 3) if s not in BASE else None,
                               usd_mes_en_meses_malos_base=round(float(ms[mb < 0].mean()), 1),
                               usd_mes_en_meses_buenos_base=round(float(ms[mb >= 0].mean()), 1),
                               por_anio={str(a): round(float(v), 0) for a, v in x.groupby(x.index.year).sum().items()})
    res["base"] = dict(usd_dia=round(float(base.mean()), 1), sd_dia=round(float(base.std()), 1), meses_malos=int((mb < 0).sum()), meses=len(mb))
    (D / "PARTE_A_SERIES.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250)
    t = pd.DataFrame(res["series"]).T[["ops_mes", "R_op", "usd_dia", "sd_dia", "stop_usd_mediano", "corr_diaria_base", "corr_mensual_base",
                                       "usd_mes_en_meses_malos_base", "usd_mes_en_meses_buenos_base"]]
    print(t.to_string()); print(res["base"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
