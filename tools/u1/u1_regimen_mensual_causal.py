#!/usr/bin/env python3
"""Experimento 1 (regimen_causal/PREREGISTRO_REGIMEN_MENSUAL_CAUSAL.md): U1-CRUZADO causal, media neta mensual (E1A/T3/S3, tope mult:3)
contra 3 medidas de régimen calculadas con las 20 sesiones anteriores al mes (rango, tendencia, volatilidad). Spearman + Holm.
Reusa el archivo de días de U1_DENSIDAD (rango diario) y el boot por bloques de meses."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

U = Path(__file__).resolve().parents[2] / "docs/research/areas_expansion_20261022/u1"; R = U / "regimen_causal"
EJ, TOPE = "E1A/T3/S3", "mult:3"


def ops():
    fs = sorted(R.glob("U1_TOPES_*_operaciones.csv")); out = []
    for f in fs:
        o = pd.read_csv(f); o = o[(o.ejecucion == EJ) & (o.tope == TOPE) & o.neto.notna()]
        out.append(o.assign(tramo="US" if "_US_" in f.name else "NQ")[["ses", "t", "neto", "tramo"]])
    return pd.concat(out, ignore_index=True)


def main():
    o = ops(); o["mes"] = (o.ses // 100).astype(int)
    m = o.groupby("mes").agg(n=("neto", "size"), media=("neto", "mean"), tramo=("tramo", "first")).reset_index()
    d = pd.read_csv(U / "topes/U1_DENSIDAD_20230101_20260930_dias.csv").sort_values("ses").reset_index(drop=True)
    d["mes"] = d.ses // 100
    cierres = R / "U1_DENSIDAD_20230101_20260930_dias.csv"          # con cierre (2026-11-02)
    if cierres.exists(): d = d.merge(pd.read_csv(cierres)[["ses", "cierre"]], on="ses", how="left")
    filas = []
    for mes in m.mes:
        prev = d[d.mes < mes].tail(20)
        if len(prev) < 20: filas.append(dict(mes=mes)); continue
        f = dict(mes=mes, rango=prev.rango.mean())
        if "cierre" in prev:
            c = prev.cierre.to_numpy(float); r = np.diff(np.log(c))
            f["tendencia"] = abs(c[-1] - c[0]) / prev.rango.sum(); f["vol"] = float(np.std(r, ddof=1))
        filas.append(f)
    M = m.merge(pd.DataFrame(filas), on="mes", how="left")
    res = dict(meses=int(len(M)), meses_positivos=int((M.media > 0).sum()), por_anio=M.assign(a=M.mes // 100).groupby("a").apply(
        lambda g: dict(meses=len(g), ops=int(g.n.sum()), media_ponderada=float((g.media * g.n).sum() / g.n.sum()))).to_dict(), pruebas={})
    ps = []
    for v in ("rango", "tendencia", "vol"):
        if v not in M: res["pruebas"][v] = "sin dato"; continue
        x = M.dropna(subset=[v]); rho, p = spearmanr(x[v], x.media)
        rng = np.random.default_rng(20261102); bs = [spearmanr(*x.iloc[rng.integers(0, len(x), len(x))][[v, "media"]].T.values)[0] for _ in range(4000)]
        por_tramo = {t: float(spearmanr(g[v], g.media)[0]) for t, g in x.groupby("tramo") if len(g) > 4}
        terc = pd.qcut(x[v], 3, labels=["bajo", "medio", "alto"])
        res["pruebas"][v] = dict(rho=float(rho), p=float(p), ic90=[float(np.nanpercentile(bs, 5)), float(np.nanpercentile(bs, 95))],
                                 por_tramo=por_tramo, media_por_tercil={str(k): float((g.media * g.n).sum() / g.n.sum()) for k, g in x.groupby(terc, observed=True)})
        ps.append((v, p))
    orden = sorted(ps, key=lambda t: t[1]); k = len(orden)
    for i, (v, p) in enumerate(orden): res["pruebas"][v]["p_holm"] = float(min(1, max(p * (k - j) for j, (_, p) in enumerate(orden[:i + 1]))))
    M.to_csv(R / "MENSUAL.csv", index=False); (R / "RESULTADO.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
