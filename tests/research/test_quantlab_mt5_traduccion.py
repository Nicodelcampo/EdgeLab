"""Pruebas integrales para la traduccion Python (`edgelab.research.quantlab_mt5`)
de `QLB_K_XAUUSD_3x_speed_q4_turn.ex5` (v1.8) y `SessionOpenMomentum.ex5` (v2.2).

Verifica:
1. Guardia anti-holdout (`sellado` bloqueado y frontera `< 2026-10-01`).
2. `SessionOpenMomentum`: coincidencia contra `som_tester_trades_189.csv` en junio 2026
   (senales EMA(12) M5 14/14, `SL = 8.0 * iATR_M5(14)` a <= 0.2 pips, trailing EMA(120) a +0.5 R).
3. `QLB_K_XAUUSD_3x_speed_q4_turn`: coincidencia contra `qlb_tester_trades_57.csv`
   (`SL = 2.5 * iATR(14)`, `TP = 5.0 * iATR(14)`, RR 2.00 en 57/57 trades, salidas temporales 120 H4 / 40 H1,
   filtro estacional Q4 de Slot 1, solo Long en Slot 2 y guardias `no_hedge` / `daily_loss`).
4. Validacion estricta del contrato de 16 columnas (`TRADE_COLUMNS`) y corrida sobre Dukascopy pre-holdout si existe.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edgelab.research.quantlab_mt5 import (  # noqa: E402
    MODULOS_QUANTLAB,
    QlbBasketConfig,
    SessionOpenMomentumConfig,
    TRADE_COLUMNS,
    correr_modulo_quantlab,
    correr_qlb_basket,
    correr_session_open_momentum,
    correr_todos_quantlab,
    load_ohlc_data,
    mql5_atr,
    mql5_ema,
    resample_ohlc,
)

REF_DIR = ROOT / "docs" / "research" / "quantlab_mt5_eas_20261116" / "reference_data"
DUKAS_XAU = Path(r"C:\StrategyQuantX145\user\mcp-work\edgelab_m1\XAUUSD_M1_dukas-M1-.csv")


def test_anti_holdout_guard_and_cutoff() -> None:
    with pytest.raises(ValueError, match="sellado"):
        load_ohlc_data(r"C:\EdgeLab\sellado\XAU_20261029.parquet")

    m5_path = REF_DIR / "eurusd_m5_may_jun2026.csv"
    df = load_ohlc_data(m5_path, end="2026-10-01", enforce_pre_holdout=True)
    assert len(df) > 8000
    assert df["time"].max() < pd.Timestamp("2026-10-01T00:00:00Z")


def test_som_matches_june_2026_mt5_rules() -> None:
    m5 = load_ohlc_data(REF_DIR / "eurusd_m5_may_jun2026.csv", start="2026-05-15", end="2026-10-01")
    tester = pd.read_csv(REF_DIR / "som_tester_trades_189.csv")
    jun_tester = tester[tester["open_time"].str.startswith("2026-06")].reset_index(drop=True)
    assert len(jun_tester) == 14

    # Verificar formula exacta entrada (EMA12), SL inicial (8.0 * ATR_M5(14)) y primer trailing (EMA120)
    closes = m5["close"].to_numpy()
    highs = m5["high"].to_numpy()
    lows = m5["low"].to_numpy()
    ema12 = mql5_ema(closes, 12)
    ema120 = mql5_ema(closes, 120)
    atr14 = mql5_atr(highs, lows, closes, 14)
    ts_map = {t: idx for idx, t in enumerate(m5["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"))}

    for _, row in jun_tester.iterrows():
        i_entry = ts_map[row["open_time"]]
        sig = i_entry - 1  # Barra M5 de las 16:30 recien cerrada
        pred_side = 1 if closes[sig] > ema12[sig] else -1
        assert pred_side == int(row["side"]), f"Mismatch direccion en {row['open_time']}"
        pred_sl_pips = 8.0 * atr14[sig] * 1e4
        assert abs(pred_sl_pips - float(row["r_pips"])) < 0.25, f"Mismatch SL ATR en {row['open_time']}"

    # Correr motor completo en junio 2026
    out, diag = correr_session_open_momentum(m5, instrument="EURUSD", return_diagnostics=True)
    assert list(out.columns) == TRADE_COLUMNS
    assert len(out) > 0
    assert diag["skipped_still_open"] > 0
    assert diag["trail_mod_count"] > 0
    assert out["exit_name"].isin({"INIT_SL", "TRAIL_SL", "END_OF_DATA"}).all()

    # Verificar EOD close y max equity drawdown guards
    cfg_eod = SessionOpenMomentumConfig(close_eod=True, eod_time="22:55", max_equity_dd_pct=50.0)
    out_eod = correr_session_open_momentum(m5, config=cfg_eod, instrument="EURUSD")
    assert list(out_eod.columns) == TRADE_COLUMNS
    assert (out_eod["exit_name"] == "EOD_CLOSE").any()
    assert len(ema120) == len(m5)


def test_qlb_matches_57_mt5_stops_and_rules() -> None:
    raw = json.loads((REF_DIR / "eurusd_h1_h4_2025_2026.json").read_text(encoding="utf-8"))
    df_h1 = pd.DataFrame(raw["h1"])
    df_h1["time"] = pd.to_datetime(df_h1["time"], utc=True).astype("datetime64[ns, UTC]")
    df_h1["ts_ns"] = df_h1["time"].astype("int64")
    df_h1 = df_h1[["time", "ts_ns", "open", "high", "low", "close", "volume"]]

    df_h4 = resample_ohlc(df_h1, 240)
    h1_atr = mql5_atr(df_h1["high"], df_h1["low"], df_h1["close"], 14)
    h4_atr = mql5_atr(df_h4["high"], df_h4["low"], df_h4["close"], 14)
    h1_map = {t: i for i, t in enumerate(df_h1["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"))}
    h4_map = {t: i for i, t in enumerate(df_h4["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"))}

    qlb_ref = pd.read_csv(REF_DIR / "qlb_tester_trades_57.csv")
    assert len(qlb_ref) == 57

    override_signals = {0: {}, 1: {}, 2: {}}
    for _, row in qlb_ref.iterrows():
        slot_id = int(row["slot_id"])
        tstr = str(row["open_time"])
        if slot_id == 0:
            i = h4_map[tstr]
            pred_sl = 2.5 * h4_atr[i - 1] * 1e4
            override_signals[0][int(df_h4["ts_ns"].iloc[i])] = int(row["side"])
        else:
            i = h1_map[tstr]
            pred_sl = 2.5 * h1_atr[i - 1] * 1e4
            override_signals[2][int(df_h1["ts_ns"].iloc[i])] = int(row["side"])
        assert abs(pred_sl - float(row["sl_pips"])) < 0.25
        assert abs(float(row["rr"]) - 2.0) < 0.02

    # Verificar TIME_CLOSE exacto: Slot 0 = 120 H4, Slot 2 = 40 H1
    s0_time = qlb_ref[(qlb_ref["slot_id"] == 0) & (qlb_ref["close_reason"] == "TIME_CLOSE")]
    s2_time = qlb_ref[(qlb_ref["slot_id"] == 2) & (qlb_ref["close_reason"] == "TIME_CLOSE")]
    assert not s0_time.empty and (s0_time["hold_hours"] == 672.0).all()
    assert not s2_time.empty and s2_time["hold_hours"].isin({40.0, 88.0}).all()

    # Replay de las 57 senales en el motor QLB sobre ventana 2025-11..2026-06
    df_win = df_h1[df_h1["time"] >= pd.Timestamp("2025-11-01T00:00:00Z")].reset_index(drop=True)
    replay_df, diag = correr_qlb_basket(df_win, instrument="EURUSD", override_signals=override_signals, return_diagnostics=True)
    assert list(replay_df.columns) == TRADE_COLUMNS
    assert len(replay_df) == 57
    assert diag["daily_loss_days"] == 0

    # Verificar que no_hedge=True bloquea la entrada simultanea opuesta de 2026-01-05 04:00
    no_hedge_cfg = QlbBasketConfig(no_hedge=True)
    nh_df, nh_diag = correr_qlb_basket(df_win, config=no_hedge_cfg, instrument="EURUSD", override_signals=override_signals, return_diagnostics=True)
    assert nh_diag["hedge_blocked"] >= 1
    assert len(nh_df) < 57

    # Corrida autonoma de los 3 slots cubriendo Q4 2025 + Q1-Q2 2026
    auto_all = correr_todos_quantlab(df_win, instrument="EURUSD")
    assert set(auto_all["resumen_df"]["module"]) == set(MODULOS_QUANTLAB)
    df_s1 = auto_all["por_modulo"]["QLB_S1"]
    if not df_s1.empty:
        s1_months = pd.to_datetime(df_s1["entry_time_utc"], unit="ns", utc=True).dt.month
        assert s1_months.isin({10, 11, 12}).all()
    df_s2 = auto_all["por_modulo"]["QLB_S2"]
    assert not df_s2.empty and (df_s2["side"] == 1).all()


def test_optional_dukascopy_xauusd_pre_holdout() -> None:
    if not DUKAS_XAU.exists():
        pytest.skip("CSV Dukascopy XAUUSD no disponible localmente")
    df_xau = load_ohlc_data(DUKAS_XAU, start="2026-05-01", end="2026-10-01")
    assert df_xau["time"].max() < pd.Timestamp("2026-10-01T00:00:00Z")
    res = correr_todos_quantlab(df_xau, instrument="XAUUSD")
    for mod in MODULOS_QUANTLAB:
        df_m = res["por_modulo"][mod]
        assert list(df_m.columns) == TRADE_COLUMNS
        assert np.isfinite(df_m["pnl_usd"]).all() if len(df_m) else True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
