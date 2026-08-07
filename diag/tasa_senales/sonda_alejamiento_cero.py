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
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    CLASE_KERNEL, LEAD_DAYS, MAX_FECHA, REGISTRY, T_DESIGN, TZ_CHART, BAR_DRIVEN,
    bars_mod, corte_del_sello, dias_research, git_head, huella_del_codigo,
    pd, ticks_mod,
)

#: Sube cuando cambia el CONJUNTO DE CAMPOS o la semántica de alguno. Dos
#: artefactos con `schema_version` distinto **no se comparan**: `comparar_sondas.py`
#: falla en vez de alinear campos que no significan lo mismo.
SCHEMA_VERSION = "sonda_alejamiento_cero_v2"

#: La misma grilla que la curva. Si la curva cambia, esta sonda la sigue: medir
#: la contaminación en umbrales que nadie usa no dice nada.
T_SONDA = T_DESIGN

#: Un adelanto de 1 ms **no** es fuga: para un kernel `bar_close` la zona nace
#: EN el cierre, así que `created_ms + 1` deja siempre esa diferencia por la
#: propia convención. Sin este umbral los tres controles dan 100 % — cierto y
#: vacío. Con él caen a 0,0 %, y ese cero es lo que prueba que el efecto es de
#: CLASE y no de medición.
UMBRAL_MATERIAL_NS = 1_000_000_000

#: Qué mide cada cifra, adentro del artefacto. Un número cuya definición hay que
#: ir a buscar al código es un número que se va a citar mal.
DEFINICIONES = {
    "frac_dentro":
        "fraccion de zonas cuyo precio esta DENTRO de la banda en el primer "
        "tick posterior a `available_ns`",
    "frac_cualquier_adelanto":
        "fraccion con `bar_end[created_bar] < (created_ms+1)*1e6`, SIN umbral. "
        "Es la definicion de la medicion historica 99%/97%",
    "frac_adelanto_mayor_1s":
        "lo mismo, pero exigiendo un adelanto MATERIAL > `umbral_material_ns`",
    "frac_vacua_por_umbral":
        "fraccion de zonas ya a T ticks o mas del borde en el primer tick de la "
        "ventana: su `k_T` valdria 0, o sea que el alejamiento NO lo produjo el "
        "precio despues de la disponibilidad",
}

