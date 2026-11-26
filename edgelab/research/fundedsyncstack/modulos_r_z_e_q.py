"""Traduccion fiel a Python de los submodulos Lote 4 (R, Z, E, Q) de FUNDEDSYNCSTACK5.dll.

Modulos incluidos:
- R: AtrPhase (`RunAtrPhase`, `ms.bip9` 10m ETH)
- Z: ZetaTrendDay (`RunZeta`, `ms.bip1` 1m ETH)
- E: EmaDivergence (`RunEmaDivergence`, `ms.bip10` 15m ETH)
- Q: Rampart5Minute (`RunRampart`, `ms.bip3` 5m ETH)

Todas las reglas, constantes, umbrales, secuencias de estado, redondeos y ordenes
de ejecucion fueron extraidos directamente del desensamblado IL de FUNDEDSYNCSTACK5.dll.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import math
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from .contracts import (
        BarSeries,
        MultiSeriesContext,
        POINT_VALUE_MNQ,
        TICK_SIZE_NQ,
        TradeRecord,
        round_tick,
        trades_to_df,
    )
except ImportError:  # pragma: no cover
    from contracts import (
        BarSeries,
        MultiSeriesContext,
        POINT_VALUE_MNQ,
        TICK_SIZE_NQ,
        TradeRecord,
        round_tick,
        trades_to_df,
    )

_NS_PER_MIN: int = 60_000_000_000

# =============================================================================
# Tablas estaticas extraidas de FUNDEDSYNCSTACK..cctor / static_arrays.json
# =============================================================================

ATR_PHASE_BLOCKED_SESSIONS: Tuple[int, ...] = (
    20220803,
    20220830,
    20230405,
    20240704,
    20241224,
    20250120,
    20250703,
    20250829,
)

ZETA_NON_FULL_NYSE: Tuple[int, ...] = (
    20100101, 20100118, 20100215, 20100402, 20100531, 20100705, 20100906, 20101125,
    20101126, 20101224, 20110117, 20110221, 20110422, 20110530, 20110704, 20110905,
    20111124, 20111125, 20111226, 20120102, 20120116, 20120220, 20120406, 20120528,
    20120703, 20120704, 20120903, 20121029, 20121030, 20121122, 20121123, 20121224,
    20121225, 20130101, 20130121, 20130218, 20130329, 20130527, 20130703, 20130704,
    20130902, 20131128, 20131129, 20131224, 20131225, 20140101, 20140120, 20140217,
    20140418, 20140526, 20140703, 20140704, 20140901, 20141127, 20141128, 20141224,
    20141225, 20150101, 20150119, 20150216, 20150403, 20150525, 20150703, 20150907,
    20151126, 20151127, 20151224, 20151225, 20160101, 20160118, 20160215, 20160325,
    20160530, 20160704, 20160905, 20161124, 20161125, 20161226, 20170102, 20170116,
    20170220, 20170414, 20170529, 20170703, 20170704, 20170904, 20171123, 20171124,
    20171225, 20180101, 20180115, 20180219, 20180330, 20180528, 20180703, 20180704,
    20180903, 20181122, 20181123, 20181205, 20181224, 20181225, 20190101, 20190121,
    20190218, 20190419, 20190527, 20190703, 20190704, 20190902, 20191128, 20191129,
    20191224, 20191225, 20200101, 20200120, 20200217, 20200410, 20200525, 20200703,
    20200907, 20201126, 20201127, 20201224, 20201225, 20210101, 20210118, 20210215,
    20210402, 20210531, 20210705, 20210906, 20211125, 20211126, 20211224, 20220117,
    20220221, 20220415, 20220530, 20220620, 20220704, 20220905, 20221124, 20221125,
    20221226, 20230102, 20230116, 20230220, 20230407, 20230529, 20230619, 20230703,
    20230704, 20230904, 20231123, 20231124, 20231225, 20240101, 20240115, 20240219,
    20240329, 20240527, 20240619, 20240703, 20240704, 20240902, 20241128, 20241129,
    20241224, 20241225, 20250101, 20250109, 20250120, 20250217, 20250418, 20250526,
    20250619, 20250703, 20250704, 20250901, 20251127, 20251128, 20251224, 20251225,
    20260101, 20260119, 20260216, 20260403, 20260525, 20260619, 20260703, 20260907,
    20261126, 20261127, 20261224, 20261225, 20270101, 20270118, 20270215, 20270326,
    20270531, 20270618, 20270705,
)


# =============================================================================
# Dataclasses de configuracion (defaults exactos del IL)
# =============================================================================

@dataclass
class AtrPhaseConfig:
    """Parametros exactos de AtrPhase (modulo R, bip9 10m ETH)."""

    ema_period: int = 21                    # alpha = 2 / (21 + 1) = 0.09090909090909091
    atr_period: int = 14                    # Wilder ATR(14) sembrado con SMA(14)
    osc_scale: float = 100.0
    osc_atr_mult: float = 3.0               # raw = 100 * (close - ema21) / (3 * atr14)
    osc_smooth_alpha: float = 0.5           # rOsc = 0.5 * raw + 0.5 * rOsc
    upper_threshold: float = 100.0          # cruce alcista: prev <= 100 and now > 100
    lower_threshold: float = -100.0         # cruce bajista: prev >= -100 and now < -100
    entry_start_min_et: int = 570           # 09:30 ET (close de barra)
    entry_end_min_et: int = 660             # 11:00 ET (exclusivo, close de barra)
    rth_vwap_start_min_et: int = 570        # 09:30 ET (apertura de barra)
    rth_vwap_end_min_et: int = 960          # 16:00 ET (exclusivo, apertura de barra)
    vwap_atr_mult: float = 2.5              # |close - vwap| < 2.5 * rAtr14
    cash_close_min_et: int = 960            # 16:00 ET (close de barra) -> CASH_CLOSE
    roll_gap_ticks: float = 400.0           # |open - prevClose| > 400 * tick_size a 00:00 UTC
    blocked_sessions: Tuple[int, ...] = ATR_PHASE_BLOCKED_SESSIONS


@dataclass
class ZetaConfig:
    """Parametros exactos de ZetaTrendDay (modulo Z, bip1 1m ETH)."""

    session_start_min_ct: int = 510         # 08:30 CT (09:30 ET)
    session_end_min_ct: int = 900           # 15:00 CT (16:00 ET) -> 390 min
    bucket_minutes: int = 15                # 15m buckets (26 buckets por sesion)
    ema_period: int = 20                    # alpha = 2 / 21, semilla SMA(20)
    min_efficiency_pct: float = 45.0        # 100 * |C - O| / (H - L) >= 45.0
    min_date_key: int = 20100101
    max_date_key: int = 20270902
    non_full_nyse: Tuple[int, ...] = ZETA_NON_FULL_NYSE


@dataclass
class EmaDivConfig:
    """Parametros exactos de EmaDivergence (modulo E, bip10 15m ETH)."""

    fast_period: int = 9
    slow_period: int = 11
    trend_period: int = 45
    rolling_window: int = 20                # capacidad de eVolumes, eRanges, eCvdHistory
    warmup_bars: int = 47                   # CurrentBars[10] >= 47
    absorption_min_count: int = 10          # max(10, capacity // 2)
    absorption_vol_z_thresh: float = 1.0    # si z_vol >= 1.0, requiere z_rng > 0.0
    absorption_range_z_thresh: float = 0.0
    cvd_min_count: int = 3
    cvd_z_thresh: float = 0.1               # |cvd_z| >= 0.1 y mismo signo que direction
    stop_points: float = 30.0
    target_points: float = 45.0
    historical_minute14_delay: bool = True  # True: State.Historical (+14m), False: Realtime
    delay_minutes: int = 14
    flatten_before_daily_futures_close: bool = True
    daily_futures_flatten_time_central: int = 154400
    daily_futures_resume_time_central: int = 170100


@dataclass
class RampartConfig:
    """Parametros exactos de Rampart5Minute (modulo Q, bip3 5m ETH)."""

    range_start_hour: int = 9
    range_start_minute: int = 15
    range_end_hour: int = 9
    range_end_minute: int = 50
    break_margin_ticks: int = 6
    stop_buffer_ticks: int = 1
    risk_reward: float = 0.30
    last_entry_hour: int = 12
    last_entry_minute: int = 0
    force_close_hour: int = 16
    force_close_minute: int = 0
    one_trade_per_side: bool = True
    min_bars_between_trades: int = 1
    risk_usd: float = 500.0                 # BaseRampartRiskUsd (50K profile = 200.0)
    max_contracts: int = 60                 # BaseRampartMaxContracts (50K profile = 28)
    sizing_point_value: Optional[float] = None


# =============================================================================
# Helpers comunes de tiempo, ejecucion 1m y estructuras auxiliares
# =============================================================================

def _tz_fields(
    ts_ns: np.ndarray,
    tz_name: str,
    shift_minutes: int = 0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Convierte ts_ns UTC (ns) a (yyyymmdd, min_of_day, dow_0_mon, hour, minute) en tz_name."""
    if len(ts_ns) == 0:
        empty_i = np.zeros(0, dtype=np.int64)
        return empty_i, empty_i, empty_i, empty_i, empty_i
    shifted = ts_ns.astype(np.int64) + int(shift_minutes) * _NS_PER_MIN
    dt_utc = pd.to_datetime(shifted, unit="ns", utc=True)
    dt_tz = dt_utc if tz_name == "UTC" else dt_utc.tz_convert(tz_name)
    years = dt_tz.year.to_numpy(dtype=np.int64)
    months = dt_tz.month.to_numpy(dtype=np.int64)
    days = dt_tz.day.to_numpy(dtype=np.int64)
    hours = dt_tz.hour.to_numpy(dtype=np.int64)
    minutes = dt_tz.minute.to_numpy(dtype=np.int64)
    dows = dt_tz.dayofweek.to_numpy(dtype=np.int64)
    date_key = years * 10000 + months * 100 + days
    min_of_day = hours * 60 + minutes
    return date_key, min_of_day, dows, hours, minutes


