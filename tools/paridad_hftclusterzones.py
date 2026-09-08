#!/usr/bin/env python3
r"""Paridad de la capa de CLUSTERS: NT8 (`.cs` v2.0.0) contra el espejo Python.

## Por qué hace falta una herramienta aparte

La capa de zonas ya está certificada EXACT (`docs/parity_coverage/HFTZonesNQ.md`) y su
motor no cambió: `ProcesarSweeps` es idéntico byte a byte entre el `.cs` v1.1.0 y el
v2.0.0. La capa de clusters, en cambio, **nunca tuvo oráculo comparado**. Esta
herramienta la compara por primera vez.

## Estimand declarado

*Fracción de eventos de cluster del oráculo que el espejo reproduce con los once campos
idénticos, emparejados por `(start_ts, update_ts, event)`.*

No es "cuántos clusters encuentra cada lado". El oráculo es la población y la pregunta
es si el espejo la reproduce. Se compara el **flujo de eventos**, no el estado final:
por las marcas de agua de la expansión, el estado final de un cluster no contiene su
historia.

## Por qué la clave es esa

`cluster_id` no sirve: cada motor lleva su propio contador y se desincronizan al primer
cluster que uno cree y el otro no. `start_ts` identifica el nacimiento y es estable
ante expansiones; `update_ts` fecha el evento; `event` lo desempata cuando dos
transiciones caen en la misma barra.

## El orden de la reproducción, que es donde se juega

El `.cs` intercala dos series. Reproducirlo exige respetar el orden exacto:

    por cada barra primaria i:
        por cada tick k de la barra:            # BarsInProgress == 1
            ProcesarSweeps()                    #   -> si una zona FINALIZA aquí,
                                                #      EvaluarHaloClusters(bar=i)
            ActualizarConsumoTick(...)
        ActualizarConsumoBarra(...)             # BarsInProgress == 0, cierre de barra
        VerificarExpiracionClusters()

Dos detalles que no son cosméticos:

**1. El cluster se evalúa cuando la zona TERMINA, no cuando empieza.** En el `.cs`,
`EvaluarHaloClusters(zones.Count - 1)` se llama justo después de agregar la zona, o sea
al finalizar el streak. La zona conserva `StartBar` = barra de su inicio (`prim_start`),
pero la evaluación ocurre en `CurrentBars[0]`, que es la barra del final. Los runners de
investigación (`rechazo_clusters_nq.py`, `decaimiento_clusters_nq.py`) disparan la
evaluación en la barra de INICIO: los clusters les nacen antes de tiempo. Ver el registro
MEDIDO/NO MEDIDO.

**2. En histórico corren los dos caminos de consumo.** La guarda de
`ActualizarConsumoBarra` sólo se activa en `Realtime`, así que reproduciendo histórico
el volumen se cuenta dos veces. El espejo lo reproduce con `consumo_por_barra=True`
porque su trabajo es parecerse al oráculo. **El certificado que emite esta herramienta
vale para el objeto histórico, no para el que se ve en vivo.**

## Riesgo conocido: la alineación de barras

NT8 arma sus barras de N ticks con su propio conteo, que depende de dónde arrancó la
sesión y de la serie que tenga cargada. El espejo las arma troceando el parquet por
índice. Si los dos cortes quedan corridos, todo lo que dependa del índice de barra
—la expiración, sobre todo— diverge aunque la lógica sea idéntica.

Por eso el reporte separa tres cosas que se confunden fácil: eventos que **faltan**,
eventos presentes con **campos distintos**, y eventos presentes con los campos bien
pero en **otra barra**. Sólo el segundo grupo es un defecto del espejo; el tercero
apunta al arnés.

    .venv\Scripts\python tools\paridad_hftclusterzones.py ^
        --instrumento "NQ 06-26" ^
        --db "C:/LoggerHFT/data/oraculo_clusters_NQ0626_20260908.sqlite" ^
        --parquet data/nt8/NQ_parquet/NQ_06-26_ticks.parquet
"""
from __future__ import annotations

import argparse
import collections
import json
import sqlite3
import sys
from pathlib import Path

import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.indicators import hftclusterzones as hc  # noqa: E402
from edgelab.bridge.indicators import hftzones_nq as hz  # noqa: E402
from edgelab.research import cluster_decay as cd  # noqa: E402

