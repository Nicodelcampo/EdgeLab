#!/usr/bin/env python3
"""Refresca las reglas públicas de Lucid con el crawler existente (`edgelab.propfirm.crawl`) y avisa si cambió alguna página respecto de la línea base.
  python tools/propfirm_refresh.py [--out DIR] [--accept]     # --accept: toma el crawl actual como nueva línea base (revisión humana de los cambios)
Escribe `RULES_CHANGED.json` (y el flag `RULES_CHANGED`) en --out si hay diferencias; el doctor del autopilot lo informa. No modifica mandate.json: ese cambio es humano."""
import argparse, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "config/propfirms/lucid_pages_sha.json"
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(ROOT / "artifacts/propfirm/crawl")); ap.add_argument("--accept", action="store_true"); a = ap.parse_args()
    subprocess.run([sys.executable, "-m", "edgelab.propfirm.crawl", "--only", "Lucid", "--out", a.out], cwd=ROOT, check=True)
    inv = json.loads((Path(a.out) / "Lucid/inventario.json").read_text()); cur = {m["url"]: m["sha256"] for m in inv["paginas_meta"]}
    base = json.loads(BASE.read_text()) if BASE.exists() else {}
    if a.accept or not base:
        BASE.write_text(json.dumps(cur, indent=1, sort_keys=True)); print(f"línea base guardada: {len(cur)} páginas"); (Path(a.out) / "RULES_CHANGED").unlink(missing_ok=True); return
    ch = dict(nuevas=sorted(set(cur) - set(base)), quitadas=sorted(set(base) - set(cur)), modificadas=sorted(u for u in cur if u in base and cur[u] != base[u]))
    flag = Path(a.out) / "RULES_CHANGED"
    if any(ch.values()):
        (Path(a.out) / "RULES_CHANGED.json").write_text(json.dumps(ch, indent=1)); flag.write_text("revisar mandato"); print("CAMBIÓ:", {k: len(v) for k, v in ch.items()})
    else: flag.unlink(missing_ok=True); print("sin cambios en las reglas de Lucid")
if __name__ == "__main__":
    main()
