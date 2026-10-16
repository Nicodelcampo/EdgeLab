#!/usr/bin/env python3
"""SOLO HUMANO: regenera config/autopilot/protected.json (hashes de gates, guardas del propio autopilot, pre-registros ya usados).
El autopilot se detiene (STOP_protected_changed) si cualquiera cambia; actualizar este manifiesto es la revisión humana de ese cambio.
  python tools/autopilot_protect.py add <ruta> [<ruta> ...]     # agrega o refresca rutas
  python tools/autopilot_protect.py check"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.autopilot.guard import check_protected, snapshot_protected
M = ROOT / "config/autopilot/protected.json"
if __name__ == "__main__":
    if sys.argv[1] == "add":
        cur = json.loads(M.read_text()) if M.exists() else {}; cur.update(snapshot_protected(sys.argv[2:], ROOT)); M.write_text(json.dumps(cur, indent=1)); print(len(cur), "rutas protegidas")
    else:
        bad = check_protected(M, ROOT); print("\n".join(bad) or "OK"); sys.exit(1 if bad else 0)
