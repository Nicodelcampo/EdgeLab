"""Runner unificado para el análisis del EURUSD en EdgeLab.

Carga el dataset de ticks de EURUSD, y procesa el full_audit (Gauntlet)
para las 3 estrategias de prueba.
"""
import sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from edgelab.config import EURUSD_TICKS
from validation.harness import full_audit
from edgelab.instruments import EURUSD

from strategies import eurusd_tickfade
from strategies import eurusd_session_breakout
from strategies import eurusd_spread_fade

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"Cargando {EURUSD_TICKS}...")
    try:
        tbl = pq.read_table(EURUSD_TICKS)
    except FileNotFoundError:
        print("ERROR: Archivo parquet no encontrado. Por favor corre primero databuild.build_eurusd")
        sys.exit(1)
        
    times_ms = tbl.column("timestamp").to_numpy(zero_copy_only=False).astype("datetime64[ms]").astype(np.int64)
    last = np.round(tbl.column("last").to_numpy(zero_copy_only=False).astype(np.float64) * 100000.0, 1)
    bid = np.round(tbl.column("bid").to_numpy(zero_copy_only=False).astype(np.float64) * 100000.0, 1)
    ask = np.round(tbl.column("ask").to_numpy(zero_copy_only=False).astype(np.float64) * 100000.0, 1)
    print(f"{len(last):,} ticks cargados")
    
    # Fees de EURUSD (RT): ~2.0 pipettes (costo exchange/broker) + el bid/ask spread cruzado por el motor
    FEES_RT_EURUSD = 2.0
    TICK_SIZE = 1.0
    TICK_VAL = EURUSD.tick_value
    
    jobs = [
        ("EURUSD Impulse Fade", eurusd_tickfade.señales, eurusd_tickfade.TP_GRID, eurusd_tickfade.SL_GRID, eurusd_tickfade.HEADLINE, eurusd_tickfade.MAX_HOLD_MS),
        ("EURUSD Session Breakout", eurusd_session_breakout.señales, eurusd_session_breakout.TP_GRID, eurusd_session_breakout.SL_GRID, eurusd_session_breakout.HEADLINE, eurusd_session_breakout.MAX_HOLD_MS),
        ("EURUSD Spread Squeeze Fade", eurusd_spread_fade.señales, eurusd_spread_fade.TP_GRID, eurusd_spread_fade.SL_GRID, eurusd_spread_fade.HEADLINE, eurusd_spread_fade.MAX_HOLD_MS),
    ]
    
    for name, fn, tp_grid, sl_grid, headline, max_hold in jobs:
        full_audit(
            name=name,
            signal_fn=fn,
            times_ms=times_ms,
            last=last,
            bid=bid,
            ask=ask,
            tp_grid=tp_grid,
            sl_grid=sl_grid,
            headline=headline,
            max_hold_ms=max_hold,
            tick=TICK_SIZE,
            fees=FEES_RT_EURUSD,
            tv=TICK_VAL,
            symmetric=True
        )
        print("\n\n" + "="*80 + "\n\n")

if __name__ == "__main__":
    main()
