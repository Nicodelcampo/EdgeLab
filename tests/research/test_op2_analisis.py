"""El análisis congelado de OP-2 separa períodos, exige los dos y calcula real − control con la misma operación."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import op2_clusters as A  # noqa: E402


def _tabla(ef_desc, ef_rep):
    rng = np.random.default_rng(2); filas = []
    for d in list(pd.bdate_range("2025-08-01", periods=80)) + list(pd.bdate_range("2026-04-01", periods=80)):
        f = int(d.strftime("%Y%m%d")); ef = ef_desc if f <= 20260331 else ef_rep
        for inst in ("NQ", "YM"):
            for p in (0, 0, 1):
                r = 1.0 if rng.random() < 0.5 + (ef if (p == 0 and inst == "YM") else 0) else -1.0
                filas.append(dict(inst=inst, fecha=f, placebo=p, op_g05=r / 2, op_g1=r, op_g2=r, op_costo_r=0.08))
    return pd.DataFrame(filas)


def test_ym_pasa_solo_si_los_dos_periodos():
    out = A.analizar(_tabla(0.3, 0.3)); assert out["pasa_al_holdout"]["YM"]                   # (el conjunto también pasa: YM es la mitad)
    assert out["grilla"]["YM/ambos/g1"]["real_menos_control"] > 0.3
    assert not A.analizar(_tabla(0.3, 0.0))["pasa_al_holdout"]["YM"]               # un solo período no alcanza
