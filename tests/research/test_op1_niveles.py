"""OP-1: la regla mecánica del filtro y el análisis usan lo declarado en el pre-registro."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import op1_niveles as OP  # noqa: E402


def test_filtro_por_regla():
    assert OP.filtro(dict(previas_nominadas=["dist_cluster=2", "dist_zona_3600=2"])) == (["dist_zona_3600"], [2])
    assert OP.filtro(dict(previas_nominadas=[], resultados=[dict(tipo="celda", nominada=True, signo=-1, nombre="aprox_s=0 ∧ dist_zona_600=2")])) == (["aprox_s", "dist_zona_600"], [0, 2])
    assert OP.filtro(dict()) == (["dist_zona_1800"], [2])


def test_analizar_grilla_y_primaria():
    rng = np.random.default_rng(3); filas = []
    for d in pd.bdate_range("2026-04-01", periods=80):
        for tipo in ("reloj", "pivote"):
            for _ in range(6):
                lejos = rng.random() < 0.5; r = (1.0 if rng.random() < (0.65 if lejos else 0.45) else -1.0)
                fila = dict(inst="NQ", fecha=int(d.strftime("%Y%m%d")), placebo=0, tipo_nivel=tipo, dist_zona_1800=99.0 if lejos else 0.2, op_costo_r=0.08)
                for m in ("toca", "atraviesa"):
                    fila[f"op_{m}_llena"] = 1.0
                    for g in ("g05", "g1", "g2"): fila[f"op_{m}_{g}"] = r
                filas.append(fila)
    out = OP.analizar(pd.DataFrame(filas), ["dist_zona_1800"], [2])
    assert len(out["grilla"]) == 12 and out["primaria"]["r_neto_limpio"] > 0.1 and out["primaria"]["limpio_menos_resto"] > 0.2 and out["pasa_al_holdout"]
