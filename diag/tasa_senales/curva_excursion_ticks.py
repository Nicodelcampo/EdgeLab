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

Pero el esquema F2 trae `sequence`, el **orden estable del archivo fuente**.
Verificado sobre datos reales (6E 03-26, 317.064 ticks):

    sequence estrictamente creciente ..... sí
    duplicados ........................... 0
    crece dentro de los empates de ts_ns .. sí
    mayor grupo de ts_ns empatado ........ 185 ticks

Un tick es un **punto**: está dentro de la banda o afuera. Con orden total no hay
"hizo las dos cosas". **La ambigüedad desaparece por construcción, no por
supuesto** — y el guard sigue: si `sequence` no fuera orden total en la ventana
cargada, la zona ABSTIENE.

## Frontera outcome-free

- Universo: sólo sesiones que entrega la **puerta research**.
- **Máximo `ts_ns` cargado ≤ 2026-06-30**, verificado y publicado. La ventana
  sellada no se lee ni se escanea.
- La entrada empieza en el instante en que la zona está **disponible**
  (`available_ns` = cierre de la barra creadora), no en su timestamp de anclaje.
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

#: FIREWALL: ningún tick posterior a esta fecha entra, ni siquiera a escanearse.
MAX_FECHA = "2026-06-30"

SALIDA = Path(__file__).resolve().parent / "curva_excursion_ticks.json"
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


def medir(archivo, fechas, indicadores, lead=LEAD_DAYS, verbose=True):
    ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
           - pd.Timedelta(days=lead))
    # FIREWALL: el fin de carga se recorta al minimo entre el ultimo dia del
    # contrato y MAX_FECHA. No se escanea un tick del holdout.
    fin_contrato = pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago") + pd.Timedelta(days=1)
    fin_sello = pd.Timestamp(MAX_FECHA + " 23:59:59.999999999", tz="UTC")
    fin = min(fin_contrato.tz_convert("UTC"), fin_sello)

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
        alej, n_sin_tramo, n_sin_campos = [], 0, 0
        for z in zonas:
            if z.get("created_ms") is None or z.get("top") is None:
                n_sin_campos += 1
                continue
            lo_t, hi_t = z["bottom"] / tick_size, z["top"] / tick_size
            c_ns = int(z["created_ms"]) * 1_000_000
            # DISPONIBLE, no anclado: la entrada empieza al CIERRE de la barra
            # creadora. Usar `created_ms` a secas dejaria entrar ticks de la
            # propia barra que creo la zona.
            ib = int(np.searchsorted(bar_end, c_ns, side="left"))
            disp_ns = int(bar_end[ib]) if ib < len(bar_end) else c_ns
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
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--indicadores", nargs="*", default=None)
    ap.add_argument("--limite-sesiones", type=int, default=None)
    ap.add_argument("--workers", type=int, default=1,
                    help="1 = secuencial. La paralelizacion esta IMPLEMENTADA "
                         "pero apagada por defecto: primero hay que demostrar "
                         "equivalencia exacta 1-worker vs N-workers.")
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

    # FIREWALL, verificado y publicado: ninguna fecha del universo supera el
    # tope. Si alguna lo hiciera, se aborta -no se recorta en silencio-.
    peor = max(d["fecha"] for d in dias)
    if peor > MAX_FECHA:
        raise SystemExit("FIREWALL: el universo trae %s > %s" % (peor, MAX_FECHA))

    print("universo: %d sesiones%s | max fecha %s <= %s | workers=%d"
          % (len(dias), "  [PILOTO]" if piloto else "", peor, MAX_FECHA,
             a.workers), flush=True)

    tareas = [(arch, sorted(f)) for arch, f in sorted(por_arch.items())]
    acum, crudo = {}, {}
    if a.workers <= 1:
        for arch, f in tareas:
            print("== %s : %d sesiones ==" % (arch, len(f)), flush=True)
            crudo[arch] = medir(arch, f, inds)
    else:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            futs = {ex.submit(medir, arch, f, inds, LEAD_DAYS, False): arch
                    for arch, f in tareas}
            for fu in futs:
                crudo[futs[fu]] = fu.result()

    for arch, r in crudo.items():
        for nombre, d in r.items():
            if d.get("estado") != "OK":
                continue
            ac = acum.setdefault(nombre, dict(zonas=0, kinds={},
                                              zonas_sin_tramo_de_ticks=0,
                                              por_umbral={}, por_kind={}))
            ac["zonas"] += d["zonas"]
            ac["zonas_sin_tramo_de_ticks"] += d["zonas_sin_tramo_de_ticks"]
            ac["alejamiento_en_primera_reentrada"] = d["alejamiento_en_primera_reentrada"]
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
    print("\nDESCARTES")
    for nombre, r in sorted(acum.items()):
        print("  %-18s zonas=%-7d sin_tramo=%-6d ambiguas=0 (orden total por `sequence`)"
              % (nombre, r["zonas"], r["zonas_sin_tramo_de_ticks"]))

    payload = dict(
        schema_version="curva_excursion_ticks_v1",
        supersede=SUPERSEDE,
        autoritativo=not piloto, workers=a.workers,
        code_commit=git_head(), umbrales=list(T_DESIGN),
        session_count=ns, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        universe_filter_report=info,
        ventana="(zona disponible, primera resolucion] -- nada posterior",
        orden="ts_ns + `sequence` (orden estable del archivo); un tick es un punto",
        outcomes_accessed=False, curvas=acum, por_contrato=crudo)
    payload["output_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    Path(a.out).write_text(json.dumps(payload, indent=1, ensure_ascii=False),
                           encoding="utf-8")
    print("\n-> %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