class _PendingEntry:
    __slots__ = (
        "side",
        "qty",
        "stop_price",
        "target_price",
        "stop_dist",
        "target_dist",
        "entry_name",
    )

    def __init__(
        self,
        side: int,
        qty: int,
        stop_price: float,
        target_price: float,
        stop_dist: float,
        target_dist: float,
        entry_name: str,
    ) -> None:
        self.side = side
        self.qty = qty
        self.stop_price = stop_price
        self.target_price = target_price
        self.stop_dist = stop_dist
        self.target_dist = target_dist
        self.entry_name = entry_name


class _ModuleExecTracker:
    """Simulador de ordenes no gestionadas (1m ETH) fiel a Calculate.OnBarClose."""

    def __init__(self, module: str, tick_size: float, point_value: float) -> None:
        self.module = module
        self.tick_size = tick_size
        self.point_value = point_value
        self.trades: List[TradeRecord] = []

        self.net: int = 0
        self.side: int = 0
        self.qty: int = 0
        self.entry_time_utc: int = 0
        self.entry_m1_idx: int = 0
        self.entry_price: float = 0.0
        self.entry_name: str = ""

        self.active_stop: float = math.nan
        self.active_target: float = math.nan
        self.record_stop: float = math.nan
        self.record_target: float = math.nan
        self.mae_pts: float = 0.0
        self.mfe_pts: float = 0.0

        self.pending_entry: Optional[_PendingEntry] = None
        self.pending_exit: Optional[str] = None

    @property
    def is_open(self) -> bool:
        return self.net != 0

    @property
    def can_enter(self) -> bool:
        return self.net == 0 and self.pending_entry is None and self.pending_exit is None

    def request_entry(
        self,
        side: int,
        qty: int,
        stop_price: float = math.nan,
        target_price: float = math.nan,
        stop_dist: float = math.nan,
        target_dist: float = math.nan,
    ) -> None:
        if not self.can_enter or qty <= 0 or side == 0:
            return
        sgn = 1 if side > 0 else -1
        ename = f"{self.module}_E_L" if sgn > 0 else f"{self.module}_E_S"
        self.pending_entry = _PendingEntry(
            side=sgn,
            qty=int(qty),
            stop_price=stop_price,
            target_price=target_price,
            stop_dist=stop_dist,
            target_dist=target_dist,
            entry_name=ename,
        )

    def request_exit(self, reason: str) -> None:
        if self.net == 0 or self.pending_exit is not None:
            return
        # En ExitModule se cancela la proteccion viva al enviar la salida de mercado.
        self.active_stop = math.nan
        self.active_target = math.nan
        self.pending_exit = reason

    def update_target(self, new_target: float) -> None:
        if self.net == 0 or math.isnan(new_target) or self.pending_exit is not None:
            return
        rounded = round_tick(new_target, self.tick_size)
        self.active_target = rounded
        self.record_target = rounded

    def _close_trade(self, m1_idx: int, ts_ns: int, exit_price: float, exit_name: str) -> None:
        pnl_pts = (exit_price - self.entry_price) * self.side
        dollar_mult = self.qty * self.point_value
        self.trades.append(
            TradeRecord(
                module=self.module,
                side=self.side,
                qty=self.qty,
                entry_time_utc=self.entry_time_utc,
                exit_time_utc=int(ts_ns),
                entry_price=self.entry_price,
                exit_price=float(exit_price),
                stop_price=self.record_stop,
                target_price=self.record_target,
                entry_name=self.entry_name,
                exit_name=exit_name,
                pnl_pts=float(pnl_pts),
                pnl_usd=float(pnl_pts * dollar_mult),
                mae_usd=float(max(0.0, self.mae_pts) * dollar_mult),
                mfe_usd=float(max(0.0, self.mfe_pts) * dollar_mult),
                bars=max(1, m1_idx - self.entry_m1_idx + 1),
            )
        )
        self.net = 0
        self.side = 0
        self.qty = 0
        self.active_stop = math.nan
        self.active_target = math.nan
        self.record_stop = math.nan
        self.record_target = math.nan
        self.mae_pts = 0.0
        self.mfe_pts = 0.0

    def on_bar_open(self, m1_idx: int, ts_ns: int, bar_open: float) -> bool:
        """Procesa ordenes Market pendientes en la apertura de la barra 1m. Devuelve True si cerro en apertura."""
        if self.pending_exit is not None and self.net != 0:
            reason = self.pending_exit
            self.pending_exit = None
            adv = self.side * (self.entry_price - bar_open)
            fav = self.side * (bar_open - self.entry_price)
            if adv > self.mae_pts:
                self.mae_pts = adv
            if fav > self.mfe_pts:
                self.mfe_pts = fav
            self._close_trade(m1_idx, ts_ns, bar_open, reason)
            return True

        if self.pending_entry is not None and self.net == 0:
            pe = self.pending_entry
            self.pending_entry = None
            self.side = pe.side
            self.qty = pe.qty
            self.net = pe.side * pe.qty
            self.entry_time_utc = int(ts_ns)
            self.entry_m1_idx = m1_idx
            self.entry_price = float(bar_open)
            self.entry_name = pe.entry_name
            self.mae_pts = 0.0
            self.mfe_pts = 0.0

            stop_p = pe.stop_price
            if not math.isnan(pe.stop_dist):
                stop_p = (
                    self.entry_price - pe.stop_dist
                    if self.side > 0
                    else self.entry_price + pe.stop_dist
                )
            if not math.isnan(stop_p):
                stop_p = round_tick(stop_p, self.tick_size)

            target_p = pe.target_price
            if not math.isnan(pe.target_dist):
                target_p = (
                    self.entry_price + pe.target_dist
                    if self.side > 0
                    else self.entry_price - pe.target_dist
                )
            if not math.isnan(target_p):
                target_p = round_tick(target_p, self.tick_size)

            self.active_stop = stop_p
            self.active_target = target_p
            self.record_stop = stop_p
            self.record_target = target_p
        return False

    def on_bar_intrabar(
        self,
        m1_idx: int,
        ts_ns: int,
        bar_open: float,
        bar_high: float,
        bar_low: float,
    ) -> None:
        """Evalua StopMarket / Limit activos intrabar sobre la barra 1m (prioridad conservadora a STOP)."""
        if self.net == 0:
            return

        has_stop = not math.isnan(self.active_stop)
        has_target = not math.isnan(self.active_target)

        if self.side > 0:
            if has_stop and bar_low <= self.active_stop:
                fill = min(bar_open, self.active_stop)
                self.mae_pts = max(self.mae_pts, self.entry_price - fill)
                self.mfe_pts = max(self.mfe_pts, bar_open - self.entry_price)
                self._close_trade(m1_idx, ts_ns, fill, "STOP")
                return
            if has_target and bar_high >= self.active_target:
                fill = max(bar_open, self.active_target)
                self.mae_pts = max(self.mae_pts, self.entry_price - bar_open)
                self.mfe_pts = max(self.mfe_pts, fill - self.entry_price)
                self._close_trade(m1_idx, ts_ns, fill, "TARGET")
                return
            self.mae_pts = max(self.mae_pts, self.entry_price - bar_low)
            self.mfe_pts = max(self.mfe_pts, bar_high - self.entry_price)
        else:
            if has_stop and bar_high >= self.active_stop:
                fill = max(bar_open, self.active_stop)
                self.mae_pts = max(self.mae_pts, fill - self.entry_price)
                self.mfe_pts = max(self.mfe_pts, self.entry_price - bar_open)
                self._close_trade(m1_idx, ts_ns, fill, "STOP")
                return
            if has_target and bar_low <= self.active_target:
                fill = min(bar_open, self.active_target)
                self.mae_pts = max(self.mae_pts, bar_open - self.entry_price)
                self.mfe_pts = max(self.mfe_pts, self.entry_price - fill)
                self._close_trade(m1_idx, ts_ns, fill, "TARGET")
                return
            self.mae_pts = max(self.mae_pts, bar_high - self.entry_price)
            self.mfe_pts = max(self.mfe_pts, self.entry_price - bar_low)


