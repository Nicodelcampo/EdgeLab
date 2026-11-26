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
    """Compacto (los kernels de Kaggle tienen tope de tamaño): cada evento = minuto UTC (hex) + índice de evento + impacto,
    decodificado al importar a la misma tupla EVENTOS = ((t_utc_s, evento, impacto), ...)."""
    from edgelab import noticias as N
    df = N.cargar().sort_values(["ts_ns", "evento"])
    t = df.ts_ns.to_numpy() // 10**9
    assert (t % 60 == 0).all(), "el calendario tiene eventos fuera del minuto"
    nombres = sorted(set(df.evento)); imps = sorted(set(df.impacto))
    cod = ";".join(f"{x // 60:x},{nombres.index(e)},{imps.index(i)}" for x, e, i in zip(t, df.evento, df.impacto))
    lineas = "\n".join("    " + repr(cod[k:k + 110]) for k in range(0, len(cod), 110))
    return ('"""GENERADO por tools/eventos_desde_noticias.py desde config/noticias/calendario_usd_tier1.csv (no editar a mano).\n'
            '(t_utc_s, evento, impacto). Codificado compacto: minuto UTC en hex, índice de evento, índice de impacto."""\n'
            f"_NOMBRES = {tuple(nombres)!r}\n_IMPACTOS = {tuple(imps)!r}\n_COD = (\n{lineas}\n)\n"
            "EVENTOS = tuple((int(m, 16) * 60, _NOMBRES[int(e)], _IMPACTOS[int(i)])\n"
            "                for m, e, i in (x.split(',') for x in _COD.split(';')))\n")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--write", action="store_true"); a = ap.parse_args(); txt = generar()
    if a.write: DESTINO.write_text(txt, encoding="utf-8"); print(f"escrito {DESTINO}")
    else: sys.stdout.write(txt)


if __name__ == "__main__":
    main()
