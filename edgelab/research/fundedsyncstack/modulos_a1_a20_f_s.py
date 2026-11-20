"""Traduccion fiel del Lote 1 (modulos A1, A20, F, S) de FUNDEDSYNCSTACK5.dll.

Submodulos incluidos:
- A1  (`RunAbsorb1m` / `RunAbsorb`, BIP 1 = 1m ETH)
- A20 (`RunAbsorb20m` / `RunAbsorb`, BIP 4 = 20m ETH)
- F   (`RunFabio`, BIP 3 = 5m ETH)
- S   (`RunSwas`, BIP 2 = 3m ETH)

Reglas reproducidas segun el IL desensamblado de `FUNDEDSYNCSTACK5.dll` y los
indicadores nativos de NinjaTrader 8 (`@ATR.cs`, `@EMA.cs`, `@ADX.cs`, `@SMA.cs`).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from .contracts import (
        TRADE_COLUMNS,
        BarSeries,
        MultiSeriesContext,
        TradeRecord,
        round_tick,
        trades_to_df,
    )
except ImportError:
    from contracts import (
        TRADE_COLUMNS,
        BarSeries,
        MultiSeriesContext,
        TradeRecord,
        round_tick,
        trades_to_df,
    )

_POS_LONG = 0
_POS_SHORT = 1
_POS_FLAT = 2

_ROLLOVER_MONTHS = (3, 6, 9, 12)
_THIRD_FRIDAY_CACHE: Dict[Tuple[int, int], date] = {}


# ---------------------------------------------------------------------------
# Dataclasses de configuracion (defaults exactos de OnStateChange / IL)
# ---------------------------------------------------------------------------


@dataclass
class _AbsorbBaseConfig:
    """Parametros compartidos de Absorb (`Ab_*`) y especificos por instancia."""

    exit_on_st_flip: bool = True   # EdgeLab 2026-11-16 (PREREGISTRO_TANDA2 L1): False = sin salida por giro de SuperTrend (variante)
    vp_length: int = 10
    vp_resolution: int = 24
    absorb_vol_mult: float = 2.5
    absorb_price_thresh: float = 1.9
    delta_lookback: int = 5
    use_vwap: bool = True
    vwap_band: float = 0.5
    max_daily_losses: int = 3
    orb_minutes: int = 30
    use_orb: bool = True
    use_rollover_filter: bool = True
    rollover_days_before: int = 10
    rollover_days_after: int = 1
    use_volatility_filter: bool = True
    vol_baseline_lookback: int = 100
    vol_regime_multiplier: float = 2.9
    use_hard_stop: bool = True
    hard_stop_atr_mult: float = 1.5
    flatten_at_session_end: bool = True
    session_start_hour: int = 5
    session_start_minute: int = 30
    session_end_hour: int = 15
    session_end_minute: int = 0
    require_supertrend_entry_alignment: bool = False
    atr_period: int = 14
    st_period: int = 4
    st_mult: float = 2.7
    allow_longs: bool = True
    allow_shorts: bool = True
    use_early_entry_block: bool = False
    block_start_hour: int = 5
    block_start_minute: int = 30
    block_end_hour: int = 6
    block_end_minute: int = 0
    block_monday_entries: bool = False
    loss_cooldown_bars: int = 0
    bars_required_to_trade: int = 60
    virtual_round_turn_commission: float = 4.36
    timezone: str = "ct"
    flatten_before_daily_futures_close: bool = True
    daily_futures_flatten_time_central: int = 154400
    daily_futures_resume_time_central: int = 170100


@dataclass
class Absorb1mConfig(_AbsorbBaseConfig):
    """Configuracion exacta de A1 (`RunAbsorb1m`, BIP 1 = 1m ETH)."""

    st_period: int = 4
    st_mult: float = 2.7
    allow_longs: bool = True
    allow_shorts: bool = True
    use_early_entry_block: bool = True
    block_start_hour: int = 5
    block_start_minute: int = 30
    block_end_hour: int = 6
    block_end_minute: int = 0
    block_monday_entries: bool = False
    loss_cooldown_bars: int = 14


@dataclass
class Absorb20mConfig(_AbsorbBaseConfig):
    """Configuracion exacta de A20 (`RunAbsorb20m`, BIP 4 = 20m ETH)."""

    st_period: int = 7
    st_mult: float = 2.0
    allow_longs: bool = False
    allow_shorts: bool = True
    use_early_entry_block: bool = False
    block_monday_entries: bool = True
    loss_cooldown_bars: int = 0


@dataclass
class FabioConfig:
    """Configuracion exacta de FabioOrb (`RunFabio`, BIP 3 = 5m ETH)."""

    start_h: int = 8
    start_m: int = 30
    dur_min: int = 30
    end_h: int = 14
    end_m: int = 0
    tp_rr: float = 1.0
    delta_threshold: int = 200
    use_cum_delta: bool = False
    cum_delta_threshold: int = 500
    disable_delta_filter: bool = False
    max_initial_risk_atr: float = 0.0
    max_initial_risk_points: float = 125.0
    loss_cooldown_bars: int = 0
    atr_period: int = 14
    virtual_round_turn_commission: float = 4.36
    timezone: str = "ct"


@dataclass
class SwasConfig:
    """Configuracion exacta de Swas (`RunSwas`, BIP 2 = 3m ETH)."""

    exit_on_st_flip: bool = True   # EdgeLab 2026-11-16 (PREREGISTRO_TANDA2 L1): False = sin salida por giro de SuperTrend (variante)
    atr_length: int = 14
    ema_period: int = 9
    use_time_filter: bool = True
    ny_open_hour: int = 9
    ny_open_minute: int = 30
    pre_block_min: int = 10
    post_block_min: int = 30
    use_eod_close: bool = True
    close_hour: int = 15
    close_minute: int = 55
    st_period: int = 10
    st_mult: float = 3.2
    use_hard_stop: bool = False
    hard_stop_atr_mult: float = 3.0
    use_adx_filter: bool = True
    adx_period: int = 14
    adx_threshold: float = 20.0
    use_vwap_ema_bias: bool = True
    bias_ema_period: int = 21
    use_regime_filter: bool = True
    regime_atr_lookback: int = 100
    regime_atr_multiplier: float = 2.9
    allow_longs: bool = True
    allow_shorts: bool = True
    require_supertrend_entry_alignment: bool = False
    min_ema_slope_atr: float = 0.05
    loss_cooldown_bars: int = 1
    block_long_entry_hour_enabled: bool = True
    blocked_long_entry_hour: int = 7
    block_short_entry_hour_enabled: bool = True
    blocked_short_entry_hour: int = 13
    bars_required_to_trade: int = 60
    virtual_round_turn_commission: float = 4.36
    timezone: str = "ct"
    flatten_before_daily_futures_close: bool = True
    daily_futures_flatten_time_central: int = 154400
    daily_futures_resume_time_central: int = 170100


def _is_daily_futures_close_blocked(
    t_ct: int,
    dow_ct: int,
    flatten_time: int,
    resume_time: int,
) -> bool:
    """Exact translation of IsDailyFuturesCloseBlocked (15:44-17:01 CT Mon-Thu, Fri 15:44 -> Sun 17:01 CT)."""
    if dow_ct == 5:  # Sabado
        return True
    if dow_ct == 6:  # Domingo
        return t_ct < resume_time
    if dow_ct == 4:  # Viernes
        return t_ct >= flatten_time
    return flatten_time <= t_ct < resume_time


# ---------------------------------------------------------------------------
# Indicadores NinjaTrader 8 exactos (@ATR.cs, @EMA.cs, @ADX.cs, SMA, MAX, MIN)
# ---------------------------------------------------------------------------


def _nt8_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """ATR recursivo exacto de NinjaTrader 8 (`@ATR.cs`)."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    p = max(1, int(period))
    out[0] = float(high[0] - low[0])
    for i in range(1, n):
        hi = float(high[i])
        lo = float(low[i])
        pc = float(close[i - 1])
        tr = max(abs(lo - pc), max(hi - lo, abs(hi - pc)))
        w = min(i + 1, p)
        out[i] = ((w - 1) * out[i - 1] + tr) / w
    return out


