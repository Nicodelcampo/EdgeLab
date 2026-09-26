"""Catálogo de calibración por contrato para **HFTZonesRange** (spec 2026-08-19).

QUÉ HACE
========
Corre **las mismas fórmulas** que `HFTZones2` sobre el store de ticks y publica, por
instrumento, las escalas congeladas que el indicador usaría como semilla:

    instrument -> { eff_*, n_sesiones, dispersión, procedencia }

POR QUÉ IMPORTA LAS FÓRMULAS EN VEZ DE COPIARLAS
================================================
`q_predator`, `q_ultra`, `q_max_avg`, `pause_mult`, `total_ms_mult`,
`vol_mult_median_tick` y `min_pasos` se leen de `hftzones2.DEFAULTS`, y el cuantil sale
de `edgelab.bridge.common.quantile_exact` — el mismo que usa el kernel. Si alguien
cambia un default, este catálogo cambia con él.

Copiar los números acá crearía **dos implementaciones de la misma fórmula**, que es
justamente el modo de falla que la §8 de la spec pone como condición de refutación.

LO QUE AGREGA LA SPEC (§4.2)
============================
    h1s = high−low en TICKS ENTEROS, por bucket de 1 s no solapado, vacíos afuera
    eff_min_sweep_ticks = max(H_FLOOR, round(Q(h1s, Q_HEIGHT)))

`H_FLOOR = 2` y `Q_HEIGHT = 0.90` están declarados en la spec **antes** de correr esto,
y no se mueven mirando el resultado.

LO QUE NO CALCULA, A PROPÓSITO
==============================
`eff_absorb_occ` necesita historia de **rachas**, no de ticks: exige correr el detector.
Sale `null` y `absorb_enabled: false`. La spec dice que sin historia el absorb va
apagado, así que publicar un número inventado sería peor que no publicarlo.

MEMORIA
=======
Lee **sólo tres columnas** por row-group (`ts_utc_ns`, `price_ticks`, `volume`) en vez
de las seis que carga `load_canonical_parquet`, y acumula por sesión. Así entran ES,
NQ y MNQ, que con la carga completa pasan de 2 GB (regla de P-25).

Target-free: sin outcomes, sin P&L. Holdout excluido por firewall.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np
import pyarrow.parquet as pq

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.common import quantile_exact  # noqa: E402
from edgelab.bridge.indicators.hftzones2 import DEFAULTS  # noqa: E402
from edgelab.data.nt8_contract import INSTRUMENT_SPECS  # noqa: E402
from edgelab.kaggle.sessions_cme import session_bounds_utc_ns  # noqa: E402

SCHEMA_VERSION = "hftzones_calib_catalog_v1"

# Declarados en docs/research/HFTZONESRANGE_SPEC_2026-08-19.md §4.2, ANTES de correr.
H_FLOOR = 2
Q_HEIGHT = 0.90
Q_OCC = 0.80          # se declara aunque no se use todavia (absorb apagado sin rachas)

NS = 1_000_000_000
HOLDOUT_FIRST_TRADE_DATE = 20260701
FIREWALL_CUTOFF_NS = session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0]

MIN_TICKS_SESION = 5_000     # sesiones mas flacas no calibran (ruido, no escala)


def _dirs(instrumento):
    base = REPO / "data" / "nt8"
    for cand in (base / instrumento, base / ("%s_parquet" % instrumento)):
        if cand.is_dir() and any(cand.glob("%s_*ticks*.parquet" % instrumento)):
            return cand
    return None


def calibrar_sesion(ts, px, vol, min_pasos):
    """Las fórmulas de `hftzones2.recalibrate`, sobre UNA sesión completa.

    Diferencia declarada: el kernel muestrea con reservoir (`calib_sample_cap`) porque
    corre en streaming; acá se usan **todos** los valores de la sesión. Es la misma
    fórmula sobre una muestra mayor, no otra fórmula.
    """
    p = DEFAULTS
    ms = np.diff(ts) / 1e6
    ms = ms[ms <= p["pause_exclude_ms"]]          # pausas AFUERA, igual que el kernel
    if len(ms) < 100 or len(vol) < 100:
        return None
    ms_l = sorted(float(x) for x in ms)
    vol_l = sorted(float(x) for x in vol)

    q_pred = quantile_exact(ms_l, p["q_predator"])
    q_ult = quantile_exact(ms_l, p["q_ultra"])
    q_max = quantile_exact(ms_l, p["q_max_avg"])
    p50 = quantile_exact(ms_l, 0.50)
    med_v = quantile_exact(vol_l, 0.50)

    eff = {}
    eff["eff_predator_ms"] = max(1.0, q_pred)
    eff["eff_ultra_ms"] = max(eff["eff_predator_ms"], q_ult)
    eff["eff_max_avg_ms"] = max(eff["eff_ultra_ms"], q_max)
    eff["eff_max_pausa_ms"] = min(5000.0, max(eff["eff_max_avg_ms"],
                                              p["pause_mult"] * max(1.0, p50)))
    eff["eff_max_total_ms"] = eff["eff_max_avg_ms"] * min_pasos * p["total_ms_mult"]
    eff["eff_min_total_vol"] = p["vol_mult_median_tick"] * med_v * min_pasos
    eff["eff_min_vol_rate"] = eff["eff_min_total_vol"] / (eff["eff_max_total_ms"] / 1000.0)

    # --- spec §4.2: altura en ticks DEL ACTIVO -------------------------------
    seg = ts // NS
    corte = np.flatnonzero(np.diff(seg)) + 1
    ini = np.concatenate(([0], corte))
    fin = np.concatenate((corte, [len(px)]))
    h1s = [int(px[a:b].max() - px[a:b].min()) for a, b in zip(ini, fin) if b > a]
    eff["eff_min_sweep_ticks"] = int(max(H_FLOOR, round(
        quantile_exact(sorted(float(x) for x in h1s), Q_HEIGHT)))) if h1s else H_FLOOR

    eff["_p50_ms"] = p50
    eff["_median_tick_vol"] = med_v
    eff["_n_ms"] = len(ms_l)
    eff["_n_buckets_1s"] = len(h1s)
    eff["_resolution_limited"] = bool(p50 <= 0.0)
    return eff


def sesiones_de_archivo(ruta, instrumento):
    """Itera (ts, px, vol) por sesión leyendo SOLO tres columnas, row-group por
    row-group. Acumula y suelta cuando cambia el trade date."""
    pf = pq.ParquetFile(ruta)
    buf_t, buf_p, buf_v, dia_actual = [], [], [], None
    for lote in pf.iter_batches(batch_size=1 << 20,
                                columns=["ts_utc_ns", "price_ticks", "volume"]):
        t = lote.column("ts_utc_ns").to_numpy(zero_copy_only=False).astype(np.int64)
        keep = t < FIREWALL_CUTOFF_NS
        if not keep.any():
            continue
        t = t[keep]
        p = lote.column("price_ticks").to_numpy(zero_copy_only=False).astype(np.int64)[keep]
        v = lote.column("volume").to_numpy(zero_copy_only=False).astype(np.float64)[keep]
        # trade date CME: la sesion abre 17:00 CT del dia anterior -> +7 h a UTC y cortar
        dia = (t + 7 * 3600 * NS) // (86_400 * NS)
        for d in np.unique(dia):
            m = dia == d
            if dia_actual is None:
                dia_actual = d
            if d != dia_actual:
                if buf_t:
                    yield (np.concatenate(buf_t), np.concatenate(buf_p), np.concatenate(buf_v))
                buf_t, buf_p, buf_v, dia_actual = [], [], [], d
            buf_t.append(t[m]); buf_p.append(p[m]); buf_v.append(v[m])
    if buf_t:
        yield (np.concatenate(buf_t), np.concatenate(buf_p), np.concatenate(buf_v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrumentos", nargs="*", default=sorted(INSTRUMENT_SPECS))
    ap.add_argument("--out", default=str(REPO / "docs" / "research" / "hftzones_calib_catalog.json"))
    a = ap.parse_args()

    print("catalogo de calibracion HFTZonesRange  ·  %s" % SCHEMA_VERSION)
    print("  MinPasos=%d  H_FLOOR=%d  Q_HEIGHT=%.2f  (declarados en la spec)"
          % (DEFAULTS["min_pasos"], H_FLOOR, Q_HEIGHT))

    catalogo, faltantes = {}, []
    for inst in a.instrumentos:
        d = _dirs(inst)
        if d is None:
            faltantes.append(inst)
            continue
        por_sesion = []
        for f in sorted(d.glob("%s_*ticks*.parquet" % inst)):
            for ts, px, vol in sesiones_de_archivo(f, inst):
                if len(ts) < MIN_TICKS_SESION:
                    continue
                eff = calibrar_sesion(ts, px, vol, DEFAULTS["min_pasos"])
                if eff:
                    por_sesion.append(eff)
        if not por_sesion:
            print("  %-4s sin sesiones calibrables" % inst)
            continue
        claves = [k for k in por_sesion[0] if not k.startswith("_")]
        agg = {}
        for k in claves:
            xs = np.array([s[k] for s in por_sesion], dtype=np.float64)
            agg[k] = round(float(np.median(xs)), 4)
            agg[k + "_p25"] = round(float(np.percentile(xs, 25)), 4)
            agg[k + "_p75"] = round(float(np.percentile(xs, 75)), 4)
        agg["eff_min_sweep_ticks"] = int(round(agg["eff_min_sweep_ticks"]))
        agg["eff_absorb_occ"] = None          # necesita historia de RACHAS, no de ticks
        agg["absorb_enabled"] = False
        agg["n_sesiones"] = len(por_sesion)
        agg["tick_size"] = INSTRUMENT_SPECS[inst].tick_size
        agg["mediana_vol_por_tick"] = round(float(np.median(
            [s["_median_tick_vol"] for s in por_sesion])), 4)
        agg["resolution_limited_en_alguna"] = bool(any(
            s["_resolution_limited"] for s in por_sesion))
        catalogo[inst] = agg
        print("  %-4s %3d sesiones   sweep>=%2d tk   max_avg %6.2f ms   min_total_vol %9.1f"
              % (inst, agg["n_sesiones"], agg["eff_min_sweep_ticks"],
                 agg["eff_max_avg_ms"], agg["eff_min_total_vol"]))

    porcelain = subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines()
    sucios = [l[3:].strip() for l in porcelain if l[:2] != "??"]

    out = dict(
        schema_version=SCHEMA_VERSION,
        spec="docs/research/HFTZONESRANGE_SPEC_2026-08-19.md",
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,
        nota=("las formulas se IMPORTAN de hftzones2.DEFAULTS y de "
              "edgelab.bridge.common.quantile_exact; copiarlas aca crearia dos "
              "implementaciones de la misma cuenta"),
        estructural=dict(min_pasos=DEFAULTS["min_pasos"],
                         fallos_tolerados=DEFAULTS["fallos_tolerados"],
                         H_FLOOR=H_FLOOR, Q_HEIGHT=Q_HEIGHT, Q_OCC=Q_OCC,
                         MERGE_GAP_MS=500,
                         nota="declarados en la spec ANTES de correr; no se tunean"),
        cuantiles_heredados={k: DEFAULTS[k] for k in
                             ("q_predator", "q_ultra", "q_max_avg", "pause_mult",
                              "total_ms_mult", "vol_mult_median_tick",
                              "pause_exclude_ms")},
        absorb=("eff_absorb_occ queda en null y absorb_enabled en false: necesita "
                "historia de RACHAS, no de ticks. La spec dice que sin historia el "
                "absorb va apagado."),
        instrumentos_sin_datos=faltantes,
        procedencia=dict(head_commit=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            archivos_sucios=sorted(sucios),
            medicion_comprometida=bool([f for f in sucios if f.startswith(("edgelab/", "diag/"))])),
        catalogo=catalogo)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("  escrito %s  (%d instrumentos%s)"
          % (a.out, len(catalogo),
             ", sin datos: %s" % ",".join(faltantes) if faltantes else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
