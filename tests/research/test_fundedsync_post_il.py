"""Pruebas deterministas offline para la campana post-IL en unidad R y firewall A4/A5."""
from __future__ import annotations

import importlib
from types import SimpleNamespace

import pandas as pd
import pytest


def test_convertir_trades_a_ops_r_y_bloqueo_terminal() -> None:
    mod = importlib.import_module("tools.fundedsync_post_il_cadena")
    ts_list = [
        "2025-02-10T15:00:00Z",  # 2025-02 -> DESC en A5
        "2025-05-12T15:00:00Z",  # 2025-05 -> REP en A5
        "2025-09-10T15:00:00Z",  # 2025-09 -> HOLDOUT en A5
        "2026-10-05T15:00:00Z",  # TERMINAL >= 2026-10-01 -> excluido
    ]
    df_t = pd.DataFrame({
        "module": ["V", "V", "V", "V"],
        "side": [1, 1, 1, 1],
        "qty": [1, 1, 1, 1],
        "entry_time_utc": ts_list,
        "exit_time_utc": ts_list,
        "entry_price": [20000.0] * 4,
        "exit_price": [20050.0, 20050.0, 20050.0, 21000.0],
        "stop_price": [19950.0] * 4,
        "target_price": [20100.0] * 4,
        "entry_name": ["e"] * 4,
        "exit_name": ["x"] * 4,
        "pnl_pts": [50.0, 50.0, 50.0, 1000.0],
        "pnl_usd": [1000.0, 1000.0, 1000.0, 20000.0],
        "mae_usd": [200.0, 200.0, 200.0, 0.0],
        "mfe_usd": [1200.0, 1200.0, 1200.0, 20000.0],
        "bars": [5] * 4,
    })
    dates = pd.to_datetime(["2025-02-10", "2025-05-12", "2025-09-10", "2026-10-05"])
    atr_ses = pd.Series([200.0, 200.0, 200.0, 200.0], index=dates)
    orb_t = pd.Series([80.0, 80.0, 80.0, 80.0], index=dates)
    ms_fake = SimpleNamespace(point_value=20.0)

    ops = mod.convertir_trades_a_ops_r(df_t, "V", "NQ", atr_ses, orb_t, ms_fake)
    assert len(ops) == 3
    assert "TERMINAL" not in set(ops["a5"])
    assert set(ops["a5"]) == {"DESC", "REP", "HOLDOUT"}
    assert ops["R_bruto"].iloc[0] == pytest.approx(1.0)
    # NQ canonica = 1.5455 pts -> (50 - 1.5455)/50 = 0.96909
    assert ops["R_neto_mini"].iloc[0] == pytest.approx((50.0 - 1.5455) / 50.0, rel=1e-4)
    # Sin leakage de stop overlay cuando cap_mae_atr_k recorta MAE >= 0.4 * 200 = 80
    ops_cap = mod.convertir_trades_a_ops_r(df_t, "V", "NQ", atr_ses, orb_t, ms_fake, cap_mae_atr_k=0.40)
    assert len(ops_cap) == 3
    assert ops_cap["riesgo_pts"].iloc[0] == pytest.approx(50.0)


    ops_vacio = mod.convertir_trades_a_ops_r(pd.DataFrame(), "F", "NQ", atr_ses, orb_t, ms_fake)
    assert ops_vacio.empty
    assert str(ops_vacio["R_neto_mini"].dtype) == "float64"

    df_mix = pd.concat([
        pd.DataFrame({"R": [0.1, -0.2, 0.3, 0.2, 0.1, -0.1] * 6, "mes": [f"2020-{m:02d}" for m in range(1, 7)] * 6, "variante": "F_a"}),
        pd.DataFrame({"R": [0.05, -0.1, 0.2, 0.15, 0.05, -0.05] * 6, "mes": [f"2020-{m:02d}" for m in range(1, 7)] * 6, "variante": "F_b"}),
        ops_vacio[["R_neto_mini", "mes"]].rename(columns={"R_neto_mini": "R"}).assign(variante="F_vacia"),
    ], ignore_index=True)
    d_mix = mod._diagnostico_con_mejor(df_mix, {"p": lambda v: v}, total_celdas=3)
    assert d_mix["variantes"] == 2
    assert d_mix["celdas_cero_ops"] == 1


def test_k33_friccion_instrumentos_y_grillas_presupuesto() -> None:
    mod = importlib.import_module("tools.fundedsync_post_il_cadena")
    f_nq, f_mnq = mod.friccion_instrumento_puntos("NQ")
    assert f_nq == pytest.approx(1.5455, rel=1e-4)
    assert f_mnq == pytest.approx(1.9775, rel=1e-4)
    f_emd, f_memd = mod.friccion_instrumento_puntos("EMD")
    assert f_emd == pytest.approx(0.4378, rel=1e-4)
    assert f_memd is None

    specs = mod._grillas_bloque_b()
    # Presupuesto PREREGISTRO: B1(14) + B2(12) + B3(21) = 47 variantes
    assert len(specs) == 47