def _nt8_ema(series: np.ndarray, period: int) -> np.ndarray:
    """EMA exacto de NinjaTrader 8 (`@EMA.cs`, semilla = input[0])."""
    n = len(series)
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    p = max(1, int(period))
    k1 = 2.0 / (1.0 + p)
    k2 = 1.0 - k1
    out[0] = float(series[0])
    for i in range(1, n):
        out[i] = float(series[i]) * k1 + out[i - 1] * k2
    return out


def _nt8_sma(series: np.ndarray, period: int) -> np.ndarray:
    """SMA exacto de NinjaTrader 8 (ventana min(i + 1, period))."""
    n = len(series)
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    p = max(1, int(period))
    running = 0.0
    for i in range(n):
        running += float(series[i])
        if i >= p:
            running -= float(series[i - p])
            out[i] = running / p
        else:
            out[i] = running / (i + 1)
    return out


def _nt8_adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """ADX exacto de NinjaTrader 8 (`@ADX.cs`, semilla Value[0] = 50)."""
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    p = max(1, int(period))
    sum_tr = float(high[0] - low[0])
    sum_dmp = 0.0
    sum_dmm = 0.0
    out[0] = 50.0
    eps = 1e-10
    for i in range(1, n):
        hi = float(high[i])
        lo = float(low[i])
        ph = float(high[i - 1])
        pl = float(low[i - 1])
        pc = float(close[i - 1])

        tr = max(abs(lo - pc), max(hi - lo, abs(hi - pc)))
        up = hi - ph
        dn = pl - lo
        dmp = max(up, 0.0) if up > dn else 0.0
        dmm = max(dn, 0.0) if dn > up else 0.0

        if i < p:
            sum_tr += tr
            sum_dmp += dmp
            sum_dmm += dmm
        else:
            sum_tr = sum_tr - sum_tr / p + tr
            sum_dmp = sum_dmp - sum_dmp / p + dmp
            sum_dmm = sum_dmm - sum_dmm / p + dmm

        di_plus = 0.0 if abs(sum_tr) <= eps else 100.0 * (sum_dmp / sum_tr)
        di_minus = 0.0 if abs(sum_tr) <= eps else 100.0 * (sum_dmm / sum_tr)
        di_sum = di_plus + di_minus
        di_diff = abs(di_plus - di_minus)
        if abs(di_sum) <= eps:
            out[i] = 50.0
        else:
            out[i] = ((p - 1) * out[i - 1] + 100.0 * di_diff / di_sum) / p
    return out


def _rolling_extrema(arr: np.ndarray, length: int, is_max: bool) -> np.ndarray:
    """MAX / MIN causal de NinjaTrader sobre ventana min(i + 1, length)."""
    s = pd.Series(arr)
    w = max(1, int(length))
    rolled = s.rolling(window=w, min_periods=1)
    return (rolled.max() if is_max else rolled.min()).to_numpy(dtype=np.float64)


# ---------------------------------------------------------------------------
# Helpers de calendario, rollover, SuperTrend y simulador de ordenes M1
# ---------------------------------------------------------------------------


