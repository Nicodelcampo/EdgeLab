#!/usr/bin/env python3
"""CANASTA-CORRELACION (2026-11-20): correlación diaria y mensual entre A20, T, R, Z-banda y RQ5 (fábricas, R neto) y la canasta
conjunta a 1 R por operación. Pre-registro: docs/research/canasta_correlacion_20261120/PREREGISTRO.md. Descriptivo.

  python tools/canasta_correlacion.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/canasta_correlacion_20261120"


def _stats(d: pd.Series) -> dict:
    m = d.groupby(d.index.to_period("M")).sum(); eq = d.cumsum(); dd = float((eq - eq.cummax()).min())
    return dict(R_mes=float(m.mean()), t_mes=float(m.mean() / (m.std(ddof=1) / np.sqrt(len(m)))), pct_meses_pos=float((m > 0).mean()),
                peor_mes=float(m.min()), peor_mes_cual=str(m.idxmin()), max_caida_R=dd, sd_mes=float(m.std(ddof=1)), meses=int(len(m)),
                R_total=float(d.sum()))


def main():
    from registro_global import exigir_contada
    exigir_contada(DIR / "PREREGISTRO.md")
    from filtros_contexto import operaciones
    from m1_largo import cargar
    from datos import ruta
    X = operaciones(); X["fecha"] = pd.to_datetime(X.ses.astype(str))
    X.loc[(X.est == "RQ5") & (X.inst == "NQ"), "est2"] = "RQ5_NQ"
    dias = pd.DatetimeIndex(sorted(X.fecha.unique()))
    S = {e: X[X.est == e].groupby("fecha").R.sum().reindex(dias, fill_value=0.0) for e in ("A20", "T", "R", "ZB", "RQ5")}
    S["RQ5_NQ"] = X[X.est2 == "RQ5_NQ"].groupby("fecha").R.sum().reindex(dias, fill_value=0.0)
    D = pd.DataFrame(S); M = D.groupby(D.index.to_period("M")).sum()
    c = cargar("NQ", ruta("M1NT8")).c.resample("ME").last(); nq = c.pct_change() * 100; nq.index = nq.index.to_period("M")
    M["NQ_%"] = nq.reindex(M.index)
    res = dict(dias=len(D), meses=len(M), ops={e: int((X.est == e).sum()) for e in ("A20", "T", "R", "ZB", "RQ5")} | {"RQ5_NQ": int((X.est2 == "RQ5_NQ").sum())},
               corr_diaria_pearson=D.corr().round(3).to_dict(), corr_diaria_spearman=D.corr("spearman").round(3).to_dict(),
               corr_mensual_pearson=M.corr().round(3).to_dict(), por_estrategia={e: _stats(D[e]) for e in D})
    canastas = {"TODAS_NQ (A20+T+R+ZB+RQ5_NQ)": ["A20", "T", "R", "ZB", "RQ5_NQ"], "SIN_A20_NQ (T+R+ZB+RQ5_NQ)": ["T", "R", "ZB", "RQ5_NQ"],
                "TODAS_RQ5_4IDX (A20+T+R+ZB+RQ5)": ["A20", "T", "R", "ZB", "RQ5"], "CANASTA_B (T+R+ZB)": ["T", "R", "ZB"]}
    res["canastas"] = {}
    for k, cols in canastas.items():
        d = D[cols].sum(1); st = _stats(d); mm = d.groupby(d.index.to_period("M")).sum(); q = M["NQ_%"]
        st["R_mes_por_NQ"] = {"NQ<-3%": float(mm[q < -3].mean()), "-3..+3%": float(mm[(q >= -3) & (q <= 3)].mean()), "NQ>+3%": float(mm[q > 3].mean())}
        res["canastas"][k] = st
    (DIR / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    D.to_csv(DIR / "SERIES_DIARIAS_R.csv.gz")
    print(pd.DataFrame(res["corr_mensual_pearson"]).round(2)); print(pd.DataFrame(res["corr_diaria_pearson"]).round(2))
    print(pd.DataFrame(res["por_estrategia"]).T.round(2)[["R_mes", "t_mes", "pct_meses_pos", "peor_mes", "max_caida_R", "sd_mes"]])
    for k, v in res["canastas"].items(): print(k, {a: (round(b, 2) if isinstance(b, float) else b) for a, b in v.items()})


if __name__ == "__main__":
    main()
