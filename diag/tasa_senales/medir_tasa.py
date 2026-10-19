# -*- coding: utf-8 -*-
"""PUNTO 1 -- tasa empirica de senales por indicador.

`f` (trades/dia) NO es una perilla de diseno: es una SALIDA de la hipotesis.
Un indicador emite las senales que emite. La tabla de 40 filas del MDE no se
puede leer hasta saber a que `f` opera cada candidato.

NO CONSUME PRESUPUESTO DE MULTIPLICIDAD: cuenta disparos, no evalua
resultados. No mira si la senal gano ni pierde, no toca outcomes, no compara
contra ningun umbral economico. Es censo de actividad, del mismo tipo que
contar cuantos dias tiene el universo.

Holdout: los dias salen de `cargar_dias_de_estudio` (puerta unica). La ventana
de ticks se recorta a esos dias. Nada >= 2026-07-01 entra.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import numpy as np

REPO = "E:/EdgeLab"
sys.path.insert(0, REPO)

from edgelab.bridge import bars as bars_mod          # noqa: E402
from edgelab.bridge import ticks as ticks_mod        # noqa: E402
from edgelab.bridge.indicators import (BAR_DRIVEN, M1_DRIVEN,  # noqa: E402
                                       REGISTRY, TICK_DRIVEN)
from edgelab.research.universo_estudio import cargar_dias_de_estudio  # noqa: E402

CT = "America/Chicago"
TZ_CHART = "America/Argentina/Buenos_Aires"   # medido, no supuesto (ver contrato de paridad)
DATA = os.path.join(REPO, "data", "nt8", "6E")
BAR_SPEC_DEF = "time:1"                        # el de los gates montados
AQUI = os.path.dirname(os.path.abspath(__file__))


def dias_por_archivo():
    dias, info = cargar_dias_de_estudio(
        os.path.join(REPO, "runs", "censo", "manifiesto_universo.json"),
        tipos_de_dia=["COMPLETO", "CIERRE_SEMANAL"], caller="medir_tasa_senales")
    por = defaultdict(list)
    for d in dias:
        por[d["archivo"]].append(d["fecha"])
    return {a: sorted(set(f)) for a, f in por.items()}, info


def ventana_ns(fechas):
    """[primer dia 00:00 CT, ultimo dia +1 00:00 CT) -- acotado a los dias de research."""
    import pandas as pd
    a = pd.Timestamp(fechas[0] + " 00:00:00", tz=CT)
    b = pd.Timestamp(fechas[-1] + " 00:00:00", tz=CT) + pd.Timedelta(days=1)
    return int(a.value), int(b.value)


def fecha_ct(ms):
    import pandas as pd
    return pd.Timestamp(int(ms), unit="ms", tz="UTC").tz_convert(CT).strftime("%Y-%m-%d")


def medir(archivo, fechas, indicadores, bar_spec=BAR_SPEC_DEF):
    lo, hi = ventana_ns(fechas)
    p = os.path.join(DATA, archivo)
    tk = ticks_mod.load_canonical_parquet(p, start_utc_ns=lo, end_utc_ns=hi)
    kind, val = bar_spec.split(":")
    b = (bars_mod.build_time_bars(tk, int(val)) if kind == "time"
         else bars_mod.build_tick_bars(tk, int(val)))
    fp = None
    setf = set(fechas)
    out = {}
    for nombre in indicadores:
        mod = REGISTRY[nombre]
        t0 = time.time()
        try:
            if nombre in BAR_DRIVEN:
                if fp is None:
                    fp = bars_mod.build_footprints(tk, b)
                r = mod.run(tk, b, fp, chart_tz=TZ_CHART)
            elif nombre in M1_DRIVEN:
                r = mod.run(tk, b, chart_tz=TZ_CHART)
            else:
                r = mod.run(tk, b, chart_tz=TZ_CHART)
        except Exception as e:
            out[nombre] = dict(error="%s: %s" % (type(e).__name__, e))
            continue
        zonas = r.get("zones") or []
        # una SENAL = una zona creada. Se cuenta por dia CT de su created_ms,
        # y se descarta cualquier zona cuyo dia no este en el universo de
        # research (defensa en profundidad: la ventana ya lo acota).
        por_dia = Counter()
        fuera = 0
        for z in zonas:
            cm = z.get("created_ms")
            if cm is None:
                continue
            f = fecha_ct(cm)
            if f in setf:
                por_dia[f] += 1
            else:
                fuera += 1
        out[nombre] = dict(n_zonas=len(zonas), n_en_universo=int(sum(por_dia.values())),
                           fuera_de_universo=fuera, por_dia=dict(por_dia),
                           segundos=round(time.time() - t0, 1))
        print("   %-18s zonas=%-6d en_universo=%-6d (%.0fs)"
              % (nombre, len(zonas), sum(por_dia.values()), time.time() - t0), flush=True)
    return out, len(tk), len(b)


def main():
    por_arch, info = dias_por_archivo()
    print("dias de research: %d | holdout descartado: %d | cuarentena: %d"
          % (sum(len(v) for v in por_arch.values()),
             info["descartados_holdout"], info["descartados_cuarentena"]))
    inds = sys.argv[1:] or list(REGISTRY)
    print("indicadores:", inds)
    todo = {}
    for archivo in sorted(por_arch):
        fechas = por_arch[archivo]
        print("\n== %s : %d dias (%s .. %s) ==" % (archivo, len(fechas), fechas[0], fechas[-1]), flush=True)
        res, nt, nb = medir(archivo, fechas, inds)
        todo[archivo] = dict(fechas=fechas, n_ticks=nt, n_barras=nb, indicadores=res)
        json.dump(todo, open(os.path.join(AQUI, "tasa_senales.json"), "w"), indent=1)
    print("\nescrito tasa_senales.json")


if __name__ == "__main__":
    main()