DB = "C:/LoggerHFT/data/oraculo_clusters_NQ0626_20260908.sqlite"

COLS = ("cluster_id,start_ts,end_ts,lower,upper,poc,initial_density,seed_volume,"
        "seed_cvd,capacity_volume,volume_inside,delta_inside,remaining_cap_pct,"
        "state,event,update_ts")

# (nombre del campo, indice en la fila del oraculo, como sacarlo del evento del espejo)
CAMPOS = [
    ("lower", 3, lambda e: e["lower"]),
    ("upper", 4, lambda e: e["upper"]),
    ("poc", 5, lambda e: e["poc"]),
    ("initial_density", 6, lambda e: e["peak_density"]),
    ("seed_volume", 7, lambda e: e["seed_volume"]),
    ("seed_cvd", 8, lambda e: e["seed_cvd"]),
    ("capacity_volume", 9, lambda e: e["capacity_volume"]),
    ("volume_inside", 10, lambda e: e["volume_inside"]),
    ("delta_inside", 11, lambda e: e["delta_inside"]),
    ("remaining_cap_pct", 12, lambda e: e["remaining_cap_pct"]),
    ("state", 13, lambda e: e["state"]),
]

TOL = 1e-6


def lados(price_ticks):
    """Regla del tick con arrastre, igual que el `.cs`:

        side = cl > clP ? 1 : (cl < clP ? -1 : lastSide)
    """
    out = []
    ultimo = 0
    previo = None
    for p in price_ticks:
        if previo is None:
            lado = 0
        elif p > previo:
            lado = 1
        elif p < previo:
            lado = -1
        else:
            lado = ultimo
        out.append(lado)
        ultimo = lado
        previo = p
    return out


