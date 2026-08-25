#!/usr/bin/env python3
"""Encuentra las fronteras de sesión en cintas .Last.txt."""
import sys
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.bars import session_ids

def main():
    filepath = Path(sys.argv[1] if len(sys.argv) > 1 else 'E:/EdgeLab/data/nt8/ES/ES 09-26.Last.txt')
    print(f"[*] Analizando fronteras de sesión en {filepath.name} ({filepath.stat().st_size/1e6:.1f} MB)...")
    
    sessions = []
    prev_td = None
    prev_line = 1
    count = 0
    first_tick_ts = None
    last_checked_ts = None
    last_td = None
    
    # We sample timestamps: when day or hour changes, we evaluate session_id
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for idx, line in enumerate(f, 1):
            # Check every 10,000 lines or on hour transition
            dt_str = line[:15]
            if len(dt_str) < 15:
                continue
            
            # Extract YYYYMMDD HHMMSS
            y = int(dt_str[0:4])
            m = int(dt_str[4:6])
            d = int(dt_str[6:8])
            hh = int(dt_str[9:11])
            mm = int(dt_str[11:13])
            ss = int(dt_str[13:15])
            
            # Fast trade date:
            # 17:00 CDT = 22:00 UTC. Any tick at UTC hour >= 22 rolls to next day.
            # Convert to date and check
            dt_date = datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)
            t_ns = int(dt_date.timestamp() * 1_000_000_000)
            
            # To be 100% exact to session_ids but vectorized/fast, we check if dt_str != last_str:
            if idx == 1 or dt_str != last_checked_ts:
                s_id = session_ids([t_ns])[0]
                td = pd.to_datetime(s_id * 86400, unit='s').strftime('%Y%m%d')
                last_checked_ts = dt_str
                last_td = td
            else:
                td = last_td
            
            if prev_td is None:
                prev_td = td
                prev_line = idx
                count = 1
                first_tick_ts = dt_str
            elif td != prev_td:
                sessions.append({
                    'td': prev_td,
                    'start_line': prev_line,
                    'end_line': idx - 1,
                    'ticks': count,
                    'first_ts': first_tick_ts,
                    'last_ts': dt_str
                })
                prev_td = td
                prev_line = idx
                count = 1
                first_tick_ts = dt_str
            else:
                count += 1
                
        if count > 0:
            sessions.append({
                'td': prev_td,
                'start_line': prev_line,
                'end_line': idx,
                'ticks': count,
                'first_ts': first_tick_ts,
                'last_ts': dt_str
            })
            
    print(f"\nTotal sesiones detectadas: {len(sessions)}")
    df = pd.DataFrame(sessions)
    print(df.to_string(index=False))

if __name__ == '__main__':
    main()
