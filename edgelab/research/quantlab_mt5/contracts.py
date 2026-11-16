"""Contratos de datos, configuraciones y especificaciones de instrumentos para QuantLab MT5.

Compatibles con el esquema estandar de 16 columnas (`TRADE_COLUMNS`) utilizado en EdgeLab.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

TRADE_COLUMNS: List[str] = [
    "module",
    "side",          # +1 Long, -1 Short
    "qty",           # Lotes (ej. 0.01 .. N)
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


@dataclass(frozen=True)
class InstrumentSpec:
    """Parametros de contrato necesarios para sizing por riesgo y calculo de PnL."""

    symbol: str
    point: float
    digits: int
    contract_size: float
    min_lot: float = 0.01
    lot_step: float = 0.01
    max_lot: float = 100.0
    tick_size: float | None = None
    tick_value: float | None = None

    @property
    def usd_per_price_unit_per_lot(self) -> float:
        """Retorna cuantos USD representa un movimiento de 1.0 en precio por 1.0 lote."""
        if self.tick_size is not None and self.tick_value is not None and self.tick_size > 0:
            return self.tick_value / self.tick_size
        return self.contract_size

    def round_price(self, price: float) -> float:
        return round(float(price), self.digits)

    def normalize_lots(self, raw_lots: float, allow_min_fallback: bool = True) -> float:
        if raw_lots < self.min_lot:
            return self.min_lot if allow_min_fallback else 0.0
        steps = int(raw_lots // self.lot_step)
        lots = round(steps * self.lot_step, 4)
        if lots < self.min_lot:
            return self.min_lot if allow_min_fallback else 0.0
        return min(self.max_lot, lots)


INSTRUMENT_PRESETS: Dict[str, InstrumentSpec] = {
    "EURUSD": InstrumentSpec(symbol="EURUSD", point=1e-5, digits=5, contract_size=100_000.0),
    "GBPUSD": InstrumentSpec(symbol="GBPUSD", point=1e-5, digits=5, contract_size=100_000.0),
    "XAUUSD": InstrumentSpec(symbol="XAUUSD", point=0.01, digits=2, contract_size=100.0),
    "XAU": InstrumentSpec(symbol="XAUUSD", point=0.01, digits=2, contract_size=100.0),
    "USATECH": InstrumentSpec(symbol="USATECH", point=0.25, digits=2, contract_size=20.0, min_lot=0.01, lot_step=0.01),
    "NQ": InstrumentSpec(symbol="NQ", point=0.25, digits=2, contract_size=20.0, min_lot=0.01, lot_step=0.01),
    "USA500": InstrumentSpec(symbol="USA500", point=0.25, digits=2, contract_size=50.0, min_lot=0.01, lot_step=0.01),
    "ES": InstrumentSpec(symbol="ES", point=0.25, digits=2, contract_size=50.0, min_lot=0.01, lot_step=0.01),
}


def resolve_instrument(instrument: str | InstrumentSpec) -> InstrumentSpec:
    if isinstance(instrument, InstrumentSpec):
        return instrument
    key = str(instrument).strip().upper()
    if key in INSTRUMENT_PRESETS:
        return INSTRUMENT_PRESETS[key]
    raise KeyError(f"Instrumento desconocido {instrument!r}. Disponibles: {sorted(INSTRUMENT_PRESETS)}")


@dataclass
class SessionOpenMomentumConfig:
    """Configuracion fiel a todos los inputs operativos de SessionOpenMomentum.ex5 (v2.2)."""

    # === Strategy ===
    open_ny: str = "16:30"
    fast_ema: int = 12
    trail_ema: int = 120
    trail_start_r: float = 0.5
    atr_period: int = 14
    sl_atr_mult: float = 8.0
    trail_seconds: int = 300
    # === Risk ===
    risk_mode: int = 0          # 0=percent, 1=money, 2=fixed lot
    risk_percent: float = 1.0
    risk_money: float = 0.0
    fixed_lot: float = 0.1
    # === Adaptive Risk ===
    use_adaptive_risk: bool = True
    vol_risk_floor: float = 0.5
    vol_risk_cap: float = 2.0
    adaptive_short_window: int = 20
    adaptive_base_window: int = 180
    # === Prop Firm Safety ===
    randomizer: bool = False
    close_eod: bool = False
    eod_time: str = "22:55"
    rotar: bool = False           # EdgeLab (mejora 2026-11-16): a la hora de entrada cierra la posición abierta y toma la señal del día
    close_weekend: bool = False   # EdgeLab (2026-11-16, regla de Nico): cierra el viernes a eod_time; las noches de semana se mantienen
    max_equity_dd_pct: float = 0.0
    close_at_equity: float = 0.0
    stop_at_equity: float = 0.0
    # === Simulation ===
    initial_balance: float = 100_000.0
    spread_price: float = 0.0


@dataclass
class QlbBasketConfig:
    """Configuracion fiel a los inputs operativos de QLB_K_XAUUSD_3x_speed_q4_turn.ex5 (v1.8)."""

    risk_mode: int = 0          # 0=percent, 1=money, 2=fixed lot
    risk_percent: float = 0.75
    risk_money: float = 0.0
    fixed_lot: float = 0.01
    trade_min_lot: bool = True
    magic_base: int = 871800
    slippage: int = 30
    trail_seconds: int = 300
    no_hedge: bool = False
    close_at_equity: float = 0.0
    stop_at_equity: float = 0.0
    max_sends_per_day: int = 8
    max_daily_loss_pct: float = 4.0
    # === Prop Firm Safety ===
    randomize: bool = False
    random_strength: int = 5
    # === Verified Internal Strategy Parameters ===
    atr_period: int = 14
    sl_atr_mult: float = 2.5
    tp_atr_mult: float = 5.0    # RR = 2.00 verificada 57/57
    slot0_max_hold_bars: int = 120   # H4 (480h trading = 672h calendario)
    slot1_max_hold_bars: int = 40    # [INFERIDO] H1
    slot2_max_hold_bars: int = 40    # H1 (40h trading exactas)
    enable_slot0: bool = True
    enable_slot1: bool = True
    enable_slot2: bool = True
    # === Simulation ===
    initial_balance: float = 100_000.0
    spread_price: float = 0.0


@dataclass
class TradeRecord:
    module: str
    side: int
    qty: float
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
    """Convierte registros de operaciones al DataFrame contractual de EdgeLab."""
    if not trades:
        return pd.DataFrame(columns=TRADE_COLUMNS)
    return pd.DataFrame([t.__dict__ for t in trades])[TRADE_COLUMNS]
