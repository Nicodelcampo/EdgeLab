#!/usr/bin/env python3
"""Exporta barras de StrategyQuant X (Dukascopy) a CSV para medir ideas de pocos parámetros en EdgeLab/Kaggle sin pasar por el Builder
(2026-11-14). Lee por MCP (read_bars, 1.000 por llamada), corta en el tope del holdout y escribe data/sqx_barras/<SIMBOLO>_<TF>.csv
con la hora del servidor de datos (EST+07 = Nueva York + 7 h; la sesión del día cierra a las 24:00 de esa hora).

  python tools/sqx_barras.py D1 [SIMBOLO ...]        # sin símbolos: todos los de list_data salvo NULO_*/PRUEBA_*
  python tools/sqx_barras.py H1 SP_M1_dukas NQ_M1_dukas ...
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "tools"))
import mcp_cliente as MC  # noqa: E402

TOPE = "2026.09.29"
SALIDA = ROOT / "data/sqx_barras"


def exportar(c, simbolo, tf):
    p = SALIDA / f"{simbolo}_{tf}.csv"
    if p.exists(): return f"{simbolo} {tf}: ya estaba"
    filas, pos = [], 0
    while True:
        r = c.llamar("read_bars", {"symbol": simbolo, "timeframe": tf, "start": pos, "count": 1000}); rows = r.get("rows", [])
        if not rows: break
        filas += [x for x in rows if x["date"][:10] <= TOPE]; pos += len(rows)
        if rows[-1]["date"][:10] > TOPE or pos >= r.get("total_count", 0): break
    SALIDA.mkdir(parents=True, exist_ok=True); tmp = p.with_suffix(".tmp")
    tmp.write_text("fecha,open,high,low,close,volume\n" + "\n".join(f'{x["date"]},{x["open"]},{x["high"]},{x["low"]},{x["close"]},{x["volume"]}' for x in filas) + "\n", encoding="utf-8")
    tmp.rename(p); return f"{simbolo} {tf}: {len(filas)} barras {filas[0]['date'][:10]} → {filas[-1]['date'][:10]}"


if __name__ == "__main__":
    tf = sys.argv[1]; c = MC.Cliente("sqx")
    sims = sys.argv[2:] or [x["symbol"] for x in c.llamar("list_data", {}).get("data", []) if not x["symbol"].startswith(("NULO_", "PRUEBA_"))]
    for s in sims: print(exportar(c, s, tf), flush=True)
