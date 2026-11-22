"""Pruebas deterministas offline para iteracion 4 FUNDEDSYNC (overlay M1 causal, hibrido NQ/MNQ, prop firm intradia, K51)."""
from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest


def test_presupuesto_68_pruebas_y_compuerta_k51() -> None:
    mod = importlib.import_module("tools.fundedsync_prop_opt")
    mod.asegurar_compuerta_iter4()
    s1 = mod.specs_etapa1_iter4()
    s2 = mod.planes_etapa2_iter4("P_OPT")
    assert len(s1) == 44
    assert len(s2) == 24
    assert len({x["variante"] for x in s1}) == 44
    assert len({x["plan_id"] for x in s2}) == 24


def test_overlay_m1_causal_be_gap_y_bloqueo_holdout() -> None:
    mod = importlib.import_module("tools.fundedsync_prop_opt")
    # 5 barras M1 en NY: 10:00..10:04 -> UTC naive +5/+4
    t_ny = pd.date_range("2025-02-10 10:00:00", periods=6, freq="1min")
    ts_ns = mod._idx_utc_ns(t_ny.tz_localize("America/New_York").tz_convert("UTC"))
    # Trade long entrada 20000 en 10:00, riesgo 50 pts (BE trigger +1.0R = 20050 en barra 10:01)
    # En 10:01 h=20060 >= 20050 y l=19995 -> NO debe saltar en BE en 10:01 (causal recien desde 10:02!)
    # En 10:02 l=19999 -> ahora SI salta BE exacto a 20000.0
    m1 = {
        "ts_ns": ts_ns,
        "o": np.array([20000.0, 20010.0, 20040.0, 20020.0, 20030.0, 20040.0]),
        "h": np.array([20020.0, 20060.0, 20045.0, 20025.0, 20035.0, 20050.0]),
        "l": np.array([19990.0, 19995.0, 19999.0, 20010.0, 20020.0, 20030.0]),
        "c": np.array([20010.0, 20040.0, 20010.0, 20020.0, 20030.0, 20045.0]),
    }
    t0 = pd.Timestamp(int(ts_ns[0]), unit="ns", tz="UTC")
    t_ex = pd.Timestamp(int(ts_ns[4]), unit="ns", tz="UTC")
    t_hold = pd.Timestamp("2026-10-02T14:00:00Z")
    df_t = pd.DataFrame({
        "side": [1, 1],
        "qty": [1, 1],
        "entry_time_utc": [t0, t_hold],
        "exit_time_utc": [t_ex, t_hold + pd.Timedelta(minutes=30)],
        "entry_price": [20000.0, 21000.0],
        "exit_price": [20030.0, 21100.0],
        "stop_price": [19950.0, 20950.0],
        "exit_name": ["EOD", "EOD"],
        "pnl_pts": [30.0, 100.0],
    })
    dates = pd.to_datetime(["2025-02-10", "2026-10-02"])
    atr = pd.Series([200.0, 200.0], index=dates)
    orb = pd.Series([50.0, 50.0], index=dates)

    ops = mod.aplicar_overlay_m1_causal(df_t, "W", atr, orb, 20.0, m1, sl_atr_k=0.25, be_trigger_r=1.0)
    assert len(ops) == 1
    assert ops["a5"].iloc[0] == "DESC"
    assert ops["riesgo_pts"].iloc[0] == pytest.approx(50.0)
    # Salio exactamente en 20000.0 (barra 10:02) tras activar BE al cierre de 10:01
    assert ops["pnl_pts"].iloc[0] == pytest.approx(0.0)
    assert ops["ex_ns"].iloc[0] == ts_ns[2]
    assert ops["mfe_pts"].iloc[0] == pytest.approx(60.0)


