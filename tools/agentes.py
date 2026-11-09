#!/usr/bin/env python3
"""Tabla de agentes del Debian (config/autopilot/AGENTES.json): imprime o regenera docs/autopilot/AGENTES.md.
  python tools/agentes.py            # imprime la tabla
  python tools/agentes.py --write    # regenera docs/autopilot/AGENTES.md y config/autopilot/TOPOLOGIA_AGENTES_DEBIAN.json
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.autopilot import agentes as A  # noqa: E402


def main():
    md = A.markdown()
    if "--write" in sys.argv:
        (ROOT / "docs/autopilot/AGENTES.md").write_text(md, encoding="utf-8")
        from edgelab.autopilot.orquestador_multiagente import TOPOLOGIA_DEBIAN_V2
        (ROOT / "config/autopilot/TOPOLOGIA_AGENTES_DEBIAN.json").write_text(json.dumps(TOPOLOGIA_DEBIAN_V2, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("escrito docs/autopilot/AGENTES.md y config/autopilot/TOPOLOGIA_AGENTES_DEBIAN.json")
    else: print(md)


if __name__ == "__main__":
    main()
