"""Causal trend-context composition for existing EdgeLab event carriers.

This module does not add a new detector. It composes closed-bar context from
VWAP, EMA and SMA so existing BigTrap2/HFT-zone events can be classified as
with-trend, counter-trend or neutral without using future prices or outcomes.
The caller must map detector-specific semantics to ``continuation_direction``.
"""
from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

CONTRACT_VERSION = "CAUSAL_TREND_CONTEXT_V1"


class TrendState(str, Enum):
    NOT_READY = "NOT_READY"
    UP = "UP"
    DOWN = "DOWN"
    NEUTRAL = "NEUTRAL"


class EventAlignment(str, Enum):
    NOT_READY = "NOT_READY"
    WITH_TREND = "WITH_TREND"
    COUNTER_TREND = "COUNTER_TREND"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True, slots=True)
class TrendParameters:
    ema_fast: int = 9
    ema_slow: int = 21
    sma_fast: int = 20
    sma_slow: int = 50
    slope_lookback: int = 3

    def __post_init__(self) -> None:
        values = (self.ema_fast, self.ema_slow, self.sma_fast, self.sma_slow, self.slope_lookback)
        if any(value <= 0 for value in values):
            raise ValueError("all trend parameters must be positive")
        if self.ema_fast >= self.ema_slow:
            raise ValueError("ema_fast must be less than ema_slow")
        if self.sma_fast >= self.sma_slow:
            raise ValueError("sma_fast must be less than sma_slow")


@dataclass(frozen=True, slots=True)
class TrendBar:
    ts_ns: int
    session_id: str
    close_ticks: float
    volume: float
    typical_price_ticks: float | None = None

    def __post_init__(self) -> None:
        if self.ts_ns < 0:
            raise ValueError("ts_ns must be non-negative")
        if not self.session_id:
            raise ValueError("session_id is required")
        if self.volume < 0:
            raise ValueError("volume must be non-negative")


@dataclass(frozen=True, slots=True)
class TrendContext:
    contract_version: str
    ts_ns: int
    available_at_ns: int
    session_id: str
    bar_index: int
    session_bar_index: int
    close_ticks: float
    vwap_ticks: float | None
    ema_fast_ticks: float
    ema_slow_ticks: float
    sma_fast_ticks: float | None
    sma_slow_ticks: float | None
    ema_slope_ticks: float | None
    vwap_slope_ticks: float | None
    close_minus_vwap_ticks: float | None
    close_minus_ema_fast_ticks: float
    close_minus_ema_slow_ticks: float
    trend_state: TrendState
    digest: str


