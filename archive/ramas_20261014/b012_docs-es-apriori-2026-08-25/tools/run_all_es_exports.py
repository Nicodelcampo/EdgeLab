import sys
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.run_mbt_export import run_export, load_canonical_ticks_fast
from edgelab.bridge.bars import session_ids

TAPE = Path("E:/EdgeLab/data/nt8/ES/ES 09-26.10sessions.Last.txt")
OUT_DIR = Path("E:/DatosNT8/es_apriori")

def main():
    print(f"[*] Iniciando bateria de exports sobre {TAPE.name} ({TAPE.stat().st_size/1e6:.1f} MB)...")
    
    ticks = load_canonical_ticks_fast(TAPE, tick_size=0.25)
    print(f"[*] Calculando trade dates para {len(ticks):,} ticks...")
    s_ids = session_ids(ticks.ts_ns)
    trade_dates = pd.to_datetime(s_ids * 86400, unit="s").strftime("%Y%m%d").values
    print(f"[*] Trade dates listos ({len(set(trade_dates))} sesiones).")
    
    # 1. Grilla canonica (TW in {10, 15, 25, 50}, rows=2, tpr=1)
    for tw in [10, 15, 25, 50]:
        run_export(TAPE, OUT_DIR, tape_window_ticks=tw, tick_size=0.25, min_stacked_rows=2, ticks_per_row=1, prefix="es_export", ticks=ticks, trade_dates=trade_dates)
        
    # 2. Comparacion directa con MinStackedRows=1 (TW=25, rows=1, tpr=1)
    run_export(TAPE, OUT_DIR, tape_window_ticks=25, tick_size=0.25, min_stacked_rows=1, ticks_per_row=1, prefix="es_export", ticks=ticks, trade_dates=trade_dates)
    
    # 3. Exploratorias de escala temporal (TW=100, 200, rows=2, tpr=1)
    for tw in [100, 200]:
        run_export(TAPE, OUT_DIR, tape_window_ticks=tw, tick_size=0.25, min_stacked_rows=2, ticks_per_row=1, prefix="es_export", ticks=ticks, trade_dates=trade_dates)
        
    # 4. Exploratoria de escala de precio (TW=25, rows=2, tpr=2)
    run_export(TAPE, OUT_DIR, tape_window_ticks=25, tick_size=0.25, min_stacked_rows=2, ticks_per_row=2, prefix="es_export", ticks=ticks, trade_dates=trade_dates)
    
    print("\n[+] Bateria completa de exports finalizada.")

if __name__ == '__main__':
    main()
