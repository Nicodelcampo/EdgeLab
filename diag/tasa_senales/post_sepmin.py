# -*- coding: utf-8 -*-
"""Censo outcome-free de tasa cruda y POST-sep_min por indicador.

REGLA ZONA->TRADE (decidida y preregistrada, no elegida aca):
  un trade por zona CREADA, entrada en el ancla, sin confirmacion, con
  sep_min=120 min aplicado sobre las creaciones.

El programa recorre TODAS las sesiones elegibles devueltas por la puerta unica
del universo. No selecciona dias centrales ni una muestra de contratos. Emite
el resultado y un sidecar content-addressed con commit, universo, configuracion
y cobertura. No accede a outcomes.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

REPO_PATH = Path(__file__).resolve().parents[2]
REPO = str(REPO_PATH)
sys.path.insert(0, REPO)

from diag.tasa_senales.census_plan import (  # noqa: E402
    build_full_plan,
    build_run_manifest,
    sha256_file,
)
from edgelab.bridge import bars as bars_mod  # noqa: E402
from edgelab.bridge import ticks as ticks_mod  # noqa: E402
from edgelab.bridge.indicators import BAR_DRIVEN, REGISTRY  # noqa: E402
from edgelab.research.universo_estudio import cargar_dias_de_estudio  # noqa: E402

CT = "America/Chicago"
TZ_CHART = "America/Argentina/Buenos_Aires"
SEP_MIN_NS = 120 * 60 * 10**9
SEP_MIN_MINUTES = 120
LEAD_DAYS = 20
AQUI = Path(__file__).resolve().parent
UNIVERSE_PATH = REPO_PATH / "runs" / "censo" / "manifiesto_universo.json"
OUTPUT_PATH = AQUI / "post_sepmin.json"
RUN_MANIFEST_PATH = AQUI / "post_sepmin.run_manifest.json"


def dias_research():
    dias, info = cargar_dias_de_estudio(
        str(UNIVERSE_PATH), tipos_de_dia=["COMPLETO", "CIERRE_SEMANAL"],
        caller="post_sepmin")
    return dias, info


def aplicar_sep_min(ms_ordenados, sep_ns=SEP_MIN_NS):
    """Decongestion voraz: toma la primera y descarta dentro de sep_min."""
    sup, ultimo = [], None
    for m in ms_ordenados:
        ns = int(m) * 10**6
        if ultimo is None or ns - ultimo >= sep_ns:
            sup.append(m)
            ultimo = ns
    return sup


def medir(archivo, fechas_medir, lead_dias=LEAD_DAYS):
    """Reporta fechas_medir y carga dias calendario previos para warm-up."""
    ini = (pd.Timestamp(fechas_medir[0] + " 00:00:00", tz=CT)
           - pd.Timedelta(days=lead_dias))
    fin = (pd.Timestamp(fechas_medir[-1] + " 00:00:00", tz=CT)
           + pd.Timedelta(days=1))
    tk = ticks_mod.load_canonical_parquet(
        str(REPO_PATH / "data" / "nt8" / "6E" / archivo),
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
        except Exception as exc:
            out[nombre] = {"error": "%s: %s" % (type(exc).__name__, exc)}
            print("   %-18s ERROR %s" % (nombre, exc), flush=True)
            continue
        ms = sorted(int(z["created_ms"]) for z in (r.get("zones") or [])
                    if z.get("created_ms") is not None)
        idx = (pd.to_datetime(ms, unit="ms", utc=True).tz_convert(CT)
               .strftime("%Y-%m-%d"))
        crudas = Counter(f for f in idx if f in setf)
        sup = aplicar_sep_min(ms)
        idxs = (pd.to_datetime(sup, unit="ms", utc=True).tz_convert(CT)
                .strftime("%Y-%m-%d"))
        post = Counter(f for f in idxs if f in setf)
        n = len(fechas_medir)
        vc = np.array([crudas.get(f, 0) for f in fechas_medir], float)
        vp = np.array([post.get(f, 0) for f in fechas_medir], float)
        out[nombre] = {
            "crudas_por_dia": dict(crudas),
            "post_por_dia": dict(post),
            "crudas": {
                "media": vc.mean(), "mediana": float(np.median(vc)),
                "p10": float(np.percentile(vc, 10)),
                "p90": float(np.percentile(vc, 90)),
                "dias_cero": int((vc == 0).sum()),
            },
            "post": {
                "media": vp.mean(), "mediana": float(np.median(vp)),
                "p10": float(np.percentile(vp, 10)),
                "p90": float(np.percentile(vp, 90)),
                "dias_cero": int((vp == 0).sum()),
            },
            "segundos": round(time.time() - t0, 1),
            "n_dias": n,
        }
        print("   %-18s cruda=%6.1f/dia post-sep_min=%5.2f/dia dias_cero=%d (%.0fs)"
              % (nombre, vc.mean(), vp.mean(), int((vp == 0).sum()),
                 time.time() - t0), flush=True)
    return out


def git_head():
    return subprocess.check_output(
        ["git", "-C", REPO, "rev-parse", "HEAD"], text=True).strip()


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False,
                               allow_nan=False) + "\n", encoding="utf-8")


def main():
    dias, info = dias_research()
    plan = build_full_plan(dias)
    n_sessions = sum(len(fechas) for _, fechas in plan)
    print("universo elegible: %d sesiones en %d contratos | holdout %d | cuarentena %d"
          % (n_sessions, len(plan), info["descartados_holdout"],
             info["descartados_cuarentena"]))
    todo = {}
    t0 = time.time()
    for archivo, fechas in plan:
        print("\n== %s : %d sesiones (%s .. %s) =="
              % (archivo, len(fechas), fechas[0], fechas[-1]), flush=True)
        todo[archivo] = {"fechas": fechas, "ind": medir(archivo, fechas)}
    write_json(OUTPUT_PATH, todo)
    manifest = build_run_manifest(
        plan=plan,
        universe_sha256=sha256_file(UNIVERSE_PATH),
        output_sha256=sha256_file(OUTPUT_PATH),
        code_commit=git_head(),
        universe_info=info,
        indicators=REGISTRY.keys(),
        sep_min_minutes=SEP_MIN_MINUTES,
        lead_days=LEAD_DAYS,
    )
    write_json(RUN_MANIFEST_PATH, manifest)
    print("\ntotal %.0fs -- escritos %s y %s"
          % (time.time() - t0, OUTPUT_PATH.name, RUN_MANIFEST_PATH.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
