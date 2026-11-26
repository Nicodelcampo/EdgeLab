"""Lectura de RESULTADOS_GESTION.json (kernel Kaggle edgelab-cartera-gestion-20261125) con el criterio pre-registrado
(docs/research/cartera_nt8_20261125/PREREGISTRO_MULTIACTIVO_Y_GESTION.md, Parte B).

  python tools/cartera_gestion_analisis.py <RESULTADOS_GESTION.json>   # -> docs/research/cartera_nt8_20261125/GESTION_RESUMEN.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "docs" / "research" / "cartera_nt8_20261125"


def tabla_gestion(g: dict) -> pd.DataFrame:
    filas = []
    for k, v in g.items():
        comp, cta, alloc, kk, dyn, freno, tope = k.split("|")
        f = dict(clave=k, comp=comp, cuenta=cta, alloc=alloc, k=int(kk[1:]), dyn=int(dyn[3:]), freno=float(freno[5:]), tope=int(tope[4:]))
        for m, r in v.items():
            for q in ("p_ganar", "ev", "pasa", "retiros", "dias", "quiebra"):
                f[f"{m}|{q}"] = r[q]
        filas.append(f)
    return pd.DataFrame(filas)


def elegir(d: pd.DataFrame, col_p: str, col_ev: str) -> pd.Series:
    m = d[col_p].max(); c = d[d[col_p] >= m - 0.02]
    return c.loc[c[col_ev].idxmax()]


def main(path: str) -> int:
    R = json.loads(Path(path).read_text())
    G = tabla_gestion(R["gestion"])
    res = {"n_paths": R["n_paths"], "cuentas": {}, "efectos_marginales": {}, "rescate": {}}
    cols = ["clave", "todo|contraida|p_ganar", "todo|contraida|ev", "todo|dev|p_ganar", "todo|cero|p_ganar", "H1|contraida|p_ganar", "H2|contraida|p_ganar",
            "todo|contraida|pasa", "todo|contraida|retiros", "todo|contraida|dias"]
    for (comp, cta), d in G.groupby(["comp", "cuenta"]):
        base = d[(d.alloc == "EQ") & (d.k == 1) & (d.dyn == 0) & (d.freno == 0) & (d.tope == 0)]
        e_todo = elegir(d, "todo|contraida|p_ganar", "todo|contraida|ev")
        e_h1 = elegir(d, "H1|contraida|p_ganar", "H1|contraida|ev")
        rho = d[["H1|contraida|p_ganar", "H2|contraida|p_ganar"]].corr(method="spearman").iloc[0, 1]
        top = d.sort_values("todo|contraida|p_ganar", ascending=False).head(8)[cols]
        res["cuentas"][f"{comp}|{cta}"] = dict(
            base=base[cols].iloc[0].to_dict() if len(base) else None,
            elegido_todo=e_todo[cols].to_dict(), elegido_H1=e_h1[cols].to_dict(),
            elegido_H1_en_H2=float(e_h1["H2|contraida|p_ganar"]), base_en_H2=float(base["H2|contraida|p_ganar"].iloc[0]) if len(base) else None,
            spearman_H1_H2=round(float(rho), 3), top8=top.to_dict(orient="records"))
        for fac in ("alloc", "k", "dyn", "freno", "tope"):
            res["efectos_marginales"].setdefault(f"{comp}|{cta}", {})[fac] = (
                d.groupby(fac)[["todo|contraida|p_ganar", "todo|cero|p_ganar", "H2|contraida|p_ganar"]].mean().round(3).to_dict(orient="index"))
        print(f"\n== {comp} {cta}: spearman H1-H2 {rho:.2f}")
        print(" base     ", None if not len(base) else {c: round(base[c].iloc[0], 3) for c in cols[1:]})
        print(" elegido  ", e_todo["clave"], {c: round(e_todo[c], 3) for c in cols[1:]})
        print(" elegidoH1", e_h1["clave"], "-> H2", round(e_h1["H2|contraida|p_ganar"], 3), "| base en H2",
              None if not len(base) else round(base["H2|contraida|p_ganar"].iloc[0], 3))
        for fac in ("alloc", "k", "dyn", "freno", "tope"):
            print("   ", fac, d.groupby(fac)["todo|contraida|p_ganar"].mean().round(3).to_dict())
    # rescate
    filas = []
    for k, v in R["rescate"].items():
        comb, freno, tope = k.split("|")
        f = dict(clave=k, comb=comb, n=len(comb.split("+")), freno=int(freno[5:]), tope=int(tope[4:]))
        for m, r in v.items():
            f[f"{m}|pasa"] = r["pasa"]; f[f"{m}|quiebra"] = r["quiebra"]; f[f"{m}|dias"] = r["dias"]
        filas.append(f)
    S = pd.DataFrame(filas)
    e = S.loc[S["todo|contraida|pasa"].idxmax()]; e1 = S.loc[S["H1|contraida|pasa"].idxmax()]
    rho = S[["H1|contraida|pasa", "H2|contraida|pasa"]].corr(method="spearman").iloc[0, 1]
    c2 = ["clave", "todo|contraida|pasa", "todo|dev|pasa", "todo|cero|pasa", "H1|contraida|pasa", "H2|contraida|pasa", "todo|contraida|dias"]
    res["rescate"] = dict(elegido_todo=e[c2].to_dict(), elegido_H1=e1[c2].to_dict(), spearman_H1_H2=round(float(rho), 3),
                          top10=S.sort_values("todo|contraida|pasa", ascending=False).head(10)[c2].to_dict(orient="records"),
                          cartera_completa=S[S.n == 8][c2].to_dict(orient="records"),
                          por_freno=S.groupby("freno")["todo|contraida|pasa"].mean().round(3).to_dict(),
                          por_tope=S.groupby("tope")["todo|contraida|pasa"].mean().round(3).to_dict())
    print("\n== RESCATE spearman H1-H2", round(rho, 2))
    print(S.sort_values("todo|contraida|pasa", ascending=False).head(10)[c2].round(3).to_string())
    print("elegido H1:", e1["clave"], "H2", round(e1["H2|contraida|pasa"], 3))
    (OUT / "GESTION_RESUMEN.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
