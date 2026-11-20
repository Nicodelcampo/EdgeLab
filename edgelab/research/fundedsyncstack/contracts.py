"""Contratos de datos e interfaz compartida para la traduccion Python de FUNDEDSYNCSTACK.

Todos los modulos (A1, A20, F, S, P, C, V, O, W, N, T, R, Z, E, Q) importan estas estructuras
y consumen `MultiSeriesContext` construido por `base_series.build_multi_series`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

TRADE_COLUMNS: List[str] = [
    "module",
    "side",          # +1 Long, -1 Short
    "qty",
    "entry_time_utc",
    "exit_time_utc",
    "entry_price",
    "exit_price",
    "stop_price",
    "target_price",
    "entry_name",
    "exit_name",
    "pnl_pts",
    "pnl_usd",
    "mae_usd",
    "mfe_usd",
    "bars",
]

TICK_SIZE_NQ: float = 0.25
POINT_VALUE_NQ: float = 20.0
POINT_VALUE_MNQ: float = 2.0


@dataclass
class BarSeries:
    """Una serie OHLCV derivada causalmente con marca de tiempo de cierre en UTC (ns) y calendarios CT/ET."""

    bip: int
    name: str
    timeframe_min: int  # 0 para Day
    ts_ns: np.ndarray        # int64 UTC cierre de barra (ns)
    open: np.ndarray         # float64
    high: np.ndarray         # float64
    low: np.ndarray          # float64
    close: np.ndarray        # float64
    volume: np.ndarray       # float64
    delta: np.ndarray        # float64 (bar delta firmado; real si viene en input, proxy si solo OHLCV)
    hhmmss_ct: np.ndarray    # int32 HHMMSS America/Chicago del timestamp de barra
    date_ct: np.ndarray      # int32 YYYYMMDD CME trade_date (Chicago + 7h) o calendario CT segun corresponda
    cal_date_ct: np.ndarray  # int32 YYYYMMDD fecha calendario Chicago
    dow_ct: np.ndarray       # int8 (0=Lun .. 6=Dom) America/Chicago
    hhmmss_et: np.ndarray    # int32 HHMMSS America/New_York del timestamp de barra
    cal_date_et: np.ndarray  # int32 YYYYMMDD fecha calendario America/New_York
    dow_et: np.ndarray       # int8 (0=Lun .. 6=Dom) America/New_York
    is_new_session: np.ndarray  # bool True cuando inicia nueva sesion respecto a la barra anterior
    m1_end_idx: np.ndarray   # int64 indice en m1_raw (bip1 / serie base M1) donde cierra esta barra


@dataclass
class MultiSeriesContext:
    """Contenedor de todas las series BIP 1..10 construidas desde M1 de NQ."""

    bip1: BarSeries   # 1m ETH
    bip2: BarSeries   # 3m ETH
    bip3: BarSeries   # 5m ETH
    bip4: BarSeries   # 20m ETH
    bip5: BarSeries   # 1m US STOCK (09:30-16:00 ET)
    bip6: BarSeries   # 5m RTH (08:30-15:15 CT / 09:30-16:15 ET)
    bip7: BarSeries   # 1d RTH
    bip8: BarSeries   # 1d ETH
    bip9: BarSeries   # 10m ETH
    bip10: BarSeries  # 15m ETH
    tick_size: float = TICK_SIZE_NQ
    point_value: float = POINT_VALUE_NQ
    has_real_delta: bool = False

    def get(self, bip: int) -> BarSeries:
        return getattr(self, f"bip{bip}")


@dataclass
class TradeRecord:
    module: str
    side: int
    qty: int
    entry_time_utc: int
    exit_time_utc: int
    entry_price: float
    exit_price: float
    stop_price: float
    target_price: float
    entry_name: str
    exit_name: str
    pnl_pts: float
    pnl_usd: float
    mae_usd: float = 0.0
    mfe_usd: float = 0.0
    bars: int = 1


def trades_to_df(trades: List[TradeRecord]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame(columns=TRADE_COLUMNS)
    df = pd.DataFrame([t.__dict__ for t in trades])
    return df[TRADE_COLUMNS]


def round_tick(price: float, tick_size: float = TICK_SIZE_NQ) -> float:
    return round(price / tick_size) * tick_size

