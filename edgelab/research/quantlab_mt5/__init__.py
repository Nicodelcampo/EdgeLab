"""Paquete Python para analisis en EdgeLab de los EAs MT5 de QuantLab:

- ``QLB_K_XAUUSD_3x_speed_q4_turn.ex5`` (v1.8): canasta multi-slot ``H4`` + ``H1`` + ``H1`` con
  ``SL = 2.5 * iATR(14)``, ``TP = 5.0 * iATR(14)`` (RR 2.00) y salida por barras maximas.
- ``SessionOpenMomentum.ex5`` (v2.2): estrategia intradia ``M5`` sobre apertura NY (`16:30`),
  filtro `EMA(12)`, `SL = 8.0 * iATR_M5(14)`, trailing en `EMA_M5(120)` desde `+0.5 R` y Adaptive Risk.
"""
from __future__ import annotations

from .cli import correr_modulo_quantlab, correr_todos_quantlab
from .contracts import (
    INSTRUMENT_PRESETS,
    InstrumentSpec,
    QlbBasketConfig,
    SessionOpenMomentumConfig,
    TRADE_COLUMNS,
    TradeRecord,
    resolve_instrument,
    trades_to_df,
)
from .indicators import (
    check_anti_holdout,
    compute_lot_size,
    load_ohlc_data,
    mql5_atr,
    mql5_ema,
    mql5_sma,
    mql5_true_range,
    resample_ohlc,
)
from .qlb_k_xauusd_basket import (
    SLOT_NAMES,
    SLOT_TIMEFRAMES_MIN,
    correr_qlb_basket,
    correr_slot_qlb,
)
from .session_open_momentum import (
    MODULO_SOM,
    compute_adaptive_volatility_factors,
    correr_session_open_momentum,
)

MODULOS_QUANTLAB = ("SOM", "QLB_S0", "QLB_S1", "QLB_S2", "QLB_BASKET")

__all__ = [
    "INSTRUMENT_PRESETS",
    "InstrumentSpec",
    "MODULOS_QUANTLAB",
    "MODULO_SOM",
    "QlbBasketConfig",
    "SLOT_NAMES",
    "SLOT_TIMEFRAMES_MIN",
    "SessionOpenMomentumConfig",
    "TRADE_COLUMNS",
    "TradeRecord",
    "check_anti_holdout",
    "compute_adaptive_volatility_factors",
    "compute_lot_size",
    "correr_modulo_quantlab",
    "correr_qlb_basket",
    "correr_session_open_momentum",
    "correr_slot_qlb",
    "correr_todos_quantlab",
    "load_ohlc_data",
    "mql5_atr",
    "mql5_ema",
    "mql5_sma",
    "mql5_true_range",
    "resample_ohlc",
    "resolve_instrument",
    "trades_to_df",
]
