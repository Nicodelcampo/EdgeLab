"""
validate_nq0626_parity_run.py — validación post-corrida de paridad aVolClusterPOI NQ 06-26
Ejecutar DESPUÉS de cerrar el chart en NT8 para confirmar que los tres CSVs son válidos.
"""
import os, sys, csv

BASE = r"D:\EdgeLab-nq-parity\data\nt8_oracles"

FILES = {
    "oracle":     os.path.join(BASE, "avolcluster_v05_NQ0626_120t_20260407_20260612_v2.csv"),
    "barprofile":  os.path.join(BASE, "avolcluster_v05_NQ0626_120t_BARPROFILE_20260902.csv"),
    "diag_blocks": os.path.join(BASE, "avolcluster_v05_NQ0626_120t_DIAG_BLOCKS_20260902.csv"),
}

def validate():
    errors = []
    for label, path in FILES.items():
        if not os.path.isfile(path):
            errors.append(f"MISSING: {label} -> {path}")
            continue
        size = os.path.getsize(path)
        with open(path, "r", encoding="utf-8") as f:
            meta = f.readline().strip()
            header = f.readline().strip()
            rows = sum(1 for _ in f)

        print(f"\n{'='*60}")
        print(f"[{label}]")
        print(f"  Path   : {path}")
        print(f"  Size   : {size:,} bytes ({size/1024/1024:.2f} MB)")
        print(f"  Meta   : {meta[:120]}...")
        print(f"  Header : {header[:120]}...")
        print(f"  Rows   : {rows:,}")

        # Validaciones básicas
        if "NQ" not in meta:
            errors.append(f"{label}: meta does not contain 'NQ' — wrong instrument?")
        if rows < 100:
            errors.append(f"{label}: only {rows} rows — too few, chart may not have loaded enough data")

        # Validaciones específicas
        if label == "barprofile":
            if "profile_volume" not in header:
                errors.append(f"{label}: header missing 'profile_volume'")
            if "primary_bar_volume" not in header:
                errors.append(f"{label}: header missing 'primary_bar_volume'")

        if label == "diag_blocks":
            if "cells" not in header:
                errors.append(f"{label}: header missing 'cells' column — DiagBlockExportEnabled was off?")

        if label == "oracle":
            if "event_type" not in header and "event_seq" not in header:
                errors.append(f"{label}: header missing event columns")

    print(f"\n{'='*60}")
    if errors:
        print(f"\n[FAIL] -- {len(errors)} error(s):")
        for e in errors:
            print(f"  * {e}")
        return 1
    else:
        print("\n[PASS] -- all three diagnostic CSVs are valid and ready for cross-reference")
        print("\nProximo paso: cruzar profile_volume/profile_min_tick contra el parquet")
        print("para resolver la frontera real de cada barra de NT8.")
        return 0


if __name__ == "__main__":
    sys.exit(validate())
