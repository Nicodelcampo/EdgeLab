"""Censo descriptivo de las zonas de HFTZonesESPureV2 sobre ES — target-free.

QUÉ CONTESTA Y QUÉ NO
=====================
Contesta: **¿el objeto tiene estructura?** Cuántas zonas hay, de qué tamaño, cuánto
duran, cómo se distribuyen en la sesión, cuánto se solapan, y qué condiciones producen
la mayor parte.

**No** contesta si sirven. No hay toques, ni rechazo, ni MFE/MAE, ni P&L. Eso es el
paso 4 del orden del auditor y necesita cruzar con los ticks del parquet, además de
hipótesis pre-registrada.

FUENTE
======
`runs/oraculo_espurev2_ES_snapshot.sqlite`, el snapshot congelado y hasheado de la
corrida controlada (`ORACULO_CONTROLADO`). Sólo zonas **pre-firewall**.

LA UNIDAD ES LA SESIÓN
======================
23.545 zonas sobre 120 sesiones **no** son 23.545 observaciones. Todo lo que se agrega
se publica **por sesión** además de en total, y la dispersión entre sesiones se publica
junto con la mediana. Es la regla que P-47 dejó escrita.

CONTEXTO DESDE EL PRINCIPIO (P-55)
==================================
Se guardan features de contexto por zona —hora dentro de la sesión, posición en el
rango del día, régimen de volatilidad de la sesión— **aunque este censo no las use para
condicionar nada**. Sin eso, preguntar por contexto más adelante exige re-correr todo.

Target-free: geometría y conteo. Sin outcomes.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import subprocess
import sys
from collections import Counter

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.kaggle.sessions_cme import (minutes_since_session_open,  # noqa: E402
                                         session_bounds_utc_ns, trade_date_ymd)

SCHEMA_VERSION = "censo_zonas_es_v1_descriptivo"
SNAPSHOT = REPO / "runs" / "oraculo_espurev2_ES_snapshot.sqlite"
HOLDOUT_FIRST_TRADE_DATE = 20260701
CUTOFF_MS = session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0] // 1_000_000

TICK_SIZE_ES = 0.25
CUANTILES = (5, 25, 50, 75, 95)


def q(v, nombre="q"):
    """Cuantiles + n, para no publicar una mediana sin su dispersion."""
    if len(v) == 0:
        return {}
    return {("%s%02d" % (nombre, p)): round(float(np.percentile(v, p)), 4) for p in CUANTILES}


def cargar(snapshot):
    con = sqlite3.connect("file:%s?mode=ro" % snapshot.as_posix(), uri=True)
    cols = ("instrument", "start_ts", "end_ts", "bucket", "dir", "price_upper",
            "price_lower", "height_ticks", "pasos", "valid_steps", "avg_ms",
            "total_ms", "total_vol", "max_tick_vol", "cvd_sweep", "no_move_vol",
            "no_move_ticks", "max_level_ticks", "max_retro")
    filas = con.execute(
        "SELECT %s FROM hft_zones WHERE start_ts < ? ORDER BY start_ts" % ",".join(cols),
        (CUTOFF_MS,)).fetchall()
    con.close()
    d = {c: np.array([f[i] for f in filas], dtype=object) for i, c in enumerate(cols)}
    for c in ("start_ts", "end_ts", "dir", "pasos", "valid_steps", "no_move_ticks",
              "max_level_ticks"):
        d[c] = np.array([0 if x is None else int(x) for x in d[c]], dtype=np.int64)
    for c in ("price_upper", "price_lower", "height_ticks", "avg_ms", "total_ms",
              "total_vol", "max_tick_vol", "cvd_sweep", "no_move_vol", "max_retro"):
        d[c] = np.array([np.nan if x is None else float(x) for x in d[c]], dtype=np.float64)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=str(SNAPSHOT))
    ap.add_argument("--out", default=str(REPO / "docs" / "research" / "censo_zonas_es.json"))
    a = ap.parse_args()

    print("censo descriptivo de zonas ES  ·  %s" % SCHEMA_VERSION)
    d = cargar(pathlib.Path(a.snapshot))
    n = len(d["start_ts"])
    ses = trade_date_ymd(d["start_ts"] * 1_000_000)
    minuto = minutes_since_session_open(d["start_ts"] * 1_000_000)
    sesiones = sorted(set(int(x) for x in ses))
    print("  %d zonas  ·  %d sesiones  ·  %s -> %s"
          % (n, len(sesiones), sesiones[0], sesiones[-1]))

    # --- por sesion: la unidad estadistica -----------------------------------------
    por_ses = Counter(int(x) for x in ses)
    zs = np.array([por_ses[s] for s in sesiones], dtype=np.float64)

    # --- geometria ------------------------------------------------------------------
    alto = (d["price_upper"] - d["price_lower"]) / TICK_SIZE_ES
    dur = (d["end_ts"] - d["start_ts"]).astype(np.float64)

    # --- solape: zonas activas simultaneamente, por sesion --------------------------
    solapes = []
    for s in sesiones:
        m = ses == s
        st, en = d["start_ts"][m], d["end_ts"][m]
        orden = np.argsort(st)
        st, en = st[orden], en[orden]
        # cuantas zonas se solapan con la siguiente en precio Y en tiempo
        sup, inf = d["price_upper"][m][orden], d["price_lower"][m][orden]
        k = 0
        for i in range(len(st) - 1):
            if st[i + 1] <= en[i] and not (inf[i + 1] > sup[i] or sup[i + 1] < inf[i]):
                k += 1
        solapes.append(k / max(len(st), 1))

    # --- contexto guardado aunque no se use (P-55) -----------------------------------
    contexto = []
    for s in sesiones:
        m = ses == s
        rng = float(np.nanmax(d["price_upper"][m]) - np.nanmin(d["price_lower"][m])) / TICK_SIZE_ES
        contexto.append(dict(
            trade_date=int(s), n_zonas=int(m.sum()),
            rango_zonas_ticks=round(rng, 2),
            vol_total=round(float(np.nansum(d["total_vol"][m])), 1),
            minuto_mediano=float(np.median(minuto[m])),
            frac_absorb=round(float(np.mean(d["bucket"][m] == "Absorb")), 4),
            frac_alcista=round(float(np.mean(d["dir"][m] > 0)), 4)))

    # --- concentracion horaria ------------------------------------------------------
    # minutos desde apertura (17:00 CT) en bloques de 60
    bloque = (minuto // 60).astype(int)
    por_hora = Counter(int(x) for x in bloque)
    horas = {str(h): por_hora.get(h, 0) for h in range(24)}
    top3 = sorted(por_hora.items(), key=lambda kv: -kv[1])[:3]
    frac_top3 = sum(v for _, v in top3) / n

    ocupa = round(float(np.mean(d["no_move_vol"] / np.where(d["total_vol"] > 0,
                                                            d["total_vol"], np.nan))), 4)

    porcelain = subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines()
    sucios = [l[3:].strip() for l in porcelain if l[:2] != "??"]

    out = dict(
        schema_version=SCHEMA_VERSION,
        fuente=dict(snapshot=str(a.snapshot), estado="ORACULO_CONTROLADO"),
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,
        nota_unidad=("23.545 zonas sobre 120 sesiones NO son 23.545 observaciones. Todo "
                     "agregado se publica por sesion ademas de en total."),
        universo=dict(n_zonas=n, n_sesiones=len(sesiones),
                      primera=sesiones[0], ultima=sesiones[-1],
                      contratos=dict(Counter(str(x) for x in d["instrument"]))),
        zonas_por_sesion=dict(mediana=float(np.median(zs)), media=round(float(zs.mean()), 1),
                              **q(zs, "p")),
        geometria=dict(
            altura_ticks=dict(mediana=float(np.median(alto)), **q(alto, "p")),
            duracion_ms=dict(mediana=float(np.median(dur)), **q(dur, "p")),
            pasos=dict(mediana=float(np.median(d["pasos"])), **q(d["pasos"], "p")),
            volumen=dict(mediana=float(np.median(d["total_vol"])), **q(d["total_vol"], "p")),
            avg_ms=dict(mediana=float(np.median(d["avg_ms"])), **q(d["avg_ms"], "p"))),
        composicion=dict(
            bucket=dict(Counter(str(x) for x in d["bucket"])),
            direccion=dict(alcista=int((d["dir"] > 0).sum()), bajista=int((d["dir"] < 0).sum())),
            frac_alcista=round(float((d["dir"] > 0).mean()), 4)),
        solape=dict(
            frac_por_sesion_mediana=round(float(np.median(solapes)), 4),
            **q(np.array(solapes), "p"),
            definicion="zona i+1 empieza antes de que termine i Y sus precios se pisan"),
        concentracion_horaria=dict(
            por_bloque_de_60min_desde_apertura=horas,
            top3_bloques=[[str(h), int(v)] for h, v in top3],
            frac_en_top3=round(frac_top3, 4)),
        ocupacion_media=ocupa,
        nota_ocupacion=("no_move_vol / total_vol. Es el estadistico que la spec de "
                        "HFTZonesRange propone para ABSORB, publicado aca como "
                        "DESCRIPTIVO -- no define nada todavia."),
        contexto_por_sesion=contexto,
        nota_contexto=("guardado por P-55 aunque este censo no condicione nada: si mas "
                       "adelante hay que preguntar por contexto, no hay que re-correr"),
        procedencia=dict(head_commit=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            archivos_sucios=sorted(sucios), alcance_comprometida=["edgelab/", "diag/"],
            medicion_comprometida=bool([f for f in sucios if f.startswith(("edgelab/", "diag/"))])))
    pathlib.Path(a.out).write_text(json.dumps(out, indent=2), encoding="utf-8")

    print()
    print("  zonas/sesion   mediana %.0f   p05 %.0f  p95 %.0f"
          % (out["zonas_por_sesion"]["mediana"], out["zonas_por_sesion"]["p05"],
             out["zonas_por_sesion"]["p95"]))
    g = out["geometria"]
    print("  altura ticks   mediana %.1f   p05 %.1f  p95 %.1f"
          % (g["altura_ticks"]["mediana"], g["altura_ticks"]["p05"], g["altura_ticks"]["p95"]))
    print("  duracion ms    mediana %.0f   p05 %.0f  p95 %.0f"
          % (g["duracion_ms"]["mediana"], g["duracion_ms"]["p05"], g["duracion_ms"]["p95"]))
    print("  pasos          mediana %.0f   p95 %.0f" % (g["pasos"]["mediana"], g["pasos"]["p95"]))
    print("  volumen        mediana %.0f   p95 %.0f" % (g["volumen"]["mediana"], g["volumen"]["p95"]))
    print("  buckets        %s" % out["composicion"]["bucket"])
    print("  alcistas       %.1f%%" % (out["composicion"]["frac_alcista"] * 100))
    print("  solape         %.1f%% de las zonas se pisan con la siguiente"
          % (out["solape"]["frac_por_sesion_mediana"] * 100))
    print("  top 3 horas    %s  = %.1f%% de todas las zonas"
          % ([h for h, _ in out["concentracion_horaria"]["top3_bloques"]], frac_top3 * 100))
    print("  ocupacion      %.3f  (no_move_vol / total_vol)" % ocupa)
    print("  escrito %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
