"""EXP-029/030: Sweep/Impulse Fade con causalidad Bid/Ask (Regla 8).

Este motor implementa la logica original de reversion de la serie ES, pero
ejecutada bajo las restricciones estrictas de EdgeLab:
- Las compras llenan al ASK, las ventas al BID.
- El Stop Loss paga spread cruzando el bid/ask del tick que lo gatilla.
- El TP se llena limitadamente si el bid/ask adverso lo penetra o toca.

Se conecta a `validation.verify.preflight` para asegurar que el codigo
este libre de lookahead, bugs de signo o asimetrias.

Ejecutar: python -m strategies.tick_fade
"""
import sys
import time
import numpy as np
import pandas as pd
from numba import njit

from edgelab.config import ES_TICKS
from validation.verify import preflight

TICK = 0.25
TV = 12.5
COST = 0.5  # Comision round-trip. El spread ya esta pagado en la ejecucion.

# ==============================================================================
# 1. KERNEL DE NUMBA (El Motor Causal)
# ==============================================================================

@njit(cache=True)
def tick_fade_engine(times_ms, last, bid, ask, tick, 
                     move_ticks, window_ms, cooldown_ms, 
                     tp_ticks, sl_ticks, max_hold_ms):
    """
    Motor que detecta el Impulse Fade (movimiento rapido en un sentido -> operar en contra).
    Retorna arrays compatibles con el dataframe del ledger.
    """
    n = len(times_ms)
    max_trades = 200000
    
    # Outputs del ledger
    t_dir = np.zeros(max_trades, dtype=np.int64)
    t_entry_px = np.full(max_trades, np.nan, dtype=np.float64)
    t_exit_px = np.full(max_trades, np.nan, dtype=np.float64)
    t_pnl = np.full(max_trades, np.nan, dtype=np.float64)
    t_reason = np.zeros(max_trades, dtype=np.int32) # 1: tp, 2: sl, 3: eod
    t_entry_time = np.zeros(max_trades, dtype=np.int64)
    t_exit_time = np.zeros(max_trades, dtype=np.int64)
    
    tc = 0
    last_sig_t = -999999999
    start = 0
    
    for i in range(1, n - 200):
        if tc >= max_trades: break
        
        t = times_ms[i]
        while t - times_ms[start] > window_ms:
            start += 1
            
        if t - last_sig_t < cooldown_ms:
            continue
            
        # Señal (solo usa LAST hacia atras)
        delta = (last[i] - last[start]) / tick
        d = 0
        if delta >= move_ticks: d = -1    # Sube -> Fade Short
        elif delta <= -move_ticks: d = 1  # Baja -> Fade Long
        
        if d != 0:
            last_sig_t = t
            
            # EJECUCION (Causal: ocurre en el tick i+1)
            entry_idx = i + 1
            entry_t = times_ms[entry_idx]
            
            # Fill riguroso Bid/Ask
            if d == 1:
                entry_px = ask[entry_idx]
            else:
                entry_px = bid[entry_idx]
                
            if np.isnan(entry_px): 
                continue
                
            tp_px = entry_px + d * tp_ticks * tick
            sl_px = entry_px - d * sl_ticks * tick
            
            exit_idx = -1
            exit_px = np.nan
            reason = 0
            end_time = entry_t + max_hold_ms
            
            for j in range(entry_idx + 1, n):
                if times_ms[j] >= end_time:
                    exit_idx = j
                    exit_px = bid[j] if d == 1 else ask[j]
                    reason = 3 # eod/time
                    break
                    
                if d == 1:
                    if bid[j] <= sl_px:
                        exit_idx = j; exit_px = bid[j]; reason = 2; break
                    if bid[j] >= tp_px:
                        exit_idx = j; exit_px = tp_px; reason = 1; break
                else:
                    if ask[j] >= sl_px:
                        exit_idx = j; exit_px = ask[j]; reason = 2; break
                    if ask[j] <= tp_px:
                        exit_idx = j; exit_px = tp_px; reason = 1; break
                        
            if exit_idx != -1 and not np.isnan(exit_px):
                t_dir[tc] = d
                t_entry_px[tc] = entry_px
                t_exit_px[tc] = exit_px
                t_pnl[tc] = (exit_px - entry_px) * d / tick
                t_reason[tc] = reason
                t_entry_time[tc] = entry_t
                t_exit_time[tc] = times_ms[exit_idx]
                tc += 1
                
    return t_dir[:tc], t_entry_px[:tc], t_exit_px[:tc], t_pnl[:tc], t_reason[:tc], t_entry_time[:tc], t_exit_time[:tc]


