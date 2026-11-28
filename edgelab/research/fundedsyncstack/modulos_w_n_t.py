"""Traduccion fiel a Python del Lote 3 (modulos W, N, T) de FUNDEDSYNCSTACK5.dll.

Modulos incluidos:
- W (`VwapCross`): cruce alcista de VWAP intradiario en 1m ETH (`ms.bip1`, Central Time).
- N (`NDayLong`): ruptura long de maximo de N dias en 1m ETH + 1d ETH (`ms.bip1`, `ms.bip8`, Central Time).
- T (`FtmOrb` / `FtmEngine`): ORB 09:30-09:45 ET en 1m ETH (`ms.bip1`, Eastern Time) con filtro de
  geometria/toques, vector de 14 features, KNN trimestral sobre etiquetas shadow exclusivas,
  refinamiento en 2 etapas y gestion dinamica de stop/target por regimen.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
import datetime as dt
import math
from typing import Any, Deque, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

try:
    from . import contracts
except ImportError:
    import contracts

_TZ_CT = ZoneInfo("America/Chicago")
_TZ_ET = ZoneInfo("America/New_York")
_NS_PER_MIN = 60_000_000_000

FTM_MODEL_FEATURE_NAMES: Tuple[str, ...] = (
    "aligned_gap_bps",
    "aligned_prior_session_open_to_rth_close_bps",
    "aligned_prior_ret_5_bps",
    "aligned_prior_ret_20_bps",
    "aligned_vwap_distance_bps",
    "aligned_ret_30m_bps",
    "breakout_side",
    "signal_elapsed_15m",
    "orb_bps",
    "touch_count",
    "weekday_sin",
    "weekday_cos",
    "month_sin",
    "month_cos",
)

FTM_CONTRACT_ROLL_EXCLUSION_DATE_KEYS: frozenset[int] = frozenset(
    {
        20200311,
        20200610,
        20200909,
        20210609,
        20210908,
        20220608,
        20220907,
        20260611,
    }
)

FTM_DEGRADED_DATA_EXCLUSION_DATE_KEYS: frozenset[int] = frozenset(
    {
        20200227,
        20200228,
        20200630,
        20200701,
        20200702,
        20211206,
        20220103,
        20240918,
        20240919,
        20250917,
        20250918,
        20250924,
        20250925,
        20251128,
        20260316,
        20260317,
        20260410,
        20260525,
        20260730,
        20260731,
    }
)


# ---------------------------------------------------------------------------
# Configuraciones (defaults exactos del IL; enable=True para ejecucion directa)
# ---------------------------------------------------------------------------


@dataclass
class VwapCrossConfig:
    """Parametros de `RunVwapCross` (modulo W) segun defaults del IL."""

    exit_on_vwap_cross: bool = True   # EdgeLab 2026-11-16 (PREREGISTRO_TANDA2 L1): False = sin salida por recruce del VWAP (variante)
    enable: bool = True
    vwap_start_time_central: int = 83000
    vwap_end_time_central: int = 150000
    initial_entry_boundary_central: int = 83100
    use_last_entry_time_filter: bool = True
    last_entry_time_central: int = 140000
    allow_reentries: bool = True
    use_vwap_slope_filter: bool = False
    vwap_slope_lookback_bars: int = 20
    minimum_vwap_slope_ticks: float = 0.0
    use_vwap_distance_filter: bool = False
    minimum_vwap_distance_ticks: float = 4.0
    use_confirmation_filter: bool = False
    confirmation_bars: int = 2
    use_cooldown_filter: bool = True
    cooldown_bars: int = 5
    use_prior_rth_range_filter: bool = False
    rth_range_lookback_sessions: int = 20
    minimum_prior_range_ratio: float = 0.75
    maximum_prior_range_ratio: float = 0.0


@dataclass
class NDayConfig:
    """Parametros de `RunNDay` (modulo N) segun defaults del IL."""

    enable: bool = True
    num_days: int = 5
    last_entry_time: int = 154500
    flatten_time: int = 160000
    treat_marketable_stop_as_market: bool = True
    use_daily_efficiency_filter: bool = False
    efficiency_lookback_days: int = 10
    minimum_daily_efficiency: float = 0.3
    use_rth_vwap_acceptance_filter: bool = True
    vwap_slope_lookback_minutes: int = 15
    use_breakout_acceptance_filter: bool = True
    acceptance_buffer_points: float = 4.0
    acceptance_confirmation_bars: int = 2
    use_volatility_scaled_loss_exit: bool = True
    maximum_loss_prior_range_fraction: float = 1.0
    use_dollar_risk_gate: bool = False
    maximum_estimated_loss_usd: float = 10000.0
    use_volatility_position_sizing: bool = False
    target_risk_usd: float = 3000.0
    maximum_contracts: int = 20
    use_failed_breakout_exit: bool = True
    failure_buffer_points: float = 0.0
    failure_confirmation_bars: int = 6
    use_choppy_high_volatility_filter: bool = False
    regime_short_range_length: int = 5
    regime_long_range_length: int = 20
    minimum_volatility_expansion_ratio: float = 1.25
    maximum_regime_efficiency: float = 0.25
    flatten_before_daily_futures_close: bool = True
    daily_futures_flatten_time_central: int = 154400
    daily_futures_resume_time_central: int = 170100


@dataclass
class FtmConfig:
    """Parametros de `FtmEngine` (modulo T) segun defaults y constantes del IL."""

    enable: bool = True
    orb_start_minute_et: int = 570
    orb_end_minute_et: int = 585
    orb_bars: int = 15
    cash_close_minute_et: int = 960
    quarter_hour_start_minute_et: int = 600
    conditional_exit_minute_et: int = 930
    breakout_buffer_ticks: int = 1
    admission_min_body_ratio: float = 0.15
    admission_min_close_location: float = 0.60
    admission_min_touches: int = 3
    prior_session_override_bps: float = -300.0
    knn_k: int = 15
    knn_laplace_alpha: float = 2.0
    knn_flip_probability_threshold: float = 0.65
    knn_min_training_rows: int = 100
    knn_min_session_date: int = 20120101
    shadow_min_session_date: int = 20100101
    shadow_slippage_ticks: int = 1
    shadow_round_turn_commission_usd: float = 2.5
    portfolio_start_cash_date: int = 20120101
    orb_history_window: int = 120
    orb_high_vol_quantile: float = 0.75
    rth_close_history_window: int = 21
    direct_first_signal_elapsed_15m: float = 1.0
    direct_first_signal_max_vwap_bps: float = 20.0
    weak_signal_max_body_ratio: float = 0.20
    weak_signal_delay_bars: int = 1
    high_vol_max_direction_touches: int = 3
    high_vol_vote_bars: int = 3
    final_prior_disagreement_min_bps: float = 100.0
    final_prior_disagreement_bars: int = 2
    final_intraday_min_ret30_bps: float = 25.0
    final_intraday_max_extension: float = 0.25
    final_intraday_bars: int = 1
    stop_orb_multiplier: float = 1.25
    stop_min_points: float = 2.0
    stop_max_points: float = 100.0
    # EdgeLab (ADAPTAR-PRESENTE, 2026-11-26): si > 0, los topes en puntos se escalan por precio_actual / escala_precio_ref
    # (precio actual = medio del rango de apertura, causal). 0 = comportamiento del vendedor.
    escala_precio_ref: float = 0.0
    high_orb_target_r: float = 1.25
    high_orb_trigger_r: float = 1.25
    high_orb_lock_r: float = 0.0
    countertrend_target_r: float = 3.0
    countertrend_trigger_r: float = 0.75
    countertrend_lock_r: float = 0.10
    baseline_target_r: float = 3.0
    baseline_trigger_r: float = 1.25
    baseline_lock_r: float = 0.0
    use_exclusion_calendars: bool = True


# ---------------------------------------------------------------------------
# Helpers compartidos (sin duplicacion entre modulos)
# ---------------------------------------------------------------------------


def _push_history(values: np.ndarray, next_index: int, value: float) -> int:
    values[next_index % len(values)] = value
    return next_index + 1


def _history_value(values: Optional[np.ndarray], next_index: int, bars_ago: int) -> float:
    if values is None or next_index <= bars_ago:
        return 0.0
    n = len(values)
    slot = (next_index - 1 - bars_ago) % n
    return float(values[slot])


def _compute_chicago_next_minute_hhmmss(ts_ns: np.ndarray) -> np.ndarray:
    """Equivalente exacto a `ToTime(Times[bip][0].AddMinutes(1.0))` en zona Chicago."""
    if len(ts_ns) == 0:
        return np.zeros(0, dtype=np.int32)
    idx_ct = pd.DatetimeIndex(
        pd.to_datetime(ts_ns + _NS_PER_MIN, unit="ns", utc=True)
    ).tz_convert(_TZ_CT)
    return (idx_ct.hour * 10000 + idx_ct.minute * 100 + idx_ct.second).to_numpy(dtype=np.int32)


def _calc_excursion_usd(
    side: int,
    qty: int,
    point_value: float,
    entry_price: float,
    exit_price: float,
    entry_idx: int,
    exit_idx: int,
    highs: np.ndarray,
    lows: np.ndarray,
    exit_at_open: bool,
) -> Tuple[float, float]:
    """Calcula `(mae_usd <= 0, mfe_usd >= 0)` sobre las barras activas del trade."""
    if exit_idx < entry_idx:
        pts = side * (exit_price - entry_price)
        mae_pts = min(0.0, pts)
        mfe_pts = max(0.0, pts)
        scale = float(qty) * float(point_value)
        return mae_pts * scale, mfe_pts * scale

    end_exclusive = exit_idx if exit_at_open else exit_idx + 1
    if end_exclusive > entry_idx:
        seg_hi = float(np.max(highs[entry_idx:end_exclusive]))
        seg_lo = float(np.min(lows[entry_idx:end_exclusive]))
    else:
        seg_hi = entry_price
        seg_lo = entry_price

    if side > 0:
        best_px = max(seg_hi, exit_price)
        worst_px = min(seg_lo, exit_price)
        mfe_pts = max(0.0, best_px - entry_price)
        mae_pts = min(0.0, worst_px - entry_price)
    else:
        best_px = min(seg_lo, exit_price)
        worst_px = max(seg_hi, exit_price)
        mfe_pts = max(0.0, entry_price - best_px)
        mae_pts = min(0.0, entry_price - worst_px)

    scale = float(qty) * float(point_value)
    return mae_pts * scale, mfe_pts * scale


def _make_trade_record(
    module: str,
    side: int,
    qty: int,
    entry_idx: int,
    exit_idx: int,
    entry_price: float,
    exit_price: float,
    stop_price: float,
    target_price: float,
    entry_name: str,
    exit_name: str,
    ts_ns: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    point_value: float,
    exit_at_open: bool,
) -> contracts.TradeRecord:
    pnl_pts = float(side) * (float(exit_price) - float(entry_price))
    pnl_usd = pnl_pts * float(qty) * float(point_value)
    mae_usd, mfe_usd = _calc_excursion_usd(
        side=side,
        qty=qty,
        point_value=point_value,
        entry_price=float(entry_price),
        exit_price=float(exit_price),
        entry_idx=entry_idx,
        exit_idx=exit_idx,
        highs=highs,
        lows=lows,
        exit_at_open=exit_at_open,
    )
    bars = max(1, int(exit_idx - entry_idx + 1))
    return contracts.TradeRecord(
        module=module,
        side=side,
        qty=int(qty),
        entry_time_utc=int(ts_ns[entry_idx]),
        exit_time_utc=int(ts_ns[exit_idx]),
        entry_price=float(entry_price),
        exit_price=float(exit_price),
        stop_price=float(stop_price),
        target_price=float(target_price),
        entry_name=entry_name,
        exit_name=exit_name,
        pnl_pts=pnl_pts,
        pnl_usd=pnl_usd,
        mae_usd=mae_usd,
        mfe_usd=mfe_usd,
        bars=bars,
    )


def _date_key_to_date(key: int) -> dt.date:
    return dt.date(key // 10000, (key // 100) % 100, key % 100)


def _date_to_key(d: dt.date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def _build_cfg(cfg_cls: Any, cfg: Optional[Any], overrides: Dict[str, Any]) -> Any:
    base = cfg_cls() if cfg is None else cfg
    if overrides:
        return replace(base, **overrides)
    return base


# ---------------------------------------------------------------------------
# Modulo W: VwapCross (ms.bip1 1m ETH, Central Time)
# ---------------------------------------------------------------------------


def _passes_vwap_range_filter(
    completed_ranges: Deque[float],
    completed_range_sum: float,
    prior_rth_range: float,
    cfg: VwapCrossConfig,
) -> bool:
    if len(completed_ranges) < cfg.rth_range_lookback_sessions or prior_rth_range <= 0.0:
        return False
    avg_range = completed_range_sum / float(len(completed_ranges))
    if prior_rth_range < avg_range * cfg.minimum_prior_range_ratio:
        return False
    if cfg.maximum_prior_range_ratio > 0.0 and prior_rth_range > avg_range * cfg.maximum_prior_range_ratio:
        return False
    return True


def _vwap_has_confirmed_closes(
    i: int,
    closes: np.ndarray,
    chart_times: np.ndarray,
    vwap_hist: np.ndarray,
    vwap_hist_idx: int,
    cfg: VwapCrossConfig,
) -> bool:
    for k in range(cfg.confirmation_bars):
        if i < k:
            return False
        t_k = int(chart_times[i - k])
        if t_k < cfg.vwap_start_time_central or t_k >= cfg.vwap_end_time_central:
            return False
        vwap_k = _history_value(vwap_hist, vwap_hist_idx, k)
        if not (float(closes[i - k]) > vwap_k):
            return False
    return True


def _passes_vwap_filters(
    i: int,
    boundary: int,
    tick_size: float,
    closes: np.ndarray,
    chart_times: np.ndarray,
    session_vwap: float,
    vwap_hist: np.ndarray,
    vwap_hist_idx: int,
    last_long_exit_bar: int,
    completed_ranges: Deque[float],
    completed_range_sum: float,
    prior_rth_range: float,
    cfg: VwapCrossConfig,
) -> bool:
    if cfg.use_last_entry_time_filter and boundary >= cfg.last_entry_time_central:
        return False
    if cfg.use_cooldown_filter and last_long_exit_bar != -2147483648:
        if i - last_long_exit_bar < cfg.cooldown_bars:
            return False
    if cfg.use_vwap_distance_filter:
        if not (float(closes[i]) - session_vwap >= cfg.minimum_vwap_distance_ticks * tick_size):
            return False
    if cfg.use_vwap_slope_filter:
        if i < cfg.vwap_slope_lookback_bars:
            return False
        prev_vwap = _history_value(vwap_hist, vwap_hist_idx, cfg.vwap_slope_lookback_bars)
        if not (session_vwap - prev_vwap >= cfg.minimum_vwap_slope_ticks * tick_size):
            return False
    if cfg.use_confirmation_filter:
        if not _vwap_has_confirmed_closes(i, closes, chart_times, vwap_hist, vwap_hist_idx, cfg):
            return False
    if cfg.use_prior_rth_range_filter:
        if not _passes_vwap_range_filter(completed_ranges, completed_range_sum, prior_rth_range, cfg):
            return False
    return True


def run_w(
    ms: contracts.MultiSeriesContext,
    qty: int = 1,
    cfg: Optional[VwapCrossConfig] = None,
) -> pd.DataFrame:
    """Ejecuta el modulo W (`VwapCross`) sobre `ms.bip1` (1m ETH, Long-only)."""
    cfg = VwapCrossConfig() if cfg is None else cfg
    if not cfg.enable or qty <= 0:
        return contracts.trades_to_df([])

    b1 = ms.bip1
    n = len(b1.close)
    if n < 2:
        return contracts.trades_to_df([])

    ts_ns = b1.ts_ns
    opens = b1.open
    highs = b1.high
    lows = b1.low
    closes = b1.close
    volumes = b1.volume
    chart_times = b1.hhmmss_ct
    cal_dates_ct = b1.cal_date_ct
    boundaries = _compute_chicago_next_minute_hhmmss(ts_ns)

    hist_len = max(241, cfg.vwap_slope_lookback_bars + cfg.confirmation_bars + 2)
    vwap_hist = np.zeros(hist_len, dtype=np.float64)
    vwap_hist_idx = 0

    cum_pv = 0.0
    cum_vol = 0.0
    session_vwap = 0.0
    signal_side = 0  # 0=unset, 1=above VWAP, 2=below VWAP (Long-only; nunca entra Short)
    last_long_exit_bar = -2147483648

    active_rth_date: Optional[int] = None
    has_active_rth_range = False
    current_rth_high = 0.0
    current_rth_low = 0.0
    prior_rth_range = 0.0
    completed_ranges: Deque[float] = deque()
    completed_range_sum = 0.0

    # Estado de posicion / orden pendiente (OnBarClose: Market orden de barra i llena en open[i+1])
    in_pos = False
    entry_idx = -1
    entry_price = 0.0
    pending_entry = False
    pending_exit_reason: Optional[str] = None
    trades: List[contracts.TradeRecord] = []

    for i in range(n):
        # Fills al open de la barra i para ordenes enviadas al cierre de i-1
        if pending_exit_reason is not None and in_pos:
            trades.append(
                _make_trade_record(
                    module="W",
                    side=1,
                    qty=qty,
                    entry_idx=entry_idx,
                    exit_idx=i,
                    entry_price=entry_price,
                    exit_price=float(opens[i]),
                    stop_price=math.nan,
                    target_price=math.nan,
                    entry_name="W_E_L",
                    exit_name=pending_exit_reason,
                    ts_ns=ts_ns,
                    highs=highs,
                    lows=lows,
                    point_value=ms.point_value,
                    exit_at_open=True,
                )
            )
            in_pos = False
            pending_exit_reason = None
        elif pending_entry and not in_pos:
            in_pos = True
            entry_idx = i
            entry_price = float(opens[i])
            pending_entry = False

        if i < 1:
            continue

        t1 = int(chart_times[i])
        t2 = int(boundaries[i])
        in_vwap_win = cfg.vwap_start_time_central <= t1 < cfg.vwap_end_time_central

        if in_vwap_win:
            bar_date = int(cal_dates_ct[i])
            if active_rth_date != bar_date:
                if has_active_rth_range and current_rth_high > current_rth_low:
                    prior_rth_range = current_rth_high - current_rth_low
                    completed_ranges.append(prior_rth_range)
                    completed_range_sum += prior_rth_range
                    while len(completed_ranges) > cfg.rth_range_lookback_sessions:
                        completed_range_sum -= completed_ranges.popleft()
                active_rth_date = bar_date
                current_rth_high = float(highs[i])
                current_rth_low = float(lows[i])
                has_active_rth_range = True
            else:
                current_rth_high = max(current_rth_high, float(highs[i]))
                current_rth_low = min(current_rth_low, float(lows[i]))

            if t1 == cfg.vwap_start_time_central:
                cum_pv = 0.0
                cum_vol = 0.0
            vol = max(0.0, float(volumes[i]))
            if vol > 0.0:
                typ = (float(highs[i]) + float(lows[i]) + float(closes[i])) / 3.0
                cum_pv += typ * vol
                cum_vol += vol
            session_vwap = (cum_pv / cum_vol) if cum_vol > 0.0 else float(closes[i])

        vwap_hist_idx = _push_history(vwap_hist, vwap_hist_idx, session_vwap)

        if t2 >= cfg.vwap_end_time_central:
            if in_pos and pending_exit_reason is None:
                pending_exit_reason = "EOD"
            signal_side = 0
            continue

        if not in_vwap_win or cum_vol <= 0.0:
            continue

        c_i = float(closes[i])
        above = c_i > session_vwap
        below = c_i < session_vwap

        if (not in_pos) and t2 == cfg.initial_entry_boundary_central:
            if above:
                signal_side = 1
                if (not pending_entry) and _passes_vwap_filters(
                    i=i,
                    boundary=t2,
                    tick_size=ms.tick_size,
                    closes=closes,
                    chart_times=chart_times,
                    session_vwap=session_vwap,
                    vwap_hist=vwap_hist,
                    vwap_hist_idx=vwap_hist_idx,
                    last_long_exit_bar=last_long_exit_bar,
                    completed_ranges=completed_ranges,
                    completed_range_sum=completed_range_sum,
                    prior_rth_range=prior_rth_range,
                    cfg=cfg,
                ):
                    pending_entry = True
            elif below:
                signal_side = 2
            continue

        if signal_side == 1 and below:
            signal_side = 2
            if in_pos and pending_exit_reason is None and cfg.exit_on_vwap_cross:
                pending_exit_reason = "VWAP"
                last_long_exit_bar = i
            continue

        if signal_side == 2 and above:
            signal_side = 1
            if cfg.allow_reentries and (not in_pos) and (not pending_entry):
                if _passes_vwap_filters(
                    i=i,
                    boundary=t2,
                    tick_size=ms.tick_size,
                    closes=closes,
                    chart_times=chart_times,
                    session_vwap=session_vwap,
                    vwap_hist=vwap_hist,
                    vwap_hist_idx=vwap_hist_idx,
                    last_long_exit_bar=last_long_exit_bar,
                    completed_ranges=completed_ranges,
                    completed_range_sum=completed_range_sum,
                    prior_rth_range=prior_rth_range,
                    cfg=cfg,
                ):
                    pending_entry = True

    return contracts.trades_to_df(trades)


# ---------------------------------------------------------------------------
# Modulo N: NDayLong (ms.bip1 1m ETH + ms.bip8 1d ETH, Central Time)
# ---------------------------------------------------------------------------


def _nday_average_range(
    d_cur: int,
    start_bars_ago: int,
    length: int,
    d_highs: np.ndarray,
    d_lows: np.ndarray,
) -> float:
    total = 0.0
    for k in range(start_bars_ago, start_bars_ago + length):
        idx = d_cur - k
        total += float(d_highs[idx]) - float(d_lows[idx])
    return total / float(length)


def _nday_positive_efficiency(
    d_cur: int,
    d_closes: np.ndarray,
    cfg: NDayConfig,
) -> bool:
    lb = cfg.efficiency_lookback_days
    path = 0.0
    for k in range(1, lb + 1):
        path += abs(float(d_closes[d_cur - k]) - float(d_closes[d_cur - (k + 1)]))
    if not (path > 0.0):
        return False
    net = float(d_closes[d_cur - 1]) - float(d_closes[d_cur - (lb + 1)])
    if not (net > 0.0):
        return False
    return (net / path) >= cfg.minimum_daily_efficiency


def _nday_choppy_regime(
    d_cur: int,
    d_highs: np.ndarray,
    d_lows: np.ndarray,
    d_closes: np.ndarray,
    cfg: NDayConfig,
) -> bool:
    short_avg = _nday_average_range(d_cur, 1, cfg.regime_short_range_length, d_highs, d_lows)
    long_avg = _nday_average_range(d_cur, 1, cfg.regime_long_range_length, d_highs, d_lows)
    if not (long_avg > 0.0):
        return False
    long_len = cfg.regime_long_range_length
    path = 0.0
    for k in range(1, long_len + 1):
        path += abs(float(d_closes[d_cur - k]) - float(d_closes[d_cur - (k + 1)]))
    if not (path > 0.0):
        return False
    eff = abs(float(d_closes[d_cur - 1]) - float(d_closes[d_cur - (long_len + 1)])) / path
    return (short_avg / long_avg >= cfg.minimum_volatility_expansion_ratio) and (
        eff <= cfg.maximum_regime_efficiency
    )


def _try_nday_quantity(prior_range: float, cfg: NDayConfig) -> Tuple[bool, int]:
    quantity = 1
    if not (prior_range > 0.0):
        return False, quantity
    est_loss_usd = prior_range * cfg.maximum_loss_prior_range_fraction * 20.0
    if cfg.use_dollar_risk_gate and est_loss_usd > cfg.maximum_estimated_loss_usd:
        return False, quantity
    if cfg.use_volatility_position_sizing:
        sized = int(math.floor(cfg.target_risk_usd / est_loss_usd))
        quantity = min(sized, cfg.maximum_contracts)
        if quantity < 1:
            return False, quantity
    return True, quantity


def _is_daily_futures_close_blocked(
    hhmmss_ct: int,
    dow_ct: int,
    cfg: NDayConfig,
) -> bool:
    """Replica `IsDailyFuturesCloseBlocked` (dow_ct: 0=Lun..4=Vie, 5=Sab, 6=Dom)."""
    if not cfg.flatten_before_daily_futures_close:
        return False
    if dow_ct == 5:  # Saturday
        return True
    if dow_ct == 4:  # Friday
        return hhmmss_ct >= cfg.daily_futures_flatten_time_central
    if dow_ct == 6:  # Sunday
        return hhmmss_ct < cfg.daily_futures_resume_time_central
    return (
        hhmmss_ct >= cfg.daily_futures_flatten_time_central
        and hhmmss_ct < cfg.daily_futures_resume_time_central
    )


def run_n(
    ms: contracts.MultiSeriesContext,
    qty: int = 1,
    cfg: Optional[NDayConfig] = None,
) -> pd.DataFrame:
    """Ejecuta el modulo N (`NDayLong`) sobre `ms.bip1` (1m ETH) y `ms.bip8` (1d ETH)."""
    cfg = NDayConfig() if cfg is None else cfg
    if not cfg.enable or qty <= 0:
        return contracts.trades_to_df([])

    b1 = ms.bip1
    b8 = ms.bip8
    n = len(b1.close)
    n_daily = len(b8.close)
    if n < 2 or n_daily == 0:
        return contracts.trades_to_df([])

    required_daily = cfg.num_days
    if cfg.use_daily_efficiency_filter:
        required_daily = max(required_daily, cfg.efficiency_lookback_days + 1)
    if cfg.use_choppy_high_volatility_filter:
        required_daily = max(
            required_daily,
            max(cfg.regime_long_range_length, cfg.regime_short_range_length) + 1,
        )

    ts_ns = b1.ts_ns
    opens = b1.open
    highs = b1.high
    lows = b1.low
    closes = b1.close
    volumes = b1.volume
    chart_times = b1.hhmmss_ct
    dow_ct = b1.dow_ct
    boundaries = _compute_chicago_next_minute_hhmmss(ts_ns)

    d_highs = b8.high
    d_lows = b8.low
    d_closes = b8.close
    d_m1_end = b8.m1_end_idx

    vwap_hist_len = max(241, cfg.vwap_slope_lookback_minutes + 2)
    rth_vwap_hist = np.zeros(vwap_hist_len, dtype=np.float64)
    rth_vwap_hist_idx = 0
    cum_pv = 0.0
    cum_vol = 0.0

    acceptance_closes = 0
    was_long = False
    closes_below_breakout = 0
    last_submitted_breakout_level = 0.0

    # Estado de ejecucion
    in_pos = False
    pos_qty = 0
    entry_idx = -1
    entry_price = 0.0
    entry_name = "N_E_L"
    pending_market_entry_qty = 0
    working_stop_entry_price: Optional[float] = None
    working_stop_entry_qty = 0
    pending_exit_reason: Optional[str] = None
    trades: List[contracts.TradeRecord] = []

    d_cur = 0
    for i in range(n):
        while d_cur < n_daily and i > int(d_m1_end[d_cur]):
            d_cur += 1

        # Procesar fills al inicio de la barra i
        if pending_exit_reason is not None and in_pos:
            trades.append(
                _make_trade_record(
                    module="N",
                    side=1,
                    qty=pos_qty,
                    entry_idx=entry_idx,
                    exit_idx=i,
                    entry_price=entry_price,
                    exit_price=float(opens[i]),
                    stop_price=math.nan,
                    target_price=math.nan,
                    entry_name=entry_name,
                    exit_name=pending_exit_reason,
                    ts_ns=ts_ns,
                    highs=highs,
                    lows=lows,
                    point_value=ms.point_value,
                    exit_at_open=True,
                )
            )
            in_pos = False
            pos_qty = 0
            pending_exit_reason = None
        elif pending_market_entry_qty > 0 and not in_pos:
            in_pos = True
            pos_qty = pending_market_entry_qty
            entry_idx = i
            entry_price = float(opens[i])
            entry_name = "N_E_L"
            pending_market_entry_qty = 0
        elif working_stop_entry_price is not None and not in_pos:
            if float(highs[i]) >= working_stop_entry_price:
                in_pos = True
                pos_qty = working_stop_entry_qty
                entry_idx = i
                entry_price = max(float(opens[i]), working_stop_entry_price)
                entry_name = "N_E_L_STOP"
                working_stop_entry_price = None
                working_stop_entry_qty = 0

        if d_cur < required_daily or (d_cur - required_daily) < 0:
            continue

        chart_time = int(chart_times[i])

        # Portfolio-level daily futures maintenance close (opcional; default False en standalone)
        maint_blocked = _is_daily_futures_close_blocked(chart_time, int(dow_ct[i]), cfg)
        if maint_blocked:
            working_stop_entry_price = None
            working_stop_entry_qty = 0
            pending_market_entry_qty = 0
            if in_pos and pending_exit_reason is None:
                pending_exit_reason = "DAILY_FUTURES_CLOSE"

        # UpdateNDayVwap
        if chart_time == 83000:
            cum_pv = 0.0
            cum_vol = 0.0
        if 83000 <= chart_time < 160000:
            typ = (float(highs[i]) + float(lows[i]) + float(closes[i])) / 3.0
            vol = float(volumes[i])
            cum_pv += typ * vol
            cum_vol += vol
            v_val = (cum_pv / cum_vol) if cum_vol > 0.0 else float(closes[i])
            rth_vwap_hist_idx = _push_history(rth_vwap_hist, rth_vwap_hist_idx, v_val)
        else:
            v_val = (
                float(closes[i])
                if rth_vwap_hist_idx <= 0
                else _history_value(rth_vwap_hist, rth_vwap_hist_idx, 0)
            )
            rth_vwap_hist_idx = _push_history(rth_vwap_hist, rth_vwap_hist_idx, v_val)

        # Flatten at N_FlattenTime
        if int(boundaries[i]) >= cfg.flatten_time:
            working_stop_entry_price = None
            working_stop_entry_qty = 0
            pending_market_entry_qty = 0
            if in_pos and pending_exit_reason is None:
                pending_exit_reason = "EOD"
            continue

        prior_range = float(d_highs[d_cur - 1]) - float(d_lows[d_cur - 1])

        if in_pos:
            if cfg.use_volatility_scaled_loss_exit and prior_range > 0.0:
                if not (
                    float(closes[i])
                    > entry_price - cfg.maximum_loss_prior_range_fraction * prior_range
                ):
                    if pending_exit_reason is None:
                        pending_exit_reason = "VOLLOSS"
                    continue

            if not was_long:
                was_long = True
                closes_below_breakout = 0
            if cfg.use_failed_breakout_exit:
                if float(closes[i]) < last_submitted_breakout_level - cfg.failure_buffer_points:
                    closes_below_breakout += 1
                else:
                    closes_below_breakout = 0
                if closes_below_breakout >= cfg.failure_confirmation_bars:
                    if pending_exit_reason is None:
                        pending_exit_reason = "FAILED"
            continue

        # Flat
        was_long = False
        closes_below_breakout = 0

        if working_stop_entry_price is not None:
            if chart_time >= cfg.last_entry_time:
                working_stop_entry_price = None
                working_stop_entry_qty = 0
            continue

        if maint_blocked or pending_market_entry_qty > 0 or chart_time >= cfg.last_entry_time:
            continue

        day_hi = float(d_highs[d_cur - 1])
        for k in range(2, cfg.num_days + 1):
            day_hi = max(day_hi, float(d_highs[d_cur - k]))

        # PassesNDayFilters
        if cfg.use_daily_efficiency_filter and not _nday_positive_efficiency(d_cur, d_closes, cfg):
            continue
        if cfg.use_choppy_high_volatility_filter and _nday_choppy_regime(
            d_cur, d_highs, d_lows, d_closes, cfg
        ):
            continue
        if cfg.use_rth_vwap_acceptance_filter:
            if not (83000 <= chart_time < 160000):
                continue
            if i < cfg.vwap_slope_lookback_minutes:
                continue
            vwap_now = _history_value(rth_vwap_hist, rth_vwap_hist_idx, 0)
            vwap_prev = _history_value(
                rth_vwap_hist, rth_vwap_hist_idx, cfg.vwap_slope_lookback_minutes
            )
            if not (float(closes[i]) > vwap_now and vwap_now > vwap_prev):
                continue
        if cfg.use_breakout_acceptance_filter:
            if float(closes[i]) > day_hi + cfg.acceptance_buffer_points:
                acceptance_closes += 1
            else:
                acceptance_closes = 0
            if acceptance_closes < cfg.acceptance_confirmation_bars:
                continue
        else:
            acceptance_closes = 0

        ok_qty, calc_qty = _try_nday_quantity(prior_range, cfg)
        if not ok_qty:
            continue
        final_qty = max(0, calc_qty * qty)
        if final_qty < 1:
            continue

        last_submitted_breakout_level = day_hi
        if day_hi <= float(closes[i]):
            if cfg.treat_marketable_stop_as_market:
                pending_market_entry_qty = final_qty
        else:
            working_stop_entry_price = contracts.round_tick(day_hi, ms.tick_size)
            working_stop_entry_qty = final_qty

    return contracts.trades_to_df(trades)


# ---------------------------------------------------------------------------
# Modulo T: FtmOrb / FtmEngine (ms.bip1 1m ETH, Eastern Time)
# ---------------------------------------------------------------------------


@dataclass
class _DirectionTrainingRow:
    session_key: int
    features: np.ndarray
    flip_wins: bool
    sequence: int


@dataclass
class _QuarterDirectionModel:
    train_x_std: np.ndarray
    train_flip: np.ndarray
    train_seq: np.ndarray
    means: np.ndarray
    scales: np.ndarray
    row_count: int


@dataclass
class _ShadowTradeState:
    side: int
    entry: float
    active_stop: float
    target: float
    risk_points: float
    managed_trigger_r: float
    managed_lock_r: float
    complete: bool = False
    pending_conditional_exit: bool = False
    exit_price: float = 0.0


@dataclass
class _ShadowPairState:
    session_key: int
    expected_parent_fill_open_utc_ns: int
    baseline_side: int
    features: np.ndarray
    prior_trend_available: bool
    prior_trend_bps: float
    initialized: bool = False
    invalid: bool = False
    label_recorded: bool = False
    breakout: Optional[_ShadowTradeState] = None
    fade: Optional[_ShadowTradeState] = None


@dataclass
class _PendingEntryDecision:
    expected_obs_open_utc_ns: int
    direction_side: int
    required_obs_bars: int
    submit_actual_order: bool
    branch: str
    direction_source: str
    baseline_side: int
    features: np.ndarray
    signal_close: float
    observed_bars: int = 0
    first_obs_open: float = 0.0


@dataclass
class _PendingFinalEntryDecision:
    expected_obs_open_utc_ns: int
    refined_side: int
    required_obs_bars: int
    submit_actual_order: bool
    branch: str
    direction_source: str
    refinement_path: str
    observed_bars: int = 0
    first_obs_open: float = 0.0


def _ftm_safe_return_bps(numerator: float, denominator: float) -> float:
    if denominator == 0.0:
        return 0.0
    return (numerator / denominator - 1.0) * 10000.0


def _ftm_lag_return_bps(values: List[float], periods: int) -> float:
    if len(values) <= periods:
        return 0.0
    denom = values[len(values) - 1 - periods]
    if denom == 0.0:
        return 0.0
    return _ftm_safe_return_bps(values[-1], denom)


def _ftm_linear_percentile(values: List[float], quantile: float) -> float:
    arr = np.sort(np.asarray(values, dtype=np.float64))
    pos = float(len(arr) - 1) * quantile
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(arr[lo])
    frac = pos - float(lo)
    return float(arr[lo] + (arr[hi] - arr[lo]) * frac)


def _ftm_round_price_offset_ticks(
    points: float, price_below_entry: bool, tick_size: float
) -> int:
    ticks = points / tick_size
    if price_below_entry:
        return int(math.ceil(ticks - 0.5))
    return int(math.floor(ticks + 0.5))


def _ftm_quarter_key_and_cutoff(session_key: int) -> Tuple[int, int]:
    y = session_key // 10000
    m = (session_key // 100) % 100
    q = (m - 1) // 3 + 1
    q_key = y * 10 + q
    q_start_month = (q - 1) * 3 + 1
    cutoff = dt.date(y, q_start_month, 1) - dt.timedelta(days=1)
    return q_key, _date_to_key(cutoff)


def _ftm_select_management_plan(
    side: int,
    prior_trend_available: bool,
    prior_trend_bps: float,
    prior_orb_q75_available: bool,
    current_orb_bps: float,
    prior_orb_q75_bps: float,
    cfg: FtmConfig,
) -> Tuple[float, float, float, str]:
    high_orb = prior_orb_q75_available and (current_orb_bps > prior_orb_q75_bps)
    countertrend = prior_trend_available and ((float(side) * prior_trend_bps) < 0.0)
    if high_orb:
        return (
            cfg.high_orb_target_r,
            cfg.high_orb_trigger_r,
            cfg.high_orb_lock_r,
            "high_orb_short_target",
        )
    if countertrend:
        return (
            cfg.countertrend_target_r,
            cfg.countertrend_trigger_r,
            cfg.countertrend_lock_r,
            "countertrend_early_guard",
        )
    return (
        cfg.baseline_target_r,
        cfg.baseline_trigger_r,
        cfg.baseline_lock_r,
        "baseline",
    )


def _ftm_fit_quarter_model(
    rows: List[_DirectionTrainingRow],
    cutoff_key: int,
    cfg: FtmConfig,
) -> Optional[_QuarterDirectionModel]:
    elig = [r for r in rows if cfg.shadow_min_session_date <= r.session_key <= cutoff_key]   # = 20100101 de fábrica (2026-11-17: parámetro, no literal)
    min_rows = max(cfg.knn_min_training_rows, cfg.knn_k)
    if len(elig) < min_rows:
        return None
    x = np.vstack([r.features for r in elig]).astype(np.float64)
    means = np.mean(x, axis=0)
    # `scaler=population-standard-deviation` (ddof=0) exacto del IL
    scales = np.sqrt(np.mean((x - means) ** 2, axis=0))
    scales = np.where(scales > 0.0, scales, 1.0)
    x_std = (x - means) / scales
    flips = np.array([r.flip_wins for r in elig], dtype=bool)
    seqs = np.array([r.sequence for r in elig], dtype=np.int64)
    return _QuarterDirectionModel(
        train_x_std=x_std,
        train_flip=flips,
        train_seq=seqs,
        means=means,
        scales=scales,
        row_count=len(elig),
    )


def _ftm_predict_knn(
    model: Optional[_QuarterDirectionModel],
    features: np.ndarray,
    cfg: FtmConfig,
) -> Tuple[bool, float, int, int]:
    if model is None:
        return False, 0.0, 0, 0
    fz = (features - model.means) / model.scales
    diff = model.train_x_std - fz
    dists = np.sqrt(np.sum(diff * diff, axis=1))
    order = np.lexsort((model.train_seq, dists))
    top_k = order[: cfg.knn_k]
    flip_neighbors = int(model.train_flip[top_k].sum())
    denom = float(cfg.knn_k) + 2.0 * cfg.knn_laplace_alpha
    flip_prob = (float(flip_neighbors) + cfg.knn_laplace_alpha) / denom
    return True, flip_prob, flip_neighbors, model.row_count


def _ftm_precompute_et_utc(
    ts_ns: np.ndarray, date_ct: np.ndarray, is_new_session: np.ndarray
) -> Tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    Dict[int, bool],
    np.ndarray,
]:
    open_ns = ts_ns - _NS_PER_MIN
    idx_close_et = pd.DatetimeIndex(pd.to_datetime(ts_ns, unit="ns", utc=True)).tz_convert(_TZ_ET)
    idx_open_et = pd.DatetimeIndex(pd.to_datetime(open_ns, unit="ns", utc=True)).tz_convert(_TZ_ET)
    idx_open_utc = pd.DatetimeIndex(pd.to_datetime(open_ns, unit="ns", utc=True))

    open_date_et = (
        idx_open_et.year * 10000 + idx_open_et.month * 100 + idx_open_et.day
    ).to_numpy(dtype=np.int32)
    close_date_et = (
        idx_close_et.year * 10000 + idx_close_et.month * 100 + idx_close_et.day
    ).to_numpy(dtype=np.int32)
    open_min_et = (idx_open_et.hour * 60 + idx_open_et.minute).to_numpy(dtype=np.int32)
    close_min_et = (idx_close_et.hour * 60 + idx_close_et.minute).to_numpy(dtype=np.int32)
    open_date_utc = (
        idx_open_utc.year * 10000 + idx_open_utc.month * 100 + idx_open_utc.day
    ).to_numpy(dtype=np.int32)
    open_hhmm_utc = (idx_open_utc.hour * 100 + idx_open_utc.minute).to_numpy(dtype=np.int32)
    exact_minute = ((ts_ns % _NS_PER_MIN) == 0).astype(bool)

    n = len(ts_ns)
    ses_starts_mask = is_new_session.astype(bool) | np.r_[True, date_ct[1:] != date_ct[:-1]]
    ses_starts = np.flatnonzero(ses_starts_mask)
    ses_ends = np.r_[ses_starts[1:] - 1, n - 1]

    is_last_bar_of_session = np.zeros(n, dtype=bool)
    full_cash_window_by_date: Dict[int, bool] = {}

    for s_start, s_end in zip(ses_starts, ses_ends):
        if s_end < n - 1:
            is_last_bar_of_session[s_end] = True
        else:
            # Ultima sesion del dataset: considerada cerrada si llega al cierre cash/ETH
            if int(close_min_et[s_end]) >= 960:
                is_last_bar_of_session[s_end] = True

        cash_key = int(date_ct[s_start])
        d_cash = _date_key_to_date(cash_key)
        req_open_ns = (
            pd.Timestamp(
                year=d_cash.year,
                month=d_cash.month,
                day=d_cash.day,
                hour=9,
                minute=30,
                tz=_TZ_ET,
            )
            .tz_convert("UTC")
            .value
        )
        req_close_ns = (
            pd.Timestamp(
                year=d_cash.year,
                month=d_cash.month,
                day=d_cash.day,
                hour=16,
                minute=0,
                tz=_TZ_ET,
            )
            .tz_convert("UTC")
            .value
        )
        ses_begin_ns = int(open_ns[s_start])
        ses_end_ns = int(ts_ns[s_end])
        has_full = (ses_begin_ns <= req_open_ns) and (ses_end_ns >= req_close_ns)
        full_cash_window_by_date[cash_key] = full_cash_window_by_date.get(cash_key, False) or has_full

    return (
        open_ns,
        open_date_et,
        close_date_et,
        open_min_et,
        close_min_et,
        open_date_utc,
        open_hhmm_utc,
        exact_minute,
        full_cash_window_by_date,
        is_last_bar_of_session,
    )


def run_t(
    ms: contracts.MultiSeriesContext,
    qty: int = 3,
    cfg: Optional[FtmConfig] = None,
) -> pd.DataFrame:
    """Ejecuta el modulo T (`FtmOrb` / `FtmEngine`) sobre `ms.bip1` (1m ETH, Eastern Time)."""
    cfg = FtmConfig() if cfg is None else cfg
    if not cfg.enable or qty <= 0:
        return contracts.trades_to_df([])

    b1 = ms.bip1
    n = len(b1.close)
    if n <= 15:
        return contracts.trades_to_df([])

    ts_ns = b1.ts_ns
    opens = b1.open
    highs = b1.high
    lows = b1.low
    closes = b1.close
    volumes = b1.volume
    date_ct = b1.date_ct
    tick_size = ms.tick_size

    (
        open_ns,
        open_date_et,
        close_date_et,
        open_min_et,
        close_min_et,
        open_date_utc,
        open_hhmm_utc,
        exact_minute,
        full_cash_window_by_date,
        is_last_bar_of_session,
    ) = _ftm_precompute_et_utc(ts_ns, date_ct, b1.is_new_session)

    # Estado persistente inter-sesion de FtmEngine
    eligible_orb_history_bps: List[float] = []
    eligible_rth_close_history: List[float] = []
    eligible_session_return_history_bps: List[float] = []
    direction_training_rows: List[_DirectionTrainingRow] = []
    training_sequence = 0
    active_quarter_key = 0
    active_quarter_model: Optional[_QuarterDirectionModel] = None

    # Estado de sesion diaria
    current_cash_date: Optional[int] = None
    prev_day_of_cash: Optional[int] = None
    session_date_eligible = False
    reference_session_open_captured = False
    reference_session_open = 0.0
    day_blocked = True
    session_ending = False
    orb_finalized = False
    breakout_consumed = False
    cash_exit_triggered = False
    cash_window_integrity = False
    orb_history_recorded = False
    rth_close_history_recorded = False

    orb_bar_count = 0
    expected_next_orb_open_min = cfg.orb_start_minute_et
    orb_high = -math.inf
    orb_low = math.inf
    orb_open = 0.0
    orb_close = 0.0
    current_orb_bps = 0.0
    current_prior_orb_q75_bps = 0.0
    current_prior_orb_q75_available = False
    current_prior_trend_bps = 0.0
    current_prior_trend_available = False

    current_rth_minute_closes: List[float] = []
    current_rth_typ_vol_sum = 0.0
    current_rth_vol_sum = 0.0
    last_cash_bar_close_ns: Optional[int] = None

    # Estado de gestion de trade activo y refino
    active_initial_stop_ticks = 0
    active_managed_stop_trigger_r = 0.0
    active_managed_stop_lock_r = 0.0
    managed_stop_activated = False
    conditional_exit_requested = False

    active_shadow_pair: Optional[_ShadowPairState] = None
    pending_entry_decision: Optional[_PendingEntryDecision] = None
    pending_final_entry_decision: Optional[_PendingFinalEntryDecision] = None

    # Estado de ejecucion real del modulo T
    in_pos = False
    pos_side = 0
    entry_idx = -1
    entry_price = 0.0
    active_stop_price = math.nan
    active_target_price = math.nan
    active_entry_name = ""

    pending_submit: Optional[Tuple[int, int, float, float, str]] = None  # (side, stop_ticks, stop_dist, target_dist, entry_name)
    pending_exit_reason: Optional[str] = None
    trades: List[contracts.TradeRecord] = []

    def invalidate_pending() -> None:
        nonlocal active_shadow_pair, pending_entry_decision, pending_final_entry_decision
        pending_entry_decision = None
        pending_final_entry_decision = None
        active_shadow_pair = None

    def block_cash_date() -> None:
        nonlocal cash_window_integrity, day_blocked, breakout_consumed
        cash_window_integrity = False
        day_blocked = True
        breakout_consumed = True

    def request_admin_exit(reason: str) -> None:
        nonlocal pending_exit_reason
        if in_pos and pending_exit_reason is None:
            pending_exit_reason = reason

    def begin_cash_date(cash_key: int) -> None:
        nonlocal current_cash_date, prev_day_of_cash, session_date_eligible
        nonlocal reference_session_open_captured, reference_session_open
        nonlocal day_blocked, session_ending, orb_finalized, breakout_consumed
        nonlocal cash_exit_triggered, cash_window_integrity
        nonlocal orb_history_recorded, rth_close_history_recorded
        nonlocal active_initial_stop_ticks, managed_stop_activated, conditional_exit_requested
        nonlocal orb_bar_count, expected_next_orb_open_min, orb_high, orb_low, orb_open, orb_close
        nonlocal current_orb_bps, current_prior_orb_q75_bps, current_prior_orb_q75_available
        nonlocal current_prior_trend_bps, current_prior_trend_available
        nonlocal current_rth_typ_vol_sum, current_rth_vol_sum, last_cash_bar_close_ns
        nonlocal active_managed_stop_trigger_r, active_managed_stop_lock_r

        has_exposure = in_pos or (pending_submit is not None)
        if (
            active_shadow_pair is not None
            or pending_entry_decision is not None
            or pending_final_entry_decision is not None
        ):
            invalidate_pending()

        current_cash_date = cash_key
        d_cash = _date_key_to_date(cash_key)
        prev_day_of_cash = _date_to_key(d_cash - dt.timedelta(days=1))

        session_date_eligible = True
        reference_session_open_captured = False
        reference_session_open = 0.0
        day_blocked = has_exposure
        session_ending = has_exposure
        orb_finalized = False
        breakout_consumed = has_exposure
        cash_exit_triggered = False
        cash_window_integrity = False
        orb_history_recorded = False
        rth_close_history_recorded = False

        active_initial_stop_ticks = 0
        managed_stop_activated = False
        conditional_exit_requested = False

        orb_bar_count = 0
        expected_next_orb_open_min = cfg.orb_start_minute_et
        orb_high = -math.inf
        orb_low = math.inf
        orb_open = 0.0
        orb_close = 0.0
        current_orb_bps = 0.0
        current_prior_orb_q75_bps = 0.0
        current_prior_orb_q75_available = False

        if len(eligible_rth_close_history) >= cfg.rth_close_history_window:
            oldest = eligible_rth_close_history[0]
            newest = eligible_rth_close_history[-1]
            if oldest > 0.0 and newest > 0.0:
                current_prior_trend_bps = _ftm_safe_return_bps(newest, oldest)
                current_prior_trend_available = True
            else:
                current_prior_trend_bps = 0.0
                current_prior_trend_available = False
        else:
            current_prior_trend_bps = 0.0
            current_prior_trend_available = False

        current_rth_minute_closes.clear()
        current_rth_typ_vol_sum = 0.0
        current_rth_vol_sum = 0.0
        last_cash_bar_close_ns = None
        active_managed_stop_trigger_r = 0.0
        active_managed_stop_lock_r = 0.0

        if has_exposure:
            request_admin_exit("OvernightExposureOrEntry")
            return

        if d_cash.weekday() >= 5:
            session_date_eligible = False
            day_blocked = True
            return

        if cfg.use_exclusion_calendars and (
            cash_key in FTM_DEGRADED_DATA_EXCLUSION_DATE_KEYS
            or cash_key in FTM_CONTRACT_ROLL_EXCLUSION_DATE_KEYS
        ):
            session_date_eligible = False
            day_blocked = True
            return

        if not full_cash_window_by_date.get(cash_key, False):
            session_date_eligible = False
            day_blocked = True
            return

        cash_window_integrity = True

    def try_record_completed_model_label() -> None:
        nonlocal active_shadow_pair, training_sequence
        sp = active_shadow_pair
        if sp is None or sp.invalid or sp.label_recorded or not sp.initialized:
            return
        if sp.breakout is None or sp.fade is None:
            return
        if not sp.breakout.complete or not sp.fade.complete:
            return

        breakout_net = (
            float(sp.breakout.side) * (sp.breakout.exit_price - sp.breakout.entry) * 20.0
            - cfg.shadow_round_turn_commission_usd
        )
        fade_net = (
            float(sp.fade.side) * (sp.fade.exit_price - sp.fade.entry) * 20.0
            - cfg.shadow_round_turn_commission_usd
        )
        flip_wins = fade_net > 0.0
        exclusive = (breakout_net > 0.0) != flip_wins
        if exclusive:
            direction_training_rows.append(
                _DirectionTrainingRow(
                    session_key=sp.session_key,
                    features=sp.features.copy(),
                    flip_wins=flip_wins,
                    sequence=training_sequence,
                )
            )
            training_sequence += 1

        sp.label_recorded = True
        active_shadow_pair = None

    def create_shadow_trade(
        side: int, parent_fill_open: float, prior_trend_avail: bool, prior_trend_bps: float
    ) -> _ShadowTradeState:
        entry_px = parent_fill_open + float(side) * float(cfg.shadow_slippage_ticks) * tick_size
        _esc = (0.5 * (orb_high + orb_low) / cfg.escala_precio_ref) if cfg.escala_precio_ref > 0.0 else 1.0
        raw_dist = max(cfg.stop_min_points * _esc, min(cfg.stop_max_points * _esc, (orb_high - orb_low) * cfg.stop_orb_multiplier))
        stop_px = contracts.round_tick(entry_px - float(side) * raw_dist, tick_size)
        risk_pts = float(side) * (entry_px - stop_px)
        t_r, trig_r, lock_r, _ = _ftm_select_management_plan(
            side=side,
            prior_trend_available=prior_trend_avail,
            prior_trend_bps=prior_trend_bps,
            prior_orb_q75_available=current_prior_orb_q75_available,
            current_orb_bps=current_orb_bps,
            prior_orb_q75_bps=current_prior_orb_q75_bps,
            cfg=cfg,
        )
        target_px = contracts.round_tick(entry_px + float(side) * raw_dist * t_r, tick_size)
        st = _ShadowTradeState(
            side=side,
            entry=entry_px,
            active_stop=stop_px,
            target=target_px,
            risk_points=risk_pts,
            managed_trigger_r=trig_r,
            managed_lock_r=lock_r,
        )
        if not (risk_pts > 0.0):
            st.complete = True
            st.exit_price = entry_px
        return st

    def process_shadow_trade_bar(st: _ShadowTradeState, idx: int, close_min: int) -> None:
        if st.complete:
            return
        slip = float(cfg.shadow_slippage_ticks) * tick_size
        op = float(opens[idx])
        hi = float(highs[idx])
        lo = float(lows[idx])
        cl = float(closes[idx])

        if st.pending_conditional_exit:
            st.exit_price = op - float(st.side) * slip
            st.complete = True
            st.pending_conditional_exit = False
            return

        if st.side == 1:
            stop_hit = lo <= st.active_stop
            target_hit = hi >= st.target
        else:
            stop_hit = hi >= st.active_stop
            target_hit = lo <= st.target

        if stop_hit:
            fill_stop = min(st.active_stop, op) if st.side == 1 else max(st.active_stop, op)
            st.exit_price = fill_stop - float(st.side) * slip
            st.complete = True
            st.pending_conditional_exit = False
            return

        if target_hit:
            fill_tgt = max(st.target, op) if st.side == 1 else min(st.target, op)
            st.exit_price = fill_tgt
            st.complete = True
            st.pending_conditional_exit = False
            return

        if close_min < cfg.cash_close_minute_et and (close_min % 15) == 0:
            close_r = float(st.side) * (cl - st.entry) / st.risk_points
            if close_r >= st.managed_trigger_r:
                new_stop = contracts.round_tick(
                    st.entry + float(st.side) * st.risk_points * st.managed_lock_r, tick_size
                )
                if st.side == 1:
                    st.active_stop = max(st.active_stop, new_stop)
                else:
                    st.active_stop = min(st.active_stop, new_stop)
            if close_min == cfg.conditional_exit_minute_et:
                if close_r < 0.0 or close_r >= 1.0:
                    st.pending_conditional_exit = True

    def submit_entry(side: int, direction_source: str, refinement_path: str) -> None:
        nonlocal active_initial_stop_ticks, active_managed_stop_trigger_r, active_managed_stop_lock_r
        nonlocal managed_stop_activated, conditional_exit_requested, pending_submit
        if in_pos or pending_submit is not None:
            return
        is_long = side == 1
        _esc = (0.5 * (orb_high + orb_low) / cfg.escala_precio_ref) if cfg.escala_precio_ref > 0.0 else 1.0
        raw_dist = max(cfg.stop_min_points * _esc, min(cfg.stop_max_points * _esc, (orb_high - orb_low) * cfg.stop_orb_multiplier))
        stop_ticks = _ftm_round_price_offset_ticks(raw_dist, is_long, tick_size)
        target_r, trig_r, lock_r, _ = _ftm_select_management_plan(
            side=side,
            prior_trend_available=current_prior_trend_available,
            prior_trend_bps=current_prior_trend_bps,
            prior_orb_q75_available=current_prior_orb_q75_available,
            current_orb_bps=current_orb_bps,
            prior_orb_q75_bps=current_prior_orb_q75_bps,
            cfg=cfg,
        )
        target_ticks = _ftm_round_price_offset_ticks(raw_dist * target_r, not is_long, tick_size)
        active_initial_stop_ticks = stop_ticks
        active_managed_stop_trigger_r = trig_r
        active_managed_stop_lock_r = lock_r
        managed_stop_activated = False
        conditional_exit_requested = False
        pending_submit = (
            side,
            stop_ticks,
            float(stop_ticks) * tick_size,
            float(target_ticks) * tick_size,
            f"T:{direction_source}:{refinement_path}",
        )

    def apply_final_entry_refinement_or_submit(
        refined_side: int,
        refinement_fill_open_utc_ns: int,
        direction_source: str,
        refinement_path: str,
        submit_actual: bool,
        baseline_side: int,
        features: np.ndarray,
        signal_close: float,
    ) -> None:
        nonlocal pending_final_entry_decision, day_blocked
        orb_range = orb_high - orb_low
        if not (orb_range > 0.0) or len(features) != 14:
            day_blocked = True
            return

        sign_flip = float(refined_side * baseline_side)
        aligned_prior = sign_flip * float(features[1])
        aligned_ret30 = sign_flip * float(features[5])
        orb_body = float(refined_side) * (orb_close - orb_open) / orb_range
        breakout_edge = orb_high if refined_side == 1 else orb_low
        signal_ext = float(refined_side) * (signal_close - breakout_edge) / orb_range

        prior_disagree = (aligned_prior > cfg.final_prior_disagreement_min_bps) and not (orb_body > 0.0)
        intraday_cont = (aligned_ret30 > cfg.final_intraday_min_ret30_bps) and not (
            signal_ext > cfg.final_intraday_max_extension
        )

        if prior_disagree:
            branch = "prior_session_disagreement"
            req_bars = cfg.final_prior_disagreement_bars
        elif intraday_cont:
            branch = "intraday_continuation"
            req_bars = cfg.final_intraday_bars
        else:
            if submit_actual:
                submit_entry(refined_side, direction_source, f"{refinement_path}->entry_condition_not_met")
            return

        pending_final_entry_decision = _PendingFinalEntryDecision(
            expected_obs_open_utc_ns=refinement_fill_open_utc_ns,
            refined_side=refined_side,
            required_obs_bars=req_bars,
            submit_actual_order=submit_actual,
            branch=branch,
            direction_source=direction_source,
            refinement_path=refinement_path,
        )

    def evaluate_admission_and_direction(idx: int, baseline_side: int) -> None:
        nonlocal breakout_consumed, day_blocked, active_quarter_key, active_quarter_model
        nonlocal active_shadow_pair, pending_entry_decision

        # TryGetExactSignalState over 15 1m bars ending at idx
        if idx < 14:
            breakout_consumed = True
            block_cash_date()
            invalidate_pending()
            return
        sig_open = float(opens[idx - 14])
        sig_high = -math.inf
        sig_low = math.inf
        c_ns = int(ts_ns[idx])
        for k in range(15):
            if int(ts_ns[idx - k]) != c_ns - k * _NS_PER_MIN:
                breakout_consumed = True
                block_cash_date()
                invalidate_pending()
                return
            sig_high = max(sig_high, float(highs[idx - k]))
            sig_low = min(sig_low, float(lows[idx - k]))
        if not (sig_high > sig_low):
            breakout_consumed = True
            block_cash_date()
            invalidate_pending()
            return
        sig_close = float(closes[idx])

        # Geometry filter
        sig_range = sig_high - sig_low
        body = float(baseline_side) * (sig_close - sig_open) / sig_range
        close_loc = (
            (sig_close - sig_low) / sig_range
            if baseline_side == 1
            else (sig_high - sig_close) / sig_range
        )
        if body < cfg.admission_min_body_ratio or close_loc < cfg.admission_min_close_location:
            return

        # Touch filter
        conf_level = (
            orb_high + float(cfg.breakout_buffer_ticks) * tick_size
            if baseline_side == 1
            else orb_low - float(cfg.breakout_buffer_ticks) * tick_size
        )
        admission_touches = 0
        for k in range(15):
            if baseline_side == 1:
                if float(highs[idx - k]) >= conf_level:
                    admission_touches += 1
            else:
                if float(lows[idx - k]) <= conf_level:
                    admission_touches += 1
        if admission_touches < cfg.admission_min_touches:
            breakout_consumed = True
            return

        # TryBuildDirectionFeatures (14 exact features)
        if not (orb_open > 0.0 and orb_close > 0.0 and current_rth_vol_sum > 0.0) or not current_rth_minute_closes:
            breakout_consumed = True
            block_cash_date()
            invalidate_pending()
            return

        prev_rth_close = eligible_rth_close_history[-1] if eligible_rth_close_history else orb_open
        prior_sess_bps = (
            eligible_session_return_history_bps[-1] if eligible_session_return_history_bps else 0.0
        )
        prior_ret5_bps = _ftm_lag_return_bps(eligible_rth_close_history, 5)
        prior_ret20_bps = _ftm_lag_return_bps(eligible_rth_close_history, 20)
        rth_vwap = current_rth_typ_vol_sum / current_rth_vol_sum
        if len(current_rth_minute_closes) <= 30:
            close_30m_ago = orb_close
        else:
            close_30m_ago = current_rth_minute_closes[len(current_rth_minute_closes) - 31]

        gap_bps = _ftm_safe_return_bps(orb_open, prev_rth_close)
        vwap_dist_bps = _ftm_safe_return_bps(sig_close, rth_vwap)
        ret_30m_bps = _ftm_safe_return_bps(sig_close, close_30m_ago)
        elapsed_15m = float(int(close_min_et[idx]) - cfg.orb_end_minute_et) / 15.0

        d_cash = _date_key_to_date(int(current_cash_date))
        wk_idx = d_cash.weekday()  # Mon=0 .. Fri=4, igual a (DayOfWeek + 6) % 7 en C#
        month = d_cash.month
        two_pi = 6.2831853071795862

        features = np.array(
            [
                float(baseline_side) * gap_bps,
                float(baseline_side) * prior_sess_bps,
                float(baseline_side) * prior_ret5_bps,
                float(baseline_side) * prior_ret20_bps,
                float(baseline_side) * vwap_dist_bps,
                float(baseline_side) * ret_30m_bps,
                float(baseline_side),
                elapsed_15m,
                current_orb_bps,
                float(admission_touches),
                math.sin(two_pi * float(wk_idx) / 5.0),
                math.cos(two_pi * float(wk_idx) / 5.0),
                math.sin(two_pi * float(month - 1) / 12.0),
                math.cos(two_pi * float(month - 1) / 12.0),
            ],
            dtype=np.float64,
        )
        if not np.all(np.isfinite(features)):
            breakout_consumed = True
            block_cash_date()
            invalidate_pending()
            return

        breakout_consumed = True

        # Prior-session override
        prior_override = (float(baseline_side) * prior_sess_bps) < cfg.prior_session_override_bps

        # Quarterly KNN prediction
        knn_override = False
        if int(current_cash_date) >= cfg.knn_min_session_date:
            q_key, cutoff_key = _ftm_quarter_key_and_cutoff(int(current_cash_date))
            if active_quarter_key != q_key:
                active_quarter_model = _ftm_fit_quarter_model(direction_training_rows, cutoff_key, cfg)
                active_quarter_key = q_key
            model_avail, flip_prob, _, _ = _ftm_predict_knn(active_quarter_model, features, cfg)
            knn_override = model_avail and (flip_prob > cfg.knn_flip_probability_threshold)

        direction_side = -baseline_side if (prior_override or knn_override) else baseline_side
        if prior_override and knn_override:
            direction_source = "prior_session_and_quarterly_knn"
        elif prior_override:
            direction_source = "prior_session"
        elif knn_override:
            direction_source = "quarterly_knn"
        else:
            direction_source = "breakout"

        # StartShadowPair (acumula labels desde shadow_min_session_date, incluso en warmup)
        if int(current_cash_date) >= cfg.shadow_min_session_date:
            if active_shadow_pair is not None:
                invalidate_pending()
                day_blocked = True
            else:
                active_shadow_pair = _ShadowPairState(
                    session_key=int(current_cash_date),
                    expected_parent_fill_open_utc_ns=c_ns,
                    baseline_side=baseline_side,
                    features=features.copy(),
                    prior_trend_available=current_prior_trend_available,
                    prior_trend_bps=current_prior_trend_bps,
                )

        if day_blocked:
            return

        context_ready = current_prior_orb_q75_available and current_prior_trend_available
        submit_actual = (int(current_cash_date) >= cfg.portfolio_start_cash_date) and context_ready

        # Direct route on first 15m signal near VWAP (usa baselineSide, sin overrides ni refino)
        aligned_vwap_bps = float(features[4])
        if (
            float(features[7]) == cfg.direct_first_signal_elapsed_15m
            and not (aligned_vwap_bps > cfg.direct_first_signal_max_vwap_bps)
        ):
            if submit_actual:
                submit_entry(baseline_side, "rc1_breakout_shadow", "direct_first_signal_near_vwap")
            return

        weak_signal = not (
            (float(direction_side) * (sig_close - sig_open) / sig_range)
            > cfg.weak_signal_max_body_ratio
        )
        high_vol = current_prior_orb_q75_available and (current_orb_bps > current_prior_orb_q75_bps)
        dir_conf_level = (
            orb_high + float(cfg.breakout_buffer_ticks) * tick_size
            if direction_side == 1
            else orb_low - float(cfg.breakout_buffer_ticks) * tick_size
        )
        direction_touches = 0
        for k in range(15):
            if direction_side == 1:
                if float(highs[idx - k]) >= dir_conf_level:
                    direction_touches += 1
            else:
                if float(lows[idx - k]) <= dir_conf_level:
                    direction_touches += 1
        high_vol_touch_vote = high_vol and not (direction_touches > cfg.high_vol_max_direction_touches)

        if weak_signal or high_vol_touch_vote:
            pending_entry_decision = _PendingEntryDecision(
                expected_obs_open_utc_ns=c_ns,
                direction_side=direction_side,
                required_obs_bars=cfg.weak_signal_delay_bars if weak_signal else cfg.high_vol_vote_bars,
                submit_actual_order=submit_actual,
                branch="weak_signal_delay_keep" if weak_signal else "high_vol_touch_vote",
                direction_source=direction_source,
                baseline_side=baseline_side,
                features=features.copy(),
                signal_close=sig_close,
            )
        else:
            apply_final_entry_refinement_or_submit(
                refined_side=direction_side,
                refinement_fill_open_utc_ns=c_ns,
                direction_source=direction_source,
                refinement_path="condition_not_met",
                submit_actual=submit_actual,
                baseline_side=baseline_side,
                features=features,
                signal_close=sig_close,
            )

    for i in range(n):
        # 1. Procesar fills pendientes e intrabar STOP/TARGET en barra i antes de FtmEngine.Run()
        if pending_exit_reason is not None and in_pos:
            trades.append(
                _make_trade_record(
                    module="T",
                    side=pos_side,
                    qty=qty,
                    entry_idx=entry_idx,
                    exit_idx=i,
                    entry_price=entry_price,
                    exit_price=float(opens[i]),
                    stop_price=active_stop_price,
                    target_price=active_target_price,
                    entry_name=active_entry_name,
                    exit_name=pending_exit_reason,
                    ts_ns=ts_ns,
                    highs=highs,
                    lows=lows,
                    point_value=ms.point_value,
                    exit_at_open=True,
                )
            )
            in_pos = False
            pos_side = 0
            pending_exit_reason = None
        else:
            if pending_submit is not None and not in_pos:
                s_side, _, s_dist, t_dist, e_name = pending_submit
                pending_submit = None
                in_pos = True
                pos_side = s_side
                entry_idx = i
                entry_price = float(opens[i])
                active_entry_name = e_name
                active_stop_price = contracts.round_tick(
                    entry_price - float(pos_side) * s_dist, tick_size
                )
                active_target_price = contracts.round_tick(
                    entry_price + float(pos_side) * t_dist, tick_size
                )

            if in_pos:
                op_i = float(opens[i])
                hi_i = float(highs[i])
                lo_i = float(lows[i])
                if pos_side == 1:
                    hit_stop = lo_i <= active_stop_price
                    hit_tgt = hi_i >= active_target_price
                else:
                    hit_stop = hi_i >= active_stop_price
                    hit_tgt = lo_i <= active_target_price

                if hit_stop:
                    exit_px = min(active_stop_price, op_i) if pos_side == 1 else max(active_stop_price, op_i)
                    trades.append(
                        _make_trade_record(
                            module="T",
                            side=pos_side,
                            qty=qty,
                            entry_idx=entry_idx,
                            exit_idx=i,
                            entry_price=entry_price,
                            exit_price=exit_px,
                            stop_price=active_stop_price,
                            target_price=active_target_price,
                            entry_name=active_entry_name,
                            exit_name="STOP",
                            ts_ns=ts_ns,
                            highs=highs,
                            lows=lows,
                            point_value=ms.point_value,
                            exit_at_open=False,
                        )
                    )
                    in_pos = False
                    pos_side = 0
                elif hit_tgt:
                    exit_px = max(active_target_price, op_i) if pos_side == 1 else min(active_target_price, op_i)
                    trades.append(
                        _make_trade_record(
                            module="T",
                            side=pos_side,
                            qty=qty,
                            entry_idx=entry_idx,
                            exit_idx=i,
                            entry_price=entry_price,
                            exit_price=exit_px,
                            stop_price=active_stop_price,
                            target_price=active_target_price,
                            entry_name=active_entry_name,
                            exit_name="TARGET",
                            ts_ns=ts_ns,
                            highs=highs,
                            lows=lows,
                            point_value=ms.point_value,
                            exit_at_open=False,
                        )
                    )
                    in_pos = False
                    pos_side = 0

        # 2. FtmEngine.Run()
        if i < 15:
            continue

        bar_open_ns = int(open_ns[i])
        bar_close_ns = int(ts_ns[i])
        cash_date_i = int(date_ct[i])

        if current_cash_date is None or cash_date_i != current_cash_date:
            begin_cash_date(cash_date_i)

        # CaptureReferenceSessionOpen (23:00 UTC del dia previo)
        if (
            session_date_eligible
            and not reference_session_open_captured
            and int(open_hhmm_utc[i]) == 2300
            and int(open_date_utc[i]) == prev_day_of_cash
        ):
            if not bool(exact_minute[i]):
                block_cash_date()
            else:
                op0 = float(opens[i])
                if not (op0 > 0.0 and math.isfinite(op0)):
                    block_cash_date()
                else:
                    reference_session_open = op0
                    reference_session_open_captured = True

        o_min_et = int(open_min_et[i])
        c_min_et = int(close_min_et[i])
        same_et_date = (
            int(open_date_et[i]) == current_cash_date
            and int(close_date_et[i]) == current_cash_date
        )
        in_cash_win = (
            same_et_date
            and o_min_et >= cfg.orb_start_minute_et
            and c_min_et <= cfg.cash_close_minute_et
        )

        if in_cash_win and not bool(exact_minute[i]):
            block_cash_date()
            invalidate_pending()
            session_ending = True
            request_admin_exit("CashTimeAlignment")
            continue

        if in_cash_win:
            if last_cash_bar_close_ns is not None and bar_open_ns != last_cash_bar_close_ns:
                block_cash_date()
                invalidate_pending()
                session_ending = True
                request_admin_exit("CashDataGap")
                continue
            last_cash_bar_close_ns = bar_close_ns
            if not day_blocked:
                vol_i = float(volumes[i])
                cl_i = float(closes[i])
                current_rth_minute_closes.append(cl_i)
                current_rth_typ_vol_sum += ((float(highs[i]) + float(lows[i]) + cl_i) / 3.0) * vol_i
                current_rth_vol_sum += vol_i

        # ProcessShadowPair
        if same_et_date and active_shadow_pair is not None:
            sp = active_shadow_pair
            if not sp.invalid and not sp.label_recorded:
                if not sp.initialized:
                    if bar_open_ns >= sp.expected_parent_fill_open_utc_ns:
                        if bar_open_ns != sp.expected_parent_fill_open_utc_ns:
                            sp.invalid = True
                        else:
                            op_i = float(opens[i])
                            sp.breakout = create_shadow_trade(
                                sp.baseline_side, op_i, sp.prior_trend_available, sp.prior_trend_bps
                            )
                            sp.fade = create_shadow_trade(
                                -sp.baseline_side, op_i, sp.prior_trend_available, sp.prior_trend_bps
                            )
                            sp.initialized = True
                if sp.initialized and not sp.invalid:
                    process_shadow_trade_bar(sp.breakout, i, c_min_et)
                    process_shadow_trade_bar(sp.fade, i, c_min_et)
                    try_record_completed_model_label()

        # ProcessPendingEntryDecision
        if same_et_date and pending_entry_decision is not None and not day_blocked:
            ped = pending_entry_decision
            if bar_open_ns >= ped.expected_obs_open_utc_ns:
                if bar_open_ns != ped.expected_obs_open_utc_ns or (bar_close_ns - bar_open_ns) != _NS_PER_MIN:
                    pending_entry_decision = None
                    day_blocked = True
                else:
                    if ped.observed_bars == 0:
                        ped.first_obs_open = float(opens[i])
                    ped.observed_bars += 1
                    ped.expected_obs_open_utc_ns = bar_close_ns
                    if ped.observed_bars >= ped.required_obs_bars:
                        r_side = ped.direction_side
                        r_path = ped.branch
                        if ped.branch == "high_vol_touch_vote":
                            mv = float(r_side) * (float(closes[i]) - ped.first_obs_open)
                            orb_r = orb_high - orb_low
                            orb_frac = (mv / orb_r) if orb_r > 0.0 else 0.0
                            if not (orb_frac > 0.0):
                                r_side = -r_side
                                r_path = "high_vol_vote_flip"
                            else:
                                r_path = "high_vol_vote_keep"
                        pending_entry_decision = None
                        apply_final_entry_refinement_or_submit(
                            refined_side=r_side,
                            refinement_fill_open_utc_ns=bar_close_ns,
                            direction_source=ped.direction_source,
                            refinement_path=r_path,
                            submit_actual=ped.submit_actual_order,
                            baseline_side=ped.baseline_side,
                            features=ped.features,
                            signal_close=ped.signal_close,
                        )

        # ProcessPendingFinalEntryDecision
        if same_et_date and pending_final_entry_decision is not None and not day_blocked:
            pfed = pending_final_entry_decision
            if bar_open_ns >= pfed.expected_obs_open_utc_ns:
                if bar_open_ns != pfed.expected_obs_open_utc_ns or (bar_close_ns - bar_open_ns) != _NS_PER_MIN:
                    pending_final_entry_decision = None
                    day_blocked = True
                else:
                    if pfed.observed_bars == 0:
                        pfed.first_obs_open = float(opens[i])
                    pfed.observed_bars += 1
                    pfed.expected_obs_open_utc_ns = bar_close_ns
                    if pfed.observed_bars >= pfed.required_obs_bars:
                        obs_mv = float(pfed.refined_side) * (float(closes[i]) - pfed.first_obs_open)
                        if pfed.branch == "prior_session_disagreement":
                            final_side = -pfed.refined_side
                            act_lbl = "prior_session_disagreement_reverse"
                        elif obs_mv > 0.0:
                            final_side = -pfed.refined_side
                            act_lbl = "intraday_continuation_reverse"
                        else:
                            final_side = pfed.refined_side
                            act_lbl = "intraday_continuation_keep"
                        d_src = f"{pfed.direction_source}+{pfed.branch}"
                        r_path = f"{pfed.refinement_path}->{act_lbl}"
                        sub_act = pfed.submit_actual_order
                        pending_final_entry_decision = None
                        if sub_act:
                            submit_entry(final_side, d_src, r_path)

        # CashClose1600ET
        if same_et_date and c_min_et >= cfg.cash_close_minute_et:
            cl_i = float(closes[i])
            if active_shadow_pair is not None:
                sp = active_shadow_pair
                if sp.invalid or not sp.initialized:
                    active_shadow_pair = None
                else:
                    if not sp.breakout.complete:
                        sp.breakout.exit_price = cl_i - float(sp.breakout.side) * float(cfg.shadow_slippage_ticks) * tick_size
                        sp.breakout.complete = True
                        sp.breakout.pending_conditional_exit = False
                    if not sp.fade.complete:
                        sp.fade.exit_price = cl_i - float(sp.fade.side) * float(cfg.shadow_slippage_ticks) * tick_size
                        sp.fade.complete = True
                        sp.fade.pending_conditional_exit = False
                    try_record_completed_model_label()

            if (
                not rth_close_history_recorded
                and session_date_eligible
                and cash_window_integrity
                and orb_finalized
                and reference_session_open_captured
            ):
                if not orb_history_recorded:
                    eligible_orb_history_bps.append(current_orb_bps)
                    while len(eligible_orb_history_bps) > cfg.orb_history_window:
                        eligible_orb_history_bps.pop(0)
                    orb_history_recorded = True
                if cl_i > 0.0 and math.isfinite(cl_i):
                    sess_ret_bps = _ftm_safe_return_bps(cl_i, reference_session_open)
                    eligible_rth_close_history.append(cl_i)
                    while len(eligible_rth_close_history) > cfg.rth_close_history_window:
                        eligible_rth_close_history.pop(0)
                    eligible_session_return_history_bps.append(sess_ret_bps)
                    while len(eligible_session_return_history_bps) > 1:
                        eligible_session_return_history_bps.pop(0)
                    rth_close_history_recorded = True

            cash_exit_triggered = True
            day_blocked = True
            request_admin_exit("CashClose1600ET")
            continue

        if bool(is_last_bar_of_session[i]):
            cash_window_integrity = False
            invalidate_pending()
            session_ending = True
            day_blocked = True
            request_admin_exit("NativeSessionEnd")
            continue

        if cash_exit_triggered:
            request_admin_exit("CashExitFollowup")
            continue

        is_quarter_hour = (
            in_cash_win
            and cfg.quarter_hour_start_minute_et <= c_min_et < cfg.cash_close_minute_et
            and (c_min_et % 15) == 0
        )

        if in_pos:
            if is_quarter_hour:
                if not managed_stop_activated and active_initial_stop_ticks >= 1 and entry_price > 0.0:
                    risk_pts = float(active_initial_stop_ticks) * tick_size
                    if risk_pts > 0.0:
                        close_r = float(pos_side) * (float(closes[i]) - entry_price) / risk_pts
                        if close_r >= active_managed_stop_trigger_r:
                            active_stop_price = contracts.round_tick(
                                entry_price + float(pos_side) * risk_pts * active_managed_stop_lock_r,
                                tick_size,
                            )
                            managed_stop_activated = True
            if in_cash_win and c_min_et == cfg.conditional_exit_minute_et:
                if not conditional_exit_requested and active_initial_stop_ticks >= 1 and entry_price > 0.0:
                    risk_pts = float(active_initial_stop_ticks) * tick_size
                    if risk_pts > 0.0:
                        close_r = float(pos_side) * (float(closes[i]) - entry_price) / risk_pts
                        if close_r < 0.0 or close_r >= 1.0:
                            conditional_exit_requested = True
                            request_admin_exit("Conditional1530ET")
            continue

        # Flat: verificar ORB y breakouts
        d_cash = _date_key_to_date(int(current_cash_date))
        if day_blocked or d_cash.weekday() >= 5:
            continue

        # CaptureOpeningRange (09:30-09:45 ET)
        if not orb_finalized:
            if (
                int(open_date_et[i]) == current_cash_date
                and int(close_date_et[i]) == current_cash_date
                and cfg.orb_start_minute_et <= o_min_et < cfg.orb_end_minute_et
            ):
                if o_min_et != expected_next_orb_open_min or c_min_et != o_min_et + 1:
                    block_cash_date()
                    continue
                if orb_bar_count == 0:
                    orb_open = float(opens[i])
                orb_high = float(highs[i]) if orb_bar_count == 0 else max(orb_high, float(highs[i]))
                orb_low = float(lows[i]) if orb_bar_count == 0 else min(orb_low, float(lows[i]))
                orb_close = float(closes[i])
                orb_bar_count += 1
                expected_next_orb_open_min += 1
                if c_min_et == cfg.orb_end_minute_et:
                    if orb_bar_count != cfg.orb_bars or not (orb_high >= orb_low):
                        block_cash_date()
                        continue
                    orb_finalized = True
                    mid = (orb_high + orb_low) / 2.0
                    current_orb_bps = ((orb_high - orb_low) / mid) * 10000.0 if mid > 0.0 else 0.0
                    current_prior_orb_q75_available = (
                        len(eligible_orb_history_bps) == cfg.orb_history_window
                    )
                    if current_prior_orb_q75_available:
                        current_prior_orb_q75_bps = _ftm_linear_percentile(
                            eligible_orb_history_bps, cfg.orb_high_vol_quantile
                        )
            elif (
                int(open_date_et[i]) == current_cash_date
                and int(close_date_et[i]) == current_cash_date
                and c_min_et > cfg.orb_end_minute_et
            ):
                block_cash_date()
                continue

        if day_blocked or not orb_finalized or breakout_consumed or not is_quarter_hour:
            continue

        cl_i = float(closes[i])
        buf = float(cfg.breakout_buffer_ticks) * tick_size
        long_break = cl_i >= contracts.round_tick(orb_high + buf, tick_size)
        short_break = cl_i <= contracts.round_tick(orb_low - buf, tick_size)
        if not long_break and not short_break:
            continue

        baseline_side = 1 if long_break else -1
        evaluate_admission_and_direction(i, baseline_side)

    return contracts.trades_to_df(trades)


# ---------------------------------------------------------------------------
# Wrappers `senales_*`
# ---------------------------------------------------------------------------


def senales_w(
    ms: contracts.MultiSeriesContext,
    qty: int = 1,
    cfg: Optional[VwapCrossConfig] = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Wrapper de alto nivel para el modulo W (`VwapCross`)."""
    return run_w(ms, qty=qty, cfg=_build_cfg(VwapCrossConfig, cfg, kwargs))


def senales_n(
    ms: contracts.MultiSeriesContext,
    qty: int = 1,
    cfg: Optional[NDayConfig] = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Wrapper de alto nivel para el modulo N (`NDayLong`)."""
    return run_n(ms, qty=qty, cfg=_build_cfg(NDayConfig, cfg, kwargs))


def senales_t(
    ms: contracts.MultiSeriesContext,
    qty: int = 3,
    cfg: Optional[FtmConfig] = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Wrapper de alto nivel para el modulo T (`FtmOrb` / `FtmEngine`)."""
    return run_t(ms, qty=qty, cfg=_build_cfg(FtmConfig, cfg, kwargs))


__all__ = [
    "FTM_MODEL_FEATURE_NAMES",
    "FTM_CONTRACT_ROLL_EXCLUSION_DATE_KEYS",
    "FTM_DEGRADED_DATA_EXCLUSION_DATE_KEYS",
    "VwapCrossConfig",
    "NDayConfig",
    "FtmConfig",
    "run_w",
    "run_n",
    "run_t",
    "senales_w",
    "senales_n",
    "senales_t",
]
