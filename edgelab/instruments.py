"""Contratos de instrumento (copiado de quantlab.config — aislamiento EdgeLab)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    symbol: str
    tick_size: float
    tick_value: float

    def ticks_to_price(self, ticks: float) -> float:
        return ticks * self.tick_size

    def price_to_ticks(self, price_delta: float) -> float:
        return price_delta / self.tick_size


ES = Instrument(symbol="ES", tick_size=0.25, tick_value=12.5)
NQ = Instrument(symbol="NQ", tick_size=0.25, tick_value=5.0)
EURUSD = Instrument(symbol="EURUSD", tick_size=0.00001, tick_value=1.25)
SIX_E = Instrument(symbol="6E", tick_size=0.00005, tick_value=6.25)
YM = Instrument(symbol="YM", tick_size=1.0, tick_value=5.0)
ZB = Instrument(symbol="ZB", tick_size=0.03125, tick_value=31.25)

INSTRUMENTS = {
    "ES": ES,
    "NQ": NQ,
    "EURUSD": EURUSD,
    "6E": SIX_E,
    "YM": YM,
    "ZB": ZB,
}