def _select_calendar_arrays(
    series: BarSeries, timezone: str
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Devuelve (hhmmss, cal_date, dow) en CT o ET segun configuracion."""
    if timezone.lower() == "et":
        return series.hhmmss_et, series.cal_date_et, series.dow_et
    return series.hhmmss_ct, series.cal_date_ct, series.dow_ct


def _third_friday(year: int, month: int) -> date:
    """Tercer viernes del mes (`GetThirdFriday` en IL)."""
    key = (year, month)
    cached = _THIRD_FRIDAY_CACHE.get(key)
    if cached is not None:
        return cached
    first = date(year, month, 1)
    # Python weekday: Mon=0..Fri=4..Sun=6 -> equivalente a (5 - C#DayOfWeek + 7) % 7
    offset = (4 - first.weekday() + 7) % 7
    tf = first + timedelta(days=offset + 14)
    _THIRD_FRIDAY_CACHE[key] = tf
    return tf


def _is_near_rollover(yyyymmdd: int, days_before: int, days_after: int) -> bool:
    """Ventana de rollover trimestral CME (`IsNearRollover` en IL)."""
    y = yyyymmdd // 10000
    m = (yyyymmdd // 100) % 100
    d = yyyymmdd % 100
    cur = date(y, m, d)
    for dy in (-1, 0, 1):
        yy = y + dy
        for qm in _ROLLOVER_MONTHS:
            tf = _third_friday(yy, qm)
            diff_days = (cur - tf).days
            if -days_before <= diff_days <= days_after:
                return True
    return False


def _supertrend_step(
    high_v: float,
    low_v: float,
    close_v: float,
    st_atr: float,
    mult: float,
    st_init: bool,
    prev_final_upper: float,
    prev_final_lower: float,
    prev_close: float,
    prev_trend: int,
) -> Tuple[float, float, int, bool]:
    """Paso SuperTrend manual identico al IL de `RunAbsorb` y `RunSwas`."""
    hl2 = 0.5 * (high_v + low_v)
    basic_upper = hl2 + mult * st_atr
    basic_lower = hl2 - mult * st_atr
    if not st_init:
        final_upper = basic_upper
        final_lower = basic_lower
        trend = -1 if close_v < basic_lower else 1
        return final_upper, final_lower, trend, True

    if basic_upper < prev_final_upper or prev_close > prev_final_upper:
        final_upper = basic_upper
    else:
        final_upper = prev_final_upper

    if basic_lower > prev_final_lower or prev_close < prev_final_lower:
        final_lower = basic_lower
    else:
        final_lower = prev_final_lower

    if prev_trend == -1 and close_v > prev_final_upper:
        trend = 1
    elif prev_trend == 1 and close_v < prev_final_lower:
        trend = -1
    else:
        trend = prev_trend

    return final_upper, final_lower, trend, True


def _lookup_abs(history: List[bool], bars_back: int, abs_hist_idx: int) -> bool:
    """Reproduce `FUNDEDSYNCSTACK.LookupAbs(history, barsBack, absHistIdx)`."""
    length = len(history)
    if abs_hist_idx - bars_back <= 0:
        return False
    idx = (abs_hist_idx - 1 - bars_back) % length
    return history[idx]


class _ModuleExecutionTracker:
    """Maquina de ejecucion causal sobre `ms.bip1` (fills a apertura M1 + stops/targets intrabar)."""

    def __init__(
        self,
        module_tag: str,
        m1: BarSeries,
        tick_size: float,
        point_value: float,
        loss_cooldown_bars: int,
        commission_rt: float,
    ) -> None:
        self.tag = module_tag
        self.m1 = m1
        self.n_m1 = len(m1.close)
        self.tick_size = tick_size
        self.point_value = point_value
        self.loss_cooldown_bars = max(0, int(loss_cooldown_bars))
        self.commission_rt = float(commission_rt)

        self.net_side: int = 0  # 0 flat, +1 long, -1 short
        self.qty: int = 0
        self.entry_m1_idx: int = -1
        self.entry_ts_ns: int = 0
        self.entry_price: float = 0.0
        self.stop_price: float = math.nan
        self.target_price: float = math.nan
        self.entry_name: str = ""
        self.mae_pts: float = 0.0
        self.mfe_pts: float = 0.0

        self.pending_entry: Optional[Tuple[int, int, float, float, str, int]] = None
        self.pending_exit: Optional[Tuple[str, int]] = None

        self.daily_losses: int = 0
        self.pending_daily_losses: int = 0
        self.loss_cooldown_remaining: int = 0
        self.seq: int = 0
        self.last_m1_idx: int = -1
        self.trades: List[TradeRecord] = []

    @property
    def pos(self) -> int:
        if self.net_side > 0:
            return _POS_LONG
        if self.net_side < 0:
            return _POS_SHORT
        return _POS_FLAT

    def can_enter(self) -> bool:
        return (
            self.net_side == 0
            and self.pending_entry is None
            and self.pending_exit is None
        )

    def consume_loss_cooldown(self) -> bool:
        if self.loss_cooldown_remaining > 0:
            self.loss_cooldown_remaining -= 1
            return False
        return True

    def flush_pending_daily_losses(self) -> None:
        if self.pending_daily_losses > 0:
            self.daily_losses += self.pending_daily_losses
            self.pending_daily_losses = 0

    def reset_daily_losses(self) -> None:
        self.daily_losses = 0
        self.pending_daily_losses = 0

    def request_entry(
        self,
        side: int,
        qty: int,
        stop_price: float,
        target_price: float,
        signal_m1_idx: int,
    ) -> bool:
        exec_idx = signal_m1_idx + 1
        if not self.can_enter() or qty <= 0 or exec_idx >= self.n_m1:
            return False
        self.seq += 1
        dir_code = "L" if side > 0 else "S"
        ename = f"{self.tag}_E_{dir_code}_{self.seq}"
        sl = round_tick(stop_price, self.tick_size) if not math.isnan(stop_price) else math.nan
        tp = round_tick(target_price, self.tick_size) if not math.isnan(target_price) else math.nan
        self.pending_entry = (side, qty, sl, tp, ename, exec_idx)
        return True

    def request_exit(self, reason: str, signal_m1_idx: int) -> bool:
        if self.net_side == 0 or self.pending_exit is not None:
            return False
        exec_idx = signal_m1_idx + 1
        if exec_idx >= self.n_m1:
            return False
        # CancelProtection() en ExitModule cancela Stop/Target antes de la siguiente barra
        self.pending_exit = (reason, exec_idx)
        return True

    def _record_close(self, exit_m1_idx: int, exit_price: float, exit_name: str) -> None:
        pnl_pts = (exit_price - self.entry_price) * self.net_side
        gross_usd = pnl_pts * self.qty * self.point_value
        comm_usd = self.commission_rt * self.qty
        net_usd = gross_usd - comm_usd

        if net_usd < 0.0:
            self.pending_daily_losses += 1
            if self.loss_cooldown_bars > 0:
                self.loss_cooldown_remaining = self.loss_cooldown_bars

        bars_held = max(1, exit_m1_idx - self.entry_m1_idx + 1)
        scale = self.qty * self.point_value
        self.trades.append(
            TradeRecord(
                module=self.tag,
                side=self.net_side,
                qty=self.qty,
                entry_time_utc=self.entry_ts_ns,
                exit_time_utc=int(self.m1.ts_ns[exit_m1_idx]),
                entry_price=self.entry_price,
                exit_price=exit_price,
                stop_price=self.stop_price,
                target_price=self.target_price,
                entry_name=self.entry_name,
                exit_name=exit_name,
                pnl_pts=pnl_pts,
                pnl_usd=net_usd,
                mae_usd=max(0.0, self.mae_pts) * scale,
                mfe_usd=max(0.0, self.mfe_pts) * scale,
                bars=bars_held,
            )
        )
        self.net_side = 0
        self.qty = 0
        self.entry_m1_idx = -1
        self.entry_ts_ns = 0
        self.entry_price = 0.0
        self.stop_price = math.nan
        self.target_price = math.nan
        self.entry_name = ""
        self.mae_pts = 0.0
        self.mfe_pts = 0.0

    def _check_intrabar_protection(self, m: int) -> None:
        if self.net_side == 0:
            return
        o = float(self.m1.open[m])
        h = float(self.m1.high[m])
        l = float(self.m1.low[m])
        has_sl = not math.isnan(self.stop_price)
        has_tp = not math.isnan(self.target_price)

        if self.net_side > 0:
            if has_sl and o <= self.stop_price:
                self.mae_pts = max(self.mae_pts, self.entry_price - o)
                self._record_close(m, o, "STOP")
                return
            if has_tp and o >= self.target_price:
                self.mfe_pts = max(self.mfe_pts, o - self.entry_price)
                self._record_close(m, o, "TARGET")
                return
            if has_sl and l <= self.stop_price:
                self.mae_pts = max(self.mae_pts, self.entry_price - self.stop_price)
                self._record_close(m, self.stop_price, "STOP")
                return
            if has_tp and h >= self.target_price:
                self.mfe_pts = max(self.mfe_pts, h - self.entry_price)
                self.mae_pts = max(self.mae_pts, self.entry_price - l)
                self._record_close(m, self.target_price, "TARGET")
                return
            self.mae_pts = max(self.mae_pts, self.entry_price - l)
            self.mfe_pts = max(self.mfe_pts, h - self.entry_price)
        else:
            if has_sl and o >= self.stop_price:
                self.mae_pts = max(self.mae_pts, o - self.entry_price)
                self._record_close(m, o, "STOP")
                return
            if has_tp and o <= self.target_price:
                self.mfe_pts = max(self.mfe_pts, self.entry_price - o)
                self._record_close(m, o, "TARGET")
                return
            if has_sl and h >= self.stop_price:
                self.mae_pts = max(self.mae_pts, self.stop_price - self.entry_price)
                self._record_close(m, self.stop_price, "STOP")
                return
            if has_tp and l <= self.target_price:
                self.mfe_pts = max(self.mfe_pts, self.entry_price - l)
                self.mae_pts = max(self.mae_pts, h - self.entry_price)
                self._record_close(m, self.target_price, "TARGET")
                return
            self.mae_pts = max(self.mae_pts, h - self.entry_price)
            self.mfe_pts = max(self.mfe_pts, self.entry_price - l)

    def advance_to(self, target_m1_idx: int) -> None:
        """Avanza ejecucion sobre `ms.bip1` hasta el cierre de `target_m1_idx` (inclusive)."""
        limit = min(target_m1_idx, self.n_m1 - 1)
        for m in range(self.last_m1_idx + 1, limit + 1):
            if self.pending_exit is not None and self.pending_exit[1] == m:
                reason, _ = self.pending_exit
                self.pending_exit = None
                if self.net_side != 0:
                    fill_px = float(self.m1.open[m])
                    adv = (self.entry_price - fill_px) * self.net_side
                    fav = (fill_px - self.entry_price) * self.net_side
                    self.mae_pts = max(self.mae_pts, adv)
                    self.mfe_pts = max(self.mfe_pts, fav)
                    self._record_close(m, fill_px, reason)
            elif self.pending_entry is not None and self.pending_entry[5] == m:
                side, qty, sl, tp, ename, _ = self.pending_entry
                self.pending_entry = None
                self.net_side = side
                self.qty = qty
                self.entry_m1_idx = m
                self.entry_ts_ns = int(self.m1.ts_ns[m])
                self.entry_price = float(self.m1.open[m])
                self.stop_price = sl
                self.target_price = tp
                self.entry_name = ename
                self.mae_pts = 0.0
                self.mfe_pts = 0.0
                self._check_intrabar_protection(m)
            elif self.net_side != 0:
                self._check_intrabar_protection(m)
        if limit > self.last_m1_idx:
            self.last_m1_idx = limit


# ---------------------------------------------------------------------------
# Submodulo A1 y A20: RunAbsorb compartido (BIP 1 = 1m ETH, BIP 4 = 20m ETH)
# ---------------------------------------------------------------------------


def _compute_vap_bands(
    close: np.ndarray,
    volume: np.ndarray,
    vol_at_price: List[float],
    j: int,
    vp_length: int,
    vp_resolution: int,
    vp_high: float,
    vp_low: float,
) -> Tuple[float, float]:
    """Calcula VAH y VAL segun el perfil de volumen exacto de `RunAbsorb`."""
    step = (vp_high - vp_low) / float(vp_resolution)
    if step <= 0.0:
        return math.nan, math.nan

    for b in range(vp_resolution):
        vol_at_price[b] = 0.0

    k_limit = min(vp_length, j + 1)
    for k in range(k_limit):
        b = int(math.floor((float(close[j - k]) - vp_low) / step))
        if 0 <= b < vp_resolution:
            vol_at_price[b] += float(volume[j - k])

    max_bin_vol = 0.0
    poc_bin = 0
    total_vol = 0.0
    for b in range(vp_resolution):
        bv = vol_at_price[b]
        total_vol += bv
        if bv > max_bin_vol:
            max_bin_vol = bv
            poc_bin = b

    va_target = total_vol * 0.7
    va_vol = vol_at_price[poc_bin]
    hi_bin = poc_bin
    lo_bin = poc_bin
    while va_vol < va_target and (hi_bin < vp_resolution - 1 or lo_bin > 0):
        up_vol = 0.0 if hi_bin >= vp_resolution - 1 else vol_at_price[hi_bin + 1]
        dn_vol = 0.0 if lo_bin <= 0 else vol_at_price[lo_bin - 1]
        if up_vol >= dn_vol and hi_bin < vp_resolution - 1:
            hi_bin += 1
            va_vol += up_vol
        elif lo_bin > 0:
            lo_bin -= 1
            va_vol += dn_vol

    vah = vp_low + hi_bin * step + step
    val = vp_low + lo_bin * step
    return vah, val


def _run_absorb(
    ms: MultiSeriesContext,
    series: BarSeries,
    tag: str,
    qty: int,
    cfg: _AbsorbBaseConfig,
) -> pd.DataFrame:
    if qty <= 0 or len(series.close) == 0 or len(ms.bip1.close) == 0:
        return trades_to_df([])

    opn = series.open
    high = series.high
    low = series.low
    close = series.close
    volume = series.volume
    m1_end_idx = series.m1_end_idx
    is_new_session = series.is_new_session
    hhmmss, cal_date, dow = _select_calendar_arrays(series, cfg.timezone)

    atr_ind = _nt8_atr(high, low, close, cfg.atr_period)
    atr_st = _nt8_atr(high, low, close, cfg.st_period)
    avg_vol_sma = _nt8_sma(volume, 20)
    vp_max_high = _rolling_extrema(high, cfg.vp_length, is_max=True)
    vp_min_low = _rolling_extrema(low, cfg.vp_length, is_max=False)
    rng10_max_high = _rolling_extrema(high, 10, is_max=True)
    rng10_min_low = _rolling_extrema(low, 10, is_max=False)

    tracker = _ModuleExecutionTracker(
        module_tag=tag,
        m1=ms.bip1,
        tick_size=ms.tick_size,
        point_value=ms.point_value,
        loss_cooldown_bars=cfg.loss_cooldown_bars,
        commission_rt=cfg.virtual_round_turn_commission,
    )

    vp_res = max(1, int(cfg.vp_resolution))
    vol_at_price = [0.0] * vp_res
    delta_hist_len = max(1, int(cfg.delta_lookback))
    delta_history = [0.0] * delta_hist_len
    delta_idx = 0
    prev_smooth_delta = 0.0

    absorption_count = 0
    abs_up_hist = [False] * 10
    abs_down_hist = [False] * 10
    abs_hist_idx = 0

    range_history = [0.0] * 60
    range_idx = 0

    atr_base_len = max(1, int(cfg.vol_baseline_lookback))
    atr_base_hist = [0.0] * atr_base_len
    atr_base_idx = 0

    orb_high = math.nan
    orb_low = math.nan
    orb_defined = False
    session_bars_count = 0
    prev_in_sess = False
    prev_in_sess_close = False

    cum_pv = 0.0
    cum_vol = 0.0

    st_init = False
    final_upper = 0.0
    final_lower = 0.0
    prev_final_upper = 0.0
    prev_final_lower = 0.0
    prev_close = 0.0
    trend = 1
    prev_trend = 1

    sess_start = cfg.session_start_hour * 60 + cfg.session_start_minute
    sess_end = cfg.session_end_hour * 60 + cfg.session_end_minute
    blk_start = cfg.block_start_hour * 60 + cfg.block_start_minute
    blk_end = cfg.block_end_hour * 60 + cfg.block_end_minute
    bar_minutes = series.timeframe_min if series.timeframe_min > 0 else 1
    orb_bars = max(1, cfg.orb_minutes // bar_minutes)

    rollover_cache: Dict[int, bool] = {}
    n_bars = len(close)
    req_bars = max(0, int(cfg.bars_required_to_trade))

    for j in range(n_bars):
        if j < req_bars:
            continue

        e_j = int(m1_end_idx[j])
        tracker.advance_to(e_j)
        can_trade_cooldown = tracker.consume_loss_cooldown()

        cur_atr = float(atr_ind[j])
        atr_base_hist[atr_base_idx % atr_base_len] = cur_atr
        atr_base_idx += 1
        ab_cnt = min(atr_base_idx, atr_base_len)
        avg_atr = sum(atr_base_hist[:ab_cnt]) / ab_cnt if ab_cnt > 0 else cur_atr
        high_vol_regime = (cur_atr > avg_atr * cfg.vol_regime_multiplier) if avg_atr > 0.0 else False
        vol_filter_pass = (not high_vol_regime) if cfg.use_volatility_filter else True

        if bool(is_new_session[j]):
            cum_pv = 0.0
            cum_vol = 0.0
        hi_j = float(high[j])
        lo_j = float(low[j])
        cl_j = float(close[j])
        op_j = float(opn[j])
        vol_j = float(volume[j])

        typical = (hi_j + lo_j + cl_j) / 3.0
        cum_pv += typical * vol_j
        cum_vol += vol_j
        vwap = (cum_pv / cum_vol) if cum_vol > 0.0 else typical
        upper_vwap_band = vwap + cur_atr * cfg.vwap_band
        lower_vwap_band = vwap - cur_atr * cfg.vwap_band

        hhmm = int(hhmmss[j]) // 100
        minute_of_day = (hhmm // 100) * 60 + (hhmm % 100)
        in_session = sess_start <= minute_of_day < sess_end
        entered_session = in_session and not prev_in_sess
        exited_session = (not in_session) and prev_in_sess_close
        prev_in_sess = in_session
        prev_in_sess_close = in_session

        if entered_session:
            tracker.reset_daily_losses()
            orb_high = math.nan
            orb_low = math.nan
            orb_defined = False
            session_bars_count = -1

        if cfg.flatten_at_session_end and exited_session and tracker.pos != _POS_FLAT:
            tracker.request_exit("SESSION", e_j)

        vah, val = _compute_vap_bands(
            close,
            volume,
            vol_at_price,
            j,
            cfg.vp_length,
            vp_res,
            float(vp_max_high[j]),
            float(vp_min_low[j]),
        )

        # Bar delta segun IL exacto de RunAbsorb (notar formula (High - Close) cuando Close < Open)
        if cl_j > op_j:
            buy_vol = vol_j
        elif cl_j == op_j:
            buy_vol = vol_j * 0.5
        else:
            bar_rng = hi_j - lo_j
            buy_vol = vol_j * ((hi_j - cl_j) / (bar_rng + 0.0001))
        bar_delta = buy_vol - (vol_j - buy_vol)

        delta_history[delta_idx % delta_hist_len] = bar_delta
        delta_idx += 1
        d_cnt = min(delta_idx, delta_hist_len)
        smooth_delta = sum(delta_history[:d_cnt]) / d_cnt if d_cnt > 0 else 0.0
        delta_shift_up = smooth_delta > 0.0 and smooth_delta > prev_smooth_delta
        delta_shift_down = smooth_delta < 0.0 and smooth_delta < prev_smooth_delta
        prev_smooth_delta = smooth_delta

        avg_vol = float(avg_vol_sma[j])
        body_atr_ratio = abs(cl_j - op_j) / (cur_atr if cur_atr > 0.0 else 1.0)
        is_absorption = (vol_j > avg_vol * cfg.absorb_vol_mult) and (body_atr_ratio < cfg.absorb_price_thresh)
        abs_up = is_absorption and (cl_j > op_j)
        abs_down = is_absorption and (cl_j < op_j)
        absorption_count = (absorption_count + 1) if is_absorption else 0

        abs_slot = abs_hist_idx % 10
        abs_up_hist[abs_slot] = abs_up
        abs_down_hist[abs_slot] = abs_down
        abs_hist_idx += 1

        range10 = float(rng10_max_high[j] - rng10_min_low[j])
        range_history[range_idx % 60] = range10
        range_idx += 1
        r_cnt = min(range_idx, 60)
        avg_range10 = sum(range_history[:r_cnt]) / r_cnt if r_cnt > 0 else range10
        is_tight_range = range10 < avg_range10 * 0.6
        is_wide_climax = (range10 > avg_range10 * 1.2) and (vol_j > avg_vol * 1.5)
        climax_long = is_wide_climax and (cl_j > op_j) and (smooth_delta > 0.0)
        climax_short = is_wide_climax and (cl_j < op_j) and (smooth_delta < 0.0)

        recent_abs_up = (
            _lookup_abs(abs_up_hist, 3, abs_hist_idx)
            or _lookup_abs(abs_up_hist, 4, abs_hist_idx)
            or _lookup_abs(abs_up_hist, 5, abs_hist_idx)
        )
        recent_abs_down = (
            _lookup_abs(abs_down_hist, 3, abs_hist_idx)
            or _lookup_abs(abs_down_hist, 4, abs_hist_idx)
            or _lookup_abs(abs_down_hist, 5, abs_hist_idx)
        )
        abs_climax_long = recent_abs_up and is_tight_range and climax_long
        abs_climax_short = recent_abs_down and is_tight_range and climax_short

        if in_session:
            session_bars_count += 1
            if session_bars_count <= orb_bars:
                orb_high = hi_j if math.isnan(orb_high) else max(orb_high, hi_j)
                orb_low = lo_j if math.isnan(orb_low) else min(orb_low, lo_j)
                orb_defined = session_bars_count == orb_bars

        prev_cl_j = float(close[j - 1]) if j > 0 else cl_j
        orb_long = cfg.use_orb and orb_defined and (cl_j > orb_high) and not (prev_cl_j > orb_high)
        orb_short = cfg.use_orb and orb_defined and (cl_j < orb_low) and not (prev_cl_j < orb_low)

        near_val = (not math.isnan(val)) and (lo_j <= val * 1.001) and (lo_j >= val * 0.999)
        near_vah = (not math.isnan(vah)) and (hi_j >= vah * 0.999) and (hi_j <= vah * 1.001)
        vp_long = near_val and abs_up and delta_shift_up
        vp_short = near_vah and abs_down and delta_shift_down

        if cfg.use_rollover_filter:
            d_key = int(cal_date[j])
            near_roll = rollover_cache.get(d_key)
            if near_roll is None:
                near_roll = _is_near_rollover(d_key, cfg.rollover_days_before, cfg.rollover_days_after)
                rollover_cache[d_key] = near_roll
            rollover_ok = not near_roll
        else:
            rollover_ok = True

        long_sig = (abs_climax_long or orb_long or vp_long) and (
            (cl_j > lower_vwap_band) if cfg.use_vwap else True
        )
        short_sig = (abs_climax_short or orb_short or vp_short) and (
            (cl_j < upper_vwap_band) if cfg.use_vwap else True
        )
        env_ok = rollover_ok and vol_filter_pass

        daily_loss_ok = tracker.daily_losses < cfg.max_daily_losses
        tracker.flush_pending_daily_losses()

        final_upper, final_lower, trend, st_init = _supertrend_step(
            hi_j,
            lo_j,
            cl_j,
            float(atr_st[j]),
            cfg.st_mult,
            st_init,
            prev_final_upper,
            prev_final_lower,
            prev_close,
            prev_trend,
        )
        st_flip_up = trend == 1 and prev_trend == -1
        st_flip_down = trend == -1 and prev_trend == 1
        st_align_long = (trend == 1) if cfg.require_supertrend_entry_alignment else True
        st_align_short = (trend == -1) if cfg.require_supertrend_entry_alignment else True

        in_block = False
        if blk_start != blk_end:
            if blk_start < blk_end:
                in_block = blk_start <= minute_of_day < blk_end
            else:
                in_block = minute_of_day >= blk_start or minute_of_day < blk_end

        early_block_pass = (not in_block) if (tag == "A1" and cfg.use_early_entry_block) else True
        monday_block_pass = (
            (int(dow[j]) != 0) if (tag == "A20" and cfg.block_monday_entries) else True
        )

        pos = tracker.pos
        daily_close_blocked = (
            _is_daily_futures_close_blocked(
                int(ms.bip1.hhmmss_ct[e_j]),
                int(ms.bip1.dow_ct[e_j]),
                cfg.daily_futures_flatten_time_central,
                cfg.daily_futures_resume_time_central,
            )
            if cfg.flatten_before_daily_futures_close
            else False
        )
        if daily_close_blocked and pos != _POS_FLAT:
            tracker.request_exit("DAILY_FUTURES_CLOSE", e_j)
        elif cfg.exit_on_st_flip and pos == _POS_LONG and st_flip_down:
            tracker.request_exit("ST", e_j)
        elif cfg.exit_on_st_flip and pos == _POS_SHORT and st_flip_up:
            tracker.request_exit("ST", e_j)

        if (
            (not daily_close_blocked)
            and cfg.allow_longs
            and long_sig
            and env_ok
            and daily_loss_ok
            and can_trade_cooldown
            and st_align_long
            and early_block_pass
            and monday_block_pass
            and tracker.can_enter()
        ):
            sl = (cl_j - cfg.hard_stop_atr_mult * cur_atr) if cfg.use_hard_stop else math.nan
            tracker.request_entry(+1, qty, sl, math.nan, e_j)
        elif (
            (not daily_close_blocked)
            and cfg.allow_shorts
            and short_sig
            and env_ok
            and daily_loss_ok
            and can_trade_cooldown
            and st_align_short
            and early_block_pass
            and monday_block_pass
            and tracker.can_enter()
        ):
            sl = (cl_j + cfg.hard_stop_atr_mult * cur_atr) if cfg.use_hard_stop else math.nan
            tracker.request_entry(-1, qty, sl, math.nan, e_j)

        prev_final_upper = final_upper
        prev_final_lower = final_lower
        prev_close = cl_j
        prev_trend = trend

    tracker.advance_to(len(ms.bip1.close) - 1)
    return trades_to_df(tracker.trades)


def run_a1(
    ms: MultiSeriesContext,
    qty: int = 1,
    cfg: Optional[Absorb1mConfig] = None,
) -> pd.DataFrame:
    """Ejecuta modulo A1 (Absorb 1m, BIP 1) de manera causal barra por barra."""
    return _run_absorb(ms, ms.bip1, "A1", qty, cfg or Absorb1mConfig())


def run_a20(
    ms: MultiSeriesContext,
    qty: int = 2,
    cfg: Optional[Absorb20mConfig] = None,
) -> pd.DataFrame:
    """Ejecuta modulo A20 (Absorb 20m, BIP 4) de manera causal barra por barra."""
    return _run_absorb(ms, ms.bip4, "A20", qty, cfg or Absorb20mConfig())


# ---------------------------------------------------------------------------
# Submodulo F: RunFabio (BIP 3 = 5m ETH)
# ---------------------------------------------------------------------------


def run_f(
    ms: MultiSeriesContext,
    qty: int = 1,
    cfg: Optional[FabioConfig] = None,
) -> pd.DataFrame:
    """Ejecuta modulo F (FabioOrb, BIP 3 = 5m ETH) de manera causal barra por barra."""
    cfg = cfg or FabioConfig()
    series = ms.bip3
    if qty <= 0 or len(series.close) == 0 or len(ms.bip1.close) == 0:
        return trades_to_df([])

    high = series.high
    low = series.low
    close = series.close
    volume = series.volume
    m1_end_idx = series.m1_end_idx
    hhmmss, cal_date, _ = _select_calendar_arrays(series, cfg.timezone)

    atr_f = _nt8_atr(high, low, close, cfg.atr_period)

    orb_start_time = cfg.start_h * 100 + cfg.start_m
    start_min = (orb_start_time // 100) * 60 + (orb_start_time % 100)
    end_min = (start_min + cfg.dur_min) % 1440
    if end_min < 0:
        end_min += 1440
    orb_end_time = (end_min // 60) * 100 + (end_min % 60)
    trade_end_time = cfg.end_h * 100 + cfg.end_m

    tracker = _ModuleExecutionTracker(
        module_tag="F",
        m1=ms.bip1,
        tick_size=ms.tick_size,
        point_value=ms.point_value,
        loss_cooldown_bars=cfg.loss_cooldown_bars,
        commission_rt=cfg.virtual_round_turn_commission,
    )

    cur_date = -1
    prev_bar_time = 0
    orb_inited = False
    orb_session_ended = False
    orb_high = 0.0
    orb_low = 0.0
    long_done_today = False
    was_long = False
    pos_sl = 0.0
    pos_tp = 0.0
    cum_delta = 0.0

    n_bars = len(close)
    for j in range(n_bars):
        t = int(hhmmss[j]) // 100
        d = int(cal_date[j])
        e_j = int(m1_end_idx[j])

        if j < 2:
            cur_date = d
            prev_bar_time = t
            continue

        tracker.advance_to(e_j)
        cooldown_ok = tracker.consume_loss_cooldown()

        hi_j = float(high[j])
        lo_j = float(low[j])
        cl_j = float(close[j])
        vol_j = float(volume[j])

        rng = hi_j - lo_j
        bar_delta = 0.0 if rng <= 0.0 else vol_j * (2.0 * (cl_j - lo_j) / rng - 1.0)

        if d != cur_date:
            cur_date = d
            orb_inited = False
            orb_session_ended = False
            orb_high = 0.0
            orb_low = 0.0
            long_done_today = False
            was_long = False
            pos_sl = 0.0
            pos_tp = 0.0
            cum_delta = 0.0

        in_orb = orb_start_time < t <= orb_end_time
        in_trade_window = orb_end_time < t <= trade_end_time

        if orb_start_time < t <= trade_end_time:
            cum_delta += bar_delta

        if in_orb:
            if not orb_inited:
                orb_high = hi_j
                orb_low = lo_j
                orb_inited = True
            else:
                if hi_j > orb_high:
                    orb_high = hi_j
                if lo_j < orb_low:
                    orb_low = lo_j

        if not orb_session_ended and orb_inited and t > orb_end_time:
            orb_session_ended = True

        pos = tracker.pos
        if pos == _POS_LONG:
            was_long = True
        if pos == _POS_FLAT and was_long:
            was_long = False
            pos_sl = 0.0
            pos_tp = 0.0

        if t >= trade_end_time and prev_bar_time < trade_end_time and pos == _POS_LONG:
            tracker.request_exit("EOD", e_j)

        prev_bar_time = t

        if (
            orb_session_ended
            and in_trade_window
            and not long_done_today
            and cooldown_ok
            and tracker.can_enter()
            and cl_j > orb_high
        ):
            entry_ref = cl_j
            sl = orb_low
            if sl < entry_ref:
                if cfg.disable_delta_filter:
                    delta_ok = True
                else:
                    delta_ok = bar_delta >= float(cfg.delta_threshold)
                    if cfg.use_cum_delta:
                        delta_ok = delta_ok and (cum_delta >= float(cfg.cum_delta_threshold))

                atr_val = float(atr_f[j])
                risk = entry_ref - sl
                if cfg.max_initial_risk_atr > 0.0:
                    atr_risk_ok = atr_val > 0.0 and risk <= cfg.max_initial_risk_atr * atr_val
                else:
                    atr_risk_ok = True

                if cfg.max_initial_risk_points > 0.0:
                    pts_risk_ok = risk <= cfg.max_initial_risk_points
                else:
                    pts_risk_ok = True

                if delta_ok and pts_risk_ok and atr_risk_ok:
                    tp = entry_ref + cfg.tp_rr * (entry_ref - sl)
                    pos_sl = sl
                    pos_tp = tp
                    tracker.request_entry(+1, qty, pos_sl, pos_tp, e_j)
                    long_done_today = True

    tracker.advance_to(len(ms.bip1.close) - 1)
    return trades_to_df(tracker.trades)


# ---------------------------------------------------------------------------
# Submodulo S: RunSwas (BIP 2 = 3m ETH)
# ---------------------------------------------------------------------------


def run_s(
    ms: MultiSeriesContext,
    qty: int = 1,
    cfg: Optional[SwasConfig] = None,
) -> pd.DataFrame:
    """Ejecuta modulo S (Swas, BIP 2 = 3m ETH) de manera causal barra por barra."""
    cfg = cfg or SwasConfig()
    series = ms.bip2
    if qty <= 0 or len(series.close) == 0 or len(ms.bip1.close) == 0:
        return trades_to_df([])

    high = series.high
    low = series.low
    close = series.close
    volume = series.volume
    m1_end_idx = series.m1_end_idx
    is_new_session = series.is_new_session
    hhmmss, cal_date, _ = _select_calendar_arrays(series, cfg.timezone)

    ema9 = _nt8_ema(close, cfg.ema_period)
    atr_s = _nt8_atr(high, low, close, cfg.atr_length)
    atr_st = _nt8_atr(high, low, close, cfg.st_period)
    adx_s = _nt8_adx(high, low, close, cfg.adx_period)
    bias_ema = _nt8_ema(close, cfg.bias_ema_period) if cfg.use_vwap_ema_bias else None

    tracker = _ModuleExecutionTracker(
        module_tag="S",
        m1=ms.bip1,
        tick_size=ms.tick_size,
        point_value=ms.point_value,
        loss_cooldown_bars=cfg.loss_cooldown_bars,
        commission_rt=cfg.virtual_round_turn_commission,
    )

    last_day = -1
    closed_today = False
    cum_pv = 0.0
    cum_vol = 0.0
    prev_ema = 0.0
    prev_vwap = 0.0

    regime_len = max(1, int(cfg.regime_atr_lookback))
    atr_regime = [0.0] * regime_len
    atr_regime_idx = 0

    st_init = False
    final_upper = 0.0
    final_lower = 0.0
    prev_final_upper = 0.0
    prev_final_lower = 0.0
    prev_close = 0.0
    trend = 1
    prev_trend = 1

    bar_minutes = series.timeframe_min if series.timeframe_min > 0 else 1
    ny_open_min = cfg.ny_open_hour * 60 + cfg.ny_open_minute
    close_min = cfg.close_hour * 60 + cfg.close_minute
    req_bars = max(0, int(cfg.bars_required_to_trade))

    n_bars = len(close)
    for j in range(n_bars):
        if j < req_bars:
            continue

        e_j = int(m1_end_idx[j])
        tracker.advance_to(e_j)
        cooldown_ok = tracker.consume_loss_cooldown()

        d_day = int(cal_date[j]) % 100
        if d_day != last_day:
            last_day = d_day
            closed_today = False

        if bool(is_new_session[j]):
            cum_pv = 0.0
            cum_vol = 0.0

        hi_j = float(high[j])
        lo_j = float(low[j])
        cl_j = float(close[j])
        vol_j = float(volume[j])

        # Swas acumula Close * Volume para su VWAP de sesion
        cum_pv += cl_j * vol_j
        cum_vol += vol_j
        vwap = (cum_pv / cum_vol) if cum_vol > 0.0 else cl_j

        ema9_val = float(ema9[j])
        cross_up = (prev_ema <= prev_vwap) and (ema9_val > vwap)
        cross_down = (prev_ema >= prev_vwap) and (ema9_val < vwap)

        hhmm = int(hhmmss[j]) // 100
        bar_hour = hhmm // 100
        bar_min = hhmm % 100
        open_min = (bar_hour * 60 + bar_min - bar_minutes) % 1440

        if cfg.use_time_filter:
            is_blocked = (ny_open_min - cfg.pre_block_min) <= open_min < (ny_open_min + cfg.post_block_min)
        else:
            is_blocked = False

        after_eod = open_min >= close_min
        if cfg.use_eod_close and after_eod:
            is_blocked = True

        atr_val = float(atr_s[j])
        if cfg.use_regime_filter:
            atr_regime[atr_regime_idx % regime_len] = atr_val
            atr_regime_idx += 1
            r_cnt = min(atr_regime_idx, regime_len)
            avg_atr = sum(atr_regime[:r_cnt]) / r_cnt if r_cnt > 0 else 0.0
            if avg_atr > 0.0 and atr_val > avg_atr * cfg.regime_atr_multiplier:
                is_blocked = True

        final_upper, final_lower, trend, st_init = _supertrend_step(
            hi_j,
            lo_j,
            cl_j,
            float(atr_st[j]),
            cfg.st_mult,
            st_init,
            prev_final_upper,
            prev_final_lower,
            prev_close,
            prev_trend,
        )
        st_flip_up = trend == 1 and prev_trend == -1
        st_flip_down = trend == -1 and prev_trend == 1
        st_align_long = (trend == 1) if cfg.require_supertrend_entry_alignment else True
        st_align_short = (trend == -1) if cfg.require_supertrend_entry_alignment else True

        adx_ok = (float(adx_s[j]) >= cfg.adx_threshold) if cfg.use_adx_filter else True
        if cfg.use_vwap_ema_bias and bias_ema is not None:
            b_ema = float(bias_ema[j])
            bias_long = vwap > b_ema
            bias_short = vwap < b_ema
        else:
            bias_long = True
            bias_short = True

        ema_slope = (ema9_val - float(ema9[j - 1])) if j > 0 else 0.0
        if cfg.min_ema_slope_atr > 0.0:
            slope_long = atr_val > 0.0 and ema_slope >= cfg.min_ema_slope_atr * atr_val
            slope_short = atr_val > 0.0 and (-ema_slope) >= cfg.min_ema_slope_atr * atr_val
        else:
            slope_long = True
            slope_short = True

        pos = tracker.pos
        daily_close_blocked = (
            _is_daily_futures_close_blocked(
                int(ms.bip1.hhmmss_ct[e_j]),
                int(ms.bip1.dow_ct[e_j]),
                cfg.daily_futures_flatten_time_central,
                cfg.daily_futures_resume_time_central,
            )
            if cfg.flatten_before_daily_futures_close
            else False
        )
        if daily_close_blocked and pos != _POS_FLAT:
            tracker.request_exit("DAILY_FUTURES_CLOSE", e_j)
        elif cfg.exit_on_st_flip and pos == _POS_LONG and st_flip_down:
            tracker.request_exit("ST", e_j)
        elif cfg.exit_on_st_flip and pos == _POS_SHORT and st_flip_up:
            tracker.request_exit("ST", e_j)

        allow_long_hour = (bar_hour != cfg.blocked_long_entry_hour) if cfg.block_long_entry_hour_enabled else True
        allow_short_hour = (bar_hour != cfg.blocked_short_entry_hour) if cfg.block_short_entry_hour_enabled else True

        long_trig = (
            (not daily_close_blocked)
            and cfg.allow_longs
            and cross_up
            and not is_blocked
            and adx_ok
            and bias_long
            and st_align_long
            and slope_long
            and allow_long_hour
        )
        short_trig = (
            (not daily_close_blocked)
            and cfg.allow_shorts
            and cross_down
            and not is_blocked
            and adx_ok
            and bias_short
            and st_align_short
            and slope_short
            and allow_short_hour
        )

        if long_trig and cooldown_ok and tracker.can_enter():
            sl = (cl_j - cfg.hard_stop_atr_mult * atr_val) if cfg.use_hard_stop else math.nan
            tracker.request_entry(+1, qty, sl, math.nan, e_j)
        elif short_trig and cooldown_ok and tracker.can_enter():
            sl = (cl_j + cfg.hard_stop_atr_mult * atr_val) if cfg.use_hard_stop else math.nan
            tracker.request_entry(-1, qty, sl, math.nan, e_j)

        if cfg.use_eod_close and after_eod and not closed_today and pos != _POS_FLAT:
            tracker.request_exit("EOD", e_j)
            closed_today = True

        prev_ema = ema9_val
        prev_vwap = vwap
        prev_final_upper = final_upper
        prev_final_lower = final_lower
        prev_close = cl_j
        prev_trend = trend

    tracker.advance_to(len(ms.bip1.close) - 1)
    return trades_to_df(tracker.trades)


# ---------------------------------------------------------------------------
# Wrappers estilo EdgeLab
# ---------------------------------------------------------------------------


def _df_to_edgelab_signals(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convierte el DataFrame `TRADE_COLUMNS` en lista de dicts estilo EdgeLab."""
    if df.empty:
        return []
    signals: List[Dict[str, Any]] = []
    for row in df.itertuples(index=False):
        ep = float(row.entry_price)
        tp = float(row.target_price)
        sp = float(row.stop_price)
        exit_name = str(row.exit_name)
        signals.append(
            {
                "available_at": int(row.entry_time_utc),
                "dir": int(row.side),
                "entry_price": ep,
                "target_pts": None if math.isnan(tp) else abs(tp - ep),
                "stop_pts": None if math.isnan(sp) else abs(ep - sp),
                "time_stop_min": int(row.bars) if exit_name in ("ST", "SESSION", "EOD") else None,
                "reason": f"{row.entry_name}->{exit_name}",
            }
        )
    return signals


def senales_a1(
    ms: MultiSeriesContext,
    qty: int = 1,
    cfg: Optional[Absorb1mConfig] = None,
) -> List[Dict[str, Any]]:
    """Wrapper estilo EdgeLab para A1."""
    return _df_to_edgelab_signals(run_a1(ms, qty=qty, cfg=cfg))


def senales_a20(
    ms: MultiSeriesContext,
    qty: int = 2,
    cfg: Optional[Absorb20mConfig] = None,
) -> List[Dict[str, Any]]:
    """Wrapper estilo EdgeLab para A20."""
    return _df_to_edgelab_signals(run_a20(ms, qty=qty, cfg=cfg))


def senales_f(
    ms: MultiSeriesContext,
    qty: int = 1,
    cfg: Optional[FabioConfig] = None,
) -> List[Dict[str, Any]]:
    """Wrapper estilo EdgeLab para FabioOrb (F)."""
    return _df_to_edgelab_signals(run_f(ms, qty=qty, cfg=cfg))


def senales_s(
    ms: MultiSeriesContext,
    qty: int = 1,
    cfg: Optional[SwasConfig] = None,
) -> List[Dict[str, Any]]:
    """Wrapper estilo EdgeLab para Swas (S)."""
    return _df_to_edgelab_signals(run_s(ms, qty=qty, cfg=cfg))


__all__ = [
    "Absorb1mConfig",
    "Absorb20mConfig",
    "FabioConfig",
    "SwasConfig",
    "run_a1",
    "run_a20",
    "run_f",
    "run_s",
    "senales_a1",
    "senales_a20",
    "senales_f",
    "senales_s",
]
