#!/usr/bin/env python3
"""Recorta ES 09-26 a las últimas 10 sesiones interiores completas (2026-07-14 a 2026-07-27) con guardrail streaming completo."""
import hashlib
import sys
from pathlib import Path

SOURCE_PATH = Path("E:/EdgeLab/data/nt8/ES/ES 09-26.Last.txt")
DEST_PATH = Path("E:/EdgeLab/data/nt8/ES/ES 09-26.10sessions.Last.txt")
TICK_SIZE = 0.25

START_LINE = 20560762
END_LINE   = 30490824

def main():
    print(f"[*] Recortando {SOURCE_PATH.name} desde línea {START_LINE:,} hasta {END_LINE:,}...")
    
    total_written = 0
    prev_px = None
    min_nonzero_dpx = float("inf")
    off_grid_last = 0
    off_grid_bid = 0
    off_grid_ask = 0
    missing_bid = 0
    missing_ask = 0
    malformed_lines = 0
    
    with open(SOURCE_PATH, "r", encoding="utf-8", errors="ignore") as src, \
         open(DEST_PATH, "w", encoding="utf-8", newline="\n") as dst:
        
        for idx, line in enumerate(src, 1):
            if idx < START_LINE:
                continue
            if idx > END_LINE:
                break
            dst.write(line)
            total_written += 1
            
            parts = line.strip().split(";")
            if len(parts) < 5:
                malformed_lines += 1
                continue
            try:
                p = float(parts[1])
                b = float(parts[2])
                a = float(parts[3])
                
                # Check grid alignment
                if abs(p / TICK_SIZE - round(p / TICK_SIZE)) > 1e-5:
                    off_grid_last += 1
                if b > 0 and abs(b / TICK_SIZE - round(b / TICK_SIZE)) > 1e-5:
                    off_grid_bid += 1
                elif b <= 0:
                    missing_bid += 1
                    
                if a > 0 and abs(a / TICK_SIZE - round(a / TICK_SIZE)) > 1e-5:
                    off_grid_ask += 1
                elif a <= 0:
                    missing_ask += 1
                    
                if prev_px is not None:
                    dpx = abs(p - prev_px)
                    if dpx > 1e-6 and dpx < min_nonzero_dpx:
                        min_nonzero_dpx = dpx
                prev_px = p
            except Exception:
                malformed_lines += 1
                
    # Compute sha256 from final closed file
    h = hashlib.sha256()
    dest_size = DEST_PATH.stat().st_size
    with open(DEST_PATH, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    dest_sha = h.hexdigest()
    
    print(f"[+] Archivo recortado generado: {DEST_PATH}")
    print(f"    Lineas / Ticks: {total_written:,}")
    print(f"    Bytes:          {dest_size:,} bytes ({dest_size/1e6:.2f} MB)")
    print(f"    SHA256:         {dest_sha}")
    
    print(f"\n[*] Guardrail Tick Size (Escaneo Streaming Completo de {total_written:,} ticks):")
    print(f"    Minimo |d_precio| no nulo: {min_nonzero_dpx}")
    print(f"    Off-grid Last:             {off_grid_last}")
    print(f"    Off-grid Bid:              {off_grid_bid}")
    print(f"    Off-grid Ask:              {off_grid_ask}")
    print(f"    Missing Bid:               {missing_bid}")
    print(f"    Missing Ask:               {missing_ask}")
    print(f"    Malformed Lines:           {malformed_lines}")
    
    if abs(min_nonzero_dpx - TICK_SIZE) > 1e-5:
        print(f"[-] ERROR CRITICO: El tick size ({min_nonzero_dpx}) NO es {TICK_SIZE}.")
        sys.exit(1)
    if off_grid_last > 0 or off_grid_bid > 0 or off_grid_ask > 0 or malformed_lines > 0:
        print(f"[-] ERROR CRITICO: Se encontraron violaciones de grid o líneas malformadas.")
        sys.exit(1)
    print(f"[+] PASS: Guardrail completo aprobado sin violaciones.")

if __name__ == '__main__':
    main()
