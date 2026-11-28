#!/usr/bin/env python3
"""Auditoría Claude 2026-11-28 de la Espiral (Antigravity): re-mide CARRIL2_VOL_LOCAL sólo con meses DESC+REP de A5.

La corrida original (`tools/carril2_vol_local_20261127.py`) leyó todos los meses < 2026-10-01, incluidos los HOLDOUT de A5, en Dow,
Russell 2000 y GC (instrumentos que equivalen a YM, RTY y GC del universo de Carril 2, cuya familia ya usó su única apertura). Acá se
reutilizan sus mismas funciones y pares; lo único que cambia es la máscara: entrada y salida en meses DESC o REP (K64).

    python tools/auditoria_espiral_20261128.py
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab.holdout import a5_bloque  # noqa: E402
import carril2_vol_local_20261127 as VL  # noqa: E402

OUT = ROOT / "docs/research/auditoria_claude_20261128"


def _ok(f: int) -> bool:
    return a5_bloque(int(f)) in ("DESC", "REP")


def main() -> int:
    import confianza_sin_forward as CSF
    cboe = pd.read_parquet(Path(VL.ruta("M1NT8")) / "cboe_volatility_daily.parquet"); cboe.index = pd.to_datetime(cboe.index).normalize()
    # ASX200 queda afuera: no es del universo de Carril 2 (la lectura de todos sus meses no toca un holdout de la familia).
    pares = [("Dow", CSF._barras("Dow"), None, cboe["vxd_close"], cboe["vix_close"], 3.0, None, 20060103),
             ("Russell2000", CSF._barras("Russell2000"), None, cboe["rvx_close"], cboe["vix_close"], 3.0, None, 20060103),
             ("GC", None, True, cboe["gvz_close"], cboe["vix_close"], None, float(VL.friccion("GC")[0]), 20080603)]
    res = {}
    agg = {}
    for inst, B, use_m1, iv_loc, iv_us, bps, fr, min_d in pares:
        m1 = None
        if use_m1:
            D = VL.cargar("GC", VL.ruta("M1NT8")); B = VL.Q.barras_desde_m1(D, "D1"); m1 = VL.Q.indices_m1(B, D, "D1")
        fechas = B[(B["fecha"] >= min_d) & (B["fecha"] < VL.CORTE_INT)]["fecha"]
        fechas = fechas[[_ok(x) for x in fechas]]
        meses = pd.to_datetime(fechas.astype(str)).dt.to_period("M").unique()
        for modo, iv in (("LOCAL", iv_loc), ("VIX_EEUU", iv_us)):
            T = VL._eval_pair(B, m1, iv, bps, fr, min_d)
            T = T[[_ok(a) and _ok(b) for a, b in zip(T["fecha"], T["fecha_sal"])]].copy()
            T["mes"] = pd.to_datetime(T["fecha"].astype(str)).dt.to_period("M")
            for r in ("C2_VBB", "C2_VZ_1F", "C2_EVRP_1F"):
                mr = T[T.definicion == r].groupby("mes")["R"].sum().reindex(meses).fillna(0.0)
                mc = T[T.definicion == r + "N"].groupby("mes")["R"].sum().reindex(meses).fillna(0.0)
                d = mr - mc
                res[f"{inst}|{modo}|{r}"] = dict(meses=len(meses), regla=VL._stats(mr), diff=VL._stats(d))
                agg.setdefault((modo, r), []).append(d.rename(inst))
    resumen = {}
    for (modo, r), lst in agg.items():
        D = pd.concat(lst, axis=1).mean(axis=1, skipna=True)
        resumen[f"{modo}|{r}"] = VL._stats(D)
    (OUT / "CARRIL2_VOL_LOCAL_SIN_HOLDOUT.json").write_text(json.dumps(dict(resumen=resumen, por_par=res), indent=1, default=str), encoding="utf-8")
    print(json.dumps(resumen, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
