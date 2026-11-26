"""Pruebas deterministas offline para vectorizacion v2, paridad OOS y perfiles de `fundedsyncstack`."""
from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from edgelab.research import fundedsyncstack as fs
from edgelab.research.fundedsyncstack import paridad_vendedor as pv
from edgelab.research.fundedsyncstack import vectorizar_vendedor as vv


def _synth_m1_df(n_bars: int = 300) -> pd.DataFrame:
    ts = pd.date_range("2025-01-02 14:30:00", periods=n_bars, freq="1min", tz="UTC")
    base = 21000.0 + np.cumsum(np.sin(np.arange(n_bars) * 0.2) * 2.5)
    return pd.DataFrame({
        "datetime": ts,
        "open": base,
        "high": base + 3.0,
        "low": base - 3.0,
        "close": base + 0.5,
        "volume": np.full(n_bars, 250.0),
    })


def test_csv_v2_cargable_y_sin_saltos_internos() -> None:
    df_v2 = pd.read_csv(pv.DEFAULT_CSV_V2)
    assert len(df_v2) >= 4000
    assert df_v2["estrategia"].nunique() == 14
    for (_, _), seg in df_v2.groupby(["estrategia", "segmento_id"]):
        diffs = seg["y_grid_unidades"].diff().abs().dropna()
        assert (diffs <= 0.15).all(), "Se detecto un salto interno en segmento limpio v2"

    mods_14 = ("A1", "E", "S", "T", "V", "W", "Z", "A20", "C", "F", "O", "P", "Q", "R")
    for mod in mods_14:
        curva = pv.cargar_curva_vendedor(pv.DEFAULT_CSV_V2, mod)
        assert len(curva) >= 50


def test_gemini_csv_filtra_outliers_bc() -> None:
    c_crudo = pv.cargar_curva_vendedor(pv.DEFAULT_CSV_GEMINI, "C", filtrar_saltos=False)
    c_limpio = pv.cargar_curva_vendedor(pv.DEFAULT_CSV_GEMINI, "C", filtrar_saltos=True)
    assert c_crudo["y_vendedor"].max() > 2.0
    assert c_limpio["y_vendedor"].max() < 0.8


def test_evaluar_paridad_y_desambiguacion_teal() -> None:
    vend_t = pv.cargar_curva_vendedor(pv.DEFAULT_CSV_V2, "T")
    vend_s = pv.cargar_curva_vendedor(pv.DEFAULT_CSV_V2, "S")

    def _a_serie(df_v: pd.DataFrame) -> pd.DataFrame:
        cal = pd.date_range("2021-09-15", "2026-04-30", freq="D")
        interp = np.interp(
            cal.to_numpy(dtype="datetime64[D]").astype(float),
            df_v["fecha"].to_numpy(dtype="datetime64[D]").astype(float),
            df_v["y_vendedor"].to_numpy(dtype=float),
        )
        pnl = np.diff(np.concatenate([[interp[0]], interp])) * 1000.0
        return pd.DataFrame({"fecha": cal, "pnl_diario": pnl})

    serie_t = _a_serie(vend_t)
    serie_s = _a_serie(vend_s)

    ev = pv.evaluar_paridad_variantes("T", {"exacta": serie_t, "cruzada": serie_s}, csv_vendedor=pv.DEFAULT_CSV_V2)
    assert ev.iloc[0]["config"] == "exacta"
    assert ev.iloc[0]["score_pre"] > 0.90
    assert bool(ev.iloc[0]["pasa_oos"]) is True

    teal_res = pv.resolver_identidad_teal(serie_s, serie_t, csv_vendedor=pv.DEFAULT_CSV_V2)
    assert teal_res["asignacion"] == {"S": "TEAL_LOWER", "T": "TEAL_UPPER"}


