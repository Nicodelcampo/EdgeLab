"""Traduccion fiel al IL de los 4 submodulos del Lote 2 de FUNDEDSYNCSTACK5.dll:
- P: NqPullback      (ms.bip1: 1m ETH)
- C: CapstoneGap     (ms.bip5: 1m US STOCK, con fallback de salida en ms.bip1 si bip5 cierra a las 16:00 ET)
- V: VaultBreak      (ms.bip6: 5m RTH, resolucion intrabar opcional con ms.bip1)
- O: Overnight       (ms.bip1: 1m ETH + ms.bip7: 1d RTH)

Todas las reglas, desigualdades, orden de evaluacion, redondeos a tick y parametros por
defecto provienen directamente del desensamblado IL (`mod_P.txt`, `mod_C.txt`, `mod_V.txt`,
`mod_O.txt`, `core_state_ctor_bar.txt`, `sizing_license_news_risk.txt` y `defaults_dump.txt`).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from typing import Deque, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from .contracts import (
        BarSeries,
        MultiSeriesContext,
        TradeRecord,
        round_tick,
        trades_to_df,
    )
except ImportError:
    from contracts import (
        BarSeries,
        MultiSeriesContext,
        TradeRecord,
        round_tick,
        trades_to_df,
    )


# ---------------------------------------------------------------------------
# Configuraciones (defaults exactos del IL / OnStateChange)
# ---------------------------------------------------------------------------


@dataclass
class PullbackConfig:
    """Parametros de NqPullback (P) con defaults exactos de FUNDEDSYNCSTACK5.dll."""

    use_volatility_sizing: bool = True
    position_size: int = 1
    capital_usd: float = 500_000.0
    risk_percent: float = 2.0
    risk_filter_percent: float = 2.0
    slippage_ticks: int = 1
    max_contracts: int = 20
    max_margin_percent: float = 50.0
    margin_per_contract_usd: float = 0.0
    margin_rate_percent: float = 10.0
    trade_longs: bool = True
    trade_shorts: bool = False
    minimum_reward_risk: float = 0.0
    max_stop_points: float = 0.0
    retest_mode: int = 1        # 1: toque VWAP (Low<=VWAP / High>=VWAP); !=1: cierre a traves de VWAP
    stop_mode: int = 1          # 1 (!=2): swing high/low; 2: extremo del pullback
    max_trades_per_day: int = 1
    stop_swing_length: int = 30
    target_swing_length: int = 5
    buffer_mode: int = 2        # 1: ticks (* 0.25); !=1: puntos
    buffer_amount: float = 0.0
    opening_range_start: int = 83000
    opening_range_end: int = 90000
    vwap_start: int = 83000
    vwap_end: int = 170000
    entry_start: int = 90000
    entry_end: int = 170000
    day_reset_time: int = 230000
    use_end_of_day_flat: bool = False
    end_of_day_flat_time: int = 155500
    base_qty: int = 1
    enforce_daily_futures_close: bool = True
    daily_futures_flatten_time_ct: int = 154400
    daily_futures_resume_time_ct: int = 170100


@dataclass
class CapstoneConfig:
    """Parametros de CapstoneGap (C) con defaults exactos de FUNDEDSYNCSTACK5.dll."""

    stop_loss_amount: float = 1500.0
    profit_target_amount: float = 2500.0
    minimum_gap_points: float = 2.0
    enable_long_entries: bool = True
    enable_short_entries: bool = False
    max_entries_per_day: int = 2
    prior_bars_lookback: int = 12
    entry_start_offset_minutes: int = 150
    entry_end_offset_minutes: int = 390
    exit_offset_minutes: int = 404
    base_qty: int = 1
    enforce_daily_futures_close: bool = True
    daily_futures_flatten_time_ct: int = 154400
    daily_futures_resume_time_ct: int = 170100


@dataclass
class VaultConfig:
    """Parametros de VaultBreak (V) con defaults exactos de FUNDEDSYNCSTACK5.dll."""

    noise_multiplier: float = 0.4
    daily_atr_length: int = 252
    earliest_entry_eastern: int = 94500
    latest_entry_eastern: int = 150000
    flatten_time_eastern: int = 155000
    maximum_trades_per_day: int = 3
    vwap_exit_bars: int = 2
    profit_target_usd_per_contract: float = 1400.0
    stop_loss_usd_per_contract: float = 2000.0
    block_entry_hour_enabled: bool = True
    blocked_entry_hour: int = 9
    base_qty: int = 3


@dataclass
class OvernightConfig:
    """Parametros de Overnight (O) con defaults exactos de FUNDEDSYNCSTACK5.dll."""

    moving_average_length: int = 20
    use_trend_filter: bool = True
    entry_time_central: int = 150000
    exit_time_central: int = 83000
    use_post_maintenance_entry: bool = True
    post_maintenance_entry_time_central: int = 170100
    volatility_lookback: int = 20
    target_risk_usd: float = 1500.0
    minimum_contracts: int = 1
    maximum_contracts: int = 50
    capital_usd: float = 100_000.0
    maximum_margin_percent: float = 50.0
    margin_per_contract_usd: float = 0.0
    margin_rate_percent: float = 10.0
    use_down_rth_day_filter: bool = False
    use_rising_ma_slope_filter: bool = True
    ma_slope_lookback: int = 5
    use_rth_range_filter: bool = True
    range_atr_length: int = 20
    maximum_rth_range_to_atr: float = 1.5
    allow_friday_entries: bool = False
    base_qty: int = 2
    enforce_daily_futures_close: bool = True
    daily_futures_flatten_time_ct: int = 154400
    daily_futures_resume_time_ct: int = 170100


# ---------------------------------------------------------------------------
# Helpers compartidos del motor de simulacion
# ---------------------------------------------------------------------------

_NQ_SIGNAL_POINT_VALUE: float = 20.0
_NQ_SIGNAL_TICK_SIZE: float = 0.25
_NQ_SIGNAL_TICK_VALUE: float = 5.0


@dataclass
class _OpenPosition:
    module: str
    side: int
    qty: int
    entry_time_utc: int
    entry_price: float
    stop_price: float
    target_price: float
    entry_name: str
    seq: int
    max_high: float
    min_low: float
    bars: int = 1


@dataclass
class _PendingMarketExit:
    reason: str


def _is_daily_futures_close_blocked(
    hhmmss_ct: int,
    dow_ct: int,
    flatten_time_ct: int = 154400,
    resume_time_ct: int = 170100,
) -> bool:
    """Equivalente exacto a `FUNDEDSYNCSTACK.IsDailyFuturesCloseBlocked` (dow_ct: 0=Lun..6=Dom)."""
    if dow_ct == 5:  # Sabado
        return True
    if dow_ct == 4:  # Viernes
        return hhmmss_ct >= flatten_time_ct
    if dow_ct == 6:  # Domingo
        return hhmmss_ct < resume_time_ct
    return flatten_time_ct <= hhmmss_ct < resume_time_ct


def _hhmmss_to_seconds(hhmmss: int) -> int:
    hh = hhmmss // 10000
    mm = (hhmmss // 100) % 100
    ss = hhmmss % 100
    return hh * 3600 + mm * 60 + ss


def _make_trade_record(
    pos: _OpenPosition,
    exit_time_utc: int,
    exit_price: float,
    exit_name: str,
    point_value: float,
) -> TradeRecord:
    """Construye `TradeRecord` con metricas de PnL/MAE/MFE consistentes con NT8."""
    pnl_pts = (exit_price - pos.entry_price) * pos.side
    pnl_usd = pnl_pts * pos.qty * point_value
    if pos.side > 0:
        max_high = max(pos.max_high, exit_price)
        min_low = min(pos.min_low, exit_price)
        mae_pts = max(0.0, pos.entry_price - min_low)
        mfe_pts = max(0.0, max_high - pos.entry_price)
    else:
        max_high = max(pos.max_high, exit_price)
        min_low = min(pos.min_low, exit_price)
        mae_pts = max(0.0, max_high - pos.entry_price)
        mfe_pts = max(0.0, pos.entry_price - min_low)
    return TradeRecord(
        module=pos.module,
        side=pos.side,
        qty=pos.qty,
        entry_time_utc=int(pos.entry_time_utc),
        exit_time_utc=int(exit_time_utc),
        entry_price=float(pos.entry_price),
        exit_price=float(exit_price),
        stop_price=float(pos.stop_price),
        target_price=float(pos.target_price),
        entry_name=pos.entry_name,
        exit_name=exit_name,
        pnl_pts=float(pnl_pts),
        pnl_usd=float(pnl_usd),
        mae_usd=float(mae_pts * pos.qty * point_value),
        mfe_usd=float(mfe_pts * pos.qty * point_value),
        bars=int(pos.bars),
    )


def _check_protective_exit_on_bar(
    pos: _OpenPosition,
    bar_open: float,
    bar_high: float,
    bar_low: float,
    bar_ts_ns: int,
    point_value: float,
    update_bars: bool = True,
) -> Optional[TradeRecord]:
    """Evalua ordenes protectoras STOP y TARGET sobre una barra OHLC (conservador: STOP primero)."""
    if update_bars:
        pos.bars += 1
    pos.max_high = max(pos.max_high, bar_high)
    pos.min_low = min(pos.min_low, bar_low)

    has_stop = not math.isnan(pos.stop_price)
    has_target = not math.isnan(pos.target_price)

    if pos.side > 0:
        if has_stop and bar_low <= pos.stop_price:
            exit_px = min(bar_open, pos.stop_price)
            return _make_trade_record(
                pos, bar_ts_ns, exit_px, f"{pos.module}_STOP_{pos.seq}", point_value
            )
        if has_target and bar_high >= pos.target_price:
            exit_px = max(bar_open, pos.target_price)
            return _make_trade_record(
                pos, bar_ts_ns, exit_px, f"{pos.module}_TARGET_{pos.seq}", point_value
            )
    else:
        if has_stop and bar_high >= pos.stop_price:
            exit_px = max(bar_open, pos.stop_price)
            return _make_trade_record(
                pos, bar_ts_ns, exit_px, f"{pos.module}_STOP_{pos.seq}", point_value
            )
        if has_target and bar_low <= pos.target_price:
            exit_px = min(bar_open, pos.target_price)
            return _make_trade_record(
                pos, bar_ts_ns, exit_px, f"{pos.module}_TARGET_{pos.seq}", point_value
            )
    return None


def _compute_strict_pivots(
    highs: np.ndarray, lows: np.ndarray, strength: int
) -> Tuple[np.ndarray, np.ndarray]:
    """Replica exacta de `PullbackPivotHigh` y `PullbackPivotLow` (comparacion estricta).

    En barra `i >= 2 * strength`, el pivote candidato esta en `i - strength`, y debe
    ser estrictamente mayor (o estrictamente menor) que las `strength` barras anteriores
    y las `strength` barras posteriores.
    """
    n = len(highs)
    piv_hi = np.zeros(n, dtype=bool)
    piv_lo = np.zeros(n, dtype=bool)
    if strength <= 0:
        piv_hi[:] = True
        piv_lo[:] = True
        return piv_hi, piv_lo
    win = 2 * strength + 1
    if n < win:
        return piv_hi, piv_lo

    w_hi = np.lib.stride_tricks.sliding_window_view(highs, win)
    c_hi = w_hi[:, strength : strength + 1]
    mask = np.arange(win) == strength
    piv_hi[win - 1 :] = np.all((w_hi < c_hi) | mask, axis=1)

    w_lo = np.lib.stride_tricks.sliding_window_view(lows, win)
    c_lo = w_lo[:, strength : strength + 1]
    piv_lo[win - 1 :] = np.all((w_lo > c_lo) | mask, axis=1)
    return piv_hi, piv_lo


# ---------------------------------------------------------------------------
# Modulo P: NqPullback (ms.bip1)
# ---------------------------------------------------------------------------


def _pullback_long_valid(
    cfg: PullbackConfig,
    stop: float,
    target: float,
    close: float,
    has_stop_swing_low: bool,
    has_target_swing_high: bool,
    pullback_low: float,
) -> bool:
    """Traduccion exacta de `FUNDEDSYNCSTACK.PullbackLongValid`."""
    stop_dist = close - stop
    if cfg.stop_mode != 2 and not has_stop_swing_low:
        return False
    if not has_target_swing_high:
        return False
    if cfg.stop_mode != 1 and pullback_low == 0.0:
        return False
    if stop >= close:
        return False
    if target <= close:
        return False
    if cfg.max_stop_points != 0.0 and stop_dist > cfg.max_stop_points:
        return False
    if cfg.minimum_reward_risk != 0.0 and ((target - close) / stop_dist) < cfg.minimum_reward_risk:
        return False
    return True


def _pullback_short_valid(
    cfg: PullbackConfig,
    stop: float,
    target: float,
    close: float,
    has_stop_swing_high: bool,
    has_target_swing_low: bool,
    pullback_high: float,
) -> bool:
    """Traduccion exacta de `FUNDEDSYNCSTACK.PullbackShortValid`."""
    stop_dist = stop - close
    if cfg.stop_mode != 2 and not has_stop_swing_high:
        return False
    if not has_target_swing_low:
        return False
    if cfg.stop_mode != 1 and pullback_high == 0.0:
        return False
    if stop <= close:
        return False
    if target >= close:
        return False
    if cfg.max_stop_points != 0.0 and stop_dist > cfg.max_stop_points:
        return False
    if cfg.minimum_reward_risk != 0.0 and ((close - target) / stop_dist) < cfg.minimum_reward_risk:
        return False
    return True


def _get_pullback_native_quantity(
    cfg: PullbackConfig, stop_distance: float, close: float
) -> int:
    """Traduccion exacta de `FUNDEDSYNCSTACK.GetPullbackNativeQuantity`."""
    if not cfg.use_volatility_sizing:
        return int(cfg.position_size)
    if stop_distance <= 0.0:
        return 0
    stop_ticks = max(
        1.0,
        math.ceil(stop_distance / _NQ_SIGNAL_TICK_SIZE) + 2 * max(0, cfg.slippage_ticks),
    )
    risk_per_contract_usd = stop_ticks * _NQ_SIGNAL_TICK_VALUE
    risk_filter_usd = cfg.capital_usd * cfg.risk_filter_percent / 100.0
    if risk_per_contract_usd <= 0.0 or math.floor(risk_filter_usd / risk_per_contract_usd) < 1.0:
        return 0

    contracts = int(math.floor((cfg.capital_usd * cfg.risk_percent / 100.0) / risk_per_contract_usd))
    margin_per_contract = (
        cfg.margin_per_contract_usd
        if cfg.margin_per_contract_usd > 0.0
        else (close * _NQ_SIGNAL_POINT_VALUE * cfg.margin_rate_percent / 100.0)
    )
    if margin_per_contract > 0.0:
        max_margin_contracts = int(
            math.floor((cfg.capital_usd * cfg.max_margin_percent / 100.0) / margin_per_contract)
        )
        contracts = min(contracts, max_margin_contracts)
    return min(max(0, contracts), cfg.max_contracts)


def run_p(
    ms: MultiSeriesContext,
    qty: Optional[int] = None,
    cfg: Optional[PullbackConfig] = None,
) -> pd.DataFrame:
    """Ejecuta `NqPullback` (`P`) sobre `ms.bip1` (1m ETH).

    Si `qty is None`, usa el sizing dinamico nativo del IL (`GetPullbackNativeQuantity * base_qty`).
    Si `qty` es un entero explicito, sobrescribe el numero de contratos tras validar el setup.
    """
    cfg = cfg or PullbackConfig()
    s: BarSeries = ms.bip1
    n = len(s.close)
    min_bars = max(2 * cfg.stop_swing_length + 1, 2 * cfg.target_swing_length + 1)
    if n <= min_bars:
        return trades_to_df([])

    stop_piv_hi, stop_piv_lo = _compute_strict_pivots(s.high, s.low, cfg.stop_swing_length)
    if cfg.target_swing_length == cfg.stop_swing_length:
        tgt_piv_hi, tgt_piv_lo = stop_piv_hi, stop_piv_lo
    else:
        tgt_piv_hi, tgt_piv_lo = _compute_strict_pivots(s.high, s.low, cfg.target_swing_length)

    trades: List[TradeRecord] = []
    pos: Optional[_OpenPosition] = None
    pending_entry: Optional[Tuple[int, int, float, float]] = None  # (side, qty, stop_px, target_px)
    pending_exit: Optional[_PendingMarketExit] = None
    seq = 0

    # Estado interno del modulo P
    trades_today = 0
    orb_ready = False
    orb_high = 0.0
    orb_low = 0.0

    cum_pv = 0.0
    cum_vol = 0.0
    session_vwap = 0.0

    last_stop_swing_high = 0.0
    last_stop_swing_low = 0.0
    has_stop_swing_high = False
    has_stop_swing_low = False

    last_target_swing_high = 0.0
    last_target_swing_low = 0.0
    has_target_swing_high = False
    has_target_swing_low = False

    long_orb_broken = False
    short_orb_broken = False
    long_vwap_touched = False
    short_vwap_touched = False
    long_closed_through = False
    short_closed_through = False
    pullback_low = 0.0
    pullback_high = 0.0
    was_long_latched = False
    was_short_latched = False

    def reset_latches() -> None:
        nonlocal long_orb_broken, short_orb_broken
        nonlocal long_vwap_touched, short_vwap_touched
        nonlocal long_closed_through, short_closed_through
        nonlocal pullback_low, pullback_high
        nonlocal was_long_latched, was_short_latched
        long_orb_broken = False
        short_orb_broken = False
        long_vwap_touched = False
        short_vwap_touched = False
        long_closed_through = False
        short_closed_through = False
        pullback_low = 0.0
        pullback_high = 0.0
        was_long_latched = False
        was_short_latched = False

    opens = s.open
    highs = s.high
    lows = s.low
    closes = s.close
    volumes = s.volume
    ts_ns = s.ts_ns
    hhmmss_ct = s.hhmmss_ct
    dow_ct = s.dow_ct
    tick = ms.tick_size
    pv = ms.point_value

    for i in range(min_bars, n):
        o_i = float(opens[i])
        h_i = float(highs[i])
        l_i = float(lows[i])
        c_i = float(closes[i])
        t_ns = int(ts_ns[i])

        # 1) Procesar ordenes pendientes al open de la barra i
        if pending_exit is not None and pos is not None:
            seq += 1
            trades.append(
                _make_trade_record(pos, t_ns, o_i, f"P_X_{pending_exit.reason}_{seq}", pv)
            )
            pos = None
            pending_exit = None
        elif pending_entry is not None and pos is None:
            e_side, e_qty, e_sl, e_tp = pending_entry
            pending_entry = None
            seq += 1
            e_name = f"P_E_L_{seq}" if e_side > 0 else f"P_E_S_{seq}"
            pos = _OpenPosition(
                module="P",
                side=e_side,
                qty=e_qty,
                entry_time_utc=t_ns,
                entry_price=o_i,
                stop_price=round_tick(e_sl, tick),
                target_price=round_tick(e_tp, tick),
                entry_name=e_name,
                seq=seq,
                max_high=o_i,
                min_low=o_i,
                bars=1,
            )
            closed = _check_protective_exit_on_bar(
                pos, o_i, h_i, l_i, t_ns, pv, update_bars=False
            )
            if closed is not None:
                trades.append(closed)
                pos = None
        elif pos is not None:
            closed = _check_protective_exit_on_bar(
                pos, o_i, h_i, l_i, t_ns, pv, update_bars=True
            )
            if closed is not None:
                trades.append(closed)
                pos = None

        # 2) EnforceDailyFuturesClose (en OnBarUpdate antes de RunPullback en bip1)
        maint_blocked = False
        if cfg.enforce_daily_futures_close:
            maint_blocked = _is_daily_futures_close_blocked(
                int(hhmmss_ct[i]),
                int(dow_ct[i]),
                cfg.daily_futures_flatten_time_ct,
                cfg.daily_futures_resume_time_ct,
            )
            if maint_blocked:
                pending_entry = None
                if pos is not None and pending_exit is None:
                    pending_exit = _PendingMarketExit("DAILY_FUTURES_CLOSE")

        # 3) RunPullback() exacto
        t0 = int(hhmmss_ct[i])
        t1 = int(hhmmss_ct[i - 1])

        in_orb = cfg.opening_range_start < t0 <= cfg.opening_range_end
        prior_in_orb = cfg.opening_range_start < t1 <= cfg.opening_range_end
        in_vwap = cfg.vwap_start < t0 <= cfg.vwap_end
        prior_in_vwap = cfg.vwap_start < t1 <= cfg.vwap_end
        in_entry = cfg.entry_start < t0 <= cfg.entry_end

        if t0 > cfg.day_reset_time and t1 <= cfg.day_reset_time:
            trades_today = 0
            orb_ready = False
            reset_latches()

        # UpdatePullbackOrb
        if in_orb and not prior_in_orb:
            orb_high = h_i
            orb_low = l_i
            orb_ready = False
        if in_orb:
            if h_i > orb_high:
                orb_high = h_i
            if l_i < orb_low:
                orb_low = l_i
        if (not in_orb) and prior_in_orb:
            orb_ready = True

        # UpdatePullbackVwap
        tp = (h_i + l_i + c_i) / 3.0
        vol = max(1.0, float(volumes[i]))
        if in_vwap and not prior_in_vwap:
            cum_pv = tp * vol
            cum_vol = vol
        elif in_vwap:
            cum_pv += tp * vol
            cum_vol += vol
        if in_vwap and cum_vol > 0.0:
            session_vwap = cum_pv / cum_vol

        # UpdatePullbackPivots
        if stop_piv_hi[i]:
            last_stop_swing_high = float(highs[i - cfg.stop_swing_length])
            has_stop_swing_high = True
        if stop_piv_lo[i]:
            last_stop_swing_low = float(lows[i - cfg.stop_swing_length])
            has_stop_swing_low = True
        if tgt_piv_hi[i]:
            last_target_swing_high = float(highs[i - cfg.target_swing_length])
            has_target_swing_high = True
        if tgt_piv_lo[i]:
            last_target_swing_low = float(lows[i - cfg.target_swing_length])
            has_target_swing_low = True

        # Rupturas ORB y latches VWAP
        post_orb = orb_ready and (not in_orb)
        if post_orb:
            if c_i > orb_high:
                long_orb_broken = True
            if c_i < orb_low:
                short_orb_broken = True

        vwap_ready = in_vwap and (cum_vol > 0.0)
        gate = post_orb and in_vwap and in_entry and vwap_ready

        long_signal = False
        short_signal = False

        if gate and long_orb_broken:
            if cfg.retest_mode == 1:
                if l_i <= session_vwap:
                    long_vwap_touched = True
                long_signal = long_vwap_touched and (c_i > session_vwap)
            else:
                if c_i < session_vwap:
                    long_closed_through = True
                long_signal = long_closed_through and (c_i > session_vwap)

        if gate and short_orb_broken:
            if cfg.retest_mode == 1:
                if h_i >= session_vwap:
                    short_vwap_touched = True
                short_signal = short_vwap_touched and (c_i < session_vwap)
            else:
                if c_i > session_vwap:
                    short_closed_through = True
                short_signal = short_closed_through and (c_i < session_vwap)

        # UpdatePullbackExtremes
        long_latched = long_vwap_touched or long_closed_through
        short_latched = short_vwap_touched or short_closed_through
        if long_latched and not was_long_latched:
            pullback_low = l_i
        elif long_latched and l_i < pullback_low:
            pullback_low = l_i

        if short_latched and not was_short_latched:
            pullback_high = h_i
        elif short_latched and h_i > pullback_high:
            pullback_high = h_i

        was_long_latched = long_latched
        was_short_latched = short_latched

        # TryEnterPullback
        can_enter = (
            (pos is None)
            and (pending_entry is None)
            and (pending_exit is None)
            and (not maint_blocked)
        )
        if can_enter and trades_today < cfg.max_trades_per_day:
            buf = (
                cfg.buffer_amount * _NQ_SIGNAL_TICK_SIZE
                if cfg.buffer_mode == 1
                else cfg.buffer_amount
            )
            long_stop = (pullback_low - buf) if cfg.stop_mode == 2 else (last_stop_swing_low - buf)
            short_stop = (
                (pullback_high + buf) if cfg.stop_mode == 2 else (last_stop_swing_high + buf)
            )
            long_target = last_target_swing_high
            short_target = last_target_swing_low

            entered = False
            if (
                long_signal
                and cfg.trade_longs
                and _pullback_long_valid(
                    cfg,
                    long_stop,
                    long_target,
                    c_i,
                    has_stop_swing_low,
                    has_target_swing_high,
                    pullback_low,
                )
            ):
                if qty is not None:
                    exec_qty = int(qty)
                else:
                    native_qty = _get_pullback_native_quantity(cfg, c_i - long_stop, c_i)
                    exec_qty = max(0, native_qty * cfg.base_qty)
                if exec_qty >= 1:
                    pending_entry = (+1, exec_qty, long_stop, long_target)
                    trades_today += 1
                    reset_latches()
                    entered = True

            if (
                not entered
                and short_signal
                and cfg.trade_shorts
                and _pullback_short_valid(
                    cfg,
                    short_stop,
                    short_target,
                    c_i,
                    has_stop_swing_high,
                    has_target_swing_low,
                    pullback_high,
                )
            ):
                if qty is not None:
                    exec_qty = int(qty)
                else:
                    native_qty = _get_pullback_native_quantity(cfg, short_stop - c_i, c_i)
                    exec_qty = max(0, native_qty * cfg.base_qty)
                if exec_qty >= 1:
                    pending_entry = (-1, exec_qty, short_stop, short_target)
                    trades_today += 1
                    reset_latches()

        # Salida EOD configurable en RunPullback
        if (
            cfg.use_end_of_day_flat
            and cfg.end_of_day_flat_time <= t0 < cfg.day_reset_time
            and pos is not None
            and pending_exit is None
        ):
            pending_exit = _PendingMarketExit("EOD")

    return trades_to_df(trades)


# ---------------------------------------------------------------------------
# Modulo C: CapstoneGap (ms.bip5, con puente de salida a ms.bip1 si bip5 cierra 16:00 ET)
# ---------------------------------------------------------------------------


@dataclass
class _WorkingCapstoneOrder:
    side: int             # +1 Long, -1 Short
    order_type: str       # "STOP" (4), "LIMIT" (0), "MARKET" (1)
    limit_price: float
    stop_price: float
    qty: int
    stop_dist: float
    target_dist: float


def _check_capstone_working_fill(
    order: _WorkingCapstoneOrder,
    bar_open: float,
    bar_high: float,
    bar_low: float,
) -> Optional[float]:
    """Determina si una orden pendiente (Market/StopMarket/Limit) se ejecuta en la barra."""
    if order.order_type == "MARKET":
        return bar_open
    if order.side > 0:
        if order.order_type == "STOP":
            if bar_open >= order.stop_price:
                return bar_open
            if bar_high >= order.stop_price:
                return order.stop_price
        elif order.order_type == "LIMIT":
            if bar_open <= order.limit_price:
                return bar_open
            if bar_low <= order.limit_price:
                return order.limit_price
    else:
        if order.order_type == "STOP":
            if bar_open <= order.stop_price:
                return bar_open
            if bar_low <= order.stop_price:
                return order.stop_price
        elif order.order_type == "LIMIT":
            if bar_open >= order.limit_price:
                return bar_open
            if bar_high >= order.limit_price:
                return order.limit_price
    return None


def _run_capstone_m1_bridge(
    pos: _OpenPosition,
    pending_exit: Optional[_PendingMarketExit],
    bip1: BarSeries,
    m1_cursor: int,
    start_ts_ns: int,
    end_ts_ns: int,
    session_date_et: int,
    exit_sec_et: int,
    cfg: CapstoneConfig,
    point_value: float,
    seq: int,
) -> Tuple[Optional[_OpenPosition], Optional[_PendingMarketExit], Optional[TradeRecord], int, int]:
    """Si `bip5` termina a las 16:00 ET antes de `exitTime_C` (~16:14/16:15 ET), monitorea
    el trade abierto sobre `ms.bip1` hasta SL/TP, `exitTime_C` o `DAILY_FUTURES_CLOSE`.
    """
    n1 = len(bip1.close)
    while m1_cursor < n1 and bip1.ts_ns[m1_cursor] <= start_ts_ns:
        m1_cursor += 1

    while m1_cursor < n1 and bip1.ts_ns[m1_cursor] < end_ts_ns:
        o_m = float(bip1.open[m1_cursor])
        h_m = float(bip1.high[m1_cursor])
        l_m = float(bip1.low[m1_cursor])
        t_m = int(bip1.ts_ns[m1_cursor])

        if pending_exit is not None:
            seq += 1
            tr = _make_trade_record(pos, t_m, o_m, f"C_X_{pending_exit.reason}_{seq}", point_value)
            return None, None, tr, m1_cursor + 1, seq

        closed = _check_protective_exit_on_bar(pos, o_m, h_m, l_m, t_m, point_value, update_bars=True)
        if closed is not None:
            return None, None, closed, m1_cursor + 1, seq

        if cfg.enforce_daily_futures_close and _is_daily_futures_close_blocked(
            int(bip1.hhmmss_ct[m1_cursor]),
            int(bip1.dow_ct[m1_cursor]),
            cfg.daily_futures_flatten_time_ct,
            cfg.daily_futures_resume_time_ct,
        ):
            pending_exit = _PendingMarketExit("DAILY_FUTURES_CLOSE")
        elif int(bip1.cal_date_et[m1_cursor]) == session_date_et:
            if _hhmmss_to_seconds(int(bip1.hhmmss_et[m1_cursor])) >= exit_sec_et:
                pending_exit = _PendingMarketExit("TIME")
        elif int(bip1.cal_date_et[m1_cursor]) > session_date_et:
            pending_exit = _PendingMarketExit("TIME")

        m1_cursor += 1

    return pos, pending_exit, None, m1_cursor, seq


def run_c(
    ms: MultiSeriesContext,
    qty: int = 1,
    cfg: Optional[CapstoneConfig] = None,
) -> pd.DataFrame:
    """Ejecuta `CapstoneGap` (`C`) sobre `ms.bip5` (1m US STOCK).

    Logica exacta verificada en IL (`mod_C.txt`):
    - Es una estrategia de **continuacion de gap** dentro del rango previo (NO gap fade):
      * Long: requiere gap alcista (`today_open > prev_close + min_gap`) contenido bajo el
        maximo previo (`today_open < prev_high`). Nivel trigger = `today_open + 0.5 * |gap|`:
        - Si `close < trigger`: orden `StopMarket` alcista en `trigger`.
        - Si `close > trigger`: orden `Limit` alcista en `LowestPriorBars_C(12)` (`min(low[i-12:i])`).
      * Short (`enable_short_entries=False` por defecto): requiere gap bajista
        (`today_open < prev_close - min_gap`) contenido sobre el minimo previo (`today_open > prev_low`).
        Nivel trigger = `today_open - 0.5 * |gap|`:
        - Si `close > trigger`: orden `StopMarket` bajista en `trigger`.
        - Si `close < trigger`: orden `Limit` bajista en `HighestPriorBars_C(12)` (`max(high[i-12:i])`).
    """
    cfg = cfg or CapstoneConfig()
    s: BarSeries = ms.bip5
    n = len(s.close)
    lookback = max(1, cfg.prior_bars_lookback)
    if n < 2 or qty <= 0:
        return trades_to_df([])

    bip1 = ms.bip1
    has_m1 = bip1 is not None and len(bip1.close) > 0
    m1_cursor = 0

    trades: List[TradeRecord] = []
    pos: Optional[_OpenPosition] = None
    working: Optional[_WorkingCapstoneOrder] = None
    pending_exit: Optional[_PendingMarketExit] = None
    seq = 0

    daily_opens: List[float] = []
    daily_highs: List[float] = []
    daily_lows: List[float] = []
    daily_closes: List[float] = []
    entries_today = 0

    entry_start_sec = 12 * 3600
    entry_end_sec = 16 * 3600
    exit_sec = 16 * 3600 + 14 * 60
    active_session_date_et = -1

    stop_dist = cfg.stop_loss_amount / _NQ_SIGNAL_POINT_VALUE
    target_dist = cfg.profit_target_amount / _NQ_SIGNAL_POINT_VALUE

    opens = s.open
    highs = s.high
    lows = s.low
    closes = s.close
    ts_ns = s.ts_ns
    hhmmss_ct = s.hhmmss_ct
    hhmmss_et = s.hhmmss_et
    cal_date_et = s.cal_date_et
    hhmmss_ct = s.hhmmss_ct
    dow_ct = s.dow_ct
    is_new_sess = s.is_new_session
    tick = ms.tick_size
    pv = ms.point_value

    for i in range(n):
        o_i = float(opens[i])
        h_i = float(highs[i])
        l_i = float(lows[i])
        c_i = float(closes[i])
        t_ns = int(ts_ns[i])

        # Si inicia nueva sesion en bip5 y quedo una posicion abierta porque bip5 cerro a las 16:00 ET,
        # resolverla causalmente con bip1 hasta `exitTime_C` (~16:14/16:15 ET).
        if is_new_sess[i] and pos is not None and has_m1 and active_session_date_et > 0:
            prev_end_ts = int(ts_ns[i - 1])
            pos, pending_exit, closed_bridge, m1_cursor, seq = _run_capstone_m1_bridge(
                pos,
                pending_exit,
                bip1,
                m1_cursor,
                prev_end_ts,
                t_ns,
                active_session_date_et,
                exit_sec,
                cfg,
                pv,
                seq,
            )
            if closed_bridge is not None:
                trades.append(closed_bridge)

        # 1) Ejecutar ordenes pendientes / working al llegar barra i
        if pending_exit is not None and pos is not None:
            seq += 1
            trades.append(
                _make_trade_record(pos, t_ns, o_i, f"C_X_{pending_exit.reason}_{seq}", pv)
            )
            pos = None
            pending_exit = None
        elif working is not None and pos is None:
            if is_new_sess[i]:
                working = None
            else:
                fill_px = _check_capstone_working_fill(working, o_i, h_i, l_i)
                if fill_px is not None:
                    seq += 1
                    entries_today += 1
                    e_side = working.side
                    if e_side > 0:
                        sl_px = round_tick(fill_px - working.stop_dist, tick)
                        tp_px = round_tick(fill_px + working.target_dist, tick)
                        e_name = f"C_E_L_{seq}"
                    else:
                        sl_px = round_tick(fill_px + working.stop_dist, tick)
                        tp_px = round_tick(fill_px - working.target_dist, tick)
                        e_name = f"C_E_S_{seq}"
                    pos = _OpenPosition(
                        module="C",
                        side=e_side,
                        qty=working.qty,
                        entry_time_utc=t_ns,
                        entry_price=fill_px,
                        stop_price=sl_px,
                        target_price=tp_px,
                        entry_name=e_name,
                        seq=seq,
                        max_high=fill_px,
                        min_low=fill_px,
                        bars=1,
                    )
                    working = None
                    closed = _check_protective_exit_on_bar(
                        pos, o_i, h_i, l_i, t_ns, pv, update_bars=False
                    )
                    if closed is not None:
                        trades.append(closed)
                        pos = None
        elif pos is not None:
            closed = _check_protective_exit_on_bar(
                pos, o_i, h_i, l_i, t_ns, pv, update_bars=True
            )
            if closed is not None:
                trades.append(closed)
                pos = None

        # Chequeo de ventana de mantenimiento diario CME
        maint_blocked = False
        if cfg.enforce_daily_futures_close:
            maint_blocked = _is_daily_futures_close_blocked(
                int(hhmmss_ct[i]),
                int(dow_ct[i]),
                cfg.daily_futures_flatten_time_ct,
                cfg.daily_futures_resume_time_ct,
            )
            if maint_blocked:
                working = None
                if pos is not None and pending_exit is None:
                    pending_exit = _PendingMarketExit("DAILY_FUTURES_CLOSE")

        # 2) RunCapstone() exacto
        cur_sec_et = _hhmmss_to_seconds(int(hhmmss_et[i]))
        if is_new_sess[i]:
            active_session_date_et = int(cal_date_et[i])
            entry_start_sec = cur_sec_et + cfg.entry_start_offset_minutes * 60
            entry_end_sec = cur_sec_et + cfg.entry_end_offset_minutes * 60
            exit_sec = cur_sec_et + cfg.exit_offset_minutes * 60
            entries_today = 0
            daily_opens.insert(0, o_i)
            daily_highs.insert(0, h_i)
            daily_lows.insert(0, l_i)
            daily_closes.insert(0, c_i)

        if not daily_closes:
            continue

        if h_i > daily_highs[0]:
            daily_highs[0] = h_i
        if l_i < daily_lows[0]:
            daily_lows[0] = l_i
        daily_closes[0] = c_i

        if len(daily_closes) < 2:
            continue

        # Salida por tiempo (`cur_sec_et == exitTime_C`, o `>=` si falto el minuto exacto)
        if pos is not None:
            if cur_sec_et >= exit_sec and pending_exit is None:
                pending_exit = _PendingMarketExit("TIME")
            continue

        # Gate de entrada
        if (
            i < lookback
            or cur_sec_et < entry_start_sec
            or cur_sec_et >= entry_end_sec
            or entries_today >= cfg.max_entries_per_day
            or maint_blocked
        ):
            working = None
            continue

        today_open = daily_opens[0]
        prev_close = daily_closes[1]
        half_gap = 0.5 * abs(today_open - prev_close)

        desired: Optional[_WorkingCapstoneOrder] = None
        use_qty = int(qty)

        if (
            cfg.enable_long_entries
            and today_open > (prev_close + cfg.minimum_gap_points)
            and today_open < daily_highs[1]
        ):
            trigger = today_open + half_gap
            if c_i < trigger:
                stop_px = round_tick(trigger, tick)
                # SubmitModuleEntryOrder convierte StopMarket ya marketable a Market
                if stop_px <= c_i:
                    desired = _WorkingCapstoneOrder(
                        +1, "MARKET", 0.0, 0.0, use_qty, stop_dist, target_dist
                    )
                else:
                    desired = _WorkingCapstoneOrder(
                        +1, "STOP", 0.0, stop_px, use_qty, stop_dist, target_dist
                    )
            elif c_i > trigger:
                lim_px = round_tick(float(np.min(lows[i - lookback : i])), tick)
                desired = _WorkingCapstoneOrder(
                    +1, "LIMIT", lim_px, 0.0, use_qty, stop_dist, target_dist
                )
        elif (
            cfg.enable_short_entries
            and today_open < (prev_close - cfg.minimum_gap_points)
            and today_open > daily_lows[1]
        ):
            trigger = today_open - half_gap
            if c_i > trigger:
                stop_px = round_tick(trigger, tick)
                if stop_px >= c_i:
                    desired = _WorkingCapstoneOrder(
                        -1, "MARKET", 0.0, 0.0, use_qty, stop_dist, target_dist
                    )
                else:
                    desired = _WorkingCapstoneOrder(
                        -1, "STOP", 0.0, stop_px, use_qty, stop_dist, target_dist
                    )
            elif c_i < trigger:
                lim_px = round_tick(float(np.max(highs[i - lookback : i])), tick)
                desired = _WorkingCapstoneOrder(
                    -1, "LIMIT", lim_px, 0.0, use_qty, stop_dist, target_dist
                )

        if desired is None:
            working = None
            continue

        # MaintainModuleEntryWithDistances: si cambia direccion u OrderType, cancela en esta barra y retorna
        if working is not None and (
            working.side != desired.side or working.order_type != desired.order_type
        ):
            working = None
            continue

        working = desired

    # Si al final de toda la serie bip5 quedo una posicion abierta en la ultima sesion,
    # intentar resolver salida por tiempo usando ms.bip1 si dispone de barras hasta exit_sec.
    if pos is not None and has_m1 and active_session_date_et > 0:
        last_ts = int(ts_ns[-1])
        pos, pending_exit, closed_bridge, m1_cursor, seq = _run_capstone_m1_bridge(
            pos,
            pending_exit,
            bip1,
            m1_cursor,
            last_ts,
            int(bip1.ts_ns[-1]) + 1,
            active_session_date_et,
            exit_sec,
            cfg,
            pv,
            seq,
        )
        if closed_bridge is not None:
            trades.append(closed_bridge)

    return trades_to_df(trades)


# ---------------------------------------------------------------------------
# Modulo V: VaultBreak (ms.bip6)
# ---------------------------------------------------------------------------


def _m1_mapping_valid(bip6: BarSeries, bip1: Optional[BarSeries]) -> bool:
    if bip1 is None or len(bip1.close) == 0 or len(bip6.m1_end_idx) != len(bip6.close):
        return False
    m1_end = bip6.m1_end_idx
    if len(bip6.close) > 1 and np.all(m1_end == 0):
        return False
    if np.any(m1_end < 0) or np.any(m1_end >= len(bip1.close)):
        return False
    return True


def _m1_slice_for_bip6_bar(
    bip6: BarSeries, bip1: BarSeries, i: int
) -> Tuple[int, int]:
    """Devuelve rango `[m1_start, m1_stop)` en `bip1` correspondiente a la barra `i` de `bip6` (5m RTH)."""
    m1_end = bip6.m1_end_idx
    m1_stop = int(m1_end[i]) + 1
    m1_start = (int(m1_end[i - 1]) + 1) if i > 0 else 0
    if bip6.is_new_session[i]:
        # Al iniciar nueva sesion RTH, no barrer barras ETH previas de la noche anterior.
        min_ts = int(bip6.ts_ns[i]) - 5 * 60_000_000_000
        while m1_start < m1_stop - 1 and int(bip1.ts_ns[m1_start]) <= min_ts:
            m1_start += 1
    return m1_start, m1_stop


def _step_v_protection(
    pos: _OpenPosition,
    bip1: Optional[BarSeries],
    use_m1: bool,
    m1_start: int,
    m1_stop: int,
    bar_open: float,
    bar_high: float,
    bar_low: float,
    bar_ts_ns: int,
    point_value: float,
    on_new_bar: bool,
) -> Tuple[Optional[_OpenPosition], Optional[TradeRecord]]:
    """Verifica SL/TP en la barra 5m actual o barra a barra sobre `bip1`."""
    if use_m1 and bip1 is not None and m1_start < m1_stop:
        if on_new_bar:
            pos.bars += 1
        for m in range(m1_start, m1_stop):
            closed = _check_protective_exit_on_bar(
                pos,
                float(bip1.open[m]),
                float(bip1.high[m]),
                float(bip1.low[m]),
                int(bip1.ts_ns[m]),
                point_value,
                update_bars=False,
            )
            if closed is not None:
                return None, closed
        return pos, None

    closed = _check_protective_exit_on_bar(
        pos, bar_open, bar_high, bar_low, bar_ts_ns, point_value, update_bars=on_new_bar
    )
    if closed is not None:
        return None, closed
    return pos, None


def run_v(
    ms: MultiSeriesContext,
    qty: int = 3,
    cfg: Optional[VaultConfig] = None,
) -> pd.DataFrame:
    """Ejecuta `VaultBreak` (`V`) sobre `ms.bip6` (5m RTH)."""
    cfg = cfg or VaultConfig()
    s: BarSeries = ms.bip6
    n = len(s.close)
    if n == 0 or qty <= 0:
        return trades_to_df([])

    bip1 = ms.bip1
    use_m1_sl_tp = _m1_mapping_valid(s, bip1)

    trades: List[TradeRecord] = []
    pos: Optional[_OpenPosition] = None
    pending_entry: Optional[int] = None          # qty
    pending_exit: Optional[_PendingMarketExit] = None
    seq = 0

    completed_ranges: Deque[float] = deque()
    rolling_range_sum = 0.0
    daily_atr = 0.0
    session_open = 0.0
    session_high = 0.0
    session_low = 0.0
    noise_up = 0.0
    cum_vol = 0.0
    cum_pv = 0.0
    session_vwap = 0.0
    trades_today = 0
    bars_below_vwap = 0
    has_session = False

    stop_dist = cfg.stop_loss_usd_per_contract / _NQ_SIGNAL_POINT_VALUE
    target_dist = cfg.profit_target_usd_per_contract / _NQ_SIGNAL_POINT_VALUE

    opens = s.open
    highs = s.high
    lows = s.low
    closes = s.close
    volumes = s.volume
    ts_ns = s.ts_ns
    hhmmss_ct = s.hhmmss_ct
    hhmmss_et = s.hhmmss_et
    is_new_sess = s.is_new_session
    tick = ms.tick_size
    pv = ms.point_value

    for i in range(n):
        o_i = float(opens[i])
        h_i = float(highs[i])
        l_i = float(lows[i])
        c_i = float(closes[i])
        t_ns = int(ts_ns[i])

        # 1) Ejecutar ordenes pendientes / proteccion SL-TP en la barra i
        if pending_exit is not None and pos is not None:
            seq += 1
            exit_ts = t_ns
            if use_m1_sl_tp:
                m1_start, m1_stop = _m1_slice_for_bip6_bar(s, bip1, i)
                if m1_start < m1_stop:
                    exit_ts = int(bip1.ts_ns[m1_start])
            trades.append(
                _make_trade_record(pos, exit_ts, o_i, f"V_X_{pending_exit.reason}_{seq}", pv)
            )
            pos = None
            pending_exit = None
        elif pending_entry is not None and pos is None:
            e_qty = pending_entry
            pending_entry = None
            seq += 1
            entry_ts = t_ns
            m1_start, m1_stop = (0, 0)
            if use_m1_sl_tp:
                m1_start, m1_stop = _m1_slice_for_bip6_bar(s, bip1, i)
                if m1_start < m1_stop:
                    entry_ts = int(bip1.ts_ns[m1_start])
            pos = _OpenPosition(
                module="V",
                side=+1,
                qty=e_qty,
                entry_time_utc=entry_ts,
                entry_price=o_i,
                stop_price=round_tick(o_i - stop_dist, tick),
                target_price=round_tick(o_i + target_dist, tick),
                entry_name=f"V_E_L_{seq}",
                seq=seq,
                max_high=o_i,
                min_low=o_i,
                bars=1,
            )
            pos, closed = _step_v_protection(
                pos, bip1, use_m1_sl_tp, m1_start, m1_stop, o_i, h_i, l_i, t_ns, pv, on_new_bar=False
            )
            if closed is not None:
                trades.append(closed)
        elif pos is not None:
            m1_start, m1_stop = (
                _m1_slice_for_bip6_bar(s, bip1, i) if use_m1_sl_tp else (0, 0)
            )
            pos, closed = _step_v_protection(
                pos, bip1, use_m1_sl_tp, m1_start, m1_stop, o_i, h_i, l_i, t_ns, pv, on_new_bar=True
            )
            if closed is not None:
                trades.append(closed)

        # 2) StartVaultSession al inicio de sesion RTH 5m
        if is_new_sess[i]:
            if has_session:
                prior_range = session_high - session_low
                if prior_range > 0.0:
                    completed_ranges.append(prior_range)
                    rolling_range_sum += prior_range
                    if len(completed_ranges) > cfg.daily_atr_length:
                        rolling_range_sum -= completed_ranges.popleft()
            if len(completed_ranges) < cfg.daily_atr_length:
                daily_atr = 0.0
            else:
                daily_atr = rolling_range_sum / len(completed_ranges)

            session_open = o_i
            session_high = h_i
            session_low = l_i
            noise_up = (
                0.0
                if daily_atr <= 0.0
                else (session_open + cfg.noise_multiplier * daily_atr)
            )
            cum_vol = 0.0
            cum_pv = 0.0
            session_vwap = c_i
            trades_today = 0
            bars_below_vwap = 0
            has_session = True
        elif not has_session:
            continue

        # 3) Actualizacion intrabar de extremos, VWAP y contador debajo de VWAP
        if h_i > session_high:
            session_high = h_i
        if l_i < session_low:
            session_low = l_i

        vol = max(0.0, float(volumes[i]))
        if vol > 0.0:
            tp = (h_i + l_i + c_i) / 3.0
            cum_pv += tp * vol
            cum_vol += vol
        session_vwap = c_i if cum_vol <= 0.0 else (cum_pv / cum_vol)

        if c_i < session_vwap:
            bars_below_vwap += 1
        else:
            bars_below_vwap = 0

        t_et = int(hhmmss_et[i])

        # 4) Salidas por tiempo o VWAP si esta Long
        if pos is not None:
            if t_et >= cfg.flatten_time_eastern:
                pending_exit = _PendingMarketExit("TIME")
                continue
            if bars_below_vwap >= cfg.vwap_exit_bars:
                pending_exit = _PendingMarketExit("VWAP")
                continue
            continue

        # 5) Entrada Long
        if daily_atr <= 0.0 or trades_today >= cfg.maximum_trades_per_day:
            continue
        # IL mod_V.txt IL_0134-0152: V_BlockedEntryHour usa Times[6][0].Hour (hora plataforma CT, NO V_1 ET)
        if cfg.block_entry_hour_enabled and (int(hhmmss_ct[i]) // 10000) == cfg.blocked_entry_hour:
            continue
        if t_et < cfg.earliest_entry_eastern or t_et > cfg.latest_entry_eastern:
            continue
        if c_i <= noise_up or c_i <= session_vwap:
            continue

        pending_entry = int(qty)
        trades_today += 1

    return trades_to_df(trades)


# ---------------------------------------------------------------------------
# Modulo O: Overnight (ms.bip1 1m ETH + ms.bip7 1d RTH)
# ---------------------------------------------------------------------------
#
# NOTA DE AUDITORIA SOBRE EL BACKTEST DEL CSV (`NinjaTrader Grid`, 2026-01-01 .. 2026-09-30):
# En el CSV de NinjaTrader, el modulo Overnight (`O`) registro **0 trades** exactamente por:
# 1) **Techo de margen en `TryOvernightSignal`**:
#    Con los defaults del IL (`O_CapitalUsd = 100,000`, `O_MaximumMarginPercent = 50%`,
#    `O_MarginPerContractUsd = 0`, `O_MarginRatePercent = 10%`), el margen por contrato
#    se calcula como `dailyClose * 20 * 0.10 = 2.0 * dailyClose`, frente a un maximo
#    permitido de `$50,000` (`100,000 * 50%`).
#    Por lo tanto, `floor(50,000 / (2.0 * dailyClose)) = floor(25,000 / dailyClose)` es **0**
#    siempre que `NQ > 25,000`! Al hacer `contracts = min(contracts, 0) = 0 < MinimumContracts (1)`,
#    `TryOvernightSignal` devuelve `false` en ~93% del periodo Ene-Sep 2026 (NQ entre 25,000 y 31,370).
# 2) **Filtro de tendencia durante el unico tramo <= 25,000**:
#    Los unicos dias de Feb-Sep 2026 con NQ <= 25,000 (9-mar y 20-mar..7-abr 2026) fueron una
#    correccion bajista donde `dailyClose <= SMA20` (`O_UseTrendFilter = True`) y/o pendiente
#    5d de la SMA20 <= 0 (`O_UseRisingMaSlopeFilter = True`), rechazando tambien esos dias.
# 3) **Detalle adicional de retornos en IL**:
#    En `TryOvernightSignal` (`mod_O.txt` IL_0043..IL_0076), el retorno usado para la volatilidad
#    no es logaritmico (`Math.Log`) sino el retorno simple del gap nocturno
#    `(Opens[7][i] - Closes[7][i + 1]) / Closes[7][i + 1]` sobre `O_VolatilityLookback` (20) dias.
#
# En que condiciones SI dispara `O`:
# - Con defaults de capital/margen: cuando `NQ <= 25,000` (ej. 2020-2025) O cuando se ajusta
#   `capital_usd` / `maximum_margin_percent` / `margin_per_contract_usd` (o se pasa `qty` explicito),
# - En dia no-viernes (`allow_friday_entries=False`),
# - Con `dailyClose > SMA20` (19 cierres diarios previos + `dailyClose`),
# - Con `SMA20_actual > SMA20_hace_5_dias`,
# - Con rango RTH actual <= `1.5 * ATR20(H-L)`,
# - Y si `use_down_rth_day_filter=True`, ademas `dailyClose < RTH_Open_hoy`.
# - Si `use_post_maintenance_entry=True` (default): evalua senal a las `15:00 CT` (`barEnd`) y
#   ejecuta entrada Long al mercado a partir de las `17:01 CT` (tras el mantenimiento CME 15:44-17:01),
#   saliendo al `OPEN` de las `08:30 CT` del dia siguiente (`barEnd.Date > entryDate`).
# ---------------------------------------------------------------------------


def _overnight_current_daily_average(
    daily_closes_hist: np.ndarray,
    d_prev: int,
    length: int,
    current_close: float,
) -> float:
    """Traduccion exacta de `FUNDEDSYNCSTACK.OvernightCurrentDailyAverage`."""
    total = current_close
    for k in range(1, length):
        total += float(daily_closes_hist[d_prev - (k - 1)])
    return total / float(length)


def _try_overnight_signal(
    cfg: OvernightConfig,
    daily_close: float,
    rth_open_today: float,
    d_opens: np.ndarray,
    d_closes: np.ndarray,
    d_prev: int,
) -> Tuple[bool, int, float, bool]:
    """Traduccion exacta de `FUNDEDSYNCSTACK.TryOvernightSignal`.

    Retorna `(ok, contracts, volatility, trend_on)`.
    """
    cur_ma = _overnight_current_daily_average(
        d_closes, d_prev, cfg.moving_average_length, daily_close
    )
    trend_on = daily_close > cur_ma

    # Desviacion estandar poblacional de retornos simples nocturnos: (Opens[7][i] - Closes[7][i+1]) / Closes[7][i+1]
    lb = cfg.volatility_lookback
    sum_r = 0.0
    sum_sq = 0.0
    for k in range(lb):
        open_k = rth_open_today if k == 0 else float(d_opens[d_prev - (k - 1)])
        prev_close_k = float(d_closes[d_prev - k])
        ret = (open_k - prev_close_k) / prev_close_k
        sum_r += ret
        sum_sq += ret * ret

    mean_r = sum_r / float(lb)
    volatility = math.sqrt(max(0.0, (sum_sq / float(lb)) - (mean_r * mean_r)))
    dollar_vol = volatility * daily_close * _NQ_SIGNAL_POINT_VALUE

    if dollar_vol <= 0.0:
        raw_contracts = float(cfg.minimum_contracts)
    else:
        raw_contracts = cfg.target_risk_usd / dollar_vol

    contracts = max(cfg.minimum_contracts, int(math.floor(raw_contracts + 0.5)))

    margin_per_contract = (
        cfg.margin_per_contract_usd
        if cfg.margin_per_contract_usd > 0.0
        else (daily_close * _NQ_SIGNAL_POINT_VALUE * cfg.margin_rate_percent / 100.0)
    )
    if margin_per_contract > 0.0:
        max_margin_contracts = int(
            math.floor((cfg.capital_usd * cfg.maximum_margin_percent / 100.0) / margin_per_contract)
        )
        contracts = min(contracts, max_margin_contracts)

    contracts = min(contracts, cfg.maximum_contracts)
    return (contracts >= cfg.minimum_contracts), contracts, volatility, trend_on


def _passes_overnight_regime(
    cfg: OvernightConfig,
    daily_close: float,
    bar_end_dow_ct: int,
    rth_open_today: float,
    rth_high_today: float,
    rth_low_today: float,
    d_highs: np.ndarray,
    d_lows: np.ndarray,
    d_closes: np.ndarray,
    d_prev: int,
) -> bool:
    """Traduccion exacta de `FUNDEDSYNCSTACK.PassesOvernightRegime`."""
    if not cfg.allow_friday_entries and bar_end_dow_ct == 4:  # Viernes
        return False

    if cfg.use_down_rth_day_filter and daily_close >= rth_open_today:
        return False

    if cfg.use_rising_ma_slope_filter:
        cur_ma = _overnight_current_daily_average(
            d_closes, d_prev, cfg.moving_average_length, daily_close
        )
        prev_sum = 0.0
        slope_lb = cfg.ma_slope_lookback
        ma_len = cfg.moving_average_length
        # En IL: V_3 = slope_lb .. slope_lb + ma_len - 1 -> Closes[7][V_3]
        for k in range(slope_lb, slope_lb + ma_len):
            prev_sum += float(d_closes[d_prev - (k - 1)])
        prev_ma = prev_sum / float(ma_len)
        if cur_ma <= prev_ma:
            return False

    if cfg.use_rth_range_filter:
        today_range = rth_high_today - rth_low_today
        atr_len = cfg.range_atr_length
        sum_range = 0.0
        for k in range(1, atr_len + 1):
            idx = d_prev - (k - 1)
            sum_range += float(d_highs[idx] - d_lows[idx])
        atr = sum_range / float(atr_len)
        if atr > 0.0 and today_range > cfg.maximum_rth_range_to_atr * atr:
            return False

    return True


def run_o(
    ms: MultiSeriesContext,
    qty: Optional[int] = None,
    cfg: Optional[OvernightConfig] = None,
) -> pd.DataFrame:
    """Ejecuta `Overnight` (`O`) sobre `ms.bip1` (1m ETH) y `ms.bip7` (1d RTH).

    Si `qty is None`, usa el sizing dinamico completo de `TryOvernightSignal * base_qty`
    (incluyendo el limite de margen que produce 0 contratos cuando `NQ > 25,000` bajo defaults).
    Si `qty` es un entero explicito, sobrescribe los contratos tras evaluar `trend_on` y
    `PassesOvernightRegime`.
    """
    cfg = cfg or OvernightConfig()
    s1: BarSeries = ms.bip1
    s7: BarSeries = ms.bip7
    n1 = len(s1.close)
    n7 = len(s7.close)
    min_daily_bars = max(
        cfg.moving_average_length + cfg.ma_slope_lookback - 1,
        max(cfg.volatility_lookback + 1, cfg.range_atr_length),
    )
    if n1 == 0 or n7 <= min_daily_bars:
        return trades_to_df([])
    if qty is not None and qty <= 0:
        return trades_to_df([])

    # Vectorizado causal de barEnd = Times[1][0].AddMinutes(1.0) en America/Chicago
    bar_end_ct_idx = pd.DatetimeIndex(
        pd.to_datetime(s1.ts_ns + 60_000_000_000, unit="ns", utc=True)
    ).tz_convert("America/Chicago")
    end_hhmmss_ct = (
        bar_end_ct_idx.hour * 10000 + bar_end_ct_idx.minute * 100 + bar_end_ct_idx.second
    ).to_numpy(dtype=np.int32)
    end_date_ct = (
        bar_end_ct_idx.year * 10000 + bar_end_ct_idx.month * 100 + bar_end_ct_idx.day
    ).to_numpy(dtype=np.int32)
    end_dow_ct = bar_end_ct_idx.dayofweek.to_numpy(dtype=np.int8)

    trades: List[TradeRecord] = []
    pos: Optional[_OpenPosition] = None
    pending_entry: Optional[int] = None
    pending_exit: Optional[_PendingMarketExit] = None
    seq = 0

    overnight_exit_pending = False
    entry_date_o = -1
    post_break_entry_pending = False
    post_break_signal_date = -1
    post_break_contracts = 0

    # Estado causal RTH del dia actual sobre bip1 (08:30 < hhmmss_ct <= 15:15)
    rth_date = -1
    rth_open = 0.0
    rth_high = 0.0
    rth_low = 0.0

    # Puntero al ultimo bar diario RTH completado estrictamente antes de cal_date_ct[i]
    d_prev = -1

    opens1 = s1.open
    highs1 = s1.high
    lows1 = s1.low
    closes1 = s1.close
    ts1 = s1.ts_ns
    hhmmss1_ct = s1.hhmmss_ct
    cal1_ct = s1.cal_date_ct
    dow1_ct = s1.dow_ct

    d_opens = s7.open
    d_highs = s7.high
    d_lows = s7.low
    d_closes = s7.close
    d_dates = s7.cal_date_ct

    pv = ms.point_value

    for i in range(n1):
        o_i = float(opens1[i])
        h_i = float(highs1[i])
        l_i = float(lows1[i])
        c_i = float(closes1[i])
        t_ns = int(ts1[i])
        t_ct = int(hhmmss1_ct[i])
        cal_i = int(cal1_ct[i])

        # 1) Ejecutar ordenes de mercado pendientes al open de la barra i
        if pending_exit is not None and pos is not None:
            seq += 1
            trades.append(
                _make_trade_record(pos, t_ns, o_i, f"O_X_{pending_exit.reason}_{seq}", pv)
            )
            pos = None
            pending_exit = None
        elif pending_entry is not None and pos is None:
            e_qty = pending_entry
            pending_entry = None
            seq += 1
            pos = _OpenPosition(
                module="O",
                side=+1,
                qty=e_qty,
                entry_time_utc=t_ns,
                entry_price=o_i,
                stop_price=float("nan"),
                target_price=float("nan"),
                entry_name=f"O_E_L_{seq}",
                seq=seq,
                max_high=o_i,
                min_low=o_i,
                bars=1,
            )
        elif pos is not None:
            pos.bars += 1
            pos.max_high = max(pos.max_high, h_i)
            pos.min_low = min(pos.min_low, l_i)

        # 2) Avanzar puntero de barras diarias completadas estrictamente previas a `cal_i`
        while (d_prev + 1) < n7 and int(d_dates[d_prev + 1]) < cal_i:
            d_prev += 1

        # 3) Acumular OHLC RTH causal de `cal_i` en curso (08:30 < t_ct <= 15:15)
        if 83000 < t_ct <= 151500:
            if rth_date != cal_i:
                rth_date = cal_i
                rth_open = o_i
                rth_high = h_i
                rth_low = l_i
            else:
                if h_i > rth_high:
                    rth_high = h_i
                if l_i < rth_low:
                    rth_low = l_i

        # 4) EnforceDailyFuturesClose (en OnBarUpdate antes de RunOvernight)
        maint_blocked = False
        if cfg.enforce_daily_futures_close:
            maint_blocked = _is_daily_futures_close_blocked(
                t_ct,
                int(dow1_ct[i]),
                cfg.daily_futures_flatten_time_ct,
                cfg.daily_futures_resume_time_ct,
            )
            if maint_blocked:
                pending_entry = None
                if pos is not None and pending_exit is None:
                    pending_exit = _PendingMarketExit("DAILY_FUTURES_CLOSE")
                    overnight_exit_pending = False

        # Warmup equivalente a `CurrentBars[7] < min_daily_bars`
        # Necesitamos al menos `min_daily_bars` barras previas completadas (`d_prev + 1 >= min_daily_bars`).
        if (d_prev + 1) < min_daily_bars:
            continue

        bar_end_time = int(end_hhmmss_ct[i])
        bar_end_d = int(end_date_ct[i])
        bar_end_dow = int(end_dow_ct[i])

        can_enter = (
            (pos is None)
            and (pending_entry is None)
            and (pending_exit is None)
            and (not maint_blocked)
        )

        # 5) Salida a las 08:30 CT (`OPEN`)
        if overnight_exit_pending:
            if (
                bar_end_time >= cfg.exit_time_central
                and bar_end_time < cfg.entry_time_central
                and bar_end_d > entry_date_o
            ):
                if pos is not None and pending_exit is None:
                    pending_exit = _PendingMarketExit("OPEN")
                overnight_exit_pending = False
                continue

        # 6) Entrada diferida post-mantenimiento (>= 17:01 CT del mismo dia de senal)
        if (
            cfg.use_post_maintenance_entry
            and post_break_entry_pending
            and post_break_signal_date == bar_end_d
            and bar_end_time >= cfg.post_maintenance_entry_time_central
            and can_enter
            and not overnight_exit_pending
        ):
            exec_qty = int(qty) if qty is not None else max(0, post_break_contracts * cfg.base_qty)
            if exec_qty > 0:
                pending_entry = exec_qty
                overnight_exit_pending = True
                entry_date_o = bar_end_d
            post_break_entry_pending = False
            continue

        # 7) Evaluacion de senal a las 15:00 CT
        if not (
            bar_end_time == cfg.entry_time_central
            and can_enter
            and not overnight_exit_pending
        ):
            continue

        post_break_entry_pending = False

        # Barra RTH en curso del dia [0]: causal desde bip1 (fallback a bip7 si ya cerro)
        if rth_date == cal_i:
            cur_rth_open = rth_open
            cur_rth_high = rth_high
            cur_rth_low = rth_low
        elif (d_prev + 1) < n7 and int(d_dates[d_prev + 1]) == cal_i and int(s7.ts_ns[d_prev + 1]) <= t_ns:
            idx_today = d_prev + 1
            cur_rth_open = float(d_opens[idx_today])
            cur_rth_high = float(d_highs[idx_today])
            cur_rth_low = float(d_lows[idx_today])
        else:
            continue

        ok_sig, native_contracts, _, trend_on = _try_overnight_signal(
            cfg, c_i, cur_rth_open, d_opens, d_closes, d_prev
        )
        if qty is None and not ok_sig:
            continue
        if cfg.use_trend_filter and not trend_on:
            continue
        if not _passes_overnight_regime(
            cfg,
            c_i,
            bar_end_dow,
            cur_rth_open,
            cur_rth_high,
            cur_rth_low,
            d_highs,
            d_lows,
            d_closes,
            d_prev,
        ):
            continue

        if cfg.use_post_maintenance_entry:
            post_break_contracts = native_contracts
            post_break_signal_date = bar_end_d
            post_break_entry_pending = True
            continue

        exec_qty = int(qty) if qty is not None else max(0, native_contracts * cfg.base_qty)
        if exec_qty > 0:
            pending_entry = exec_qty
            overnight_exit_pending = True
            entry_date_o = bar_end_d

    return trades_to_df(trades)


# ---------------------------------------------------------------------------
# Wrappers `senales_*`
# ---------------------------------------------------------------------------


def senales_p(
    ms: MultiSeriesContext,
    qty: Optional[int] = None,
    cfg: Optional[PullbackConfig] = None,
) -> pd.DataFrame:
    """Wrapper de compatibilidad alrededor de `run_p`."""
    return run_p(ms, qty=qty, cfg=cfg)


def senales_c(
    ms: MultiSeriesContext,
    qty: int = 1,
    cfg: Optional[CapstoneConfig] = None,
) -> pd.DataFrame:
    """Wrapper de compatibilidad alrededor de `run_c`."""
    return run_c(ms, qty=qty, cfg=cfg)


def senales_v(
    ms: MultiSeriesContext,
    qty: int = 3,
    cfg: Optional[VaultConfig] = None,
) -> pd.DataFrame:
    """Wrapper de compatibilidad alrededor de `run_v`."""
    return run_v(ms, qty=qty, cfg=cfg)


def senales_o(
    ms: MultiSeriesContext,
    qty: Optional[int] = None,
    cfg: Optional[OvernightConfig] = None,
) -> pd.DataFrame:
    """Wrapper de compatibilidad alrededor de `run_o`."""
    return run_o(ms, qty=qty, cfg=cfg)


__all__ = [
    "PullbackConfig",
    "CapstoneConfig",
    "VaultConfig",
    "OvernightConfig",
    "run_p",
    "run_c",
    "run_v",
    "run_o",
    "senales_p",
    "senales_c",
    "senales_v",
    "senales_o",
]
