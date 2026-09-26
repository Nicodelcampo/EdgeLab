# -*- coding: utf-8 -*-
"""F3 — generalización a ES. Repite F0.2 (censo) + F1.1 (nulo-B, el corregido)
sobre el mismo calendario de 201 sesiones de 6E, mapeado a contratos ES.

Justificación de población, condición de refutación y por qué reutilizar el
calendario de 6E es correcto (no un atajo): ver
`docs/JUSTIFICACION_POBLACION_GENERALIZACION_ES_2026-08-10.md`.

## El mapeo fecha → contrato, y su verificación

`dias_research()` agrupa las 201 fechas por archivo de contrato 6E
(`6E_03-26_ticks.parquet`, …). ES cotiza los mismos contratos trimestrales
(mismo sufijo de mes/año, convención CME), así que el archivo ES equivalente
es una sustitución directa del prefijo. **Esa sustitución se verifica, no se
asume**: para cada grupo, se carga el parquet ES y se confirma que TODAS las
fechas del grupo caen dentro de su rango de timestamps. Si una fecha queda
fuera, el módulo aborta — no omite la fecha en silencio.

Sin retornos, sin P&L. `outcomes_accessed=False`.
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
from diag.tasa_senales.F1_supervivencia_y_depletion import aalen_johansen  # noqa: E402
from edgelab.bridge.indicators.bigtrap2 import DEFAULTS  # noqa: E402
from edgelab.research.first_touch_census import session_date_ct  # noqa: E402

SCHEMA_VERSION = "F3_generalizacion_ES_v1"
INDICADOR = "BigTrap2"
INSTRUMENTO = "ES"
SEMILLA = 20260810
HORIZONTE = 120
MAX_AGE_BARS = int(DEFAULTS["max_age_bars"])


def verificar_cobertura(arch_es, fechas):
    """Falla fuerte si alguna fecha del grupo 6E no cae en el rango real del
    parquet ES sustituido -- la sustitución de nombre se verifica, no se asume."""
    ruta = REPO_PATH / "data" / "nt8" / f"{INSTRUMENTO}_parquet" / arch_es
    if not ruta.exists():
        raise SystemExit("cobertura ES: no existe %s" % ruta)
    tk = ticks_mod.load_canonical_parquet(str(ruta))
    ini = pd.Timestamp(int(tk.ts_ns.min()), unit="ns", tz="UTC")
    fin = pd.Timestamp(int(tk.ts_ns.max()), unit="ns", tz="UTC")
    fuera = [f for f in fechas
             if not (ini.strftime("%Y-%m-%d") <= f <= fin.strftime("%Y-%m-%d"))]
    if fuera:
        raise SystemExit("cobertura ES: %s no cubre %d fecha(s) del grupo 6E: %s"
                         % (arch_es, len(fuera), fuera[:5]))
    return True


def medir(arch_es, fechas):
    ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
           - pd.Timedelta(days=LEAD_DAYS))
    fin_contrato = (pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago")
                    + pd.Timedelta(days=1))
    fin = min(fin_contrato.tz_convert("UTC"), corte_del_sello())
    tk = ticks_mod.load_canonical_parquet(
        str(REPO_PATH / "data" / "nt8" / f"{INSTRUMENTO}_parquet" / arch_es),
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
    vols = vol_por_zona(r.get("csv_lines") or [])
    _ses, rango_sesion = sesiones_de_barras(bar_end, fechas)
    rng = np.random.default_rng([SEMILLA, zlib.crc32(("ES:" + arch_es).encode())])

    censo = dict(zonas=0, tocadas=0)
    filas_real, filas_nulo = [], []
    ps_real, ps_nulo = {}, {}

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

        censo["zonas"] += 1
        censo["tocadas"] += int(tocada)

        fin_ms = z.get("ended_ms")
        vida = None
        if fin_ms is not None:
            bf = int(np.searchsorted(bar_end, int(fin_ms) * 1_000_000, side="left"))
            if bf >= cb:
                vida = bf - cb
        filas_real.append(dict(causa=str(razon), censurado=(razon is None),
                               vida_barras=vida, tocada=tocada))
        s = ps_real.setdefault(ses, dict(n=0, tocadas=0, rotas=0))
        s["n"] += 1; s["tocadas"] += int(tocada); s["rotas"] += int(rota)

        j0, j1 = rango_sesion[ses]
        lo_h, hi_h = max(j0, cb - VENTANA_LOCAL), min(j1, cb + VENTANA_LOCAL)
        jb = int(rng.integers(lo_h, hi_h + 1))
        centro = int(close_t[jb])
        lo_n = centro - alto // 2
        hi_n = lo_n + alto - 1
        bar_fin, razon_n, _tc, tocada_n = vida_de_zona(
            lo_n, hi_n, is_bull, cb, high_t, low_t, close_t, n)
        rota_n = razon_n in ("close_through", "close_through_gap")
        filas_nulo.append(dict(causa=str(razon_n), censurado=(razon_n is None),
                               vida_barras=(bar_fin - cb), tocada=tocada_n))
        sn = ps_nulo.setdefault(ses, dict(n=0, tocadas=0, rotas=0))
        sn["n"] += 1; sn["tocadas"] += int(tocada_n); sn["rotas"] += int(rota_n)

    return dict(estado="OK", sesiones=len(fechas), n_barras=n, censo=censo,
                real=filas_real, nulo=filas_nulo, ps_real=ps_real, ps_nulo=ps_nulo)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != (REPO_PATH / ".venv").resolve():
        print("NO ES EL .venv DEL REPO -- no se ejecuta.")
        return 2

    dias, info = dias_research()
    por_arch_6e = {}
    for d in dias:
        por_arch_6e.setdefault(d["archivo"], []).append(d["fecha"])
    plan = [(arch_6e.replace("6E_", "%s_" % INSTRUMENTO), sorted(f))
            for arch_6e, f in sorted(por_arch_6e.items())]
    peor = max(f for _x, fs in plan for f in fs)
    assert peor <= MAX_FECHA, "FIREWALL: %s > %s" % (peor, MAX_FECHA)
    ns = sum(len(fs) for _x, fs in plan)

    print("F3  GENERALIZACION A %s -- censo + nulo-B, mismo calendario de 6E" % INSTRUMENTO)
    print("  verificando cobertura real (no asumida) del mapeo de contrato...")
    for arch_es, fechas in plan:
        verificar_cobertura(arch_es, fechas)
        print("  OK  %-24s cubre %d fechas" % (arch_es, len(fechas)))
    print("  universo %d sesiones | semilla %d" % (ns, SEMILLA))

    censo_tot = dict(zonas=0, tocadas=0)
    real_all, nulo_all = [], []
    ps_real_all, ps_nulo_all = {}, {}
    crudo = {}
    for arch_es, fechas in plan:
        print("\n== %s : %d sesiones" % (arch_es, len(fechas)), flush=True)
        res = medir(arch_es, fechas)
        crudo[arch_es] = dict(estado=res.get("estado"))
        if res.get("estado") != "OK":
            print("   %s: %s" % (res["estado"], res.get("motivo")))
            continue
        censo_tot["zonas"] += res["censo"]["zonas"]
        censo_tot["tocadas"] += res["censo"]["tocadas"]
        real_all.extend(res["real"]); nulo_all.extend(res["nulo"])
        ps_real_all.update(res["ps_real"]); ps_nulo_all.update(res["ps_nulo"])
        crudo[arch_es] = dict(estado="OK", n_barras=res["n_barras"], zonas=res["censo"]["zonas"])
        print("   barras=%d  zonas=%d  tocadas=%.1f%%"
              % (res["n_barras"], res["censo"]["zonas"],
                 100 * res["censo"]["tocadas"] / max(1, res["censo"]["zonas"])))

    n = censo_tot["zonas"]
    print("\n" + "=" * 70)
    print("CENSO %s  (%d zonas, %d sesiones)" % (INSTRUMENTO, n, ns))
    print("  tocadas alguna vez   %.2f%%" % (100 * censo_tot["tocadas"] / n))

    tr = sum(1 for f in real_all if f["tocada"]) / len(real_all)
    tn = sum(1 for f in nulo_all if f["tocada"]) / len(nulo_all)
    rr = sum(1 for f in real_all if f["causa"] in ("close_through", "close_through_gap")) / len(real_all)
    rn = sum(1 for f in nulo_all if f["causa"] in ("close_through", "close_through_gap")) / len(nulo_all)
    print("\nNULO-B  %s  (n=%d pares)" % (INSTRUMENTO, len(real_all)))
    print("  %-24s %10s %10s" % ("", "REAL", "NULO-B"))
    print("  %-24s %9.2f%% %9.2f%%" % ("tocada alguna vez", 100 * tr, 100 * tn))
    print("  %-24s %9.2f%% %9.2f%%" % ("rota", 100 * rr, 100 * rn))

    dt, dr = [], []
    for ses in sorted(set(ps_real_all) & set(ps_nulo_all)):
        rr_ = ps_real_all[ses]; nn_ = ps_nulo_all[ses]
        if rr_["n"] == 0 or nn_["n"] == 0:
            continue
        dt.append(rr_["tocadas"] / rr_["n"] - nn_["tocadas"] / nn_["n"])
        dr.append(rr_["rotas"] / rr_["n"] - nn_["rotas"] / nn_["n"])
    dt_a, dr_a = np.asarray(dt), np.asarray(dr)
    print("\n  diferencia PAREADA por sesion, REAL - NULO-B (n=%d sesiones)" % len(dt))
    print("    tocada: media %+.4f  sesiones REAL>NULO %d/%d"
          % (dt_a.mean(), int((dt_a > 0).sum()), len(dt_a)))
    print("    rota:   media %+.4f  sesiones REAL>NULO %d/%d"
          % (dr_a.mean(), int((dr_a > 0).sum()), len(dr_a)))

    obs_r = [f for f in real_all if f["vida_barras"] is not None or f["censurado"]]
    aj_r = aalen_johansen([f["vida_barras"] if f["vida_barras"] is not None else HORIZONTE for f in obs_r],
                          [f["causa"] for f in obs_r], [f["censurado"] for f in obs_r], HORIZONTE)

    condicion = "GENERALIZA" if (dt_a.mean() >= 0.23) else "NO GENERALIZA (brecha < mitad de 6E)"
    print("\n  CONDICION DE REFUTACION declarada en JUSTIFICACION_POBLACION_*: %s" % condicion)

    payload = dict(
        schema_version=SCHEMA_VERSION, fase="F3_ES", instrumento=INSTRUMENTO,
        que_es="censo + nulo-B replicados sobre ES, mismo calendario que 6E",
        justificacion="docs/JUSTIFICACION_POBLACION_GENERALIZACION_ES_2026-08-10.md",
        semilla=SEMILLA, session_count=ns, max_fecha_universo=peor,
        firewall_max_fecha=MAX_FECHA, firewall_corte_iso=str(corte_del_sello()),
        universe_filter_report=info, outcomes_accessed=False,
        censo=dict(zonas=n, tocadas_frac=round(censo_tot["tocadas"] / n, 6)),
        nulo=dict(n_pares=len(real_all),
                 tocada=dict(real=round(tr, 6), nulo_b=round(tn, 6)),
                 rota=dict(real=round(rr, 6), nulo_b=round(rn, 6)),
                 diferencia_pareada_por_sesion=dict(
                     tocada=dict(media=round(float(dt_a.mean()), 6), n_sesiones=len(dt_a),
                                sesiones_real_mayor=int((dt_a > 0).sum())),
                     rota=dict(media=round(float(dr_a.mean()), 6), n_sesiones=len(dr_a),
                              sesiones_real_mayor=int((dr_a > 0).sum())))),
        condicion_refutacion_evaluada=condicion,
        supervivencia_real=aj_r,
        por_contrato=crudo,
        code_commit=git_head(),
        measurement_code_sha256=huella_del_codigo([INDICADOR]),
        entorno=dict(python=sys.version.split()[0], plataforma=platform.platform()))
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        .encode()).hexdigest()
    salida = Path(a.out) if a.out else (
        Path(__file__).resolve().parent
        / ("F3_generalizacion_ES__%s.json" % payload["payload_sha256"][:12]))
    salida.write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str)
                      + "\n", encoding="utf-8")
    print("\n-> %s" % salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
