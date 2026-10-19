#!/usr/bin/env python3
"""Recorta ES 09-26 a trade date >= 2026-07-27 y valida el tick size."""
import hashlib
import math
import os
import sys
from pathlib import Path
import numpy as np

SOURCE_PATH = Path('E:/EdgeLab/data/nt8/ES/ES 09-26.Last.txt')
DEST_PATH = Path('E:/EdgeLab/data/nt8/ES/ES 09-26.frontmonth.Last.txt')
START_LINE = 29366964  # Primera línea de trade date 20260727 (2026-07-26 22:00:00 UTC)

def main():
    print(f"[*] Recortando {SOURCE_PATH.name} desde la línea {START_LINE:,}...")
    
    total_written = 0
    prices = []
    
    h = hashlib.sha256()
    with open(SOURCE_PATH, 'r', encoding='utf-8', errors='ignore') as src, \
         open(DEST_PATH, 'w', encoding='utf-8', newline='\n') as dst:
        
        for idx, line in enumerate(src, 1):
            if idx < START_LINE:
                continue
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
    print(f"    Líneas / Ticks: {total_written:,}")
    print(f"    Bytes:          {dest_size:,} bytes ({dest_size/1e6:.2f} MB)")
    print(f"    SHA256:         {dest_sha}")
    
    # PASO 0b: Guardrail de tick size
    px_arr = np.array(prices, dtype=np.float64)
    diffs = np.abs(np.diff(px_arr))
    nonzero_diffs = diffs[diffs > 1e-6]
    min_diff = np.min(nonzero_diffs) if len(nonzero_diffs) > 0 else float('nan')
    unique_small_diffs = np.unique(np.round(nonzero_diffs[:5000], 4))[:10]
    
    print(f"\n[*] PASO 0b - Guardrail Tick Size:")
    print(f"    Minimo |d_precio| no nulo observado: {min_diff}")
    print(f"    Primeras diferencias no nulas:     {unique_small_diffs}")
    
    if abs(min_diff - 0.25) > 1e-5:
        print(f"[-] ERROR CRITICO: El tick size observado ({min_diff}) NO es 0.25.")
        sys.exit(1)
    else:
        print(f"[+] PASS: Tick size confirmado exactamente en 0.25 (CME ES).")

if __name__ == '__main__':
    main()
