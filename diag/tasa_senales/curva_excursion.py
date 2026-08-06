# -*- coding: utf-8 -*-
"""Curva de excursion previa -> tasa de senales. El dato para elegir el umbral.

## Que contesta

Nico define el toque asi: *"el precio se tiene que alejar a partir de cierta
cantidad de ticks"*, y dice que no esta en posicion de elegir cuantos. Esto
produce el dato que falta para elegirlo: **para cada umbral T, cuantas senales
por sesion sobreviven, por indicador**.

Un toque CALIFICA a umbral T si, despues de la barra creadora, el precio se
alejo **>= T ticks** de la banda y DESPUES volvio a entrar. T=0 recupera la
regla actual (cualquier reentrada cuenta), asi que la familia contiene al caso
de hoy y la eleccion es un barrido, no un salto.

## Por que sirve para los SEIS indicadores

Trabaja sobre `zones` (`top`/`bottom`/`created_ms`) y el precio de las barras.
**No usa el bucle de toques del indicador.** Por eso mide igual a
`AACloseOpenDiffs`, que no tiene ese bucle, y a `Gaps2`/`HFTZones2`, que hoy
registran toques en la barra creadora.

## Justificacion economica

El umbral decide dos cosas a la vez: **cuando entras** y **cuantas veces por
dia** -o sea el `f` que alimenta el MDE-. Elegirlo a ojo es elegir la potencia
estadistica del test a ojo.

## Frontera outcome-free, declarada y verificable

Se mide EXCLUSIVAMENTE en la ventana `(barra creadora, primera reentrada]`. En
cuanto una zona reentra, **se deja de mirar**: no se lee un solo tick posterior
a la reentrada. La excursion que EXPLORE-001 evalua como estimando es la que va
DESPUES de la entrada; esta es la de ANTES, y son ventanas disjuntas por
construccion. No hay retornos, no hay P&L, no hay outcomes.

## Como podria refutarse

Si la curva fuera plana -si la tasa por sesion no cambiara con T- el umbral no
seria una palanca y la definicion de Nico no agregaria nada sobre la regla
actual. La curva es justamente lo que decide si vale la pena.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.post_sepmin import (  # noqa: E402
    BAR_DRIVEN, LEAD_DAYS, REGISTRY, TZ_CHART, bars_mod, dias_research,
    git_head, pd, ticks_mod,
)

CT = ZoneInfo("America/Chicago")
#: Grilla declarada ANTES de ver la curva. Fibonacci-ish para cubrir tres
#: ordenes de magnitud sin sesgar hacia ningun valor "redondo".
UMBRALES = (0, 1, 2, 3, 5, 8, 13, 21, 34)
SALIDA = Path(__file__).resolve().parent / "curva_excursion.json"


def sesion_ct(ms):
    d = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone(CT)
    return (d.date().isoformat() if d.hour < 17
            else (d + pd.Timedelta(days=1)).date().isoformat())


def reentradas_de_zona(lo_t, hi_t, hi_arr, lo_arr, ns_arr, i0, i_fin):
    """Devuelve [(unix_ms, max_alejamiento_ticks)] en cada reentrada a la banda.

    `max_alejamiento` es el maximo, hasta ese momento, de cuanto se alejo el
    precio del borde mas cercano de la banda. Es monotono no decreciente, asi
    que la primera reentrada que califica a umbral T es la primera con
    `max_alejamiento >= T`: una sola pasada sirve para TODA la grilla.

    Empieza en `i0` = barra creadora + 1. La barra creadora no interactua
    (`voltickspoc2.py:133`), y el censo lo exige como invariante
    (`touch_bar > created_bar`).
    """
    out, lejos = [], 0.0
    for i in range(i0, i_fin):
        h, l = hi_arr[i], lo_arr[i]
        if h >= lo_t and l <= hi_t:          # solapa la banda => reentrada
            out.append((int(ns_arr[i] // 1_000_000), lejos))
        else:
            d = (l - hi_t) if l > hi_t else (lo_t - h)
            if d > lejos:
                lejos = d
    return out


def medir(archivo, fechas, indicadores, lead=LEAD_DAYS):
    ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
           - pd.Timedelta(days=lead))
    fin = (pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago")
           + pd.Timedelta(days=1))
    tk = ticks_mod.load_canonical_parquet(
        str(REPO_PATH / "data" / "nt8" / "6E" / archivo),
        start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))
    b = bars_mod.build_time_bars(tk, 1)
    fp = None
    ns, hi_a, lo_a = b.start_ns, b.high_t, b.low_t
    ts = b.tick_size
    n = len(ns)
    setf = set(fechas)
    res = {}
    for nombre in indicadores:
        t0 = time.time()
        mod = REGISTRY[nombre]
        if nombre in BAR_DRIVEN:
            if fp is None:
                fp = bars_mod.build_footprints(tk, b)
            r = mod.run(tk, b, fp, chart_tz=TZ_CHART)
        else:
            r = mod.run(tk, b, chart_tz=TZ_CHART)
        zonas = r.get("zones") or []
        por_umbral = {t: Counter() for t in UMBRALES}
        alejamientos = []
        for z in zonas:
            if z.get("created_ms") is None or z.get("top") is None:
                continue
            lo_t, hi_t = z["bottom"] / ts, z["top"] / ts
            c_ns = int(z["created_ms"]) * 1_000_000
            i0 = int(pd.Series(ns).searchsorted(c_ns, side="right"))
            fin_ms = z.get("ended_ms")
            i_fin = (int(pd.Series(ns).searchsorted(int(fin_ms) * 1_000_000,
                                                    side="right"))
                     if fin_ms else n)
            re = reentradas_de_zona(lo_t, hi_t, hi_a, lo_a, ns, i0, min(i_fin, n))
            if not re:
                continue
            alejamientos.append(re[0][1])
            for T in UMBRALES:
                for ms, lejos in re:
                    if lejos >= T:
                        f = sesion_ct(ms)
                        if f in setf:
                            por_umbral[T][f] += 1
                        break
        res[nombre] = dict(
            zonas=len(zonas),
            por_umbral={str(T): dict(c) for T, c in por_umbral.items()},
            alejamiento_en_primera_reentrada=sorted(alejamientos)[:0] or None)
        # distribucion del alejamiento en la PRIMERA reentrada: dice que
        # umbrales son siquiera alcanzables
        if alejamientos:
            s = sorted(alejamientos)
            q = lambda p: s[min(len(s) - 1, int(p * len(s)))]
            res[nombre]["alejamiento_en_primera_reentrada"] = dict(
                n=len(s), p10=q(.10), p25=q(.25), p50=q(.50), p75=q(.75),
                p90=q(.90), max=s[-1])
        print("   %-18s %5d zonas (%.0fs)" % (nombre, len(zonas), time.time() - t0),
              flush=True)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--indicadores", nargs="*", default=None)
    ap.add_argument("--limite-sesiones", type=int, default=None)
    ap.add_argument("--out", default=str(SALIDA))
    a = ap.parse_args(argv)

    dias, info = dias_research()
    piloto = a.limite_sesiones is not None
    if piloto:
        dias = dias[:a.limite_sesiones]
    inds = a.indicadores or list(REGISTRY)
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])

    print("universo: %d sesiones%s" % (len(dias), "  [PILOTO]" if piloto else ""),
          flush=True)
    acum = {}
    for arch in sorted(por_arch):
        print("== %s : %d sesiones ==" % (arch, len(por_arch[arch])), flush=True)
        for nombre, r in medir(arch, sorted(por_arch[arch]), inds).items():
            a_ = acum.setdefault(nombre, dict(zonas=0, por_umbral={}))
            a_["zonas"] += r["zonas"]
            a_["alejamiento_en_primera_reentrada"] = r["alejamiento_en_primera_reentrada"]
            for T, c in r["por_umbral"].items():
                a_["por_umbral"].setdefault(T, {}).update(c)

    ns = len(dias)
    print("\nseñales por sesión, por umbral de alejamiento previo (ticks)")
    print("%-18s %s" % ("indicador", "".join("%8s" % T for T in UMBRALES)))
    for nombre, r in sorted(acum.items()):
        fila = "".join("%8.2f" % (sum(r["por_umbral"].get(str(T), {}).values()) / ns)
                       for T in UMBRALES)
        print("%-18s %s" % (nombre, fila))
    print("\nalejamiento en la PRIMERA reentrada (ticks) — qué umbrales son alcanzables")
    for nombre, r in sorted(acum.items()):
        d = r.get("alejamiento_en_primera_reentrada")
        if d:
            print("  %-18s n=%-6d p10=%.1f p25=%.1f p50=%.1f p75=%.1f p90=%.1f max=%.1f"
                  % (nombre, d["n"], d["p10"], d["p25"], d["p50"], d["p75"],
                     d["p90"], d["max"]))

    payload = dict(schema_version="curva_excursion_v1", autoritativo=not piloto,
                   code_commit=git_head(), umbrales=list(UMBRALES),
                   session_count=ns, universe_filter_report=info,
                   ventana="(barra creadora, primera reentrada] — nada posterior",
                   outcomes_accessed=False, curvas=acum)
    payload["output_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    Path(a.out).write_text(json.dumps(payload, indent=1, ensure_ascii=False),
                           encoding="utf-8")
    print("\n-> %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