# =============================================================================
# Modulo R: AtrPhase (ms.bip9 10m ETH)
# =============================================================================

class _AtrPhaseEngine:
    """Estado e indicador exacto de AtrPhase."""

    def __init__(self, cfg: AtrPhaseConfig, tick_size: float) -> None:
        self.cfg = cfg
        self.tick_size = tick_size
        self.blocked_set = frozenset(cfg.blocked_sessions)
        self.ema_alpha = 2.0 / (float(cfg.ema_period) + 1.0)
        self.reset_state()

    def reset_state(self) -> None:
        self.r_prev_close_ready: bool = False
        self.r_osc_ready: bool = False
        self.r_atr_ready: bool = False
        self.r_ema_ready: bool = False
        self.r_tr_seed_sum: float = 0.0
        self.r_prev_decision_close: float = 0.0
        self.r_osc: float = 0.0
        self.r_atr14: float = 0.0
        self.r_ema21: float = 0.0
        self.r_pending_reversal_side: int = 0
        self.r_shadow_side: int = 0
        self.r_tr_seed_count: int = 0
        self.r_vwap_date: int = -1
        self.r_vwap_vol: float = 0.0
        self.r_vwap_pv: float = 0.0

    def update_indicator(self, high: float, low: float, close: float) -> bool:
        """Traduccion exacta de UpdateAtrPhaseIndicator(high, low, close)."""
        alpha = self.ema_alpha
        if not self.r_ema_ready:
            self.r_ema21 = close
            self.r_ema_ready = True
        else:
            self.r_ema21 = alpha * close + (1.0 - alpha) * self.r_ema21

        if not self.r_prev_close_ready:
            tr = high - low
        else:
            tr = max(
                high - low,
                max(
                    abs(high - self.r_prev_decision_close),
                    abs(low - self.r_prev_decision_close),
                ),
            )
        self.r_prev_decision_close = close
        self.r_prev_close_ready = True

        n_atr = self.cfg.atr_period
        if not self.r_atr_ready:
            self.r_tr_seed_count += 1
            self.r_tr_seed_sum += tr
            if self.r_tr_seed_count == n_atr:
                self.r_atr14 = self.r_tr_seed_sum / float(n_atr)
                self.r_atr_ready = True
        else:
            self.r_atr14 = (float(n_atr - 1) * self.r_atr14 + tr) / float(n_atr)

        if not self.r_atr_ready or self.r_atr14 <= 0.0 or math.isnan(self.r_atr14):
            return False

        raw_osc = (self.cfg.osc_scale * (close - self.r_ema21)) / (
            self.cfg.osc_atr_mult * self.r_atr14
        )
        if not self.r_osc_ready:
            self.r_osc = raw_osc
            self.r_osc_ready = True
        else:
            a_osc = self.cfg.osc_smooth_alpha
            self.r_osc = a_osc * raw_osc + (1.0 - a_osc) * self.r_osc
        return True


