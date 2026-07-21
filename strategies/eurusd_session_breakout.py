"""Estrategia de Session Breakout (Rango Asiático) para EURUSD.

El EURUSD suele consolidar durante la sesión asiática (00:00-07:00 UTC).
Al abrir Londres (07:00), si se rompe el rango máximo/mínimo asiático, 
apostamos por una continuación direccional.
"""
import numpy as np
from numba import njit
import pandas as pd

TICK = 1.0
RTH0, RTH1 = 7, 9  # Solo se entra de 07:00 a 09:00 UTC (London open)
MAX_HOLD_MS = 300_000 # 5 min

TP_GRID = np.array([40, 60, 100, 150, 200, 300], dtype=np.float64) # 4 a 30 pips
SL_GRID = np.array([20, 30, 50, 80, 100], dtype=np.float64)        # 2 a 10 pips
HEADLINE = (150.0, 50.0) # tp=15 pips, sl=5 pips

@njit(cache=True)
def _breakout_signals(times_ms, last, rth0, rth1):
    n = len(last)
    idx = np.empty(n // 50 + 16, np.int64)
    dirs = np.empty(n // 50 + 16, np.int64)
    m = 0
    
    current_day = -1
    hi_asian = -1.0
    lo_asian = 1e9
    
    # Flags para limitar a 1 trade por dirección por día
    long_taken = False
    short_taken = False
    
    for i in range(1, n - 2):
        t = times_ms[i]
        
        # Obtener el día juliano aproximado UTC
        day = t // 86400000 
        h = (t // 3600000) % 24
        
        if day != current_day:
            current_day = day
            hi_asian = -1.0
            lo_asian = 1e9
            long_taken = False
            short_taken = False
            
        # Acumular max/min durante sesión asiática (00:00 a 06:59 UTC)
        if h < rth0:
            if last[i] > hi_asian: hi_asian = last[i]
            if last[i] < lo_asian: lo_asian = last[i]
            continue
            
        # Solo operar si tuvimos un rango asiático válido
        if hi_asian == -1.0 or lo_asian == 1e9:
            continue
            
        # Ventana de oportunidad: 07:00 a 08:59 UTC
        if h >= rth0 and h < rth1:
            if not long_taken and last[i] > hi_asian:
                idx[m] = i
                dirs[m] = 1 # Breakout alcista
                m += 1
                long_taken = True
            elif not short_taken and last[i] < lo_asian:
                idx[m] = i
                dirs[m] = -1 # Breakout bajista
                m += 1
                short_taken = True
                
    return idx[:m], dirs[:m]

def señales(times_ms, last, bid, ask):
    return _breakout_signals(times_ms, last, RTH0, RTH1)
