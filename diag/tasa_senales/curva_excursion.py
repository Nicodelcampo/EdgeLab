# -*- coding: utf-8 -*-
"""Curva de excursion previa -> tasa de senales. El dato para elegir el umbral.

## Que contesta

Nico define el toque asi: *"el precio se tiene que alejar a partir de cierta
cantidad de ticks"*, y dice que no esta en posicion de elegir cuantos. Esto
produce el dato que falta para elegirlo: **para cada umbral T, cuantas senales
por sesion sobreviven, por indicador**.

**DOS arquetipos de entrada, no uno.** La v1 medía solo "alejarse y VOLVER" y
lo aplicaba a los seis indicadores. Nico lo objeto: *"no es lo mismo una entrada
en un gap que en una burbuja de absorcion"*. Tiene razon -para un gap la
hipotesis clasica es el relleno; para `BigTrap2`, si hay vendedores atrapados
que tienen que recomprar, el precio se va DE la zona y la entrada seria la
ruptura-. Se miden los dos:

- **retorno**: se alejo >= T y DESPUES volvio a la banda. Fade / relleno.
- **ruptura**: se alejo >= T. Continuacion. No exige que vuelva.

T=0 en `retorno` recupera la regla actual, asi que la familia contiene al caso
de hoy y la eleccion es un barrido, no un salto.

Todo se desglosa ademas por `kind`, que es donde vive la semantica y la
direccion de cada indicador: `trapped_buyers`/`trapped_sellers`,
`bull_gap`/`bear_gap`, `gap_up`/`gap_down`, `poc_anomaly`.

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


def eventos_de_zona(lo_t, hi_t, hi_arr, lo_arr, ns_arr, i0, i_fin, umbrales):
    """Una pasada. Dos arquetipos con RELOJES SEPARADOS. Ambiguo => ABSTAIN.

    Devuelve `(ruptura_arriba, ruptura_abajo, retorno, primera, ambigua)`.

    - `ruptura_*[T]`: ms en que el alejamiento alcanzo T ticks, POR LADO. No
      exige que el precio vuelva. La direccion importa: un `trapped_sellers` que
      rompe hacia abajo contradice el mecanismo, y la v2 los sumaba juntos.
    - `retorno[T]`: ms de la primera reentrada habiendose alejado >= T. Reloj
      distinto: exige el regreso.
    - `ambigua`: la barra hizo LAS DOS COSAS -su rango solapa la banda Y se aleja
      >= 1 tick-. Desde OHLC el ORDEN INTRABAR es indemostrable: pudo alejarse y
      volver (retorno) o volver y alejarse (ruptura). **Son eventos distintos y
      no se puede elegir uno.** La zona se ABSTIENE.

    La v2 no lo veia porque evaluaba en dos ramas excluyentes: si la barra
    solapaba, nunca actualizaba el alejamiento, y la ambiguedad quedaba resuelta
    por construccion a favor del retorno.
    """
    rup_up, rup_dn, retorno = {}, {}, {}
    lejos, primera, ambigua = 0.0, None, False
    for i in range(i0, i_fin):
        h, l = hi_arr[i], lo_arr[i]
        solapa = (h >= lo_t and l <= hi_t)
        d_up = h - hi_t if h > hi_t else 0.0     # cuanto salio por arriba
        d_dn = lo_t - l if l < lo_t else 0.0     # y por abajo
        d = max(d_up, d_dn)

        if solapa and d >= 1.0:
            # HACE LAS DOS COSAS EN LA MISMA BARRA. Indemostrable desde OHLC.
            ambigua = True
            break

        if solapa:
            if primera is None:
                primera = lejos
            for T in umbrales:
                if T not in retorno and lejos >= T:
                    retorno[T] = int(ns_arr[i] // 1_000_000)
        elif d > lejos:
            lejos = d
            ms = int(ns_arr[i] // 1_000_000)
            dst = rup_up if d_up >= d_dn else rup_dn
            for T in umbrales:
                if T not in dst and d >= T:
                    dst[T] = ms
        if (len(retorno) == len(umbrales)
                and len(rup_up) + len(rup_dn) >= len(umbrales)):
            break
    return rup_up, rup_dn, retorno, primera, ambigua


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
    # `searchsorted` una sola vez sobre el array, NO una Series por zona: con
    # ~7.000 zonas y ~30.000 barras eso era O(zonas x barras) solo en construir
    # objetos, y habria hecho la corrida de 201 sesiones inviable.
    import numpy as _np
    ns_arr = _np.asarray(ns)
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
        # ARQUETIPO x UMBRAL x KIND. `kind` trae la semantica Y la direccion:
        # BigTrap2 -> trapped_buyers/trapped_sellers; Gaps2 -> bull_gap/bear_gap;
        # AACloseOpenDiffs -> gap_up/gap_down; VolTicksPOC2 -> poc_anomaly.
        # La v1 los agregaba a todos juntos: promediaba mecanismos opuestos.
        ARQ = ("retorno", "ruptura_arriba", "ruptura_abajo")
        por = {a_: {t: Counter() for t in UMBRALES} for a_ in ARQ}
        por_kind = {a_: {t: Counter() for t in UMBRALES} for a_ in ARQ}
        alejamientos = []
        n_ambiguas = 0
        for z in zonas:
            if z.get("created_ms") is None or z.get("top") is None:
                continue
            lo_t, hi_t = z["bottom"] / ts, z["top"] / ts
            c_ns = int(z["created_ms"]) * 1_000_000
            i0 = int(_np.searchsorted(ns_arr, c_ns, side="right"))
            fin_ms = z.get("ended_ms")
            i_fin = (int(_np.searchsorted(ns_arr, int(fin_ms) * 1_000_000,
                                          side="right")) if fin_ms else n)
            rup_up, rup_dn, ret, primera, ambigua = eventos_de_zona(
                lo_t, hi_t, hi_a, lo_a, ns, i0, min(i_fin, n), UMBRALES)
            if ambigua:
                # ABSTAIN por orden intrabar indemostrable. NO se cuenta en
                # ningun arquetipo: contarla en uno seria elegir el orden.
                n_ambiguas += 1
                continue
            if primera is not None:
                alejamientos.append(primera)
            k = z.get("kind") or "?"
            for a_, d in (("retorno", ret), ("ruptura_arriba", rup_up),
                          ("ruptura_abajo", rup_dn)):
                for T in UMBRALES:
                    ms = d.get(T)
                    if ms is None:
                        continue
                    f = sesion_ct(ms)
                    if f in setf:
                        por[a_][T][f] += 1
                        por_kind[a_][T][k + "|" + f] += 1
        res[nombre] = dict(
            zonas=len(zonas),
            # descartes con motivo, exigido por el auditor en la v0.2
            zonas_abstenidas_por_ambiguedad_intrabar=n_ambiguas,
            kinds=dict(Counter(z.get("kind") for z in zonas)),
            por_umbral={a_: {str(T): dict(c) for T, c in d.items()}
                        for a_, d in por.items()},
            por_kind={a_: {str(T): dict(c) for T, c in d.items()}
                      for a_, d in por_kind.items()},
            alejamiento_en_primera_reentrada=None)
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
            ac = acum.setdefault(nombre, dict(zonas=0, kinds={},
                                              zonas_abstenidas_por_ambiguedad_intrabar=0,
                                              por_umbral={}, por_kind={}))
            ac["zonas"] += r["zonas"]
            ac["zonas_abstenidas_por_ambiguedad_intrabar"] += r[
                "zonas_abstenidas_por_ambiguedad_intrabar"]
            ac["alejamiento_en_primera_reentrada"] = r["alejamiento_en_primera_reentrada"]
            for k, v in r["kinds"].items():
                ac["kinds"][k] = ac["kinds"].get(k, 0) + v
            for campo in ("por_umbral", "por_kind"):
                for a_, d in r[campo].items():
                    for T, c in d.items():
                        ac[campo].setdefault(a_, {}).setdefault(T, {}).update(c)

    ns = len(dias)
    for a_ in ("retorno", "ruptura_arriba", "ruptura_abajo"):
        print("\nARQUETIPO %s -- senales/sesion por umbral de alejamiento (ticks)"
              % a_.upper())
        print("%-18s %s" % ("indicador", "".join("%8s" % T for T in UMBRALES)))
        for nombre, r in sorted(acum.items()):
            d = r["por_umbral"].get(a_, {})
            fila = "".join("%8.2f" % (sum(d.get(str(T), {}).values()) / ns)
                           for T in UMBRALES)
            print("%-18s %s" % (nombre, fila))
    print("\nkinds por indicador (semantica y direccion, desglose en el JSON)")
    for nombre, r in sorted(acum.items()):
        print("  %-18s %s" % (nombre, r.get("kinds")))
    print("\nDESCARTES -- zonas ABSTENIDAS por orden intrabar indemostrable")
    for nombre, r in sorted(acum.items()):
        z, amb = r["zonas"], r["zonas_abstenidas_por_ambiguedad_intrabar"]
        print("  %-18s %6d de %6d  (%.1f%%)" % (nombre, amb, z,
                                                100.0 * amb / z if z else 0))
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
