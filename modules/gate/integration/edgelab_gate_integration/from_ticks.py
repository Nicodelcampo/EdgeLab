"""Compatibilidad mínima para el viejo import from_ticks.

La implementación original quedó retirada: sellaba barras al inicio del minuto,
llamaba OFI al signed tape y VPIN a una media móvil temporal, y además fabricaba
eventos. La única ruta válida delega a gate_features_l1_v0.
"""
from __future__ import annotations

import pandas as pd

try:
    from modules.gate.core.gate_features_l1_v0 import build_l1_minute_features
except ModuleNotFoundError:  # ejecución directa desde el directorio legacy
    from gate_features_l1_v0 import build_l1_minute_features


def ticks_to_bars_1m(ticks: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "timestamp": "ts_utc_ns",
        "time": "ts_utc_ns",
        "last": "price_ticks",
        "bid": "bid_ticks",
        "ask": "ask_ticks",
        "session_id": "cme_session",
        "symbol": "instrument",
    }
    frame = ticks.rename(columns={k: v for k, v in aliases.items() if k in ticks.columns and v not in ticks.columns})
    return build_l1_minute_features(frame)


def features_from_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = {
        "data_window_end", "feature_available_at", "tape_imbalance",
        "spread_ticks_mean", "tick_rate_per_second",
    }
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValueError(f"bars no proviene del builder causal: faltan {missing}")
    return bars.copy()


def events_from_bars(*args, **kwargs):
    raise RuntimeError("retirado: GATE no fabrica eventos; consuma export real del indicador")
