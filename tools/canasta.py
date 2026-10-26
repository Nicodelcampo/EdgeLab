#!/usr/bin/env python3
"""Canasta de estrategias de régimen (edgelab/funnel/canasta.py): estado, altas desde el embudo, operaciones forward y retiros.

  python tools/canasta.py estado   [--ruta docs/research/canasta/CANASTA.json]
  python tools/canasta.py alta     <estrategia.json> <embudo/<cid>/estado.json>     # sólo si el embudo terminó CONFIRMADA
  python tools/canasta.py ops      <id> <netos.csv | x1,x2,...>                     # operaciones forward netas, en orden
  python tools/canasta.py retirar  <id> "<motivo>"
La canasta propone pesos; operar con dinero real es decisión humana.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.funnel.canasta import Canasta, Estrategia  # noqa: E402

RUTA = ROOT / "docs/research/canasta/CANASTA.json"


def _netos(arg: str) -> list:
    p = Path(arg)
    txt = p.read_text(encoding="utf-8") if p.exists() else arg
    return [float(x) for x in txt.replace("\n", ",").split(",") if x.strip()]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("estado", "alta", "ops", "retirar")); ap.add_argument("args", nargs="*")
    ap.add_argument("--ruta", default=str(RUTA)); a = ap.parse_args(); c = Canasta(Path(a.ruta))
    if a.cmd == "estado": out = c.reporte()
    elif a.cmd == "alta":
        e = Estrategia(**json.loads(Path(a.args[0]).read_text(encoding="utf-8")))
        out = c.alta(e, json.loads(Path(a.args[1]).read_text(encoding="utf-8"))).id
    elif a.cmd == "ops": out = c.operaciones(a.args[0], _netos(a.args[1]))
    else: out = c.retirar(a.args[0], a.args[1])
    print(json.dumps(out, indent=1, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
