# -*- coding: utf-8 -*-
"""Curva de diseño outcome-free, **sobre TICKS**. Supersede a la versión M1.

## Por qué existe: la versión sobre barras de minuto descartaba el 90 %

`curva_excursion.py` (M1) mide sobre barras de 1 minuto. Al implementar la regla
de **ABSTAIN por orden intrabar indemostrable** que pidió el auditor, el piloto
devolvió:

    AACloseOpenDiffs   7179 de 7858 zonas abstenidas  (91,4 %)
    BigTrap2            570 de  696                   (81,9 %)

La regla era correcta y el resultado inutilizable. **La causa no era la regla:
era el insumo.** El rango de una barra de un minuto casi siempre toca la banda
*y* se aleja, y desde ese OHLC el orden es indemostrable.

**Bajar el umbral de ambigüedad habría sido un fail-open** (así lo llamó Nico).
La corrección es leer los ticks, que ya están en disco.

## Por qué acá la ambigüedad se resuelve, y está MEDIDO

En 6E el **66,1 %** de los ticks consecutivos comparte `ts_ns` — el intervalo
mediano entre ticks es 0 ms, que es lo que `HIPOTESIS_PENDIENTES.md` ya
documentaba. Así que `ts_ns` **solo** no ordena.

Pero el esquema F2 trae `sequence`, el **orden estable del ARCHIVO**.

> **`sequence` NO es verdad de mercado.** Es el orden de fila del F2, no el orden
> del matching engine del exchange. Sirve para **determinismo reproducible** —dos
> corridas sobre el mismo archivo dan lo mismo— y **no** para afirmar qué pasó
> primero en el libro. La formulación correcta del orden es
> **`(ts_ns, sequence_de_archivo)`**, y así se declara en el manifiesto.
Verificado sobre datos reales (6E 03-26, 317.064 ticks):

    sequence estrictamente creciente ..... sí
    duplicados ........................... 0
    crece dentro de los empates de ts_ns .. sí
    mayor grupo de ts_ns empatado ........ 185 ticks

Un tick es un **punto**: está dentro de la banda o afuera. Con orden total no hay
"hizo las dos cosas". La ambigüedad **de lectura** desaparece: sobre `(ts_ns, sequence)` el orden es
total y la corrida es reproducible. Lo que **no** se afirma es que ése sea el
orden económico verdadero — para eso haría falta el libro, que no está. Y el
guard sigue: si `sequence` no fuera orden total en la ventana, la unidad ABSTIENE.

## RELOJ DE DISPONIBILIDAD — **una regla por CLASE de kernel, no una sola**

`available_ns = bar_end[created_bar]` es correcto **sólo para kernels que crean
al CIERRE de la barra**. Aplicarlo a los que crean **a mitad de barra** mete en
la ventana ticks anteriores a que la zona existiera.

**Medido** sobre 6E 03-26 (10 días), fracción de zonas con
`created_ms > bar_end[created_bar]` —o sea **cualquier** adelanto, sin umbral—
y retraso mediano:

| indicador | clase | zonas afectadas | retraso mediano |
|---|---|---|---|
| `BigTrap2` | `bar_close` | **0 %** | — |
| `VolTicksPOC2` | `bar_close` | **0 %** | — |
| `aVolCellPOI2` | `bar_close` | — | — |
| **`Gaps2`** | **`tick_create`** | **99 %** | **21,5 s** |
| **`HFTZones2`** | **`tick_create`** | **97 %** | **27,5 s** |

> **Estatus (2026-08-07): REPRODUCE.** Se replicó con
> `sonda_alejamiento_cero.py` sobre **8 sesiones de 6E 09-26** —otro contrato,
> otro trimestre— **bajo la misma definición**: `Gaps2` **100 %** (p50 27,7 s) y
> `HFTZones2` **96,4 %** (p50 28,2 s). Las fracciones reproducen. El p50 de
> `Gaps2` difiere ~6 s entre contratos (21,5 → 27,7); el de `HFTZones2` no.
>
> El `0 %` de los tres `bar_close` **sólo vale con un umbral material**: sin
> umbral dan 100 %, porque para un kernel que crea al cierre el `created_ms + 1`
> deja 1 ms de diferencia **por la propia convención**. Con umbral > 1 s los
> tres caen a 0,0 % y los `tick_create` a 96,7 % / 92,9 %. Ese control a cero es
> lo que confirma que el efecto es **de clase**, no de medición.
>
> Artefactos: los dos `sonda_alejamiento_cero__*.json`.

En una barra de un minuto, 21-27 s son **~35-45 % de la barra** contaminando la
ventana. Misma familia que el `-1`: **no explota, miente**.

```text
bar_close   (BigTrap2, VolTicksPOC2, aVolCellPOI2):
    available_ns = bar_end[created_bar]          # path M1

tick_create (Gaps2, HFTZones2):
    available_ns = (created_ms + 1) en ns        # NO bar_end[created_bar]
    i0 = primer tick ESTRICTAMENTE posterior a la creación
```

**El `+1 ms` no es un margen arbitrario.** `created_ms` es una **truncación** del
`ts_ns` del tick creador, así que `ts > created_ms·10⁶` podría incluir **al
propio tick que creó la zona**. Avanzar al milisegundo siguiente garantiza
«estrictamente posterior» al costo de descartar, como mucho, 1 ms. Fail-closed.

> **Prohibido unificar las dos clases bajo una sola regla**, y prohibido mezclar
> un `created_bar` de otra `bar_spec` contra `bar_end` de M1. Este path es
> **`time:1` / M1**; la clase de cada indicador se declara en el manifiesto.

## Frontera outcome-free

- Universo: sólo sesiones que entrega la **puerta research**.
- **Máximo `ts_ns` cargado ≤ 2026-06-30**, verificado y publicado. La ventana
  sellada no se lee ni se escanea.
- La entrada empieza en el instante en que la zona está **disponible**, que
  **depende de la clase del kernel** (ver «Reloj de disponibilidad»):
  `bar_end[created_bar]` para `bar_close`, `(created_ms+1)` para `tick_create`.
  Nunca el timestamp de anclaje a secas.
- Se mide en `(disponible, primera resolución]`. Nada posterior.
- `outcomes_accessed: false` en el manifiesto y en cada checkpoint.

**Sólo se emiten datos target-free:** eventos elegibles, señales por sesión,
cobertura, descartes con motivo, ambigüedades y tiempo de cómputo. **Ningún**
retorno posterior, P&L, TP/SL, expectativa ni «mejor T».
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales import post_sepmin as post_sepmin_mod  # noqa: E402
from diag.tasa_senales.post_sepmin import (  # noqa: E402
    BAR_DRIVEN, LEAD_DAYS, REGISTRY, TZ_CHART, bars_mod, dias_research,
    git_head, pd, ticks_mod,
)

CT = ZoneInfo("America/Chicago")

#: Grilla de DISEÑO, no confirmatoria. El auditor lo separó explícitamente en la
#: DRAFT v0.2: sirve para elegir una grilla confirmatoria sin adivinar, y no es
#: ella misma la grilla que se va a testear. Sin el 0: «alejarse 0 ticks» no es
#: un alejamiento, es la regla de hoy.
T_DESIGN = (1, 2, 3, 5, 8, 13, 21, 34)

#: CLASE DE KERNEL: decide de dónde sale el reloj de disponibilidad. Fail-closed:
#: un indicador que no esté acá NO se estima — se descarta y se cuenta.
CLASE_KERNEL = {
    "BigTrap2": "bar_close",
    "VolTicksPOC2": "bar_close",
    "aVolCellPOI2": "bar_close",
    "Gaps2": "tick_create",
    "HFTZones2": "tick_create",
    # AACloseOpenDiffs no entra: no exporta `created_bar` ni tiene ZONE_TOUCHED.
}

#: FIREWALL. `MAX_FECHA` es una fecha de **SESIÓN CT**, no un corte civil UTC.
#:
#: La v1 cortaba en `2026-06-30 23:59:59 UTC`, que son las **18:59 CT** — y la
#: sesión `2026-07-01`, primer día del holdout, **arranca a las 17:00 CT**. O sea
#: que dejaba entrar **2 horas de la primera sesión sellada**. Fuga latente: los
#: pilotos corrieron sobre diciembre 2025 y nunca la dispararon, pero la corrida
#: completa sí la habría disparado.
#:
#: El corte correcto es el INICIO de la sesión siguiente a `MAX_FECHA`, con la
#: misma convención que usa todo el proyecto (17:00 America/Chicago,
#: `[inicio, fin)`; ver `SESION_HORA_CORTE` en `pred004_analyze.py` y
#: `bars.py::session_ids`).
MAX_FECHA = "2026-06-30"
SESION_HORA_CORTE = 17
SESION_TZ = "America/Chicago"


def corte_del_sello():
    """Primer instante EXCLUIDO: el inicio de la sesión siguiente a MAX_FECHA."""
    d = pd.Timestamp(MAX_FECHA, tz=SESION_TZ) + pd.Timedelta(hours=SESION_HORA_CORTE)
    return d.tz_convert("UTC")

SALIDA = Path(__file__).resolve().parent / "curva_excursion_ticks.json"
CHECKPOINT = Path(__file__).resolve().parent / "curva_excursion_ticks.checkpoint.json"


class CheckpointMismatch(RuntimeError):
    """El checkpoint no corresponde a esta corrida. Fail-closed a propósito."""


def huella_del_codigo(indicadores):
    """sha256 de las fuentes que realmente pueden mover un resultado.

    Reemplaza a `git_head()` dentro de la clave. **`git_head()` era demasiado
    grueso y eso lo volvía inútil:** devuelve el HEAD del repo, así que
    commitear un README invalidaba un checkpoint de 24 h de cómputo. Fail-closed
    sobre cambios que no pueden afectar el número no es prudencia — es tirar el
    checkpoint por ruido.

    Y era demasiado FINO en el otro sentido, que es peor: en un árbol sucio el
    HEAD no cambia aunque se edite el kernel, así que editar `bigtrap2.py` sin
    commitear dejaba el checkpoint pasando como válido.

    Se hashean los BYTES de: este script, `post_sepmin` (de donde salen las
    barras, el universo y el registro) y el módulo de cada indicador medido.
    Cambió algo que puede mover un número → cambia la clave, commiteado o no.
    """
    fuentes = [Path(__file__).resolve(),
               Path(post_sepmin_mod.__file__).resolve()]
    for n in sorted(indicadores):
        m = REGISTRY.get(n)
        f = getattr(m, "__file__", None)
        if f:
            fuentes.append(Path(f).resolve())
    h = hashlib.sha256()
    for p in fuentes:
        # el nombre entra al hash: mover un archivo ES un cambio de identidad
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def clave_de_corrida(plan, indicadores):
    """Identidad de lo que se está midiendo.

    Misma disciplina que `post_sepmin.clave_de_corrida`: si cualquiera de estos
    cambia, el checkpoint viejo **no se puede mezclar** — sería juntar dos
    configuraciones distintas dentro de una misma curva.

    Incluye `CLASE_KERNEL` a propósito: reclasificar un indicador de
    `tick_create` a `bar_close` mueve sus señales un 20 %, así que un checkpoint
    de antes de la reclasificación **no es reutilizable**.

    **Limitación conocida, y no es un detalle:** `indicadores` está en la clave,
    así que AGREGAR un indicador invalida el checkpoint entero y obliga a
    recalcular los que ya estaban. El checkpoint sirve para reanudar una corrida
    interrumpida, **nunca** para extender una corrida cerrada. Es correcto
    —mezclar dos universos de indicadores dentro de una curva sería falsear el
    denominador— pero conviene saberlo antes de planificar un «le agrego uno».
    """
    from edgelab.research.universo_estudio import huella_del_universo, ruta_por_defecto
    try:
        uni = huella_del_universo(str(ruta_por_defecto()))["sha256"]
    except Exception:
        uni = None
    payload = json.dumps({
        "schema_version": "curva_excursion_ticks_v1",
        "plan": [[a, list(f)] for a, f in plan],
        "indicadores": sorted(indicadores),
        "universo_sha256": uni,
        "huella_del_codigo": huella_del_codigo(indicadores),
        "t_design": list(T_DESIGN),
        "lead_days": LEAD_DAYS,
        "firewall_corte_utc_ns": int(corte_del_sello().value),
        "clase_kernel": dict(sorted(CLASE_KERNEL.items())),
    }, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def leer_checkpoint(path, clave):
    """Resultados ya calculados, o `{}`. **Falla cerrado** si el checkpoint es de
    otra corrida: no se descarta en silencio porque esa discrepancia **es
    información** — alguien cambió el universo, el código o la clasificación."""
    if not path.exists():
        return {}
    ck = json.loads(path.read_text(encoding="utf-8"))
    if ck.get("clave_de_corrida") != clave:
        raise CheckpointMismatch(
            "el checkpoint %s es de OTRA corrida (universo, commit, T_design, "
            "firewall o CLASE_KERNEL distintos). Se CONSERVA sin tocar. Para "
            "empezar de cero: --fresh." % path.name)
    return ck.get("hecho", {})


def escribir_checkpoint(path, clave, hecho, plan, indicadores):
    """Se reescribe entero después de CADA `(contrato, indicador)`, con
    escritura atómica `.tmp` → `replace`. Es el grano más fino disponible."""
    faltan = sum(1 for a, _ in plan for i in indicadores
                 if i not in hecho.get(a, {}))
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps({
        "complete": faltan == 0,
        "aviso": "CURVA PARCIAL — checkpoint de reanudación, NO es una curva "
                 "cerrada ni autoritativa.",
        "clave_de_corrida": clave,
        "unidades_pendientes": faltan,
        "outcomes_accessed": False,
        "hecho": hecho,
    }, indent=1, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)
SUPERSEDE = "diag/tasa_senales/curva_excursion.py (M1) — 91,4 % de ABSTAIN"


def sesion_ct(ns):
    d = datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).astimezone(CT)
    return (d.date().isoformat() if d.hour < 17
            else (d + pd.Timedelta(days=1)).date().isoformat())


def eventos_de_zona(px, lo_t, hi_t, i0, i1, umbrales):
    """Vectorizado sobre el tramo de ticks `[i0, i1)`. Un tick es un PUNTO.

    Devuelve `(rup_up, rup_dn, retorno, primera)` con índices relativos, o
    `None` si el tramo está vacío.

    - `rup_up[T]` / `rup_dn[T]`: primer tick que se aleja >= T por arriba / abajo.
      **Relojes separados**: la ruptura no exige regreso.
    - `retorno[T]`: primer tick DENTRO de la banda habiéndose alejado antes >= T.
      Reloj propio: exige el regreso.

    No hay caso ambiguo: con orden total un tick está dentro o afuera, y el
    acumulado `lejos` es el máximo ESTRICTAMENTE ANTERIOR (por eso el shift).
    """
    if i1 <= i0:
        return None
    p = px[i0:i1]
    d_up = np.maximum(p - hi_t, 0)
    d_dn = np.maximum(lo_t - p, 0)
    dentro = (p >= lo_t) & (p <= hi_t)
    # `lejos` ANTES del tick actual: un tick dentro de la banda no puede
    # justificar su propio retorno.
    lejos_prev = np.concatenate(([0], np.maximum.accumulate(
        np.maximum(d_up, d_dn))[:-1]))

    def primero(mask):
        return int(np.argmax(mask)) if mask.any() else None

    rup_up, rup_dn, retorno = {}, {}, {}
    for T in umbrales:
        a = primero(d_up >= T)
        if a is not None:
            rup_up[T] = a
        b = primero(d_dn >= T)
        if b is not None:
            rup_dn[T] = b
        c = primero(dentro & (lejos_prev >= T))
        if c is not None:
            retorno[T] = c
    d1 = primero(dentro)
    primera = float(lejos_prev[d1]) if d1 is not None else None
    return rup_up, rup_dn, retorno, primera


def medir(archivo, fechas, indicadores, lead=LEAD_DAYS, verbose=True,
          on_unidad=None):
    ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
           - pd.Timedelta(days=lead))
    # FIREWALL: el fin de carga se recorta al minimo entre el ultimo dia del
    # contrato y MAX_FECHA. No se escanea un tick del holdout.
    fin_contrato = pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago") + pd.Timedelta(days=1)
    fin = min(fin_contrato.tz_convert("UTC"), corte_del_sello())

    t0 = time.time()
    tk = ticks_mod.load_canonical_parquet(
        str(REPO_PATH / "data" / "nt8" / "6E" / archivo),
        start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))
    ts = np.asarray(tk.ts_ns)
    px = np.asarray(tk.price_ticks).astype(np.float64)
    sq = np.asarray(tk.sequence)

    # GUARD: sin orden total no hay como demostrar el orden intrabar => ABSTAIN
    # de toda la unidad. Es el caso que el auditor exigio no dar por resuelto.
    orden_total = bool((np.diff(sq) > 0).all())
    max_ts = int(ts[-1]) if len(ts) else 0
    if verbose:
        print("   ticks=%d  orden_total=%s  max_ts=%s  (%.0fs)"
              % (len(ts), orden_total, sesion_ct(max_ts) if max_ts else "-",
                 time.time() - t0), flush=True)
    if not orden_total:
        return {n: dict(estado="ABSTAIN",
                        motivo="`sequence` no es orden total en la ventana: el "
                               "orden intrabar no es demostrable")
                for n in indicadores}

    b = bars_mod.build_time_bars(tk, 1)
    bar_end = np.asarray(b.end_ns)
    fp = None
    setf = set(fechas)
    res = {}
    for nombre in indicadores:
        t1 = time.time()
        clase_ind = CLASE_KERNEL.get(nombre)
        mod = REGISTRY[nombre]
        if nombre in BAR_DRIVEN:
            if fp is None:
                fp = bars_mod.build_footprints(tk, b)
            r = mod.run(tk, b, fp, chart_tz=TZ_CHART)
        else:
            r = mod.run(tk, b, chart_tz=TZ_CHART)
        zonas = r.get("zones") or []
        tick_size = tk.tick_size
        ARQ = ("retorno", "ruptura_arriba", "ruptura_abajo")
        por = {a: {t: Counter() for t in T_DESIGN} for a in ARQ}
        por_kind = {a: {t: Counter() for t in T_DESIGN} for a in ARQ}
        alej, n_sin_tramo, n_sin_campos, n_sin_created_bar = [], 0, 0, 0
        n_sin_clase = 0
        for z in zonas:
            if z.get("created_ms") is None or z.get("top") is None:
                n_sin_campos += 1
                continue
            lo_t, hi_t = z["bottom"] / tick_size, z["top"] / tick_size
            # DISPONIBLE, no anclado: la entrada empieza al CIERRE de la barra
            # creadora. Se toma de `created_bar` EXPORTADO por el kernel, no se
            # reconstruye desde `created_ms`: esa reconstruccion truncaba ns,
            # podia anclar la barra equivocada, y trataba distinto a kernels con
            # semanticas de `created_ms` distintas.
            #
            # FAIL-CLOSED: sin `created_bar` la zona NO se estima con heuristica.
            # Se cuenta aparte y se abstiene.
            clase = CLASE_KERNEL.get(nombre)
            if clase is None:
                n_sin_clase += 1
                continue
            cb = z.get("created_bar")
            if cb is None or not isinstance(cb, (int, np.integer)):
                n_sin_created_bar += 1
                continue
            # `cb < 0` NO es un detalle: `gaps2.py:12` declara que antes del
            # primer cierre primario vale -1, y en Python `bar_end[-1]` es la
            # ULTIMA barra. Sin este guard la zona no fallaba: anclaba su
            # disponibilidad al final de la serie, en silencio. Es el peor modo
            # de falla -no explota, miente-.
            if cb < 0 or cb >= len(bar_end):
                n_sin_created_bar += 1
                continue
            if clase == "bar_close":
                disp_ns = int(bar_end[int(cb)])
            else:
                # tick_create: la zona nace a MITAD de la barra siguiente al
                # ultimo cierre. `bar_end[created_bar]` arrancaria la ventana
                # ANTES de que la zona existiera.
                #
                # LA CIFRA Y SU ESTATUS -- REPRODUCE. Ver la tabla del docstring
                # de este archivo para la medicion original y su muestra.
                #
                #   ORIGINAL: 6E 03-26, 10 dias, definicion `created_ms >
                #   bar_end[created_bar]` = CUALQUIER adelanto, sin umbral.
                #       Gaps2 99%  (p50 21,5 s)   HFTZones2 97%  (p50 27,5 s)
                #
                #   CORROBORACION (2026-08-07), sonda_alejamiento_cero.py,
                #   8 sesiones de 6E_09-26 -otro contrato, otro trimestre-,
                #   BAJO LA MISMA DEFINICION:
                #       Gaps2 100% (p50 27,7 s)   HFTZones2 96,4% (p50 28,2 s)
                #
                # Las fracciones reproducen. El p50 de Gaps2 difiere ~6 s entre
                # contratos (21,5 vs 27,7); el de HFTZones2 no (27,5 vs 28,2).
                #
                # Con un umbral MATERIAL de >1 s da 96,7% / 92,9%, y los tres
                # `bar_close` caen a 0,0% -sin umbral dan 100%, porque para un
                # kernel que crea AL CIERRE el `created_ms + 1` deja 1 ms de
                # diferencia por la propia convencion-. Ese control a 0% es lo
                # que confirma que el efecto es de clase, no de medicion.
                #
                # Ver docs/SCRATCHPAD_PROVENANCE_AUDIT_2026-08-07.md §4.
                #
                # `+1 ms` porque `created_ms` TRUNCA el ts_ns del tick creador:
                # sin eso, `ts > created_ms*1e6` podria incluir ese mismo tick.
                disp_ns = (int(z["created_ms"]) + 1) * 1_000_000
            i0 = int(np.searchsorted(ts, disp_ns, side="right"))
            fin_ms = z.get("ended_ms")
            i1 = (int(np.searchsorted(ts, int(fin_ms) * 1_000_000, side="right"))
                  if fin_ms else len(ts))
            out = eventos_de_zona(px, lo_t, hi_t, i0, min(i1, len(ts)), T_DESIGN)
            if out is None:
                n_sin_tramo += 1
                continue
            rup_up, rup_dn, ret, primera = out
            if primera is not None:
                alej.append(primera)
            k = z.get("kind") or "?"
            for a, d in (("retorno", ret), ("ruptura_arriba", rup_up),
                         ("ruptura_abajo", rup_dn)):
                for T, rel in d.items():
                    f = sesion_ct(int(ts[i0 + rel]))
                    if f in setf:
                        por[a][T][f] += 1
                        por_kind[a][T][k + "|" + f] += 1
        res[nombre] = dict(
            estado="OK", zonas=len(zonas),
            kinds=dict(Counter(z.get("kind") for z in zonas)),
            zonas_sin_tramo_de_ticks=n_sin_tramo,
            zonas_sin_campos=n_sin_campos,
            zonas_sin_created_bar=n_sin_created_bar,
            zonas_sin_clase_declarada=n_sin_clase,
            clase_kernel=clase_ind,
            zonas_abstenidas_por_ambiguedad_intrabar=0,   # imposible con orden total
            segundos=round(time.time() - t1, 1),
            por_umbral={a: {str(T): dict(c) for T, c in d.items()}
                        for a, d in por.items()},
            por_kind={a: {str(T): dict(c) for T, c in d.items()}
                      for a, d in por_kind.items()},
            alejamiento_en_primera_reentrada=None)
        if alej:
            s = sorted(alej)
            q = lambda p: s[min(len(s) - 1, int(p * len(s)))]
            res[nombre]["alejamiento_en_primera_reentrada"] = dict(
                n=len(s), p10=q(.10), p25=q(.25), p50=q(.50), p75=q(.75),
                p90=q(.90), max=s[-1])
        if verbose:
            print("   %-18s %6d zonas  sin_tramo=%d  (%.0fs)"
                  % (nombre, len(zonas), n_sin_tramo, time.time() - t1), flush=True)
        # checkpoint DESPUES de cada (contrato, indicador): es el grano mas fino
        if on_unidad is not None:
            on_unidad(nombre, res[nombre])
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--indicadores", nargs="*", default=None)
    ap.add_argument("--limite-sesiones", type=int, default=None)
    ap.add_argument("--workers", type=int, default=1,
                    help="DEFAULT 1. La equivalencia 1 vs 2 esta DEMOSTRADA "
                         "exacta (2 contratos, subset fijo), asi que --workers 2 "
                         "es seguro. El default sigue en 1 por tres razones: el "
                         "speedup medido fue 1,16x y venia del DESBALANCE entre "
                         "contratos (60 vs 10 sesiones), no del CPU; los dos "
                         "kernels que dominan la corrida real quedaron fuera de "
                         "esa medicion; y el grano de checkpoint es mas fino en "
                         "secuencial.")
    ap.add_argument("--out", default=str(SALIDA))
    ap.add_argument("--checkpoint", default=str(CHECKPOINT))
    ap.add_argument("--fresh", action="store_true",
                    help="descarta el checkpoint. NO borra: lo ignora y lo pisa "
                         "al terminar la primera unidad.")
    a = ap.parse_args(argv)

    dias, info = dias_research()
    piloto = a.limite_sesiones is not None
    if piloto:
        dias = dias[:a.limite_sesiones]
    inds = a.indicadores or list(REGISTRY)
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])

    # FIREWALL, verificado y publicado: ninguna fecha del universo supera el
    # tope. Si alguna lo hiciera, se aborta -no se recorta en silencio-.
    peor = max(d["fecha"] for d in dias)
    if peor > MAX_FECHA:
        raise SystemExit("FIREWALL: el universo trae %s > %s" % (peor, MAX_FECHA))

    print("universo: %d sesiones%s | max fecha %s <= %s | workers=%d"
          % (len(dias), "  [PILOTO]" if piloto else "", peor, MAX_FECHA,
             a.workers), flush=True)

    tareas = [(arch, sorted(f)) for arch, f in sorted(por_arch.items())]
    clave = clave_de_corrida(tareas, inds)
    ckpt = Path(a.checkpoint)
    hecho = {} if a.fresh else leer_checkpoint(ckpt, clave)
    if hecho:
        n_ok = sum(len(v) for v in hecho.values())
        print("checkpoint: %d unidad(es) ya calculadas, se saltean" % n_ok, flush=True)

    acum, crudo = {}, {}
    if a.workers <= 1:
        for arch, f in tareas:
            faltan = [i for i in inds if i not in hecho.get(arch, {})]
            if not faltan:
                print("== %s : [checkpoint completo] ==" % arch, flush=True)
                crudo[arch] = hecho[arch]
                continue
            print("== %s : %d sesiones | %d indicador(es) pendiente(s) =="
                  % (arch, len(f), len(faltan)), flush=True)

            def guardar(nombre, resultado, _a=arch):
                hecho.setdefault(_a, {})[nombre] = resultado
                escribir_checkpoint(ckpt, clave, hecho, tareas, inds)

            r = medir(arch, f, faltan, on_unidad=guardar)
            crudo[arch] = dict(hecho.get(arch, {}))
            crudo[arch].update(r)
    else:
        # CHECKPOINT TAMBIEN EN PARALELO. La v1 llamaba a `medir` sin
        # `on_unidad` y sin consultar `hecho`: el path paralelo ni reanudaba ni
        # checkpointeaba, asi que una corrida larga con N workers no sobrevivia
        # una interrupcion aunque la de 1 worker si. Asimetria silenciosa.
        #
        # Los WORKERS no escriben el checkpoint -serian escrituras concurrentes
        # sobre el mismo archivo-. Escribe el PADRE, serialmente, a medida que
        # llegan los futuros. El grano es (contrato, indicadores pendientes de
        # ese contrato): mas grueso que en secuencial, y se declara.
        from concurrent.futures import ProcessPoolExecutor, as_completed
        pend = [(arch, f, [i for i in inds if i not in hecho.get(arch, {})])
                for arch, f in tareas]
        listos = [(arch, f) for arch, f, faltan in pend if not faltan]
        for arch, _ in listos:
            print("== %s : [checkpoint completo] ==" % arch, flush=True)
            crudo[arch] = hecho[arch]
        pend = [(arch, f, faltan) for arch, f, faltan in pend if faltan]
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            futs = {ex.submit(medir, arch, f, faltan, LEAD_DAYS, False): arch
                    for arch, f, faltan in pend}
            for fu in as_completed(futs):
                arch = futs[fu]
                r = fu.result()
                hecho.setdefault(arch, {}).update(r)
                escribir_checkpoint(ckpt, clave, hecho, tareas, inds)
                crudo[arch] = dict(hecho[arch])
                print("== %s : %d indicador(es) [checkpoint]" % (arch, len(r)),
                      flush=True)

    for arch, r in crudo.items():
        for nombre, d in r.items():
            if d.get("estado") != "OK":
                continue
            ac = acum.setdefault(nombre, dict(zonas=0, kinds={},
                                              zonas_sin_tramo_de_ticks=0,
                                              zonas_sin_created_bar=0,
                                              zonas_sin_clase_declarada=0,
                                              alejamiento_por_contrato={},
                                              por_umbral={}, por_kind={}))
            ac["zonas"] += d["zonas"]
            ac["zonas_sin_tramo_de_ticks"] += d["zonas_sin_tramo_de_ticks"]
            ac["zonas_sin_created_bar"] += d["zonas_sin_created_bar"]
            ac["zonas_sin_clase_declarada"] += d["zonas_sin_clase_declarada"]
            ac["clase_kernel"] = d.get("clase_kernel")
            # los cuantiles NO se pisan entre contratos: se guardan por contrato.
            # Sobrescribirlos publicaba los del ultimo contrato como si fueran
            # los del universo.
            ac["alejamiento_por_contrato"][arch] = d["alejamiento_en_primera_reentrada"]
            # NO se publica un cuantil global: fusionar cuantiles ya calculados
            # promediandolos daria un numero que no es el cuantil de nada. Se
            # publica por contrato y se declara que no hay global.
            ac["alejamiento_global"] = None
            ac["nota_alejamiento"] = (
                "NO hay cuantil global. Los cuantiles no se promedian: fusionar "
                "p50 de cuatro contratos no da el p50 del universo. Se publica "
                "`alejamiento_por_contrato` y punto.")
            for k, v in d["kinds"].items():
                ac["kinds"][k] = ac["kinds"].get(k, 0) + v
            for campo in ("por_umbral", "por_kind"):
                for arq, dd in d[campo].items():
                    for T, c in dd.items():
                        ac[campo].setdefault(arq, {}).setdefault(T, {}).update(c)

    ns = len(dias)
    for arq in ("retorno", "ruptura_arriba", "ruptura_abajo"):
        print("\n%s -- senales/sesion por umbral de alejamiento previo (ticks)" % arq.upper())
        print("%-18s %s" % ("indicador", "".join("%8s" % T for T in T_DESIGN)))
        for nombre, r in sorted(acum.items()):
            d = r["por_umbral"].get(arq, {})
            print("%-18s %s" % (nombre, "".join(
                "%8.2f" % (sum(d.get(str(T), {}).values()) / ns) for T in T_DESIGN)))
    print("\nDESCARTES  (un descarte no reportado es un numero que nadie puede reconstruir)")
    print("  %-18s %-12s %8s %16s %10s %12s"
          % ("indicador", "clase", "zonas", "sin_created_bar", "sin_tramo", "sin_clase"))
    for nombre, r in sorted(acum.items()):
        print("  %-18s %-12s %8d %16d %10d %12d"
              % (nombre, r.get("clase_kernel") or "-", r["zonas"],
                 r["zonas_sin_created_bar"], r["zonas_sin_tramo_de_ticks"],
                 r["zonas_sin_clase_declarada"]))

    payload = dict(
        schema_version="curva_excursion_ticks_v1",
        clave_de_corrida=clave,
        supersede=SUPERSEDE,
        # NOMBRE CORREGIDO (antes `autoritativo`). El campo sólo dice si el
        # universo se recortó con `--limite-sesiones`; NO dice que alguien haya
        # aceptado la curva. Llamarlo `autoritativo` invitaba a leer un booleano
        # de completitud como un sello de adjudicación, que es justo lo que el
        # auditor prohibió. La adjudicación es un acto de una persona y va en un
        # campo aparte que este script NO puede poner en `si`.
        universo_completo=not piloto,
        estado_de_adjudicacion="no_adjudicada",
        workers=a.workers,
        code_commit=git_head(), umbrales=list(T_DESIGN),
        session_count=ns, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_utc_ns=int(corte_del_sello().value),
        firewall_corte_iso=str(corte_del_sello()),
        # GRANO DEL CHECKPOINT, que no es el mismo en los dos caminos y hay que
        # poder leerlo del artefacto, no solo del codigo.
        grano_checkpoint=("secuencial: (contrato, indicador) -- se pierde 1 "
                          "indicador como mucho. paralelo: (contrato, "
                          "indicadores pendientes de ese contrato) -- se puede "
                          "perder el resto de indicadores de ese contrato."),
        # EQUIVALENCIA: el veredicto esta VERIFICADO y es reproducible; las
        # cifras de RSS que se publicaron con el, NO. Ver el acta de procedencia.
        equivalencia_workers=(
            "1 vs 2 EXACTA sobre 2 contratos con trabajo real en ambos, subset "
            "{BigTrap2, VolTicksPOC2, aVolCellPOI2}: por_umbral, por_kind, "
            "descartes y clases identicos. Re-verificado 2026-08-07 desde "
            "artefactos versionados (equivalencia_workers__w1/w2_70s.json): 12 "
            "campos x 6 unidades, con verificar_equivalencia_workers.py."),
        rss_pico=(
            "1925 MiB = 1,88 GiB (1 worker) vs 2734 MiB = 2,67 GiB (2 workers). "
            "Medicion de 70 sesiones preservada en rss_y_equivalencia_70s.log. "
            "Son LOS MISMOS numeros que `equivalencia_workers` publicaba como "
            "'1.925 vs 2.734 MB' -punto de MILES, notacion es-AR-: 1,88 x 1024 "
            "= 1925,1. Lo unico que estaba mal era la NOMENCLATURA: el "
            "instrumento divide por 2**30, asi que son unidades binarias (MiB / "
            "GiB), no MB / GB. Se publican las dos representaciones para que no "
            "haya que convertir ni adivinar el separador decimal. "
            "Ver docs/SCRATCHPAD_PROVENANCE_AUDIT_2026-08-07.md §3."),
        identidad_de_barras={
            "path": "time:1 / M1 -- build_time_bars(tk, 1)",
            "bar_close": "available_ns = bar_end[created_bar]",
            "tick_create": "available_ns = (created_ms + 1) en ns; NO bar_end[]",
            "por_indicador": dict(CLASE_KERNEL),
            "prohibido": "una sola regla para las dos clases, o mezclar "
                         "created_bar de otra bar_spec con bar_end de M1"},
        universe_filter_report=info,
        ventana="(zona disponible, primera resolucion] -- nada posterior",
        orden="(ts_ns, sequence_de_archivo) -- orden de FILA del F2, determinista y "
              "reproducible. NO es el orden del matching engine ni verdad de mercado.",
        outcomes_accessed=False, curvas=acum, por_contrato=crudo)
    payload["output_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    Path(a.out).write_text(json.dumps(payload, indent=1, ensure_ascii=False),
                           encoding="utf-8")
    print("\n-> %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
