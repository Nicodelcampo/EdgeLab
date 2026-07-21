"""Estrategia Spread Squeeze Fade para EURUSD.

Detecta picos anormales de ensanchamiento de spread (falta de liquidez).
Cuando el spread se normaliza, toma un trade de mean-reversion asumiendo
que el precio fue movido por la iliquidez más que por flujo direccional.
"""
import numpy as np
from numba import njit

TICK = 1.0
RTH0, RTH1 = 7, 17 # London + NY
COOLDOWN_MS = 120_000
MAX_HOLD_MS = 300_000

TP_GRID = np.array([20, 40, 60, 100, 140, 200], dtype=np.float64) # 2 a 20 pips
SL_GRID = np.array([10, 20, 30, 50, 70], dtype=np.float64)        # 1 a 7 pips
HEADLINE = (100.0, 30.0) # tp=10 pips, sl=3 pips

SPIKE_MULT = 3.0
RECOVERY_MULT = 1.5
LOOKBACK_MS = 60000 # 60 segundos

@njit(cache=True)
def _spread_signals(times_ms, last, bid, ask, rth0, rth1, spike_mult, recov_mult, lookback_ms, cooldown_ms):
    n = len(last)
    idx = np.empty(n // 50 + 16, np.int64)
    dirs = np.empty(n // 50 + 16, np.int64)
    m = 0
    
    last_sig = -np.int64(1) << 60
    
    st = 0
    in_spike = False
    spike_direction = 0 # Dirección en la que se movió el midprice durante el spike
    pre_spike_mid = 0.0
    
    # Usar media simple en vez de mediana completa por rendimiento (O(N) vs O(N log N) en sliding window)
    # Una ventana de spread rolling:
    sum_spread = 0.0
    count_spread = 0
    
    for i in range(1, n - 2):
        t = times_ms[i]
        
        # Mantener ventana para media de spread
        sum_spread += (ask[i] - bid[i])
        count_spread += 1
        
        while st < i and t - times_ms[st] > lookback_ms:
            sum_spread -= (ask[st] - bid[st])
            count_spread -= 1
            st += 1
            
        h = (t // 3600000) % 24
        if h < rth0 or h >= rth1 or t - last_sig < cooldown_ms:
            continue
            
        if count_spread < 10:
            continue
            
        mean_spread = sum_spread / count_spread
        current_spread = ask[i] - bid[i]
        
        if not in_spike:
            if current_spread > mean_spread * spike_mult:
                in_spike = True
                pre_spike_mid = last[st] # Precio aproximado antes del spike (hace 60s)
        else:
            if current_spread < mean_spread * recov_mult:
                # El spread se recuperó
                in_spike = False
                
                # En qué dirección se movió el precio por la falta de liquidez?
                if last[i] > pre_spike_mid:
                    # Subió artificialmente -> short
                    idx[m] = i
                    dirs[m] = -1
                    m += 1
                    last_sig = t
                elif last[i] < pre_spike_mid:
                    # Bajó artificialmente -> long
                    idx[m] = i
                    dirs[m] = 1
                    m += 1
                    last_sig = t
                    
    return idx[:m], dirs[:m]

def señales(times_ms, last, bid, ask):
    return _spread_signals(times_ms, last, bid, ask, RTH0, RTH1, SPIKE_MULT, RECOVERY_MULT, LOOKBACK_MS, COOLDOWN_MS)
