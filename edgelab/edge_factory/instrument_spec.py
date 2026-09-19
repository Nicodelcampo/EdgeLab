"""Canonical instrument specifications for EdgeLab & Edge Discovery Factory.
Explicitly defines tick size, price precision, contract multiplier, and asset class
for all 11 verified CME futures instruments.
Eliminates heuristic or hardcoded approximations.
"""

from typing import Dict, Any

INSTRUMENT_SPECS: Dict[str, Dict[str, Any]] = {
    "ES": {
        "name": "E-mini S&P 500",
        "asset_class": "EQUITY_INDEX",
        "tick_size": 0.25,
        "precision": 2,
        "point_value": 50.0,
        "tick_value": 12.50,
        "exchange": "CME",
    },
    "MES": {
        "name": "Micro E-mini S&P 500",
        "asset_class": "EQUITY_INDEX",
        "tick_size": 0.25,
        "precision": 2,
        "point_value": 5.0,
        "tick_value": 1.25,
        "exchange": "CME",
    },
    "NQ": {
        "name": "E-mini Nasdaq-100",
        "asset_class": "EQUITY_INDEX",
        "tick_size": 0.25,
        "precision": 2,
        "point_value": 20.0,
        "tick_value": 5.00,
        "exchange": "CME",
    },
    "MNQ": {
        "name": "Micro E-mini Nasdaq-100",
        "asset_class": "EQUITY_INDEX",
        "tick_size": 0.25,
        "precision": 2,
        "point_value": 2.0,
        "tick_value": 0.50,
        "exchange": "CME",
    },
    "YM": {
        "name": "E-mini Dow ($5)",
        "asset_class": "EQUITY_INDEX",
        "tick_size": 1.0,
        "precision": 0,
        "point_value": 5.0,
        "tick_value": 5.00,
        "exchange": "CBOT",
    },
    "6E": {
        "name": "Euro FX Futures",
        "asset_class": "FX",
        "tick_size": 0.00005,
        "precision": 5,
        "point_value": 125000.0,
        "tick_value": 6.25,
        "exchange": "CME",
    },
    "6B": {
        "name": "British Pound Futures",
        "asset_class": "FX",
        "tick_size": 0.0001,
        "precision": 4,
        "point_value": 62500.0,
        "tick_value": 6.25,
        "exchange": "CME",
    },
    "6J": {
        "name": "Japanese Yen Futures",
        "asset_class": "FX",
        "tick_size": 0.0000005,
        "precision": 7,
        "point_value": 12500000.0,
        "tick_value": 6.25,
        "exchange": "CME",
    },
    "ZB": {
        "name": "30-Year U.S. Treasury Bond Futures",
        "asset_class": "FIXED_INCOME",
        "tick_size": 0.03125, # 1/32 of a point
        "precision": 5,
        "point_value": 1000.0,
        "tick_value": 31.25,
        "exchange": "CBOT",
    },
    "GC": {
        "name": "Gold Futures",
        "asset_class": "COMMODITY_METALS",
        "tick_size": 0.10,
        "precision": 1,
        "point_value": 100.0,
        "tick_value": 10.00,
        "exchange": "COMEX",
    },
    "MBT": {
        "name": "Micro Bitcoin Futures",
        "asset_class": "CRYPTO",
        "tick_size": 5.0,
        "precision": 1,
        "point_value": 0.1,
        "tick_value": 0.50,
        "exchange": "CME",
    },
}

def get_instrument_spec(symbol: str) -> Dict[str, Any]:
    """Returns canonical specification for symbol. Raises ValueError if unknown."""
    sym = symbol.upper().strip()
    if sym not in INSTRUMENT_SPECS:
        raise ValueError(f"Unknown instrument symbol '{symbol}'. Allowed: {list(INSTRUMENT_SPECS.keys())}")
    return INSTRUMENT_SPECS[sym]

def price_to_ticks(price_diff: float, symbol: str) -> float:
    """Converts a price difference to exact ticks for given symbol."""
    spec = get_instrument_spec(symbol)
    ts = spec["tick_size"]
    return round(price_diff / ts, 4)
