#!/usr/bin/env python3
"""Diagnóstico de mecanismo de una grilla y de episodios (K55/K56): imprime las líneas «Diagnóstico de grilla:» y «Episodios:» que todo
RESULTADO que lea mesetas, PBO o «N/N variantes», o que declare una regla apagada, tiene que llevar (tests/test_diagnostico_obligatorio.py).

  python tools/diagnostico_grilla.py <ops.csv[.gz]> [--variante COL] [--valor R] [--fecha COL] [--filtro "expr pandas"]
"""
import argparse, json, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))


def main(a=None):
    from edgelab.research.diagnostico_grilla import diagnostico, episodios
    p = argparse.ArgumentParser(); p.add_argument("ops"); p.add_argument("--variante", default="variante"); p.add_argument("--valor", default="R")
    p.add_argument("--fecha", default="ses"); p.add_argument("--filtro", default=None); x = p.parse_args(a)
    o = pd.read_csv(x.ops)
    if x.filtro: o = o.query(x.filtro)
    o["mes"] = pd.to_datetime(o[x.fecha].astype(str)).dt.to_period("M").astype(str)
    out = {}
    if x.variante in o and o[x.variante].nunique() > 1:
        out["grilla"] = diagnostico(o, x.variante, x.valor); print(out["grilla"]["linea"])
    out["episodios"] = episodios(o, x.valor); print(out["episodios"]["linea"])
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "linea"} for k, v in out.items()}, ensure_ascii=False, default=str)[:3000])


if __name__ == "__main__":
    main()