def _digest(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _mean(values: deque[float], required: int) -> float | None:
    if len(values) < required:
        return None
    return sum(values) / required


def compute_trend_contexts(
    bars: Iterable[TrendBar],
    *,
    params: TrendParameters = TrendParameters(),
    availability_lag_ns: int = 1,
) -> list[TrendContext]:
    """Compute prefix-invariant context from bars closed at ``ts_ns``.

    EMA/SMA state continues across session boundaries on the supplied continuous
    series. Session VWAP resets when ``session_id`` changes. The current closed
    bar is included and context becomes available after the declared lag.
    """
    rows = list(bars)
    if availability_lag_ns <= 0:
        raise ValueError("availability_lag_ns must be positive")
    if any(current.ts_ns <= previous.ts_ns for previous, current in zip(rows, rows[1:])):
        raise ValueError("bars must be strictly increasing by ts_ns")

    alpha_fast = 2.0 / (params.ema_fast + 1.0)
    alpha_slow = 2.0 / (params.ema_slow + 1.0)
    ema_fast = ema_slow = None
    fast_window: deque[float] = deque(maxlen=params.sma_fast)
    slow_window: deque[float] = deque(maxlen=params.sma_slow)
    ema_history: list[float] = []
    session_vwaps: list[float | None] = []
    session_id = None
    session_bar_index = -1
    cumulative_volume = 0.0
    cumulative_price_volume = 0.0
    contexts: list[TrendContext] = []

    for bar_index, bar in enumerate(rows):
        if bar.session_id != session_id:
            session_id = bar.session_id
            session_bar_index = 0
            cumulative_volume = 0.0
            cumulative_price_volume = 0.0
            session_vwaps = []
        else:
            session_bar_index += 1

        close = float(bar.close_ticks)
        ema_fast = close if ema_fast is None else alpha_fast * close + (1.0 - alpha_fast) * ema_fast
        ema_slow = close if ema_slow is None else alpha_slow * close + (1.0 - alpha_slow) * ema_slow
        fast_window.append(close)
        slow_window.append(close)
        sma_fast = _mean(fast_window, params.sma_fast)
        sma_slow = _mean(slow_window, params.sma_slow)

        if bar.volume > 0:
            typical = close if bar.typical_price_ticks is None else float(bar.typical_price_ticks)
            cumulative_price_volume += typical * float(bar.volume)
            cumulative_volume += float(bar.volume)
        vwap = cumulative_price_volume / cumulative_volume if cumulative_volume > 0 else None

        ema_history.append(ema_fast)
        session_vwaps.append(vwap)
        ema_slope = None
        if len(ema_history) > params.slope_lookback:
            ema_slope = ema_fast - ema_history[-1 - params.slope_lookback]
        vwap_slope = None
        if len(session_vwaps) > params.slope_lookback:
            prior_vwap = session_vwaps[-1 - params.slope_lookback]
            if vwap is not None and prior_vwap is not None:
                vwap_slope = vwap - prior_vwap

        ready = all(value is not None for value in (sma_fast, sma_slow, vwap, ema_slope, vwap_slope))
        if not ready:
            state = TrendState.NOT_READY
        else:
            up = close > vwap and ema_fast > ema_slow and sma_fast > sma_slow and ema_slope > 0 and vwap_slope > 0
            down = close < vwap and ema_fast < ema_slow and sma_fast < sma_slow and ema_slope < 0 and vwap_slope < 0
            state = TrendState.UP if up else TrendState.DOWN if down else TrendState.NEUTRAL

        payload = {
            "contract_version": CONTRACT_VERSION,
            "ts_ns": bar.ts_ns,
            "available_at_ns": bar.ts_ns + availability_lag_ns,
            "session_id": bar.session_id,
            "bar_index": bar_index,
            "session_bar_index": session_bar_index,
            "close_ticks": close,
            "vwap_ticks": vwap,
            "ema_fast_ticks": ema_fast,
            "ema_slow_ticks": ema_slow,
            "sma_fast_ticks": sma_fast,
            "sma_slow_ticks": sma_slow,
            "ema_slope_ticks": ema_slope,
            "vwap_slope_ticks": vwap_slope,
            "close_minus_vwap_ticks": close - vwap if vwap is not None else None,
            "close_minus_ema_fast_ticks": close - ema_fast,
            "close_minus_ema_slow_ticks": close - ema_slow,
            "trend_state": state.value,
        }
        contexts.append(TrendContext(
            contract_version=CONTRACT_VERSION,
            ts_ns=bar.ts_ns,
            available_at_ns=bar.ts_ns + availability_lag_ns,
            session_id=bar.session_id,
            bar_index=bar_index,
            session_bar_index=session_bar_index,
            close_ticks=close,
            vwap_ticks=vwap,
            ema_fast_ticks=ema_fast,
            ema_slow_ticks=ema_slow,
            sma_fast_ticks=sma_fast,
            sma_slow_ticks=sma_slow,
            ema_slope_ticks=ema_slope,
            vwap_slope_ticks=vwap_slope,
            close_minus_vwap_ticks=payload["close_minus_vwap_ticks"],
            close_minus_ema_fast_ticks=payload["close_minus_ema_fast_ticks"],
            close_minus_ema_slow_ticks=payload["close_minus_ema_slow_ticks"],
            trend_state=state,
            digest=_digest(payload),
        ))

    return contexts


def align_event_with_trend(
    continuation_direction: int,
    context: TrendContext,
    *,
    event_available_at_ns: int,
) -> EventAlignment:
    """Classify an existing event without inventing detector direction semantics."""
    if continuation_direction not in (-1, 1):
        raise ValueError("continuation_direction must be +1 or -1")
    if event_available_at_ns < context.available_at_ns:
        raise ValueError("event precedes trend context availability")
    if context.trend_state is TrendState.NOT_READY:
        return EventAlignment.NOT_READY
    if context.trend_state is TrendState.NEUTRAL:
        return EventAlignment.NEUTRAL
    trend_direction = 1 if context.trend_state is TrendState.UP else -1
    return EventAlignment.WITH_TREND if continuation_direction == trend_direction else EventAlignment.COUNTER_TREND
