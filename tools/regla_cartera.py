#!/usr/bin/env python3
"""REGLA-CARTERA (2026-11-26): regla fija de construcción de cartera por suma de estrategias decorrelacionadas (elegible t ≥ 1,5 y ≥ 60 %
de años +; orden por t; correlación ≤ 0,4 con la cartera y ≤ 0,6 con cada miembro; riesgo parejo). Validación: selección 2019-07 → 2023-06,
evaluación 2023-07 → 2026-09. Pre-registro: docs/research/regla_cartera_20261126/PREREGISTRO.md.   python tools/regla_cartera.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/regla_cartera_20261126"
NOCHE = ("SOMSF", "C2VZ", "C2EVRP", "FS_O_")
INTRA8 = ["T_NQ", "R_NQ", "Z_NQ", "V_NQ", "RQ5_NQ", "FR_NQ", "RQ5_ES", "ES5N_ES"]
INTER3 = ["SOMSF_NQ", "C2VZ_NQ", "C2VZ_ES"]


def _m(x): return x.groupby(x.index.to_period("M")).sum()


def _st(x):
    m = _m(x); eq = x.cumsum(); a = x.groupby(x.index.year).sum()
    return dict(usd_mes=float(m.mean()), t_mes=float(m.mean() / (m.std(ddof=1) / np.sqrt(len(m)))) if m.std() > 0 else 0.0,
                sharpe=float(m.mean() / m.std(ddof=1) * np.sqrt(12)) if m.std() > 0 else 0.0, pct_meses_pos=float((m > 0).mean()),
                pct_anios_pos=float((a > 0).mean()), caida_max=float((eq - eq.cummax()).min()), peor_mes=float(m.min()), meses=int(len(m)))


def regla(X: pd.DataFrame) -> tuple[list, dict]:
    st = {c: _st(X[c]) for c in X.columns}
    eleg = sorted([c for c in X.columns if st[c]["t_mes"] >= 1.5 and st[c]["pct_anios_pos"] >= 0.6], key=lambda c: -st[c]["t_mes"])
    M = _m(X); sel = []
    for c in eleg:
        if not sel: sel.append(c); continue
        cp = M[c].corr(M[sel].sum(axis=1)); cm = max(M[c].corr(M[s]) for s in sel)
        if cp <= 0.4 and cm <= 0.6: sel.append(c)
    sd = M[sel].std(); w = (1 / sd); w = w / w.mean()
    return sel, w.to_dict()


def main():
    from registro_global import exigir_contada
    exigir_contada(DIR / "PREREGISTRO.md")
    X = pd.read_csv(ROOT / "docs/research/estabilidad_cartera_20261126/SERIES_DIARIAS.csv.gz", index_col=0, parse_dates=True)
    X = X.loc[:, X.notna().all()]                                     # cobertura completa (fuera Carril 2 sólo DESC/REP)
    uni = {"INTRADIA": [c for c in X.columns if not c.startswith(NOCHE)], "MIXTO": list(X.columns)}
    base = {"INTRADIA": INTRA8, "MIXTO": INTRA8 + INTER3}
    sel_ini, ev_ini = ("2019-07-01", "2023-06-30"), ("2023-07-01", "2026-09-30")
    res = {}
    for u, cols in uni.items():
        S = X[cols]; A = S.loc[sel_ini[0]:sel_ini[1]]; E = S.loc[ev_ini[0]:ev_ini[1]]
        sel, w = regla(A); ws = pd.Series(w)
        r = dict(seleccion_2019_2023=sel, pesos=w,
                 validacion_regla_riesgo_parejo=_st((E[sel] * ws).sum(axis=1)), validacion_regla_1micro=_st(E[sel].sum(axis=1)),
                 validacion_cartera_actual=_st(X[base[u]].loc[ev_ini[0]:ev_ini[1]].sum(axis=1)))
        sel_t, w_t = regla(S); wt = pd.Series(w_t); mic = wt.round().clip(lower=1).astype(int)
        r.update(toda_ventana_seleccion=sel_t, toda_ventana_pesos=w_t, toda_ventana_micros=mic.to_dict(),
                 toda_ventana_riesgo_parejo=_st((S[sel_t] * wt).sum(axis=1)), toda_ventana_micros_enteros=_st((S[sel_t] * mic).sum(axis=1)),
                 toda_ventana_1micro=_st(S[sel_t].sum(axis=1)), toda_ventana_actual=_st(X[base[u]].sum(axis=1)))
        res[u] = r
        pd.DataFrame({"regla_validacion": (E[sel] * ws).sum(axis=1), "actual_validacion": X[base[u]].loc[ev_ini[0]:ev_ini[1]].sum(axis=1)}).to_csv(DIR / f"VALIDACION_{u}.csv.gz")
        pd.DataFrame({"regla_toda": (S[sel_t] * wt).sum(axis=1), "regla_toda_micros": (S[sel_t] * mic).sum(axis=1), "actual": X[base[u]].sum(axis=1)}).to_csv(DIR / f"TODA_{u}.csv.gz")
    (DIR / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    for u, r in res.items():
        print("==", u); print(" selección 2019-23:", r["seleccion_2019_2023"])
        for k in ("validacion_regla_riesgo_parejo", "validacion_regla_1micro", "validacion_cartera_actual"):
            print(" ", k, {a: round(b, 2) for a, b in r[k].items()})
        print(" toda la ventana:", r["toda_ventana_seleccion"], r["toda_ventana_micros"])
        for k in ("toda_ventana_riesgo_parejo", "toda_ventana_micros_enteros", "toda_ventana_actual"):
            print(" ", k, {a: round(b, 2) for a, b in r[k].items()})


if __name__ == "__main__":
    main()