def ruta_de_salida(contrato, n_sesiones):
    """Un archivo POR CORRIDA, no uno fijo.

    La primera versión escribía siempre `sonda_alejamiento_cero.json`, así que
    la corrida de 40 sesiones **pisó en silencio** la de 8 — y las dos eran
    evidencia: la chica es la que expuso el plateau espurio de `VolTicksPOC2`
    que la grande después descartó. Perder la corrida anterior es perder la
    comparación, que acá es justamente el control.

    Es el mismo modo de falla que `ESPEC_TEST_EXPLORE-001.md`, que existe dos
    veces con el mismo nombre y contenidos distintos.
    """
    base = contrato.replace("_ticks.parquet", "").replace(".parquet", "")
    return (Path(__file__).resolve().parent
            / ("sonda_alejamiento_cero__%s_%02ds.json" % (base, n_sesiones)))


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
        adelanto_s = []        # cuanto ANTES abriria la ventana el reloj de barra
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

            # SEGUNDA MEDICION, y esta reproduce una afirmacion PUBLICADA.
            #
            # `curva_excursion_ticks.py` declara, para justificar el split por
            # clase de kernel, que usar `bar_end[created_bar]` en un kernel
            # `tick_create` abriria la ventana "~21-27 s ANTES de que la zona
            # existiera -medido: 99% de las zonas de Gaps2 y 97% de HFTZones2-".
            #
            # Ese numero sostiene la reclasificacion, que movio las senales un
            # 20%. Estaba publicado y su evidencia NO estaba versionada: vivia
            # en un script de un directorio temporal. Se remide aca, gratis,
            # porque los dos relojes salen de datos que este loop ya tiene.
            ns_cierre = int(bar_end[int(cb)])
            ns_creacion = (int(z["created_ms"]) + 1) * 1_000_000
            if ns_cierre < ns_creacion:
                c["cierre_de_barra_ANTES_de_existir"] += 1
                adelanto_s.append((ns_creacion - ns_cierre) / 1e9)
                # UMBRAL MATERIAL. Sin esto la metrica enganaba: para un kernel
                # `bar_close` la zona nace EN el cierre, asi que `created_ms` es
                # ese mismo instante truncado a ms y el `+1 ms` lo deja siempre
                # 1 ms despues. Resultado: frac = 1,00 para los tres bar_close,
                # con adelanto mediano de 0,0 s. Cierto y vacio -contaba el
                # milisegundo de la propia convencion como si fuera fuga-.
                if ns_creacion - ns_cierre > 1_000_000_000:
                    c["adelanto_mayor_a_1s"] += 1

            disp_ns = ns_cierre if clase == "bar_close" else ns_creacion
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
        if adelanto_s:
            q = np.percentile(adelanto_s, [50, 90])
            d["reloj_de_barra_abriria_antes"] = dict(
                n=len(adelanto_s),
                frac_cualquier_adelanto=round(len(adelanto_s) / n, 4) if n else None,
                frac_adelanto_mayor_1s=(round(d.get("adelanto_mayor_a_1s", 0) / n, 4)
                                        if n else None),
                adelanto_s_p50=round(float(q[0]), 1),
                adelanto_s_p90=round(float(q[1]), 1))
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

    print("\nreproduce la afirmacion PUBLICADA que justifica el split por clase:")
    print("usar bar_end[created_bar] en un kernel tick_create abriria la ventana")
    print("ANTES de que la zona existiera")
    print("  %-16s %-12s %12s %13s %13s" % ("indicador", "clase", "frac_>1s",
                                            "adelanto_p50", "adelanto_p90"))
    for n, d in sorted(res.items(), key=lambda kv: (kv[1]["clase_kernel"], kv[0])):
        r = d.get("reloj_de_barra_abriria_antes") or {}
        print("  %-16s %-12s %12s %13s %13s"
              % (n, d["clase_kernel"], r.get("frac_adelanto_mayor_1s", 0.0),
                 r.get("adelanto_s_p50", "-"), r.get("adelanto_s_p90", "-")))

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

    # IDENTIDAD DEL ARTEFACTO. Dos corridas de esta sonda tienen que poder
    # compararse SIN adivinar: la primera version emitia sólo `contrato`,
    # `sesiones` y `por_indicador`, y cuando se le agregó la medición del reloj
    # quedaron dos artefactos versionados del MISMO script con conjuntos de
    # campos distintos y nada que lo explicara. Ese es el defecto que estos
    # campos cierran — y lo cierra `comparar_sondas.py`, que falla si el
    # `schema_version` no coincide en vez de comparar peras con manzanas.
    payload = dict(
        schema_version=SCHEMA_VERSION,
        pregunta="posicion del precio y del reloj de disponibilidad al inicio "
                 "de la ventana de cada zona",
        contrato=a.contrato, sesiones=len(fechas), max_fecha=peor,
        firewall_max_fecha=MAX_FECHA,
        firewall_corte_utc_ns=int(corte_del_sello().value),
        firewall_corte_iso=str(corte_del_sello()),
        umbrales=list(T_SONDA),
        definiciones=DEFINICIONES,
        umbral_material_ns=UMBRAL_MATERIAL_NS,
        clase_kernel=dict(CLASE_KERNEL),
        huella_del_codigo=huella_del_codigo(sorted(CLASE_KERNEL)),
        code_commit=git_head(),
        outcomes_accessed=False,
        por_indicador=res)
    payload["output_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    salida = ruta_de_salida(a.contrato, len(fechas))
    salida.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print("\nschema %s | huella %s | sha %s"
          % (SCHEMA_VERSION, payload["huella_del_codigo"][:12],
             payload["output_sha256"][:12]))
    print("-> %s" % salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
