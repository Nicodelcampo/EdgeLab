#!/usr/bin/env python3
"""FS-NFCO-A5 (2026-11-26): N, F, C y O de FundedSync (traducción corregida) en R por bloque A5: DESC (BH q 0,10) → REP.
Pre-registro: docs/research/fs_nfco_a5_20261126/PREREGISTRO.md.   python tools/fs_nfco_a5.py"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/fs_nfco_a5_20261126"; MODS = ("N", "F", "C", "O")


def _p(g, rng, B=4000):
    if len(g) < 3: return float("nan"), 1.0
    s = g.groupby("ses").R.sum(); n = g.groupby("ses").size(); m = g.R.mean()
    i = rng.integers(0, len(s), (B, len(s))); bm = s.to_numpy()[i].sum(1) / n.to_numpy()[i].sum(1)
    return float(m), float(((bm - m) >= m).mean() + 1 / B)


def main():
    from registro_global import exigir_contada
    exigir_contada(DIR / "PREREGISTRO.md")
    from edgelab.holdout import a5_bloque
    from edgelab.discovery.scan import benjamini_hochberg
    O = pd.read_csv(ROOT / "docs/research/remedicion_fs_il_20261121/FS_OPS_NQ_IL.csv.gz", parse_dates=["dia"])
    O = O[O.modulo.isin(MODS) & (O.dia >= "2018-01-01") & (O.dia <= "2026-09-30")].copy()
    unidad = np.where(O.riesgo.fillna(0) > 0, O.riesgo, O.atr20)          # enmienda: sin stop (N, O) -> ATR20 de la sesión previa
    O = O[np.isfinite(unidad) & (unidad > 0)]; unidad = unidad[np.isfinite(unidad) & (unidad > 0)]
    O["R"] = O.neto / unidad; O["ses"] = O.dia.dt.strftime("%Y%m%d").astype(int); O["bloque"] = O.ses.map(a5_bloque)
    rng = np.random.default_rng(20261126); res = {}
    for m in MODS:
        g = O[O.modulo == m]; d, r = g[g.bloque == "DESC"], g[g.bloque == "REP"]
        md, pd_ = _p(d, rng); sd = d.R.std()
        res[m] = dict(n_desc=int(len(d)), R_desc=md, p_desc=pd_, mde80_desc=float(2.49 * sd / np.sqrt(len(d))), n_rep=int(len(r)),
                      por_anio={int(k): float(v) for k, v in g.groupby(g.dia.dt.year).R.mean().items()})
    q = benjamini_hochberg([res[m]["p_desc"] for m in MODS])
    for m, qq in zip(MODS, q):
        res[m]["q_desc"] = float(qq); res[m]["nominada"] = bool(qq <= 0.10)
        g = O[(O.modulo == m) & (O.bloque == "REP")]
        if res[m]["nominada"] and len(g) > 2:
            mr, pr = _p(g, rng); res[m].update(R_rep=mr, p_rep=pr, mde80_rep=float(2.49 * g.R.std() / np.sqrt(len(g))))
            res[m]["desenlace"] = "CONFIRMA_REP" if pr < 0.05 and mr > 0 else "NO_CONCLUYENTE"
        else:
            res[m]["desenlace"] = "SIN_NOMINAR" if not res[m]["nominada"] else "SIN_REP"
    (DIR / "RESULTADO.json").write_text(json.dumps(res, indent=1))
    for m in MODS: print(m, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in res[m].items() if k != "por_anio"})


if __name__ == "__main__":
    main()