# ==============================================================================
# 2. ADAPTADOR RUN_TRADES (Para el Gauntlet)
# ==============================================================================

def run_trades_impulse(times_ms, last, bid, ask, 
                       move_ticks=8, window_ms=2000, cooldown=60000,
                       tp=8, sl=4, max_hold=300000):
    """Adaptador que cumple con la firma esperada por synthetic_check."""
    t_dir, t_en, t_ex, t_pnl, t_res, t_en_t, t_ex_t = tick_fade_engine(
        times_ms, last, bid, ask, TICK, move_ticks, window_ms, cooldown, tp, sl, max_hold
    )
    
    # Mapear reason num a str
    reason_map = {1: "tp", 2: "sl", 3: "eod", 0: "uknown"}
    reason_str = [reason_map[r] for r in t_res]
    
    df = pd.DataFrame({
        "dir": t_dir,
        "entry_px": t_en,
        "exit_px": t_ex,
        "pnl_ticks": t_pnl,
        "reason": reason_str,
        "entry_t": t_en_t,
        "exit_t": t_ex_t
    })
    return df


# ==============================================================================
# 3. EJECUCION
# ==============================================================================

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Cargando ES_ticks.parquet (timestamp, last, bid, ask)...")
    
    try:
        tape = pd.read_parquet(ES_TICKS, columns=["ts_ns", "last", "bid", "ask"])
        times_ms = tape["ts_ns"].to_numpy() // 1_000_000
    except Exception:
        # Fallback al archivo nativo del viejo ecosistema para pruebas si ES_TICKS_CLEAN falla
        tape = pd.read_parquet(r"C:\$AVectorBTecosistema\ES_ticks.parquet", columns=["timestamp", "last", "bid", "ask"])
        times_ms = tape["timestamp"].values.astype("datetime64[ms]").astype(np.int64)
        
    last = tape["last"].to_numpy(np.float64)
    bid = tape["bid"].to_numpy(np.float64)
    ask = tape["ask"].to_numpy(np.float64)
    
    # 1. PREFLIGHT GAUNTLET
    ok = preflight("Tick Impulse Fade (Causal Bid/Ask)", run_trades_impulse, 
                   times_ms, last, bid, ask, tick=TICK, cost=COST)
                   
    if not ok:
        print("\nEl motor fallo la validacion de seguridad. Abortando ejecucion sobre datos reales.")
        sys.exit(1)
        
    # 2. EJECUCION REAL
    print("\nPreflight superado. Ejecutando motor causal sobre toda la cinta...")
    t0 = time.time()
    df = run_trades_impulse(times_ms, last, bid, ask)
    
    if len(df) == 0:
        print("Cero trades generados.")
        return
        
    pnl_net = df["pnl_ticks"] - COST
    exp = pnl_net.mean()
    win = (pnl_net > 0).mean() * 100
    
    print(f"\nRESULTADO FINAL (Spread Real y Causalidad):")
    print(f"Trades: {len(df)}")
    print(f"Win Rate: {win:.1f}%")
    print(f"Expectancy: {exp:+.2f} ticks (${exp * TV:+.2f})")
    print(f"Total Net PnL: {pnl_net.sum():+.2f} ticks")
    print(f"Tiempo de simulacion: {time.time() - t0:.2f}s")


if __name__ == "__main__":
    main()
