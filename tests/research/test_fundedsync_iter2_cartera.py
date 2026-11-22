"""Pruebas deterministas offline para iteracion 2 FUNDEDSYNC (permutaciones, pesos, concurrencia, K51)."""
from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest


def test_presupuesto_grillas_y_compuerta_k51() -> None:
    mod = importlib.import_module("tools.fundedsync_iter2_cartera")
    mod.asegurar_compuerta_iter2()
    specs = mod._grillas_iter2()
    v1 = [s for s in specs if s["bloque"] == "V1"]
    v2 = [s for s in specs if s["bloque"] == "V2"]
    assert len(v1) == 23
    assert len(v2) == 22
    assert len(specs) == 45


def test_bateria_permutaciones_distingue_senal_de_ruido() -> None:
    mod = importlib.import_module("tools.fundedsync_iter2_cartera")
    rng = np.random.default_rng(123)
    fechas = [20200101 + i for i in range(400)]
    series = {
        "EDGE_FUERTE": pd.Series(0.35 + rng.normal(0.0, 0.8, 400), index=fechas),
        **{f"RUIDO_{k}": pd.Series(rng.normal(0.0, 1.0, 400), index=fechas) for k in range(1, 10)},
    }
    res = mod.calcular_bateria_permutaciones(series, fechas, n_eff=8.0, n_perm=2000, seed=7).set_index("variante")
    assert res.loc["EDGE_FUERTE", "p_perm"] < 0.01
    assert res.loc["EDGE_FUERTE", "q_bh"] <= 0.01
    assert res.loc["EDGE_FUERTE", "p_maxT"] < 0.05
    assert res.loc["EDGE_FUERTE", "DSR"] > 0.90
    assert float(res.loc["RUIDO_1", "p_maxT"]) > 0.15


def test_pesos_y_tope_concurrencia_causal() -> None:
    mod = importlib.import_module("tools.fundedsync_iter2_cartera")
    rng = np.random.default_rng(5)
    fechas = [20210101 + i for i in range(60)]
    d_desc = pd.DataFrame({
        "A::NQ": rng.normal(0.15, 0.8, 60),
        "B::NQ": rng.normal(0.30, 0.4, 60),
        "C::ES": rng.normal(0.10, 0.5, 60),
    }, index=fechas)
    m_desc = pd.DataFrame({"A::NQ": [2.0, 1.0, 3.0], "B::NQ": [1.5, 1.0, 2.0], "C::ES": [0.8, 0.5, 1.2]})
    pesos = mod.calcular_pesos_esquemas(d_desc, m_desc, {"A::NQ": 60.0, "B::NQ": 360.0, "C::ES": 180.0})
    assert set(pesos) == {"W0_equal_1R", "W1_inv_vol_dia", "W2_inv_vol_mes_freq", "W3_ERC_cov_cap", "W4_HRP", "W5_freq_dur_conc"}
    # Tope de concurrencia causal: 3 entradas simultaneas en +1 con peso 1.2 -> cap 2.5 limita total a 2.5
    ops = {
        "S1": pd.DataFrame({"fecha_int": [20210102], "mes": ["2021-01"], "en_ns": [100], "ex_ns": [500], "side": [1], "R_neto_mini": [1.0], "riesgo_pts": [50.0]}),
        "S2": pd.DataFrame({"fecha_int": [20210102], "mes": ["2021-01"], "en_ns": [150], "ex_ns": [450], "side": [1], "R_neto_mini": [1.0], "riesgo_pts": [50.0]}),
        "S3": pd.DataFrame({"fecha_int": [20210102], "mes": ["2021-01"], "en_ns": [200], "ex_ns": [400], "side": [1], "R_neto_mini": [1.0], "riesgo_pts": [50.0]}),
    }
    tr, max_open = mod.aplicar_tope_concurrencia_causal(ops, {"S1": 1.2, "S2": 1.2, "S3": 1.2}, cap_r=2.5)
    assert max_open <= 2.5001
    assert tr["w_eff"].tolist() == [pytest.approx(1.2), pytest.approx(1.2), pytest.approx(0.1)]
    assert tr["R_eff"].sum() == pytest.approx(2.5)


def test_convertir_ops_enriquecidas_y_bloqueo_terminal() -> None:
    mod = importlib.import_module("tools.fundedsync_iter2_cartera")
    df_t = pd.DataFrame({
        "side": [1, 1],
        "qty": [1, 1],
        "entry_time_utc": ["2025-02-10T15:00:00Z", "2026-10-02T15:00:00Z"],
        "exit_time_utc": ["2025-02-10T16:30:00Z", "2026-10-02T16:00:00Z"],
        "entry_price": [20000.0, 20000.0],
        "stop_price": [19950.0, 19950.0],
        "pnl_pts": [50.0, 100.0],
        "pnl_usd": [1000.0, 2000.0],
        "mae_usd": [200.0, 0.0],
        "mfe_usd": [1200.0, 2000.0],
    })
    dates = pd.to_datetime(["2025-02-10", "2026-10-02"])
    atr_ses = pd.Series([200.0, 200.0], index=dates)
    orb_raw = pd.Series([85.0, 85.0], index=dates)
    ops = mod.convertir_ops_enriquecidas(df_t, "T", "NQ", atr_ses, orb_raw, 20.0, stop_orb_mult=1.0)
    assert len(ops) == 1
    assert ops["a5"].iloc[0] == "DESC"
    assert ops["riesgo_pts"].iloc[0] == pytest.approx(85.0)
    assert ops["dur_min"].iloc[0] == pytest.approx(90.0)
