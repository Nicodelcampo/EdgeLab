#!/usr/bin/env python3
r"""Bundle de visor con PROFUNDIDAD L2 de una sesion (mapa de calor del libro + velas de los trades del propio feed).

**Target-free. Solo visualizacion / estructura del libro.** Sin retornos, sin senales, sin outcomes.

Entrada: parquets canonicos `l1_quotes` y `l2_depth` de una sesion (`edgelab_schema nt8_l2_depth_v2`).
Reconstruye el libro por posicion (MBP de 10 niveles) aplicando cada evento de L2 en el orden de `source_row`:
    operation 0 = alta  -> inserta en `level` y corre lo de abajo
    operation 1 = cambio-> fija precio/tamano en `level`
    operation 2 = baja  -> elimina `level` y sube lo de abajo
    side 0 = ask, side 1 = bid (enum MarketDataType de NT8)
y saca una foto del libro cada `--snap-seconds` segundos.

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

LAST_SIDE, ASK, BID = 2, 0, 1
CUTOFF_DATE = 20260630
PRICE_PRECISION = {"GC": 1, "6E": 5, "ES": 2, "NQ": 2}


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


def build(l1_path: Path, l2_path: Path, snap_seconds: int, tick_size: float):
    l1 = pq.read_table(l1_path).to_pandas()
    l2 = pq.read_table(l2_path).to_pandas()
    l1 = l1.sort_values("source_row", kind="stable")
    l2 = l2.sort_values("source_row", kind="stable")

    tr = l1[l1.side == LAST_SIDE]
    q = l1[l1.side.isin((ASK, BID))]

    # ---- velas de 1 minuto con los trades del propio feed
    cand = {}
    for ts, px, sz in zip((tr.ts_us // 1_000_000).tolist(), tr.price.tolist(), tr["size"].tolist()):
        k = ts - ts % 60
        c = cand.get(k)
        if c is None:
            cand[k] = [px, px, px, px, sz]
        else:
            if px > c[1]: c[1] = px
            if px < c[2]: c[2] = px
            c[3] = px; c[4] += sz
    candles = [{"time": k, "open": v[0], "high": v[1], "low": v[2], "close": v[3], "volume": float(v[4])}
               for k, v in sorted(cand.items())]

    # ---- libro por posicion, fotos cada snap_seconds, validacion contra L1
    bids, asks = [], []
    r_l2 = l2.source_row.to_numpy()
    side, op, lvl = l2.side.tolist(), l2.operation.tolist(), l2.level.tolist()
    tick, size, ts = l2.price_tick.tolist(), l2["size"].tolist(), (l2.ts_us // 1_000_000).tolist()
    q_row = q.source_row.to_numpy(); q_side = q.side.tolist(); q_tick = q.price_tick.tolist()
    qi, nq = 0, len(q_row)
    match = dict(bid=[0, 0], ask=[0, 0])
    crossed = 0
    snap_t, snap_off, cell_tick, cell_size = [], [], [], []      # cell_size: + bid / - ask
    last_bucket = None
    pending = None

    def check(j):
        book = bids if q_side[j] == BID else asks
        if book:
            key = "bid" if q_side[j] == BID else "ask"
            match[key][1] += 1
            match[key][0] += int(book[0][0] == q_tick[j])

    def dump(bucket):
        snap_t.append(bucket * snap_seconds)
        snap_off.append(len(cell_tick))
        for t, s in bids:
            cell_tick.append(t); cell_size.append(s)
        for t, s in asks:
            cell_tick.append(t); cell_size.append(-s)

    for i in range(len(r_l2)):
        bucket = ts[i] // snap_seconds
        if last_bucket is None:
            last_bucket = bucket
        elif bucket != last_bucket:
            dump(last_bucket)                   # estado al cierre del bucket anterior
            last_bucket = bucket
        while qi < nq and q_row[qi] < r_l2[i]:  # cotizaciones L1 anteriores a este evento L2
            if pending is not None:             # la L1 llega ANTES de las filas L2 que la producen: se evalua
                check(pending)                  # con el libro tras la rafaga L2 que la sigue
            pending = qi
            qi += 1
        apply_l2(None, asks if side[i] == ASK else bids, op[i], lvl[i], tick[i], size[i])
        if bids and asks and bids[0][0] >= asks[0][0]:
            crossed += 1
    if pending is not None:
        check(pending)
    if last_bucket is not None:
        dump(last_bucket)
    snap_off.append(len(cell_tick))
    validation = dict(
        best_bid_match=match["bid"][0] / max(1, match["bid"][1]), best_bid_checks=match["bid"][1],
        best_ask_match=match["ask"][0] / max(1, match["ask"][1]), best_ask_checks=match["ask"][1],
        crossed_book_events=crossed, l2_events=len(r_l2))
    l2b = dict(snap_seconds=snap_seconds, tick_size=tick_size, t=snap_t, off=snap_off, tick=cell_tick, size=cell_size)
    return candles, l2b, validation, dict(trades=len(tr), l2_events=len(l2), first_ts=int(l2.ts_us.min() // 1_000_000),
                                          last_ts=int(l2.ts_us.max() // 1_000_000))


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
    ap.add_argument("--snap-seconds", type=int, default=5)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if int(a.date) >= CUTOFF_DATE:
        raise SystemExit(f"sesion {a.date} >= {CUTOFF_DATE}: fuera del limite pre-holdout (el reloj L2 no esta resuelto)")
    man = json.loads((a.base / "manifests" / f"{a.date}.manifest.json").read_text(encoding="utf-8"))
    tick_size = float(man["conversion"]["tick_size"])
    candles, l2b, val, info = build(a.base / "l1_quotes" / f"{a.date}.parquet", a.base / "l2_depth" / f"{a.date}.parquet",
                                    a.snap_seconds, tick_size)
    aid = f"{a.instrument}_L2_{a.date}"
    bundle = {
        "meta": dict(id=aid, instrument=a.instrument, contract=f"{a.contract} L2 {a.date}", tick_size=tick_size,
                     precision=PRICE_PRECISION.get(a.instrument, 2), chart_tz="UTC (reloj NT8, referencia sin resolver)",
                     n_candles=len(candles), n_zones=0, rolls=[], kind="L2_DEPTH_SESSION",
                     clock="NT8_WALL_CLOCK_INTERPRETED_AS_UTC_REFERENCE_UNRESOLVED", outcome_firewall="ENFORCED",
                     source=dict(l1=str(a.base / "l1_quotes" / f"{a.date}.parquet"), l2=str(a.base / "l2_depth" / f"{a.date}.parquet")),
                     book_validation=val, **info),
        "bar_series": {"time_1m": {"kind": "time_1m", "name": "1 Minuto (trades L1 del feed L2)", "param": 1, "candles": candles}},
        "runs": [{"id": "l2_depth_stub", "name": "Profundidad L2 (sin zonas)", "indicator": "L2Depth", "bar_key": "time_1m",
                  "has_oracle": False, "zones": [], "parity": {"status": "PARITY_ABSTAIN", "gate": "PARITY_ABSTAIN"}, "params": {}}],
        "l2": l2b,
    }
    a.out.mkdir(parents=True, exist_ok=True)
    p = a.out / f"{aid}.json"
    p.write_text(json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
    registered = register(a.out, bundle)
    print(json.dumps(dict(asset_id=aid, registered=registered, bytes=p.stat().st_size, candles=len(candles), snapshots=len(l2b["t"]),
                          cells=len(l2b["tick"]), validation=val, **info)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
