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
import os
import subprocess
import sys
import tempfile
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
#: v3: identidad al INICIO -commit, huellas separadas del generador y del
#:     codigo de medicion, fechas exactas, hashes de universo y parquet-,
#:     `payload_sha256` con su nombre correcto y sidecar de bytes.
#: v4: el gate deja de ser "los .py estan limpios" y pasa a ser un CONJUNTO
#:     EXPLICITO DE DEPENDENCIAS derivado de `sys.modules` + manifiesto +
#:     parquet + lockfile. Tres campos separados en vez de uno que mentia:
#:     `git_worktree_dirty_start` (el status COMPLETO),
#:     `dependency_set_dirty_start` (lo unico que bloquea) e
#:     `ignored_generated_outputs` (por ruta exacta, no por extension).
#:     Mas promocion atomica del JSON y sidecar escrito DESPUES.
SCHEMA_VERSION = "sonda_alejamiento_cero_v4"

#: La pregunta va en una constante para que el comparador pueda EXIGIR que
#: coincida: dos artefactos no miden lo mismo si cambia lo que preguntan.
PREGUNTA = ("posicion del precio y del reloj de disponibilidad al inicio "
            "de la ventana de cada zona")

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


def sha_de_archivo(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _rel(p):
    try:
        return Path(p).resolve().relative_to(REPO_PATH).as_posix()
    except Exception:
        return None


def salidas_generadas():
    """Rutas **exactas** que este script escribe. Enumeradas, no filtradas.

    La regla de nombres es determinista (`ruta_de_salida`), así que la familia
    se puede enumerar de disco en vez de describirse por extensión. Excluir por
    extensión —`*.json`— habría tapado también cualquier `.json` de
    configuración que sí es dependencia.
    """
    d = Path(__file__).resolve().parent
    out = set()
    for p in sorted(d.glob("sonda_alejamiento_cero__*.json")):
        r = _rel(p)
        if r:
            out.add(r)
            out.add(r + ".sha256")
    return out


def conjunto_de_dependencias(contrato):
    """Todo lo que puede cambiar el número, con su `sha256`. **Derivado, no
    escrito a mano.**

    ## Por qué no es una lista

    Una lista de dependencias mantenida a mano envejece: alguien agrega un
    `import` y nadie actualiza la lista. Acá los módulos salen de `sys.modules`
    —lo que el proceso **realmente importó**— filtrado a los que viven dentro
    del repo. Si mañana la sonda importa un módulo nuevo, entra solo.

    A eso se suman las dependencias que **no son módulos** y que ningún
    `sys.modules` iba a delatar: el manifiesto de universo (define la muestra),
    el parquet de entrada (son los datos) y el lockfile del entorno (define las
    versiones de numpy/pandas con las que se calculó).

    ## Lo que esto corrige

    La versión anterior filtraba el `git status` por extensión `.py` y llamaba
    a eso «árbol limpio». **No era lo mismo**: un `.py` limpio no dice nada del
    manifiesto, del parquet ni del lock. Y el campo se llamaba
    `working_tree_dirty_start`, que prometía el worktree entero.
    """
    ## Repo y entorno van SEPARADOS, y el motivo no es estético
    ##
    ## Los dos pueden mover un número, pero por causas distintas y con distinto
    ## remedio. Un `.py` del repo que cambia es **código**: se commitea. Un
    ## `.pyd` de `numpy` que cambia es **entorno**: se reinstala desde el lock.
    ## Mezclarlos en un solo hash haría que dos corridas de la misma máquina y
    ## el mismo commit parezcan incomparables por una actualización de pandas
    ## —y, peor, que un cambio de código quede escondido detrás de eso—.
    repo, entorno = {}, {}
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if not f or "__pycache__" in str(f):
            continue
        r = _rel(f)
        if not r or not Path(f).is_file():
            continue
        (entorno if r.startswith(".venv/") else repo)[r] = sha_de_archivo(f)

    extras = [REPO_PATH / "data" / "nt8" / "6E" / contrato,
              REPO_PATH / "requirements" / "core-bridge-dev.lock"]
    try:
        from edgelab.research.universo_estudio import ruta_por_defecto
        extras.append(Path(ruta_por_defecto()))
    except Exception:
        pass
    for p in extras:
        r = _rel(p)
        if r and Path(p).is_file():
            repo[r] = sha_de_archivo(p)
    return repo, entorno


def estado_del_worktree(dependencias):
    """Clasifica **todo** lo sucio en tres cubetas, sin llamarle «limpio» a nada.

    - `git_worktree_dirty_start`  — el `git status` COMPLETO, sin filtrar. Es el
      dato honesto: si el worktree está sucio, el campo lo dice.
    - `dependency_set_dirty_start` — la intersección con el conjunto de
      dependencias. **Es lo único que bloquea**, porque es lo único que puede
      mover un número.
    - `ignored_generated_outputs` — lo sucio que son salidas de este mismo
      script, por ruta exacta.
    - `sin_clasificar` — el resto. **No bloquea, pero se publica**: es la
      superficie que el gate declara no cubrir, y esconderla sería fingir un
      alcance que no tiene.
    """
    try:
        out = subprocess.run(["git", "status", "--porcelain"],
                             cwd=str(REPO_PATH), capture_output=True,
                             text=True, timeout=60).stdout
    except Exception:
        return dict(git_worktree_dirty_start=["(no se pudo consultar git)"],
                    dependency_set_dirty_start=["(no se pudo consultar git)"],
                    ignored_generated_outputs=[], sin_clasificar=[])
    sucio = sorted(l[3:].strip().strip('"') for l in out.splitlines() if l.strip())
    salidas = salidas_generadas()
    return dict(
        git_worktree_dirty_start=sucio,
        dependency_set_dirty_start=sorted(r for r in sucio if r in dependencias),
        ignored_generated_outputs=sorted(r for r in sucio if r in salidas),
        sin_clasificar=sorted(r for r in sucio
                              if r not in dependencias and r not in salidas),
    )


def identidad_de_corrida(contrato, fechas):
    """Todo lo que hace falta para reconstruir ESTA corrida. **Se toma al INICIO.**

    ## Por qué al inicio y no al final

    La versión anterior armaba la identidad **después** de medir, hasheando
    archivos que pudieron cambiar mientras el proceso corría. Y el `code_commit`
    salía de `git_head()`, que en un árbol sucio **no se mueve**: el artefacto de
    8 sesiones quedó declarando `d5a4a2e` cuando el código que lo generó recién
    se commiteó en `bf8c995`. **El commit declarado no permitía reconstruir el
    generador** — que es exactamente lo que un campo de procedencia promete.

    ## Qué cubre, y qué cubría de menos

    `huella_del_codigo()` hashea la curva, `post_sepmin` y los indicadores —pero
    **no esta sonda**—, así que se podía cambiar la lógica de la sonda sin que la
    huella se moviera. Por eso van separados y los dos:

      - `generator_sha256`        — esta sonda
      - `measurement_code_sha256` — curva + post_sepmin + indicadores

    Y la muestra: contrato + cantidad de sesiones + fecha máxima **no identifica
    qué ocho sesiones se usaron**. Van las fechas exactas, su hash, el hash del
    manifiesto de universo y el del parquet de entrada.
    """
    parquet = REPO_PATH / "data" / "nt8" / "6E" / contrato
    try:
        from edgelab.research.universo_estudio import (huella_del_universo,
                                                       ruta_por_defecto)
        uni = huella_del_universo(str(ruta_por_defecto()))["sha256"]
    except Exception:
        uni = None
    dep_repo, dep_entorno = conjunto_de_dependencias(contrato)
    est = estado_del_worktree(dep_repo)
    h = lambda d: hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()
    return dict(
        code_commit_start=git_head(),
        # TRES campos, no uno: el nombre de cada uno dice exactamente qué mira.
        git_worktree_dirty_start=est["git_worktree_dirty_start"],
        dependency_set_dirty_start=est["dependency_set_dirty_start"],
        ignored_generated_outputs=est["ignored_generated_outputs"],
        worktree_sucio_sin_clasificar=est["sin_clasificar"],
        # El conjunto completo con su hash: no hay que creerle al gate, se
        # puede recomputar. REPO y ENTORNO por separado -ver el docstring-.
        dependency_set_repo=dep_repo,
        dependency_set_repo_sha256=h(dep_repo),
        dependency_set_repo_n=len(dep_repo),
        # El entorno NO se lista entero -son ~440 binarios de .venv y ninguna
        # persona los va a leer-: va el hash agregado, que es lo que permite
        # detectar que cambio, mas el lock que lo declara.
        dependency_set_entorno=dep_entorno,
        dependency_set_entorno_sha256=h(dep_entorno),
        dependency_set_entorno_n=len(dep_entorno),
        dependency_set_n=len(dep_repo) + len(dep_entorno),
        # DEMOSTRACION pedida por el auditor: que dependencias mutables hay
        # FUERA de los `.py` del repo. Si esta lista esta vacia, el gate viejo
        # -que miraba solo .py- habria sido suficiente; si no, no lo era.
        dependencias_repo_fuera_de_py=sorted(
            r for r in dep_repo if not r.endswith(".py")),
        generator_sha256=sha_de_archivo(Path(__file__).resolve()),
        measurement_code_sha256=huella_del_codigo(sorted(CLASE_KERNEL)),
        session_dates=list(fechas),
        session_dates_sha256=hashlib.sha256(
            json.dumps(list(fechas), sort_keys=True).encode()).hexdigest(),
        universe_manifest_sha256=uni,
        input_parquet=contrato,
        input_parquet_sha256=sha_de_archivo(parquet) if parquet.exists() else None,
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sesiones", type=int, default=8,
                    help="cuántas sesiones del contrato (muestra chica a propósito)")
    ap.add_argument("--contrato", default="6E_09-26_ticks.parquet")
    ap.add_argument("--permitir-arbol-sucio", action="store_true",
                    help="SOLO para diagnóstico: el artefacto sale marcado y no "
                         "puede usarse como canónico")
    a = ap.parse_args(argv)

    dias, info = dias_research()
    fechas = sorted({d["fecha"] for d in dias
                     if d["archivo"] == a.contrato})[:a.sesiones]
    if not fechas:
        print("sin sesiones para %s" % a.contrato)
        return 2
    peor = max(fechas)
    assert peor <= MAX_FECHA, "FIREWALL: %s > %s" % (peor, MAX_FECHA)

    # IDENTIDAD AL INICIO. Fail-closed sobre DEPENDENCIAS sucias: un artefacto
    # generado desde código sin commitear declara un commit que NO lo contiene,
    # y eso es peor que no declarar nada -- promete una reconstrucción que no
    # existe. Bloquea el conjunto de dependencias, no el worktree entero: ver
    # `estado_del_worktree` para por qué son cosas distintas.
    ident = identidad_de_corrida(a.contrato, fechas)
    if ident["dependency_set_dirty_start"] and not a.permitir_arbol_sucio:
        print("DEPENDENCIAS SUCIAS -- no se publica. Sin commitear:")
        for r in ident["dependency_set_dirty_start"]:
            print("   %s" % r)
        print("\nEstan en el conjunto de %d dependencias de repo que pueden mover"
              % ident["dependency_set_repo_n"])
        print("el numero. El artefacto declararia `code_commit` = %s, que NO las"
              % (ident["code_commit_start"] or "?")[:12])
        print("contiene. Con --permitir-arbol-sucio sale MARCADO como diagnostico")
        print("y el comparador lo rechaza como canonico.")
        return 2

    print("contrato %s | %d sesiones | max %s <= %s"
          % (a.contrato, len(fechas), peor, MAX_FECHA))
    print("commit %s | generador %s | medicion %s"
          % ((ident["code_commit_start"] or "?")[:12],
             ident["generator_sha256"][:12],
             ident["measurement_code_sha256"][:12]))

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
    # RE-VERIFICACION AL CIERRE. Si el código cambió MIENTRAS la corrida estaba
    # viva, el artefacto describiría un generador que ya no existe. Se aborta
    # sin publicar: un artefacto a medias es recuperable, uno que miente no.
    #
    # SE COMPARAN HASHES DE LOS ARCHIVOS QUE YA ESTABAN, NO LOS CONJUNTOS.
    # La primera versión comparaba `dependency_set_*_sha256` de punta a punta y
    # **abortaba siempre**: `sys.modules` CRECE durante la corrida —`pyarrow`
    # importa submódulos recién al leer el parquet—, así que el conjunto final
    # nunca es el inicial. Eso confundía dos cosas distintas:
    #
    #   - que un archivo CAMBIE       -> peligroso, aborta
    #   - que se importe uno NUEVO    -> esperado, se registra y sigue
    #
    # Un gate que aborta siempre no es estricto: es un gate que alguien va a
    # desactivar.
    fin = identidad_de_corrida(a.contrato, fechas)
    movidos = [(k, ident[k], fin[k])
               for k in ("code_commit_start", "generator_sha256",
                         "measurement_code_sha256", "universe_manifest_sha256",
                         "input_parquet_sha256", "dependency_set_repo_sha256")
               if ident[k] != fin[k]]
    # entorno: sólo los que ya estaban, y sólo si cambió su contenido
    ent_ini = ident["dependency_set_entorno"]
    ent_fin = fin["dependency_set_entorno"]
    movidos += [("entorno:" + r, ent_ini[r], ent_fin[r])
                for r in sorted(ent_ini) if r in ent_fin and ent_ini[r] != ent_fin[r]]
    if movidos:
        print("\nCAMBIO UNA DEPENDENCIA DURANTE LA CORRIDA -- no se publica.")
        for k, va, vb in movidos:
            print("   %-30s %.16s -> %.16s" % (k, va, vb))
        return 2

    # Lo que se importó DESPUÉS del arranque: no es un error, pero es parte de
    # la identidad y se publica en vez de desaparecer.
    nuevos = sorted(set(ent_fin) - set(ent_ini))
    ident["entorno_importado_durante_la_corrida"] = nuevos
    ident["dependency_set_entorno_n_fin"] = len(ent_fin)
    ident["dependency_set_entorno_sha256_fin"] = hashlib.sha256(
        json.dumps(ent_fin, sort_keys=True).encode()).hexdigest()

    payload = dict(
        schema_version=SCHEMA_VERSION,
        pregunta=PREGUNTA,
        contrato=a.contrato, sesiones=len(fechas), max_fecha=peor,
        firewall_max_fecha=MAX_FECHA,
        firewall_corte_utc_ns=int(corte_del_sello().value),
        firewall_corte_iso=str(corte_del_sello()),
        umbrales=list(T_SONDA),
        definiciones=DEFINICIONES,
        umbral_material_ns=UMBRAL_MATERIAL_NS,
        clase_kernel=dict(CLASE_KERNEL),
        identidad=ident,
        diagnostico_arbol_sucio=bool(ident["dependency_set_dirty_start"]),
        outcomes_accessed=False,
        por_indicador=res)

    # `payload_sha256`, NO `output_sha256`. El nombre viejo prometia el hash del
    # ARCHIVO y era otra cosa: se calcula sobre el payload ANTES de agregar este
    # mismo campo y con una serializacion canonica -sort_keys, sin indent- que
    # no es la de escritura. Es un hash de CONTENIDO sin autorreferencia, util y
    # valido, pero hay que llamarlo por su nombre. El sha256 de los BYTES del
    # archivo va aparte, en el sidecar `.sha256`.
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    salida = ruta_de_salida(a.contrato, len(fechas))
    salida.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    sidecar = salida.with_suffix(salida.suffix + ".sha256")
    sidecar.write_text("%s  %s\n" % (sha_de_archivo(salida), salida.name),
                       encoding="utf-8")

    print("\nschema  %s" % SCHEMA_VERSION)
    print("payload %s   (hash de contenido, excluye este campo)"
          % payload["payload_sha256"][:16])
    print("bytes   %s   (sha256 real del archivo -> %s)"
          % (sha_de_archivo(salida)[:16], sidecar.name))
    print("-> %s" % salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
