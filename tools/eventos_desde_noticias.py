"""Genera `edgelab/research/eventos_datos.py` desde el calendario canónico de noticias (`edgelab/noticias.py`,
`config/noticias/calendario_usd_tier1.csv`): los kernels de Kaggle sólo llevan módulos embebidos, no archivos de config, así que el
filtro de eventos de la grilla necesita los horarios como datos de Python. Fuente única: el CSV de noticias (se regenera con
`tools/noticias_calendario.py`); `tests/research/test_eventos.py` falla si este módulo quedó desactualizado.
  python tools/eventos_desde_noticias.py            # muestra
  python tools/eventos_desde_noticias.py --write    # regenera
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
DESTINO = ROOT / "edgelab" / "research" / "eventos_datos.py"


def generar() -> str:
    from edgelab import noticias as N
    df = N.cargar().sort_values(["ts_ns", "evento"])
    filas = "\n".join(f"    ({int(t) // 10**9}, {e!r}, {i!r})," for t, e, i in zip(df.ts_ns, df.evento, df.impacto))
    return ('"""GENERADO por tools/eventos_desde_noticias.py desde config/noticias/calendario_usd_tier1.csv (no editar a mano).\n'
            '(t_utc_s, evento, impacto). Fuentes por fila en el CSV; criterio en edgelab/noticias.py."""\n'
            f"EVENTOS = (\n{filas}\n)\n")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--write", action="store_true"); a = ap.parse_args(); txt = generar()
    if a.write: DESTINO.write_text(txt, encoding="utf-8"); print(f"escrito {DESTINO}")
    else: sys.stdout.write(txt)


if __name__ == "__main__":
    main()
