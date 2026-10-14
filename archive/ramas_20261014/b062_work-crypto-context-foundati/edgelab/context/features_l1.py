"""Features L1/tape honestas y causales para un futuro detector de contexto.

No produce estados ni entrena un modelo. Evita deliberadamente los nombres OFI y VPIN:
el input disponible sólo permite tape imbalance, spread, actividad, RV y eficiencia.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_REQUIRED = (
    "ts_utc_ns",
    "price_ticks",
    "bid_ticks",
    "ask_ticks",
    "volume",
    "instrument",
    "contract",
    "cme_session",
)
_KEYS = ["instrument", "contract", "cme_session"]


def build_l1_minute_features(
    ticks: pd.DataFrame,
    *,
    rv_window: int = 15,
    efficiency_window: int = 10,
) -> pd.DataFrame:
    """Agrega ticks a minutos cerrados y publica disponibilidad al fin del minuto.

    Un tick exactamente en ``HH:MM:00`` pertenece al minuto que termina en
    ``HH:MM+1:00``. Así nunca se publica una feature antes de haber visto sus datos.
    """
    missing = [c for c in _REQUIRED if c not in ticks.columns]
    if missing:
        raise ValueError(f"ticks: faltan columnas {missing}")
    if rv_window < 2 or efficiency_window < 2:
        raise ValueError("ventanas deben ser >= 2")
    if len(ticks) == 0:
        raise ValueError("ticks vacío")

    t = ticks.loc[:, list(_REQUIRED)].copy()
    for key in _KEYS:
        t[key] = t[key].astype(str)
    t["timestamp"] = pd.to_datetime(
        pd.to_numeric(t["ts_utc_ns"], errors="raise").astype("int64"),
        unit="ns",
        utc=True,
    )
    for col in ("price_ticks", "bid_ticks", "ask_ticks", "volume"):
        t[col] = pd.to_numeric(t[col], errors="raise")
    if (t["ask_ticks"] < t["bid_ticks"]).any():
        raise ValueError("ticks: ask_ticks < bid_ticks")
    if (t["volume"] <= 0).any():
        raise ValueError("ticks: volume debe ser > 0")

    t = t.sort_values(_KEYS + ["timestamp"], kind="mergesort").reset_index(drop=True)
    t["minute_start"] = t["timestamp"].dt.floor("min")
    t["mid_ticks"] = (t["bid_ticks"].astype(float) + t["ask_ticks"].astype(float)) / 2.0
    t["spread_ticks"] = (t["ask_ticks"] - t["bid_ticks"]).astype(float)
    valid_quote = t["ask_ticks"] > t["bid_ticks"]
    side = np.where(
        valid_quote & (t["price_ticks"] >= t["ask_ticks"]),
        1.0,
        np.where(valid_quote & (t["price_ticks"] <= t["bid_ticks"]), -1.0, 0.0),
    )
    t["signed_volume"] = side * t["volume"].astype(float)

    grouped = t.groupby(_KEYS + ["minute_start"], sort=True, dropna=False)
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
    bars = bars.sort_values(_KEYS + ["minute_start"], kind="mergesort").reset_index(drop=True)

    by_identity = bars.groupby(_KEYS, sort=False, dropna=False)
    bars["mid_return_ticks"] = by_identity["mid_close_ticks"].diff()
    rv_name = f"rv_ticks_{rv_window}m"
    bars[rv_name] = by_identity["mid_return_ticks"].transform(
        lambda s: s.rolling(rv_window, min_periods=min(5, rv_window)).std(ddof=0)
    )
    shifted = by_identity["mid_close_ticks"].shift(efficiency_window)
    net = (bars["mid_close_ticks"] - shifted).abs()
    path = by_identity["mid_return_ticks"].transform(
        lambda s: s.abs().rolling(
            efficiency_window, min_periods=efficiency_window
        ).sum()
    )
    bars[f"efficiency_ratio_{efficiency_window}m"] = (
        net / path.replace(0, np.nan)
    ).clip(0, 1)

    if (bars["data_window_end"] > bars["feature_available_at"]).any():
        raise AssertionError("feature publicada antes del fin de su ventana")
    return bars
