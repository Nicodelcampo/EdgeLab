# -*- coding: utf-8 -*-
"""¿Por qué `alejamiento_en_primera_reentrada` da 0 en Gaps2 y HFTZones2?

## El hallazgo que dispara esta sonda

La curva de diseño (`curva_excursion_ticks.json`, sha `76e1c876…`) publicó los
cuantiles del alejamiento acumulado **justo antes** de la primera reentrada:

    indicador       p25   p50   p75   p90     clase
    Gaps2           0,0   0,0   0,0   2,0     tick_create
    HFTZones2       0,0   0,0   1,0   3,0     tick_create
    BigTrap2        1,5   3,5   8,5  20,5     bar_close
    VolTicksPOC2    0,5   3,5  10,5  22,5     bar_close
    aVolCellPOI2    0,0   1,5   5,5  15,5     bar_close

Para `Gaps2`, **el p75 es 0**: en al menos tres de cada cuatro zonas el precio
**no se alejó ni un tick** antes de su primera «reentrada». Y es estable en los
cuatro contratos, así que no es ruido de un trimestre.

Una reentrada sin salida previa **no es una reentrada**. Si eso domina el
arquetipo `retorno`, entonces las 260 señales/sesión de `Gaps2` a T=1 no son
«más señal que BigTrap2»: son **otro evento**, y compararlas de frente es
comparar dos cosas distintas.

## La hipótesis, y por qué NO alcanza con que sea plausible

`alejamiento = 0` puede salir de dos situaciones que el cuantil **no
distingue**:

  (a) la zona ya **contiene al precio en el instante en que queda disponible**
      — el primer tick de la ventana ya está dentro de la banda;
  (b) el precio sale de la banda y vuelve, pero sin superarla por un tick
      entero.

Si manda (a), el 0 es un **artefacto del reloj de disponibilidad**: para un
kernel `tick_create` la zona nace en `created_ms + 1 ms`, o sea prácticamente
en el instante de creación — y una zona de gap se construye **alrededor del
precio de ese momento**. Entonces «entrar a la zona» es donde el precio ya
estaba, y el evento es vacío por definición.

Si manda (b), el 0 es un hecho de mercado —oscilación dentro de la banda— y la
lectura es completamente distinta.

**La explicación (a) es la que yo predigo, y por eso justamente hay que
medirla.** Elegir la hipótesis que cuadra con lo que uno espera, sin separarla
de la otra, es fabricar acuerdo. Esta sonda las separa contando el caso (a)
directamente: `i0 dentro de la banda`.

## Qué NO hace

No toca outcomes, no mira P&L, no abre el holdout: sólo cuenta en qué posición
relativa está el precio cuando la zona queda disponible. Corre sobre una
muestra chica —lo que se está midiendo es una proporción cerca de 0 o de 1, no
una diferencia fina— y la muestra se declara en la salida.

Uso:
    .venv\\Scripts\\python diag\\tasa_senales\\sonda_alejamiento_cero.py --sesiones 8
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    CLASE_KERNEL, LEAD_DAYS, MAX_FECHA, REGISTRY, T_DESIGN, TZ_CHART, BAR_DRIVEN,
    bars_mod, corte_del_sello, dias_research, pd, ticks_mod,
)

#: La misma grilla que la curva. Si la curva cambia, esta sonda la sigue: medir
#: la contaminación en umbrales que nadie usa no dice nada.
T_SONDA = T_DESIGN

SALIDA = Path(__file__).resolve().parent / "sonda_alejamiento_cero.json"


def sondear(archivo, fechas, indicadores):
    ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
           - pd.Timedelta(days=LEAD_DAYS))
    fin_contrato = (pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago")
                    + pd.Timedelta(days=1))
    fin = min(fin_contrato.tz_convert("UTC"), corte_del_sello())

    tk = ticks_mod.load_canonical_parquet(
        str(REPO_PATH / "data" / "nt8" / "6E" / archivo),
        start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))
    ts = np.asarray(tk.ts_ns)
    px = np.asarray(tk.price_ticks).astype(np.float64)
    b = bars_mod.build_time_bars(tk, 1)
    bar_end = np.asarray(b.end_ns)
    fp = None

    res = {}
    for nombre in indicadores:
        clase = CLASE_KERNEL.get(nombre)
        if clase is None:
            continue
        mod = REGISTRY[nombre]
        if nombre in BAR_DRIVEN:
            if fp is None:
                fp = bars_mod.build_footprints(tk, b)
            r = mod.run(tk, b, fp, chart_tz=TZ_CHART)
        else:
            r = mod.run(tk, b, chart_tz=TZ_CHART)

        c = Counter()
        distancia_al_borde = []
        # Segunda pregunta, que salio de la primera: un evento cuyo "alejamiento"
        # ES LA POSICION DE PARTIDA no es una excursion. Ver el bloque de abajo.
        vacuo = {t: Counter() for t in T_SONDA}
        for z in r.get("zones") or []:
            if z.get("created_ms") is None or z.get("top") is None:
                continue
            cb = z.get("created_bar")
            if cb is None or not isinstance(cb, (int, np.integer)):
                continue
            if cb < 0 or cb >= len(bar_end):
                continue
            lo_t = z["bottom"] / tk.tick_size
            hi_t = z["top"] / tk.tick_size
            disp_ns = (int(bar_end[int(cb)]) if clase == "bar_close"
                       else (int(z["created_ms"]) + 1) * 1_000_000)
            i0 = int(np.searchsorted(ts, disp_ns, side="right"))
            if i0 >= len(ts):
                c["sin_tramo"] += 1
                continue
            p0 = float(px[i0])
            c["zonas"] += 1
            if lo_t <= p0 <= hi_t:
                # (a) la zona YA contiene al precio cuando queda disponible
                c["precio_dentro_al_quedar_disponible"] += 1
                fuera = 0.0
            else:
                c["precio_fuera_al_quedar_disponible"] += 1
                fuera = (lo_t - p0) if p0 < lo_t else (p0 - hi_t)
                distancia_al_borde.append(fuera)

            # EVENTO VACUO. `eventos_de_zona` calcula la primera cruza sobre la
            # acumulada que ARRANCA EN i0, asi que si el precio ya esta a T o mas
            # ticks del borde en el primer tick de la ventana, `rup_up[T]` (o
            # `rup_dn[T]`) vale 0: una "ruptura" que no rompio nada, y a partir de
            # ahi cualquier vuelta a la banda cuenta como `retorno[T]` sin que
            # haya habido excursion. El alejamiento no lo produjo el precio: LO
            # PRODUJO LA ZONA, que nacio detras de donde el precio ya estaba.
            for t in T_SONDA:
                if fuera >= t:
                    vacuo[t]["ya_afuera_por_T_o_mas"] += 1

        d = dict(c)
        n = d.get("zonas", 0)
        d["clase_kernel"] = clase
        d["frac_dentro"] = (round(d.get("precio_dentro_al_quedar_disponible", 0)
                                  / n, 4) if n else None)
        if distancia_al_borde:
            q = np.percentile(distancia_al_borde, [50, 90])
            d["dist_al_borde_si_fuera"] = dict(p50=float(q[0]), p90=float(q[1]))
        d["frac_vacua_por_umbral"] = {
            str(t): (round(vacuo[t]["ya_afuera_por_T_o_mas"] / n, 4) if n else None)
            for t in T_SONDA}
        res[nombre] = d
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sesiones", type=int, default=8,
                    help="cuántas sesiones del contrato (muestra chica a propósito)")
    ap.add_argument("--contrato", default="6E_09-26_ticks.parquet")
    a = ap.parse_args(argv)

    dias, info = dias_research()
    fechas = sorted({d["fecha"] for d in dias
                     if d["archivo"] == a.contrato})[:a.sesiones]
    if not fechas:
        print("sin sesiones para %s" % a.contrato)
        return 2
    peor = max(fechas)
    assert peor <= MAX_FECHA, "FIREWALL: %s > %s" % (peor, MAX_FECHA)
    print("contrato %s | %d sesiones | max %s <= %s"
          % (a.contrato, len(fechas), peor, MAX_FECHA))

    res = sondear(a.contrato, fechas, sorted(CLASE_KERNEL))

    print("\n¿el precio está DENTRO de la banda en el instante en que la zona "
          "queda disponible?")
    print("  %-16s %-12s %8s %10s %12s" % ("indicador", "clase", "zonas",
                                           "frac_dentro", "borde_p50"))
    for n, d in sorted(res.items(), key=lambda kv: (kv[1]["clase_kernel"], kv[0])):
        db = d.get("dist_al_borde_si_fuera") or {}
        print("  %-16s %-12s %8d %10s %12s"
              % (n, d["clase_kernel"], d.get("zonas", 0),
                 d.get("frac_dentro"), round(db.get("p50", 0), 1)))

    print("\nfraccion de zonas YA a T ticks o mas del borde en el primer tick de "
          "su ventana\n(el alejamiento no lo produjo el precio: lo produjo la "
          "zona, que nacio detras)")
    print("  %-16s %-12s %s" % ("indicador", "clase",
                                " ".join("%7d" % t for t in T_SONDA)))
    for n, d in sorted(res.items(), key=lambda kv: (kv[1]["clase_kernel"], kv[0])):
        f = d.get("frac_vacua_por_umbral") or {}
        print("  %-16s %-12s %s"
              % (n, d["clase_kernel"],
                 " ".join("%7s" % f.get(str(t)) for t in T_SONDA)))

    SALIDA.write_text(json.dumps(
        dict(pregunta="fraccion de zonas cuyo precio ya esta DENTRO de la banda "
                      "en el instante de disponibilidad",
             contrato=a.contrato, sesiones=len(fechas), max_fecha=peor,
             outcomes_accessed=False, por_indicador=res),
        indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n-> %s" % SALIDA)
    return 0


if __name__ == "__main__":
    sys.exit(main())
