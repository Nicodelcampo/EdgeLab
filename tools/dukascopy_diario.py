#!/usr/bin/env python3
"""Descarga diaria de Dukascopy para el embudo (la corre edgelab-datos-dukascopy.timer en el Debian).
Lee `dukascopy` de /etc/edgelab/autopilot.json: {"simbolos": [...], "salida_sellada": carpeta, "desde": "AAAA-MM-DD"} y baja
desde `desde` hasta ayer (UTC) cada símbolo. Retoma solo: un día completo no se vuelve a pedir.
  python tools/dukascopy_diario.py [--config /etc/edgelab/autopilot.json]
"""
import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("dk", Path(__file__).resolve().parent / "dukascopy_descarga.py")
DK = importlib.util.module_from_spec(spec); spec.loader.exec_module(DK)


def main(cfg_path: str, hoy: dt.date | None = None):
    c = json.loads(Path(cfg_path).read_text(encoding="utf-8")).get("dukascopy") or {}
    if not c.get("simbolos"): print("dukascopy: sin símbolos en la configuración"); return []
    hasta = (hoy or dt.datetime.now(dt.timezone.utc).date()) - dt.timedelta(days=1); out = []
    for s in c["simbolos"]:
        d = dt.date.fromisoformat(c["desde"])
        while d <= hasta:
            if d.weekday() != 5: out.append((s, d.isoformat(), str(DK.bajar_dia(s, d, Path(c["salida_sellada"])))))
            d += dt.timedelta(days=1)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--config", default="/etc/edgelab/autopilot.json")
    for x in main(ap.parse_args().config): print(*x)
