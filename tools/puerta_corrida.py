#!/usr/bin/env python3
"""Puerta unica pre-corrida (Capas 1-4): valida estado vivo, modulo, memoria activa, pre-registro y script antes de ejecutar.

Uso:
  python tools/puerta_corrida.py --verificar-estado
  python tools/puerta_corrida.py --prereg docs/research/.../PREREGISTRO.md --modulo edgelab.research.mi_mod --exigir-contada
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edgelab.research.puerta_corrida import verificar_corrida  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Puerta pre-corrida fail-closed de EdgeLab (Capas 1-4)")
    ap.add_argument("--prereg", default=None, help="Ruta al PREREGISTRO*.md")
    ap.add_argument("--modulo", default=None, help="Modulo Python canonico (ej. edgelab.research.u1_indaga)")
    ap.add_argument("--familia", default=None, help="ID de familia para consultar memoria activa y holdout")
    ap.add_argument("--script", default=None, help="Script de kernel a validar con puerta_kernel")
    ap.add_argument("--exigir-contada", action="store_true", help="Exige commit del prereg y alta en TRIAL_REGISTRY_GLOBAL.jsonl")
    ap.add_argument("--sintetico", action="store_true", help="Ejecuta preflight dinamico sobre datos sinteticos")
    ap.add_argument("--verificar-estado", action="store_true", help="Valida docs/ESTADO_VIVO.md y frontera holdout")
    ap.add_argument("--sin-estado", action="store_true", help="Omite validacion de docs/ESTADO_VIVO.md")
    ap.add_argument("--json", action="store_true", help="Imprime salida completa en JSON")
    args = ap.parse_args(argv)

    res = verificar_corrida(
        prereg=args.prereg,
        modulo=args.modulo,
        familia=args.familia,
        script=args.script,
        exigir_contada=args.exigir_contada,
        correr_sintetico=args.sintetico,
        verificar_estado=not args.sin_estado,
    )
    if args.json:
        print(json.dumps(res, indent=1, ensure_ascii=False))
    else:
        for av in res["avisos"]:
            print("AVISO:", av)
        for err in res["errores"]:
            print("BLOQUEADO:", err)
        if res["ok"]:
            print("PUERTA CORRIDA OK (L1..L4)")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
