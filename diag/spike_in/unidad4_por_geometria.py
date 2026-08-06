# -*- coding: utf-8 -*-
"""UNIDAD 4 -- MDE POR GEOMETRIA. Cierra la objecion (a).

El 1,14 ticks reportado es AGREGADO sobre 40 geometrias cuyo break-even va de
4,89 a 54,70 ticks. "Cero geometrias ciegas" no se sigue de un numero agregado:
una geometria de barreras anchas tiene varianza POR TRADE mucho mayor que la
mezcla, asi que su MDE puede ser varias veces el agregado.

Este script emite las 40 filas. Para eso hace falta la varianza por trade de
cada geometria, que las corridas anteriores no persistieron (guardaban sumas,
no sumas de cuadrados). Se re-corre acumulando sum(x) y sum(x^2) por dia.

Estadistico: expectativa neta en TICKS por ancla (el primario).
Umbral: la friccion de 2,704 ticks, DIRECTO -- no el lift 2,704/(P+N), que es
el umbral del estadistico de TASA y no aplica acá.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from spike_in import (A0, CFG, DATA_DIR, dias_del_atlas_sellado,  # noqa: E402
                      geometrias)

RONDAS = int(os.environ.get("SPIKE_RONDAS", "25"))
# FUENTE UNICA (2026-08-06): antes era `2.704` hardcodeado, y actualizar la
# comision real de Lucid no lo tocaba. Da 2,768 con $2,40/pata.
from edgelab.research.costs import friccion_rt_ticks  # noqa: E402
FRICCION = friccion_rt_ticks()


def procesar(args):
    """Por dia y geometria: n, sum(ticks), sum(ticks^2) del nulo (m=0)."""
    archivo, contrato, fecha, data_dir, ronda = args
    try:
        import duckdb
        from zoneinfo import ZoneInfo
        CT = ZoneInfo("America/Chicago")
        p = os.path.join(data_dir, archivo).replace("\\", "/")
        d0 = datetime.strptime(fecha, "%Y-%m-%d").replace(tzinfo=CT)
        a = int(d0.timestamp() * 1e9)
        b = int((d0 + timedelta(days=1)).timestamp() * 1e9)
        con = duckdb.connect()
        df = con.execute(
            "select ts_utc_ns, price_ticks from read_parquet('%s') "
            "where ts_utc_ns>=%d and ts_utc_ns<%d order by ts_utc_ns" % (p, a, b)).df()
        if len(df) < 5000:
            return None
        ts = df.ts_utc_ns.values.astype(np.int64)
        px = df.price_ticks.values.astype(np.int64)
        del df

        hmax = max(CFG["horizontes_min"])
        sep_ns = CFG["sep_min_minutos"] * 60 * 10**9
        vol_ns = CFG["vol_lookback_min"] * 60 * 10**9
        r = A0._rng(CFG["seed"], contrato, fecha, "anclas", ronda)
        t_lo, t_hi = int(ts[0]) + vol_ns, int(ts[-1]) - hmax * 60 * 10**9
        if t_hi <= t_lo:
            return None
        cand = np.sort(r.integers(t_lo, t_hi, size=CFG["anclas_por_dia"] * 4))
        anclas, ultimo = [], None
        for t in cand:
            t = int(t)
            if ultimo is None or t - ultimo >= sep_ns:
                anclas.append(t); ultimo = t
            if len(anclas) >= CFG["anclas_por_dia"]:
                break
        if not anclas:
            return None

        acc = {g: [0, 0.0, 0.0] for g in geometrias()}   # n, sum, sumsq
        idx = np.searchsorted(ts, anclas, side="right") - 1
        for k, i in enumerate(idx):
            if i < 1:
                continue
            t0, p0 = int(ts[i]), int(px[i])
            j = np.searchsorted(ts, t0 - vol_ns, side="left")
            if i - j < 50:
                continue
            rd = A0._rng(CFG["seed"], contrato, fecha, ronda, k)
            direccion = 1 if rd.integers(0, 2) == 0 else -1
            for H in CFG["horizontes_min"]:
                e = np.searchsorted(ts, t0 + H * 60 * 10**9, side="right")
                fut = px[i + 1:e]
                if len(fut) == 0:
                    continue
                delta = (fut - p0) * direccion
                for (P, N) in CFG["pares_pn"]:
                    g = "H%d_P%d_N%d" % (H, P, N)
                    fav = np.flatnonzero(delta >= P)
                    adv = np.flatnonzero(delta <= -N)
                    f0 = int(fav[0]) if len(fav) else -1
                    a0 = int(adv[0]) if len(adv) else -1
                    if f0 < 0 and a0 < 0:
                        tk = float(delta[-1])
                    elif a0 < 0 or (f0 >= 0 and f0 < a0):
                        tk = float(P)
                    else:
                        tk = float(-N)
                    c = acc[g]
                    c[0] += 1; c[1] += tk; c[2] += tk * tk
        return dict(fecha=fecha, acc=acc)
    except Exception:
        return None


def main():
    import multiprocessing as mp
    dias, _ = dias_del_atlas_sellado()
    tareas = [(ar, co, f, DATA_DIR, rd) for (ar, co, f) in dias for rd in range(RONDAS)]
    tot = {g: {} for g in geometrias()}
    t0 = time.time()
    with mp.Pool(max(1, min(mp.cpu_count() - 2, 10))) as pool:
        for n, res in enumerate(pool.imap_unordered(procesar, tareas, chunksize=4)):
            if not res:
                continue
            for g, (c, s, sq) in res["acc"].items():
                d = tot[g].setdefault(res["fecha"], [0, 0.0, 0.0])
                d[0] += c; d[1] += s; d[2] += sq
            if (n + 1) % 1000 == 0:
                print("   %d/%d (%.0fs)" % (n + 1, len(tareas), time.time() - t0), flush=True)
    json.dump(tot, open(os.path.join(AQUI, "por_geom_nulo.json"), "w"), separators=(",", ":"))
    return tot


if __name__ == "__main__":
    main()
