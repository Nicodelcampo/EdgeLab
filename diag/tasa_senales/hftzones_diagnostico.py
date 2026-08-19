"""Diagnóstico del store para la calibración de HFTZonesRange — corregido.

POR QUÉ ESTE ARCHIVO EXISTE
===========================
`hftzones_calibrar.py` produjo `hftzones_calib_catalog.json` (commit `19e8713…`) y el
auditor lo invalidó con tres defectos verificados **contra el código**, no discutidos:

1. **Segmentación de sesiones mal.** Agrupaba con `(t + 7 h) // día`, que corta a las
   **17:00 UTC**. La sesión CME abre 17:00 **CT** = 22:00 UTC en DST y 23:00 fuera.
   Cortaba 5–6 horas antes y **ignoraba el DST**. El repo ya tiene
   `sessions_cme.trade_date_ymd`, que usa `SESSION_OPEN_HOUR_CT` sobre hora local.
2. **Filtro de `ms` distinto del kernel.** El kernel usa `0 <= ms <= pause_exclude_ms`
   (l. 464); el calibrador usaba sólo `ms <= …`, sin rechazar negativos.
3. **`resolution_limited_en_alguna` es un `any()`** y yo lo leí como universal. No son
   lo mismo, y **YM lo contradice**: su `eff_max_pausa` mediano de 20 ms implica
   `p50 ≈ 4 ms` vía `5 × max(1, p50)`. Además `eff_max_avg` depende de **q15**, no de
   la mediana: puede colapsar a 1 con `p50 > 0`.

Y una cuarta que el auditor marcó y es real: el kernel muestrea con `_Sampler`
(decimación determinística por stride) y el calibrador usaba **todos** los valores.
Llamar «la misma calibración» a dos caminos distintos era una afirmación sin medir.

QUÉ HACE ESTE SCRIPT
====================
**Sólo diagnóstico.** No propone umbrales, no toca `Q_HEIGHT`, `H_FLOOR` ni `MinPasos`,
y no implementa el indicador. Publica, por instrumento:

  - sesiones agrupadas con `trade_date_ymd`
  - `n_dt_negativos` y verificación de monotonicidad
  - `frac_dt_cero` y cuantiles 2/5/15/50/75/95 de `dt`
  - `n_sesiones_limited / n_sesiones` (**no** un `any`)
  - distribución de trades que comparten timestamp
  - volumen: `frac(volume == 1)` y q50/q75/q90/q95/q99 — diagnóstico, no un gate
  - calibración con **muestra completa** vs **sampler del kernel**, lado a lado
  - fracción de sesiones pegadas a `H_FLOOR`

Target-free: sin outcomes, sin MAE/MFE, sin P&L. Holdout excluido por firewall.
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
from edgelab.bridge.indicators.hftzones2 import DEFAULTS, _Sampler  # noqa: E402
from edgelab.data.nt8_contract import INSTRUMENT_SPECS  # noqa: E402
from edgelab.kaggle.sessions_cme import session_bounds_utc_ns, trade_date_ymd  # noqa: E402

SCHEMA_VERSION = "hftzones_diagnostico_v2_1_sampler_completo"

# CONGELADOS. Se citan para poder reproducir la cuenta, NO se tocan (P-47 / §4.4).
H_FLOOR = 2
Q_HEIGHT = 0.90

NS = 1_000_000_000
HOLDOUT_FIRST_TRADE_DATE = 20260701
FIREWALL_CUTOFF_NS = session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0]
MIN_TICKS_SESION = 5_000
CUANTILES_DT = (0.02, 0.05, 0.15, 0.50, 0.75, 0.95)
CUANTILES_VOL = (0.50, 0.75, 0.90, 0.95, 0.99)


def _dir_de(inst):
    base = REPO / "data" / "nt8"
    for c in (base / inst, base / ("%s_parquet" % inst)):
        if c.is_dir() and any(c.glob("%s_*ticks*.parquet" % inst)):
            return c
    return None


def sesiones_de_archivo(ruta, inst):
    """Itera (ts, px, vol) por **trade date CME**, leyendo 3 columnas por row-group.

    La version anterior agrupaba con `(t + 7 h) // dia`, que corta a las 17:00 UTC e
    ignora el DST. `trade_date_ymd` resuelve hora local y suma el dia cuando el
    segundo-del-dia pasa `SESSION_OPEN_HOUR_CT`, que es la definicion canonica del repo.
    """
    pf = pq.ParquetFile(ruta)
    buf_t, buf_p, buf_v, actual = [], [], [], None
    for lote in pf.iter_batches(batch_size=1 << 20,
                                columns=["ts_utc_ns", "price_ticks", "volume"]):
        t = lote.column("ts_utc_ns").to_numpy(zero_copy_only=False).astype(np.int64)
        keep = t < FIREWALL_CUTOFF_NS
        if not keep.any():
            continue
        t = t[keep]
        p = lote.column("price_ticks").to_numpy(zero_copy_only=False).astype(np.int64)[keep]
        v = lote.column("volume").to_numpy(zero_copy_only=False).astype(np.float64)[keep]
        td = trade_date_ymd(t)
        cortes = np.flatnonzero(np.diff(td)) + 1
        ini = np.concatenate(([0], cortes))
        fin = np.concatenate((cortes, [len(td)]))
        for a, b in zip(ini, fin):
            d = int(td[a])
            if actual is None:
                actual = d
            if d != actual:
                if buf_t:
                    yield actual, np.concatenate(buf_t), np.concatenate(buf_p), np.concatenate(buf_v)
                buf_t, buf_p, buf_v, actual = [], [], [], d
            buf_t.append(t[a:b]); buf_p.append(p[a:b]); buf_v.append(v[a:b])
    if buf_t:
        yield actual, np.concatenate(buf_t), np.concatenate(buf_p), np.concatenate(buf_v)


def _eff(ms_ord, vol_ord, min_pasos):
    """Las formulas del kernel, sobre una lista YA ORDENADA."""
    p = DEFAULTS
    if len(ms_ord) < 100 or len(vol_ord) < 100:
        return None
    p50 = quantile_exact(ms_ord, 0.50)
    med_v = quantile_exact(vol_ord, 0.50)
    e = {}
    e["eff_predator_ms"] = max(1.0, quantile_exact(ms_ord, p["q_predator"]))
    e["eff_ultra_ms"] = max(e["eff_predator_ms"], quantile_exact(ms_ord, p["q_ultra"]))
    e["eff_max_avg_ms"] = max(e["eff_ultra_ms"], quantile_exact(ms_ord, p["q_max_avg"]))
    e["eff_max_pausa_ms"] = min(5000.0, max(e["eff_max_avg_ms"],
                                            p["pause_mult"] * max(1.0, p50)))
    e["eff_max_total_ms"] = e["eff_max_avg_ms"] * min_pasos * p["total_ms_mult"]
    e["eff_min_total_vol"] = p["vol_mult_median_tick"] * med_v * min_pasos
    e["eff_min_vol_rate"] = e["eff_min_total_vol"] / (e["eff_max_total_ms"] / 1000.0)
    e["_p50_ms"] = p50
    e["_median_vol"] = med_v
    e["_resolution_limited"] = bool(p50 <= 0.0)
    return e


def diagnosticar_sesion(ts, px, vol, min_pasos):
    p = DEFAULTS
    dt = np.diff(ts) / 1e6
    n_neg = int((dt < 0).sum())
    # Filtro EXACTO del kernel (l. 464): `0 <= ms <= pause_exclude_ms`.
    ms = dt[(dt >= 0) & (dt <= p["pause_exclude_ms"])]
    if len(ms) < 100 or len(vol) < 100:
        return None
    ms_ord = sorted(float(x) for x in ms)
    vol_ord = sorted(float(x) for x in vol)

    completo = _eff(ms_ord, vol_ord, min_pasos)

    # Camino del kernel: decimacion determinista por stride, mismo cap.
    sm, sv = _Sampler(int(p["calib_sample_cap"])), _Sampler(int(p["calib_sample_cap"]))
    for x in ms:
        sm.add(float(x))
    for x in vol:
        sv.add(float(x))
    muestreado = _eff(sorted(sm.vals), sorted(sv.vals), min_pasos)

    # altura por bucket de 1 s (para la fraccion pegada a H_FLOOR)
    seg = ts // NS
    cortes = np.flatnonzero(np.diff(seg)) + 1
    ini = np.concatenate(([0], cortes)); fin = np.concatenate((cortes, [len(px)]))
    h1s = [int(px[a:b].max() - px[a:b].min()) for a, b in zip(ini, fin) if b > a]
    sweep = int(max(H_FLOOR, round(quantile_exact(sorted(float(x) for x in h1s), Q_HEIGHT)))) \
        if h1s else H_FLOOR

    # trades que comparten timestamp exacto
    _, cuentas = np.unique(ts, return_counts=True)

    return dict(
        n_ticks=len(ts), n_dt_negativos=n_neg, monotona=bool(n_neg == 0),
        frac_dt_cero=float((dt == 0).mean()),
        q_dt={("q%03d" % int(q * 100)): quantile_exact(ms_ord, q) for q in CUANTILES_DT},
        frac_vol_1=float((vol == 1).mean()),
        q_vol={("q%03d" % int(q * 100)): quantile_exact(vol_ord, q) for q in CUANTILES_VOL},
        mismo_ts_max=int(cuentas.max()), mismo_ts_p95=float(np.percentile(cuentas, 95)),
        sweep_ticks=sweep, pegada_a_floor=bool(sweep <= H_FLOOR),
        completo=completo, muestreado=muestreado,
        stride_ms=int(sm.stride), n_muestra_ms=len(sm.vals), n_total_ms=len(ms_ord))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrumentos", nargs="*", default=sorted(INSTRUMENT_SPECS))
    ap.add_argument("--out", default=str(REPO / "docs" / "research" / "hftzones_diagnostico_v2.json"))
    a = ap.parse_args()

    print("diagnostico HFTZonesRange  ·  %s" % SCHEMA_VERSION)
    print("  sesiones por trade_date_ymd (17:00 CT, DST-aware) — NO por (t+7h)//dia")
    mp = DEFAULTS["min_pasos"]
    salida, faltan = {}, []

    for inst in a.instrumentos:
        d = _dir_de(inst)
        if d is None:
            faltan.append(inst)
            continue
        ses = []
        for f in sorted(d.glob("%s_*ticks*.parquet" % inst)):
            for td, ts, px, vol in sesiones_de_archivo(f, inst):
                if len(ts) < MIN_TICKS_SESION:
                    continue
                r = diagnosticar_sesion(ts, px, vol, mp)
                if r:
                    r["trade_date"] = int(td)
                    ses.append(r)
        if not ses:
            print("  %-4s sin sesiones" % inst)
            continue

        n = len(ses)
        med = lambda f: float(np.median([f(s) for s in ses]))                      # noqa: E731
        pct = lambda f, q: float(np.percentile([f(s) for s in ses], q))            # noqa: E731
        lim = [s for s in ses if s["completo"]["_resolution_limited"]]
        floor = [s for s in ses if s["pegada_a_floor"]]
        # EQUIVALENCIA DEL SAMPLER SOBRE TODO EL VECTOR (v2.1).
        #
        # v2 comparaba solo `eff_max_avg_ms` y `eff_min_total_vol` -- justamente los dos
        # campos SATURADOS por sus pisos, que coinciden casi por construccion. De ahi
        # concluir "muestra completa y sampler son identicos" era una sobreafirmacion:
        # no se miraba `eff_max_pausa_ms`, que es donde YM conserva variacion, ni `p50`,
        # ni `resolution_limited`.
        CAMPOS_EFF = ("eff_predator_ms", "eff_ultra_ms", "eff_max_avg_ms",
                      "eff_max_pausa_ms", "eff_max_total_ms", "eff_min_total_vol",
                      "eff_min_vol_rate", "_p50_ms", "_median_vol")
        dif_por_campo, discrepan = {}, {}
        for c in CAMPOS_EFF:
            xs = [abs(s["completo"][c] - s["muestreado"][c]) for s in ses if s["muestreado"]]
            dif_por_campo[c] = round(float(max(xs)), 6) if xs else None
            discrepan[c] = int(sum(1 for x in xs if x > 0))
        rl = [(s["completo"]["_resolution_limited"], s["muestreado"]["_resolution_limited"])
              for s in ses if s["muestreado"]]
        dif_rl = int(sum(1 for a_, b_ in rl if a_ != b_))

        salida[inst] = dict(
            n_sesiones=n,
            # --- lo que el `any()` escondia -------------------------------------
            n_sesiones_limited=len(lim),
            frac_sesiones_limited=round(len(lim) / n, 4),
            p50_ms=dict(mediana=med(lambda s: s["completo"]["_p50_ms"]),
                        p25=pct(lambda s: s["completo"]["_p50_ms"], 25),
                        p75=pct(lambda s: s["completo"]["_p50_ms"], 75)),
            q_dt_mediano={k: med(lambda s, k=k: s["q_dt"][k]) for k in
                          ("q002", "q005", "q015", "q050", "q075", "q095")},
            # --- integridad -----------------------------------------------------
            n_dt_negativos_total=int(sum(s["n_dt_negativos"] for s in ses)),
            sesiones_no_monotonas=int(sum(0 if s["monotona"] else 1 for s in ses)),
            frac_dt_cero_mediana=round(med(lambda s: s["frac_dt_cero"]), 4),
            trades_mismo_ts_max=int(max(s["mismo_ts_max"] for s in ses)),
            trades_mismo_ts_p95_mediano=round(med(lambda s: s["mismo_ts_p95"]), 2),
            # --- volumen: diagnostico, NO un gate --------------------------------
            frac_volume_1_mediana=round(med(lambda s: s["frac_vol_1"]), 4),
            q_vol_mediano={k: med(lambda s, k=k: s["q_vol"][k]) for k in
                           ("q050", "q075", "q090", "q095", "q099")},
            # --- altura ----------------------------------------------------------
            sweep_ticks_mediano=int(round(med(lambda s: s["sweep_ticks"]))),
            n_sesiones_pegadas_a_floor=len(floor),
            frac_sesiones_pegadas_a_floor=round(len(floor) / n, 4),
            # --- muestra completa vs sampler del kernel ---------------------------
            sampler=dict(
                stride_mediano=int(med(lambda s: s["stride_ms"])),
                n_muestra_mediana=int(med(lambda s: s["n_muestra_ms"])),
                n_total_mediana=int(med(lambda s: s["n_total_ms"])),
                dif_max_por_campo=dif_por_campo,
                sesiones_que_discrepan_por_campo=discrepan,
                sesiones_que_discrepan_resolution_limited=dif_rl,
                campos_comparados=len(CAMPOS_EFF) + 1,
                identicos_vector_completo=bool(
                    all(v == 0 for v in dif_por_campo.values() if v is not None)
                    and dif_rl == 0)),
            # --- eff_* con la muestra completa, para el diff viejo->nuevo ---------
            eff_completo={k: round(med(lambda s, k=k: s["completo"][k]), 4)
                          for k in ("eff_predator_ms", "eff_ultra_ms", "eff_max_avg_ms",
                                    "eff_max_pausa_ms", "eff_max_total_ms",
                                    "eff_min_total_vol", "eff_min_vol_rate")})
        s_ = salida[inst]
        print("  %-4s %3d ses · limited %d/%d (%.0f%%) · p50 %.2f ms · q15 %.2f · "
              "vol=1 %.0f%% · sweep %d (floor %.0f%%) · sampler identico %s"
              % (inst, n, s_["n_sesiones_limited"], n, s_["frac_sesiones_limited"] * 100,
                 s_["p50_ms"]["mediana"], s_["q_dt_mediano"]["q015"],
                 s_["frac_volume_1_mediana"] * 100, s_["sweep_ticks_mediano"],
                 s_["frac_sesiones_pegadas_a_floor"] * 100, s_["sampler"]["identicos"]))

    porcelain = subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines()
    sucios = [l[3:].strip() for l in porcelain if l[:2] != "??"]
    no_trackeados = [l[3:].strip() for l in porcelain if l[:2] == "??"]
    out = dict(
        schema_version=SCHEMA_VERSION,
        reemplaza="docs/research/hftzones_calib_catalog.json (19e8713, SUPERSEDED)",
        motivo=("el catalogo anterior agrupaba sesiones con (t+7h)//dia -> cortes a las "
                "17:00 UTC, no 17:00 CT, ignorando DST; filtraba ms sin rechazar "
                "negativos; y su `resolution_limited_en_alguna` es un any() que se "
                "leyo como universal"),
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,
        congelado=dict(H_FLOOR=H_FLOOR, Q_HEIGHT=Q_HEIGHT,
                       min_pasos=DEFAULTS["min_pasos"],
                       nota="citados para reproducir; NO se tocan"),
        instrumentos_sin_datos=faltan,
        procedencia=dict(head_commit=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            archivos_sucios=sorted(sucios), archivos_no_trackeados=sorted(no_trackeados),
            alcance_comprometida=["edgelab/", "diag/"],
            medicion_comprometida=bool([f for f in sucios if f.startswith(("edgelab/", "diag/"))]),
            nota_medicion=(
                "medicion_comprometida=false significa: NINGUN archivo sucio dentro del "
                "alcance declarado (edgelab/, diag/). NO significa arbol limpio -- puede "
                "haber sucios fuera de ese alcance, y estan listados en "
                "`archivos_sucios`. Tampoco significa que la medicion sea "
                "metodologicamente valida: el catalogo de 19e8713 tenia este campo en "
                "false y estaba mal segmentado.")),
        diagnostico=salida)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("  escrito %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
