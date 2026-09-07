# -*- coding: utf-8 -*-
"""Compara la liquidez y tamaño entre GC JUN26 y GC AUG26."""
from pathlib import Path

def main():
    p_jun = Path("E:/DatosNT8/replay_gc0826_raw_csv/GC JUN26")
    p_aug = Path("E:/DatosNT8/replay_gc0826_raw_csv/GC AUG26")

    jun_files = {f.stem: f for f in p_jun.glob("*.csv") if f.stat().st_size > 1024*1024}
    aug_files = {f.stem: f for f in p_aug.glob("*.csv") if f.stat().st_size > 1024*1024 and int(f.stem) <= 20260630}

    all_dates = sorted(set(jun_files.keys()).union(set(aug_files.keys())))

    print("=== COMPARATIVA DE TAMAÑO Y LIQUIDEZ PRE-HOLDOUT (HASTA 30-JUN-2026) ===")
    print(f"{'Fecha':<10} | {'GC JUN26 (MB)':<15} | {'GC AUG26 (MB)':<15} | {'Ratio AUG/JUN':<15} | {'Contrato Dominante'}")
    print("-" * 80)

    aug_dominant_count = 0
    jun_dominant_count = 0

    for d in all_dates:
        sz_jun = jun_files[d].stat().st_size / (1024*1024) if d in jun_files else 0.0
        sz_aug = aug_files[d].stat().st_size / (1024*1024) if d in aug_files else 0.0
        ratio = (sz_aug / sz_jun) if sz_jun > 0 else 999.0
        if sz_aug > sz_jun:
            dom = "GC 08-26 (AUG) [FRONT MONTH]"
            aug_dominant_count += 1
        else:
            dom = "GC 06-26 (JUN) [EXPIRING]"
            jun_dominant_count += 1
            
        print(f"{d:<10} | {sz_jun:<15.2f} | {sz_aug:<15.2f} | {ratio:<15.2f} | {dom}")

    print("-" * 80)
    print(f"Total fechas evaluadas: {len(all_dates)}")
    print(f"Fechas donde GC AUG26 fue el contrato dominante de liquidez: {aug_dominant_count}")
    print(f"Fechas donde GC JUN26 fue mayor: {jun_dominant_count}")

if __name__ == "__main__":
    main()
