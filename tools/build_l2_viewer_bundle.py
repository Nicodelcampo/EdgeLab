#!/usr/bin/env python3
r"""Bundle de visor con PROFUNDIDAD L2 de una sesion: heatmap del libro (Bookmap-like) + cinta de trades + velas.

**Target-free. Solo visualizacion / estructura del libro.** Sin retornos, sin senales, sin outcomes.

Entrada: parquets canonicos `l1_quotes` y `l2_depth` de una sesion (`edgelab_schema nt8_l2_depth_v2`).
Reconstruye el libro por posicion (MBP de 10 niveles) aplicando cada evento de L2 en el orden de `source_row`:
    operation 0 = alta  -> inserta en `level` y corre lo de abajo
    operation 1 = cambio-> fija precio/tamano en `level`
    operation 2 = baja  -> elimina `level` y sube lo de abajo
    side 0 = ask, side 1 = bid (enum MarketDataType de NT8)
y saca una foto del libro cada `--snap-seconds` segundos (defecto 1s: resolucion Bookmap-like).

CINTA DE TRADES (Bookmap-like). Cada ejecucion (L1 `side=2`) se clasifica por agresor comparando su precio contra
el mejor bid/ask del libro reconstruido EN ESE INSTANTE (regla de cotizacion: precio >= ask -> compra agresiva,
precio <= bid -> venta agresiva; si el libro esta vacio o el precio cae adentro del spread, se usa la regla de tick
contra el trade anterior; si tampoco resuelve, queda NEUTRAL). **Es una clasificacion HEURISTICA**: no hay campo de
agresor en el feed y no se valido contra un oraculo. Se publica en `meta.trade_classification` la fraccion de cada
clase para que quede auditable. Los trades se AGREGAN por (celda de `snap_seconds`, precio) en compra/venta/neutral
antes de publicarse: dibujar cada ejecucion individual satura la pantalla quicando hay muchas por segundo (se
solapan y forman bloques solidos sin informacion); agregados, el tamano de la burbuja diferencia de verdad.

DETECTORES PROVISIONALES (iceberg / spoofing). Ver `edgelab/research/l2_manipulation_heuristics.py` para la
definicion exacta de cada heuristica y sus limites. Se publican en `manipulation.icebergs` / `manipulation.spoofs`.

RELOJ. `ts_us` es la hora de pared de NT8 leida como UTC y su referencia NO esta resuelta contra los ticks
(edgelab/data/l2.py, CORRECCION_ESQUEMA_L1_ES_SEP26). Por eso las velas se arman con los trades (L1 `side=2`) del
MISMO archivo, que comparte reloj con el libro. Nunca se une por cercania de timestamp con los bundles de ticks.

HOLDOUT. Se rechazan sesiones con fecha >= 20260630 (el reloj no esta resuelto: se corta con margen).

Validacion incluida: cada cotizacion L1 (mejor bid/ask) se compara con el tope del libro reconstruido y se publica
la tasa en `meta.book_validation`. En el feed la L1 llega ANTES de las filas L2 que la producen, asi que se evalua con
el libro tras la rafaga L2 que la sigue (comparar antes daba ~51 %, un artefacto del orden, no del libro).

    .venv\Scripts\python tools\build_l2_viewer_bundle.py --base E:\DatosNT8\gc_aug26_canonical_parquets --date 20260615 ^
        --instrument GC --contract "GC 08-26" --out viewer\nt8_bridge\bundles
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.research.l2_manipulation_heuristics import (  # noqa: E402
    IcebergTracker, SpoofTracker, large_size_thresholds)

LAST_SIDE, ASK, BID = 2, 0, 1
CUTOFF_DATE = 20260630
PRICE_PRECISION = {"GC": 1, "6E": 5, "ES": 2, "NQ": 2}
CANDLE_BUCKETS = {"time_5s": 5, "time_1m": 60}


def apply_l2(book, side_book, op, lvl, tick, size):
    """Aplica un evento a la lista de un lado (posicion 0 = mejor precio)."""
    if op == 0:                                   # alta
        if lvl > len(side_book):
            lvl = len(side_book)
        side_book.insert(lvl, [tick, size])
    elif op == 1:                                 # cambio
        if lvl < len(side_book):
            side_book[lvl] = [tick, size]
        else:
            side_book.append([tick, size])
    elif op == 2:                                 # baja
        if lvl < len(side_book):
            del side_book[lvl]


def classify_aggressor(price_tick, bid_tick, ask_tick, prev_trade_tick):
    """Regla de cotizacion (Lee-Ready simplificada) + tick-test de respaldo. +1 compra agresiva, -1 venta agresiva, 0 neutral."""
    if ask_tick is not None and price_tick >= ask_tick:
        return 1
    if bid_tick is not None and price_tick <= bid_tick:
        return -1
    if prev_trade_tick is not None:
        if price_tick > prev_trade_tick:
            return 1
        if price_tick < prev_trade_tick:
            return -1
    return 0


def bin_candles(ts_list, px_list, sz_list, bucket_seconds):
    cand = {}
    for ts, px, sz in zip(ts_list, px_list, sz_list):
        k = ts - ts % bucket_seconds
        c = cand.get(k)
        if c is None:
            cand[k] = [px, px, px, px, sz]
        else:
            if px > c[1]: c[1] = px
            if px < c[2]: c[2] = px
            c[3] = px; c[4] += sz
    return [{"time": k, "open": v[0], "high": v[1], "low": v[2], "close": v[3], "volume": float(v[4])}
            for k, v in sorted(cand.items())]


#  Calibrados a mano por barrido sobre GC 08-26 2026-06-15 (3.921.238 eventos L2). Con menos exigencia, el
#  "candidato" mas comun es simplemente el touch siendo tradeado y re-cotizado todo el dia (miles por sesion,
#  sin informacion: es como quedan las cifras "en crudo", antes de filtrar por cercania y tamano notable):
#    large_size_pctl=95  -> spoofs sin filtro de cercania: miles (thr ~6 lotes: "grande" era casi cualquier orden)
#    large_size_pctl=99.9, near_ticks=5, sin filtro de tamano en iceberg -> ~1.300 icebergs (el touch se re-cotiza
#      dentro de una sesion HFT cientos de veces sin que eso sea un iceberg real)
#    + min_avg_size (p90 del lado) + refill_min_ratio=0.85 -> ~5-25 icebergs por sesion (rango medido en las 29
#      sesiones de GC 08-26 pre-holdout: 4-65)
#    + near_ticks=3, max_lifetime_s=5, max_fill_ratio=0.15 -> ~20-300 spoofs por sesion (mismo rango de 29 sesiones)
#  Sigue siendo mucho volumen para heuristicas sin ground truth: la calibracion baja el ruido obvio (re-cotizado
#  rutinario del touch), no certifica que lo que queda sea manipulacion real.
DEFAULT_LARGE_SIZE_PCTL = 99.9                 # "grande" = percentil 99.9 del lado (excluye a casi todo el ruido)
DEFAULT_ICEBERG_KWARGS = dict(min_refills=5, refill_min_ratio=0.85, near_ticks=5)
DEFAULT_SPOOF_KWARGS = dict(max_lifetime_s=5, max_fill_ratio=0.15, near_ticks=3)
ICEBERG_MIN_AVG_SIZE_PCTL = 90.0                # ademas, el nivel que se rellena debe ser notablemente grande


def build(l1_path: Path, l2_path: Path, snap_seconds: int, tick_size: float, *,
         iceberg_kwargs: dict | None = None, spoof_kwargs: dict | None = None,
         large_size_pctl: float = DEFAULT_LARGE_SIZE_PCTL):
    l1 = pq.read_table(l1_path).to_pandas().sort_values("source_row", kind="stable")
    l2 = pq.read_table(l2_path).to_pandas().sort_values("source_row", kind="stable")

    tr = l1[l1.side == LAST_SIDE]
    tr_ts, tr_px, tr_sz = (tr.ts_us // 1_000_000).tolist(), tr.price.tolist(), tr["size"].tolist()
    bar_series = {k: bin_candles(tr_ts, tr_px, tr_sz, secs) for k, secs in CANDLE_BUCKETS.items()}

    # ---- recorrido unico por source_row: aplica L2 al libro, valida cotizaciones L1, clasifica trades L1,
    # agrega trades por (celda de tiempo, precio) para la cinta de burbujas, y alimenta los detectores provisionales
    bids, asks = [], []
    r_l2 = l2.source_row.to_numpy()
    side, op, lvl = l2.side.tolist(), l2.operation.tolist(), l2.level.tolist()
    tick, size, ts = l2.price_tick.tolist(), l2["size"].tolist(), (l2.ts_us // 1_000_000).tolist()

    l1_side = l1.side.tolist(); l1_row = l1.source_row.to_numpy(); l1_tick = l1.price_tick.tolist()
    l1_size = l1["size"].tolist(); l1_ts = (l1.ts_us // 1_000_000).tolist()
    li, n1 = 0, len(l1_row)
    match = dict(bid=[0, 0], ask=[0, 0])
    crossed = 0
    snap_t, snap_off, cell_tick, cell_size = [], [], [], []      # cell_size: + bid / - ask
    trade_cells = {}                                             # (bucket,tick) -> [buy, sell, neutral]
    last_bucket = None
    pending = None                                  # cotizacion L1 pendiente de validar (ver nota de orden)
    prev_trade_tick = None
    side_counts = {1: 0, -1: 0, 0: 0}

    side_a, op_a, size_a = np.asarray(side), np.asarray(op), np.asarray(size, dtype=float)
    thresholds = large_size_thresholds(side_a, op_a, size_a, large_size_pctl)
    ice_kwargs = dict(DEFAULT_ICEBERG_KWARGS, min_avg_size=large_size_thresholds(side_a, op_a, size_a, ICEBERG_MIN_AVG_SIZE_PCTL))
    ice_kwargs.update(iceberg_kwargs or {})
    spf_kwargs = dict(DEFAULT_SPOOF_KWARGS)
    spf_kwargs.update(spoof_kwargs or {})
    iceberg = IcebergTracker(**ice_kwargs)
    spoof = SpoofTracker(thresholds, **spf_kwargs)

    def check_quote(j):
        book = bids if l1_side[j] == BID else asks
        if book:
            key = "bid" if l1_side[j] == BID else "ask"
            match[key][1] += 1
            match[key][0] += int(book[0][0] == l1_tick[j])

    def dump(bucket):
        snap_t.append(bucket * snap_seconds)
        snap_off.append(len(cell_tick))
        for t, s in bids:
            cell_tick.append(t); cell_size.append(s)
        for t, s in asks:
            cell_tick.append(t); cell_size.append(-s)

    def handle_l1_row(j, pend, prev_tick):
        """Clasifica un trade, o difiere una cotizacion ASK/BID para validar tras la rafaga L2 que la produce.
        Otros codigos de `side` (3,4,5,6,7,8: estadisticas de sesion, volumen diario, etc.) se ignoran: no son
        ni ejecuciones ni el mejor bid/ask del libro."""
        if l1_side[j] == LAST_SIDE:
            b = bids[0][0] if bids else None
            a = asks[0][0] if asks else None
            d = classify_aggressor(l1_tick[j], b, a, prev_tick)
            side_counts[d] += 1
            tk, sz, tsj = l1_tick[j], l1_size[j], l1_ts[j]
            key = (tsj - tsj % snap_seconds, tk)
            cell = trade_cells.get(key)
            if cell is None:
                trade_cells[key] = cell = [0.0, 0.0, 0.0]
            cell[0 if d > 0 else (1 if d < 0 else 2)] += sz
            iceberg.on_trade(tk, tsj, d)
            spoof.on_trade(tk, tsj, sz, d)
            return j + 1, pend, tk
        if l1_side[j] in (ASK, BID):
            if pend is not None:                # la L1 llega ANTES de las filas L2 que la producen: se evalua
                check_quote(pend)                # con el libro tras la rafaga L2 que la sigue
            return j + 1, j, prev_tick
        return j + 1, pend, prev_tick

    for i in range(len(r_l2)):
        bucket = ts[i] // snap_seconds
        if last_bucket is None:
            last_bucket = bucket
        elif bucket != last_bucket:
            dump(last_bucket)                   # estado al cierre del bucket anterior
            last_bucket = bucket
        while li < n1 and l1_row[li] < r_l2[i]:  # filas L1 anteriores a este evento L2
            li, pending, prev_trade_tick = handle_l1_row(li, pending, prev_trade_tick)
        apply_l2(None, asks if side[i] == ASK else bids, op[i], lvl[i], tick[i], size[i])
        if side[i] == BID:
            depth = (bids[0][0] - tick[i]) if bids else None
        else:
            depth = (tick[i] - asks[0][0]) if asks else None
        iceberg.on_l2_event(side[i], op[i], tick[i], size[i], ts[i], depth)
        spoof.on_l2_event(side[i], op[i], tick[i], size[i], ts[i], depth)
        if bids and asks and bids[0][0] >= asks[0][0]:
            crossed += 1
    while li < n1:                              # filas L1 despues del ultimo evento L2
        li, pending, prev_trade_tick = handle_l1_row(li, pending, prev_trade_tick)
    if pending is not None:
        check_quote(pending)
    if last_bucket is not None:
        dump(last_bucket)
    snap_off.append(len(cell_tick))
    validation = dict(
        best_bid_match=match["bid"][0] / max(1, match["bid"][1]), best_bid_checks=match["bid"][1],
        best_ask_match=match["ask"][0] / max(1, match["ask"][1]), best_ask_checks=match["ask"][1],
        crossed_book_events=crossed, l2_events=len(r_l2))
    n_tr = max(1, len(tr))
    trade_classification = dict(buy_aggressor=side_counts[1] / n_tr, sell_aggressor=side_counts[-1] / n_tr,
                                neutral=side_counts[0] / n_tr, method="quote_rule_then_tick_test_HEURISTIC_UNVALIDATED")
    l2b = dict(snap_seconds=snap_seconds, tick_size=tick_size, t=snap_t, off=snap_off, tick=cell_tick, size=cell_size)

    tc_t, tc_off, tc_tick, tc_buy, tc_sell, tc_neu = [], [], [], [], [], []
    for key in sorted(trade_cells):
        bucket_ts, tk = key
        buy, sell, neu = trade_cells[key]
        if not tc_t or tc_t[-1] != bucket_ts:
            tc_t.append(bucket_ts); tc_off.append(len(tc_tick))
        tc_tick.append(tk); tc_buy.append(buy); tc_sell.append(sell); tc_neu.append(neu)
    tc_off.append(len(tc_tick))
    trades = dict(snap_seconds=snap_seconds, t=tc_t, off=tc_off, tick=tc_tick, buy=tc_buy, sell=tc_sell, neutral=tc_neu)

    def to_price(cands, keys):
        out = []
        for c in cands:
            c = dict(c)
            c["price"] = c["tick"] * tick_size
            out.append({k: c[k] for k in keys})
        return out

    _all_ice = iceberg.candidates(); _all_spf = spoof.candidates()
    icebergs = sorted(_all_ice, key=lambda c: -c["refills"])[:300]
    spoofs = sorted(_all_spf, key=lambda c: c["filled_ratio"])[:300]
    manipulation = dict(
        icebergs=to_price(icebergs, ("side", "price", "first_ts", "last_ts", "refills", "avg_size")),
        spoofs=to_price(spoofs, ("side", "price", "born_ts", "death_ts", "peak_size", "filled_ratio")),
        large_size_threshold_ask=thresholds[ASK], large_size_threshold_bid=thresholds[BID],
        raw_iceberg_count=len(_all_ice), raw_spoof_count=len(_all_spf),
        method="PROVISIONAL_HEURISTIC_UNVALIDATED_NO_ORDER_ID (ver edgelab/research/l2_manipulation_heuristics.py)")

    return bar_series, l2b, trades, validation, trade_classification, manipulation, dict(
        trades=len(tr), l2_events=len(l2), first_ts=int(l2.ts_us.min() // 1_000_000), last_ts=int(l2.ts_us.max() // 1_000_000))


def register(out_dir: Path, bundle: dict) -> bool:
    """Alta/actualizacion de la sesion en `bundles/manifest.js` (catalogo del visor) si ese archivo existe."""
    mf = out_dir / "manifest.js"
    if not mf.exists():
        return False
    txt = mf.read_text(encoding="utf-8")
    cat = json.loads(txt[txt.index("["):txt.rindex("]") + 1])
    m = bundle["meta"]
    entry = dict(id=m["id"], name=f"{m['contract']}", group=f"Profundidad L2 {m['instrument']}", instrument=m["instrument"],
                 contract=m["contract"], tick_size=m["tick_size"], precision=m["precision"], candles=m["n_candles"],
                 zones=0, rolls=0, parity_status="PARITY_ABSTAIN", kind=m["kind"])
    cat = [e for e in cat if e.get("id") != entry["id"]] + [entry]
    mf.write_text("window.ASSET_CATALOG = " + json.dumps(cat, indent=2, ensure_ascii=False) + ";\n", encoding="utf-8")
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True, help="carpeta con l1_quotes/, l2_depth/ y manifests/")
    ap.add_argument("--date", required=True, help="yyyymmdd")
    ap.add_argument("--instrument", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--snap-seconds", type=int, default=1, help="resolucion del heatmap (Bookmap-like). Defecto 1s.")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if int(a.date) >= CUTOFF_DATE:
        raise SystemExit(f"sesion {a.date} >= {CUTOFF_DATE}: fuera del limite pre-holdout (el reloj L2 no esta resuelto)")
    man = json.loads((a.base / "manifests" / f"{a.date}.manifest.json").read_text(encoding="utf-8"))
    tick_size = float(man["conversion"]["tick_size"])
    bar_series, l2b, trades, val, trclass, manip, info = build(
        a.base / "l1_quotes" / f"{a.date}.parquet", a.base / "l2_depth" / f"{a.date}.parquet", a.snap_seconds, tick_size)
    aid = f"{a.instrument}_L2_{a.date}"
    n_candles = len(bar_series["time_5s"])
    bundle = {
        "meta": dict(id=aid, instrument=a.instrument, contract=f"{a.contract} L2 {a.date}", tick_size=tick_size,
                     precision=PRICE_PRECISION.get(a.instrument, 2), chart_tz="UTC (reloj NT8, referencia sin resolver)",
                     n_candles=n_candles, n_zones=0, rolls=[], kind="L2_DEPTH_SESSION",
                     clock="NT8_WALL_CLOCK_INTERPRETED_AS_UTC_REFERENCE_UNRESOLVED", outcome_firewall="ENFORCED",
                     source=dict(l1=str(a.base / "l1_quotes" / f"{a.date}.parquet"), l2=str(a.base / "l2_depth" / f"{a.date}.parquet")),
                     book_validation=val, trade_classification=trclass, manipulation_summary=dict(
                         icebergs=len(manip["icebergs"]), spoofs=len(manip["spoofs"])), **info),
        "bar_series": {
            "time_5s": {"kind": "time_5s", "name": "5 Segundos (trades L1 del feed L2)", "param": 5, "candles": bar_series["time_5s"]},
            "time_1m": {"kind": "time_1m", "name": "1 Minuto (trades L1 del feed L2)", "param": 1, "candles": bar_series["time_1m"]},
        },
        "runs": [{"id": "l2_depth_stub", "name": "Profundidad L2 (sin zonas)", "indicator": "L2Depth", "bar_key": "time_5s",
                  "has_oracle": False, "zones": [], "parity": {"status": "PARITY_ABSTAIN", "gate": "PARITY_ABSTAIN"}, "params": {}}],
        "l2": l2b,
        "trades": trades,
        "manipulation": manip,
    }
    a.out.mkdir(parents=True, exist_ok=True)
    p = a.out / f"{aid}.json"
    p.write_text(json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
    registered = register(a.out, bundle)
    print(json.dumps(dict(asset_id=aid, registered=registered, bytes=p.stat().st_size, candles=n_candles, snapshots=len(l2b["t"]),
                          cells=len(l2b["tick"]), trade_cells=len(trades["tick"]), trade_classification=trclass,
                          icebergs=len(manip["icebergs"]), spoofs=len(manip["spoofs"]), validation=val, **info)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
