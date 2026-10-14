#!/usr/bin/env python3
"""Escaneo ultra-rápido de sesiones CME en ES 09-26.Last.txt."""
import sys
from pathlib import Path
from datetime import datetime, timedelta

def main():
    filepath = Path(sys.argv[1] if len(sys.argv) > 1 else 'E:/EdgeLab/data/nt8/ES/ES 09-26.Last.txt')
    print(f"[*] Analizando sesiones en {filepath.name} ({filepath.stat().st_size/1e6:.1f} MB)...")
    
    sessions = []
    prev_td = None
    prev_line = 1
    count = 0
    first_tick_ts = None
    
    # Precompute cache for (YYYY, MM, DD, HH) -> trade_date
    td_cache = {}
    
    def get_td(dt_str_hour):
        # dt_str_hour is YYYYMMDD HH
        if dt_str_hour in td_cache:
            return td_cache[dt_str_hour]
        y = int(dt_str_hour[0:4])
        m = int(dt_str_hour[4:6])
        d = int(dt_str_hour[6:8])
        hh = int(dt_str_hour[9:11])
        dt = datetime(y, m, d, hh, 0, 0)
        # CME Chicago (CDT = UTC-5 in summer):
        # 17:00 CDT = 22:00 UTC
        # If UTC hour >= 22: belongs to next trading day
        # If Saturday: no regular session; if Sunday before 22: pre-open
        if hh >= 22:
            # Advance to next day
            dt_next = dt + timedelta(days=1)
            # If next day is Saturday, advance to Monday
            if dt_next.weekday() == 5:
                dt_next += timedelta(days=2)
            td_str = dt_next.strftime('%Y%m%d')
        else:
            # Current day
            # If Sunday before 22 UTC -> Monday
            if dt.weekday() == 6:
                dt_next = dt + timedelta(days=1)
                td_str = dt_next.strftime('%Y%m%d')
            elif dt.weekday() == 5: # Saturday
                dt_next = dt + timedelta(days=2)
                td_str = dt_next.strftime('%Y%m%d')
            else:
                td_str = dt.strftime('%Y%m%d')
        td_cache[dt_str_hour] = td_str
        return td_str

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for idx, line in enumerate(f, 1):
            if len(line) < 15:
                continue
            hour_str = line[:11]
            td = get_td(hour_str)
            
            if prev_td is None:
                prev_td = td
                prev_line = idx
                count = 1
                first_tick_ts = line[:15]
            elif td != prev_td:
                sessions.append({
                    'td': prev_td,
                    'start_line': prev_line,
                    'end_line': idx - 1,
                    'ticks': count,
                    'first_ts': first_tick_ts,
                    'last_ts': last_tick_ts
                })
                prev_td = td
                prev_line = idx
                count = 1
                first_tick_ts = line[:15]
            else:
                count += 1
            last_tick_ts = line[:15]
            
        if count > 0:
            sessions.append({
                'td': prev_td,
                'start_line': prev_line,
                'end_line': idx,
                'ticks': count,
                'first_ts': first_tick_ts,
                'last_ts': last_tick_ts
            })
            
    print(f"\nTotal sesiones detectadas: {len(sessions)}")
    for s in sessions:
        print(f"Sesion {s['td']}: lineas {s['start_line']:10,d} a {s['end_line']:10,d} ({s['ticks']:9,d} ticks) | {s['first_ts']} -> {s['last_ts']}")

if __name__ == '__main__':
    main()
