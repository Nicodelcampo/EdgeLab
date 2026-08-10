# -*- coding: utf-8 -*-
"""F0.2 — censo COMPLETO de zonas. **El denominador que faltó todo el programa.**

## El agujero que cierra

Se midieron **15.577 primeros toques** sobre 201 sesiones. Nunca se contó
**cuántas zonas nacen**. Es decir: todo el corpus de evidencia sobre BigTrap2
—censo, curva de excursión, sello E-R1, H1 y su acta de muerte— se construyó
sobre **un numerador sin denominador**.

Si resulta que la mayoría de las zonas no se toca nunca, la población de H1 era
una minoría no representativa del objeto que el indicador produce, y eso cambia
qué se puede concluir de su muerte. Ver
`docs/SESGO_DE_DISENO_2026-08-10_EL_TOQUE_COMO_UNICA_ENTRADA.md`.

## Qué mide, y qué NO

**Mide, sólo con salidas del kernel:** zonas creadas, cuántas se tocan alguna
vez, cuántas mueren sin ser tocadas, el histograma de `touches`, el `end_reason`
de **todas** las zonas —no sólo las tocadas—, la geometría (altura en ticks,
volumen atrapado) y la vida en barras.

**NO mide un solo outcome.** No lee un precio posterior a ningún evento para
evaluar un desenlace económico. `outcomes_accessed=False`, y lo dice como HECHO:
la bandera se deriva de que este módulo no tiene ninguna ruta que lea P&L.

> El kernel consume ticks para construir las zonas —eso es el indicador
> computándose a sí mismo, target-free por `docs/kernel_contract.md`—. Distinto
> de leer precios *después* de un evento para juzgarlo, que es lo que INC-002
> definió como outcome.

## Construido para el barrido desde el primer día

El costo dominante es cargar ticks, construir barras y footprints: **eso se hace
UNA vez por contrato** y después se corren N celdas de parámetros sobre los
mismos datos. Los footprints son independientes de los parámetros —`ticks_per_row`
se aplica adentro de `process_bar`, no en `build_footprints`—, así que reusarlos
es correcto y no una optimización riesgosa.

Con eso, F2 (el barrido de fuerza bruta target-free) es este mismo módulo con
otra lista de celdas. No hay que escribir un segundo camino que después divirja
del primero — que es exactamente cómo nació el sesgo que este módulo repara.

Uso:
    ./.venv/Scripts/python.exe diag/tasa_senales/censo_zonas_completo.py
    ./.venv/Scripts/python.exe diag/tasa_senales/censo_zonas_completo.py --celdas grilla.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    BAR_DRIVEN, CLASE_KERNEL, LEAD_DAYS, MAX_FECHA, REGISTRY, TZ_CHART,
    bars_mod, corte_del_sello, dias_research, git_head, huella_del_codigo, pd,
    ticks_mod,
)
from edgelab.bridge.indicators.bigtrap2 import DEFAULTS  # noqa: E402
from edgelab.research.first_touch_census import session_date_ct  # noqa: E402

SCHEMA_VERSION = "censo_zonas_completo_v1"
INDICADOR = "BigTrap2"

#: Percentiles que se publican de cada distribución. Fijos y declarados: elegir
#: percentiles después de ver la forma es elegir el resultado.
PCTS = (10, 25, 50, 75, 90)


def resumen(xs):
    """Resumen distribucional de una lista numérica. `None` si está vacía."""
    if not len(xs):
        return None
    a = np.asarray(xs, dtype=np.float64)
    d = dict(n=int(a.size), media=round(float(a.mean()), 4),
             sd=round(float(a.std(ddof=0)), 4),
             min=round(float(a.min()), 4), max=round(float(a.max()), 4))
    for q in PCTS:
        d["p%d" % q] = round(float(np.percentile(a, q)), 4)
    return d


def altura_ticks_exacta(top, bottom, tick_size):
    """Altura de zona en ticks enteros, SIN ruido de redondeo.

    ## El defecto que esto corrige (encontrado 2026-08-10, DESPUÉS de haber
    ## publicado F0.2/F1.2/F2/F0.3 con la fórmula ingenua)

    `round(top/tick_size) - round(bottom/tick_size)` parece razonable pero
    `bigtrap2.py:202-203` construye la geometría con relleno de MEDIO tick:

        zone_lo = lo_tick * tick_size - tick_size / 2.0
        zone_hi = hi_tick * tick_size + tick_size / 2.0

    Para una zona de una sola fila (`lo_tick == hi_tick == T`), eso da
    `top/tick_size = T + 0.5` y `bottom/tick_size = T - 0.5` — **exactamente**
    en el límite de redondeo. `round()` de Python usa banker's rounding
    (redondea al par más cercano), así que el resultado depende de la paridad
    de `T` **y** del error de punto flotante al representar `T ± 0.5` en la
    escala de `tick_size` (verificado empíricamente: da 0, 1 **o** 2 para una
    altura que es SIEMPRE exactamente 1 tick por construcción).

    `store.py::_core()` ya conocía este problema y lo evita midiendo en
    unidades de MEDIO-tick, donde `zone_lo`/`zone_hi` caen siempre en un
    entero exacto, sin redondeo:

        ht = tick_size / 2
        lo_ht = round(zone_lo / ht)   # exacto, no hay .5 que resolver
        hi_ht = round(zone_hi / ht)
        altura_ticks = (hi_ht - lo_ht) / 2

    Esta función replica exactamente esa técnica. Usarla en vez de la resta de
    `round()` directos siempre que la altura se use para CONSTRUIR geometría
    (no sólo para reportarla) — es el caso de los nulos de F1.1 y afines.
    """
    ht = tick_size / 2.0
    lo_ht = round(bottom / ht)
    hi_ht = round(top / ht)
    return (hi_ht - lo_ht) / 2.0


def vol_por_zona(csv_lines):
    """`vol` (volumen atrapado) por `zone_id`, parseado de las líneas ZONE_CREATED.

    El kernel NO promueve `vol` al dict de zona emitido (`bigtrap2.py:309-313`
    proyecta id/top/bottom/created_*/ended_ms/state/kind/touches/end_reason y
    descarta el resto), pero sí lo emite en el payload del evento. Se lee de ahí
    en vez de tocar el kernel, que está bajo contrato de paridad NT8.
    """
    out = {}
    for ln in csv_lines:
        partes = ln.split("|", 3)
        if len(partes) < 4 or partes[2] != "ZONE_CREATED":
            continue
        campos = dict(kv.split("=", 1) for kv in partes[3].split(";") if "=" in kv)
        zid, v = campos.get("zone_id"), campos.get("vol")
        if zid is None or v is None:
            continue
        try:
            out[zid] = float(v)
        except ValueError:
            pass
    return out


def censar(r, tick_size, bar_end, fechas):
    """Censo target-free de UNA corrida del kernel. No lee un solo precio."""
    setf = set(fechas)
    vols = vol_por_zona(r.get("csv_lines") or [])

    n_warmup = n_sin_geo = 0
    alturas, volumenes, vidas_barras, toques = [], [], [], []
    razones, estados, lados = Counter(), Counter(), Counter()
    por_sesion = Counter()
    tocadas = nunca_tocadas = 0
    muertas_sin_toque = Counter()      # end_reason de las que nunca se tocaron

    for z in r.get("zones") or []:
        if z.get("top") is None or z.get("created_ms") is None:
            n_sin_geo += 1
            continue
        ses = session_date_ct(int(z["created_ms"]))
        if ses not in setf:
            n_warmup += 1              # nacio en el lead-in, fuera del calendario
            continue

        por_sesion[ses] += 1
        t = int(z.get("touches") or 0)
        toques.append(t)
        estados[str(z.get("state"))] += 1
        lados[str(z.get("kind"))] += 1
        razones[str(z.get("end_reason"))] += 1
        alturas.append((float(z["top"]) - float(z["bottom"])) / tick_size)
        if z["id"] in vols:
            volumenes.append(vols[z["id"]])

        if t > 0:
            tocadas += 1
        else:
            nunca_tocadas += 1
            muertas_sin_toque[str(z.get("end_reason"))] += 1

        cb = z.get("created_bar")
        fin_ms = z.get("ended_ms")
        if cb is not None and fin_ms is not None and 0 <= int(cb) < len(bar_end):
            bf = int(np.searchsorted(bar_end, int(fin_ms) * 1_000_000, side="left"))
            if bf >= int(cb):
                vidas_barras.append(bf - int(cb))

    n = len(toques)
    return dict(
        estado="OK",
        sesiones=len(fechas),
        zonas_creadas=n,
        zonas_tocadas_alguna_vez=tocadas,
        zonas_nunca_tocadas=nunca_tocadas,
        frac_nunca_tocadas=(round(nunca_tocadas / n, 4) if n else None),
        zonas_por_sesion=(round(n / len(fechas), 3) if fechas else None),
        end_reason_todas=dict(razones),
        end_reason_de_las_nunca_tocadas=dict(muertas_sin_toque),
        estado_final=dict(estados),
        lado=dict(lados),
        toques=resumen(toques),
        histograma_toques=dict(Counter(toques)),
        altura_ticks=resumen(alturas),
        volumen_atrapado=resumen(volumenes),
        vida_barras=resumen(vidas_barras),
        zonas_de_warmup_excluidas=n_warmup,
        zonas_sin_geometria=n_sin_geo)


def acumular(dst, src):
    """Suma un censo de contrato al acumulado global. Las distribuciones no se
    promedian: se recomponen del crudo en `main`."""
    for k in ("zonas_creadas", "zonas_tocadas_alguna_vez", "zonas_nunca_tocadas",
              "zonas_de_warmup_excluidas", "zonas_sin_geometria", "sesiones"):
        dst[k] = dst.get(k, 0) + src[k]
    for k in ("end_reason_todas", "end_reason_de_las_nunca_tocadas",
              "estado_final", "lado", "histograma_toques"):
        c = Counter(dst.get(k) or {})
        c.update(src[k])
        dst[k] = dict(c)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--celdas", default=None,
                    help="JSON con [{nombre, params}] para barrer. Sin esto "
                         "corre UNA celda: los defaults (la celda de H1).")
    ap.add_argument("--contrato", default=None, help="limitar a un archivo")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != (REPO_PATH / ".venv").resolve():
        print("NO ES EL .venv DEL REPO -- no se ejecuta.")
        return 2

    if a.celdas:
        celdas = json.loads(Path(a.celdas).read_text(encoding="utf-8"))
    else:
        celdas = [dict(nombre="defaults", params={})]
    for c in celdas:
        desconocidos = sorted(set(c.get("params") or {}) - set(DEFAULTS))
        if desconocidos:
            print("celda %r declara params que el kernel no tiene: %s"
                  % (c.get("nombre"), desconocidos))
            return 2

    dias, info = dias_research()
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])
    plan = [(arch, sorted(f)) for arch, f in sorted(por_arch.items())
            if a.contrato is None or arch == a.contrato]
    if not plan:
        print("plan vacio")
        return 2
    peor = max(f for _x, fs in plan for f in fs)
    assert peor <= MAX_FECHA, "FIREWALL: %s > %s" % (peor, MAX_FECHA)
    ns = sum(len(fs) for _x, fs in plan)

    print("F0.2 CENSO COMPLETO DE ZONAS -- el denominador que faltaba")
    print("  universo   %d sesiones | max %s <= %s" % (ns, peor, MAX_FECHA))
    print("  indicador  %s | celdas %d | corte %s"
          % (INDICADOR, len(celdas), corte_del_sello()))

    crudo = {c["nombre"]: {} for c in celdas}
    for arch, fechas in plan:
        print("\n== %s : %d sesiones -- cargando ticks" % (arch, len(fechas)),
              flush=True)
        ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
               - pd.Timedelta(days=LEAD_DAYS))
        fin_contrato = (pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago")
                        + pd.Timedelta(days=1))
        fin = min(fin_contrato.tz_convert("UTC"), corte_del_sello())
        tk = ticks_mod.load_canonical_parquet(
            str(REPO_PATH / "data" / "nt8" / "6E" / arch),
            start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))
        sq = np.asarray(tk.sequence)
        if not bool((np.diff(sq) > 0).all()):
            for c in celdas:
                crudo[c["nombre"]][arch] = dict(
                    estado="ABSTAIN", motivo="`sequence` no es orden total")
            continue

        # UNA sola vez por contrato: barras y footprints no dependen de params.
        b = bars_mod.build_time_bars(tk, 1)
        bar_end = np.asarray(b.end_ns)
        fp = bars_mod.build_footprints(tk, b) if INDICADOR in BAR_DRIVEN else None
        mod = REGISTRY[INDICADOR]

        for c in celdas:
            r = (mod.run(tk, b, fp, params=c.get("params") or {}, chart_tz=TZ_CHART)
                 if fp is not None
                 else mod.run(tk, b, params=c.get("params") or {}, chart_tz=TZ_CHART))
            res = censar(r, tk.tick_size, bar_end, fechas)
            crudo[c["nombre"]][arch] = res
            print("   %-14s zonas=%5d  tocadas=%5d  NUNCA tocadas=%5d (%.1f%%)"
                  % (c["nombre"], res["zonas_creadas"],
                     res["zonas_tocadas_alguna_vez"], res["zonas_nunca_tocadas"],
                     100 * (res["frac_nunca_tocadas"] or 0)), flush=True)

    totales = {}
    for c in celdas:
        t = {}
        for arch, res in crudo[c["nombre"]].items():
            if res.get("estado") == "OK":
                acumular(t, res)
        n = t.get("zonas_creadas", 0)
        t["frac_nunca_tocadas"] = (round(t.get("zonas_nunca_tocadas", 0) / n, 4)
                                   if n else None)
        t["zonas_por_sesion"] = round(n / ns, 3) if ns else None
        totales[c["nombre"]] = t

        print("\n" + "=" * 66)
        print("CELDA %s" % c["nombre"])
        if c.get("params"):
            print("  params  %s" % json.dumps(c["params"], sort_keys=True))
        print("  zonas creadas            %6d   (%.2f por sesion)"
              % (n, t["zonas_por_sesion"] or 0))
        print("  tocadas alguna vez       %6d   %5.1f%%"
              % (t.get("zonas_tocadas_alguna_vez", 0),
                 100 * (1 - (t["frac_nunca_tocadas"] or 0))))
        print("  NUNCA tocadas            %6d   %5.1f%%"
              % (t.get("zonas_nunca_tocadas", 0),
                 100 * (t["frac_nunca_tocadas"] or 0)))
        print("  end_reason (todas)       %s" % json.dumps(
            t.get("end_reason_todas", {}), sort_keys=True, ensure_ascii=False))
        print("  end_reason (sin tocar)   %s" % json.dumps(
            t.get("end_reason_de_las_nunca_tocadas", {}), sort_keys=True,
            ensure_ascii=False))
        print("  estado final             %s" % json.dumps(
            t.get("estado_final", {}), sort_keys=True, ensure_ascii=False))
        h = t.get("histograma_toques", {})
        top = sorted(((int(k), v) for k, v in h.items()))[:8]
        print("  toques 0,1,2,...         %s" % ", ".join(
            "%s:%d" % (k, v) for k, v in top))

    payload = dict(
        schema_version=SCHEMA_VERSION, fase="F0.2",
        que_es="censo COMPLETO de zonas: el denominador que falto todo el "
               "programa. Se midieron 15.577 primeros toques sin saber nunca "
               "cuantas zonas nacen.",
        plan="docs/PLAN_ANALISIS_v2_2026-08-10.md",
        sesgo="docs/SESGO_DE_DISENO_2026-08-10_EL_TOQUE_COMO_UNICA_ENTRADA.md",
        indicador=INDICADOR, clase_kernel=CLASE_KERNEL.get(INDICADOR),
        celdas=[dict(nombre=c["nombre"], params=c.get("params") or {})
                for c in celdas],
        session_count=ns, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_iso=str(corte_del_sello()),
        universe_filter_report=info,
        # HECHO, no intencion: este modulo no tiene ninguna ruta que lea un
        # precio posterior a un evento para juzgarlo economicamente.
        outcomes_accessed=False,
        percentiles_publicados=list(PCTS),
        totales=totales, por_celda=crudo,
        code_commit=git_head(),
        measurement_code_sha256=huella_del_codigo([INDICADOR]),
        entorno=dict(python=sys.version.split()[0], plataforma=platform.platform()))
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        .encode()).hexdigest()
    salida = Path(a.out) if a.out else (
        Path(__file__).resolve().parent
        / ("censo_zonas_completo__%s.json" % payload["payload_sha256"][:12]))
    salida.write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str)
                      + "\n", encoding="utf-8")
    print("\n-> %s" % salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
