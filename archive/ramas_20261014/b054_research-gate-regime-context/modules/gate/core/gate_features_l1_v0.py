"""Features L1/tape causales del reemplazo GATE v0.

La barra [HH:MM, HH:MM+1) se publica en HH:MM+1. No calcula OFI ni VPIN:
con last/bid/ask/volume sólo se declaran tape imbalance, spread, actividad,
volatilidad realizada y efficiency ratio.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_TICK_COLUMNS = (
    "ts_utc_ns", "price_ticks", "bid_ticks", "ask_ticks", "volume",
    "instrument", "contract", "cme_session",
)
IDENTITY = ["instrument", "contract", "cme_session"]


def build_l1_minute_features(ticks: pd.DataFrame, *, rv_window: int = 15,
                             efficiency_window: int = 10) -> pd.DataFrame:
    missing = [c for c in REQUIRED_TICK_COLUMNS if c not in ticks.columns]
    if missing:
        raise ValueError(f"ticks: faltan columnas {missing}")
    if len(ticks) == 0:
        raise ValueError("ticks vacío")
    if rv_window < 2 or efficiency_window < 2:
        raise ValueError("ventanas deben ser >= 2")

    t = ticks.loc[:, list(REQUIRED_TICK_COLUMNS)].copy()
    for key in IDENTITY:
        t[key] = t[key].astype(str)
    t["timestamp"] = pd.to_datetime(
        pd.to_numeric(t["ts_utc_ns"], errors="raise").astype("int64"), unit="ns", utc=True
    )
    for col in ("price_ticks", "bid_ticks", "ask_ticks", "volume"):
        t[col] = pd.to_numeric(t[col], errors="raise")
    if (t["ask_ticks"] < t["bid_ticks"]).any():
        raise ValueError("ticks: ask_ticks < bid_ticks")
    if (t["volume"] <= 0).any():
        raise ValueError("ticks: volume debe ser > 0")

    t = t.sort_values(IDENTITY + ["timestamp"], kind="mergesort").reset_index(drop=True)
    t["minute_start"] = t["timestamp"].dt.floor("min")
    t["mid_ticks"] = (t["bid_ticks"].astype(float) + t["ask_ticks"].astype(float)) / 2.0
    t["spread_ticks"] = (t["ask_ticks"] - t["bid_ticks"]).astype(float)
    quote_valid = t["ask_ticks"] > t["bid_ticks"]
    side = np.where(
        quote_valid & (t["price_ticks"] >= t["ask_ticks"]), 1.0,
        np.where(quote_valid & (t["price_ticks"] <= t["bid_ticks"]), -1.0, 0.0),
    )
    t["signed_volume"] = side * t["volume"].astype(float)

    grouped = t.groupby(IDENTITY + ["minute_start"], sort=True, dropna=False)
    bars = grouped.agg(
        data_window_end=("timestamp", "max"),
        mid_open_ticks=("mid_ticks", "first"),
        mid_close_ticks=("mid_ticks", "last"),
        spread_ticks_mean=("spread_ticks", "mean"),
        volume=("volume", "sum"),
        signed_volume=("signed_volume", "sum"),
        tick_count=("timestamp", "size"),
    ).reset_index()
    bars["feature_available_at"] = bars["minute_start"] + pd.Timedelta(minutes=1)
    bars["tick_rate_per_second"] = bars["tick_count"].astype(float) / 60.0
    bars["tape_imbalance"] = (
        bars["signed_volume"] / bars["volume"].replace(0, np.nan)
    ).clip(-1.0, 1.0)
    bars = bars.sort_values(IDENTITY + ["minute_start"], kind="mergesort").reset_index(drop=True)

    by_identity = bars.groupby(IDENTITY, sort=False, dropna=False)
    bars["mid_return_ticks"] = by_identity["mid_close_ticks"].diff()
    bars[f"rv_ticks_{rv_window}m"] = by_identity["mid_return_ticks"].transform(
        lambda s: s.rolling(rv_window, min_periods=min(5, rv_window)).std(ddof=0)
    )
    shifted = by_identity["mid_close_ticks"].shift(efficiency_window)
    net = (bars["mid_close_ticks"] - shifted).abs()
    path = by_identity["mid_return_ticks"].transform(
        lambda s: s.abs().rolling(efficiency_window, min_periods=efficiency_window).sum()
    )
    bars[f"efficiency_ratio_{efficiency_window}m"] = (
        net / path.replace(0, np.nan)
    ).clip(0.0, 1.0)

    if (bars["data_window_end"] > bars["feature_available_at"]).any():
        raise AssertionError("feature publicada antes del fin de su ventana")
    forbidden = {"ofi", "ofi_z", "ofi_ema_z", "vpin"}
    if forbidden & set(bars.columns):
        raise AssertionError("se reintrodujo un nombre de microestructura no medido")
    return bars