def barra_de_entrega(z, ticks_por_barra, n_barras):
    """Barra en la que el motor de clusters RECIBE la zona: la de su FINAL.

    El `.cs` llama a `EvaluarHaloClusters` justo despues de agregar la zona, o sea al
    finalizar el streak, con `CurrentBars[0]` = barra del final. Los runners de
    investigacion usan la barra de INICIO y por eso les nacen clusters antes de tiempo.
    """
    return min(z["idx_end"] // ticks_por_barra, n_barras - 1)


def barra_de_nacimiento(z, ticks_por_barra, n_barras):
    """Barra que la zona declara como propia: la de su INICIO (`prim_start` en el `.cs`).

    Es distinta de la de entrega, y las dos se usan: la de nacimiento entra en el pool
    y decide la edad; la de entrega decide CUANDO se reevalua el campo.
    """
    return min(z["idx_start"] // ticks_por_barra, n_barras - 1)


def reproducir(ts, px, vo, tick_size, ticks_por_barra, params):
    """Corre el espejo respetando el orden de las dos series del `.cs`.

    Devuelve `(eventos, zonas, barras)`. Cada evento lleva `update_ms`, el timestamp de
    la barra primaria en curso — que es lo que el `.cs` graba en `LogClusterEvent`,
    **no** el timestamp del tick.
    """
    zonas, _ = hz.accept_all(hz.detect_candidates(ts, px, vo),
                             dict(hz.ACCEPT_DEFAULTS), tick_size)
    barras, _ = cd.barras_desde_ticks(ts, px, vo, ticks_por_barra)
    if not barras:
        return [], zonas, barras

    lado = lados(px)
    eng = hc.ClusterEngine(tick_size, params)

    # La zona se ENTREGA al motor de clusters en la barra donde su streak TERMINA,
    # conservando `start_bar` = barra donde EMPEZO. Es la distincion que los runners
    # de investigacion no hacen.
    por_barra_fin = collections.defaultdict(list)
    for z in zonas:
        por_barra_fin[barra_de_entrega(z, ticks_por_barra, len(barras))].append(z)

    acumuladas = []
    eventos = []

    def sellar(nuevos, bar_i):
        ms = ts[barras[bar_i]["i0"]] // 1_000_000
        for e in nuevos:
            e = dict(e)
            e["update_ms"] = ms
            e["start_ms"] = ts[barras[e["start_bar"]]["i0"]] // 1_000_000 \
                if 0 <= e["start_bar"] < len(barras) else None
            eventos.append(e)

    for i, b in enumerate(barras):
        # ---- BarsInProgress == 1: la sub-serie de ticks ----
        nacen = por_barra_fin.get(i, [])
        pendientes = {z["idx_end"]: z for z in nacen}
        for k in range(b["i0"], b["i1"]):
            z = pendientes.pop(k, None)
            if z is not None:
                acumuladas.append(dict(
                    lower=z["sw_lo_tk"] * tick_size, upper=z["sw_hi_tk"] * tick_size,
                    start_bar=barra_de_nacimiento(z, ticks_por_barra, len(barras)),
                    total_vol=z["total_vol"], cvd=z["cvd"]))
                sellar(eng.on_zone_created(acumuladas, bar=i), i)
            sellar(eng.on_tick(px[k] * tick_size, float(vo[k]), lado[k], i), i)
        # las que terminaron fuera del rango de la barra (borde del troceo)
        for z in pendientes.values():
            acumuladas.append(dict(
                lower=z["sw_lo_tk"] * tick_size, upper=z["sw_hi_tk"] * tick_size,
                start_bar=min(z["idx_start"] // ticks_por_barra, len(barras) - 1),
                total_vol=z["total_vol"], cvd=z["cvd"]))
            sellar(eng.on_zone_created(acumuladas, bar=i), i)

        # ---- BarsInProgress == 0: cierre de la barra primaria ----
        if params.get("consumo_por_barra"):
            vol_barra = float(sum(vo[b["i0"]:b["i1"]]))
            sellar(eng.on_bar_consumo(b["lo"] * tick_size, b["hi"] * tick_size,
                                      vol_barra, i), i)
        sellar(eng.on_bar(i), i)

    return eventos, zonas, barras


_TRAD = {"CLUSTER_CREATED": "CREATED", "CLUSTER_EXPANDED": "EXPANDED",
         "CLUSTER_TOUCHED_POC": "TOUCHED_POC", "CLUSTER_DEPLETED": "DEPLETED",
         "CLUSTER_EXPIRED": "EXPIRED", "CLUSTER_EVICTED": "EVICTED"}


def _norm_evento(nombre):
    n = str(nombre).upper()
    return _TRAD.get(n, n.replace("CLUSTER_", ""))


def cargar_oraculo(instrumento, db=DB):
    con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    try:
        filas = con.execute(
            "select %s from hft_clusters where instrument=? order by update_ts, id"
            % COLS, (instrumento,)).fetchall()
    finally:
        con.close()
    return filas


def comparar(orac, espejo, tick_size):
    """Empareja por `(start_ms, update_ms, event)` y compara campo a campo."""
    idx = collections.defaultdict(list)
    solo_campos = collections.defaultdict(list)   # sin la barra, para el tercer grupo
    for e in espejo:
        ev = _norm_evento(e["event"])
        idx[(e.get("start_ms"), e.get("update_ms"), ev)].append(e)
        solo_campos[(e.get("start_ms"), ev)].append(e)

    exactos = con_dif = sin_par = otra_barra = 0
    por_campo = collections.Counter()
    por_evento = collections.Counter()
    ejemplos = []

    for r in orac:
        ev = _norm_evento(r[14])
        por_evento[ev] += 1
        cands = idx.get((r[1], r[15], ev))
        if not cands:
            alt = solo_campos.get((r[1], ev))
            if alt and any(all(abs(_f(r[i]) - _f(g(e))) <= TOL
                               for _, i, g in CAMPOS if _num(r[i]))
                           for e in alt):
                otra_barra += 1
            else:
                sin_par += 1
            continue
        mejor = None
        for e in cands:
            d = sum(1 for _, i, g in CAMPOS if not _igual(r[i], g(e)))
            if mejor is None or d < mejor[0]:
                mejor = (d, e)
        if mejor[0] == 0:
            exactos += 1
        else:
            con_dif += 1
            for nom, i, g in CAMPOS:
                if not _igual(r[i], g(mejor[1])):
                    por_campo[nom] += 1
                    if len(ejemplos) < 12:
                        ejemplos.append(dict(start_ms=r[1], update_ms=r[15],
                                             evento=ev, campo=nom,
                                             oraculo=r[i], espejo=g(mejor[1])))
    return dict(exactos=exactos, con_diferencia=con_dif, sin_par=sin_par,
                emparejados_en_otra_barra=otra_barra,
                diferencias_por_campo=dict(por_campo),
                eventos_del_oraculo=dict(por_evento), ejemplos=ejemplos)


def _num(v):
    return isinstance(v, (int, float))


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def _igual(a, b):
    if isinstance(a, str) or isinstance(b, str):
        return str(a).lower() == str(b).lower()
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= TOL


def correr(instrumento, parquet, tick_size, ticks_por_barra, db):
    orac = cargar_oraculo(instrumento, db)
    if not orac:
        return dict(error="el oraculo no tiene clusters para %s" % instrumento)

    t0 = min(r[15] for r in orac) * 1_000_000
    t1 = (max(r[15] for r in orac) + 60_000) * 1_000_000
    tbl = pq.read_table(parquet,
                        filters=[("ts_utc_ns", ">=", t0), ("ts_utc_ns", "<", t1)],
                        columns=["ts_utc_ns", "price_ticks", "volume"])
    ts = tbl.column("ts_utc_ns").to_numpy(zero_copy_only=False).astype("int64").tolist()
    px = tbl.column("price_ticks").to_numpy(zero_copy_only=False).astype("int64").tolist()
    vo = tbl.column("volume").to_numpy(zero_copy_only=False).astype("float64").tolist()
    if not ts:
        return dict(error="el parquet no cubre la ventana del oraculo")

    params = dict(hc.MOTOR_V2)
    eventos, zonas, barras = reproducir(ts, px, vo, tick_size, ticks_por_barra, params)
    rep = comparar(orac, eventos, tick_size)

    rep.update(
        instrumento=instrumento, parquet=str(parquet), db=str(db),
        tick_size=tick_size, ticks_por_barra=ticks_por_barra,
        oraculo_eventos=len(orac),
        oraculo_clusters=len({r[1] for r in orac}),
        ticks_leidos=len(ts), barras=len(barras), zonas_espejo=len(zonas),
        espejo_eventos=len(eventos),
        pct_exactos=round(100.0 * rep["exactos"] / len(orac), 4),
        campos_comparados=len(orac) * len(CAMPOS),
        motor=params,
        advertencia=("el oraculo se produjo por reproduccion historica, donde el `.cs` "
                     "cuenta el volumen por los DOS caminos. El certificado vale para "
                     "el objeto historico, no para el que se ve en vivo."),
    )
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrumento", default="NQ 06-26")
    ap.add_argument("--parquet", default="data/nt8/NQ_parquet/NQ_06-26_ticks.parquet")
    ap.add_argument("--tick-size", type=float, default=0.25)
    ap.add_argument("--ticks-por-barra", type=int, default=25)
    ap.add_argument("--db", default=DB)
    ap.add_argument("--out", default="data/nt8_oracles/paridad_hftclusterzones.json")
    a = ap.parse_args(argv)

    r = correr(a.instrumento, REPO / a.parquet, a.tick_size, a.ticks_por_barra, a.db)
    if "error" in r:
        print("ERROR:", r["error"])
        return 2

    print("oraculo            %8d eventos, %d clusters (%s)"
          % (r["oraculo_eventos"], r["oraculo_clusters"], a.instrumento))
    print("ticks leidos       %8d   barras %d" % (r["ticks_leidos"], r["barras"]))
    print("espejo             %8d eventos, %d zonas"
          % (r["espejo_eventos"], r["zonas_espejo"]))
    print()
    print("exactos                       %8d  (%.2f %%)"
          % (r["exactos"], r["pct_exactos"]))
    print("con diferencia de campo       %8d  <- defecto del espejo"
          % r["con_diferencia"])
    print("emparejados en OTRA barra     %8d  <- apunta al arnes, no al espejo"
          % r["emparejados_en_otra_barra"])
    print("sin par                       %8d" % r["sin_par"])
    if r["diferencias_por_campo"]:
        print("\ndiferencias por campo:")
        for k, v in sorted(r["diferencias_por_campo"].items(), key=lambda x: -x[1]):
            print("   %-20s %6d" % (k, v))
    if r["ejemplos"]:
        print("\nprimeros ejemplos:")
        for e in r["ejemplos"][:6]:
            print("   %s %-12s %-18s oraculo=%s espejo=%s"
                  % (e["update_ms"], e["evento"], e["campo"], e["oraculo"], e["espejo"]))

    out = REPO / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(r, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nescrito:", out)
    return 0 if r["con_diferencia"] == 0 and r["sin_par"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
