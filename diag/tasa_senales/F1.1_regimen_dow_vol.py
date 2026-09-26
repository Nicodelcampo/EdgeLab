# -*- coding: utf-8 -*-
"""F1.1 x régimen — la brecha de atracción (real vs nulo-B) cruzada con día de
semana y volatilidad de sesión.

## Por qué esto

`REGISTRO_NO_MEDIDO_2026-08-10.md` §3.5 deja abierto: F0.3 midió estacionalidad
intradía (pico 11-13h CT) pero "nada de eso se cruzó todavía con ruptura ni con
toque. Sin condicionamiento por volatilidad, tendencia ni día de la semana." Es
la tarea #6 registrada. Misma técnica que F1.2 (estratificar una métrica
target-free ya establecida por una covariable descriptiva — ahí volumen/altura/
toques, acá régimen) y que `F1.1_grilla_parametros.py` (misma pregunta, otro
eje: parámetros del indicador en vez de régimen del mercado). No es F4: no se
pregunta si la distribución de RETORNOS cambia con el estado — eso sigue bajo
STOP —, se pregunta si la brecha de TOQUE (ya establecida, target-free, F1.1)
se sostiene pareja a través del régimen o está concentrada en un subconjunto.

## Qué NO es esto

`E1/E4/E5 como hipótesis por derecho propio` es F5.3 (monetización, bajo STOP,
`PLAN_ANALISIS_v2` §3 línea 235-237) — correctamente excluido de este módulo.
Este módulo no toca P&L, no propone entradas nuevas, no lee un retorno: re-corre
exactamente el protocolo nulo-B de `F1_nulo_zonas_aleatorias.py` (misma
semilla, misma ventana local, misma regla `vida_de_zona`) sobre subconjuntos de
sesiones agrupados por régimen. `outcomes_accessed=False`.

## Dos ejes, cada uno con su propia partición — no se cruzan entre sí

1. **Día de semana** (lunes..viernes) — de la fecha de sesión.
2. **Volatilidad de sesión** — rango REALIZADO de toda la sesión
   (`max(high) - min(low)` en ticks), terciles sobre las 201 sesiones.
   **Caveat declarado:** es un rango ex-post de la sesión completa (incluye
   barras posteriores a la creación de cualquier zona dentro de ese día) — sirve
   para preguntar «¿la brecha depende del régimen?», no para proponer un filtro
   pre-computable en vivo. Cruzar los dos ejes entre sí (día × volatilidad, 15
   celdas) diluiría la potencia muy por debajo de lo útil con sólo 201 sesiones
   — se publican por separado, no cruzados.

## MDE

Misma fórmula y los mismos dos lentes que `F1.1_grilla_parametros.py` (SE de la
diferencia pareada por sesión dentro de cada estrato; `z=1,96` descriptivo,
`z=3,50` el multiplicador de multiplicidad que E-R1 dejó establecido, aplicado
por consistencia). Con ~40 sesiones por día de semana o ~67 por tercil de
volatilidad, el MDE de cada celda es varias veces el de la comparación global
(n=201) — se publica explícito para que un nulo dentro de una celda no se lea
como «no hay efecto en este régimen» sin mirar cuánto podía detectar la celda.

## Procedencia dirty-aware

Además de `code_commit`, publica si el árbol estaba limpio ANTES y DESPUÉS de
correr (regla `CLAUDE.md`, post-incidente de procedencia 2026-08-10).

Uso:
    ./.venv/Scripts/python.exe diag/tasa_senales/F1.1_regimen_dow_vol.py
    ./.venv/Scripts/python.exe diag/tasa_senales/F1.1_regimen_dow_vol.py --archivos 6E_09-25_ticks.parquet   # smoke test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import zlib
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.censo_zonas_completo import (  # noqa: E402
    altura_ticks_exacta,
)
from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    BAR_DRIVEN, LEAD_DAYS, MAX_FECHA, REGISTRY, TZ_CHART, bars_mod,
    corte_del_sello, dias_research, git_head, huella_del_codigo, pd, ticks_mod,
)
from diag.tasa_senales.F1_nulo_zonas_aleatorias import (  # noqa: E402
    VENTANA_LOCAL, sesiones_de_barras, vida_de_zona,
)
from edgelab.bridge.indicators.bigtrap2 import DEFAULTS  # noqa: E402
from edgelab.research.first_touch_census import session_date_ct  # noqa: E402

SCHEMA_VERSION = "F1.1_regimen_dow_vol_v1"
INDICADOR = "BigTrap2"
MAX_AGE_BARS = int(DEFAULTS["max_age_bars"])
SEMILLA = 20260810
Z_DESCRIPTIVO = 1.96
Z_MULTIPLICIDAD = 3.50   # el mismo multiplicador que E-R1 establecio, por consistencia

DIAS_SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def git_dirty():
    out = subprocess.check_output(
        ["git", "-C", str(REPO_PATH), "status", "--porcelain"], text=True)
    return bool(out.strip())


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
    _ses, rango_sesion = sesiones_de_barras(bar_end, fechas)
    rng = np.random.default_rng([SEMILLA, zlib.crc32(arch.encode("utf-8"))])

    # regimen por sesion: dia de semana + rango realizado (ticks), de la
    # sesion COMPLETA -- ver caveat en el docstring del modulo.
    regimen = {}
    for f, (j0, j1) in rango_sesion.items():
        rango_ticks = int(high_t[j0:j1 + 1].max() - low_t[j0:j1 + 1].min())
        regimen[f] = dict(dow=DIAS_SEMANA[pd.Timestamp(f).weekday()],
                          rango_ticks=rango_ticks)

    ps_real, ps_nulo = {}, {}
    zonas = 0
    for z in r.get("zones") or []:
        if z.get("top") is None or z.get("created_ms") is None:
            continue
        ses = session_date_ct(int(z["created_ms"]))
        if ses not in setf or ses not in rango_sesion:
            continue
        cb = int(z["created_bar"])
        if not (0 <= cb < n):
            continue
        alto = int(altura_ticks_exacta(float(z["top"]), float(z["bottom"]), tk.tick_size))
        is_bull = (z.get("kind") == "trapped_buyers")
        tocada = int(z.get("touches") or 0) > 0
        zonas += 1

        s = ps_real.setdefault(ses, dict(n=0, tocadas=0))
        s["n"] += 1
        s["tocadas"] += int(tocada)

        j0, j1 = rango_sesion[ses]
        lo_h, hi_h = max(j0, cb - VENTANA_LOCAL), min(j1, cb + VENTANA_LOCAL)
        jb = int(rng.integers(lo_h, hi_h + 1))
        centro = int(close_t[jb])
        lo_n = centro - alto // 2
        hi_n = lo_n + alto - 1
        _bf, _rz, _tc, tocada_n = vida_de_zona(
            lo_n, hi_n, is_bull, cb, high_t, low_t, close_t, n)
        sn = ps_nulo.setdefault(ses, dict(n=0, tocadas=0))
        sn["n"] += 1
        sn["tocadas"] += int(tocada_n)

    return dict(estado="OK", zonas=zonas, ps_real=ps_real, ps_nulo=ps_nulo,
                regimen=regimen)


def celda_stats(ps_real, ps_nulo, sesiones):
    """Paired-by-session real-vs-nulo, mismo criterio de unidad de analisis
    que F1_nulo_zonas_aleatorias.py. `tr`/`tn` son PROMEDIO de tasas por
    sesion (no pool de zonas) para que `tr - tn == dt.mean()` exacto."""
    validas = [s for s in sesiones
              if s in ps_real and s in ps_nulo
              and ps_real[s]["n"] > 0 and ps_nulo[s]["n"] > 0]
    if len(validas) < 2:
        return dict(n_sesiones=len(validas), abstain="menos de 2 sesiones")
    tasas_r = np.array([ps_real[s]["tocadas"] / ps_real[s]["n"] for s in validas])
    tasas_n = np.array([ps_nulo[s]["tocadas"] / ps_nulo[s]["n"] for s in validas])
    dt = tasas_r - tasas_n
    se = float(dt.std(ddof=1) / np.sqrt(len(dt)))
    return dict(
        n_sesiones=len(validas),
        tocada_real_media_sesion=round(float(tasas_r.mean()), 6),
        tocada_nulo_media_sesion=round(float(tasas_n.mean()), 6),
        brecha_pareada_media=round(float(dt.mean()), 6),
        brecha_pareada_mediana=round(float(np.median(dt)), 6),
        sesiones_real_mayor=int((dt > 0).sum()),
        se_pareado=round(se, 6),
        mde_z196=round(Z_DESCRIPTIVO * se, 6),
        mde_z350=round(Z_MULTIPLICIDAD * se, 6))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=None)
    ap.add_argument("--archivos", default=None,
                    help="subconjunto separado por comas, para smoke test "
                         "(ej. 6E_09-25_ticks.parquet). Default: universo completo.")
    a = ap.parse_args(argv)

    if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != (REPO_PATH / ".venv").resolve():
        print("NO ES EL .venv DEL REPO -- no se ejecuta.")
        return 2

    dirty_start = git_dirty()
    head_start = git_head()

    dias, info = dias_research()
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])
    plan = [(x, sorted(f)) for x, f in sorted(por_arch.items())]
    if a.archivos:
        quiere = set(s.strip() for s in a.archivos.split(","))
        plan = [(x, f) for x, f in plan if x in quiere]
        if not plan:
            print("FILTRO --archivos no matchea ningun archivo del universo.")
            return 2
    peor = max(f for _x, fs in plan for f in fs)
    if not a.archivos:
        assert peor <= MAX_FECHA, "FIREWALL: %s > %s" % (peor, MAX_FECHA)
    ns = sum(len(fs) for _x, fs in plan)

    print("F1.1 x REGIMEN -- brecha de atraccion por dia de semana y volatilidad de sesion")
    print("  universo %d sesiones | semilla %d | ventana local %d barras%s"
          % (ns, SEMILLA, VENTANA_LOCAL, "  [SMOKE TEST: %s]" % a.archivos if a.archivos else ""))

    ps_real_all, ps_nulo_all, regimen_all = {}, {}, {}
    crudo = {}
    for arch, fechas in plan:
        res = medir(arch, fechas)
        crudo[arch] = dict(estado=res.get("estado"))
        if res.get("estado") != "OK":
            print("   %s: %s -- %s" % (arch, res["estado"], res.get("motivo")))
            continue
        ps_real_all.update(res["ps_real"])
        ps_nulo_all.update(res["ps_nulo"])
        regimen_all.update(res["regimen"])
        crudo[arch] = dict(estado="OK", zonas=res["zonas"])
        print("   %-24s zonas=%5d sesiones=%d" % (arch, res["zonas"], len(res["ps_real"])))

    todas = sorted(regimen_all)
    global_stats = celda_stats(ps_real_all, ps_nulo_all, todas)
    print("\n" + "=" * 70)
    print("GLOBAL (ancla -- deberia aprox. matchear el F1.1 ya publicado)")
    print("  n_sesiones=%d  brecha=%+.4f  MDE(3.50)=%.4f"
          % (global_stats.get("n_sesiones", 0), global_stats.get("brecha_pareada_media", float("nan")),
             global_stats.get("mde_z350", float("nan"))))

    print("\n-- DIA DE SEMANA --")
    por_dow = {}
    for dow in DIAS_SEMANA:
        ses_dow = [s for s in todas if regimen_all[s]["dow"] == dow]
        if not ses_dow:
            continue
        st = celda_stats(ps_real_all, ps_nulo_all, ses_dow)
        por_dow[dow] = st
        if "abstain" in st:
            print("  %-10s ABSTAIN: %s (n=%d)" % (dow, st["abstain"], st["n_sesiones"]))
        else:
            print("  %-10s n=%3d brecha=%+.4f (%d/%d real>nulo) MDE(3.50)=%.4f"
                  % (dow, st["n_sesiones"], st["brecha_pareada_media"],
                     st["sesiones_real_mayor"], st["n_sesiones"], st["mde_z350"]))

    rangos = np.array([regimen_all[s]["rango_ticks"] for s in todas], dtype=float)
    por_vol = {}
    if len(rangos) >= 3:
        t1, t2 = np.percentile(rangos, [100 / 3, 200 / 3])
        tercil_de = {s: ("bajo" if regimen_all[s]["rango_ticks"] <= t1
                         else ("medio" if regimen_all[s]["rango_ticks"] <= t2 else "alto"))
                    for s in todas}
        print("\n-- VOLATILIDAD DE SESION (rango realizado, terciles) --")
        print("  cortes: tercil1<=%.0f ticks  tercil2<=%.0f ticks  (min=%.0f max=%.0f)"
              % (t1, t2, rangos.min(), rangos.max()))
        for tercil in ("bajo", "medio", "alto"):
            ses_t = [s for s in todas if tercil_de[s] == tercil]
            st = celda_stats(ps_real_all, ps_nulo_all, ses_t)
            por_vol[tercil] = st
            if "abstain" in st:
                print("  %-6s ABSTAIN: %s (n=%d)" % (tercil, st["abstain"], st["n_sesiones"]))
            else:
                print("  %-6s n=%3d brecha=%+.4f (%d/%d real>nulo) MDE(3.50)=%.4f"
                      % (tercil, st["n_sesiones"], st["brecha_pareada_media"],
                         st["sesiones_real_mayor"], st["n_sesiones"], st["mde_z350"]))
    else:
        t1 = t2 = float("nan")
        print("\n-- VOLATILIDAD DE SESION -- muy pocas sesiones para terciles (smoke test) --")

    dirty_end = git_dirty()
    head_end = git_head()
    if dirty_start or dirty_end:
        print("\n  AVISO procedencia: arbol no estaba limpio (dirty_start=%s dirty_end=%s) -- "
              "code_commit no garantiza que ese commit sea exactamente lo que corrio."
              % (dirty_start, dirty_end))

    payload = dict(
        schema_version=SCHEMA_VERSION, fase="F1.1_regimen_dow_vol",
        que_es="brecha de atraccion (real vs nulo-B, F1.1) estratificada por "
               "dia de semana y por volatilidad de sesion (terciles de rango "
               "realizado). Mismo protocolo nulo-B, misma semilla, misma "
               "ventana local que F1_nulo_zonas_aleatorias.py. No es F4 "
               "(no mide retornos); no es F5.3 (no propone entrada).",
        plan="docs/REGISTRO_NO_MEDIDO_2026-08-10.md #3.5",
        outcomes_accessed=False, smoke_test=bool(a.archivos),
        semilla=SEMILLA, max_age_bars=MAX_AGE_BARS, ventana_local_barras=VENTANA_LOCAL,
        session_count=ns, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_iso=str(corte_del_sello()),
        universe_filter_report=info,
        global_ancla=global_stats,
        por_dia_semana=por_dow,
        por_volatilidad=dict(
            cortes_ticks=dict(tercil1=round(float(t1), 2) if rangos.size else None,
                              tercil2=round(float(t2), 2) if rangos.size else None),
            rango_ticks_minmax=([float(rangos.min()), float(rangos.max())]
                                if rangos.size else None),
            celdas=por_vol),
        por_contrato=crudo,
        code_commit=head_start, head_start=head_start, head_end=head_end,
        dirty_start=dirty_start, dirty_end=dirty_end,
        measurement_code_sha256=huella_del_codigo([INDICADOR]),
        entorno=dict(python=sys.version.split()[0], plataforma=platform.platform()))
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        .encode()).hexdigest()
    salida = Path(a.out) if a.out else (
        Path(__file__).resolve().parent
        / ("F1.1_regimen_dow_vol__%s.json" % payload["payload_sha256"][:12]))
    salida.write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str)
                      + "\n", encoding="utf-8")
    print("\n-> %s" % salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
