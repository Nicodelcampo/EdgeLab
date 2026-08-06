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

import argparse
import hashlib
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
CHECKPOINT_SUFFIX = ".checkpoint.json"


class CheckpointMismatch(RuntimeError):
    """El checkpoint no corresponde a esta corrida. Fail-closed a propósito."""


def clave_de_corrida(plan, universe_sha256, code_commit, sep_min_minutes,
                     lead_days):
    """Identidad de lo que se está midiendo. Si cambia, el checkpoint viejo NO
    se puede mezclar: sería juntar resultados de dos configuraciones distintas
    dentro de un mismo censo, que es exactamente el defecto que el manifiesto
    existe para hacer imposible."""
    payload = json.dumps({
        "plan": [[a, list(f)] for a, f in plan],
        "universe_sha256": universe_sha256,
        "code_commit": code_commit,
        "sep_min_minutes": sep_min_minutes,
        "lead_days": lead_days,
    }, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def leer_checkpoint(path, clave, permitir_descartar=False):
    """Devuelve los resultados ya calculados, o {} si no hay checkpoint.

    Falla cerrado si el checkpoint existe pero pertenece a otra corrida: no se
    descarta en silencio porque esa discrepancia es información (alguien cambió
    el universo, el código o la configuración a mitad de camino)."""
    if not path.exists():
        return {}
    ck = json.loads(path.read_text(encoding="utf-8"))
    if ck.get("clave_de_corrida") != clave:
        if not permitir_descartar:
            raise CheckpointMismatch(
                "el checkpoint %s es de OTRA corrida (universo, commit o "
                "configuración distintos). Se conserva sin tocar. Para empezar "
                "de cero usar --fresh." % path.name)
        return {}
    return ck.get("hecho", {})


def escribir_checkpoint(path, clave, hecho, plan, indicadores):
    """Se reescribe entero después de CADA (contrato, indicador). Es el grano
    más fino disponible: la unidad de cómputo va de 3 s a 5 h."""
    faltan = sum(1 for a, _ in plan for i in indicadores
                 if i not in hecho.get(a, {}))
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps({
        "complete": False,
        "aviso": "CENSO PARCIAL — checkpoint de reanudación, no es un censo "
                 "cerrado. El censo válido es post_sepmin.json + su manifiesto.",
        "clave_de_corrida": clave,
        "unidades_pendientes": faltan,
        "hecho": hecho,
    }, indent=1, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


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


def medir(archivo, fechas_medir, lead_dias=LEAD_DAYS, indicadores=None,
          ya_hechos=None, on_unidad=None):
    """Reporta fechas_medir y carga dias calendario previos para warm-up.

    `ya_hechos`: resultados de una corrida previa para este archivo; los
    indicadores presentes se saltan. `on_unidad(nombre, resultado)` se invoca al
    terminar cada indicador, para persistir el checkpoint."""
    indicadores = list(indicadores or REGISTRY)
    out = dict(ya_hechos or {})
    pendientes = [n for n in indicadores if n not in out]
    if not pendientes:
        print("   (todos los indicadores ya estaban en el checkpoint)", flush=True)
        return out
    for n in indicadores:
        if n in out:
            print("   %-18s [checkpoint]" % n, flush=True)

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
    for nombre in pendientes:
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
            if on_unidad is not None:
                on_unidad(nombre, out[nombre])
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
        if on_unidad is not None:
            on_unidad(nombre, out[nombre])
    return out


def git_head():
    return subprocess.check_output(
        ["git", "-C", REPO, "rev-parse", "HEAD"], text=True).strip()


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False,
                               allow_nan=False) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--indicators", default=None,
                    help="subconjunto separado por comas. Default: todos. Una "
                         "corrida parcial se marca como tal en el manifiesto.")
    ap.add_argument("--out", default=str(OUTPUT_PATH),
                    help="ruta del JSON de salida. Cambiala para no pisar una "
                         "corrida en curso.")
    ap.add_argument("--fresh", action="store_true",
                    help="ignora el checkpoint existente y empieza de cero.")
    a = ap.parse_args(argv)

    if a.indicators:
        indicadores = [s.strip() for s in a.indicators.split(",") if s.strip()]
        desconocidos = [n for n in indicadores if n not in REGISTRY]
        if desconocidos:
            ap.error("indicador desconocido: %s (validos: %s)"
                     % (", ".join(desconocidos), ", ".join(REGISTRY)))
    else:
        indicadores = list(REGISTRY)
    parcial = len(indicadores) < len(REGISTRY)

    out_path = Path(a.out)
    manifest_path = out_path.with_name(out_path.stem + ".run_manifest.json")
    ck_path = out_path.with_name(out_path.stem + CHECKPOINT_SUFFIX)

    dias, info = dias_research()
    plan = build_full_plan(dias)
    n_sessions = sum(len(fechas) for _, fechas in plan)
    universe_sha256 = sha256_file(UNIVERSE_PATH)
    commit = git_head()
    clave = clave_de_corrida(plan, universe_sha256, commit, SEP_MIN_MINUTES,
                             LEAD_DAYS)

    print("universo elegible: %d sesiones en %d contratos | holdout %d | cuarentena %d"
          % (n_sessions, len(plan), info["descartados_holdout"],
             info["descartados_cuarentena"]))
    print("indicadores: %s%s" % (", ".join(indicadores),
                                 "   [CORRIDA PARCIAL]" if parcial else ""))

    if a.fresh and ck_path.exists():
        ck_path.unlink()
        print("checkpoint anterior descartado por --fresh")
    hecho = leer_checkpoint(ck_path, clave)
    if hecho:
        ya = sum(len(v) for v in hecho.values())
        print("checkpoint: %d unidades (contrato x indicador) ya calculadas"
              % ya)

    t0 = time.time()
    for archivo, fechas in plan:
        print("\n== %s : %d sesiones (%s .. %s) =="
              % (archivo, len(fechas), fechas[0], fechas[-1]), flush=True)

        def guardar(nombre, resultado, _archivo=archivo):
            hecho.setdefault(_archivo, {})[nombre] = resultado
            escribir_checkpoint(ck_path, clave, hecho, plan, indicadores)

        medir(archivo, fechas, indicadores=indicadores,
              ya_hechos=hecho.get(archivo), on_unidad=guardar)

    todo = {a_: {"fechas": f_, "ind": {n: hecho[a_][n] for n in indicadores}}
            for a_, f_ in plan}
    write_json(out_path, todo)
    manifest = build_run_manifest(
        plan=plan,
        universe_sha256=universe_sha256,
        output_sha256=sha256_file(out_path),
        code_commit=commit,
        universe_info=info,
        indicators=indicadores,
        sep_min_minutes=SEP_MIN_MINUTES,
        lead_days=LEAD_DAYS,
    )
    manifest["indicadores_parciales"] = parcial
    if parcial:
        manifest["faltan_indicadores"] = sorted(set(REGISTRY) - set(indicadores))
    write_json(manifest_path, manifest)
    ck_path.unlink(missing_ok=True)      # el censo cerrado reemplaza al parcial
    print("\ntotal %.0fs -- escritos %s y %s"
          % (time.time() - t0, out_path.name, manifest_path.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
