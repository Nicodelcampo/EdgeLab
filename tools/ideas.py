#!/usr/bin/env python3
"""Banco de ideas multi-fuente (edgelab/research/ideas.py).
  python tools/ideas.py                    # balance y próximo lote balanceado
  python tools/ideas.py agregar ficha.json # agrega una ficha (valida campos y novedad del mecanismo)
  python tools/ideas.py lote 8             # próximo lote balanceado de 8
  python tools/ideas.py --write            # regenera docs/research/ideas/BANCO_IDEAS.md
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.research import ideas as I  # noqa: E402


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if a[:1] == ["agregar"]: print(json.dumps(I.agregar(json.loads(Path(a[1]).read_text(encoding="utf-8"))), ensure_ascii=False))
    elif a[:1] == ["lote"]: [print(x["id"], x["clase"], x["prior"], "-", x["titulo"]) for x in I.lote(int(a[1]) if len(a) > 1 else 5)]
    elif "--write" in sys.argv: I.VISTA.write_text(I.markdown(), encoding="utf-8"); print("escrito", I.VISTA.relative_to(ROOT))
    else: print(json.dumps(I.resumen_para_agente(), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
