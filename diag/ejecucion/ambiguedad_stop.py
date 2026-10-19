# -*- coding: utf-8 -*-
"""Cuánto de la decisión de un trade la resuelve la RESOLUCIÓN del stream de
ejecución en vez del mercado.

## Por qué existe

`sim.simulate` recorre un stream de *steps*. Cuando un step contiene a la vez el
target y el stop, la spec §6.3 no adivina el orden: **gana el adverso**
(`exit_reason="stop_ambiguous"`). Es la regla conservadora correcta —el
backtest no puede fabricar un edge inventando que el favorable llegó primero—
pero tiene un costo que hasta ahora nadie midió: **cada ambigüedad es un trade
cuyo resultado lo decidió el tamaño de la barra, no el precio.**

Sobre barras m1 ese costo es sistemático y va en una sola dirección: esconde
performance. Una campaña que cierra en negativo sobre m1 puede estar cerrando
en negativo *por la resolución*.

## El patrón de oro

Con steps de tick, `low = high = last`. Para que `hit_t and hit_s` sea cierto
haría falta `last >= tgt` y `last <= stp` a la vez, o sea `tgt <= stp`, que es
falso por construcción (el target está del lado favorable). **La ambigüedad es
exactamente cero, no aproximadamente cero.** Por eso el stream de tick no es
"otra resolución más": es la respuesta contra la que se miden las demás.

## Qué se mantiene fijo

Las señales se construyen UNA vez sobre barras m1 —mismas zonas, mismos
disparos, mismos `stop_ticks`/`target_ticks`— y se simulan sobre cada stream.
Lo único que varía es la resolución de ejecución. Sin eso, cualquier diferencia
sería atribuible al cambio de señales.

## Lo que este script NO es

No reproduce CAMP-001. Usa **sus parámetros** (`defaults + min_gap_ticks=2`,
`time:1`, chart_tz ART) pero el `kernel_id` cambió desde el sellado, así que el
`config_id` es otro y estos números **no restablecen ni revisan su veredicto**.
Lo que se mide acá es una propiedad del simulador y de los datos, no un edge.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from edgelab.bridge import bars as bars_mod          # noqa: E402
from edgelab.bridge import ticks as ticks_mod        # noqa: E402
from edgelab.bridge.indicators import gaps2          # noqa: E402
from edgelab.research import camp001 as C            # noqa: E402
from edgelab.research.sim import simulate            # noqa: E402

TZ_CHART = "America/Argentina/Buenos_Aires"
TICK_VALUE_USD = 6.25
SCENARIO = "base"
PARAMS_CAMP001 = {**gaps2.DEFAULTS, "min_gap_ticks": 2}

# Resoluciones a comparar. `None` = un step por tick (patrón de oro).
RESOLUCIONES = (("tick", None), ("1s", 1), ("5s", 5), ("10s", 10),
                ("30s", 30), ("60s", 60))


def zonas_a_filas(zonas, tick_size):
    """Zonas del kernel -> el formato de fila que consume `camp001`.

    El store guarda los bordes en ENTEROS de tick; el kernel los devuelve como
    precio. Se convierte con round-half-away-from-zero, igual que `snap_to_tick`,
    y no con `int()`, que truncaría hacia cero.
    """
    out = []
    for z in zonas:
        out.append(dict(
            zone_id=z["id"],
            lower_tick=int(np.floor(z["bottom"] / tick_size + 0.5)),
            upper_tick=int(np.floor(z["top"] / tick_size + 0.5)),
            kind=z["kind"], created_ms=int(z["created_ms"]),
            ended_ms=None if z["ended_ms"] is None else int(z["ended_ms"]),
            features=json.dumps({"size_ticks": int(z["size_ticks"])})))
    return out


def _quotes(tk, idx):
    """bid/ask reales en los índices `idx`, con el mismo fallback que
    `camp001.build_steps`: quote cruzado/vacío/absurdo cae al libro de 1 tick
    alrededor del precio. Se CUENTA, no se oculta."""
    px = tk.price_ticks[idx].astype(np.int64)
    if tk.bid_ticks is None or tk.ask_ticks is None:
        return px, px + 1, 0
    bid = tk.bid_ticks[idx].astype(np.int64)
    ask = tk.ask_ticks[idx].astype(np.int64)
    bad = (bid <= 0) | (ask <= 0) | (ask <= bid) | ((ask - bid) > 10)
    if bad.any():
        bid = np.where(bad, px, bid)
        ask = np.where(bad, px + 1, ask)
    return bid, ask, int(bad.sum())


def steps_por_tick(tk):
    """Un step por tick: `low = high = last`. Ambigüedad cero por construcción."""
    n = len(tk.price_ticks)
    idx = np.arange(n)
    px = tk.price_ticks.astype(np.int64)
    bid, ask, nbad = _quotes(tk, idx)
    sid = bars_mod.session_ids(tk.ts_ns)
    ts = tk.ts_ns // 1_000_000
    ts_ = ts.tolist(); px_ = (px * tk.tick_size).tolist()
    bid_ = (bid * tk.tick_size).tolist(); ask_ = (ask * tk.tick_size).tolist()
    sid_ = sid.tolist()
    steps = [dict(ts=ts_[i], last=px_[i], bid=bid_[i], ask=ask_[i],
                  low=px_[i], high=px_[i], session_id=sid_[i])
             for i in range(n)]
    return steps, dict(n_steps=n, n_quotes_degraded=nbad, resolucion="tick")


def steps_por_segundos(tk, secs):
    """Barras de `secs` segundos, construidas acá y NO en `bars.py`.

    `bars.build_time_bars` toma minutos ENTEROS (`period = minutes*60*NS`), así
    que no puede expresar 5 s ni 10 s. Se replica su semántica localmente en vez
    de tocar el primitivo compartido: `build_time_bars` alimenta los gates de
    paridad, y ampliarlo para un diagnóstico sería mover el piso de todo lo que
    ya está en PASS.
    """
    period = int(secs) * 1_000_000_000
    bucket = tk.ts_ns // period
    corte = np.flatnonzero(np.diff(bucket)) + 1
    ini = np.concatenate(([0], corte))
    fin = np.concatenate((corte, [len(bucket)]))
    n = len(ini)
    px = tk.price_ticks
    op = np.empty(n, np.int64); hi = np.empty(n, np.int64); lo = np.empty(n, np.int64)
    for i in range(n):
        seg = px[ini[i]:fin[i]]
        op[i] = seg[0]; hi[i] = seg.max(); lo[i] = seg.min()
    bid, ask, nbad = _quotes(tk, ini)
    sid = bars_mod.session_ids(tk.ts_ns[ini])
    ts = (tk.ts_ns[ini] // 1_000_000)
    tsz = tk.tick_size
    steps = [dict(ts=int(ts[i]), last=float(op[i]) * tsz,
                  bid=float(bid[i]) * tsz, ask=float(ask[i]) * tsz,
                  low=float(lo[i]) * tsz, high=float(hi[i]) * tsz,
                  session_id=int(sid[i])) for i in range(n)]
    return steps, dict(n_steps=n, n_quotes_degraded=nbad,
                       resolucion="%ds" % secs)


def resumen(res, cost_ticks):
    t = res.trades
    n = len(t)
    if not n:
        return dict(n_trades=0)
    razones = {}
    for x in t:
        razones[x["exit_reason"]] = razones.get(x["exit_reason"], 0) + 1
    amb = razones.get("stop_ambiguous", 0)
    return dict(n_trades=n, ambiguos=amb, pct_ambiguo=100.0 * amb / n,
                neto_ticks=sum(x["neto_ticks"] for x in t),
                bruto_ticks=sum(x["bruto_ticks"] for x in t),
                razones=razones)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--parquet", default="6E_09-26_ticks.parquet")
    ap.add_argument("--contract", default="6E 09-26")
    ap.add_argument("--desde", default="2026-06-15")
    ap.add_argument("--hasta", default="2026-06-19",
                    help="exclusivo; el default cubre lun-jue de la ventana "
                         "pre-holdout ya vetada en PEDIDOS_NT8_2026-07-27")
    ap.add_argument("--familias", default="F1,F2,F3,F4")
    ap.add_argument("--out", default=os.path.join(
        REPO, "diag", "ejecucion", "ambiguedad_stop.json"))
    a = ap.parse_args(argv)

    ini = int(pd.Timestamp(a.desde, tz="UTC").value)
    fin = int(pd.Timestamp(a.hasta, tz="UTC").value)
    print("=" * 78)
    print("AMBIGUEDAD DE STOP vs RESOLUCION DEL STREAM DE EJECUCION")
    print("=" * 78)
    print("ventana %s .. %s (excl) | %s" % (a.desde, a.hasta, a.contract))

    tk = ticks_mod.load_canonical_parquet(
        os.path.join(REPO, "data", "nt8", "6E", a.parquet),
        contract=a.contract, start_utc_ns=ini, end_utc_ns=fin)
    b = bars_mod.build_time_bars(tk, 1)
    print("%d ticks | %d barras m1" % (len(tk.price_ticks), len(b)))

    z = gaps2.run(tk, b, params=PARAMS_CAMP001, chart_tz=TZ_CHART)["zones"]
    filas = zonas_a_filas(z, tk.tick_size)
    cache = C.precompute_triggers(filas, b)
    print("%d zonas | %d con disparo" % (len(filas), len(cache)))

    # Las señales se construyen UNA vez, sobre m1, y NO se vuelven a tocar.
    steps_m1, info_m1 = C.build_steps(tk, b)
    familias = [f.strip() for f in a.familias.split(",") if f.strip()]
    grid = [g for g in C.expand_grid() if g["family"] in familias]
    print("%d celdas de grilla | quotes degradados m1=%d\n"
          % (len(grid), info_m1["n_quotes_degraded"]))

    streams = {}
    for nombre, secs in RESOLUCIONES:
        t0 = time.time()
        s, info = (steps_por_tick(tk) if secs is None
                   else steps_por_segundos(tk, secs))
        streams[nombre] = s
        print("  stream %-5s %8d steps  (%.1fs)" % (nombre, info["n_steps"],
                                                    time.time() - t0))

    cost = C.cost_round_turn(SCENARIO, TICK_VALUE_USD)
    out = {}
    print("\n%-22s %-6s %7s %7s %8s %11s" % (
        "config", "res", "trades", "ambig", "%ambig", "neto_ticks"))
    print("-" * 70)
    for g in grid:
        sigs, _ = C.signals_from_cache(
            cache, b, steps_m1, g["family"], g["zone_min_size"],
            g["stop_pad"], g["target_R"], g["time_stop_bars"],
            tk.tick_size, SCENARIO)
        if not sigs:
            continue
        fila = {}
        for nombre, _s in RESOLUCIONES:
            r = simulate(sigs, streams[nombre], scenario=SCENARIO,
                         tick_size=tk.tick_size, tick_value=TICK_VALUE_USD,
                         close_at_session_end=True, check_guard=False)
            fila[nombre] = resumen(r, cost["total_ticks"])
            m = fila[nombre]
            if m["n_trades"]:
                print("%-22s %-6s %7d %7d %7.1f%% %11.2f" % (
                    g["config_id"], nombre, m["n_trades"], m["ambiguos"],
                    m["pct_ambiguo"], m["neto_ticks"]))
        out[g["config_id"]] = fila
        print("-" * 70)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(dict(ventana=[a.desde, a.hasta], contrato=a.contract,
                   params=PARAMS_CAMP001, chart_tz=TZ_CHART,
                   escenario=SCENARIO, resultados=out),
              open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\nartefacto: %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
