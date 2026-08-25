#!/usr/bin/env python3
"""Recorta ES 09-26 a las últimas 10 sesiones interiores completas (2026-07-14 a 2026-07-27)."""
import hashlib
import sys
from pathlib import Path
import numpy as np

SOURCE_PATH = Path('E:/EdgeLab/data/nt8/ES/ES 09-26.Last.txt')
DEST_PATH = Path('E:/EdgeLab/data/nt8/ES/ES 09-26.10sessions.Last.txt')

# Sesiones interiores completas:
# Sesión 1: 20260714 (inicio: 2026-07-13 22:00:00 UTC, línea 20,560,762)
# Sesión 10: 20260727 (fin: 2026-07-27 20:59:58 UTC, línea 30,490,824)
START_LINE = 20560762
END_LINE   = 30490824

def main():
    print(f"[*] Recortando {SOURCE_PATH.name} desde línea {START_LINE:,} hasta {END_LINE:,}...")
    
    total_written = 0
    prices = []
    
    h = hashlib.sha256()
    with open(SOURCE_PATH, 'r', encoding='utf-8', errors='ignore') as src, \
         open(DEST_PATH, 'w', encoding='utf-8', newline='\n') as dst:
        
        for idx, line in enumerate(src, 1):
            if idx < START_LINE:
                continue
            if idx > END_LINE:
                break
            dst.write(line)
            h.update(line.encode('utf-8'))
            total_written += 1
            if total_written <= 50000:
                parts = line.strip().split(';')
                if len(parts) >= 2:
                    prices.append(float(parts[1]))
                    
    dest_size = DEST_PATH.stat().st_size
    dest_sha = h.hexdigest()
    
    print(f"[+] Archivo recortado generado: {DEST_PATH}")
    print(f"    Lineas / Ticks: {total_written:,}")
    print(f"    Bytes:          {dest_size:,} bytes ({dest_size/1e6:.2f} MB)")
    print(f"    SHA256:         {dest_sha}")
    
    # Guardrail Tick Size
    px_arr = np.array(prices, dtype=np.float64)
    diffs = np.abs(np.diff(px_arr))
    nonzero_diffs = diffs[diffs > 1e-6]
    min_diff = np.min(nonzero_diffs) if len(nonzero_diffs) > 0 else float('nan')
    
    print(f"\n[*] Guardrail Tick Size:")
    print(f"    Minimo |d_precio| no nulo observado: {min_diff}")
    
    if abs(min_diff - 0.25) > 1e-5:
        print(f"[-] ERROR CRITICO: El tick size ({min_diff}) NO es 0.25.")
        sys.exit(1)
    else:
        print(f"[+] PASS: Tick size confirmado exactamente en 0.25 (CME ES).")

if __name__ == '__main__':
    main()
