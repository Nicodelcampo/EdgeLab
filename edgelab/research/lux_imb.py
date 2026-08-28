"""Contrato geométrico target-free para OG/VI de LUX-IMB.

La semántica base proviene del archivo NT8 entregado por el operador
``ImbalanceDetectorLuxAlgoMTF.cs`` (SHA-256 crudo declarado abajo). Este
módulo no mide retornos, no clasifica reacciones y no abre el holdout.

Una discrepancia deliberada corrige un defecto del archivo recibido: las
zonas OG se representan wick-a-wick, de acuerdo con su propia condición de
detección, no body-a-body.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite
from typing import Literal

NT8_SOURCE_SHA256 = "bff0e66242d055152f891c9fcb2e04b3890346a1cf6b88311607e4645350c533"
SEMANTICS_ID = "lux_og_vi_nt8_candidate_v1"


class GeometryError(ValueError):
    """La entrada no permite reconstruir geometría causal."""


class WidthMethod(str, Enum):
    POINTS = "points"
    PERCENT = "percent"
    ATR = "atr"


@dataclass(frozen=True)
class WidthFilter:
    enabled: bool = False
    value: float = 0.0
    method: WidthMethod = WidthMethod.POINTS

    def __post_init__(self) -> None:
        if not isfinite(self.value) or self.value < 0:
            raise GeometryError("min_width debe ser finito y >= 0")


@dataclass(frozen=True)
class OhlcBar:
    """Barra cerrada; ``timestamp`` es su instante de disponibilidad."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise GeometryError("timestamp debe incluir zona horaria")
        values = (self.open, self.high, self.low, self.close)
        if any(not isfinite(value) for value in values):
            raise GeometryError("OHLC debe ser finito")
        if self.high < max(self.open, self.close) or self.low > min(
            self.open, self.close
        ):
            raise GeometryError("OHLC inconsistente")
        if self.high < self.low:
            raise GeometryError("high no puede ser menor que low")


@dataclass(frozen=True)
class ImbalanceZone:
    family: Literal["OG", "VI"]
    direction: Literal["bullish", "bearish"]
    top: float
    bottom: float
    source_bar_time: datetime
    available_at: datetime
    semantics_id: str = SEMANTICS_ID
    source_sha256: str = NT8_SOURCE_SHA256

    def __post_init__(self) -> None:
        if not isfinite(self.top) or not isfinite(self.bottom):
            raise GeometryError("bordes de zona no finitos")
        if self.top <= self.bottom:
            raise GeometryError("top debe ser estrictamente mayor que bottom")
        if self.available_at < self.source_bar_time:
            raise GeometryError("available_at no puede preceder source_bar_time")

    @property
    def width(self) -> float:
        return self.top - self.bottom


def _passes_width(
    top: float,
    bottom: float,
    width_filter: WidthFilter,
    *,
    atr: float | None,
) -> bool:
    if top <= bottom:
        raise GeometryError("ancho de zona no positivo")
    if not width_filter.enabled:
        return True
    distance = top - bottom
    if width_filter.method is WidthMethod.POINTS:
        threshold = width_filter.value
    elif width_filter.method is WidthMethod.PERCENT:
        if bottom <= 0:
            raise GeometryError("percent requiere precio inferior positivo")
        threshold = bottom * width_filter.value / 100.0
    elif width_filter.method is WidthMethod.ATR:
        if atr is None or not isfinite(atr) or atr <= 0:
            raise GeometryError("ATR positivo requerido para filtro ATR")
        threshold = atr * width_filter.value
    else:  # pragma: no cover
        raise GeometryError("método de ancho desconocido")
    return distance > threshold


def _validate_pair(previous: OhlcBar, current: OhlcBar) -> None:
    if current.timestamp <= previous.timestamp:
        raise GeometryError("las barras deben estar estrictamente ordenadas")


def detect_opening_gaps(
    previous: OhlcBar,
    current: OhlcBar,
    *,
    width_filter: WidthFilter = WidthFilter(),
    atr: float | None = None,
) -> tuple[ImbalanceZone, ...]:
    """Detecta OG con geometría wick-a-wick."""
    _validate_pair(previous, current)
    zones: list[ImbalanceZone] = []
    if current.low > previous.high:
        top, bottom = current.low, previous.high
        if _passes_width(top, bottom, width_filter, atr=atr):
            zones.append(
                ImbalanceZone(
                    "OG", "bullish", top, bottom,
                    previous.timestamp, current.timestamp,
                )
            )
    if current.high < previous.low:
        top, bottom = previous.low, current.high
        if _passes_width(top, bottom, width_filter, atr=atr):
            zones.append(
                ImbalanceZone(
                    "OG", "bearish", top, bottom,
                    previous.timestamp, current.timestamp,
                )
            )
    return tuple(zones)


def detect_volume_imbalances(
    previous: OhlcBar,
    current: OhlcBar,
    *,
    width_filter: WidthFilter = WidthFilter(),
    atr: float | None = None,
) -> tuple[ImbalanceZone, ...]:
    """Replica las desigualdades VI del NT8 recibido, sin outcomes."""
    _validate_pair(previous, current)
    zones: list[ImbalanceZone] = []

    current_body_low = min(current.close, current.open)
    previous_body_high = max(previous.close, previous.open)
    previous_body_low = min(previous.close, previous.open)
    current_body_high = max(current.close, current.open)

    bullish = (
        current.open > previous.close
        and previous.high > current.low
        and current.close > previous.close
        and current.open > previous.open
        and previous.high < current_body_low
    )
    if bullish and _passes_width(
        current_body_low, previous_body_high, width_filter, atr=atr
    ):
        zones.append(
            ImbalanceZone(
                "VI", "bullish", current_body_low, previous_body_high,
                previous.timestamp, current.timestamp,
            )
        )

    bearish = (
        current.open < previous.close
        and previous.low < current.high
        and current.close < previous.close
        and current.open < previous.open
        and previous.low > current_body_high
    )
    if bearish and _passes_width(
        previous_body_low, current_body_high, width_filter, atr=atr
    ):
        zones.append(
            ImbalanceZone(
                "VI", "bearish", previous_body_low, current_body_high,
                previous.timestamp, current.timestamp,
            )
        )
    return tuple(zones)


def detect_og_vi(
    previous: OhlcBar,
    current: OhlcBar,
    *,
    show_og: bool = True,
    show_vi: bool = True,
    og_width: WidthFilter = WidthFilter(),
    vi_width: WidthFilter = WidthFilter(),
    atr: float | None = None,
) -> tuple[ImbalanceZone, ...]:
    zones: list[ImbalanceZone] = []
    if show_og:
        zones.extend(
            detect_opening_gaps(
                previous, current, width_filter=og_width, atr=atr
            )
        )
    if show_vi:
        zones.extend(
            detect_volume_imbalances(
                previous, current, width_filter=vi_width, atr=atr
            )
        )
    return tuple(zones)
