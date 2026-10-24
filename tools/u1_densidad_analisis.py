#!/usr/bin/env python3
"""Análisis B de PREREGISTRO_OOS_FIX27_Y_DENSIDAD_U1.md: ¿las señales U1 por sesión siguen al mercado (rango) o al feed (ticks)?
Target-free. Entrada: U1_DENSIDAD_<desde>_<hasta>.json (señales por trimestre) y _dias.csv (por día). Salida: U1_DENSIDAD_ANALISIS.json.
    python tools/u1_densidad_analisis.py docs/research/areas_expansion_20261022/u1/topes/U1_DENSIDAD_20230101_20260930"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr


def parcial(y, x, z):
    """Spearman parcial de y con x controlando z: correlación de los residuos de los rangos."""
    ry, rx, rz = (rankdata(v) for v in (y, x, z))
    res = lambda a: a - np.polyval(np.polyfit(rz, a, 1), rz)
    return float(np.corrcoef(res(ry), res(rx))[0, 1])


def lectura(r_rt, r_tr):
    if r_rt >= 0.5 and r_tr < 0.5: return "MERCADO"
    if r_tr >= 0.5 and r_rt < 0.5: return "FEED"
    return "INDETERMINADO"


def main(base):
    base = Path(base); J = json.loads(base.with_suffix(".json").read_text()); csv = Path(str(base) + "_dias.csv")
    D = pd.read_csv(csv); D["fecha"] = pd.to_datetime(D.ses.astype(str))
    filas = []
    for q in J["senales_por_trimestre"]:
        g = D[(D.ses >= q["desde"]) & (D.ses <= q["hasta"])]
        if not len(g) or not q.get("sesiones"): continue
        filas.append(dict(trimestre=f"{q['desde'] // 10000}-T{(q['desde'] // 100 % 100 - 1) // 3 + 1}", desde=q["desde"], hasta=q["hasta"],
                          dias=int(len(g)), senales=int(q["senales"]), sesiones=int(q["sesiones"]), senales_por_sesion=q["senales"] / q["sesiones"],
                          ticks_med=float(g.ticks.median()), minutos_med=float(g.minutos.median()), zonas_med=float(g.zonas.median()),
                          rango_med=float(g.rango.median())))
    T = pd.DataFrame(filas); y = T.senales_por_sesion.to_numpy()
    rho = {k: float(spearmanr(y, T[c]).statistic) for k, c in (("rango", "rango_med"), ("ticks", "ticks_med"), ("minutos", "minutos_med"), ("zonas", "zonas_med"))}
    rho["rango_vs_ticks"] = float(spearmanr(T.rango_med, T.ticks_med).statistic)
    r_rt = parcial(y, T.rango_med.to_numpy(), T.ticks_med.to_numpy()); r_tr = parcial(y, T.ticks_med.to_numpy(), T.rango_med.to_numpy())
    T["ticks_vs_2023T1"] = T.ticks_med / T.ticks_med.iloc[0]; T["minutos_vs_2023T1"] = T.minutos_med / T.minutos_med.iloc[0]
    huecos = []
    for r in T.itertuples():
        g = D[(D.ses >= r.desde) & (D.ses <= r.hasta)]
        m = g[(g.minutos < 1000) | (g.ticks < 0.25 * r.ticks_med)]
        huecos += [dict(ses=int(x.ses), ticks=int(x.ticks), minutos=int(x.minutos), trimestre=r.trimestre) for x in m.itertuples()]
    out = dict(analisis="U1-DENSIDAD-B", preregistro="docs/research/areas_expansion_20261022/u1/PREREGISTRO_OOS_FIX27_Y_DENSIDAD_U1.md",
               csv_sha256=hashlib.sha256(csv.read_bytes()).hexdigest(), dias=int(len(D)), por_trimestre=T.round(4).to_dict("records"),
               spearman=rho, parcial_rango_dado_ticks=r_rt, parcial_ticks_dado_rango=r_tr, lectura=lectura(r_rt, r_tr),
               dias_con_hueco=huecos, nota="15 puntos: descriptivo, sin p como evidencia")
    dest = base.parent / "U1_DENSIDAD_ANALISIS.json"; dest.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(T[["trimestre", "senales", "sesiones", "senales_por_sesion", "ticks_med", "minutos_med", "zonas_med", "rango_med"]].round(3).to_string(index=False))
    print(json.dumps(dict(spearman=rho, parcial_R_T=r_rt, parcial_T_R=r_tr, lectura=out["lectura"], n_dias_hueco=len(huecos)), indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
