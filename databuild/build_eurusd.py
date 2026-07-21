"""Construye el parquet eurusd_ticks.parquet a partir del CSV de JForex."""
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path

from edgelab.config import EURUSD_TICKS_RAW, EURUSD_TICKS

def build_eurusd():
    print(f"Leyendo CSV crudo: {EURUSD_TICKS_RAW}")
    
    # El archivo de JForex (Dukascopy) no tiene headers en algunas exportaciones.
    # Vamos a leer los primeros megas para chequear si el header está.
    sample = pd.read_csv(EURUSD_TICKS_RAW, nrows=10)
    has_header = "time" in sample.columns or "time" in str(sample.columns[0]).lower()
    
    if has_header:
        df = pd.read_csv(EURUSD_TICKS_RAW)
        # Rename si es necesario
        df.columns = ["time", "bid", "ask", "bidVolume", "askVolume"]
    else:
        df = pd.read_csv(EURUSD_TICKS_RAW, header=None, 
                         names=["time", "bid", "ask", "bidVolume", "askVolume"])

    print(f"Lineas leídas: {len(df):,}")

    # Validar nulos
    n_null = df["time"].isnull().sum()
    if n_null > 0:
        print(f"Dropping {n_null} null rows")
        df = df.dropna(subset=["time"])
        
    print("Convirtiendo timestamps...")
    # time en el csv de JForex está en ms (ej 1740779312369)
    ts = pd.to_datetime(df["time"], unit='ms')
    
    print("Derivando LAST price (mid)...")
    bid = df["bid"].astype(np.float64)
    ask = df["ask"].astype(np.float64)
    last = ((bid + ask) / 2).astype(np.float64)
    
    print("Validando monotonicidad temporal...")
    diff = ts.diff().dt.total_seconds()
    if (diff < 0).any():
        print("  WARNING: Timestamps not monotonic. Sorting...")
        df = df.set_index(ts).sort_index().reset_index(drop=True)
        ts = ts.sort_values()
        # sort again the arrays
        bid = df["bid"].astype(np.float64)
        ask = df["ask"].astype(np.float64)
        last = ((bid + ask) / 2).astype(np.float64)

    print("Calculando estadisticas del spread (pipettes)...")
    spread = (ask - bid) / 0.00001
    print(f"  Min spread : {spread.min():.1f} pipettes")
    print(f"  P50 spread : {spread.median():.1f} pipettes")
    print(f"  P99 spread : {spread.quantile(0.99):.1f} pipettes")
    print(f"  Max spread : {spread.max():.1f} pipettes")

    # Guardar en parquet
    print(f"\nEscribiendo {EURUSD_TICKS}")
    table = pa.Table.from_arrays(
        [
            pa.array(ts.values),
            pa.array(last.values),
            pa.array(bid.values),
            pa.array(ask.values)
        ],
        names=["timestamp", "last", "bid", "ask"]
    )
    pq.write_table(table, EURUSD_TICKS)
    print("HECHO.")

if __name__ == "__main__":
    build_eurusd()
