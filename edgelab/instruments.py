"""Contratos de instrumento (copiado de quantlab.config — aislamiento EdgeLab).

Fuente única de las cantidades por instrumento: `tick_size`, `tick_value` y el
multiplicador de contrato derivado de ambos. Toda herramienta que necesite esas
cantidades las importa de acá; volver a declararlas a mano es la vía por la que
una tabla driftea sin que nadie lo note (defecto 5 de la auditoría del builder
de Kaggle, 2026-08-14: `tools/build_kaggle_bundle.py` traía su propia copia).
"""
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

    @property
    def multiplier(self) -> float:
        """Multiplicador del contrato, derivado: tick_value / tick_size.

        Se expone derivado y no como campo propio para que no puedan quedar
        dos números en desacuerdo dentro del mismo objeto.
        """
        return self.tick_value / self.tick_size


ES = Instrument(symbol="ES", tick_size=0.25, tick_value=12.5)
NQ = Instrument(symbol="NQ", tick_size=0.25, tick_value=5.0)
EURUSD = Instrument(symbol="EURUSD", tick_size=0.00001, tick_value=1.25)
SIX_E = Instrument(symbol="6E", tick_size=0.00005, tick_value=6.25)
YM = Instrument(symbol="YM", tick_size=1.0, tick_value=5.0)
ZB = Instrument(symbol="ZB", tick_size=0.03125, tick_value=31.25)

# --- Resto del universo CME del dataset multi-activo (agregado 2026-08-14) ---
# Especificaciones de contrato de CME; tick_value = tick_size * multiplicador.
SIX_B = Instrument(symbol="6B", tick_size=0.0001, tick_value=6.25)  # 62.500 GBP
SIX_J = Instrument(symbol="6J", tick_size=0.0000005, tick_value=6.25)  # 12.500.000 JPY
GC = Instrument(symbol="GC", tick_size=0.10, tick_value=10.0)  # 100 oz troy
MBT = Instrument(symbol="MBT", tick_size=5.0, tick_value=0.5)  # 0,1 BTC
MES = Instrument(symbol="MES", tick_size=0.25, tick_value=1.25)  # multiplicador 5
MNQ = Instrument(symbol="MNQ", tick_size=0.25, tick_value=0.5)  # multiplicador 2

INSTRUMENTS = {
    "ES": ES,
    "NQ": NQ,
    "EURUSD": EURUSD,
    "6E": SIX_E,
    "YM": YM,
    "ZB": ZB,
}

# Los 11 futuros del dataset de Kaggle. `INSTRUMENTS` queda intacto (incluye
# EURUSD, que es spot y no tiene contrato) para no cambiarle la semántica a los
# consumidores existentes; los que necesiten el universo de futuros usan esto.
CME_UNIVERSE = {
    "6B": SIX_B,
    "6E": SIX_E,
    "6J": SIX_J,
    "ES": ES,
    "GC": GC,
    "MBT": MBT,
    "MES": MES,
    "MNQ": MNQ,
    "NQ": NQ,
    "YM": YM,
    "ZB": ZB,
}
