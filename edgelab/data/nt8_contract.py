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
    tick_size: float          # p.ej. 6E = 0.00005
    tick_value: float         # USD por tick (6E = 6.25)
    multiplier: float         # tamaño de contrato (6E = 125000 EUR)


# 6E — futuros EUR/USD (CME). Precios internos en ticks enteros.
SIX_E = InstrumentSpec(symbol="6E", tick_size=0.00005, tick_value=6.25, multiplier=125000.0)

# YM — futuros Mini Dow ($5) (CBOT/CME). tick_value = tick_size * multiplier,
# igual que 6E (1.0 * 5.0 = 5.00): consistente con la formula, no un dato suelto.
YM = InstrumentSpec(symbol="YM", tick_size=1.0, tick_value=5.00, multiplier=5.0)

# ES — futuros E-mini S&P 500 (CME). tick_value = 0.25 * 50.0 = 12.50.
ES = InstrumentSpec(symbol="ES", tick_size=0.25, tick_value=12.50, multiplier=50.0)

# NQ — futuros E-mini Nasdaq-100 (CME). tick_value = 0.25 * 20.0 = 5.00.
NQ = InstrumentSpec(symbol="NQ", tick_size=0.25, tick_value=5.00, multiplier=20.0)


class Nt8TickContract(BaseModel):
    """Contrato del formato. `declared_tz` es OBLIGATORIA (sin default) → una
    spec sin zona declarada falla en carga (ValidationError)."""
    model_config = ConfigDict(extra="forbid")

    declared_tz: str = Field(min_length=1)     # zona DECLARADA del export (F2 la verifica)
    instrument: InstrumentSpec
    field_sep: str = ";"
    columns: tuple[str, ...] = ("ts", "last", "bid", "ask", "volume")
    ts_format: str = "yyyyMMdd HHmmss fffffff"
    frac_digits: int = 7
    frac_unit_ns: int = 100                    # 100 ns por unidad (.NET ticks)
    price_align_tol: float = 1e-9              # tolerancia relativa de alineación a tick
    # semántica de agresor (documental): last==ask -> buy, last==bid -> sell, otro -> unclassified
