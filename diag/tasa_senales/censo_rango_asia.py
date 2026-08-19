"""Censo TARGET-FREE del rango de la sesión asiática y sus rupturas posteriores.

QUÉ CONTESTA Y QUÉ NO
=====================

Nico preguntó si el precio «suele revertir al tomar un lado de Asia». Esa pregunta
**no se contesta acá**: medir reversión es medir un resultado direccional, y eso cae
bajo el STOP (manifiesto de campaña + N_eff + riesgos + OK explícito, `CLAUDE.md`).

Lo que sí se mide es la **capa 1**: población y geometría.

  - ¿cuántas sesiones tienen rango asiático bien definido?
  - ¿qué tamaño tiene ese rango?
  - una vez terminada Asia, ¿se rompe algún extremo? ¿cuál primero? ¿cuándo?
  - ¿se terminan tocando **los dos** extremos?

Todo eso son eventos de toque de nivel — geometría pura, sin retornos, sin P&L, sin
MAE/MFE. Es el mismo orden que impuso H-Z2A: primero existe la población, después se
pregunta si hace algo.

ADVERTENCIA QUE VIAJA CON EL RESULTADO
======================================

La tasa de «se tocaron los dos extremos» **NO se puede leer como evidencia de
reversión**. Un paseo aleatorio sin deriva que acaba de tocar un borde de un rango
tiene probabilidad ALTA de tocar el otro antes de alejarse: es reflexión, no
comportamiento. `docs/research/H-SWEEP-1_YM_PRERANGE.md` ya midió esta trampa en otra
ventana y dejó escrito que **el nulo correcto no es 50% sino 54–76%**.

Publicar la tasa sin su nulo sería exactamente el error que ese documento documenta.

LA VENTANA, DECLARADA CON SUS ALTERNATIVAS
==========================================

Se usa **una sola** llamada a `minute_window_matrices` de 18:00 a 17:00 hora de Nueva
York (23 h = la sesión CME completa del trade date), y se parte por índice de minuto:

    slots    0 ..  539   ->  18:00–03:00 NY   ASIA        (apertura CME -> apertura Londres)
    slots  540 .. 1379   ->  03:00–17:00 NY   POSTERIOR

Una sola ventana garantiza que Asia y su posterior **pertenecen a la misma fila**. Dos
llamadas separadas las etiquetarían con fechas distintas (Asia cruza medianoche) y
alinearlas a mano es una fuente de error silencioso.

**Elección de reloj, y su consecuencia.** La ventana se fija en hora de **Nueva York**,
que es el reloj al que está anclada la sesión CME y el firewall del holdout. Eso
implica que, respecto de Tokio, la ventana **se corre una hora en cada cambio de DST**
(EST/EDT). La alternativa —fijarla en `Asia/Tokyo`— mantiene fija la sesión japonesa y
mueve el borde respecto de la sesión CME.

No es una elección neutral y por eso se declara: es la misma pregunta de huso horario
que dejó bloqueada H-SWEEP-1 en YM. Acá se resuelve **por el lado CME**, que es el
único reloj que este dataset tiene verificado.

`session_days` va en `None`: el calendario de research todavía no existe, así que
`calendar_complete` sale **False** y estas cuentas son **diagnóstico, no denominador
formal**. La propia función lo dice en su docstring. El denominador formal necesita el
calendario, que sigue siendo una compuerta abierta.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.bars import build_time_bars  # noqa: E402
from edgelab.bridge.ticks import TickSeries, load_canonical_parquet  # noqa: E402
from edgelab.kaggle.sessions_cme import session_bounds_utc_ns  # noqa: E402
from edgelab.sessions import minute_window_matrices  # noqa: E402

SCHEMA_VERSION = "censo_rango_asia_v1_targetfree"

VENTANA_INICIO = "18:00"      # apertura de la sesión CME, hora de Nueva York
VENTANA_FIN = "17:00"
MIN_ASIA = 540                # 18:00 -> 03:00
MIN_POST = 840                # 03:00 -> 17:00

MIN_BARRAS_ASIA = 120         # cobertura mínima para considerar el rango definido

HOLDOUT_FIRST_TRADE_DATE = 20260701
FIREWALL_CUTOFF_NS = session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0]

# Canon verificado SOLO para 6E. Para cualquier otro instrumento no existe tabla de
# hashes canonicos todavia, asi que el sha256 se COMPUTA Y SE DECLARA -- no se puede
# decir "verificado" de algo contra lo que no hay canon. El artefacto lo distingue con
# `canon_disponible`.
CONTRATOS_6E = (
    ("6E_12-25_ticks.parquet", "ea8b9f211929658494d952677fe302c33db66086ec1a21731f1f5d7ff74f7336"),
    ("6E_03-26_ticks.parquet", "b54120bfd99b97f218d73a1fe132bd111b997eab6095a529699473131f57cf76"),
    ("6E_06-26_ticks.parquet", "124b37507b95a1027aa753a75213b15e74f66b1396ca8df3c4324ea835f96cb1"),
    ("6E_09-26_ticks.parquet", "6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4"),
)


def sha256_archivo(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _contratos(d_in, instrumento):
    """6E usa la serie formal de 4 contratos (la misma del portador). Cualquier otro
    instrumento toma todos sus parquets de ticks, ordenados cronologicamente despues de
    cargarlos. Si dos contratos se solapan en el tiempo, `minute_window_matrices` corta
    con 'mas de una barra para el mismo dia/minuto': el chequeo de solape es el propio
    error, no un supuesto."""
    if instrumento == "6E":
        return [(fn, esperado) for fn, esperado in CONTRATOS_6E], True
    fs = sorted(d_in.glob("%s_*ticks*.parquet" % instrumento))
    if not fs:
        raise SystemExit("ABORTA: sin parquets de %s en %s" % (instrumento, d_in))
    return [(f.name, None) for f in fs], False


def cargar_barras(d_in, instrumento):
    contratos, canon = _contratos(d_in, instrumento)
    hashes, col = {}, {k: [] for k in ("ts", "px", "vol", "bid", "ask", "seq")}
    tick_size = None
    for fn, esperado in contratos:
        real = sha256_archivo(d_in / fn)
        hashes[fn] = dict(sha256=real, canonico=(real == esperado) if canon else None,
                          canon_disponible=canon)
        if canon and real != esperado:
            raise SystemExit("ABORTA: %s no es canonico" % fn)
        p = load_canonical_parquet(d_in / fn, instrument=instrumento)
        print("  %-26s %9d ticks  sha256 CANONICO" % (fn, len(p.ts_ns)))
        for k, v in (("ts", p.ts_ns), ("px", p.price_ticks), ("vol", p.volume),
                     ("bid", p.bid_ticks), ("ask", p.ask_ticks), ("seq", p.sequence)):
            col[k].append(v)
        tick_size = p.tick_size
        del p
    for k in list(col):
        col[k] = np.concatenate(col.pop(k)) if False else np.concatenate(col[k])
    gc.collect()
    orden = np.argsort(col["ts"], kind="stable")
    for k in list(col):
        col[k] = col[k][orden]
    del orden
    keep = col["ts"] < FIREWALL_CUTOFF_NS
    n_bruto = len(col["ts"])
    for k in list(col):
        col[k] = col[k][keep]
    print("  ticks   %d brutos -> %d tras firewall" % (n_bruto, len(col["ts"])))
    tkf = TickSeries(col["ts"], col["px"], col["vol"], col["bid"], col["ask"],
                     col["seq"], tick_size, instrumento,
                     "%s_%dC" % (instrumento, len(contratos)))
    bars = build_time_bars(tkf, minutes=1)
    del col, tkf
    gc.collect()
    return bars, hashes, tick_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrumento", default="6E")
    ap.add_argument("--dir", default=None,
                    help="por defecto data/nt8/<instrumento>")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    d_in = pathlib.Path(a.dir) if a.dir else (REPO / "data" / "nt8" / a.instrumento)
    print("censo rango Asia (TARGET-FREE)  ·  %s  ·  %s" % (SCHEMA_VERSION, a.instrumento))
    print("  ventana %s -> %s NY   Asia = primeros %d min   posterior = %d min"
          % (VENTANA_INICIO, VENTANA_FIN, MIN_ASIA, MIN_POST))
    bars, hashes, tick_size = cargar_barras(d_in, a.instrumento)

    # M1 en ticks ENTEROS: el rango de Asia y sus rupturas se comparan sin float.
    idx = pd.to_datetime(bars.end_ns, unit="ns", utc=True)
    df = pd.DataFrame(
        {"open": bars.open_t.astype(np.float64),
         "high": bars.high_t.astype(np.float64),
         "low": bars.low_t.astype(np.float64),
         "close": bars.close_t.astype(np.float64),
         "volume": bars.volume.astype(np.float64)},
        index=idx)
    print("  barras M1 %d   de %s a %s UTC" % (len(df), idx[0], idx[-1]))

    w = minute_window_matrices(df, start=VENTANA_INICIO, end=VENTANA_FIN)
    H, L, C = w["H"], w["L"], w["C"]
    dias = w["days"]
    print("  dias en la ventana %d   calendar_complete=%s" % (len(dias), w["calendar_complete"]))

    filas = []
    for i in range(len(dias)):
        hA, lA = H[i, :MIN_ASIA], L[i, :MIN_ASIA]
        n_asia = int(np.sum(~np.isnan(hA)))
        hP, lP = H[i, MIN_ASIA:], L[i, MIN_ASIA:]
        n_post = int(np.sum(~np.isnan(hP)))
        if n_asia < MIN_BARRAS_ASIA or n_post == 0:
            filas.append(dict(dia=str(dias[i].date()), n_barras_asia=n_asia,
                              n_barras_post=n_post, usable=False))
            continue
        alto = int(np.nanmax(hA))
        bajo = int(np.nanmin(lA))
        rango = alto - bajo

        rompe_alto = np.flatnonzero(hP > alto)
        rompe_bajo = np.flatnonzero(lP < bajo)
        t_alto = int(rompe_alto[0]) if len(rompe_alto) else None
        t_bajo = int(rompe_bajo[0]) if len(rompe_bajo) else None

        if t_alto is None and t_bajo is None:
            primero, t_primero = "ninguno", None
        elif t_bajo is None or (t_alto is not None and t_alto < t_bajo):
            primero, t_primero = "alto", t_alto
        else:
            primero, t_primero = "bajo", t_bajo

        filas.append(dict(
            dia=str(dias[i].date()), usable=True,
            n_barras_asia=n_asia, n_barras_post=n_post,
            rango_ticks=rango,
            rompe_alto=t_alto is not None, rompe_bajo=t_bajo is not None,
            ambos=(t_alto is not None and t_bajo is not None),
            primero=primero,
            minutos_hasta_primera_ruptura=t_primero,
            minutos_hasta_alto=t_alto, minutos_hasta_bajo=t_bajo))

    us = [f for f in filas if f["usable"]]
    rangos = np.array([f["rango_ticks"] for f in us], dtype=np.int64)
    con = [f for f in us if f["primero"] != "ninguno"]
    t1 = np.array([f["minutos_hasta_primera_ruptura"] for f in con], dtype=np.int64)

    resumen = dict(
        dias_en_ventana=len(dias), dias_usables=len(us),
        rango_ticks=dict(
            min=int(rangos.min()) if len(rangos) else None,
            p25=float(np.percentile(rangos, 25)) if len(rangos) else None,
            mediana=float(np.median(rangos)) if len(rangos) else None,
            p75=float(np.percentile(rangos, 75)) if len(rangos) else None,
            max=int(rangos.max()) if len(rangos) else None),
        rompe_alguno=sum(1 for f in us if f["primero"] != "ninguno"),
        rompe_ninguno=sum(1 for f in us if f["primero"] == "ninguno"),
        primero_alto=sum(1 for f in us if f["primero"] == "alto"),
        primero_bajo=sum(1 for f in us if f["primero"] == "bajo"),
        ambos_extremos=sum(1 for f in us if f["ambos"]),
        minutos_hasta_primera_ruptura=dict(
            p25=float(np.percentile(t1, 25)) if len(t1) else None,
            mediana=float(np.median(t1)) if len(t1) else None,
            p75=float(np.percentile(t1, 75)) if len(t1) else None) if len(t1) else None)

    porcelain = subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines()
    sucios = [l[3:].strip() for l in porcelain if l[:2] != "??"]
    criticos = [f for f in sucios if f.startswith(("edgelab/", "diag/"))]

    payload = dict(
        schema_version=SCHEMA_VERSION,
        instrumento=a.instrumento,
        outcomes_accessed=False, pnl_accessed=False,
        advertencia=("la tasa de 'ambos extremos' NO es evidencia de reversion: el nulo "
                     "de un paseo aleatorio que toco un borde es alto por reflexion. "
                     "Ver docs/research/H-SWEEP-1_YM_PRERANGE.md (54-76%, no 50%)."),
        ventana=dict(inicio_ny=VENTANA_INICIO, fin_ny=VENTANA_FIN,
                     minutos_asia=MIN_ASIA, minutos_post=MIN_POST,
                     reloj="America/New_York (anclado a la sesion CME; se corre 1 h "
                           "respecto de Tokio en cada cambio de DST)",
                     min_barras_asia=MIN_BARRAS_ASIA,
                     calendar_complete=bool(w["calendar_complete"]),
                     calendar_sha256=w["calendar_sha256"],
                     nota_denominador=("session_days=None: calendario de research "
                                       "inexistente, esto es diagnostico y NO "
                                       "denominador formal")),
        firewall=dict(holdout_first_trade_date=HOLDOUT_FIRST_TRADE_DATE,
                      cutoff_ns=int(FIREWALL_CUTOFF_NS),
                      holdout_included=False),
        procedencia=dict(
            contratos=hashes,
            todos_canonicos=(all(v["canonico"] for v in hashes.values())
                             if a.instrumento == "6E" else None),
            tick_size=tick_size,
            runner_blob=subprocess.check_output(
                ["git", "-C", str(REPO), "hash-object", str(pathlib.Path(__file__))],
                text=True).strip(),
            head_commit=subprocess.check_output(
                ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            archivos_sucios=sorted(sucios), sucios_criticos=sorted(criticos),
            medicion_comprometida=bool(criticos)),
        resumen=resumen, dias=filas)

    pathlib.Path(a.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print()
    print("  dias usables            %d de %d" % (len(us), len(dias)))
    if len(rangos):
        print("  rango Asia (ticks)      p25 %.0f  mediana %.0f  p75 %.0f  max %d"
              % (resumen["rango_ticks"]["p25"], resumen["rango_ticks"]["mediana"],
                 resumen["rango_ticks"]["p75"], resumen["rango_ticks"]["max"]))
    print("  rompe algun extremo     %d   ninguno %d"
          % (resumen["rompe_alguno"], resumen["rompe_ninguno"]))
    print("  primero alto / bajo     %d / %d" % (resumen["primero_alto"], resumen["primero_bajo"]))
    print("  toca AMBOS extremos     %d" % resumen["ambos_extremos"])
    if resumen["minutos_hasta_primera_ruptura"]:
        m = resumen["minutos_hasta_primera_ruptura"]
        print("  min hasta 1ra ruptura   p25 %.0f  mediana %.0f  p75 %.0f"
              % (m["p25"], m["mediana"], m["p75"]))
    print("  medicion_comprometida   %s" % bool(criticos))
    print("  informe %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