def run_r(
    ms: MultiSeriesContext,
    qty: int = 1,
    cfg: Optional[AtrPhaseConfig] = None,
) -> pd.DataFrame:
    """Ejecuta AtrPhase (modulo R) sobre ms.bip9 (10m ETH) con ejecucion en ms.bip1."""
    cfg = cfg or AtrPhaseConfig()
    if qty <= 0 or len(ms.bip1.ts_ns) == 0 or len(ms.bip9.ts_ns) == 0:
        return trades_to_df([])

    b1 = ms.bip1
    b9 = ms.bip9
    n1 = len(b1.ts_ns)
    n9 = len(b9.ts_ns)

    _, close_min_et, _, _, _ = _tz_fields(b9.ts_ns, "America/New_York", 0)
    open_date_et, open_min_et, _, _, _ = _tz_fields(b9.ts_ns, "America/New_York", -10)
    _, _, _, open_utc_h, open_utc_m = _tz_fields(b9.ts_ns, "UTC", -10)

    tracker = _ModuleExecTracker("R", ms.tick_size, ms.point_value)
    eng = _AtrPhaseEngine(cfg, ms.tick_size)

    def _on_bip9_bar(k: int) -> None:
        if k < 1:
            return

        sess_date = int(open_date_et[k])
        if sess_date in eng.blocked_set:
            eng.r_shadow_side = 0
            eng.r_pending_reversal_side = 0
            if tracker.is_open:
                tracker.request_exit("INCOMPLETE_SESSION")
            return

        op = float(b9.open[k])
        hi = float(b9.high[k])
        lo = float(b9.low[k])
        cl = float(b9.close[k])
        vol = float(b9.volume[k])

        if (
            int(open_utc_h[k]) == 0
            and int(open_utc_m[k]) == 0
            and eng.r_prev_close_ready
            and abs(op - eng.r_prev_decision_close) > cfg.roll_gap_ticks * ms.tick_size
        ):
            had_shadow = eng.r_shadow_side != 0
            eng.reset_state()
            if had_shadow and tracker.is_open:
                tracker.request_exit("ROLL_RESET")

        prev_osc = eng.r_osc
        prev_osc_ready = eng.r_osc_ready
        osc_ready_now = eng.update_indicator(hi, lo, cl)

        vwap_ok = False
        op_min = int(open_min_et[k])
        if cfg.rth_vwap_start_min_et <= op_min < cfg.rth_vwap_end_min_et:
            if eng.r_vwap_date != sess_date:
                eng.r_vwap_date = sess_date
                eng.r_vwap_vol = 0.0
                eng.r_vwap_pv = 0.0
            typical = (hi + lo + cl) / 3.0
            eng.r_vwap_pv += typical * vol
            eng.r_vwap_vol += vol
            if eng.r_vwap_vol > 0.0 and eng.r_atr_ready:
                vwap = eng.r_vwap_pv / eng.r_vwap_vol
                vwap_ok = abs(cl - vwap) < cfg.vwap_atr_mult * eng.r_atr14

        cl_min = int(close_min_et[k])
        if cl_min == cfg.cash_close_min_et:
            eng.r_shadow_side = 0
            eng.r_pending_reversal_side = 0
            if tracker.is_open:
                tracker.request_exit("CASH_CLOSE")
            return

        if not prev_osc_ready or not osc_ready_now:
            return

        bull_cross = (not math.isnan(prev_osc)) and (prev_osc <= cfg.upper_threshold) and (eng.r_osc > cfg.upper_threshold)
        bear_cross = (not math.isnan(prev_osc)) and (prev_osc >= cfg.lower_threshold) and (eng.r_osc < cfg.lower_threshold)
        if not bull_cross and not bear_cross:
            return

        new_side = 1 if bull_cross else -1
        if eng.r_shadow_side == new_side:
            return

        in_entry_window = cfg.entry_start_min_et <= cl_min < cfg.entry_end_min_et

        if eng.r_shadow_side == 0:
            if not in_entry_window:
                return
            eng.r_shadow_side = new_side
            if vwap_ok and tracker.can_enter:
                tracker.request_entry(new_side, qty)
            return

        if not in_entry_window:
            eng.r_shadow_side = 0
            eng.r_pending_reversal_side = 0
            if tracker.is_open:
                tracker.request_exit("OPPOSITE")
            return

        eng.r_shadow_side = new_side
        if tracker.is_open:
            eng.r_pending_reversal_side = new_side if vwap_ok else 0
            tracker.request_exit("REVERSAL")
            return

        if vwap_ok and tracker.can_enter:
            tracker.request_entry(new_side, qty)

    k9 = 0
    while k9 < n9 and int(b9.m1_end_idx[k9]) < 0:
        k9 += 1

    for m1 in range(n1):
        ts = int(b1.ts_ns[m1])
        op1 = float(b1.open[m1])
        closed_open = tracker.on_bar_open(m1, ts, op1)
        if not closed_open:
            tracker.on_bar_intrabar(m1, ts, op1, float(b1.high[m1]), float(b1.low[m1]))

        # OnBarUpdate(bip=1): TrySubmitAtrPhaseReversal() corre antes que RunAtrPhase(bip=9)
        if eng.r_pending_reversal_side != 0 and tracker.can_enter:
            rev_side = eng.r_pending_reversal_side
            eng.r_pending_reversal_side = 0
            tracker.request_entry(rev_side, qty)

        while k9 < n9 and int(b9.m1_end_idx[k9]) <= m1:
            _on_bip9_bar(k9)
            k9 += 1

    return trades_to_df(tracker.trades)


# =============================================================================
# Modulo Z: ZetaTrendDay (ms.bip1 1m ETH)
# =============================================================================

