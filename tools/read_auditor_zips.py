# -*- coding: utf-8 -*-
"""Lee e inspecciona minuciosamente los dos zips entregados por el auditor."""
import zipfile
from pathlib import Path
import sys

def inspect_zip(zip_path: Path):
    print(f"\n{'='*70}")
    print(f"  INSPECCIÓN COMPLETA DE: {zip_path.name}")
    print(f"{'='*70}")
    
    with zipfile.ZipFile(zip_path) as zf:
        namelist = sorted(zf.namelist())
        print(f"Total archivos en el ZIP: {len(namelist)}\n")
        
        for name in namelist:
            if name.endswith("/"):
                continue
            data = zf.read(name)
            sz_kb = len(data) / 1024
            print(f"[*] {name} ({sz_kb:.1f} KB)")
            
            # Si es texto (md, json, patch, log, txt)
            if any(name.endswith(ext) for ext in [".md", ".json", ".patch", ".log", ".txt", ".py"]):
                try:
                    text = data.decode("utf-8", errors="replace")
                    lines = text.splitlines()
                    preview = "\n".join(lines[:25])
                    print(f"    --- Vista previa ({len(lines)} líneas) ---")
                    for pline in lines[:20]:
                        print(f"      | {pline}")
                    if len(lines) > 20:
                        print(f"      | ... [{len(lines)-20} líneas restantes]")
                except Exception as e:
                    print(f"    (Error decodificando texto: {e})")
            print()

def main():
    # Configurar salida segura UTF-8 para consola Windows
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        
    z_freeze = Path("E:/DatosNT8/Notion/EdgeLab_P2A_Freeze_Candidate_V1-R1_2026-08-26.zip")
    z_audit = Path("E:/DatosNT8/Notion/EdgeLab_C_Canonical_Delivery_Audit_2026-08-26.zip")
    
    if z_freeze.exists():
        inspect_zip(z_freeze)
    else:
        print(f"No existe {z_freeze}")
        
    if z_audit.exists():
        inspect_zip(z_audit)
    else:
        print(f"No existe {z_audit}")

if __name__ == "__main__":
    main()
