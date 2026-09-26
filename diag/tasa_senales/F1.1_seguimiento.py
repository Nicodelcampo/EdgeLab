# -*- coding: utf-8 -*-
"""Los tres seguimientos que F1.1 dejó abiertos — mismo protocolo, mismo `time:1`.

Registrados en `F1.1_NULO_ZONAS_ALEATORIAS_RESULTADO_2026-08-10.md` §7:

**(b) ¿Es distancia pura?** F1.1 mostró tocada real 97,9 % vs nulo-B 51,4 %,
pero nunca ligó la tasa de toque del nulo-B a SU PROPIA distancia realizada.
Acá se estratifica: si aun a distancia chica el nulo sigue perdiendo contra lo
real, no alcanza con "estar cerca".

**(c) ¿Es inmediata o acumulada?** F1.1 midió con horizonte de 2.000 barras
(~33 h). Acá se agrega `tocada` dentro de 20 y 60 barras — la ventana donde una
entrada real podría ejecutarse.

**(d) ¿Es imbalance o nodo de volumen genérico?** Nulo-C: mismo diseño que
nulo-B (desplazamiento local) pero el punto se elige por **volumen de barra más
parecido** al de la barra de creación real, no al azar dentro de la ventana.
Aísla "cerca en el tiempo" de "tan activo como". Simplificación declarada: usa
volumen de la BARRA (turnover), no volumen atrapado al precio exacto — es un
proxy más grueso que el imbalance que BigTrap2 usa, y se dice así.

Sin retornos, sin P&L, `outcomes_accessed=False`.
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

SCHEMA_VERSION = "F1.1_seguimiento_v1"
INDICADOR = "BigTrap2"
MAX_AGE_BARS = int(DEFAULTS["max_age_bars"])
SEMILLA = 20260810
HORIZONTES_CORTOS = (20, 60)
#: cuantiles de distancia realizada del nulo-B, para (b)
CORTES_DISTANCIA = (10, 25, 50, 75, 90)


def tocada_en_horizonte(lo_t, hi_t, created_bar, high_t, low_t, n, k):
    b0, b1 = created_bar + 1, min(created_bar + k, n - 1)
    if b0 > b1:
        return False
    return bool(((high_t[b0:b1 + 1] >= lo_t) & (low_t[b0:b1 + 1] <= hi_t)).any())


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
    bar_vol = np.asarray(b.volume, dtype=np.float64)
    fp = bars_mod.build_footprints(tk, b) if INDICADOR in BAR_DRIVEN else None
    mod = REGISTRY[INDICADOR]
    r = mod.run(tk, b, fp, chart_tz=TZ_CHART) if fp is not None \
        else mod.run(tk, b, chart_tz=TZ_CHART)

    setf = set(fechas)
    vols = vol_por_zona(r.get("csv_lines") or [])
    _ses, rango_sesion = sesiones_de_barras(bar_end, fechas)
    rng = np.random.default_rng([SEMILLA, zlib.crc32(("seguimiento:" + arch).encode())])

    filas = []
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
        j0, j1 = rango_sesion[ses]
        lo_h, hi_h = max(j0, cb - VENTANA_LOCAL), min(j1, cb + VENTANA_LOCAL)

        # lo_tick/hi_tick EXACTOS (no round() independiente): +/-0.5 cancela el
        # relleno de medio-tick de bigtrap2.py:202-203 sin boundary de .5.
        lo_t = round(float(z["bottom"]) / tk.tick_size + 0.5)
        hi_t = round(float(z["top"]) / tk.tick_size - 0.5)

        fila = dict(sesion=ses)
        # --- REAL, horizontes cortos ---
        for k in HORIZONTES_CORTOS:
            fila["real_tocada_%d" % k] = tocada_en_horizonte(
                lo_t, hi_t, cb, high_t, low_t, n, k)

        # --- NULO-B: desplazamiento local, CON su distancia realizada ---
        jb = int(rng.integers(lo_h, hi_h + 1))
        centro_b = int(close_t[jb])
        fila["dist_b_ticks"] = abs(centro_b - int(close_t[cb]))
        lo_nb = centro_b - alto // 2
        hi_nb = lo_nb + alto - 1   # rango INCLUSIVO de `alto` ticks
        _bf, _rz, _tc, tocada_b = vida_de_zona(lo_nb, hi_nb, is_bull, cb,
                                               high_t, low_t, close_t, n)
        fila["nulo_b_tocada"] = tocada_b
        for k in HORIZONTES_CORTOS:
            fila["nulo_b_tocada_%d" % k] = tocada_en_horizonte(
                lo_nb, hi_nb, cb, high_t, low_t, n, k)

        # --- NULO-C: local, pero elegido por VOLUMEN DE BARRA mas parecido ---
        objetivo = vols.get(z["id"], bar_vol[cb])
        ventana_vol = bar_vol[lo_h:hi_h + 1]
        jc = lo_h + int(np.argmin(np.abs(ventana_vol - objetivo)))
        centro_c = int(close_t[jc])
        fila["dist_c_ticks"] = abs(centro_c - int(close_t[cb]))
        lo_nc = centro_c - alto // 2
        hi_nc = lo_nc + alto - 1   # rango INCLUSIVO de `alto` ticks
        _bf, _rz, _tc, tocada_c = vida_de_zona(lo_nc, hi_nc, is_bull, cb,
                                               high_t, low_t, close_t, n)
        fila["nulo_c_tocada"] = tocada_c
        for k in HORIZONTES_CORTOS:
            fila["nulo_c_tocada_%d" % k] = tocada_en_horizonte(
                lo_nc, hi_nc, cb, high_t, low_t, n, k)

        fila["real_tocada"] = int(z.get("touches") or 0) > 0
        filas.append(fila)

    return dict(estado="OK", sesiones=len(fechas), filas=filas)


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

    print("F1.1 SEGUIMIENTO -- distancia propia / horizonte corto / nulo por volumen")
    print("  universo %d sesiones | semilla %d" % (ns, SEMILLA))

    filas = []
    crudo = {}
    for arch, fechas in plan:
        print("\n== %s : %d sesiones" % (arch, len(fechas)), flush=True)
        res = medir(arch, fechas)
        if res.get("estado") != "OK":
            crudo[arch] = res
            print("   %s: %s" % (res["estado"], res.get("motivo")))
            continue
        filas.extend(res["filas"])
        crudo[arch] = dict(estado="OK", sesiones=res["sesiones"], zonas=len(res["filas"]))
        print("   zonas=%d" % len(res["filas"]))

    n = len(filas)
    print("\n" + "=" * 70)
    print("(c) HORIZONTE CORTO -- tocada dentro de K barras  (n=%d)" % n)
    print("  %-10s %10s %10s %10s" % ("horiz.", "REAL", "NULO-B", "NULO-C"))
    horiz_out = {}
    for k in HORIZONTES_CORTOS:
        vr = sum(f["real_tocada_%d" % k] for f in filas) / n
        vb = sum(f["nulo_b_tocada_%d" % k] for f in filas) / n
        vc = sum(f["nulo_c_tocada_%d" % k] for f in filas) / n
        horiz_out[k] = dict(real=round(vr, 6), nulo_b=round(vb, 6), nulo_c=round(vc, 6))
        print("  %-10d %9.2f%% %9.2f%% %9.2f%%" % (k, 100 * vr, 100 * vb, 100 * vc))
    vr2000 = sum(f["real_tocada"] for f in filas) / n
    vb2000 = sum(f["nulo_b_tocada"] for f in filas) / n
    vc2000 = sum(f["nulo_c_tocada"] for f in filas) / n
    print("  %-10s %9.2f%% %9.2f%% %9.2f%%   (referencia F1.1, horizonte completo)"
          % ("2000", 100 * vr2000, 100 * vb2000, 100 * vc2000))

    print("\n(d) NULO POR VOLUMEN -- comparacion global  (n=%d)" % n)
    print("  tocada  REAL %.2f%%   NULO-B %.2f%%   NULO-C %.2f%%"
          % (100 * vr2000, 100 * vb2000, 100 * vc2000))
    dist_b = resumen([f["dist_b_ticks"] for f in filas])
    dist_c = resumen([f["dist_c_ticks"] for f in filas])
    print("  distancia realizada (ticks)  nulo-B mediana %.1f   nulo-C mediana %.1f"
          % (dist_b["p50"], dist_c["p50"]))

    print("\n(b) TASA DE TOQUE DEL NULO-B, ESTRATIFICADA POR SU PROPIA DISTANCIA")
    d_arr = np.asarray([f["dist_b_ticks"] for f in filas], dtype=np.float64)
    t_arr = np.asarray([f["nulo_b_tocada"] for f in filas], dtype=bool)
    cortes = [float(np.percentile(d_arr, q)) for q in CORTES_DISTANCIA]
    estratos = {}
    bordes = [0.0] + cortes + [float(d_arr.max()) + 1]
    print("  %-22s %8s %10s" % ("rango distancia (ticks)", "n", "tocada"))
    for i in range(len(bordes) - 1):
        lo_, hi_ = bordes[i], bordes[i + 1]
        m = (d_arr >= lo_) & (d_arr < hi_) if i < len(bordes) - 2 else (d_arr >= lo_) & (d_arr <= hi_)
        if not m.any():
            continue
        tasa = float(t_arr[m].mean())
        estratos["q%d" % (i + 1)] = dict(rango=[round(lo_, 1), round(hi_, 1)],
                                         n=int(m.sum()), tocada=round(tasa, 6))
        print("  [%6.1f , %6.1f)     %8d   %8.2f%%" % (lo_, hi_, int(m.sum()), 100 * tasa))
    print("  (referencia: REAL toca %.2f%% con distancia por construccion = 0)" % (100 * vr2000))

    payload = dict(
        schema_version=SCHEMA_VERSION, fase="F1.1_seguimiento",
        que_es="tres seguimientos de F1.1: distancia propia del nulo-B, "
               "horizonte corto, nulo por volumen de barra",
        plan="docs/F1.1_NULO_ZONAS_ALEATORIAS_RESULTADO_2026-08-10.md §7",
        semilla=SEMILLA, horizontes_cortos=list(HORIZONTES_CORTOS),
        session_count=ns, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_iso=str(corte_del_sello()),
        universe_filter_report=info, outcomes_accessed=False,
        n_pares=n,
        horizonte_corto=horiz_out,
        horizonte_2000=dict(real=round(vr2000, 6), nulo_b=round(vb2000, 6),
                            nulo_c=round(vc2000, 6)),
        distancia_realizada_ticks=dict(nulo_b=dist_b, nulo_c=dist_c),
        estratificacion_nulo_b_por_distancia=dict(
            cortes_percentiles=list(CORTES_DISTANCIA), estratos=estratos),
        por_contrato=crudo,
        code_commit=git_head(),
        measurement_code_sha256=huella_del_codigo([INDICADOR]),
        entorno=dict(python=sys.version.split()[0], plataforma=platform.platform()))
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        .encode()).hexdigest()
    salida = Path(a.out) if a.out else (
        Path(__file__).resolve().parent
        / ("F1.1_seguimiento__%s.json" % payload["payload_sha256"][:12]))
    salida.write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str)
                      + "\n", encoding="utf-8")
    print("\n-> %s" % salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