def test_holdout_firewall_en_serie_diaria() -> None:
    trades = pd.DataFrame({
        "qty": [1, 1],
        "exit_time_utc": ["2026-09-29T18:00:00Z", "2026-10-01T15:00:00Z"],
        "pnl_pts": [10.0, 999.0],
        "pnl_usd": [200.0, 19980.0],
    })
    with pytest.raises(ValueError, match="HOLDOUT-A4"):
        pv.serie_diaria_desde_trades(trades, hasta="2026-10-01")
    with pytest.raises(ValueError, match="HOLDOUT-A4"):
        pv.serie_diaria_desde_trades(trades, desde="2026-10-01", hasta="2026-10-02")

    s = pv.serie_diaria_desde_trades(trades, modo="bruto_1cto", desde="2026-09-25", hasta="2026-09-30")
    assert pytest.approx(s["pnl_diario"].sum()) == 200.0


def test_perfiles_il_fabrica_intacto_y_api_correr(monkeypatch: pytest.MonkeyPatch) -> None:
    for tag, cls in fs.CONFIG_CLASSES.items():
        cfg_il = pv.obtener_config_modulo(tag, perfil="il_fabrica")
        assert cfg_il == cls()

    with pytest.raises(ValueError, match="Perfil desconocido"):
        pv.obtener_config_modulo("F", perfil="inexistente")

    # Verificar overrides reales promovidos por validacion OOS sin alterar il_fabrica
    for mod_prom in ("O", "S", "W", "C"):
        assert mod_prom in pv.VENDOR_PARITY_OVERRIDES
        assert pv.VENDOR_PARITY_OVERRIDES[mod_prom]["parametros"]
    assert pv.obtener_config_modulo("O", perfil="il_fabrica").use_rth_range_filter is True
    assert pv.obtener_config_modulo("O", perfil="vendedor_calibrado").use_rth_range_filter is False
    assert pv.obtener_config_modulo("C", perfil="il_fabrica").minimum_gap_points == 2.0
    assert pv.obtener_config_modulo("C", perfil="vendedor_calibrado").minimum_gap_points == 10.0

    # Simular un override en memoria sin contaminar defaults de fabrica
    monkeypatch.setitem(
        pv.VENDOR_PARITY_OVERRIDES,
        "F",
        {"parametros": {"disable_delta_filter": True}},
    )
    assert pv.obtener_config_modulo("F", perfil="il_fabrica").disable_delta_filter is False
    assert pv.obtener_config_modulo("F", perfil="vendedor_calibrado").disable_delta_filter is True

    df_m1 = _synth_m1_df(320)
    ms = fs.build_multi_series(df_m1, tz_input="UTC", allow_sellado=False)
    df_il = fs.correr_modulo("F", ms, perfil="il_fabrica")
    df_cal = fs.correr_modulo("F", ms, perfil="vendedor_calibrado")
    assert isinstance(df_il, pd.DataFrame)
    assert isinstance(df_cal, pd.DataFrame)

    # Verifica compatibilidad de firma en correr_todos con perfil
    res_cal = fs.correr_todos(ms, perfil="vendedor_calibrado", incluir_cartera=False)
    assert len(res_cal["por_modulo"]) == 15


def test_limpiar_segmentos_v2_elimina_picos() -> None:
    xs = np.arange(100, 120)
    ys = np.full(20, 0.50, dtype=float)
    ys[10] = 1.90  # pico aislado de 1 pixel
    df_raw = pd.DataFrame({
        "estrategia": "B · C",
        "fecha": pd.date_range("2023-01-01", periods=20, freq="D").strftime("%Y-%m-%d"),
        "x_px": xs,
        "y_px": 385.0 - ys * 82.5,
        "y_grid_unidades": ys,
        "margen_color": 0.05,
    })
    clean = vv._limpiar_segmentos_y_saltos(df_raw)
    assert len(clean) == 19
    assert clean["y_grid_unidades"].max() < 0.60


def test_fundedsync_cadena_construir_embebe_paridad_y_pasa_puerta_kernel() -> None:
    import ast
    import importlib
    from edgelab.research.puerta_kernel import validar_script_kernel

    fc = importlib.import_module("tools.fundedsync_cadena")
    assert "paridad_vendedor" in fc.ORDEN
    assert fc.ORDEN.index("paridad_vendedor") < fc.ORDEN.index("__init__")

    kernel_path = fc.construir()
    txt = kernel_path.read_text(encoding="utf-8")
    ast.parse(txt)
    assert "edgelab.research.fundedsyncstack.paridad_vendedor" in txt
    assert validar_script_kernel(txt, require_canonical=True) == []
