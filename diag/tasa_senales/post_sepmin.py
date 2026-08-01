# -*- coding: utf-8 -*-
"""Tasa POST-sep_min por indicador -- lo unico que falta para cerrar 3.3.

REGLA ZONA->TRADE (decidida y preregistrada, no elegida aca):
  un trade por zona CREADA, entrada en el ancla, sin confirmacion, con
  sep_min=120 min aplicado sobre las creaciones.

Motivo: el SE de 0,0420 se midio sobre un proceso de anclas incondicional,
separado por 120 min. Cualquier otra regla (primer toque, toque con
confirmacion) cambia el proceso de anclas y INVALIDA el denominador del MDE.

La tasa CRUDA no discrimina candidatos: todo lo que emita mas de ~10/dia queda
recortado al mismo techo (sesion de 20 h / 120 min = 10 ranuras). La tasa
POST-sep_min si discrimina, y es la unica columna que hace falta.

Guarda de tiempo: ventana acotada, no corpus completo.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter

import numpy as np
import pandas as pd

REPO = "E:/EdgeLab"
sys.path.insert(0, REPO)

from edgelab.bridge import bars as bars_mod          # noqa: E402
from edgelab.bridge import ticks as ticks_mod        # noqa: E402
from edgelab.bridge.indicators import (BAR_DRIVEN, M1_DRIVEN,  # noqa: E402
                                       REGISTRY)
from edgelab.research.universo_estudio import cargar_dias_de_estudio  # noqa: E402

CT = "America/Chicago"
TZ_CHART = "America/Argentina/Buenos_Aires"
SEP_MIN_NS = 120 * 60 * 10**9
AQUI = os.path.dirname(os.path.abspath(__file__))


def dias_research():
    dias, info = cargar_dias_de_estudio(
        os.path.join(REPO, "runs", "censo", "manifiesto_universo.json"),
        tipos_de_dia=["COMPLETO", "CIERRE_SEMANAL"], caller="post_sepmin")
    return dias, info


def aplicar_sep_min(ms_ordenados, sep_ns=SEP_MIN_NS):
    """Decongestion voraz: se toma la primera y se descarta todo lo que caiga
    dentro de `sep_min`. Misma regla que usa el atlas para las anclas placebo."""
    sup, ultimo = [], None
    for m in ms_ordenados:
        ns = int(m) * 10**6
        if ultimo is None or ns - ultimo >= sep_ns:
            sup.append(m)
            ultimo = ns
    return sup


def medir(archivo, fechas_medir, lead_dias=20):
    """`fechas_medir` son los dias que se REPORTAN; se cargan `lead_dias`
    calendario extra por delante para el warm-up de los kernels con historia."""
    ini = pd.Timestamp(fechas_medir[0] + " 00:00:00", tz=CT) - pd.Timedelta(days=lead_dias)
    fin = pd.Timestamp(fechas_medir[-1] + " 00:00:00", tz=CT) + pd.Timedelta(days=1)
    tk = ticks_mod.load_canonical_parquet(os.path.join(REPO, "data/nt8/6E", archivo),
                                          start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))
    b = bars_mod.build_time_bars(tk, 1)
    fp = None
    setf = set(fechas_medir)
    out = {}
    for nombre in REGISTRY:
        mod = REGISTRY[nombre]
        t0 = time.time()
        try:
            if nombre in BAR_DRIVEN:
                if fp is None:
                    fp = bars_mod.build_footprints(tk, b)
                r = mod.run(tk, b, fp, chart_tz=TZ_CHART)
            else:
                r = mod.run(tk, b, chart_tz=TZ_CHART)
        except Exception as e:
            out[nombre] = dict(error="%s: %s" % (type(e).__name__, e))
            print("   %-18s ERROR %s" % (nombre, e), flush=True)
            continue
        ms = sorted(int(z["created_ms"]) for z in (r.get("zones") or [])
                    if z.get("created_ms") is not None)
        idx = pd.to_datetime(ms, unit="ms", utc=True).tz_convert(CT).strftime("%Y-%m-%d")
        # crudas y post-sep_min, ambas restringidas a los dias reportados
        crudas = Counter(f for f in idx if f in setf)
        sup = aplicar_sep_min(ms)
        idxs = pd.to_datetime(sup, unit="ms", utc=True).tz_convert(CT).strftime("%Y-%m-%d")
        post = Counter(f for f in idxs if f in setf)
        n = len(fechas_medir)
        vc = np.array([crudas.get(f, 0) for f in fechas_medir], float)
        vp = np.array([post.get(f, 0) for f in fechas_medir], float)
        out[nombre] = dict(
            crudas_por_dia=dict(crudas), post_por_dia=dict(post),
            crudas=dict(media=vc.mean(), mediana=float(np.median(vc)),
                        p10=float(np.percentile(vc, 10)), p90=float(np.percentile(vc, 90)),
                        dias_cero=int((vc == 0).sum())),
            post=dict(media=vp.mean(), mediana=float(np.median(vp)),
                      p10=float(np.percentile(vp, 10)), p90=float(np.percentile(vp, 90)),
                      dias_cero=int((vp == 0).sum())),
            segundos=round(time.time() - t0, 1), n_dias=n)
        print("   %-18s cruda=%6.1f/dia  post-sep_min=%5.2f/dia  dias_cero=%d  (%.0fs)"
              % (nombre, vc.mean(), vp.mean(), int((vp == 0).sum()), time.time() - t0), flush=True)
    return out


if __name__ == "__main__":
    dias, info = dias_research()
    print("universo: %d dias | holdout %d | cuarentena %d"
          % (len(dias), info["descartados_holdout"], info["descartados_cuarentena"]))
    por = {}
    for d in dias:
        por.setdefault(d["archivo"], []).append(d["fecha"])
    # ESTRATIFICACION: 10 dias de cada uno de los dos contratos con mas
    # cobertura de research, tomados del tramo central (evita bordes de roll).
    plan = []
    for arch in ("6E_06-26_ticks.parquet", "6E_03-26_ticks.parquet"):
        fs = sorted(set(por[arch]))
        m = len(fs) // 2
        plan.append((arch, fs[m - 5:m + 5]))
    todo = {}
    t0 = time.time()
    for arch, fechas in plan:
        print("\n== %s : %d dias (%s .. %s) ==" % (arch, len(fechas), fechas[0], fechas[-1]), flush=True)
        todo[arch] = dict(fechas=fechas, ind=medir(arch, fechas))
    json.dump(todo, open(os.path.join(AQUI, "post_sepmin.json"), "w"), indent=1)
    print("\ntotal %.0fs -- escrito post_sepmin.json" % (time.time() - t0))