def test_cache_key_determinista_y_seleccion_finalistas() -> None:
    mod = importlib.import_module("tools.fundedsync_post_il_cadena")
    assert mod._cache_key("nq", "V", {}) == "NQ_fabrica_V"
    k1 = mod._cache_key("ES", "Q", {"risk_reward": 1.5, "break_margin_ticks": 6})
    k2 = mod._cache_key("es", "Q", {"break_margin_ticks": 6, "risk_reward": 1.5})
    assert k1 == k2 and k1.startswith("ES_Q_")

    df_b = pd.DataFrame([
        {"variante": "F_a", "modulo": "F", "pasa_desc": True, "R_por_mes": 1.1, "t_ses": 2.5,
         "pasa_desc_2020": True, "R_neto_2020": 0.15, "R_mes_2020": 1.5, "t_ses_2020": 2.8, "degenerada_2020": False, "R_neto_mini": 0.10},
        {"variante": "S_a", "modulo": "S", "pasa_desc": False, "R_por_mes": -0.2, "t_ses": -0.5,
         "pasa_desc_2020": True, "R_neto_2020": 0.08, "R_mes_2020": 2.2, "t_ses_2020": 2.4, "degenerada_2020": False, "R_neto_mini": -0.02},
        {"variante": "S_b", "modulo": "S", "pasa_desc": False, "R_por_mes": -0.3, "t_ses": -0.7,
         "pasa_desc_2020": True, "R_neto_2020": 0.07, "R_mes_2020": 1.9, "t_ses_2020": 2.1, "degenerada_2020": False, "R_neto_mini": -0.03},
        {"variante": "V_a", "modulo": "V", "pasa_desc": False, "R_por_mes": 0.2, "t_ses": 1.4,
         "pasa_desc_2020": True, "R_neto_2020": 0.09, "R_mes_2020": 1.4, "t_ses_2020": 2.2, "degenerada_2020": False, "R_neto_mini": 0.02},
        {"variante": "W_a", "modulo": "W", "pasa_desc": False, "R_por_mes": -1.0, "t_ses": -2.0,
         "pasa_desc_2020": True, "R_neto_2020": 0.06, "R_mes_2020": 1.8, "t_ses_2020": 2.0, "degenerada_2020": False, "R_neto_mini": -0.04},
        {"variante": "A20_a", "modulo": "A20", "pasa_desc": False, "R_por_mes": -0.4, "t_ses": -1.0,
         "pasa_desc_2020": True, "R_neto_2020": 0.11, "R_mes_2020": 1.7, "t_ses_2020": 2.3, "degenerada_2020": False, "R_neto_mini": -0.02},
        {"variante": "C_a", "modulo": "C", "pasa_desc": False, "R_por_mes": 0.1, "t_ses": 0.8,
         "pasa_desc_2020": True, "R_neto_2020": 0.14, "R_mes_2020": 1.1, "t_ses_2020": 2.1, "degenerada_2020": False, "R_neto_mini": 0.03},
        {"variante": "Q_a", "modulo": "Q", "pasa_desc": False, "R_por_mes": -0.9, "t_ses": -1.5,
         "pasa_desc_2020": True, "R_neto_2020": 0.05, "R_mes_2020": 0.9, "t_ses_2020": 2.0, "degenerada_2020": False, "R_neto_mini": -0.05},
    ])
    fin = mod._seleccionar_finalistas_b4(df_b)
    assert len(fin) == 6
    assert fin[0] == "F_a"
    assert "S_b" not in fin  # un finalista por modulo distinto
    assert fin == ["F_a", "S_a", "W_a", "A20_a", "V_a", "C_a"]


def test_compuerta_k51_y_resumen_r() -> None:
    mod = importlib.import_module("tools.fundedsync_post_il_cadena")
    mod.asegurar_compuerta()

    ops = pd.DataFrame({
        "fecha_int": [20250201 + i for i in range(10)],
        "mes": ["2025-02"] * 10,
        "R_bruto": [0.3, 0.7, 0.5, 0.6, 0.4, 0.8, 0.35, 0.65, 0.55, 0.45],
        "R_neto_mini": [0.2, 0.6, 0.4, 0.5, 0.3, 0.7, 0.25, 0.55, 0.45, 0.35],
        "R_neto_micro": [0.18, 0.58, 0.38, 0.48, 0.28, 0.68, 0.23, 0.53, 0.43, 0.33],
        "fric_R": [0.1] * 10,
    })
    st = mod.resumir_serie_r(ops, meses_totales=1)
    assert st["n"] == 10
    assert st["R_neto_mini"] == pytest.approx(0.43)
    assert st["p_boot"] < 0.05
