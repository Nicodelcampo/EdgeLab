# -*- coding: utf-8 -*-
"""F1.1 — nulo contra zonas aleatorias. **El gate de muerte de la familia.**

## La pregunta que ninguna otra fase contesta

Todo lo medido hasta acá (F0.2, F1.2, F1.3, F2) describe **cómo se comporta una
zona de BigTrap2**: vive una mediana de 6 barras, rompe el 96,3 % de las veces,
invariante a altura/volumen/selectividad. Ninguna de esas mediciones responde la
pregunta anterior y más básica: **¿ese comportamiento es del indicador, o es lo
que le pasa a cualquier nivel horizontal puesto en este mercado?**

Si una zona puesta AL AZAR se comporta igual, BigTrap2 no aporta nada por
encima de "una línea horizontal en un mercado que se mueve", y ningún barrido de
parámetros posterior lo puede arreglar — es el diseño de
`arXiv 2101.07410` (*Evidence and Behaviour of Support and Resistance Levels*),
generalizado de niveles a zonas.

## Diseño: apareado por zona, no muestra independiente — DOS nulos, no uno

Por cada zona real se generan **dos** zonas nulas que preservan **sesión y
barra de creación** (`created_bar`), **altura** (`hi - lo` en ticks) y **lado**
(`is_bull`, derivado de `kind` — misma regla de invalidación `close > hi` vs
`close < lo`). Difieren en cómo se sortea el precio central:

**Nulo A — posición NO controlada.** Barra `j` uniforme dentro de la MISMA
sesión; centro = `close_t[j]`. Es la versión ingenua, y **tiene un confusor
conocido de antemano**: una zona real nace en el precio del instante de
creación casi por definición (se construye desde el volumen atrapado EN ese
precio), así que empieza cerca de donde el precio ya está. El nulo A puede caer
en cualquier punto del rango del día, sistemáticamente más lejos. Una diferencia
en tasa de toque entre real y nulo-A puede ser, sin más, «estar cerca de precio
importa» — algo trivial, no evidencia de que el indicador aporte información.

**Nulo B — desplazamiento temporal LOCAL.** Barra `j = created_bar + h`, `h`
sorteado uniforme en `[-VENTANA_LOCAL, +VENTANA_LOCAL]` recortado a los límites
de la sesión; centro = `close_t[j]`. Usa un precio real y cercano en el tiempo,
pero **desacoplado del evento de imbalance específico**. Es el nulo que
contesta la pregunta que importa: dado que va a estar cerca del precio, ¿el
NIVEL que BigTrap2 elige (por imbalance) se comporta distinto de un nivel
igual de cercano elegido sin mirar el imbalance?

Se publican los dos, sin promediarlos, y se reporta la distancia real
(precio de creación vs. centro del nulo) de cada uno como diagnóstico de que el
nulo B efectivamente queda "local" y no es una forma encubierta del nulo A.

El apareamiento por sesión convierte la comparación en un diseño pareado: la
unidad de análisis para cualquier lectura agregada es la **sesión**, igual que
en H1, y por la misma razón (evitar pseudo-réplica dentro del día).

## Cómo se resuelve la vida de la zona nula

La MISMA regla que el kernel, reimplementada sobre los mismos arrays de barras
(`high_t`, `low_t`, `close_t`) que el kernel ya usa — no una aproximación:

    tocada[b]   = high_t[b] >= lo_t  Y  low_t[b] <= hi_t
    adversa[b]  = close_t[b] > hi_t  (is_bull)  O  close_t[b] < lo_t  (~is_bull)
    razon       = "max_age"            si b - created_bar > max_age_bars
                  "close_through"      si adversa Y tocada
                  "close_through_gap"  si adversa Y NO tocada
                  (sigue activa, censurada al final de los datos)

`max_age_bars=2000` (default del kernel) acota la búsqueda. Se vectoriza con
`numpy` por zona: no son 15.947 loops de Python por barra, son 15.947 slices.

## Qué NO hace

No lee un precio para juzgar un desenlace económico — la vida de una zona
nula es geometría vs. precio, no P&L. No es un test de hipótesis con decisión
sellada (VIVE/MUERE): es un diagnóstico descriptivo, target-free, que informa si
corresponde seguir invirtiendo en esta familia. `outcomes_accessed=False`.

Uso:
    ./.venv/Scripts/python.exe diag/tasa_senales/F1_nulo_zonas_aleatorias.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import zlib
from collections import Counter
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    BAR_DRIVEN, LEAD_DAYS, MAX_FECHA, REGISTRY, TZ_CHART, bars_mod,
    corte_del_sello, dias_research, git_head, huella_del_codigo, pd, ticks_mod,
)
from diag.tasa_senales.censo_zonas_completo import resumen  # noqa: E402
from diag.tasa_senales.F1_supervivencia_y_depletion import aalen_johansen  # noqa: E402
from edgelab.bridge.indicators.bigtrap2 import DEFAULTS  # noqa: E402
from edgelab.research.first_touch_census import session_date_ct  # noqa: E402

SCHEMA_VERSION = "F1_nulo_zonas_aleatorias_v1"
INDICADOR = "BigTrap2"
MAX_AGE_BARS = int(DEFAULTS["max_age_bars"])
#: Semilla fija y publicada -- el sorteo de la barra nula es reproducible.
SEMILLA = 20260810
HORIZONTE = 120
#: Ventana del nulo B: +/- 180 barras (3h a time:1) alrededor de la creacion,
#: recortada a la sesion. Bastante para desacoplar del evento puntual de
#: imbalance, bastante chica para seguir siendo "local" en precio.
VENTANA_LOCAL = 180


def sesiones_de_barras(bar_end_ns, fechas):
    """Sesion CT de cada barra, y el rango [ini,fin] de barra de cada sesion.

    Una sola pasada de `session_date_ct` por barra (vectorizable via pandas: el
    corte horario es fijo, no depende del precio) y despues se agrupa.
    """
    ses = np.array([session_date_ct(int(t) // 1_000_000) for t in bar_end_ns],
                   dtype=object)
    rango = {}
    idx = np.arange(len(ses))
    for f in fechas:
        m = idx[ses == f]
        if len(m):
            rango[f] = (int(m[0]), int(m[-1]))
    return ses, rango


def vida_de_zona(lo_t, hi_t, is_bull, created_bar, high_t, low_t, close_t, n):
    """Replica la regla de invalidacion del kernel sobre un rango de barras.
    Devuelve (bar_fin, razon, touches, tocada_alguna_vez)."""
    b0 = created_bar + 1
    b1 = min(created_bar + MAX_AGE_BARS, n - 1)
    if b0 > b1:
        return created_bar, None, 0, False
    h, lo_, c = high_t[b0:b1 + 1], low_t[b0:b1 + 1], close_t[b0:b1 + 1]
    tocada = (h >= lo_t) & (lo_ <= hi_t)
    adversa = (c > hi_t) if is_bull else (c < lo_t)
    invalid = adversa | (np.arange(b0, b1 + 1) - created_bar > MAX_AGE_BARS)
    if not invalid.any():
        touches = int(tocada.sum())
        return b1, None, touches, bool(tocada.any())
    k = int(np.argmax(invalid))
    bar_fin = b0 + k
    touches = int(tocada[:k + 1].sum())
    if (bar_fin - created_bar) > MAX_AGE_BARS:
        razon = "max_age"
    else:
        razon = "close_through" if tocada[k] else "close_through_gap"
    return bar_fin, razon, touches, bool(tocada[:k + 1].any())


def medir(arch, fechas):
    ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
           - pd.Timedelta(days=LEAD_DAYS))
    fin_contrato = (pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago")
                    + pd.Timedelta(days=1))
    fin = min(fin_contrato.tz_convert("UTC"), corte_del_sello())
    tk = ticks_mod.load_canonical_parquet(
        str(REPO_PATH / "data" / "nt8" / "6E" / arch),
        start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))
    if not bool((np.diff(np.asarray(tk.sequence)) > 0).all()):
        return dict(estado="ABSTAIN", motivo="`sequence` no es orden total")

    b = bars_mod.build_time_bars(tk, 1)
    n = len(b)
    bar_end = np.asarray(b.end_ns)
    high_t, low_t, close_t = (np.asarray(b.high_t), np.asarray(b.low_t),
                              np.asarray(b.close_t))
    fp = bars_mod.build_footprints(tk, b) if INDICADOR in BAR_DRIVEN else None
    mod = REGISTRY[INDICADOR]
    r = mod.run(tk, b, fp, chart_tz=TZ_CHART) if fp is not None \
        else mod.run(tk, b, chart_tz=TZ_CHART)

    setf = set(fechas)
    ses_de_barra, rango_sesion = sesiones_de_barras(bar_end, fechas)

    # semilla determinista y distinta por archivo -- reproducible, no compartida
    # entre contratos (evitaria correlacionar sorteos de contratos distintos).
    # NO usar hash() built-in: esta salteado por proceso (PYTHONHASHSEED) desde
    # Python 3.3 y rompe la reproducibilidad entre corridas.
    rng = np.random.default_rng([SEMILLA, zlib.crc32(arch.encode("utf-8"))])

    por_sesion = {"real": {}, "nulo_a": {}, "nulo_b": {}}
    filas = {"real": [], "nulo_a": [], "nulo_b": []}
    distancias_b = []

    for z in r.get("zones") or []:
        if z.get("top") is None or z.get("created_ms") is None:
            continue
        ses = session_date_ct(int(z["created_ms"]))
        if ses not in setf or ses not in rango_sesion:
            continue
        cb = int(z["created_bar"])
        if not (0 <= cb < n):
            continue
        lo_t = int(round(float(z["bottom"]) / tk.tick_size))
        hi_t = int(round(float(z["top"]) / tk.tick_size))
        alto = hi_t - lo_t
        is_bull = (z.get("kind") == "trapped_buyers")
        j0, j1 = rango_sesion[ses]

        # --- real: la vida ya la escribio el kernel (end_reason/ended_ms) ---
        fin_ms = z.get("ended_ms")
        vida_real = None
        if fin_ms is not None:
            bf = int(np.searchsorted(bar_end, int(fin_ms) * 1_000_000, side="left"))
            if bf >= cb:
                vida_real = bf - cb
        real = dict(causa=str(z.get("end_reason")),
                    censurado=(z.get("end_reason") is None),
                    vida_barras=vida_real, tocada=int(z.get("touches") or 0) > 0)
        filas["real"].append(real)
        s = por_sesion["real"].setdefault(ses, Counter())
        s["n"] += 1
        s["tocadas"] += int(real["tocada"])
        s["rotas"] += int(real["causa"] in ("close_through", "close_through_gap"))

        # --- nulo A: posicion NO controlada, uniforme en toda la sesion ---
        ja = int(rng.integers(j0, j1 + 1))
        _acumular_nulo(filas["nulo_a"], por_sesion["nulo_a"], ses,
                       int(close_t[ja]), alto, is_bull, cb,
                       high_t, low_t, close_t, n)

        # --- nulo B: desplazamiento LOCAL, +/- VENTANA_LOCAL recortado a sesion
        lo_h, hi_h = max(j0, cb - VENTANA_LOCAL), min(j1, cb + VENTANA_LOCAL)
        jb = int(rng.integers(lo_h, hi_h + 1))
        distancias_b.append(abs(int(close_t[jb]) - int(close_t[cb])))
        _acumular_nulo(filas["nulo_b"], por_sesion["nulo_b"], ses,
                       int(close_t[jb]), alto, is_bull, cb,
                       high_t, low_t, close_t, n)

    return dict(estado="OK", sesiones=len(fechas), filas=filas,
                por_sesion={k: {s: dict(c) for s, c in v.items()}
                           for k, v in por_sesion.items()},
                distancias_nulo_b_ticks=distancias_b)


def _acumular_nulo(filas_out, sesion_out, ses, centro, alto, is_bull, cb,
                   high_t, low_t, close_t, n):
    lo_n = centro - alto // 2
    hi_n = lo_n + alto
    bar_fin, razon, touches, tocada = vida_de_zona(
        lo_n, hi_n, is_bull, cb, high_t, low_t, close_t, n)
    fila = dict(causa=str(razon), censurado=(razon is None),
               vida_barras=(bar_fin - cb), tocada=tocada)
    filas_out.append(fila)
    s = sesion_out.setdefault(ses, Counter())
    s["n"] += 1
    s["tocadas"] += int(tocada)
    s["rotas"] += int(razon in ("close_through", "close_through_gap"))


def diferencia_pareada_por_sesion(reales, otras):
    """Para cada sesion, tasa REAL - tasa DE LA OTRA SERIE. Unidad de analisis
    = sesion, igual que H1 -- evita pseudo-replica dentro del dia."""
    diffs_tocadas, diffs_rotas = [], []
    for ses in sorted(set(reales) & set(otras)):
        r, nl = reales[ses], otras[ses]
        if r["n"] == 0 or nl["n"] == 0:
            continue
        diffs_tocadas.append(r["tocadas"] / r["n"] - nl["tocadas"] / nl["n"])
        diffs_rotas.append(r["rotas"] / r["n"] - nl["rotas"] / nl["n"])
    return diffs_tocadas, diffs_rotas


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != (REPO_PATH / ".venv").resolve():
        print("NO ES EL .venv DEL REPO -- no se ejecuta.")
        return 2

    dias, info = dias_research()
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])
    plan = [(x, sorted(f)) for x, f in sorted(por_arch.items())]
    peor = max(f for _x, fs in plan for f in fs)
    assert peor <= MAX_FECHA, "FIREWALL: %s > %s" % (peor, MAX_FECHA)
    ns = sum(len(fs) for _x, fs in plan)

    print("F1.1  NULO CONTRA ZONAS ALEATORIAS -- gate de muerte de la familia")
    print("  universo %d sesiones | semilla %d | max_age_bars %d | ventana local %d barras"
          % (ns, SEMILLA, MAX_AGE_BARS, VENTANA_LOCAL))

    filas = {"real": [], "nulo_a": [], "nulo_b": []}
    por_sesion = {"real": {}, "nulo_a": {}, "nulo_b": {}}
    distancias_b = []
    crudo = {}
    for arch, fechas in plan:
        print("\n== %s : %d sesiones" % (arch, len(fechas)), flush=True)
        res = medir(arch, fechas)
        if res.get("estado") != "OK":
            crudo[arch] = res
            print("   %s: %s" % (res["estado"], res.get("motivo")))
            continue
        for k in filas:
            filas[k].extend(res["filas"][k])
            por_sesion[k].update(res["por_sesion"][k])
        distancias_b.extend(res["distancias_nulo_b_ticks"])
        crudo[arch] = dict(estado="OK", sesiones=res["sesiones"], zonas=len(res["filas"]["real"]))
        tr = sum(1 for f in res["filas"]["real"] if f["tocada"]) / max(1, len(res["filas"]["real"]))
        ta = sum(1 for f in res["filas"]["nulo_a"] if f["tocada"]) / max(1, len(res["filas"]["nulo_a"]))
        tb = sum(1 for f in res["filas"]["nulo_b"] if f["tocada"]) / max(1, len(res["filas"]["nulo_b"]))
        print("   zonas=%d   tocada REAL=%.1f%%  NULO-A=%.1f%%  NULO-B=%.1f%%"
              % (len(res["filas"]["real"]), 100 * tr, 100 * ta, 100 * tb))

    d = resumen(distancias_b)
    print("\n  diagnostico nulo B -- distancia |centro_nulo - precio_en_creacion|, ticks")
    print("    mediana %.1f   p90 %.1f   media %.2f   (n=%d)" % (d["p50"], d["p90"], d["media"], d["n"]))

    n_r = len(filas["real"])
    resultados = {}
    print("\n" + "=" * 70)
    print("COMPARACION GLOBAL  (n=%d pares)" % n_r)
    print("  %-24s %10s %10s %10s" % ("", "REAL", "NULO-A", "NULO-B"))
    for etiqueta, cond in (
            ("tocada alguna vez", lambda f: f["tocada"]),
            ("rota (close_through*)", lambda f: f["causa"] in ("close_through", "close_through_gap")),
            ("expira sin romper", lambda f: f["causa"] == "max_age")):
        vals = {k: sum(1 for f in filas[k] if cond(f)) / len(filas[k]) for k in filas}
        resultados[etiqueta] = vals
        print("  %-24s %9.1f%% %9.1f%% %9.1f%%" % (etiqueta, 100 * vals["real"],
                                                    100 * vals["nulo_a"], 100 * vals["nulo_b"]))

    vida = {k: resumen([f["vida_barras"] for f in filas[k] if f["vida_barras"] is not None])
           for k in filas}
    print("\n  vida en barras (mediana / media / p90)")
    for k in ("real", "nulo_a", "nulo_b"):
        v = vida[k]
        print("    %-8s %6.1f / %6.2f / %6.1f" % (k, v["p50"], v["media"], v["p90"]))

    aj = {}
    for k in filas:
        obs = [f for f in filas[k] if f["vida_barras"] is not None or f["censurado"]]
        aj[k] = aalen_johansen(
            [f["vida_barras"] if f["vida_barras"] is not None else HORIZONTE for f in obs],
            [f["causa"] for f in obs], [f["censurado"] for f in obs], HORIZONTE)

    print("\n  supervivencia (fraccion viva a las N barras)")
    print("  %-9s %10s %10s %10s" % ("barras", "REAL", "NULO-A", "NULO-B"))
    for t in (1, 2, 5, 10, 20, 60, 120):
        fila = []
        for k in ("real", "nulo_a", "nulo_b"):
            s = aj[k]["supervivencia"].get(t)
            if s is None:
                ks = [kk for kk in aj[k]["supervivencia"] if kk <= t]
                s = aj[k]["supervivencia"][max(ks)] if ks else 1.0
            fila.append(s)
        print("  %-9d %10.4f %10.4f %10.4f" % (t, *fila))

    dif = {}
    for k in ("nulo_a", "nulo_b"):
        dt, dr = diferencia_pareada_por_sesion(por_sesion["real"], por_sesion[k])
        dt_a, dr_a = np.asarray(dt), np.asarray(dr)
        dif[k] = dict(
            tocada=dict(media=round(float(dt_a.mean()), 6), mediana=round(float(np.median(dt_a)), 6),
                       n_sesiones=len(dt_a), sesiones_real_mayor=int((dt_a > 0).sum())),
            rota=dict(media=round(float(dr_a.mean()), 6), mediana=round(float(np.median(dr_a)), 6),
                     n_sesiones=len(dr_a), sesiones_real_mayor=int((dr_a > 0).sum())))
        print("\n  diferencia PAREADA por sesion, REAL - %s (n=%d sesiones)" % (k.upper(), len(dt)))
        print("    tocada:  media %+.4f  mediana %+.4f  sesiones REAL>otro %d/%d"
              % (dt_a.mean(), np.median(dt_a), int((dt_a > 0).sum()), len(dt_a)))
        print("    rota:    media %+.4f  mediana %+.4f  sesiones REAL>otro %d/%d"
              % (dr_a.mean(), np.median(dr_a), int((dr_a > 0).sum()), len(dr_a)))

    print("\n  NOTA: diagnostico descriptivo target-free, sin decision sellada")
    print("  VIVE/MUERE -- eso es privativo del protocolo de outcomes (H1 y afines).")
    print("  NULO-A tiene confusor de distancia conocido: leer NULO-B como el de referencia.")

    payload = dict(
        schema_version=SCHEMA_VERSION, fase="F1.1",
        que_es="nulo contra zonas aleatorias -- gate de muerte de la familia. "
               "Diagnostico descriptivo target-free, NO es una decision sellada.",
        plan="docs/PLAN_ANALISIS_v2_2026-08-10.md",
        diseno=dict(
            nulo_a="posicion NO controlada: barra uniforme en toda la sesion. "
                  "CONFUSOR CONOCIDO: sistematicamente mas lejos del precio de "
                  "creacion que una zona real, que nace en el precio del instante.",
            nulo_b="desplazamiento LOCAL: barra = creacion +/- %d, recortada a "
                   "la sesion. Controla el confusor de distancia; es el de "
                   "referencia." % VENTANA_LOCAL),
        semilla=SEMILLA, max_age_bars=MAX_AGE_BARS, horizonte_barras=HORIZONTE,
        ventana_local_barras=VENTANA_LOCAL,
        session_count=ns, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_iso=str(corte_del_sello()),
        universe_filter_report=info, outcomes_accessed=False,
        n_pares=n_r,
        distancia_nulo_b_ticks=d,
        tasas=resultados, vida_barras=vida,
        supervivencia={k: aj[k] for k in aj},
        diferencia_pareada_por_sesion=dif,
        por_contrato=crudo,
        code_commit=git_head(),
        measurement_code_sha256=huella_del_codigo([INDICADOR]),
        entorno=dict(python=sys.version.split()[0], plataforma=platform.platform()))
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        .encode()).hexdigest()
    salida = Path(a.out) if a.out else (
        Path(__file__).resolve().parent
        / ("F1_nulo_zonas_aleatorias__%s.json" % payload["payload_sha256"][:12]))
    salida.write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str)
                      + "\n", encoding="utf-8")
    print("\n-> %s" % salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
