#!/usr/bin/env python3
"""Re-corrida CORREGIDA de F3/F4 de la campaña multi-instrumento (bug de apertura RTH, 2026-09-23).

Mismas hipótesis, variantes, datos, costos, nulo y estadística que `tools/campaign_ticks_multi.py`
(pre-registro 60154b9). Solo cambia el arreglo del bug: la apertura RTH se busca en la mañana de la fecha
de trading, no en la barra de las 18:00 ET de la noche previa.

NO registra pruebas en el Edge Brain: el presupuesto de C-TICKS-F3/F4 ya se consumió con los resultados
invalidados, y abrir una campaña nueva requiere aprobación humana (NO_SELF_APPROVAL). Escribe
`artifacts/campaign_ticks_multi/landscape_F3F4_fix.json` a la espera de esa aprobación.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from tools.campaign_ticks_multi import (COMM_TICKS, DIRS, DISC_END, FAMILIES, OUT, SEED, _prep,  # noqa: E402
                                        mcpt_family, session_ci_and_dsr, simulate)


def main() -> int:
    rng = np.random.default_rng(SEED + 1)
    rows = []
    for inst in DIRS:
        b = _prep(pd.read_parquet(OUT / f"bars_{inst}.parquet"))
        disc = set(b.date[b.date <= DISC_END]); val = set(b.date[b.date > DISC_END])
        spr = b[b.date <= DISC_END].groupby("et_hour")["spread"].median()
        cost = {int(h): float(v) + COMM_TICKS[inst] for h, v in spr.items() if np.isfinite(v)}
        for fam in ("F3", "F4"):
            vt = [simulate(b, inst, fam, p) for p in FAMILIES[fam]]
            stat, pval, obs = mcpt_family(b, vt, cost, disc, rng)
            for vi, (p, tr) in enumerate(zip(FAMILIES[fam], vt)):
                vtr = [t for t in tr if t[0] in val]
                base = session_ci_and_dsr(vtr, val, cost, 1.0); stress = session_ci_and_dsr(vtr, val, cost, 1.5)
                s13 = bool(pval < 0.05 and base["ci_pass"] and stress["ci_pass"] and base["dsr_pass"])
                rows.append(dict(inst=inst, family=fam, variant=vi, params=p,
                                 disc_trades=int(sum(1 for t in tr if t[0] in disc)),
                                 disc_expectancy=None if not np.isfinite(obs[vi]) else float(obs[vi]),
                                 family_mcpt_p=pval, val_base=base, val_stress=stress, survives_1_3=s13))
            print(json.dumps(dict(inst=inst, fam=fam, mcpt_p=round(pval, 4),
                                  val=[None if r["val_base"]["expectancy"] is None else round(r["val_base"]["expectancy"], 3)
                                       for r in rows[-4:]],
                                  ntr=[r["val_base"]["n_trades"] for r in rows[-4:]])), flush=True)
    (OUT / "landscape_F3F4_fix.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    land = pd.DataFrame(rows)
    rep = land[land.survives_1_3].groupby(["family", "variant"]).inst.nunique()
    print(json.dumps(dict(trials=len(rows), survives_1_3=int(land.survives_1_3.sum()),
                          replicated=[dict(family=f, variant=int(v), n=int(n)) for (f, v), n in rep.items() if n >= 2])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
