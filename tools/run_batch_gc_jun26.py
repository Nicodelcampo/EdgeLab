#!/usr/bin/env python3
"""Batch converter para todas las sesiones de GC JUN26 excepto la sellada 20260618.csv."""
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.convert_l2_to_parquet import convert_one_file

INPUT_DIR = Path("E:/DatosNT8/replay.csv/GC JUN26")
OUTPUT_DIR = Path("E:/DatosNT8/replay.csv/GC JUN26/parquet_out")
SEALED_SESSION = "20260618.csv"
INSTRUMENT = "GC 06-26"
TICK_SIZE = 0.1

def main():
    csv_files = sorted([f for f in INPUT_DIR.glob("*.csv") if f.is_file()])
    print(f"[*] Encontrados {len(csv_files)} archivos CSV en {INPUT_DIR.name}")
    
    converted_count = 0
    t0_total = time.time()
    
    for idx, f in enumerate(csv_files, 1):
        if f.name == SEALED_SESSION:
            print(f"[{idx}/{len(csv_files)}] SALTANDO SESIÓN SELLADA: {f.name} (NO LEER / NO CONVERTIR)")
            continue

        manifest_file = OUTPUT_DIR / "manifests" / f"{f.stem}.manifest.json"
        if manifest_file.is_file():
            print(f"[{idx}/{len(csv_files)}] {f.name} ya convertido (manifest existe). Saltando.")
            converted_count += 1
            continue
        t0 = time.time()
        
        manifest = convert_one_file(
            f,
            OUTPUT_DIR,
            instrument=INSTRUMENT,
            tick_size=TICK_SIZE,
            chunk_rows=500_000,
            overwrite=False,
            allow_dirty=False,
        )
        
        dt = time.time() - t0
        rows = manifest["source"]["rows"]
        l2_rows = manifest["outputs"]["l2_depth"]["rows"]
        l1_rows = manifest["outputs"]["l1_quotes"]["rows"]
        print(f"  OK: rows={rows:,} (L2={l2_rows:,}, L1={l1_rows:,}) en {dt:.1f}s")
        converted_count += 1
        
    print(f"\n[+] Proceso completado: {converted_count} sesiones convertidas en {time.time() - t0_total:.1f}s.")

if __name__ == '__main__':
    main()
