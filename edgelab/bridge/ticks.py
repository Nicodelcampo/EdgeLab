"""Carga de ticks canónicos F2 para el bridge NT8.

Consume el parquet canónico F2 (schema fijo). `tick_size` sale del catálogo de
instrumentos (`nt8_contract`), por `instrument` — NO como float suelto. Filtra
por `contract` + rango UTC `[start, end)`. NO reparsea `.Last.txt` (eso es F2)
ni acepta schemas alternativos.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from edgelab.data.nt8_contract import INSTRUMENT_SPECS, InstrumentSpec

# Alias histórico: una sola fuente de verdad vive en nt8_contract.py.
INSTRUMENT_CATALOG = INSTRUMENT_SPECS

_REQUIRED = ("ts_utc_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks",
             "sequence", "instrument", "contract")


def instrument_spec(symbol: str) -> InstrumentSpec:
    if symbol not in INSTRUMENT_CATALOG:
        raise KeyError(f"instrument '{symbol}' no está en el catálogo del bridge "
                       f"({sorted(INSTRUMENT_CATALOG)})")
    return INSTRUMENT_CATALOG[symbol]


@dataclass
class TickSeries:
    ts_ns: np.ndarray
    price_ticks: np.ndarray
    volume: np.ndarray
    bid_ticks: Optional[np.ndarray]
    ask_ticks: Optional[np.ndarray]
    sequence: np.ndarray
    tick_size: float
    instrument: str = "?"
    contract: str = "?"
    source: str = "?"
    # Lado del AGRESOR informado por la fuente, cuando existe: +1 comprador
    # taker, -1 vendedor taker, 0 desconocido. Es un dato del venue, no una
    # inferencia. Binance lo publica como `is_buyer_maker` en sus trades.
    # None = la fuente no lo provee y se clasifica por quote/tick-rule.
    aggressor_side: Optional[np.ndarray] = None

    def __post_init__(self):
        d = np.diff(self.ts_ns)
        if len(d) and d.min() < 0:
            raise ValueError("ticks no monótonos (gate P0): auditar/ordenar antes de usar")

    def __len__(self):
        return len(self.ts_ns)

    def price(self, i: int) -> float:
        return float(self.price_ticks[i]) * self.tick_size


def load_canonical_parquet(path, contract=None, start_utc_ns=None, end_utc_ns=None,
                           instrument=None) -> TickSeries:
    """Lee el parquet canónico F2, filtrado por `contract` y `[start, end)` UTC."""
    import pyarrow.parquet as pq

    filters = []
    if contract is not None:
        filters.append(("contract", "==", contract))
    if start_utc_ns is not None:
        filters.append(("ts_utc_ns", ">=", int(start_utc_ns)))
    if end_utc_ns is not None:
        filters.append(("ts_utc_ns", "<", int(end_utc_ns)))
    tbl = pq.read_table(path, filters=filters or None)
    missing = set(_REQUIRED) - set(tbl.column_names)
    if missing:
        raise ValueError(f"no es un parquet canónico F2: faltan columnas {sorted(missing)}")
    if tbl.num_rows == 0:
        raise ValueError("selección vacía (contract/rango sin ticks)")

    def col(name):
        return tbl.column(name).to_numpy(zero_copy_only=False)

    inst = instrument or str(tbl.column("instrument")[0].as_py())
    spec = instrument_spec(inst)
    return TickSeries(
        ts_ns=col("ts_utc_ns").astype(np.int64),
        price_ticks=col("price_ticks").astype(np.int64),
        volume=col("volume").astype(np.float64),
        bid_ticks=col("bid_ticks").astype(np.int64),
        ask_ticks=col("ask_ticks").astype(np.int64),
        sequence=col("sequence").astype(np.int64),
        tick_size=spec.tick_size, instrument=inst,
        contract=contract or str(tbl.column("contract")[0].as_py()),
        source=str(path))


def make_synthetic(start_utc: str = "2026-06-01T23:00:00", n_sessions: int = 3,
                   ticks_per_session: int = 30000, tick_size: float = 0.25,
                   seed: int = 7) -> TickSeries:
    """Ticks sintéticos deterministas para tests/demo."""
    rng = np.random.default_rng(seed)
    t0 = int(datetime.fromisoformat(start_utc).replace(tzinfo=timezone.utc).timestamp() * 1e9)
    ts, px, vol, bid, ask = [], [], [], [], []
    price = 20000
    for s in range(n_sessions):
        t = t0 + s * 86_400_000_000_000
        i = 0
        while i < ticks_per_session:
            burst = rng.random() < 0.002
            n = int(rng.integers(10, 25)) if burst else 1
            d = int(rng.integers(0, 2)) * 2 - 1
            for _k in range(n):
                dt_ms = float(rng.integers(1, 4)) if burst else float(rng.exponential(120) + 4)
                t += int(dt_ms * 1e6)
                if burst:
                    price += d
                else:
                    price += int(rng.integers(-1, 2))
                    if rng.random() < 0.001:
                        price += int(rng.integers(3, 9)) * (1 if rng.random() < 0.5 else -1)
                v = float(rng.integers(1, 8))
                spread_up = int(rng.random() < 0.5)
                ts.append(t); px.append(price); vol.append(v)
                bid.append(price - spread_up); ask.append(price + (1 - spread_up))
                i += 1
                if i >= ticks_per_session:
                    break
    n = len(ts)
    return TickSeries(
        ts_ns=np.asarray(ts, np.int64), price_ticks=np.asarray(px, np.int64),
        volume=np.asarray(vol, np.float64), bid_ticks=np.asarray(bid, np.int64),
        ask_ticks=np.asarray(ask, np.int64), sequence=np.arange(n, dtype=np.int64),
        tick_size=tick_size, instrument="SYN", contract="SYN 06-26", source="synthetic")
