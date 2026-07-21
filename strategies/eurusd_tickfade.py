"""Estrategia de Reversión a la media de impulsos para EURUSD.

Detecta movimientos agresivos de |X| pips en menos de Y segundos y 
apuesta a la reversión (fade). El EURUSD es altamente líquido y tiende
a absorber choques rápidos.
"""
import numpy as np
from numba import njit

TICK = 1.0
# RTH: 07:00 a 17:00 UTC (London + NY overlap)
RTH0, RTH1 = 7, 17
COOLDOWN_MS = 60_000
MAX_HOLD_MS = 300_000

# Grids y headline
TP_GRID = np.array([30, 50, 80, 120, 160, 240], dtype=np.float64) # 3 a 24 pips
SL_GRID = np.array([15, 25, 40, 60, 80], dtype=np.float64)        # 1.5 a 8 pips
HEADLINE = (120.0, 40.0) # tp=12 pips, sl=4 pips

# Parámetros del impulso
MOVE_T = 80       # 8 pips de movimiento
WINDOW_MS = 5000  # en 5 segundos

@njit(cache=True)
def _impulse_signals(times_ms, last, rth0, rth1, move_t, window_ms, cooldown_ms, tick):
    n = len(last)
    idx = np.empty(n // 50 + 16, np.int64)
    dirs = np.empty(n // 50 + 16, np.int64)
    m = 0
    last_sig = -np.int64(1) << 60
    st = 0
    
    for i in range(1, n - 2):
        t = times_ms[i]
        
        while t - times_ms[st] > window_ms:
            st += 1
            
        h = (t // 3600000) % 24
        if h < rth0 or h >= rth1 or t - last_sig < cooldown_ms:
            continue
            
        dlt = (last[i] - last[st]) / tick
        
        if dlt >= move_t:
            idx[m] = i
            dirs[m] = -1 # fade: short
            m += 1
            last_sig = t
        elif dlt <= -move_t:
            idx[m] = i
            dirs[m] = 1 # fade: long
            m += 1
            last_sig = t
            
    return idx[:m], dirs[:m]

def señales(times_ms, last, bid, ask):
    return _impulse_signals(times_ms, last, RTH0, RTH1, MOVE_T, WINDOW_MS, COOLDOWN_MS, TICK)
