#!/usr/bin/env python3
"""Auditoría de paridad del loader rápido vs loader canónico en ES 09-26.10sessions.Last.txt."""
import sys
import hashlib
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.sweep_bigtrap2_tickframes import load_canonical_ticks
from tools.run_mbt_export import load_canonical_ticks_fast

TAPE = Path("E:/EdgeLab/data/nt8/ES/ES 09-26.10sessions.Last.txt")
TICK_SIZE = 0.25

def hash_array(arr: np.ndarray) -> str:
    h = hashlib.sha256()
    h.update(arr.tobytes())
    return h.hexdigest()

def main():
    print(f"[*] Auditando cinta: {TAPE.name} ({TAPE.stat().st_size/1e6:.1f} MB)...")
    
    # 1. Chequeo de malformed lines, missing bids/asks, off-grid
    malformed_lines = 0
    missing_bid = 0
    missing_ask = 0
    off_grid_last = 0
    off_grid_bid = 0
    off_grid_ask = 0
    prev_px = None
    min_nonzero_dpx = float("inf")
    total_lines = 0
    
    with open(TAPE, "r", encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f, 1):
            total_lines += 1
            parts = line.strip().split(";")
            if len(parts) < 5:
                malformed_lines += 1
                continue
            try:
                p = float(parts[1])
                b = float(parts[2])
                a = float(parts[3])
                v = float(parts[4])
                
                # Check off grid
                if abs(p / TICK_SIZE - round(p / TICK_SIZE)) > 1e-5:
                    off_grid_last += 1
                if b > 0 and abs(b / TICK_SIZE - round(b / TICK_SIZE)) > 1e-5:
                    off_grid_bid += 1
                if a > 0 and abs(a / TICK_SIZE - round(a / TICK_SIZE)) > 1e-5:
                    off_grid_ask += 1
                    
                if b <= 0:
                    missing_bid += 1
                if a <= 0:
                    missing_ask += 1
                    
                if prev_px is not None:
                    dpx = abs(p - prev_px)
                    if dpx > 1e-6 and dpx < min_nonzero_dpx:
                        min_nonzero_dpx = dpx
                prev_px = p
            except Exception:
                malformed_lines += 1
                
    print(f"[*] Escaneo de cinta completo:")
    print(f"    Total líneas:      {total_lines:,}")
    print(f"    Malformed lines:   {malformed_lines}")
    print(f"    Missing bid (<=0): {missing_bid}")
    print(f"    Missing ask (<=0): {missing_ask}")
    print(f"    Off-grid Last:     {off_grid_last}")
    print(f"    Off-grid Bid:      {off_grid_bid}")
    print(f"    Off-grid Ask:      {off_grid_ask}")
    print(f"    Mínimo |d_px| > 0: {min_nonzero_dpx}")
    
    # 2. Carga con loader rápido
    print(f"\n[*] Cargando con load_canonical_ticks_fast...")
    ticks_fast = load_canonical_ticks_fast(TAPE, tick_size=TICK_SIZE)
    
    # 3. Carga con loader canónico
    print(f"\n[*] Cargando con load_canonical_ticks...")
    ticks_canon, _, _, _, _, _ = load_canonical_ticks(TAPE, tick_size=TICK_SIZE)
    
    # 4. Comparación de columnas
    print(f"\n[*] Comparando atributos:")
    n_f = len(ticks_fast)
    n_c = len(ticks_canon)
    print(f"    Ticks count: Fast={n_f:,}, Canon={n_c:,} -> {'MATCH' if n_f == n_c else 'FAIL'}")
    
    h_ts_f = hash_array(ticks_fast.ts_ns)
    h_ts_c = hash_array(ticks_canon.ts_ns)
    print(f"    ts_ns:       Fast={h_ts_f[:16]}..., Canon={h_ts_c[:16]}... -> {'MATCH' if h_ts_f == h_ts_c else 'FAIL'}")
    if h_ts_f != h_ts_c:
        diff = np.abs(ticks_fast.ts_ns - ticks_canon.ts_ns)
        print(f"        Max diff ts_ns: {np.max(diff)} ns")
        print(f"        Mean diff ts_ns: {np.mean(diff)} ns")
        
    h_px_f = hash_array(ticks_fast.price_ticks)
    h_px_c = hash_array(ticks_canon.price_ticks)
    print(f"    price_ticks: Fast={h_px_f[:16]}..., Canon={h_px_c[:16]}... -> {'MATCH' if h_px_f == h_px_c else 'FAIL'}")
    
    h_bid_f = hash_array(ticks_fast.bid_ticks)
    h_bid_c = hash_array(ticks_canon.bid_ticks)
    print(f"    bid_ticks:   Fast={h_bid_f[:16]}..., Canon={h_bid_c[:16]}... -> {'MATCH' if h_bid_f == h_bid_c else 'FAIL'}")
    
    h_ask_f = hash_array(ticks_fast.ask_ticks)
    h_ask_c = hash_array(ticks_canon.ask_ticks)
    print(f"    ask_ticks:   Fast={h_ask_f[:16]}..., Canon={h_ask_c[:16]}... -> {'MATCH' if h_ask_f == h_ask_c else 'FAIL'}")
    
    h_vol_f = hash_array(ticks_fast.volume)
    h_vol_c = hash_array(ticks_canon.volume)
    print(f"    volume:      Fast={h_vol_f[:16]}..., Canon={h_vol_c[:16]}... -> {'MATCH' if h_vol_f == h_vol_c else 'FAIL'}")
    
    h_seq_f = hash_array(ticks_fast.sequence)
    h_seq_c = hash_array(ticks_canon.sequence)
    print(f"    sequence:    Fast={h_seq_f[:16]}..., Canon={h_seq_c[:16]}... -> {'MATCH' if h_seq_f == h_seq_c else 'FAIL'}")

if __name__ == '__main__':
    main()