def is_full_zeta_session(
    key: int,
    non_full_set: frozenset[int],
    min_date_key: int = 20100101,
    max_date_key: int = 20270902,
) -> bool:
    """Traduccion exacta de IsFullZetaSession(long key)."""
    try:
        y = key // 10000
        m = (key // 100) % 100
        d = key % 100
        dt = date(y, m, d)
    except ValueError:
        return False
    if dt.weekday() >= 5:  # Sat=5, Sun=6
        return False
    if min_date_key <= key <= max_date_key:
        return key not in non_full_set
    return True


def next_full_zeta_session(
    key: int,
    non_full_set: frozenset[int],
    min_date_key: int = 20100101,
    max_date_key: int = 20270902,
) -> int:
    """Traduccion exacta de NextFullZetaSession(long key)."""
    try:
        dt = date(key // 10000, (key // 100) % 100, key % 100) + timedelta(days=1)
    except ValueError:
        return 0
    for _ in range(20):
        k = dt.year * 10000 + dt.month * 100 + dt.day
        if is_full_zeta_session(k, non_full_set, min_date_key, max_date_key):
            return k
        dt += timedelta(days=1)
    return 0


def round_zeta_target(side: int, price: float, tick_size: float = TICK_SIZE_NQ) -> float:
    """Traduccion exacta de RoundZetaTarget(int side, double price)."""
    if side <= 0:
        return math.floor(price / tick_size) * tick_size
    return math.ceil(price / tick_size) * tick_size


class _ZetaEngine:
    """Maquina de estado exacta de ZetaTrendDay."""

    def __init__(self, cfg: ZetaConfig) -> None:
        self.cfg = cfg
        self.ema_alpha = 2.0 / (float(cfg.ema_period) + 1.0)  # 2/21 = 0.09523809523809523
        self.z_ema_seed: List[float] = [0.0] * cfg.ema_period
        self.reset_state()

    def reset_bucket(self) -> None:
        self.z_bucket_active: bool = False
        self.z_bucket_index: int = -1
        self.z_bucket_count: int = 0
        self.z_bucket_valid: bool = True
        self.z_bucket_high: float = 0.0
        self.z_bucket_low: float = 0.0
        self.z_bucket_close: float = 0.0

    def reset_ema(self) -> None:
        self.z_ema_value: float = 0.0
        self.z_ema_ready: bool = False
        self.z_ema_seed_count: int = 0
        self.z_ema_seed = [0.0] * self.cfg.ema_period

    def reset_state(self) -> None:
        self.reset_ema()
        self.reset_bucket()
        self.z_session_active: bool = False
        self.z_session_date_key: int = 0
        self.z_session_valid: bool = False
        self.z_session_bucket_count: int = 0
        self.z_session_minute_count: int = 0
        self.z_session_open: float = 0.0
        self.z_session_high: float = 0.0
        self.z_session_low: float = 0.0
        self.z_session_close: float = 0.0
        self.z_session_ema_observable: bool = False
        self.z_session_touch_free: bool = False

        self.z_pending_entry: bool = False
        self.z_pending_entry_direction: int = 0
        self.z_pending_entry_target: float = 0.0
        self.z_pending_entry_session_key: int = 0

        self.z_pending_qualified: bool = False
        self.z_pending_summary_available: bool = False
        self.z_pending_session_date_key: int = 0

    def update_ema(self, close: float) -> None:
        if not (close > 0.0):
            return
        n_ema = self.cfg.ema_period
        if not self.z_ema_ready:
            if self.z_ema_seed_count < n_ema:
                self.z_ema_seed[self.z_ema_seed_count] = close
                self.z_ema_seed_count += 1
            if self.z_ema_seed_count == n_ema:
                self.z_ema_value = sum(self.z_ema_seed) / float(n_ema)
                self.z_ema_ready = True
            return
        self.z_ema_value = self.z_ema_value + self.ema_alpha * (close - self.z_ema_value)

    def start_session(self, key: int, op: float, hi: float, lo: float, cl: float) -> None:
        self.z_session_active = True
        self.z_session_date_key = key
        self.z_session_valid = True
        self.z_session_bucket_count = 0
        self.z_session_minute_count = 0
        self.z_session_open = op
        self.z_session_high = hi
        self.z_session_low = lo
        self.z_session_close = cl
        self.z_session_ema_observable = True
        self.z_session_touch_free = True
        self.reset_bucket()

    def finalize_session(self) -> None:
        if not self.z_session_active:
            return
        if self.z_bucket_active:
            self.z_session_valid = False
            self.reset_bucket()
            self.reset_ema()

        expected_minutes = self.cfg.session_end_min_ct - self.cfg.session_start_min_ct  # 390
        expected_buckets = expected_minutes // self.cfg.bucket_minutes                  # 26
        all_bars_valid = (
            self.z_session_valid
            and self.z_session_minute_count == expected_minutes
            and self.z_session_bucket_count == expected_buckets
        )
        session_range = self.z_session_high - self.z_session_low
        efficiency = (
            0.0
            if session_range <= 0.0
            else (100.0 * abs(self.z_session_close - self.z_session_open) / session_range)
        )
        self.z_pending_summary_available = True
        self.z_pending_qualified = (
            all_bars_valid
            and self.z_session_ema_observable
            and (session_range > 0.0)
            and self.z_session_touch_free
            and (efficiency >= self.cfg.min_efficiency_pct)
        )
        self.z_pending_session_date_key = self.z_session_date_key
        if not all_bars_valid:
            self.reset_ema()
        self.z_session_active = False
        self.reset_bucket()

    def update_bucket(self, minute_offset: int, hi: float, lo: float, cl: float) -> bool:
        b_size = self.cfg.bucket_minutes  # 15
        b_idx = minute_offset // b_size
        b_min = minute_offset % b_size

        if self.z_bucket_active and self.z_bucket_index != b_idx:
            self.z_session_valid = False
            self.reset_bucket()
            self.reset_ema()

        if not self.z_bucket_active:
            self.z_bucket_active = True
            self.z_bucket_index = b_idx
            self.z_bucket_count = 0
            self.z_bucket_valid = (b_min == 0) and (b_idx == self.z_session_bucket_count)
            self.z_bucket_high = hi
            self.z_bucket_low = lo
            self.z_bucket_close = cl
        else:
            self.z_bucket_high = max(self.z_bucket_high, hi)
            self.z_bucket_low = min(self.z_bucket_low, lo)
            self.z_bucket_close = cl

        if b_min != self.z_bucket_count:
            self.z_bucket_valid = False
        self.z_bucket_count += 1

        if b_min != b_size - 1:  # != 14
            return False

        if not self.z_bucket_valid or self.z_bucket_count != b_size:
            self.z_session_valid = False
            self.reset_ema()
            self.reset_bucket()
            return False

        if not self.z_ema_ready:
            self.z_session_ema_observable = False
        else:
            if self.z_bucket_low <= self.z_ema_value <= self.z_bucket_high:
                self.z_session_touch_free = False

        self.update_ema(self.z_bucket_close)
        self.z_session_bucket_count += 1
        self.reset_bucket()
        return True


def run_z(
    ms: MultiSeriesContext,
    qty: int = 2,
    cfg: Optional[ZetaConfig] = None,
) -> pd.DataFrame:
    """Ejecuta ZetaTrendDay (modulo Z) sobre ms.bip1 (1m ETH)."""
    cfg = cfg or ZetaConfig()
    if qty <= 0 or len(ms.bip1.ts_ns) == 0:
        return trades_to_df([])

    b1 = ms.bip1
    n1 = len(b1.ts_ns)
    open_date_ct, open_min_ct, _, _, _ = _tz_fields(b1.ts_ns, "America/Chicago", -1)
    non_full_set = frozenset(cfg.non_full_nyse)

    tracker = _ModuleExecTracker("Z", ms.tick_size, ms.point_value)
    eng = _ZetaEngine(cfg)

    for i in range(n1):
        ts = int(b1.ts_ns[i])
        op = float(b1.open[i])
        hi = float(b1.high[i])
        lo = float(b1.low[i])
        cl = float(b1.close[i])

        closed_open = tracker.on_bar_open(i, ts, op)
        if not closed_open:
            tracker.on_bar_intrabar(i, ts, op, hi, lo)

        if i < 1:
            continue

        key = int(open_date_ct[i])
        min_ct = int(open_min_ct[i])
        if (
            min_ct < cfg.session_start_min_ct
            or min_ct >= cfg.session_end_min_ct
            or not is_full_zeta_session(key, non_full_set, cfg.min_date_key, cfg.max_date_key)
        ):
            continue

        if not eng.z_session_active or eng.z_session_date_key != key:
            if eng.z_session_active:
                eng.finalize_session()

            if eng.z_pending_summary_available:
                nxt = next_full_zeta_session(
                    eng.z_pending_session_date_key,
                    non_full_set,
                    cfg.min_date_key,
                    cfg.max_date_key,
                )
                if nxt != key:
                    eng.reset_ema()
                    eng.z_pending_qualified = False
                    eng.z_pending_summary_available = False

            qualified_from_prev = eng.z_pending_summary_available and eng.z_pending_qualified
            eng.z_pending_qualified = False
            eng.z_pending_summary_available = False

            if tracker.is_open:
                tracker.request_exit("SESSION_SAFETY")

            eng.start_session(key, op, hi, lo, cl)

            if min_ct == cfg.session_start_min_ct and qualified_from_prev and eng.z_ema_ready:
                if op > eng.z_ema_value:
                    direction = -1
                elif op < eng.z_ema_value:
                    direction = 1
                else:
                    direction = 0
                if direction != 0:
                    eng.z_pending_entry = True
                    eng.z_pending_entry_direction = direction
                    eng.z_pending_entry_target = eng.z_ema_value
                    eng.z_pending_entry_session_key = key

        minute_offset = min_ct - cfg.session_start_min_ct
        if minute_offset != eng.z_session_minute_count:
            eng.z_session_valid = False
        eng.z_session_minute_count += 1
        eng.z_session_high = max(eng.z_session_high, hi)
        eng.z_session_low = min(eng.z_session_low, lo)
        eng.z_session_close = cl

        bucket_closed = eng.update_bucket(minute_offset, hi, lo, cl)

        if eng.z_pending_entry and min_ct == cfg.session_start_min_ct:
            if eng.z_pending_entry_direction <= 0:
                if not (lo > eng.z_pending_entry_target):
                    eng.z_pending_entry = False
            else:
                if not (hi < eng.z_pending_entry_target):
                    eng.z_pending_entry = False

        if (
            eng.z_pending_entry
            and min_ct == cfg.session_start_min_ct
            and key == eng.z_pending_entry_session_key
        ):
            still_valid = (
                (cl > eng.z_pending_entry_target)
                if eng.z_pending_entry_direction <= 0
                else (cl < eng.z_pending_entry_target)
            )
            if still_valid and tracker.can_enter:
                tgt = round_zeta_target(
                    eng.z_pending_entry_direction,
                    eng.z_pending_entry_target,
                    ms.tick_size,
                )
                tracker.request_entry(
                    eng.z_pending_entry_direction,
                    qty,
                    target_price=tgt,
                )
            eng.z_pending_entry = False
        elif eng.z_pending_entry and min_ct != cfg.session_start_min_ct:
            eng.z_pending_entry = False

        if bucket_closed and tracker.is_open:
            side_now = 1 if tracker.net > 0 else -1
            tracker.update_target(round_zeta_target(side_now, eng.z_ema_value, ms.tick_size))

        last_minute = cfg.session_end_min_ct - 1  # 899
        if min_ct >= last_minute and tracker.is_open:
            tracker.request_exit("EOD")
        if min_ct == last_minute:
            eng.finalize_session()

    return trades_to_df(tracker.trades)


# =============================================================================
# Modulo E: EmaDivergence (ms.bip10 15m ETH + RollingValues)
# =============================================================================

class RollingValues:
    """Traduccion exacta de la clase circular RollingValues de FUNDEDSYNCSTACK."""

    def __init__(self, size: int) -> None:
        cap = max(1, int(size))
        self._values: List[float] = [0.0] * cap
        self._next: int = 0
        self._count: int = 0

    @property
    def count(self) -> int:
        return self._count

    @property
    def capacity(self) -> int:
        return len(self._values)

    def push(self, value: float) -> None:
        cap = len(self._values)
        self._values[self._next] = float(value)
        self._next = (self._next + 1) % cap
        if self._count < cap:
            self._count += 1

    def get(self, bars_ago: int) -> float:
        cap = len(self._values)
        idx = ((self._next - 1 - bars_ago) % cap + cap) % cap
        return self._values[idx]

    def mean(self) -> float:
        if self._count == 0:
            return 0.0
        total = 0.0
        for i in range(self._count):
            total += self.get(i)
        return total / float(self._count)

    def standard_deviation(self) -> float:
        if self._count < 2:
            return 0.0
        mu = self.mean()
        sq = 0.0
        for i in range(self._count):
            d = self.get(i) - mu
            sq += d * d
        return math.sqrt(sq / float(self._count - 1))


def ema_step(previous: float, value: float, period: int, seed: bool) -> float:
    """Traduccion exacta de EmaStep(double previous, double value, int period, bool seed)."""
    if seed:
        return value
    k = 2.0 / (float(period) + 1.0)
    return previous + k * (value - previous)


class _EmaDivEngine:
    """Estado de EmaDivergence."""

    def __init__(self, cfg: EmaDivConfig) -> None:
        self.cfg = cfg
        self.e_fast_now: float = 0.0
        self.e_fast_prev: float = 0.0
        self.e_slow_now: float = 0.0
        self.e_slow_prev: float = 0.0
        self.e_trend_now: float = 0.0
        self.e_seeded: bool = False
        self.e_cvd: float = 0.0
        self.e_armed: int = 0
        self.e_pulled: bool = False
        self.e_volumes = RollingValues(cfg.rolling_window)
        self.e_ranges = RollingValues(cfg.rolling_window)
        self.e_cvd_history = RollingValues(cfg.rolling_window)
        self.e_hist_entry_pending: bool = False
        self.e_hist_entry_submit_ns: int = 0

    def absorption_allows(self) -> bool:
        min_cnt = max(self.cfg.absorption_min_count, self.e_volumes.capacity // 2)
        if self.e_volumes.count < min_cnt:
            return True
        vol_sd = self.e_volumes.standard_deviation()
        rng_sd = self.e_ranges.standard_deviation()
        if vol_sd <= 0.0 or rng_sd <= 0.0 or self.e_ranges.mean() <= 0.0:
            return True
        z_vol = (self.e_volumes.get(0) - self.e_volumes.mean()) / vol_sd
        z_rng = (self.e_ranges.get(0) - self.e_ranges.mean()) / rng_sd
        if math.isnan(z_vol) or z_vol < self.cfg.absorption_vol_z_thresh:
            return True
        if math.isnan(z_rng):
            return True
        return z_rng > self.cfg.absorption_range_z_thresh

    def cvd_allows(self, direction: int) -> bool:
        if self.e_cvd_history.count < self.cfg.cvd_min_count:
            return True
        cvd_sd = self.e_cvd_history.standard_deviation()
        if cvd_sd <= 0.0:
            cvd_z = 0.0
        else:
            cvd_z = (
                self.e_cvd_history.get(0)
                - self.e_cvd_history.get(self.e_cvd_history.count - 1)
            ) / cvd_sd
        if math.isnan(cvd_z) or abs(cvd_z) < self.cfg.cvd_z_thresh:
            return False
        if cvd_z > 0.0 and direction > 0:
            return True
        if cvd_z < 0.0 and direction < 0:
            return True
        return False


def run_e(
    ms: MultiSeriesContext,
    qty: int = 1,
    cfg: Optional[EmaDivConfig] = None,
) -> pd.DataFrame:
    """Ejecuta EmaDivergence (modulo E) sobre ms.bip10 (15m ETH) con ejecucion en ms.bip1."""
    cfg = cfg or EmaDivConfig()
    if qty <= 0 or len(ms.bip1.ts_ns) == 0 or len(ms.bip10.ts_ns) == 0:
        return trades_to_df([])

    b1 = ms.bip1
    b10 = ms.bip10
    n1 = len(b1.ts_ns)
    n10 = len(b10.ts_ns)

    tracker = _ModuleExecTracker("E", ms.tick_size, ms.point_value)
    eng = _EmaDivEngine(cfg)

    def _submit_or_queue_long(bar_ts_ns: int) -> None:
        if cfg.historical_minute14_delay:
            eng.e_hist_entry_pending = True
            eng.e_hist_entry_submit_ns = bar_ts_ns + cfg.delay_minutes * _NS_PER_MIN
            return
        if tracker.can_enter:
            tracker.request_entry(
                1,
                qty,
                stop_dist=cfg.stop_points,
                target_dist=cfg.target_points,
            )

    def _on_bip10_bar(k: int) -> None:
        cl = float(b10.close[k])
        hi = float(b10.high[k])
        lo = float(b10.low[k])
        vol = float(b10.volume[k])

        eng.e_fast_prev = eng.e_fast_now
        eng.e_slow_prev = eng.e_slow_now
        seed = not eng.e_seeded
        eng.e_fast_now = ema_step(eng.e_fast_now, cl, cfg.fast_period, seed)
        eng.e_slow_now = ema_step(eng.e_slow_now, cl, cfg.slow_period, seed)
        eng.e_trend_now = ema_step(eng.e_trend_now, cl, cfg.trend_period, seed)
        eng.e_seeded = True

        if k > 0:
            prev_cl = float(b10.close[k - 1])
            sign = 1 if cl > prev_cl else (-1 if cl < prev_cl else 0)
        else:
            sign = 0
        signed_vol = float(sign) * vol

        eng.e_volumes.push(vol)
        eng.e_ranges.push(max(hi - lo, 0.0))
        eng.e_cvd += signed_vol
        eng.e_cvd_history.push(eng.e_cvd)
        if bool(b10.is_new_session[k]):
            eng.e_cvd = 0.0

        if k < cfg.warmup_bars:
            return

        is_last_bar_of_session = (
            (k + 1 < n10 and bool(b10.is_new_session[k + 1]))
            or (k == n10 - 1 and int(b10.hhmmss_et[k]) == 170000)
        )
        if is_last_bar_of_session:
            if tracker.is_open:
                tracker.request_exit("SESSION_CLOSE")
            eng.e_armed = 0
            eng.e_pulled = False
            return

        if tracker.is_open:
            is_long = tracker.net > 0
            if (is_long and eng.e_fast_now < eng.e_slow_now) or (
                not is_long and eng.e_fast_now > eng.e_slow_now
            ):
                tracker.request_exit("OPPOSITE_CROSS")
            return

        bull_cross = (eng.e_fast_prev <= eng.e_slow_prev) and (eng.e_fast_now > eng.e_slow_now)
        bear_cross = (eng.e_fast_prev >= eng.e_slow_prev) and (eng.e_fast_now < eng.e_slow_now)
        if bull_cross and cl > eng.e_trend_now:
            eng.e_armed = 1
            eng.e_pulled = False
        elif bear_cross and cl < eng.e_trend_now:
            eng.e_armed = -1
            eng.e_pulled = False

        if eng.e_armed == 0:
            return

        if eng.e_armed > 0:
            if not eng.e_pulled:
                if cl < eng.e_fast_now:
                    eng.e_pulled = True
                return
            if not (cl > eng.e_fast_now and cl > eng.e_trend_now):
                return
            if not eng.absorption_allows() or not eng.cvd_allows(1):
                return
            eng.e_armed = 0
            eng.e_pulled = False
            _submit_or_queue_long(int(b10.ts_ns[k]))
            return

        # eArmed == -1: no envia entrada corta en IL; limpia armado tras pullback y quiebre
        if not eng.e_pulled:
            if cl > eng.e_fast_now:
                eng.e_pulled = True
            return
        if cl < eng.e_fast_now and cl < eng.e_trend_now:
            eng.e_armed = 0
            eng.e_pulled = False

    k10 = 0
    while k10 < n10 and int(b10.m1_end_idx[k10]) < 0:
        k10 += 1

    def _is_daily_close_blocked(t_ct: int, d_ct: int) -> bool:
        if not cfg.flatten_before_daily_futures_close:
            return False
        if d_ct == 5:  # Sabado
            return True
        if d_ct == 6:  # Domingo antes de 17:01 CT
            return t_ct < cfg.daily_futures_resume_time_central
        if d_ct == 4:  # Viernes >= 15:44 CT
            return t_ct >= cfg.daily_futures_flatten_time_central
        return cfg.daily_futures_flatten_time_central <= t_ct < cfg.daily_futures_resume_time_central

    for m1 in range(n1):
        ts = int(b1.ts_ns[m1])
        op1 = float(b1.open[m1])
        closed_open = tracker.on_bar_open(m1, ts, op1)
        if not closed_open:
            tracker.on_bar_intrabar(m1, ts, op1, float(b1.high[m1]), float(b1.low[m1]))

        daily_blocked = _is_daily_close_blocked(int(b1.hhmmss_ct[m1]), int(b1.dow_ct[m1]))
        if daily_blocked:
            if tracker.is_open:
                tracker.request_exit("DAILY_FUTURES_CLOSE")
            eng.e_hist_entry_pending = False
            eng.e_hist_entry_submit_ns = 0

        # OnBarUpdate(bip=1): TrySubmitHistoricalEmaEntry() corre antes que bip=10
        if (not daily_blocked) and eng.e_hist_entry_pending and ts >= eng.e_hist_entry_submit_ns:
            eng.e_hist_entry_pending = False
            eng.e_hist_entry_submit_ns = 0
            if tracker.can_enter:
                tracker.request_entry(
                    1,
                    qty,
                    stop_dist=cfg.stop_points,
                    target_dist=cfg.target_points,
                )

        while k10 < n10 and int(b10.m1_end_idx[k10]) <= m1:
            _on_bip10_bar(k10)
            if daily_blocked:
                eng.e_hist_entry_pending = False
                eng.e_hist_entry_submit_ns = 0
            k10 += 1

    return trades_to_df(tracker.trades)


# =============================================================================
# Modulo Q: Rampart5Minute (ms.bip3 5m ETH)
# =============================================================================

def rampart_quantity(
    stop_distance_points: float,
    risk_usd: float = 500.0,
    max_contracts: int = 60,
    point_value: float = 20.0,
    *,
    sizing_point_value: Optional[float] = None,
) -> int:
    """Traduccion exacta de RampartQuantity(double stopDistancePoints)."""
    if not (stop_distance_points > 0.0) or risk_usd <= 0.0 or max_contracts <= 0:
        return 0
    if sizing_point_value is not None:
        pv = sizing_point_value
    else:
        pv = point_value / 10.0 if point_value >= 10.0 else point_value
    if pv <= 0.0:
        pv = POINT_VALUE_MNQ
    risk_per_contract = stop_distance_points * pv
    raw = int(math.floor(risk_usd / risk_per_contract))
    return min(max_contracts, max(1, raw))


class _RampartEngine:
    """Estado por sesion y estado continuo de Rampart5Minute."""

    def __init__(self) -> None:
        self.q_current_session: Optional[int] = None
        self.q_last_trade_bar: Optional[int] = None
        self.q_prev_qual_long: bool = False
        self.q_prev_qual_short: bool = False
        self.reset_session()

    def reset_session(self) -> None:
        self.q_range_high: float = 0.0
        self.q_range_low: float = 0.0
        self.q_range_seen: bool = False
        self.q_longs_today: int = 0
        self.q_shorts_today: int = 0


def run_q(
    ms: MultiSeriesContext,
    qty: Optional[int] = None,
    cfg: Optional[RampartConfig] = None,
) -> pd.DataFrame:
    """Ejecuta Rampart5Minute (modulo Q) sobre ms.bip3 (5m ETH) con ejecucion en ms.bip1."""
    cfg = cfg or RampartConfig()
    if qty is not None and qty <= 0:
        return trades_to_df([])
    if len(ms.bip1.ts_ns) == 0 or len(ms.bip3.ts_ns) == 0:
        return trades_to_df([])

    b1 = ms.bip1
    b3 = ms.bip3
    n1 = len(b1.ts_ns)
    n3 = len(b3.ts_ns)

    open_date_et, open_min_et, open_dow_et, _, _ = _tz_fields(b3.ts_ns, "America/New_York", -5)

    # IL mod_Q.txt:60-102: RampartQuantity dimensiona en MNQ (pv = point_value / 10 = 2.0)
    tracker_pv = (
        (ms.point_value / 10.0 if ms.point_value >= 10.0 else ms.point_value)
        if qty is None
        else ms.point_value
    )
    tracker = _ModuleExecTracker("Q", ms.tick_size, tracker_pv)
    eng = _RampartEngine()

    range_start_min = cfg.range_start_hour * 60 + cfg.range_start_minute
    range_end_min = cfg.range_end_hour * 60 + cfg.range_end_minute
    force_close_min = cfg.force_close_hour * 60 + cfg.force_close_minute
    last_entry_min = min(cfg.last_entry_hour * 60 + cfg.last_entry_minute, force_close_min)
    break_margin = float(cfg.break_margin_ticks) * ms.tick_size
    stop_buffer = max(float(cfg.stop_buffer_ticks) * ms.tick_size, ms.tick_size)
    max_trades_today = 2 if cfg.one_trade_per_side else 1

    def _on_bip3_bar(k: int) -> None:
        if k < 2:
            return

        op_min = int(open_min_et[k])
        sess_key = int(open_date_et[k])
        if sess_key != eng.q_current_session:
            if eng.q_current_session is not None and tracker.is_open:
                tracker.request_exit("SESSION_ROLL")
            eng.q_current_session = sess_key
            eng.reset_session()

        hi = float(b3.high[k])
        lo = float(b3.low[k])
        cl = float(b3.close[k])

        if (op_min + 5 > range_start_min) and (op_min < range_end_min):
            if not eng.q_range_seen:
                eng.q_range_high = hi
                eng.q_range_low = lo
            else:
                eng.q_range_high = max(eng.q_range_high, hi)
                eng.q_range_low = min(eng.q_range_low, lo)
            eng.q_range_seen = True

        range_ready = eng.q_range_seen and (eng.q_range_high > eng.q_range_low)
        qual_long = range_ready and (cl >= eng.q_range_high + break_margin)
        qual_short = range_ready and (cl <= eng.q_range_low - break_margin)
        trig_long = qual_long and (not eng.q_prev_qual_long)
        trig_short = qual_short and (not eng.q_prev_qual_short)
        eng.q_prev_qual_long = qual_long
        eng.q_prev_qual_short = qual_short

        if op_min >= force_close_min:
            if tracker.is_open:
                tracker.request_exit("RAMPART_FLAT")
            return

        is_weekday = int(open_dow_et[k]) <= 4
        bars_since_last = (k - eng.q_last_trade_bar) if eng.q_last_trade_bar is not None else 2147483647
        eligible = (
            is_weekday
            and (op_min >= range_end_min)
            and (op_min < last_entry_min)
            and range_ready
            and (not tracker.is_open)
            and tracker.can_enter
            and ((eng.q_longs_today + eng.q_shorts_today) < max_trades_today)
            and (bars_since_last >= cfg.min_bars_between_trades)
        )
        if not eligible:
            return

        if trig_long and (not cfg.one_trade_per_side or eng.q_longs_today == 0):
            enter_long = True
        elif trig_short and (not cfg.one_trade_per_side or eng.q_shorts_today == 0):
            enter_long = False
        else:
            return

        stop_price = round_tick(
            (lo - stop_buffer) if enter_long else (hi + stop_buffer),
            ms.tick_size,
        )
        stop_dist = abs(cl - stop_price)
        if not (stop_dist >= 0.5 * ms.tick_size):
            return

        target_price = round_tick(
            (cl + stop_dist * cfg.risk_reward)
            if enter_long
            else (cl - stop_dist * cfg.risk_reward),
            ms.tick_size,
        )
        if not (abs(target_price - cl) >= 0.5 * ms.tick_size):
            return

        contracts = (
            int(qty)
            if qty is not None
            else rampart_quantity(
                stop_dist,
                cfg.risk_usd,
                cfg.max_contracts,
                ms.point_value,
                sizing_point_value=cfg.sizing_point_value,
            )
        )
        if contracts < 1:
            return

        if enter_long:
            tracker.request_entry(1, contracts, stop_price=stop_price, target_price=target_price)
            eng.q_longs_today += 1
        else:
            tracker.request_entry(-1, contracts, stop_price=stop_price, target_price=target_price)
            eng.q_shorts_today += 1
        eng.q_last_trade_bar = k

    k3 = 0
    while k3 < n3 and int(b3.m1_end_idx[k3]) < 0:
        k3 += 1

    for m1 in range(n1):
        ts = int(b1.ts_ns[m1])
        op1 = float(b1.open[m1])
        closed_open = tracker.on_bar_open(m1, ts, op1)
        if not closed_open:
            tracker.on_bar_intrabar(m1, ts, op1, float(b1.high[m1]), float(b1.low[m1]))

        while k3 < n3 and int(b3.m1_end_idx[k3]) <= m1:
            _on_bip3_bar(k3)
            k3 += 1

    return trades_to_df(tracker.trades)


# =============================================================================
# Wrappers senales_*
# =============================================================================

def senales_r(
    ms: MultiSeriesContext,
    qty: int | AtrPhaseConfig = 1,
    cfg: Optional[AtrPhaseConfig] = None,
) -> pd.DataFrame:
    """Wrapper de senales para AtrPhase (modulo R)."""
    if isinstance(qty, AtrPhaseConfig):
        return run_r(ms, cfg=qty)
    return run_r(ms, qty=qty, cfg=cfg)


def senales_z(
    ms: MultiSeriesContext,
    qty: int | ZetaConfig = 2,
    cfg: Optional[ZetaConfig] = None,
) -> pd.DataFrame:
    """Wrapper de senales para ZetaTrendDay (modulo Z)."""
    if isinstance(qty, ZetaConfig):
        return run_z(ms, cfg=qty)
    return run_z(ms, qty=qty, cfg=cfg)


def senales_e(
    ms: MultiSeriesContext,
    qty: int | EmaDivConfig = 1,
    cfg: Optional[EmaDivConfig] = None,
) -> pd.DataFrame:
    """Wrapper de senales para EmaDivergence (modulo E)."""
    if isinstance(qty, EmaDivConfig):
        return run_e(ms, cfg=qty)
    return run_e(ms, qty=qty, cfg=cfg)


def senales_q(
    ms: MultiSeriesContext,
    qty: Optional[int] | RampartConfig = None,
    cfg: Optional[RampartConfig] = None,
) -> pd.DataFrame:
    """Wrapper de senales para Rampart5Minute (modulo Q)."""
    if isinstance(qty, RampartConfig):
        return run_q(ms, cfg=qty)
    return run_q(ms, qty=qty, cfg=cfg)


__all__ = [
    "ATR_PHASE_BLOCKED_SESSIONS",
    "ZETA_NON_FULL_NYSE",
    "AtrPhaseConfig",
    "ZetaConfig",
    "EmaDivConfig",
    "RampartConfig",
    "RollingValues",
    "ema_step",
    "is_full_zeta_session",
    "next_full_zeta_session",
    "round_zeta_target",
    "rampart_quantity",
    "run_r",
    "run_z",
    "run_e",
    "run_q",
    "senales_r",
    "senales_z",
    "senales_e",
    "senales_q",
]
