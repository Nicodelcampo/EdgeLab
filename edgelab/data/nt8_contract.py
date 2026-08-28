"""Data Contract de ticks NT8 exportados como `.Last.txt` (gate P0).

Formato confirmado (muestreo read-only de TickData/6E):
    yyyyMMdd HHmmss fffffff ; last ; bid ; ask ; volume
- separador `;`, 5 campos; el campo 1 lleva espacios (fecha, hora, fracción).
- fracción de 7 dígitos en unidades de 100 ns (.NET ticks).
- timestamps duplicados legítimos (varios ticks en el mismo stamp).

TIMEZONE: se DECLARA (`declared_tz`), NUNCA se asume. La UI de NT8 reportó
(UTC-03:00) America/Argentina/Buenos_Aires sin DST, pero hay evidencia
preliminar de que la base real del export podría diferir (trades un viernes
20:00–20:15 hora archivo = 23:00 UTC si fuese ART, posterior al cierre CME).
Por eso F1 solo almacena la zona declarada; **F2 la verifica empíricamente**
contra los bordes del gap de fin de semana (cierre vie 17:00 ET / reapertura
dom 18:00 ET, DST-aware) y falla si inferida ≠ declarada.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class InstrumentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    symbol: str
    tick_size: float
    tick_value: float
    multiplier: float


SIX_E = InstrumentSpec(symbol="6E", tick_size=0.00005, tick_value=6.25, multiplier=125000.0)
YM = InstrumentSpec(symbol="YM", tick_size=1.0, tick_value=5.00, multiplier=5.0)
ES = InstrumentSpec(symbol="ES", tick_size=0.25, tick_value=12.50, multiplier=50.0)
NQ = InstrumentSpec(symbol="NQ", tick_size=0.25, tick_value=5.00, multiplier=20.0)

# ZB — 30-Year U.S. Treasury Bond: 1/32 point, USD 31.25 por tick.
ZB = InstrumentSpec(symbol="ZB", tick_size=0.03125, tick_value=31.25, multiplier=1000.0)

# GC — COMEX Gold futures: 0.10 USD por onza, contrato de 100 oz,
# tick_value = 0.10 * 100 = USD 10. Este catálogo solo define geometría del
# contrato; no adjudica que un parquet sea canónico (eso requiere hash/P0/P1A).
GC = InstrumentSpec(symbol="GC", tick_size=0.1, tick_value=10.0, multiplier=100.0)

# 6J — CME Japanese Yen futures. Contrato de 12.500.000 JPY, cotizado en USD por JPY.
#
# `tick_size` NO se acepta de palabra: 5e-07 está declarado en los manifiestos de los
# parquets (`data/nt8/6J_parquet/6J_*_manifest.json`, campo `tick_size`), generados por
# `build_nt8_ticks` desde los .Last.txt. Coincide con lo que informó Nico.
#
# La aritmética se auto-verifica: 0,0000005 × 12.500.000 = 6,25 USD por tick, el mismo
# tick_value que 6E (0,00005 × 125.000 = 6,25). Si alguno de los tres números estuviera
# mal, el producto no cerraría — ver `tests/data/test_nt8_contract_6j.py`.
SIX_J = InstrumentSpec(symbol="6J", tick_size=0.0000005, tick_value=6.25,
                       multiplier=12_500_000.0)

INSTRUMENT_SPECS: dict[str, InstrumentSpec] = {
    "6E": SIX_E,
    "YM": YM,
    "ES": ES,
    "NQ": NQ,
    "ZB": ZB,
    "GC": GC,
    "6J": SIX_J,
}


class Nt8TickContract(BaseModel):
    """Contrato del formato. `declared_tz` es OBLIGATORIA (sin default)."""
    model_config = ConfigDict(extra="forbid")

    declared_tz: str = Field(min_length=1)
    instrument: InstrumentSpec
    field_sep: str = ";"
    columns: tuple[str, ...] = ("ts", "last", "bid", "ask", "volume")
    ts_format: str = "yyyyMMdd HHmmss fffffff"
    frac_digits: int = 7
    frac_unit_ns: int = 100
    price_align_tol: float = 1e-9
