# -*- coding: utf-8 -*-
"""`bar_spec` como eje — repite F0.2 (censo) + F1.1 (nulo local) bajo `tick:25`.

## Por qué esta dimensión, y por qué 25 ticks

`time:1` está **hardcodeado** en siete módulos de research y nunca se justificó
por escrito (`REGISTRO_NO_MEDIDO_2026-08-10.md` §2.1) — es la dimensión más
grande sin explorar de todo el programa, porque BigTrap2 es *bar-driven* +
footprint: cambiar la barra cambia toda la agregación de imbalance y volumen
atrapado, un efecto mayor que cualquier parámetro del indicador (F2 ya mostró
`ticks_per_row`/`imbalance_ratio`/`min_trap_volume` invariantes).

`tick:25` no es un valor arbitrario para probar: `docs/nt8_bridge.md:363`
documenta que **BigTrap2 corre históricamente sobre charts de 5t/25t** en NT8,
y `docs/nt8_indicator_parity_contract.md` registra un oráculo sellado a
`tick:25` (aunque con `ImbalanceMode=SameLevel`, no defaults — ver el caveat
abajo). `time:1` fue la elección de TODO este programa sin que nadie la
comparara contra la resolución con la que el indicador se usa de hecho.

## Caveat de paridad — declarado ANTES de correr, no después de ver números

`build_tick_bars` está testeado y documentado (defecto TICKBAR-001, reinicio
por sesión) y `build_footprints` es agnóstico al tipo de barra —confirmado
leyendo el código: opera sobre `bars.tick_bar_idx`, sin ninguna rama de
`time`—. Pero la combinación específica **"BigTrap2 defaults (Diagonal) +
tick:25"** no tiene oráculo NT8 sellado: sólo están validados "Diagonal @
time:1" y "SameLevel @ tick:25". Este módulo es **evidencia interna Python**,
útil para decidir dónde mirar — si el resultado es interesante, sugiere pedir
un oráculo nuevo de esa combinación exacta, no reemplaza tenerlo.

## Qué hace

Un único paso por contrato produce, sobre `tick:25`:

1. **Censo** (F0.2): zonas creadas, tocadas, `end_reason`, altura, vida.
2. **Nulo local** (F1.1, sólo nulo-B — el que controla distancia): mismo
   diseño, misma semilla, reimplementando `vida_de_zona` que ya es agnóstica al
   tipo de barra (opera sobre índices de barra genéricos).

`outcomes_accessed=False`. Sin retornos, sin P&L, sin tocar el holdout.
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

from diag.tasa_senales.censo_zonas_completo import (  # noqa: E402
    altura_ticks_exacta, resumen, vol_por_zona,
)
from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    LEAD_DAYS, MAX_FECHA, REGISTRY, TZ_CHART, bars_mod, corte_del_sello,
    dias_research, git_head, huella_del_codigo, pd, ticks_mod,
)
from diag.tasa_senales.F1_nulo_zonas_aleatorias import (  # noqa: E402
    VENTANA_LOCAL, sesiones_de_barras, vida_de_zona,
)
from diag.tasa_senales.F1_supervivencia_y_depletion import aalen_johansen  # noqa: E402
from edgelab.bridge.indicators.bigtrap2 import DEFAULTS  # noqa: E402
from edgelab.research.first_touch_census import session_date_ct  # noqa: E402

SCHEMA_VERSION = "F_barspec_tick25_v1"
INDICADOR = "BigTrap2"
TICKS_POR_BARRA = 25
MAX_AGE_BARS = int(DEFAULTS["max_age_bars"])
SEMILLA = 20260810   # misma semilla que F1.1 -- mismo protocolo, otra barra
HORIZONTE = 120


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

    b = bars_mod.build_tick_bars(tk, TICKS_POR_BARRA, reiniciar_por_sesion=True)
    n = len(b)
    bar_end = np.asarray(b.end_ns)
    high_t, low_t, close_t = (np.asarray(b.high_t), np.asarray(b.low_t),
                              np.asarray(b.close_t))
    fp = bars_mod.build_footprints(tk, b)
    mod = REGISTRY[INDICADOR]
    r = mod.run(tk, b, fp, chart_tz=TZ_CHART)

    setf = set(fechas)
    vols = vol_por_zona(r.get("csv_lines") or [])
    _ses_de_barra, rango_sesion = sesiones_de_barras(bar_end, fechas)
    rng = np.random.default_rng([SEMILLA, zlib.crc32(("tick25:" + arch).encode())])

    censo = dict(zonas=0, tocadas=0, razones=Counter(), alturas=[], vidas=[])
    real_filas, nulo_filas = [], []
    real_ps, nulo_ps = {}, {}

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
        razon = z.get("end_reason")

        censo["zonas"] += 1
        censo["tocadas"] += int(tocada)
        censo["razones"][str(razon)] += 1
        censo["alturas"].append(alto)
        fin_ms = z.get("ended_ms")
        if fin_ms is not None:
            bf = int(np.searchsorted(bar_end, int(fin_ms) * 1_000_000, side="left"))
            if bf >= cb:
                censo["vidas"].append(bf - cb)

        rota = razon in ("close_through", "close_through_gap")
        real_filas.append(dict(causa=str(razon), censurado=(razon is None),
                               vida_barras=(bf - cb) if fin_ms is not None and bf >= cb else None,
                               tocada=tocada))
        s = real_ps.setdefault(ses, Counter())
        s["n"] += 1; s["tocadas"] += int(tocada); s["rotas"] += int(rota)

        j0, j1 = rango_sesion[ses]
        lo_h, hi_h = max(j0, cb - VENTANA_LOCAL), min(j1, cb + VENTANA_LOCAL)
        jb = int(rng.integers(lo_h, hi_h + 1))
        centro = int(close_t[jb])
        lo_n = centro - alto // 2
        hi_n = lo_n + alto - 1   # rango INCLUSIVO de `alto` ticks: [lo_n, lo_n+alto-1]
        bar_fin, razon_n, _touches, tocada_n = vida_de_zona(
            lo_n, hi_n, is_bull, cb, high_t, low_t, close_t, n)
        rota_n = razon_n in ("close_through", "close_through_gap")
        nulo_filas.append(dict(causa=str(razon_n), censurado=(razon_n is None),
                               vida_barras=(bar_fin - cb), tocada=tocada_n))
        sn = nulo_ps.setdefault(ses, Counter())
        sn["n"] += 1; sn["tocadas"] += int(tocada_n); sn["rotas"] += int(rota_n)

    return dict(estado="OK", sesiones=len(fechas), n_barras=n,
                censo=censo, real=real_filas, nulo=nulo_filas,
                real_ps={k: dict(v) for k, v in real_ps.items()},
                nulo_ps={k: dict(v) for k, v in nulo_ps.items()})


def diferencia_pareada(a, b):
    dt, dr = [], []
    for ses in sorted(set(a) & set(b)):
        ra, rb = a[ses], b[ses]
        if ra["n"] == 0 or rb["n"] == 0:
            continue
        dt.append(ra["tocadas"] / ra["n"] - rb["tocadas"] / rb["n"])
        dr.append(ra["rotas"] / ra["n"] - rb["rotas"] / rb["n"])
    return dt, dr


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

    print("bar_spec = tick:%d  (BigTrap2 defaults)  -- censo + nulo local" % TICKS_POR_BARRA)
    print("  universo %d sesiones | semilla %d" % (ns, SEMILLA))

    tot_censo = dict(zonas=0, tocadas=0, razones=Counter(), alturas=[], vidas=[])
    real_all, nulo_all = [], []
    real_ps_all, nulo_ps_all = {}, {}
    crudo = {}
    for arch, fechas in plan:
        print("\n== %s : %d sesiones" % (arch, len(fechas)), flush=True)
        res = medir(arch, fechas)
        crudo[arch] = dict(estado=res.get("estado"))
        if res.get("estado") != "OK":
            print("   %s: %s" % (res["estado"], res.get("motivo")))
            continue
        c = res["censo"]
        tot_censo["zonas"] += c["zonas"]; tot_censo["tocadas"] += c["tocadas"]
        tot_censo["razones"].update(c["razones"])
        tot_censo["alturas"].extend(c["alturas"]); tot_censo["vidas"].extend(c["vidas"])
        real_all.extend(res["real"]); nulo_all.extend(res["nulo"])
        real_ps_all.update(res["real_ps"]); nulo_ps_all.update(res["nulo_ps"])
        crudo[arch] = dict(estado="OK", n_barras=res["n_barras"], zonas=c["zonas"])
        print("   barras=%d  zonas=%d  tocadas=%.1f%%  altura med=%.1f"
              % (res["n_barras"], c["zonas"], 100 * c["tocadas"] / max(1, c["zonas"]),
                 resumen(c["alturas"])["p50"] if c["alturas"] else float("nan")))

    n = tot_censo["zonas"]
    alt = resumen(tot_censo["alturas"])
    vid = resumen(tot_censo["vidas"])
    print("\n" + "=" * 70)
    print("CENSO bajo tick:%d  (%d zonas, %d sesiones)" % (TICKS_POR_BARRA, n, ns))
    print("  tocadas alguna vez   %.2f%%" % (100 * tot_censo["tocadas"] / n))
    print("  altura (ticks)       mediana %.2f  p90 %.2f" % (alt["p50"], alt["p90"]))
    print("  vida (barras)        mediana %.2f  p90 %.2f" % (vid["p50"], vid["p90"]))
    print("  end_reason           %s" % dict(tot_censo["razones"]))

    tr = sum(1 for f in real_all if f["tocada"]) / len(real_all)
    tn = sum(1 for f in nulo_all if f["tocada"]) / len(nulo_all)
    rr = sum(1 for f in real_all if f["causa"] in ("close_through", "close_through_gap")) / len(real_all)
    rn = sum(1 for f in nulo_all if f["causa"] in ("close_through", "close_through_gap")) / len(nulo_all)
    print("\nNULO LOCAL bajo tick:%d  (n=%d pares)" % (TICKS_POR_BARRA, len(real_all)))
    print("  %-24s %10s %10s" % ("", "REAL", "NULO-B"))
    print("  %-24s %9.2f%% %9.2f%%" % ("tocada alguna vez", 100 * tr, 100 * tn))
    print("  %-24s %9.2f%% %9.2f%%" % ("rota", 100 * rr, 100 * rn))

    dt, dr = diferencia_pareada(real_ps_all, nulo_ps_all)
    dt_a, dr_a = np.asarray(dt), np.asarray(dr)
    print("\n  diferencia PAREADA por sesion, REAL - NULO-B (n=%d sesiones)" % len(dt))
    print("    tocada: media %+.4f  sesiones REAL>NULO %d/%d"
          % (dt_a.mean(), int((dt_a > 0).sum()), len(dt_a)))
    print("    rota:   media %+.4f  sesiones REAL>NULO %d/%d"
          % (dr_a.mean(), int((dr_a > 0).sum()), len(dr_a)))

    obs_r = [f for f in real_all if f["vida_barras"] is not None or f["censurado"]]
    obs_n = [f for f in nulo_all if f["vida_barras"] is not None or f["censurado"]]
    aj_r = aalen_johansen([f["vida_barras"] if f["vida_barras"] is not None else HORIZONTE for f in obs_r],
                          [f["causa"] for f in obs_r], [f["censurado"] for f in obs_r], HORIZONTE)
    aj_n = aalen_johansen([f["vida_barras"] if f["vida_barras"] is not None else HORIZONTE for f in obs_n],
                          [f["causa"] for f in obs_n], [f["censurado"] for f in obs_n], HORIZONTE)

    payload = dict(
        schema_version=SCHEMA_VERSION, fase="bar_spec:tick25",
        que_es="repite F0.2+F1.1(nulo-B) bajo tick:25 en vez de time:1",
        caveat_paridad="build_tick_bars/build_footprints son agnosticos al "
            "tipo de barra (verificado leyendo el codigo), pero 'BigTrap2 "
            "defaults + tick:25' NO tiene oraculo NT8 sellado -- solo Diagonal"
            "@time:1 y SameLevel@tick:25 lo estan. Evidencia interna Python.",
        bar_spec="tick:%d" % TICKS_POR_BARRA, semilla=SEMILLA,
        session_count=ns, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_iso=str(corte_del_sello()),
        universe_filter_report=info, outcomes_accessed=False,
        censo=dict(zonas=n, tocadas_frac=round(tot_censo["tocadas"] / n, 6),
                  altura_ticks=alt, vida_barras=vid,
                  end_reason=dict(tot_censo["razones"])),
        nulo=dict(n_pares=len(real_all),
                 tocada=dict(real=round(tr, 6), nulo_b=round(tn, 6)),
                 rota=dict(real=round(rr, 6), nulo_b=round(rn, 6)),
                 diferencia_pareada_por_sesion=dict(
                     tocada=dict(media=round(float(dt_a.mean()), 6), n_sesiones=len(dt_a),
                                sesiones_real_mayor=int((dt_a > 0).sum())),
                     rota=dict(media=round(float(dr_a.mean()), 6), n_sesiones=len(dr_a),
                              sesiones_real_mayor=int((dr_a > 0).sum())))),
        supervivencia=dict(real=aj_r, nulo_b=aj_n),
        por_contrato=crudo,
        code_commit=git_head(),
        measurement_code_sha256=huella_del_codigo([INDICADOR]),
        entorno=dict(python=sys.version.split()[0], plataforma=platform.platform()))
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        .encode()).hexdigest()
    salida = Path(a.out) if a.out else (
        Path(__file__).resolve().parent
        / ("F_barspec_tick25__%s.json" % payload["payload_sha256"][:12]))
    salida.write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str)
                      + "\n", encoding="utf-8")
    print("\n-> %s" % salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