def test_hibrido_nq_mnq_y_calibracion_prop_firm_intradia() -> None:
    mod = importlib.import_module("tools.fundedsync_prop_opt")
    n_nq, n_mnq, save10 = mod.calcular_ahorro_hibrido_nq_mnq(10, 1.5455, 1.9775)
    assert (n_nq, n_mnq) == (1, 0)
    assert save10 == pytest.approx(8.64, abs=1e-6)
    _, _, save9 = mod.calcular_ahorro_hibrido_nq_mnq(9, 1.5455, 1.9775)
    assert save9 == pytest.approx(0.0)

    # Calibracion determinista del motor intradia (evaluacion, colchon, DLL, eval_cap_cons)
    # 1) DLL recorta perdida intradia sin quemar al instante pero quema en 2 dias
    P_dll = np.array([-300.0] * 10, dtype=np.float64)
    LO_dll = np.array([-900.0] * 10, dtype=np.float64)
    pasa, quema, cob, _, _, _ = mod._trayectoria_cuenta_intradia(
        P_dll, LO_dll, P_dll, LO_dll, P_dll, LO_dll, P_dll, LO_dll,
        0.0, 0.0, 1, 1, 20, 1250.0, 1000.0, 600.0, 100.0, 1000.0, 0.50, True, 0.0, False,
    )
    assert pasa[0] == 0 and quema[0] == 1 and cob[0] == 0.0

    # 2) Dia windfall +1500 y cuatro de +500 (ciclo 5 -> 3500 total, mayor/bal=42.86% > 40%): con cap pasa!
    P_win = np.array([1500.0, 500.0, 500.0, 500.0, 500.0], dtype=np.float64)
    LO_win = np.zeros_like(P_win)
    p_nocap, _, _, _, d_nocap, _ = mod._trayectoria_cuenta_intradia(
        P_win, LO_win, P_win, LO_win, P_win, LO_win, P_win, LO_win,
        0.0, 0.0, 1, 7, 5, 3000.0, 2000.0, 1200.0, 150.0, 2000.0, 0.40, True, 0.0, False,
    )
    assert p_nocap[0] == 0 and d_nocap[0] == 0  # bloqueado por cons 40% en los 5 dias
    pasa_cap, _, _, _, d_cap, _ = mod._trayectoria_cuenta_intradia(
        P_win, LO_win, P_win, LO_win, P_win, LO_win, P_win, LO_win,
        0.0, 0.0, 1, 7, 5, 3000.0, 2000.0, 1200.0, 150.0, 2000.0, 0.40, True, 0.0, True,
    )
    assert pasa_cap[0] == 1 and d_cap[0] == 5

    # 3) Colchon minimo evita retirar con solo $400 sobre el piso +$100
    P_f = np.array([500.0] * 30, dtype=np.float64)
    LO_f = np.zeros_like(P_f)
    _, _, _, nr_nocol, _, _ = mod._trayectoria_cuenta_intradia(
        P_f, LO_f, P_f, LO_f, P_f, LO_f, P_f, LO_f,
        0.0, 0.0, 1, 2, 40, 1250.0, 1000.0, 600.0, 100.0, 1000.0, 0.50, False, 0.0, False,
    )
    assert nr_nocol[0] == 5
    _, _, cob_col, nr_col, _, _ = mod._trayectoria_cuenta_intradia(
        P_f, LO_f, P_f, LO_f, P_f, LO_f, P_f, LO_f,
        0.0, 0.0, 1, 2, 40, 1250.0, 1000.0, 600.0, 100.0, 1000.0, 0.50, False, 1000.0, False,
    )
    assert nr_col[0] >= 1 and cob_col[0] > 0.0

    # 4) Reinyectar mae_pts (> 0 incluso en ganador) y R_bruto tras IT2.aplicar_tope_concurrencia_causal + LO <= min(0, P)
    import fundedsync_iter2_cartera as IT2
    ops_s = {
        "S1": pd.DataFrame({
            "fecha_int": [20250210],
            "mes": ["2025-02"],
            "en_ns": [1000],
            "ex_ns": [5000],
            "side": [1],
            "riesgo_pts": [50.0],
            "R_bruto": [1.5],
            "R_neto_mini": [1.5 - 1.5455 / 50.0],
            "R_neto_micro": [1.5 - 1.9775 / 50.0],
            "mae_pts": [35.0],  # trade ganador que sufrió -35 pts intradia
        })
    }
    tr_conc, _ = IT2.aplicar_tope_concurrencia_causal(ops_s, {"S1": 1.0}, None, cap_r=3.0)
    tr_ok = mod._reinyectar_mae_y_bruto(tr_conc, ops_s, 1.5455)
    assert tr_ok["mae_pts"].iloc[0] == pytest.approx(35.0)
    assert tr_ok["R_bruto"].iloc[0] == pytest.approx(1.5)
    P_d, LO_d, _ = mod.construir_serie_intradia_prop(tr_ok, [20250210, 20250211], 200.0, 40, False, 1.5455, 1.9775)
    assert P_d[0] > 0.0 and LO_d[0] < -100.0 and LO_d[0] <= min(0.0, P_d[0])
    assert P_d[1] == 0.0 and LO_d[1] == 0.0
