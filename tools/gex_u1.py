#!/usr/bin/env python3
"""GEX-U1 (pre-registro docs/research/gex_u1_20261108/PREREGISTRO.md): R de la canasta U1 de CANASTA-GLOBAL por tercil del GEX del día
hábil anterior. Usa las series de las tandas (data/canasta_global/parte*.pkl) y el DIX.csv de SqueezeMetrics."""
import json, pickle, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; DIR = ROOT / "docs/research/gex_u1_20261108"


def serie_canasta():
    R = json.loads((ROOT / "docs/research/canasta_global_20261108/RESULTADO_CANASTA_GLOBAL.json").read_text())
    T = json.loads((ROOT / "docs/research/canasta_global_20261108/TANDAS.json").read_text()); dias = np.array(T["dias"])
    partes = [p for f in sorted((ROOT / "data/canasta_global").glob("parte*.pkl")) for p in pickle.loads(f.read_bytes())]
    cols = []
    for x in R["reglas"]:
        c = next(p for p in partes if p["nombre"] == x["cubo"] and x["celda_plana"] in set(p["ev"].tolist()))
        cols.append(c["series"][:, list(c["ev"]).index(x["celda_plana"])].astype(float))
    return dias, np.mean(cols, axis=0)


def main():
    dias, c = serie_canasta()
    g = pd.read_csv(ROOT / "data/DIX_squeezemetrics_20261108.csv", dtype={"date": str})
    g["d"] = g.date.str.replace("-", "").astype(int); g = g.sort_values("d")
    idx = np.searchsorted(g.d.to_numpy(), dias, side="left") - 1                  # último día hábil ANTES de la sesión
    gex = g.gex.to_numpy()[idx]; ok = idx >= 0
    cortes = np.quantile(gex[ok], [1 / 3, 2 / 3]); terc = np.searchsorted(cortes, gex, side="right")
    medias = [float(c[ok & (terc == k)].mean()) for k in range(3)]; obs = medias[2] - medias[0]
    rng = np.random.default_rng(20261108); lab = terc[ok]; x = c[ok]; nul = []
    for _ in range(10000):
        p = rng.permutation(lab); nul.append(x[p == 2].mean() - x[p == 0].mean())
    pv = float((1 + (np.array(nul) >= obs).sum()) / 10001)
    out = dict(sesiones=int(ok.sum()), cortes_gex=cortes.tolist(), media_por_tercil=medias, n_por_tercil=[int((lab == k).sum()) for k in range(3)],
               diferencia_alto_menos_bajo=obs, p=pv, pasa=bool(pv < 0.10 and obs > 0))
    (DIR / "RESULTADO.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))


if __name__ == "__main__":
    main()
