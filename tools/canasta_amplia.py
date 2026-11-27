#!/usr/bin/env python3
"""CANASTA-AMPLIA (2026-11-27): la ventaja medida a nivel canasta, donde el N de operaciones y el N de estrategias se suman
(pedido de Nico: «el n diluye las exigencias tanto en nuestra como en cantidad de estrategias»).

  python tools/canasta_amplia.py explorar   # → docs/research/canasta_amplia_20261127/EXPLORACION.json (registro posterior, EF2)

Fases:
  1. Encogimiento: en el pozo de 100 series CME (estabilidad_cartera_20261126/SERIES_DIARIAS), con las que tienen los tres bloques A5,
     cuánto del Sharpe de DESC se conserva en REP y en HOLDOUT (pendiente b), por grupo de selección.
  2. Canasta por regla fija (DESC > 0, pesos 1/sd mensual de DESC) fuera del bloque donde se eligió.
  3. Pozos con HOLDOUT A5 sellado (Carril 2, barrido multiactivo de Kaggle, cripto): la misma canasta en DESC y REP y la potencia de una
     lectura única del HOLDOUT A5.
  4. Carril 2 como canasta: concentración por regla e instrumento, sin cada regla, y combinación con la canasta intradía.
Nada de esto lee meses HOLDOUT de las familias selladas (Carril 2 filtra en origen; Kaggle y cripto guardan NaN).
"""
from __future__ import annotations

import json
import sys
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab.holdout import a5_bloque  # noqa: E402

OUT = ROOT / "docs" / "research" / "canasta_amplia_20261127"
POZO = ROOT / "docs/research/estabilidad_cartera_20261126/SERIES_DIARIAS.csv.gz"
Phi = lambda z: 0.5 * (1 + erf(z / sqrt(2)))


def _blq(idx: pd.DatetimeIndex) -> pd.Series:
    return pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in idx], index=idx)


def _mens(s):
    return s.groupby(s.index.to_period("M")).sum()


def _est(s: pd.Series) -> dict:
    m = _mens(s)
    if len(m) < 3 or m.std() == 0:
        return dict(meses=int(len(m)))
    return dict(meses=int(len(m)), sharpe=round(float(m.mean() / m.std() * np.sqrt(12)), 2),
                t=round(float(m.mean() / (m.std() / np.sqrt(len(m)))), 2), pct_meses_pos=round(float((m > 0).mean()), 2))


def _canasta(S: pd.DataFrame, b: pd.Series, cols) -> pd.Series:
    sd = _mens(S.loc[b == "DESC", cols]).std().replace(0, np.nan)
    w = (1 / sd).fillna(0); w = w / w[w > 0].mean()
    return (S[cols].fillna(0) * w).sum(axis=1)


def fase1_2() -> dict:
    X = pd.read_csv(POZO, index_col=0, parse_dates=True); X = X[X.index < "2026-10-01"]; b = _blq(X.index)
    filas = {}
    for c in X.columns:
        r = {}
        for k in ("DESC", "REP", "HOLDOUT"):
            s = X.loc[b == k, c].dropna()
            if len(s) == 0 or (s == 0).all():
                continue
            m = _mens(s); r[k] = (float(m.mean()), float(m.std()), float(m.mean() / (m.std() / np.sqrt(len(m)))) if m.std() > 0 else 0.0)
        filas[c] = r
    ok = [c for c, r in filas.items() if all(k in r for k in ("DESC", "REP", "HOLDOUT"))]
    sh = {k: np.array([filas[c][k][0] / filas[c][k][1] for c in ok]) for k in ("DESC", "REP", "HOLDOUT")}
    pend = {f"{a}->{z}": round(float(np.cov(sh[a], sh[z])[0, 1] / np.var(sh[a], ddof=1)), 2) for a, z in (("DESC", "REP"), ("DESC", "HOLDOUT"))}
    grupos = {}
    for lab, f in (("todas", lambda c: True), ("DESC>0", lambda c: filas[c]["DESC"][0] > 0), ("DESC_t>1", lambda c: filas[c]["DESC"][2] > 1),
                   ("DESC_t>2", lambda c: filas[c]["DESC"][2] > 2), ("DESC<=0", lambda c: filas[c]["DESC"][0] <= 0)):
        sel = [c for c in ok if f(c)]
        P = _canasta(X, b, sel)
        grupos[lab] = dict(n=len(sel), rep_pos=round(float(np.mean([filas[c]["REP"][0] > 0 for c in sel])), 2),
                           holdout_pos=round(float(np.mean([filas[c]["HOLDOUT"][0] > 0 for c in sel])), 2),
                           canasta_REP=_est(P[b == "REP"]), canasta_HOLDOUT=_est(P[b == "HOLDOUT"]))
    return dict(series_pozo=len(filas), series_3_bloques=len(ok), pendiente_sharpe=pend, grupos=grupos)


def _carril2() -> pd.DataFrame:
    C = pd.concat([pd.read_csv(ROOT / f"docs/research/carril2_extension_20261126/OPS_LOTE{k}.csv.gz") for k in (1, 2)])
    C = C[~C.definicion.str.endswith("N")]                                     # los «N» son los controles, no estrategias
    C["dia"] = pd.to_datetime(C.fecha.astype(str)); C["k"] = C.definicion + "_" + C.inst
    return C.pivot_table(index="dia", columns="k", values="R", aggfunc="sum").fillna(0.0)


