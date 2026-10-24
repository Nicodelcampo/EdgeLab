#!/usr/bin/env python3
"""Evaluación A de PREREGISTRO_OOS_FIX27_Y_DENSIDAD_U1.md: OOS de U1-CRUZADO en USATECH 2023-01 → 2025-07 con el fix 27.
Une los dos tramos, resume por ejecución (bootstrap por sesiones), MDE, riesgo y por año; decide en el MISMO paso 3 de LORD++
de la corrida descartada (se reconstruye desde oos_eval.json sin ese paso); compara operación por operación contra la descartada.
    python tools/u1_oos_fix27_eval.py docs/research/areas_expansion_20261022/u1/integridad_oos"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.funnel.escalera import LordPP, mde, probar_lote, resumen_sesiones  # noqa: E402

TRAMOS = ("20230101_20240331", "20240401_20250731")


def riesgo(g):
    x = g.sort_values("t").neto.dropna(); eq = x.cumsum(); racha = (x < 0).astype(int).groupby((x >= 0).cumsum()).sum().max()
    return dict(drawdown_max=float((eq - eq.cummax()).min()), peor_dia=float(g.groupby("ses").neto.sum().min()), peor_racha=int(racha),
                p01=float(x.quantile(0.01)), total=float(x.sum()))


def main(d):
    d = Path(d)
    nuevo = pd.concat([pd.read_csv(d / f"U1_OOS_US_FIX27_{t}_operaciones.csv") for t in TRAMOS]).dropna(subset=["neto"])
    viejo = pd.concat([pd.read_csv(d / f"U1_OOS_US_{t}_operaciones.csv") for t in TRAMOS]).dropna(subset=["neto"])
    filas, pruebas = {}, []
    for ej, g in nuevo.groupby("ejecucion"):
        rs = resumen_sesiones(g.neto.to_numpy(float), g.ses.to_numpy())
        anio = g.groupby(g.ses // 10000).neto.agg(["count", "mean"])
        filas[ej] = dict(n=rs["n_ops"], sesiones=rs["n_sesiones"], media=rs["media"], mediana=float(g.neto.median()), se=rs["se"], ic90=rs["ic"],
                         p=rs["p_unilateral"], mde=mde(rs["se"]), acierto=float((g.neto > 0).mean()), peor=float(g.neto.min()), riesgo=riesgo(g),
                         por_anio={int(k): dict(n=int(v["count"]), media=float(v["mean"])) for k, v in anio.iterrows()})
        pruebas.append((ej, rs["p_unilateral"]))
    previo = json.loads((d / "oos_eval.json").read_text())["lord"]
    L = LordPP.from_dict(dict(previo, t=2, historia=previo["historia"][:2], rechazos=[r for r in previo["rechazos"] if r <= 2]))
    lote = probar_lote(L, pruebas, "U1-CRUZADO OOS USATECH 2023-2025 con fix 27 (reemplaza la corrida descartada en el paso 3)")
    m = nuevo.merge(viejo[["k_us", "ejecucion", "neto"]], on=["k_us", "ejecucion"], how="outer", suffixes=("_fix27", "_descartada"), indicator=True)
    dif = (m.neto_fix27 - m.neto_descartada).dropna()
    comp = dict(solo_fix27=int((m._merge == "left_only").sum()), solo_descartada=int((m._merge == "right_only").sum()), comunes=int(len(dif)),
                cambiadas=int((dif.abs() > 1e-9).sum()), dif_media=float(dif.mean()) if len(dif) else None,
                dif_min=float(dif.min()) if len(dif) else None, dif_max=float(dif.max()) if len(dif) else None,
                media_descartada={ej: float(g.neto.mean()) for ej, g in viejo.groupby("ejecucion")})
    rech_desc = bool(previo["historia"][2]["rechazo"])
    lectura = ("NO_CONCLUYENTE (discrepa con la descartada)" if lote["rechazo"] != rech_desc else
               "CONFIRMA" if lote["rechazo"] else
               "CONSISTENTE SIN POTENCIA" if all(f["media"] > 0 for f in filas.values()) else "NO FUNCIONABA EN 2023-2025 (media <= 0 en alguna ejecución)")
    out = dict(evaluacion="U1-OOS-USATECH-FIX27", preregistro="docs/research/areas_expansion_20261022/u1/PREREGISTRO_OOS_FIX27_Y_DENSIDAD_U1.md",
               filas=filas, lote=lote, lord=L.to_dict(), contra_descartada=comp, lectura=lectura)
    (d / "oos_eval_fix27.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main(sys.argv[1])
