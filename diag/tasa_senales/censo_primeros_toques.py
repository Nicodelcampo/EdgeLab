# -*- coding: utf-8 -*-
"""Censo outcome-free sobre la poblacion AUTORITATIVA: PRIMEROS TOQUES.

## Por que existe

`post_sepmin.py` aplica `sep_min` sobre **creaciones de zona**. La enmienda
`docs/amendments/EXPLORE-001-2026-08-04_first_touch_decongestion.md` -CONGELADA
antes de ejecutar este censo- declara que esa poblacion es la equivocada:

    "La separacion de 120 minutos estaba implementada sobre creaciones de zonas,
     pero EXPLORE-001 define la entrada primaria en el primer toque posterior.
     La restriccion representa capacidad de exposicion, por lo que debe operar
     sobre el instante de entrada y no sobre el instante en que nacio una zona
     todavia no operable."

Y su efecto de autoridad es explicito: *"Las tasas de creaciones siguen siendo
DIAGNOSTICAS. H1-H3 solo pueden congelarse con tasas producidas por esta
poblacion y esta politica."*

La maquinaria (`first_touch_population`, `first_touch_decongestion`,
`first_touch_census`) estaba construida y con 10 tests en verde, pero **ningun
programa la llamaba**: no habia runner. Este es el runner que faltaba.

## Justificacion economica

D3 -"la tasa post-sep_min no discrimina entre indicadores"- se midio sobre
CREACIONES. Si la saturacion es un artefacto de esa poblacion, D3 se disuelve y
§3.3 se puede llenar; si persiste sobre primeros toques, D3 es real y hay que
decidir el criterio. **Hoy no se sabe cual de las dos, y esa es la unica razon
por la que §3.3 sigue vacia.**

## Como podria refutarse

Si `build_first_touch_census` rechazara los resultados de los kernels -por
`zone_id` ausente, `ZONE_CREATED` duplicado o lifecycle que no permite probar la
regla anti look-ahead-, la premisa "el censo correcto es corrible hoy" queda
refutada y el bloqueo pasa a ser el emisor, no el runner.

No accede a outcomes. No abre el holdout: el universo sale de la puerta unica.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.post_sepmin import (  # noqa: E402
    BAR_DRIVEN, LEAD_DAYS, REGISTRY, TZ_CHART, bars_mod, dias_research,
    git_head, pd, ticks_mod,
)
from edgelab.research.first_touch_census import build_first_touch_census  # noqa: E402
from edgelab.research.first_touch_decongestion import (  # noqa: E402
    FIRST_TOUCH_SEP_MINUTES,
)

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "primeros_toques.json"


def resultados_por_archivo(dias, indicadores, lead_dias=LEAD_DAYS, verbose=True):
    """Corre los kernels y devuelve {archivo: {"events": [...]}} por indicador.

    Mismo warm-up (`lead_dias`) y misma carga de parquet que `post_sepmin.py`:
    si difirieran, las dos tasas no serian comparables y toda la contrastacion
    diagnostico-vs-autoritativo perderia sentido.
    """
    por_archivo = {}
    for d in dias:
        por_archivo.setdefault(d["archivo"], []).append(d["fecha"])
    out = {n: {} for n in indicadores}
    for archivo in sorted(por_archivo):
        fechas = sorted(por_archivo[archivo])
        ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
               - pd.Timedelta(days=lead_dias))
        fin = (pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago")
               + pd.Timedelta(days=1))
        if verbose:
            print("== %s : %d sesiones ==" % (archivo, len(fechas)), flush=True)
        tk = ticks_mod.load_canonical_parquet(
            str(REPO_PATH / "data" / "nt8" / "6E" / archivo),
            start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))
        b = bars_mod.build_time_bars(tk, 1)
        fp = None
        for nombre in indicadores:
            t0 = time.time()
            mod = REGISTRY[nombre]
            if nombre in BAR_DRIVEN:
                if fp is None:
                    fp = bars_mod.build_footprints(tk, b)
                r = mod.run(tk, b, fp, chart_tz=TZ_CHART)
            else:
                r = mod.run(tk, b, chart_tz=TZ_CHART)
            out[nombre][archivo] = {"events": r.get("events") or []}
            if verbose:
                print("   %-18s %6d eventos (%.0fs)"
                      % (nombre, len(out[nombre][archivo]["events"]), time.time() - t0),
                      flush=True)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--indicadores", nargs="*", default=None)
    ap.add_argument("--limite-sesiones", type=int, default=None,
                    help="PILOTO: recorta el universo. Una corrida con limite NO "
                         "es autoritativa y se marca como tal en la salida.")
    ap.add_argument("--out", default=str(SALIDA))
    a = ap.parse_args(argv)

    dias, info = dias_research()
    piloto = a.limite_sesiones is not None
    if piloto:
        dias = dias[:a.limite_sesiones]
    indicadores = a.indicadores or list(REGISTRY)
    elegibles = [{"archivo": d["archivo"], "fecha": d["fecha"]} for d in dias]

    print("universo: %d sesiones%s | indicadores: %s"
          % (len(elegibles), "  [PILOTO, NO AUTORITATIVO]" if piloto else "",
             indicadores), flush=True)

    crudos = resultados_por_archivo(dias, indicadores)
    censos, errores = {}, {}
    for nombre in indicadores:
        try:
            censos[nombre] = build_first_touch_census(
                indicator_results_by_archive=crudos[nombre],
                eligible_days=elegibles,
                sep_minutes=FIRST_TOUCH_SEP_MINUTES)
        except Exception as exc:
            # Fail-closed y VISIBLE: un indicador cuyo lifecycle no permite
            # probar la regla anti look-ahead no se estima igual con una
            # aproximacion. Se reporta el rechazo.
            errores[nombre] = "%s: %s" % (type(exc).__name__, exc)
            print("   %-18s RECHAZADO %s" % (nombre, exc), flush=True)

    payload = {
        "schema_version": "first_touch_census_run_v1",
        "purpose": "EXPLORE-001 poblacion AUTORITATIVA (primeros toques)",
        "autoritativo": not piloto,
        "code_commit": git_head(),
        "sep_minutes": FIRST_TOUCH_SEP_MINUTES,
        "session_count": len(elegibles),
        "universe_filter_report": info,
        "censos": censos,
        "rechazados": errores,
        "outcomes_accessed": False,
    }
    payload["output_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    Path(a.out).write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")

    print("\n%-18s %10s %10s %8s" % ("indicador", "cru/ses", "post/ses", "colapso"))
    n = len(elegibles)
    for nombre, c in sorted(censos.items(), key=lambda x: -x[1]["post_sep_count"]):
        cr, po = c["raw_count"] / n, c["post_sep_count"] / n
        print("%-18s %10.2f %10.2f %7.1f%%"
              % (nombre, cr, po, 100 * (1 - po / cr) if cr else 0))
    print("\n-> %s" % a.out)
    return 0 if not errores else 1


if __name__ == "__main__":
    sys.exit(main())
