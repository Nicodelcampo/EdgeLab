#!/usr/bin/env python3
"""Paridad del motor de zonas HFT: NT8 (`.cs`) contra el espejo Python.

## Estimand declarado

*Fracción de zonas del oráculo que el espejo reproduce con **los veinte campos
idénticos**, emparejadas por `(start_ms, end_ms, dir)`.*

No es "cuántas zonas encuentra cada uno": eso mediría otra cosa. Se toma el oráculo
como población y se pregunta si el espejo la reproduce.

## Por qué la clave lleva `dir`

Con `(start_ms, end_ms)` sola, el 2,8 % de las zonas colisiona: hay zonas que nacen y
mueren **dentro del mismo milisegundo** (208 de 7.494 en la ventana de referencia, con
hasta 189 ticks en ese milisegundo). Dos zonas distintas —una bajista y una alcista— en
el mismo milisegundo se emparejaban cruzadas y aparecían como seis diferencias que no
existían. La dirección las separa.

## Limitación del oráculo, no del espejo

La tabla `hft_zones` tiene `UNIQUE(instrument, start_ts)` con `INSERT OR IGNORE`, y
`start_ts` está en milisegundos. **Dos zonas que arrancan en el mismo milisegundo: la
segunda se descarta en silencio.** Por eso el espejo produce ~30 zonas que el oráculo
no tiene. No son falsos positivos: son zonas que la base no puede representar.

La consecuencia práctica es que el oráculo mide **cobertura**, no igualdad de conteo.
Para verificar el conteo haría falta que el `.cs` emitiera un id monotónico por zona o
un timestamp sub-ms.

    .venv\\Scripts\\python tools\\paridad_hftzones_nq.py --instrumento "ES 09-26" \\
        --parquet data/nt8/ES_parquet/ES_09-26_ticks.parquet
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

from edgelab.bridge.indicators import hftzones_nq as hz  # noqa: E402

DB = "C:/LoggerHFT/data/hft_logger_v4.sqlite"

COLS = ("start_ts,end_ts,dir,price_lower,price_upper,valid_steps,pasos,avg_ms,"
        "total_ms,vol_rate,total_vol,height_ticks,max_retro,cvd_sweep,buy_vol,"
        "sell_vol,delta_slope,delta_first,delta_second,max_tick_vol,no_move_ticks,"
        "no_move_vol,max_level_ticks")

# (nombre, indice en la fila del oraculo, cómo sacarlo del espejo)
CAMPOS = [
    ("price_lower", 3, lambda c, tk: c["sw_lo_tk"] * tk),
    ("price_upper", 4, lambda c, tk: c["sw_hi_tk"] * tk),
    ("valid_steps", 5, lambda c, tk: c["valid_steps"]),
    ("pasos", 6, lambda c, tk: c["pasos"]),
    ("avg_ms", 7, lambda c, tk: c["avg_ms"]),
    ("total_ms", 8, lambda c, tk: c["total_ms"]),
    ("vol_rate", 9, lambda c, tk: c["vol_rate"]),
    ("total_vol", 10, lambda c, tk: c["total_vol"]),
    ("height_ticks", 11, lambda c, tk: c["height_ticks"]),
    ("max_retro", 12, lambda c, tk: c["max_retro_ticks"]),
    ("cvd_sweep", 13, lambda c, tk: c["cvd"]),
    ("buy_vol", 14, lambda c, tk: c["buy_vol"]),
    ("sell_vol", 15, lambda c, tk: c["sell_vol"]),
    ("delta_slope", 16, lambda c, tk: c["delta_slope"]),
    ("delta_first", 17, lambda c, tk: c["delta_first"]),
    ("delta_second", 18, lambda c, tk: c["delta_second"]),
    ("max_tick_vol", 19, lambda c, tk: c["max_tick_vol"]),
    ("no_move_ticks", 20, lambda c, tk: c["no_move_ticks"]),
    ("no_move_vol", 21, lambda c, tk: c["no_move_vol"]),
    ("max_level_ticks", 22, lambda c, tk: c["max_level_ticks"]),
]

TOL = 1e-6


def cargar_oraculo(instrumento, db=DB):
    con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    filas = con.execute("select %s from hft_zones where instrument=?" % COLS,
                        (instrumento,)).fetchall()
    con.close()
    return filas


def gates_coherentes(filas):
    """Chequeo previo: ¿todas las filas cumplen los umbrales default?

    La base no guarda con qué parámetros se corrió. Esto no prueba que fueran los
    defaults —una configuración más estricta también los cumpliría— pero una sola
    violación probaría que NO lo eran, y ahí la comparación no tendría sentido.
    """
    d = hz.ACCEPT_DEFAULTS
    mal = 0
    for r in filas:
        if (r[7] > d["max_avg_ms"] or r[8] > d["max_total_ms"]
                or r[9] < d["min_volume_rate"] or r[10] < d["min_total_volume"]):
            mal += 1
    return mal


def correr(instrumento, parquet, tick_size, db=DB):
    orac = cargar_oraculo(instrumento, db)
    if not orac:
        return dict(error="el oraculo no tiene zonas para %s" % instrumento)

    viol = gates_coherentes(orac)
    t0 = min(r[0] for r in orac) * 1_000_000
    t1 = (max(r[1] for r in orac) + 1000) * 1_000_000

    tbl = pq.read_table(parquet,
                        filters=[("ts_utc_ns", ">=", t0), ("ts_utc_ns", "<", t1)],
                        columns=["ts_utc_ns", "price_ticks", "volume"])
    ts = tbl.column("ts_utc_ns").to_numpy(zero_copy_only=False).astype("int64").tolist()
    px = tbl.column("price_ticks").to_numpy(zero_copy_only=False).astype("int64").tolist()
    vo = tbl.column("volume").to_numpy(zero_copy_only=False).astype("float64").tolist()
    if not ts:
        return dict(error="el parquet no cubre la ventana del oraculo")

    # Umbrales CERTIFICADOS, fijados explicitamente. No se heredan de los defaults del
    # modulo: si manana alguien mueve un default, este validador tiene que seguir
    # comparando contra la misma configuracion con la que se emitio el certificado, o
    # el resultado deja de significar lo que el documento dice que significa.
    espejo, _ = hz.accept_all(hz.detect_candidates(ts, px, vo),
                              dict(hz.ACCEPT_DEFAULTS), tick_size=tick_size)

    idx = collections.defaultdict(list)
    for c in espejo:
        idx[(c["ts_start"] // 1_000_000, c["ts_end"] // 1_000_000, c["direction"])].append(c)

    exactas = con_dif = sin_par = 0
    por_campo = collections.Counter()
    ejemplos = []
    for r in orac:
        cands = idx.get((r[0], r[1], r[2]))
        if not cands:
            sin_par += 1
            continue
        mejor = None
        for c in cands:
            d = sum(1 for _, i, g in CAMPOS
                    if abs(float(r[i]) - float(g(c, tick_size))) > TOL)
            if mejor is None or d < mejor[0]:
                mejor = (d, c)
        if mejor[0] == 0:
            exactas += 1
        else:
            con_dif += 1
            for nom, i, g in CAMPOS:
                v = g(mejor[1], tick_size)
                if abs(float(r[i]) - float(v)) > TOL:
                    por_campo[nom] += 1
                    if len(ejemplos) < 10:
                        ejemplos.append(dict(start_ms=r[0], campo=nom,
                                             oraculo=r[i], espejo=v))

    ms_ocupados = collections.Counter(r[0] for r in orac)
    extras = [k for k in idx if ms_ocupados.get(k[0], 0) > 0
              and (k[0], k[1]) not in {(r[0], r[1]) for r in orac}]

    return dict(
        instrumento=instrumento, parquet=str(parquet), tick_size=tick_size,
        oraculo_zonas=len(orac), violaciones_de_gate=viol,
        ticks_leidos=len(ts), espejo_zonas=len(espejo),
        exactas=exactas, con_diferencia=con_dif, sin_par=sin_par,
        pct_exactas=round(100.0 * exactas / len(orac), 4),
        campos_comparados=len(orac) * len(CAMPOS),
        diferencias_por_campo=dict(por_campo), ejemplos=ejemplos,
        zonas_duracion_0ms=sum(1 for r in orac if r[0] == r[1]),
        espejo_sin_lugar_en_el_oraculo=len(extras),
        defaults=hz.ACCEPT_DEFAULTS,
    )


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrumento", default="ES 09-26")
    ap.add_argument("--parquet", default="data/nt8/ES_parquet/ES_09-26_ticks.parquet")
    ap.add_argument("--tick-size", type=float, default=0.25)
    ap.add_argument("--db", default=DB)
    ap.add_argument("--out", default="data/nt8_oracles/paridad_hftzones_nq.json")
    a = ap.parse_args(argv)

    r = correr(a.instrumento, REPO / a.parquet, a.tick_size, a.db)
    if "error" in r:
        print("ERROR:", r["error"])
        return 2

    print(f"oraculo            {r['oraculo_zonas']:>8,} zonas ({a.instrumento})")
    print(f"violaciones gate   {r['violaciones_de_gate']:>8,}   "
          f"(>0 = la corrida no uso los defaults)")
    print(f"ticks leidos       {r['ticks_leidos']:>8,}")
    print(f"espejo             {r['espejo_zonas']:>8,} zonas")
    print(f"EXACTAS 20 campos  {r['exactas']:>8,}   {r['pct_exactas']}%")
    print(f"con diferencia     {r['con_diferencia']:>8,}")
    print(f"sin par            {r['sin_par']:>8,}")
    if r["diferencias_por_campo"]:
        print("campos:", r["diferencias_por_campo"])

    out = REPO / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(r, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("escrito:", out)
    return 0 if (r["con_diferencia"] == 0 and r["sin_par"] == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