def fase3_4() -> dict:
    out = {}
    S1 = _carril2(); b1 = _blq(S1.index)
    inc = [c for c in S1.columns if _mens(S1.loc[b1 == "DESC", c]).mean() > 0]
    K = pd.read_csv(ROOT / "docs/research/auditoria_cartera_20261126/kaggle_m1_out/KAGGLE_M1_DAILY_DR.csv.gz", index_col=0, parse_dates=True)
    J = json.loads((ROOT / "docs/research/auditoria_cartera_20261126/kaggle_m1_out/KAGGLE_M1_EXPANSION.json").read_text())["candidates"]
    S2 = K[[c for c in K.columns if c in J and J[c]["DESC"]["usd_mes"] > 0]].fillna(0.0)
    S3 = pd.read_csv(ROOT / "docs/research/cripto_pit_20261127/SERIES_DESC_REP_BASE.csv.gz", index_col=0, parse_dates=True)[
        ["CR_Donchian_1D", "CR_Trend_4H_EMA", "CR_XSMOM_Neutral"]].fillna(0.0)
    pozos = {}
    for nom, S, cols in (("CARRIL2", S1, inc), ("KAGGLE_MULTIACTIVO", S2, list(S2.columns)), ("CRIPTO", S3, list(S3.columns))):
        b = _blq(S.index); P = _canasta(S, b, cols)
        d, r = _est(P[b == "DESC"]), _est(P[b == "REP"])
        rango = pd.period_range(S.index.min(), "2026-09", freq="M")
        nh = sum(1 for p in rango if a5_bloque(int((p.start_time + pd.Timedelta(days=14)).strftime("%Y%m%d"))) == "HOLDOUT")
        pozos[nom] = dict(n=len(cols), DESC=d, REP=r, meses_holdout_sellado=nh,
                          potencia_lectura_unica={str(f): round(Phi(f * d.get("sharpe", 0) * sqrt(nh / 12) - 1.645), 2) for f in (0.5, 0.7, 1.0)})
    out["pozos_sellados"] = pozos
    # Carril 2: concentración y sin cada regla (REP)
    b1 = _blq(S1.index); sd = _mens(S1.loc[b1 == "DESC", inc]).std(); w = (1 / sd); w = w / w.mean()
    rep = S1.loc[b1 == "REP", inc] * w; tot = float(rep.sum().sum())
    regla = lambda k: "_".join(k.split("_")[:2])
    out["carril2_aporte_REP_pct"] = {"por_regla": {g: round(100 * float(v) / tot) for g, v in rep.sum().groupby(regla).sum().sort_values(ascending=False).items()},
                                     "por_instrumento": {g: round(100 * float(v) / tot) for g, v in rep.sum().groupby(lambda k: k.split("_")[-1]).sum().items()}}
    out["carril2_sin_cada_regla_REP_t"] = {}
    for r_ in sorted({regla(k) for k in inc}):
        keep = [c for c in inc if regla(c) != r_]
        out["carril2_sin_cada_regla_REP_t"][r_] = _est((S1[keep] * w[keep]).sum(axis=1)[b1 == "REP"]).get("t")
    out["carril2_incluidas"] = inc
    # combinación con la canasta intradía (DESC > 0 del pozo, sin Carril 2 ni SOM)
    X = pd.read_csv(POZO, index_col=0, parse_dates=True); X = X[X.index < "2026-10-01"]; bx = _blq(X.index)
    intra = []
    for c in X.columns:
        if c.startswith(("C2", "SOMSF")):
            continue
        ss = {k: X.loc[bx == k, c].dropna() for k in ("DESC", "REP", "HOLDOUT")}
        if any(len(v) == 0 or (v == 0).all() for v in ss.values()):
            continue
        if _mens(ss["DESC"]).mean() > 0:
            intra.append(c)
    I = _canasta(X, bx, intra); P2 = (S1[inc] * w).sum(axis=1); P2 = P2[P2.index >= "2019-07-01"]
    idx = I.index.union(P2.index); I = I.reindex(idx).fillna(0); P2 = P2.reindex(idx).fillna(0); b = _blq(idx)
    si, sc = _mens(I[b == "DESC"]).std(), _mens(P2[b == "DESC"]).std(); T = I / si + P2 / sc
    out["combinada"] = dict(n_intradia=len(intra), corr_mensual_DESC=round(float(_mens(I[b == "DESC"]).corr(_mens(P2[b == "DESC"]))), 2),
                            corr_mensual_REP=round(float(_mens(I[b == "REP"]).corr(_mens(P2[b == "REP"]))), 2),
                            intradia={k: _est(I[b == k]) for k in ("DESC", "REP", "HOLDOUT")},
                            carril2_2019={k: _est(P2[b == k]) for k in ("DESC", "REP")},
                            combinada={k: _est(T[b == k]) for k in ("DESC", "REP")})
    return out


def explorar() -> int:
    from registro_global import exigir_contada
    exigir_contada(OUT / "REGISTRO_POSTERIOR.md")
    res = dict(fase1_2=fase1_2(), fase3_4=fase3_4())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "EXPLORACION.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps(res, indent=1, ensure_ascii=False, default=float)[:6000])
    return 0


if __name__ == "__main__":
    a = sys.argv[1:] + [""]
    raise SystemExit({"explorar": explorar}.get(a[0], lambda: print(__doc__) or 2)())
