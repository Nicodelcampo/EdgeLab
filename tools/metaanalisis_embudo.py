#!/usr/bin/env python3
"""Meta-análisis entre instrumentos de UNA regla congelada a partir de los estados del embudo (2026-10-26).

  python tools/metaanalisis_embudo.py <raiz> CID:i [CID:i ...] [--etapa oos|atras]
CID:i = la candidata i (orden de `candidatas`) de la campaña CID. Combina la media neta y el IC90 de esa etapa con
`edgelab.funnel.metaanalisis.combinar`. Las filas tienen que estar en la misma unidad (P&L normalizado, `NORMALIZAR`, o una moneda
común) y ser la misma regla; el comando no lo puede verificar: lo declara quien lo corre, antes de mirar.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.funnel.metaanalisis import combinar  # noqa: E402


def filas(raiz: Path, refs, etapa: str) -> list:
    out = []
    for r in refs:
        cid, _, i = r.partition(":"); st = json.loads((raiz / cid / "estado.json").read_text(encoding="utf-8"))
        v = ((st.get(etapa) or {}).get("veredictos") or [])[int(i or 0)]
        out.append(dict(instrumento=cid, celda=v.get("celda"), media=v.get("media"), ic90=v.get("ic90"), n=v.get("n")))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("raiz"); ap.add_argument("refs", nargs="+"); ap.add_argument("--etapa", default="oos", choices=("oos", "atras"))
    a = ap.parse_args(); f = filas(Path(a.raiz), a.refs, a.etapa)
    print(json.dumps(dict(filas=f, combinado=combinar(f)), indent=1, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
