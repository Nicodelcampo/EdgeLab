#!/usr/bin/env python3
r"""Bundle de visor con PROFUNDIDAD L2 de una sesion: heatmap del libro (Bookmap-like) + cinta de trades + velas.

**Target-free. Solo visualizacion / estructura del libro.** Sin retornos, sin senales, sin outcomes.

Entrada: parquets canonicos `l1_quotes` y `l2_depth` de una sesion (`edgelab_schema nt8_l2_depth_v2`). Es MBP
(Market By Price, por nivel), **no MBO** (no hay ID de orden ni prioridad); `source_row` es el orden total dentro
del CSV original de origen, **no** el numero de secuencia de paquete del exchange — no confundir los dos.

Reconstruye el libro por posicion (MBP de 10 niveles) aplicando cada evento de L2 en el orden de `source_row`:
    operation 0 = alta  -> inserta en `level`
    operation 1 = cambio-> fija precio/tamano en `level`
    operation 2 = baja  -> elimina `level`
    side 0 = ask, side 1 = bid (enum MarketDataType de NT8)
y saca una foto del libro cada `--snap-seconds` segundos (defecto 1s: resolucion Bookmap-like).

RECONSTRUCCION FAIL-CLOSED (auditoria 2026-09-21). Un `level` fuera de rango en alta/cambio/baja YA NO se repara
en silencio (recortarlo a la posicion valida mas cercana inventa una posicion que el feed no dijo). Cada evento
invalido cuenta en `invalid_add_count` / `invalid_change_count` / `invalid_delete_count` y el libro pasa a un
estado ABSTAIN_* explicito (ver `BookStatus`). Por defecto (`--exploratory` no pasado), el proceso ABORTA en el
primer evento invalido o en la primera inversion de reloj — no se sigue alimentando heatmap/trades/detectores con
un libro que dejo de ser certificable. Con `--exploratory` continua, pero el bundle queda marcado
`meta.book_status != "PASS"` y `meta.exploratory_mode = true`, visible para quien lo consuma.

CONTRATO TEMPORAL (auditoria 2026-09-21). Todo el tiempo interno — orden de eventos, ventanas de los detectores,
validacion de cotizaciones — usa `ts_us`: MICROSEGUNDOS ENTEROS, sin truncar a segundos. Antes se truncaba a
segundos ANTES de alimentar los detectores, lo que perdia el orden real entre eventos del mismo segundo (comun:
con velas de HFT, cientos de eventos pueden caer en el mismo segundo). Los "buckets" de 1s del heatmap y las velas
de 5s/1min siguen siendo agregaciones legitimas — se calculan DESPUES, a partir de `ts_us`, no reemplazando su
precision. El orden total dentro de un mismo `ts_us` lo da `source_row` (se itera siempre en ese orden).

CINTA DE TRADES (Bookmap-like). Cada ejecucion (L1 `side=2`) se clasifica por agresor comparando su precio contra
el mejor bid/ask del libro reconstruido EN ESE INSTANTE (regla de cotizacion: precio >= ask -> compra agresiva,
precio <= bid -> venta agresiva; si el libro esta vacio o el precio cae adentro del spread, se usa la regla de tick
contra el trade anterior; si tampoco resuelve, queda NEUTRAL). **Es una clasificacion HEURISTICA**: no hay campo de
agresor en el feed y no se valido contra un oraculo. Se publica en `meta.trade_classification` la fraccion de cada
clase, Y la fraccion que vino de cada METODO (regla de cotizacion vs tick-test) por separado, para que quede
auditable. Los trades se AGREGAN por (celda de `snap_seconds`, precio) en compra/venta/neutral antes de publicarse:
dibujar cada ejecucion individual satura la pantalla cuando hay muchas por segundo (se solapan y forman bloques
solidos sin informacion); agregados, el tamano de la burbuja diferencia de verdad.

DETECTORES PROVISIONALES (iceberg / spoofing). Ver `edgelab/research/l2_manipulation_heuristics.py` para la
definicion exacta de cada heuristica, la politica de trades neutrales (`--neutral-policy`, default "abstain") y
sus limites. Se publican en `manipulation.icebergs` / `manipulation.spoofs`, cada uno `status=HEURISTIC_UNVALIDATED`.

RELOJ. `ts_us` es la hora de pared de NT8. Para GC 08-26 esta RESUELTA como ART (America/Argentina/Buenos_Aires,
UTC-3) por evidencia forense contra el calendario CME (30/30 sesiones lunes-jueves con el halt de mantenimiento
cayendo exacto a las 18:00 leido como UTC = 16:00 CT real; ver docs/research/RESOLUCION_RELOJ_GC_L2_20260922.md).
Lo que SIGUE sin resolver es la correspondencia absoluta contra los ticks `.Last.txt` (conversor distinto, no
solo timezone) -- por eso las velas se arman con los trades (L1 `side=2`) del MISMO archivo, que comparte reloj
con el libro. Nunca se une por cercania de timestamp con los bundles de ticks.

HOLDOUT. Se rechazan sesiones con fecha >= 20260630. El margen de este corte es una decision de holdout, no solo
de reloj -- resolver el reloj (arriba) no autoriza a estrecharlo sin decision explicita de Nico.

Validacion incluida: cada cotizacion L1 (mejor bid/ask) se compara con el tope del libro reconstruido y se publica
la tasa en `meta.book_validation`. En el feed la L1 llega ANTES de las filas L2 que la producen, asi que se evalua con
el libro tras la rafaga L2 que la sigue (comparar antes daba ~51 %, un artefacto del orden, no del libro).

    .venv\\Scripts\\python tools\\build_l2_viewer_bundle.py --base E:\\DatosNT8\\gc_aug26_canonical_parquets --date 20260615 ^
        --instrument GC --contract "GC 08-26" --out viewer\\nt8_bridge\\bundles
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
    AbsorptionTracker, IcebergTracker, SpoofTracker, large_size_thresholds)

LAST_SIDE, ASK, BID = 2, 0, 1
CUTOFF_DATE = 20260630
PRICE_PRECISION = {"GC": 1, "6E": 5, "ES": 2, "NQ": 2}
CANDLE_BUCKETS = {"time_5s": 5, "time_15s": 15, "time_30s": 30, "time_1m": 60}
DEFAULT_BAR_KEY = "time_15s"   # ver docs/research/L2_VISOR_RESOLUCION_20260923.md
CROSSED_RATIO_ABSTAIN = 0.01    # >1% de eventos con libro cruzado degrada la certificacion (ver BookStatus)

# Reloj resuelto POR INSTRUMENTO -- no generalizar de uno a otro sin medir (cada uno tiene su propia conversion
# NRD->CSV). Ausente de este dict = sigue "sin resolver": el default explicito abajo. GC: 30/30 sesiones
# lunes-jueves con el halt de mantenimiento CME cayendo exacto a las 18:00 leido como UTC (docs/research/
# RESOLUCION_RELOJ_GC_L2_20260922.md). ES: evidencia equivalente en docs/research/INTAKE_L2_ES_NRD_2026-08-21.md
# S5.1 (halt, apertura dominical, cierre RTH), pero esa sesion sigue en cuarentena de holdout (P-56): resuelto el
# reloj, NO autorizado para uso mas alla de target-free.
WALL_CLOCK_RESOLVED_TZ = {
    "GC": ("America/Argentina/Buenos_Aires (ART, UTC-3) -- resuelto 2026-09-22, ver "
           "docs/research/RESOLUCION_RELOJ_GC_L2_20260922.md"),
    "ES": ("America/Argentina/Buenos_Aires (ART, UTC-3) -- resuelto 2026-08-21, ver "
           "docs/research/INTAKE_L2_ES_NRD_2026-08-21.md S5.1"),
    "6E": ("America/Argentina/Buenos_Aires (ART, UTC-3) -- resuelto 2026-09-23, ver "
           "docs/research/L2_VISOR_RESOLUCION_20260923.md S1"),
}


def _clock_meta(instrument: str) -> tuple[str, str]:
    """(chart_tz, clock) segun si este instrumento tiene el reloj resuelto por evidencia forense propia."""
    tz = WALL_CLOCK_RESOLVED_TZ.get(instrument)
    if tz is None:
        return "UTC (reloj NT8, referencia sin resolver)", "NT8_WALL_CLOCK_INTERPRETED_AS_UTC_REFERENCE_UNRESOLVED"
    return tz, f"NT8_WALL_CLOCK_RESOLVED_ART_UTC-3_{instrument}"

PASS = "PASS"
ABSTAIN_INVALID_LEVEL = "ABSTAIN_INVALID_LEVEL"
ABSTAIN_CROSSED_BOOK = "ABSTAIN_CROSSED_BOOK"
ABSTAIN_CLOCK_INVERSION = "ABSTAIN_CLOCK_INVERSION"


class BookAbstain(Exception):
    """El libro dejo de ser certificable. `status` es uno de los codigos ABSTAIN_*; `row` es el source_row donde
    ocurrio (para reproducir). No se captura fuera de `build()`: para eso existe `--exploratory`."""

    def __init__(self, status: str, row: int, detail: str):
        super().__init__(f"{status} en source_row={row}: {detail}")
        self.status = status
        self.row = row


def apply_l2(side_book: list, op: int, lvl: int, tick: int, size: float) -> str | None:
    """Aplica un evento a la lista de un lado (posicion 0 = mejor precio). Devuelve None si el nivel era valido,
    o el codigo de error si NO lo era (fail-closed: ya no se recorta el nivel a una posicion valida inventada)."""
    n = len(side_book)
    if op == 0:                                   # alta
        if lvl > n:
            return ABSTAIN_INVALID_LEVEL
        side_book.insert(lvl, [tick, size])
    elif op == 1:                                 # cambio
        if lvl >= n:
            return ABSTAIN_INVALID_LEVEL
        side_book[lvl] = [tick, size]
    elif op == 2:                                 # baja
        if lvl >= n:
            return ABSTAIN_INVALID_LEVEL
        del side_book[lvl]
    return None


def classify_aggressor(price_tick, bid_tick, ask_tick, prev_trade_tick):
    """Regla de cotizacion (Lee-Ready simplificada) + tick-test de respaldo. Devuelve (direccion, metodo).
    direccion: +1 compra agresiva, -1 venta agresiva, 0 neutral. metodo: "quote_rule" | "tick_test" | "neutral"."""
    if ask_tick is not None and price_tick >= ask_tick:
        return 1, "quote_rule"
    if bid_tick is not None and price_tick <= bid_tick:
        return -1, "quote_rule"
    if prev_trade_tick is not None:
        if price_tick > prev_trade_tick:
            return 1, "tick_test"
        if price_tick < prev_trade_tick:
            return -1, "tick_test"
    return 0, "neutral"


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
DEFAULT_SPOOF_KWARGS = dict(max_lifetime_us=5_000_000.0, max_fill_ratio=0.15, near_ticks=3)
ICEBERG_MIN_AVG_SIZE_PCTL = 90.0                # ademas, el nivel que se rellena debe ser notablemente grande


def build(l1_path: Path, l2_path: Path, snap_seconds: int, tick_size: float, *,
         iceberg_kwargs: dict | None = None, spoof_kwargs: dict | None = None,
         large_size_pctl: float = DEFAULT_LARGE_SIZE_PCTL, neutral_policy: str = "abstain",
         exploratory: bool = False):
    l1 = pq.read_table(l1_path).to_pandas().sort_values("source_row", kind="stable")
    l2 = pq.read_table(l2_path).to_pandas().sort_values("source_row", kind="stable")

    tr = l1[l1.side == LAST_SIDE]
    # `price` (float64) ya no se guarda en el parquet L1 (redundante con price_tick*tick_size, auditoria
    # 2026-09-22): se reconstruye aca, igual que en el resto del archivo (ver linea de `c["price"]` abajo).
    tr_ts = (tr.ts_us // 1_000_000).tolist()
    tr_px = (tr.price_tick.to_numpy(dtype=float) * tick_size).tolist()
    tr_sz = tr["size"].tolist()
    bar_series = {k: bin_candles(tr_ts, tr_px, tr_sz, secs) for k, secs in CANDLE_BUCKETS.items()}

    # ---- recorrido unico por source_row: aplica L2 al libro, valida cotizaciones L1, clasifica trades L1,
    # agrega trades por (celda de tiempo, precio) para la cinta de burbujas, y alimenta los detectores provisionales.
    # `ts_us` (microsegundos enteros) es el reloj interno unico; los buckets de segundos son agregaciones derivadas.
    bids: list = []
    asks: list = []
    r_l2 = l2.source_row.to_numpy()
    side, op, lvl = l2.side.tolist(), l2.operation.tolist(), l2.level.tolist()
    tick, size = l2.price_tick.tolist(), l2["size"].tolist()
    ts_us_l2 = l2.ts_us.tolist()

    l1_side = l1.side.tolist(); l1_row = l1.source_row.to_numpy(); l1_tick = l1.price_tick.tolist()
    l1_size = l1["size"].tolist(); l1_ts_us = l1.ts_us.tolist()
    li, n1 = 0, len(l1_row)
    match = dict(bid=[0, 0], ask=[0, 0])
    method_counts = {"quote_rule": 0, "tick_test": 0, "neutral": 0}
    crossed = 0
    empty_book_intervals = 0
    snap_t, snap_off, cell_tick, cell_size = [], [], [], []      # cell_size: + bid / - ask
    trade_cells = {}  # (bucket_s,tick) -> volúmenes, conteos, métodos, máximo y rango temporal
    last_bucket = None
    pending = None                                  # cotizacion L1 pendiente de validar (ver nota de orden)
    prev_trade_tick = None
    side_counts = {1: 0, -1: 0, 0: 0}
    invalid_add = invalid_change = invalid_delete = 0
    book_status = PASS
    abstain_row = None

    side_a, op_a, size_a = np.asarray(side), np.asarray(op), np.asarray(size, dtype=float)
    thresholds = large_size_thresholds(side_a, op_a, size_a, large_size_pctl)
    ice_kwargs = dict(DEFAULT_ICEBERG_KWARGS, min_avg_size=large_size_thresholds(side_a, op_a, size_a, ICEBERG_MIN_AVG_SIZE_PCTL),
                      neutral_policy=neutral_policy)
    ice_kwargs.update(iceberg_kwargs or {})
    spf_kwargs = dict(DEFAULT_SPOOF_KWARGS, neutral_policy=neutral_policy)
    spf_kwargs.update(spoof_kwargs or {})
    iceberg = IcebergTracker(**ice_kwargs)
    spoof = SpoofTracker(thresholds, **spf_kwargs)
    absorption = AbsorptionTracker()

    def check_quote(j):
        book = bids if l1_side[j] == BID else asks
        if book:
            key = "bid" if l1_side[j] == BID else "ask"
            match[key][1] += 1
            match[key][0] += int(book[0][0] == l1_tick[j])

    def dump(bucket_s):
        nonlocal empty_book_intervals
        snap_t.append(bucket_s * snap_seconds)
        snap_off.append(len(cell_tick))
        if not bids and not asks:
            empty_book_intervals += 1
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
            d, method = classify_aggressor(l1_tick[j], b, a, prev_tick)
            side_counts[d] += 1
            method_counts[method] += 1
            tk, sz, tsj_us = l1_tick[j], l1_size[j], l1_ts_us[j]
            bucket_s = (tsj_us // 1_000_000) - (tsj_us // 1_000_000) % snap_seconds
            key = (bucket_s, tk)
            cell = trade_cells.get(key)
            if cell is None:
                trade_cells[key] = cell = dict(
                    buy=0.0, sell=0.0, neutral=0.0, buy_count=0, sell_count=0, neutral_count=0,
                    max_trade_size=0.0, first_ts_us=tsj_us, last_ts_us=tsj_us,
                    method_quote_rule_count=0, method_tick_test_count=0, method_neutral_count=0,
                    method_quote_rule_volume=0.0, method_tick_test_volume=0.0, method_neutral_volume=0.0)
            side_name = "buy" if d > 0 else ("sell" if d < 0 else "neutral")
            cell[side_name] += sz; cell[side_name + "_count"] += 1
            cell["max_trade_size"] = max(cell["max_trade_size"], float(sz))
            cell["first_ts_us"] = min(cell["first_ts_us"], tsj_us)
            cell["last_ts_us"] = max(cell["last_ts_us"], tsj_us)
            cell["method_" + method + "_count"] += 1
            cell["method_" + method + "_volume"] += sz
            iceberg.on_trade(tk, tsj_us, sz, d)
            spoof.on_trade(tk, tsj_us, sz, d)
            absorption.on_trade(tk, tsj_us, sz, d)
            return j + 1, pend, tk
        if l1_side[j] in (ASK, BID):
            if pend is not None:                # la L1 llega ANTES de las filas L2 que la producen: se evalua
                check_quote(pend)                # con el libro tras la rafaga L2 que la sigue
            return j + 1, j, prev_tick
        return j + 1, pend, prev_tick

    prev_ts_us = None
    for i in range(len(r_l2)):
        ts_us_i = ts_us_l2[i]
        if prev_ts_us is not None and ts_us_i < prev_ts_us:
            book_status, abstain_row = ABSTAIN_CLOCK_INVERSION, int(r_l2[i])
            if not exploratory:
                raise BookAbstain(book_status, abstain_row, f"ts_us retrocede: {ts_us_i} < {prev_ts_us}")
        prev_ts_us = ts_us_i
        bucket_s = ts_us_i // 1_000_000 // snap_seconds
        if last_bucket is None:
            last_bucket = bucket_s
        elif bucket_s != last_bucket:
            dump(last_bucket)                   # estado al cierre del bucket anterior
            last_bucket = bucket_s
        while li < n1 and l1_row[li] < r_l2[i]:  # filas L1 anteriores a este evento L2
            li, pending, prev_trade_tick = handle_l1_row(li, pending, prev_trade_tick)
        err = apply_l2(asks if side[i] == ASK else bids, op[i], lvl[i], tick[i], size[i])
        if err is not None:
            if op[i] == 0: invalid_add += 1
            elif op[i] == 1: invalid_change += 1
            else: invalid_delete += 1
            book_status, abstain_row = err, int(r_l2[i])
            if not exploratory:
                raise BookAbstain(book_status, abstain_row,
                                  f"side={side[i]} op={op[i]} lvl={lvl[i]} fuera de rango")
            continue                            # exploratorio: el evento invalido se descarta, se sigue leyendo
        if side[i] == BID:
            depth = (bids[0][0] - tick[i]) if bids else None
        else:
            depth = (tick[i] - asks[0][0]) if asks else None
        iceberg.on_l2_event(side[i], op[i], tick[i], size[i], ts_us_i, depth)
        spoof.on_l2_event(side[i], op[i], tick[i], size[i], ts_us_i, depth)
        if bids and asks and bids[0][0] >= asks[0][0]:
            crossed += 1
    while li < n1:                              # filas L1 despues del ultimo evento L2
        li, pending, prev_trade_tick = handle_l1_row(li, pending, prev_trade_tick)
    if pending is not None:
        check_quote(pending)
    if last_bucket is not None:
        dump(last_bucket)
    snap_off.append(len(cell_tick))

    crossed_ratio = crossed / max(1, len(r_l2))
    if book_status == PASS and crossed_ratio > CROSSED_RATIO_ABSTAIN:
        book_status, abstain_row = ABSTAIN_CROSSED_BOOK, int(r_l2[-1]) if len(r_l2) else None
        if not exploratory:
            raise BookAbstain(book_status, abstain_row, f"cruzado en {crossed_ratio:.4%} de los eventos (> {CROSSED_RATIO_ABSTAIN:.0%})")

    validation = dict(
        best_bid_match=match["bid"][0] / max(1, match["bid"][1]), best_bid_checks=match["bid"][1],
        best_ask_match=match["ask"][0] / max(1, match["ask"][1]), best_ask_checks=match["ask"][1],
        crossed_book_events=crossed, crossed_book_ratio=crossed_ratio, crossed_ratio_abstain_threshold=CROSSED_RATIO_ABSTAIN,
        l2_events=len(r_l2), invalid_add_count=invalid_add, invalid_change_count=invalid_change,
        invalid_delete_count=invalid_delete, empty_book_intervals=empty_book_intervals,
        first_source_row=int(r_l2[0]) if len(r_l2) else None, last_source_row=int(r_l2[-1]) if len(r_l2) else None,
        source_row_monotonic=bool(np.all(np.diff(r_l2) > 0)) if len(r_l2) > 1 else True,
        book_status=book_status, abstain_source_row=abstain_row, exploratory_mode=exploratory)
    n_tr = max(1, len(tr))
    trade_classification = dict(buy_aggressor=side_counts[1] / n_tr, sell_aggressor=side_counts[-1] / n_tr,
                                neutral=side_counts[0] / n_tr,
                                method_quote_rule=method_counts["quote_rule"] / n_tr,
                                method_tick_test=method_counts["tick_test"] / n_tr,
                                method_neutral=method_counts["neutral"] / n_tr,
                                method="quote_rule_then_tick_test_HEURISTIC_UNVALIDATED")
    l2b = dict(schema="L2_DEPTH_CELLS_V1", namespace="l2.depth", certification=book_status,
               snap_seconds=snap_seconds, tick_size=tick_size, t=snap_t, off=snap_off, tick=cell_tick, size=cell_size)

    names = ("buy", "sell", "neutral", "buy_count", "sell_count", "neutral_count", "max_trade_size",
             "first_ts_us", "last_ts_us", "method_quote_rule_count", "method_tick_test_count", "method_neutral_count",
             "method_quote_rule_volume", "method_tick_test_volume", "method_neutral_volume")
    cols = {name: [] for name in names}; tc_t, tc_off, tc_tick = [], [], []
    for (bucket_ts, tk), cell in sorted(trade_cells.items()):
        if not tc_t or tc_t[-1] != bucket_ts:
            tc_t.append(bucket_ts); tc_off.append(len(tc_tick))
        tc_tick.append(tk)
        for name in names: cols[name].append(cell[name])
    tc_off.append(len(tc_tick))
    totals = sorted(c["buy"] + c["sell"] + c["neutral"] for c in trade_cells.values())
    def percentile(p):
        return float(totals[min(len(totals) - 1, int(len(totals) * p))]) if totals else 1.0
    trades = dict(schema="L2_TRADE_CELLS_V2", namespace="l2.trades",
                  certification="HEURISTIC_AGGRESSOR_UNVALIDATED", snap_seconds=snap_seconds,
                  scale_scope="SESSION", size_tier_percentiles=[0.50, 0.75, 0.90, 0.97],
                  size_tiers=[percentile(0.50), percentile(0.75), percentile(0.90), percentile(0.97)],
                  t=tc_t, off=tc_off, tick=tc_tick,
                  trade_count=[cols["buy_count"][i] + cols["sell_count"][i] + cols["neutral_count"][i]
                               for i in range(len(tc_tick))], **cols)

    def to_price(cands):
        out = []
        for c in cands:
            c = dict(c)
            c["price"] = c["tick"] * tick_size
            out.append(c)
        return out

    _all_ice = iceberg.candidates(); _all_spf = spoof.candidates(); _all_abs = absorption.candidates()
    absorptions = sorted(_all_abs, key=lambda c: -c["attributed_volume"])[:300]
    icebergs = sorted(_all_ice, key=lambda c: -c["refill_count"])[:300]
    spoofs = sorted(_all_spf, key=lambda c: c["fill_ratio"])[:300]
    manipulation = dict(
        icebergs=to_price(icebergs), spoofs=to_price(spoofs), absorptions=to_price(absorptions),
        raw_absorption_count=len(_all_abs),
        large_size_threshold_ask=thresholds[ASK], large_size_threshold_bid=thresholds[BID],
        raw_iceberg_count=len(_all_ice), raw_spoof_count=len(_all_spf), neutral_policy=neutral_policy,
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
    entry = dict(id=m["id"], name=f"{m['contract']}", group=m.get("group") or f"Profundidad L2 {m['instrument']}", instrument=m["instrument"],
                 contract=m["contract"], tick_size=m["tick_size"], precision=m["precision"], candles=m["n_candles"],
                 zones=0, rolls=0, parity_status="PARITY_ABSTAIN", kind=m["kind"], book_status=m.get("book_status"))
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
    ap.add_argument("--neutral-policy", default="abstain", choices=("abstain", "distribute", "credit_both_exploratory"))
    ap.add_argument("--exploratory", action="store_true",
                    help="no abortar ante libro invalido/cruzado/con inversion de reloj: seguir, marcando el bundle")
    ap.add_argument("--holdout-view-only", action="store_true",
                    help="admitir sesiones del holdout SOLO para el visor (target-free); el bundle queda marcado")
    ap.add_argument("--group", default=None, help="grupo del selector del visor (default: 'Profundidad L2 <inst>')")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    holdout_view = int(a.date) >= CUTOFF_DATE
    if holdout_view and not a.holdout_view_only:
        raise SystemExit(f"sesion {a.date} >= {CUTOFF_DATE}: holdout. Solo se admite como dato de VISOR (target-free, "
                         f"NORTH_STAR: 'Permitido solo para ... visor'); pasar --holdout-view-only para marcarlo asi")
    man = json.loads((a.base / "manifests" / f"{a.date}.manifest.json").read_text(encoding="utf-8"))
    tick_size = float(man["conversion"]["tick_size"])
    try:
        bar_series, l2b, trades, val, trclass, manip, info = build(
            a.base / "l1_quotes" / f"{a.date}.parquet", a.base / "l2_depth" / f"{a.date}.parquet", a.snap_seconds,
            tick_size, neutral_policy=a.neutral_policy, exploratory=a.exploratory)
    except BookAbstain as e:
        raise SystemExit(f"libro NO certificable, build abortado (pasar --exploratory para continuar de todos modos): {e}")
    aid = f"{a.instrument}_L2_{a.date}"
    n_candles = len(bar_series[DEFAULT_BAR_KEY])
    chart_tz, clock_status = _clock_meta(a.instrument)
    bundle = {
        "meta": dict(id=aid, instrument=a.instrument, contract=f"{a.contract} L2 {a.date}", tick_size=tick_size,
                     precision=PRICE_PRECISION.get(a.instrument, 2),
                     chart_tz=chart_tz,
                     n_candles=n_candles, n_zones=0, rolls=[], kind="L2_DEPTH_SESSION",
                     clock=clock_status, outcome_firewall="ENFORCED",
                     holdout_view_only=holdout_view, group=a.group,
                     source=dict(l1=str(a.base / "l1_quotes" / f"{a.date}.parquet"), l2=str(a.base / "l2_depth" / f"{a.date}.parquet")),
                     book_validation=val, trade_classification=trclass, book_status=val["book_status"],
                     exploratory_mode=a.exploratory, manipulation_summary=dict(
                         icebergs=len(manip["icebergs"]), spoofs=len(manip["spoofs"]),
                         absorptions=len(manip["absorptions"])), **info),
        "bar_series": {
            "time_5s": {"kind": "time_5s", "name": "5 Segundos (trades L1 del feed L2)", "param": 5, "candles": bar_series["time_5s"]},
            "time_15s": {"kind": "time_15s", "name": "15 Segundos (trades L1 del feed L2)", "param": 15, "candles": bar_series["time_15s"]},
            "time_30s": {"kind": "time_30s", "name": "30 Segundos (trades L1 del feed L2)", "param": 30, "candles": bar_series["time_30s"]},
            "time_1m": {"kind": "time_1m", "name": "1 Minuto (trades L1 del feed L2)", "param": 1, "candles": bar_series["time_1m"]},
        },
        "runs": [{"id": "l2_depth_stub", "name": "Profundidad L2 (sin zonas)", "indicator": "L2Depth", "bar_key": DEFAULT_BAR_KEY,
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
