# -*- coding: utf-8 -*-
"""Profundización post-fuerza-bruta — el nulo-B (atracción) cruzado con la
grilla de parámetros de BigTrap2, y el MDE de F1.1 que faltaba publicar.

## Por qué esto y no seguir cortando ruptura

F2 (12 celdas) y el barrido de los 9 parámetros restantes ya mostraron
invariancia total de la tasa de ruptura — 12 de 12 veces. Repetir esa métrica
sobre más celdas no puede decir nada nuevo. Lo que la fuerza bruta NUNCA cruzó
es la métrica que F1.1 mostró que sí discrimina: **atracción** (tocar). Este
módulo corre el nulo-B corregido (mismo protocolo de
`F1_nulo_zonas_aleatorias.py`, semilla igual) sobre cinco celdas elegidas por
lo que cada eje ya demostró mover:

- `defaults` — ancla, mismo código que el resto de la sesión
- `ticks_per_row=4` — la geometría más alta y consistente (F2)
- `imbalance_ratio=2.0` — selección más permisiva, más zonas (F2)
- `min_trap_volume=50.0` — selección más estricta, "más calidad" (F2)
- `imbalance_mode=SameLevel` — una REGLA de selección distinta, no un umbral (F4)

## El MDE que faltaba

`CLAUDE.md` (regla agregada 2026-08-10, de Constitución v3): todo nulo publica
su efecto mínimo detectable. F1.1 nunca lo hizo. Se publica acá para las cinco
celdas, usando la SD de la diferencia pareada por sesión (n=201 bloques) y dos
lentes: `z=1,96` (descriptivo, 95%) y `z=3,50` (el multiplicador de
multiplicidad que E-R1 dejó establecido para este programa, aplicado por
consistencia — esto NO es una decisión sellada, es descriptivo).

## Qué NO hace

Sin retornos, sin P&L. `outcomes_accessed=False`. No es una adjudicación —F1.1
sigue siendo "diagnóstico descriptivo, no decisión sellada"—, es la misma
regla extendida a más celdas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import zlib
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.censo_zonas_completo import (  # noqa: E402
    altura_ticks_exacta, resumen, vol_por_zona,
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

SCHEMA_VERSION = "F1.1_grilla_parametros_v1"
INDICADOR = "BigTrap2"
SEMILLA = 20260810
Z_DESCRIPTIVO = 1.96
Z_MULTIPLICIDAD = 3.50   # el mismo multiplicador que E-R1 establecio, por consistencia

CELDAS = [
    dict(nombre="defaults", params={}),
    dict(nombre="ticks_per_row_4", params={"ticks_per_row": 4}),
    dict(nombre="imbalance_ratio_2.0", params={"imbalance_ratio": 2.0}),
    dict(nombre="min_trap_volume_50", params={"min_trap_volume": 50.0}),
    dict(nombre="imbalance_mode_SameLevel", params={"imbalance_mode": "SameLevel"}),
]


def medir(arch, fechas, params, rng_tag):
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
    r = mod.run(tk, b, fp, params=params, chart_tz=TZ_CHART) if fp is not None \
        else mod.run(tk, b, params=params, chart_tz=TZ_CHART)

    setf = set(fechas)
    _ses, rango_sesion = sesiones_de_barras(bar_end, fechas)
    rng = np.random.default_rng([SEMILLA, zlib.crc32((rng_tag + ":" + arch).encode())])

    filas_real, filas_nulo = [], []
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
        razon = z.get("end_reason")
        rota = razon in ("close_through", "close_through_gap")
        zonas += 1

        filas_real.append(tocada)
        s = ps_real.setdefault(ses, dict(n=0, tocadas=0, rotas=0))
        s["n"] += 1; s["tocadas"] += int(tocada); s["rotas"] += int(rota)

        j0, j1 = rango_sesion[ses]
        lo_h, hi_h = max(j0, cb - VENTANA_LOCAL), min(j1, cb + VENTANA_LOCAL)
        jb = int(rng.integers(lo_h, hi_h + 1))
        centro = int(close_t[jb])
        lo_n = centro - alto // 2
        hi_n = lo_n + alto - 1
        _bf, razon_n, _tc, tocada_n = vida_de_zona(
            lo_n, hi_n, is_bull, cb, high_t, low_t, close_t, n)
        rota_n = razon_n in ("close_through", "close_through_gap")
        filas_nulo.append(tocada_n)
        sn = ps_nulo.setdefault(ses, dict(n=0, tocadas=0, rotas=0))
        sn["n"] += 1; sn["tocadas"] += int(tocada_n); sn["rotas"] += int(rota_n)

    return dict(estado="OK", zonas=zonas, real_tocada=filas_real,
                nulo_tocada=filas_nulo, ps_real=ps_real, ps_nulo=ps_nulo)


def diferencia_pareada(ps_real, ps_nulo):
    dt = []
    for ses in sorted(set(ps_real) & set(ps_nulo)):
        r, nl = ps_real[ses], ps_nulo[ses]
        if r["n"] == 0 or nl["n"] == 0:
            continue
        dt.append(r["tocadas"] / r["n"] - nl["tocadas"] / nl["n"])
    return np.asarray(dt)


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

    print("F1.1 x GRILLA -- atraccion cruzada con parametros que F2/F4 mostraron que mueven algo")
    print("  universo %d sesiones | semilla %d | %d celdas" % (ns, SEMILLA, len(CELDAS)))

    resultados = {}
    for celda in CELDAS:
        nombre, params = celda["nombre"], celda["params"]
        print("\n" + "=" * 70)
        print("CELDA %s  params=%s" % (nombre, params))
        real_all, nulo_all = [], []
        ps_real_all, ps_nulo_all = {}, {}
        zonas_tot = 0
        crudo = {}
        for arch, fechas in plan:
            res = medir(arch, fechas, params, nombre)
            crudo[arch] = dict(estado=res.get("estado"))
            if res.get("estado") != "OK":
                print("   %s: %s -- %s" % (arch, res["estado"], res.get("motivo")))
                continue
            real_all.extend(res["real_tocada"]); nulo_all.extend(res["nulo_tocada"])
            ps_real_all.update(res["ps_real"]); ps_nulo_all.update(res["ps_nulo"])
            zonas_tot += res["zonas"]
            crudo[arch] = dict(estado="OK", zonas=res["zonas"])
            print("   %-24s zonas=%5d" % (arch, res["zonas"]))

        n = len(real_all)
        tr = sum(real_all) / n
        tn = sum(nulo_all) / n
        dt = diferencia_pareada(ps_real_all, ps_nulo_all)
        se = float(dt.std(ddof=1) / np.sqrt(len(dt)))
        mde_desc = Z_DESCRIPTIVO * se
        mde_mult = Z_MULTIPLICIDAD * se

        print("  tocada REAL=%.4f  NULO-B=%.4f  brecha pareada=%.4f (n=%d sesiones, %d/%d REAL>NULO)"
              % (tr, tn, float(dt.mean()), len(dt), int((dt > 0).sum()), len(dt)))
        print("  SE(pareado)=%.4f  MDE(z=1,96)=%.4f  MDE(z=3,50)=%.4f" % (se, mde_desc, mde_mult))

        resultados[nombre] = dict(
            params=params, zonas=zonas_tot, n_pares=n,
            tocada_real=round(tr, 6), tocada_nulo=round(tn, 6),
            brecha_pareada_media=round(float(dt.mean()), 6),
            brecha_pareada_n_sesiones=len(dt),
            sesiones_real_mayor=int((dt > 0).sum()),
            se_pareado=round(se, 6),
            mde_z196=round(mde_desc, 6), mde_z350=round(mde_mult, 6),
            por_contrato=crudo)

    print("\n" + "=" * 70)
    print("RESUMEN -- brecha de atraccion por celda")
    print("  %-28s %9s %9s %9s %9s" % ("celda", "REAL", "NULO-B", "brecha", "MDE(3,50)"))
    for nombre, r in resultados.items():
        print("  %-28s %8.2f%% %8.2f%% %+8.2f%% %8.2f%%"
              % (nombre, 100 * r["tocada_real"], 100 * r["tocada_nulo"],
                 100 * r["brecha_pareada_media"], 100 * r["mde_z350"]))

    payload = dict(
        schema_version=SCHEMA_VERSION, fase="F1.1_grilla_parametros",
        que_es="nulo-B (atraccion) cruzado con 5 celdas de parametros de "
               "BigTrap2 que F2/F4 ya mostraron que mueven algo -- y el MDE "
               "de F1.1 que no se habia publicado",
        celdas=[c["nombre"] for c in CELDAS],
        semilla=SEMILLA, z_descriptivo=Z_DESCRIPTIVO, z_multiplicidad=Z_MULTIPLICIDAD,
        session_count=ns, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_iso=str(corte_del_sello()),
        universe_filter_report=info, outcomes_accessed=False,
        resultados=resultados,
        code_commit=git_head(),
        measurement_code_sha256=huella_del_codigo([INDICADOR]),
        entorno=dict(python=sys.version.split()[0], plataforma=platform.platform()))
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        .encode()).hexdigest()
    salida = Path(a.out) if a.out else (
        Path(__file__).resolve().parent
        / ("F1.1_grilla_parametros__%s.json" % payload["payload_sha256"][:12]))
    salida.write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str)
                      + "\n", encoding="utf-8")
    print("\n-> %s" % salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
