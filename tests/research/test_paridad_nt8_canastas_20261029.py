"""Tests unitarios para paridad con NinjaTrader 8 Strategy Analyzer y simulación de Canastas de Regímenes (`paridad_nt8_canastas.py`)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from edgelab.research import analizador as AN, paridad_nt8_canastas as PNC


def _ops_sinteticas() -> pd.DataFrame:
    return pd.DataFrame({
        "celda": [0, 0, 0, 1, 1],
        "t": [1712000000, 1712000300, 1712086400, 1712000100, 1712086500],
        "ses": [20260401, 20260401, 20260402, 20260401, 20260402],
        "k": [100, 105, 500, 102, 502],
        "neto": [15.0, -8.0, 22.0, 12.0, 18.0],
    })


def test_filtrar_solapadas_nt8_bloquea_dentro_de_ventana() -> None:
    ops = _ops_sinteticas()
    c0 = ops[ops["celda"] == 0].reset_index(drop=True)
    # Las dos primeras operaciones en 20260401 están a 300s (< 900s): NT8 Flat-Only bloquea la segunda (-8.0)
    nt8 = PNC.filtrar_solapadas_nt8(c0, duracion_s=900)
    assert len(nt8) == 2
    assert np.allclose(nt8["neto"].to_numpy(), [15.0, 22.0])

    # Con una_por_sesion=True también quedan 2 (una en 20260401 y otra en 20260402)
    nt8_1s = PNC.filtrar_solapadas_nt8(c0, duracion_s=900, una_por_sesion=True)
    assert len(nt8_1s) == 2


def test_reporte_paridad_nt8_y_curva_equity() -> None:
    ops = _ops_sinteticas()
    c0 = ops[ops["celda"] == 0].reset_index(drop=True)
    rep = PNC.reporte_paridad_nt8(c0, instrumento="NQ", duracion_s=900)
    assert rep["n_raw"] == 3
    assert rep["n_nt8"] == 2
    assert np.isclose(rep["raw"]["neto_total"], 29.0)
    assert np.isclose(rep["nt8_flat"]["neto_total"], 37.0)
    assert np.isclose(rep["neto_usd_micro_nt8"], 74.0)  # MNQ = $2/pt
    assert len(rep["curva_nt8"]["eq_pts"]) == 2
    assert rep["curva_nt8"]["eq_pts"][-1] == 37.0


def test_simular_canasta_regimen_m1_y_m2() -> None:
    ops = _ops_sinteticas()
    res = PNC.simular_canasta_regimen(ops, n_celdas=2, instrumento="NQ", duracion_s=900)
    assert res["ok"] is True
    assert res["n_celdas_canasta"] == 2
    # En M1: celda 0 tiene 2 ops no solapadas (15 + 22 = 37) y celda 1 tiene 2 ops no solapadas (12 + 18 = 30) -> suma = 67, 1/K = 33.5
    assert res["m1_subcuentas_1_k"]["n_ops"] == 4
    assert np.isclose(res["m1_subcuentas_1_k"]["neto_total_suma_k_pts"], 67.0)
    assert np.isclose(res["m1_subcuentas_1_k"]["neto_total_1x_pts"], 33.5)
    # En M2 (Flat global en toda la canasta): en 20260401 entra celda 0 en t=1712000000 y bloquea celda 1 en t=1712000100; igual en 20260402
    assert res["m2_cuenta_unica_flat"]["n_ops"] == 2
    assert np.isclose(res["m2_cuenta_unica_flat"]["neto_total_pts"], 37.0)


def test_exportar_senales_nt8_csv_y_estrategia_cs(tmp_path: Path) -> None:
    ops = _ops_sinteticas()
    out_csv = tmp_path / "senales_nt8.csv"
    n = PNC.exportar_senales_nt8_csv(ops, out_csv)
    assert n == 5
    assert out_csv.exists()
    cs_path = Path(__file__).resolve().parents[2] / "nt8/strategies/EdgeLabSpiralBasketExecutor.cs"
    assert cs_path.exists()
    src = cs_path.read_text(encoding="utf-8")
    assert "class EdgeLabSpiralBasketExecutor : Strategy" in src
    assert "ApplyConservativeStopCap" in src
    assert "VirtualSubAccountsNetting" in src
    assert "SingleGlobalFlatLock" in src
    assert src.endswith("\t}\n}\n") or src.endswith("\t}\n}")
