"""Script para perfilar la microestructura de EURUSD vs ES/NQ.

Extrae estadísticas descriptivas clave para comparar activos:
1. Autocorrelación de Ticks (Reversión a la media vs Momentum)
2. Costo del Spread relativo a la volatilidad
3. Densidad de ticks por hora (Perfil Intradiario)
"""
import sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

from edgelab.config import EURUSD_TICKS, NQ_TICKS_CLEAN, ES_TICKS
from edgelab.instruments import INSTRUMENTS

def profile_asset(name, parquet_path, instrument):
    print(f"\n[{name}] Analizando {parquet_path.name}...")
    try:
        tbl = pq.read_table(parquet_path, columns=["timestamp", "last", "bid", "ask"])
    except Exception as e:
        print(f"No se pudo cargar {name}: {e}")
        return
        
    ts = tbl.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[ms]")
    last = tbl.column("last").to_numpy(zero_copy_only=False).astype(np.float64)
    bid = tbl.column("bid").to_numpy(zero_copy_only=False).astype(np.float64)
    ask = tbl.column("ask").to_numpy(zero_copy_only=False).astype(np.float64)
    
    n_ticks = len(last)
    tick = instrument.tick_size
    
    # 1. Spread Metrics
    spread_ticks = (ask - bid) / tick
    median_spread = np.nanmedian(spread_ticks)
    p99_spread = np.nanpercentile(spread_ticks, 99)
    
    # 2. Autocorrelación de saltos tick-a-tick
    # Calculamos saltos distintos de cero
    diffs = np.diff(last)
    non_zero = diffs[diffs != 0]
    
    if len(non_zero) > 1:
        # Autocorrelación lag-1 (correlación de Pearson entre diff[i] y diff[i-1])
        x = non_zero[:-1]
        y = non_zero[1:]
        # Centrar (aunque la media es muy cercana a 0)
        x_m = x - x.mean()
        y_m = y - y.mean()
        # Evitar divide by zero
        denom = (np.std(x) * np.std(y))
        autocorr = np.mean(x_m * y_m) / denom if denom > 0 else 0
    else:
        autocorr = np.nan
        
    # 3. Probabilidad de reversión inmediata (Tick Bounce)
    # Si subió, qué % de veces el siguiente tick que mueve el precio baja?
    if len(non_zero) > 1:
        signs = np.sign(non_zero)
        reversals = (signs[:-1] != signs[1:]).sum()
        rev_prob = reversals / len(signs[:-1])
    else:
        rev_prob = np.nan
        
    # 4. Distribución horaria (UTC)
    hours = (ts.astype(np.int64) // 3600000) % 24
    hour_counts = np.bincount(hours, minlength=24)
    peak_hour = np.argmax(hour_counts)
    
    # 5. Volatilidad (recorrido bruto por tick en ticks)
    avg_move = np.mean(np.abs(non_zero)) / tick
    
    print(f"  Total Ticks        : {n_ticks:,}")
    print(f"  Spread Mediano     : {median_spread:.1f} ticks")
    print(f"  Spread P99         : {p99_spread:.1f} ticks")
    print(f"  Tamaño Mov. Medio  : {avg_move:.2f} ticks")
    print(f"  Autocorr. Lag-1    : {autocorr:+.3f} (Negativo = Reversión, Positivo = Inercia)")
    print(f"  Prob. Reversión    : {rev_prob*100:.1f}% (50% es random walk)")
    print(f"  Hora Pico (UTC)    : {peak_hour}:00")

def main():
    profile_asset("EURUSD", EURUSD_TICKS, INSTRUMENTS["EURUSD"])
    if NQ_TICKS_CLEAN.exists():
        profile_asset("NQ", NQ_TICKS_CLEAN, INSTRUMENTS["NQ"])
    if ES_TICKS.exists():
        profile_asset("ES", ES_TICKS, INSTRUMENTS["ES"])

if __name__ == "__main__":
    main()
