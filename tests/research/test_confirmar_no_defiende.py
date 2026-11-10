"""La confirmación congelada de «no defiende» calcula H1 sólo con NQ+RTY+YM, deja ES como diagnóstico y H2 con los cortes de DESC."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import confirmar_no_defiende as C  # noqa: E402


def test_analizar_usa_los_activos_y_cortes_declarados():
    rng = np.random.default_rng(1); filas = []
    for inst in ("NQ", "ES", "RTY", "YM"):
        for d in pd.bdate_range("2026-04-01", periods=60):
            f = int(d.strftime("%Y%m%d"))
            for p in (0, 0, 1, 1):
                ef = 0.3 if (p == 0 and inst != "ES") else 0.0
                filas.append(dict(inst=inst, fecha=f, placebo=p, tendencia_alineada=rng.normal(0, 5), rompe=1.0 if rng.random() < 0.5 + ef / 2 else -1.0))
    out = C.analizar(pd.DataFrame(filas))
    assert out["H1"]["media"] > 0.15 and out["H1"]["p_media"] < 0.01 and set(out["H1_por_activo"]) == {"NQ", "RTY", "YM"}
    assert abs(out["ES_diagnostico"]["media"]) < 0.2 and out["H2"]["n"] > 0
