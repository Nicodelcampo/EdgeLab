#!/usr/bin/env python3
"""Reconstruccion rapida del libro L2 (MBP-10) por sesion con Numba: snapshots por segundo + celdas de trades.

Misma semantica de libro que `edgelab.research.l2_phase0.apply_event` / `tools.build_l2_viewer_bundle.apply_l2`
(op 0 alta en `level`, 1 cambio, 2 baja; resincronizacion del borde P-75; truncado a LEVELS+1 en altas; fail-closed ante
reloj que retrocede, nivel invalido o libro cruzado > 1 %). Reemplaza el recorrido fila a fila en Python (44-83 s por sesion)
para el uso de ENTRENAMIENTO. No incluye detectores de iceberg/spoofing ni clasificacion de agresor (heuristica sin validar).

Salida por sesion (npz comprimido): bucket (segundo), bid_n/ask_n, bid_tick/bid_size/ask_tick/ask_size [S,11],
trades: tr_bucket, tr_tick, tr_vol, tr_cnt (ejecuciones L1 `side==2` agregadas por (segundo, tick)), y meta JSON de QA.

Uso: python tools/l2_fast_book.py --root E:/l2_parquet --instrument ES --out E:/l2_agg [--workers 2] [--limit N]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from numba import njit

ASK, BID, LAST_SIDE = 0, 1, 2
LEVELS = 10
K = LEVELS + 1          # niveles guardados por snapshot (el libro admite LEVELS+1)
CAP = 16
CROSSED_RATIO_ABSTAIN = 0.01
PASS, CLOCK_INVERSION, INVALID_LEVEL, CROSSED = 0, 1, 2, 3


@njit(cache=True)
def _ordered_after_last(bt, bn, s, tick):
    n = bn[s]
    if n == 0:
        return True
    if s == ASK:
        return tick > bt[s, n - 1]
    return tick < bt[s, n - 1]


@njit(cache=True)
def replay(ts_us, side, op, lvl, tick, size, snap_s, max_snaps):
    n_ev = len(ts_us)
    bt = np.zeros((2, CAP), np.int32)
    bs = np.zeros((2, CAP), np.int32)
    bn = np.zeros(2, np.int64)
    o_bucket = np.zeros(max_snaps, np.int64)
    o_n = np.zeros((max_snaps, 2), np.int16)
    o_t = np.zeros((max_snaps, 2, K), np.int32)
    o_s = np.zeros((max_snaps, 2, K), np.int32)
    ns = 0
    status = 0
    bad_row = -1
    resync = 0
    crossed = 0
    last_bucket = -1
    have_last = False
    prev_ts = -1
    for i in range(n_ev):
        t = ts_us[i]
        if prev_ts >= 0 and t < prev_ts:
            status = 1
            bad_row = i
            break
        prev_ts = t
        b = t // 1000000 // snap_s
        if not have_last:
            last_bucket = b
            have_last = True
        elif b != last_bucket:
            if ns >= max_snaps:
                status = 2
                bad_row = i
                break
            o_bucket[ns] = last_bucket
            for s in range(2):
                m = min(bn[s], K)
                o_n[ns, s] = m
                for j in range(m):
                    o_t[ns, s, j] = bt[s, j]
                    o_s[ns, s, j] = bs[s, j]
            ns += 1
            last_bucket = b
        s = ASK if side[i] == ASK else BID
        n = bn[s]
        o = op[i]
        lv = lvl[i]
        tk = tick[i]
        sz = size[i]
        rc = 1                                   # 1 OK, 2 RESYNC, 0 INVALID
        if o == 0:
            if lv <= n:
                if n + 1 > CAP:
                    rc = 0
                else:
                    for j in range(n, lv, -1):
                        bt[s, j] = bt[s, j - 1]
                        bs[s, j] = bs[s, j - 1]
                    bt[s, lv] = tk
                    bs[s, lv] = sz
                    n += 1
                    if n > K:
                        n = K
                    bn[s] = n
            elif _ordered_after_last(bt, bn, s, tk) and n < CAP:
                bt[s, n] = tk
                bs[s, n] = sz
                bn[s] = n + 1
                rc = 2
            else:
                rc = 0
        elif o == 1:
            if lv < n:
                bt[s, lv] = tk
                bs[s, lv] = sz
            elif _ordered_after_last(bt, bn, s, tk) and n < CAP:
                bt[s, n] = tk
                bs[s, n] = sz
                bn[s] = n + 1
                rc = 2
            else:
                rc = 0
        elif o == 2:
            if lv < n:
                for j in range(lv, n - 1):
                    bt[s, j] = bt[s, j + 1]
                    bs[s, j] = bs[s, j + 1]
                bn[s] = n - 1
            else:
                if n > 0 and bt[s, n - 1] == tk:
                    bn[s] = n - 1
                rc = 2
        else:
            rc = 0
        if rc == 0:
            status = 2
            bad_row = i
            break
        if rc == 2:
            resync += 1
        if bn[BID] > 0 and bn[ASK] > 0 and bt[BID, 0] >= bt[ASK, 0]:
            crossed += 1
    if status == 0 and have_last:
        o_bucket[ns] = last_bucket
        for s in range(2):
            m = min(bn[s], K)
            o_n[ns, s] = m
            for j in range(m):
                o_t[ns, s, j] = bt[s, j]
                o_s[ns, s, j] = bs[s, j]
        ns += 1
    if status == 0 and n_ev > 0 and crossed / n_ev > CROSSED_RATIO_ABSTAIN:
        status = 3
    return ns, status, bad_row, resync, crossed, o_bucket, o_n, o_t, o_s


def _col(tbl, name):
    return tbl[name].to_numpy()


def process_session(l2_path: str, l1_path: str, snap_s: int = 1) -> tuple[dict, dict]:
    t0 = time.time()
    l2 = pq.read_table(l2_path, columns=["source_row", "ts_us", "side", "operation", "level", "price_tick", "size"])
    sr = _col(l2, "source_row")
    order = None if (len(sr) < 2 or bool(np.all(sr[1:] > sr[:-1]))) else np.argsort(sr, kind="stable")
    g = lambda n: (_col(l2, n) if order is None else _col(l2, n)[order])
    ts, side, op, lvl, tick, size = g("ts_us"), g("side"), g("operation"), g("level"), g("price_tick"), g("size")
    span_s = int((ts[-1] - ts[0]) // 1_000_000 // snap_s) + 2 if len(ts) else 2
    max_snaps = max(span_s + 8, 16)
    ns, status, bad_row, resync, crossed, ob, on, ot, os_ = replay(
        ts.astype(np.int64), side.astype(np.int8), op.astype(np.int8), lvl.astype(np.int8), tick.astype(np.int32), size.astype(np.int32),
        snap_s, max_snaps)
    l1 = pq.read_table(l1_path, columns=["ts_us", "side", "price_tick", "size"])
    m = _col(l1, "side") == LAST_SIDE
    tts = _col(l1, "ts_us")[m] // 1_000_000 // snap_s
    tpx = _col(l1, "price_tick")[m].astype(np.int64)
    tsz = _col(l1, "size")[m].astype(np.int64)
    key = tts.astype(np.int64) * 1_000_000 + (tpx - tpx.min() if len(tpx) else 0)
    uk, inv = np.unique(key, return_inverse=True)
    vol = np.bincount(inv, weights=tsz).astype(np.int64) if len(uk) else np.zeros(0, np.int64)
    cnt = np.bincount(inv).astype(np.int64) if len(uk) else np.zeros(0, np.int64)
    first = np.zeros(len(uk), np.int64)
    if len(uk):
        first[inv[::-1]] = np.arange(len(inv))[::-1]
    arrs = dict(bucket=ob[:ns], n=on[:ns], tick=ot[:ns], size=os_[:ns],
                tr_bucket=tts[first] if len(uk) else tts, tr_tick=tpx[first] if len(uk) else tpx, tr_vol=vol, tr_cnt=cnt)
    meta = dict(schema="L2_FAST_BOOK_V1", source_l2=os.path.basename(l2_path), l2_events=int(len(ts)), snapshots=int(ns), snap_seconds=snap_s,
                status={0: "PASS", 1: "ABSTAIN_CLOCK_INVERSION", 2: "ABSTAIN_INVALID_LEVEL", 3: "ABSTAIN_CROSSED_BOOK"}[status],
                abstain_row=None if bad_row < 0 else int(bad_row), edge_resync=int(resync), crossed_events=int(crossed),
                crossed_ratio=float(crossed / max(1, len(ts))), trades_cells=int(len(uk)), seconds=round(time.time() - t0, 2))
    return arrs, meta


def _work(a):
    l2_path, l1_path, out_path, snap_s = a
    if os.path.exists(out_path):
        return out_path, "SKIP", 0.0
    arrs, meta = process_session(l2_path, l1_path, snap_s)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    np.savez_compressed(out_path, meta=json.dumps(meta), **arrs)
    return out_path, meta["status"], meta["seconds"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="E:/l2_parquet"); ap.add_argument("--instrument", required=True)
    ap.add_argument("--out", default="E:/l2_agg"); ap.add_argument("--snap-seconds", type=int, default=1)
    ap.add_argument("--workers", type=int, default=2); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    jobs = []
    for c in sorted(glob.glob(f"{a.root}/{a.instrument}_*")):
        if not os.path.isdir(c):
            continue
        for f in sorted(glob.glob(f"{c}/l2_depth/*.parquet")):
            d = re.search(r"(20\d{6})", os.path.basename(f)).group(1)
            jobs.append((f, f.replace("l2_depth", "l1_quotes"), f"{a.out}/{os.path.basename(c)}/{d}.npz", a.snap_seconds))
    if a.limit:
        jobs = jobs[: a.limit]
    t0 = time.time()
    if a.workers > 1:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(a.workers) as p:
            for r in p.imap_unordered(_work, jobs):
                print(r, flush=True)
    else:
        for j in jobs:
            print(_work(j), flush=True)
    print(f"{len(jobs)} sesiones en {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
