"""Pruebas deterministas offline para iteracion 3 FUNDEDSYNC (multi-activo y adaptacion Oro GC)."""
from __future__ import annotations

import importlib

import pandas as pd
import pytest


def test_presupuesto_grillas_y_compuerta_k51() -> None:
    mod = importlib.import_module("tools.fundedsync_multiactivo_oro")
    mod.asegurar_compuerta_iter3()
    b1 = mod.specs_etapa_b1_oro()
    b2 = mod.specs_etapa_b2_indices()
    gc_nuc = mod._specs_etapa_a_gc_nucleo()
    assert len(b1) == 60
    assert len(b2) == 48
    assert len(gc_nuc) == 7
    assert len({s["variante"] for s in b1}) == 60
    assert len({s["variante"] for s in b2}) == 48


def test_friccion_mgc_y_escala_gc_indices() -> None:
    mod = importlib.import_module("tools.fundedsync_multiactivo_oro")
    fgc, fmgc = mod.friccion_multiactivo("GC")
    assert fgc == pytest.approx(0.605, abs=0.01)
    assert fmgc == pytest.approx(0.692, abs=0.01)

    frty, mrty = mod.friccion_multiactivo("RTY")
    assert frty > 0.0
    assert mrty is None

    femd, memd = mod.friccion_multiactivo("EMD")
    assert femd > 0.0
    assert memd is None

    b1 = {s["variante"]: s for s in mod.specs_etapa_b1_oro()}
    assert b1["T_gc_comex1330_m100"]["orb_win"] == (510, 525)
    assert b1["T_gc_lon0300_m100"]["orb_win"] == (180, 195)
    assert b1["V_gc_nm30_raw"]["params"]["profit_target_usd_per_contract"] == pytest.approx(200.0)

    b2 = {s["variante"]: s for s in mod.specs_etapa_b2_indices()}
    # YM tiene ATR ~421 pts: T_scaled_100 debe desbloquear stop_max_points > 200 (vs 100 fabrica)
    assert b2["YM__T_scaled_100"]["params"]["stop_max_points"] > 200.0
    assert b2["YM__T_scaled_100"]["stop_max_pts"] > 200.0


def test_convertir_ops_activo_usa_mgc_orb_y_bloquea_terminal() -> None:
    mod = importlib.import_module("tools.fundedsync_multiactivo_oro")
    df_t = pd.DataFrame({
        "side": [1, -1],
        "qty": [1, 1],
        "entry_time_utc": ["2025-02-10T14:00:00Z", "2026-10-02T14:00:00Z"],
        "exit_time_utc": ["2025-02-10T15:30:00Z", "2026-10-02T15:30:00Z"],
        "entry_price": [2800.0, 2900.0],
        "stop_price": [2792.0, 2908.0],
        "pnl_pts": [10.0, 12.0],
        "pnl_usd": [1000.0, 1200.0],
        "mae_usd": [200.0, 0.0],
        "mfe_usd": [1100.0, 1200.0],
    })
    dates = pd.to_datetime(["2025-02-10", "2026-10-02"])
    atr_ses = pd.Series([27.0, 27.0], index=dates)
    orb_raw = pd.Series([6.0, 6.0], index=dates)
    ops = mod.convertir_ops_activo(
        df_t, "T", "GC", atr_ses, orb_raw, 100.0,
        stop_orb_mult=1.0, stop_min_pts=0.5, stop_max_pts=15.0,
    )
    assert len(ops) == 1
    assert ops["a5"].iloc[0] == "DESC"
    assert ops["riesgo_pts"].iloc[0] == pytest.approx(6.0)
    assert ops["R_neto_mini"].iloc[0] == pytest.approx((10.0 - 0.605) / 6.0, abs=1e-3)
    assert ops["R_neto_micro"].iloc[0] == pytest.approx((10.0 - 0.692) / 6.0, abs=1e-3)


def test_clasificador_etapa_a_distingue_multi_activo_vs_nq_vs_oro() -> None:
    mod = importlib.import_module("tools.fundedsync_multiactivo_oro")
    rows = []
    for m, inst, d_r, r_r in (
        ("R", "NQ", 0.40, 0.25), ("R", "ES", 0.15, 0.10),
        ("T", "NQ", 0.15, 0.08),
        ("E", "GC", 0.12, 0.09),
    ):
        rows.append({"modulo": m, "instrumento": inst, "variante": "fabrica", "periodo": "POST_2020", "particion_a5": "DESC", "n": 50, "R_neto_mini": d_r, "med_fric_R": 0.03})
        rows.append({"modulo": m, "instrumento": inst, "variante": "fabrica", "periodo": "POST_2020", "particion_a5": "REP", "n": 15, "R_neto_mini": r_r, "med_fric_R": 0.03})
    res = mod._clasificar_etapa_a(pd.DataFrame(rows))
    assert res["R"]["categoria"] == "MULTI_ACTIVO"
    assert res["T"]["categoria"] == "ESPECIFICO_NQ"
    assert res["E"]["categoria"] == "ORO_NATIVO"
    assert res["Q"]["categoria"] == "SIN_VENTAJA_BASE"
