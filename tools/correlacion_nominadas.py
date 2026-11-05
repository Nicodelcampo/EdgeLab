#!/usr/bin/env python3
"""Correlación entre las 12 nominadas al holdout + U1-CRUZADO, con su P&L CAUSAL de DESC + réplica (nunca el holdout).
Matriz sesión × regla con el P&L neto sumado por sesión en unidades de desvío (0 donde la regla no operó), como
`grilla_generica.matriz_sesiones`. Por par: Pearson y Spearman sobre el calendario común (sesiones en que operó alguna de las
dos y ambas tenían datos), IC90 por bootstrap de sesiones, co-ocurrencia (sesiones con las dos operando) y correlación sólo en
esas sesiones. Número efectivo de estrategias independientes: `escalera.n_efectivo` (Li-Ji).
  python tools/correlacion_nominadas.py
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.funnel.escalera import n_efectivo  # noqa: E402

REM = ROOT / "docs/research/canasta_7_20261030/remedicion_causal_20261102"
U1 = ROOT / "docs/research/areas_expansion_20261022/u1/regimen_causal"
SAL = ROOT / "docs/research/canasta_7_20261030/correlacion_nominadas"
REGLAS = ["CVGAP-NQ", "CVGAP-CFD-NQ", "U1-ZONAS-AVCL-NQ", "U1-RACIMOS-GRILLA-NQ", "U1-ZONAS-NQ", "U1-ORO-GRILLA", "U1-YM-GRILLA",
          "U1-ES-GRILLA", "U1-RACIMOS-GRILLA-ES", "U1-ZONAS-BT2-ES", "U1-ZONAS-BT2-NQ", "U1-ZONAS-ES"]


def series() -> dict:
    out = {}
    for c in REGLAS:
        s, x, per = [], [], []
        for t in ("desc", "oos"):
            o = json.loads((REM / f"{c}__{t}.json").read_text()).get("operaciones") or {}
            s += o.get("ses", []); x += o.get("neto", [])
        out[c] = pd.Series(x, index=np.array(s, int), dtype=float)
    ops = pd.concat([pd.read_csv(f) for f in sorted(U1.glob("U1_TOPES_NQ_*_operaciones.csv"))])
    ops = ops[(ops.ejecucion == "E1A/T3/S3") & (ops.tope == "mult:3") & ops.neto.notna()]
    out["U1-CRUZADO"] = pd.Series(ops.neto.to_numpy(float), index=ops.ses.to_numpy(int))
    return out


def main(B=2000, seed=20261102):
    S = series(); rng = np.random.default_rng(seed)
    por_ses = {c: (s / s.std(ddof=1)).groupby(level=0).sum() for c, s in S.items()}
    rango = {c: (s.index.min(), s.index.max()) for c, s in S.items()}
    filas = []; nombres = list(S)
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            lo, hi = max(rango[a][0], rango[b][0]), min(rango[a][1], rango[b][1])
            if lo >= hi: continue
            ses = sorted({x for x in por_ses[a].index.union(por_ses[b].index) if lo <= x <= hi})
            xa = por_ses[a].reindex(ses, fill_value=0).to_numpy(); xb = por_ses[b].reindex(ses, fill_value=0).to_numpy()
            ambas = (xa != 0) & (xb != 0)
            if len(ses) < 20 or xa.std() == 0 or xb.std() == 0: continue
            r = float(np.corrcoef(xa, xb)[0, 1]); rs = float(pd.Series(xa).rank().corr(pd.Series(xb).rank()))
            bs = []
            for _ in range(B):
                k = rng.integers(0, len(ses), len(ses)); ya, yb = xa[k], xb[k]
                if ya.std() > 0 and yb.std() > 0: bs.append(np.corrcoef(ya, yb)[0, 1])
            r_ambas = float(np.corrcoef(xa[ambas], xb[ambas])[0, 1]) if ambas.sum() >= 10 else None
            filas.append(dict(a=a, b=b, sesiones=len(ses), pearson=r, spearman=rs, ic90=[float(np.percentile(bs, 5)), float(np.percentile(bs, 95))],
                              coocurrencia=int(ambas.sum()), frac_coocurrencia=float(ambas.mean()), pearson_si_ambas=r_ambas))
    F = pd.DataFrame(filas).sort_values("pearson", ascending=False)
    # matriz común para Li-Ji (sesiones 2025-08-05 -> 2026-09-25, donde operan todas las de NQ/ES/GC)
    ses = sorted({x for c in nombres for x in por_ses[c].index if 20250805 <= x <= 20260925})
    M = np.column_stack([por_ses[c].reindex(ses, fill_value=0).to_numpy() for c in nombres])
    neff = n_efectivo(M)
    SAL.mkdir(parents=True, exist_ok=True); F.to_csv(SAL / "PARES.csv", index=False)
    C = pd.DataFrame(np.corrcoef(M.T), index=nombres, columns=nombres).round(3); C.to_csv(SAL / "MATRIZ.csv")
    res = dict(n_reglas=len(nombres), sesiones_matriz=len(ses), n_efectivo_li_ji=neff, mas=F.head(8).to_dict("records"),
               menos=F.tail(8).to_dict("records"), cerca_de_cero=F.iloc[(F.pearson.abs()).argsort()[:8]].to_dict("records"))
    (SAL / "RESULTADO.json").write_text(json.dumps(res, indent=1, default=float)); return res, F, C


if __name__ == "__main__":
    res, F, C = main()
    print("n efectivo", res["n_efectivo_li_ji"], "de", res["n_reglas"], "sesiones", res["sesiones_matriz"])
    print(F[["a", "b", "sesiones", "pearson", "ic90", "coocurrencia", "pearson_si_ambas"]].round(3).to_string())
