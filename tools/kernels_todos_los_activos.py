"""¿Corren los 6 kernels en TODOS los activos, o sólo en 6E?

Toda la paridad medida del proyecto es sobre 6E (y un oráculo de aVol en ES). Antes
de pedir oráculos NT8 por instrumento —que cuesta tiempo de Nico— conviene saber si
los kernels siquiera terminan sobre cada activo: no se puede tener paridad en un
instrumento donde el kernel se rompe.

Esto NO es paridad. Es un smoke de ejecutabilidad y sanidad de salida, target-free:
sin oráculo, sin outcomes, sin holdout. Un kernel puede terminar y aun así estar mal;
lo que este script descarta es lo contrario: que ni siquiera termine.

Ventana corta a propósito (`--dias`): el costo de HFTZones2 es cuadrático en ticks
(exponente medido 2,0-2,5), así que barrer 11 activos con ventana larga cuesta horas
y no agrega información sobre si el kernel corre.

Uso:
    python tools/kernels_todos_los_activos.py --dias 5 --out runs/kernels_activos.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import traceback

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge import bars as bars_mod  # noqa: E402
from edgelab.bridge import ticks as ticks_mod  # noqa: E402

DIA_NS = 86_400_000_000_000

# (modulo, pide footprints)
KERNELS = [
    ("bigtrap2", "edgelab.bridge.indicators.bigtrap2", True),
    ("avolclusterpoi", "edgelab.bridge.indicators.avolclusterpoi", True),
    ("avolcellpoi2", "edgelab.bridge.indicators.avolcellpoi2", True),
    ("gaps2", "edgelab.bridge.indicators.gaps2", False),
    ("hftzones2", "edgelab.bridge.indicators.hftzones2", False),
    ("voltickspoc2", "edgelab.bridge.indicators.voltickspoc2", True),
    ("aacloseopendiffs", "edgelab.bridge.indicators.aacloseopendiffs", False),
]


def parquets(raiz):
    """Un contrato por activo: el de más filas, que es el más líquido."""
    porto = {}
    for p in sorted(pathlib.Path(raiz).rglob("*_ticks.parquet")):
        activo = p.name.split("_")[0]
        porto.setdefault(activo, []).append(p)
    elegidos = {}
    for activo, ps in porto.items():
        elegidos[activo] = max(ps, key=lambda x: x.stat().st_size)
    return dict(sorted(elegidos.items()))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default="E:/EdgeLab/data/nt8_research_v2")
    ap.add_argument("--dias", type=int, default=5)
    ap.add_argument("--barras", default="time:1")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    elegidos = parquets(a.raiz)
    print("activos encontrados: %d -> %s" % (len(elegidos), ", ".join(elegidos)))
    print("ventana: %d dias  bar_spec: %s" % (a.dias, a.barras))
    print()

    filas = []
    for activo, p in elegidos.items():
        try:
            t0 = ticks_mod.load_canonical_parquet(str(p))
            ini = int(t0.ts_ns[0])
            tk = ticks_mod.load_canonical_parquet(
                str(p), start_utc_ns=ini, end_utc_ns=ini + a.dias * DIA_NS)
        except Exception as e:
            print("%-5s CARGA FALLA: %s" % (activo, str(e)[:70]))
            filas.append(dict(activo=activo, archivo=p.name, error_carga=str(e)[:300]))
            continue

        tipo, val = a.barras.split(":")
        bars = (bars_mod.build_time_bars(tk, int(val)) if tipo == "time"
                else bars_mod.build_tick_bars(tk, int(val)))
        fps = bars_mod.build_footprints(tk, bars)
        print("%-5s %-28s ticks=%-9d barras=%-7d tick_size=%s"
              % (activo, p.name, len(tk.ts_ns), len(bars.close_t), tk.tick_size))

        res_activo = dict(activo=activo, archivo=p.name,
                          sha_prefijo=None, ticks=len(tk.ts_ns),
                          barras=len(bars.close_t), tick_size=tk.tick_size, kernels={})
        for nombre, mod_name, usa_fp in KERNELS:
            t0 = time.time()
            try:
                mod = __import__(mod_name, fromlist=["run"])
                r = mod.run(tk, bars, fps) if usa_fp else mod.run(tk, bars)
                z = r.get("zones", []) if isinstance(r, dict) else (r or [])
                ev = r.get("events", []) if isinstance(r, dict) else []
                res_activo["kernels"][nombre] = dict(
                    ok=True, zonas=len(z), eventos=len(ev), segundos=round(time.time() - t0, 2))
                print("      %-18s ok   zonas=%-6d eventos=%-7d %5.1fs"
                      % (nombre, len(z), len(ev), time.time() - t0))
            except Exception as e:
                res_activo["kernels"][nombre] = dict(
                    ok=False, error=type(e).__name__, mensaje=str(e)[:300],
                    traceback=traceback.format_exc()[-800:],
                    segundos=round(time.time() - t0, 2))
                print("      %-18s FALLA  %s: %s"
                      % (nombre, type(e).__name__, str(e)[:80]))
        filas.append(res_activo)
        print()

    # resumen: matriz activo x kernel
    nombres = [k[0] for k in KERNELS]
    print("=" * 78)
    print("%-6s %s" % ("", " ".join("%-9s" % n[:9] for n in nombres)))
    fallas = 0
    for f in filas:
        if "error_carga" in f:
            print("%-6s CARGA FALLA" % f["activo"])
            fallas += 1
            continue
        celdas = []
        for n in nombres:
            k = f["kernels"].get(n, {})
            celdas.append("%-9s" % ("ok" if k.get("ok") else "FALLA"))
            if not k.get("ok"):
                fallas += 1
        print("%-6s %s" % (f["activo"], " ".join(celdas)))
    print("=" * 78)
    print("celdas en falla: %d de %d" % (fallas, len(filas) * len(nombres)))

    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(dias=a.dias, barras=a.barras, raiz=a.raiz,
                                   activos=filas), indent=1, default=str),
                   encoding="utf-8")
    print("informe: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
