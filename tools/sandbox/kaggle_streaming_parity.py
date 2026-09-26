#!/usr/bin/env python3
"""Paridad streaming vs batch del acumulador de integridad.

Si el camino por batches (el que corre en Kaggle sobre 16,74 GB) no produce los
mismos numeros que el camino en memoria (el que se puede auditar a mano), la
validacion no vale. Este test alimenta el acumulador con el archivo canonico
6E_09-26 en batches de tamanios distintos y compara clave por clave.

Paths de sandbox del auditor (no de CI): /data/replica y /data/p16.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, "/data/replica")

from edgelab.kaggle import identity, integrity, seal  # noqa: E402
from edgelab.kaggle.streaming import TickStreamAccumulator  # noqa: E402

COLS = ("ts_utc_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "sequence")
FAILS: list[str] = []

z = np.load("/data/p16/ticks_90d.npz")
arrs = {c: z[c].astype(np.int64) for c in COLS}
n = arrs["ts_utc_ns"].size
print(f"ticks: {n}")

ref_checks = integrity.tick_checks(
    ts_utc_ns=arrs["ts_utc_ns"],
    price_ticks=arrs["price_ticks"],
    volume=arrs["volume"],
    bid_ticks=arrs["bid_ticks"],
    ask_ticks=arrs["ask_ticks"],
    sequence=arrs["sequence"],
)
ref_act = integrity.session_activity(arrs["ts_utc_ns"], volume=arrs["volume"])
_, ref_seal = seal.apply_seal(arrs["ts_utc_ns"])

results = {}
for batch in (7919, 100_000, 500_000, n):
    acc = TickStreamAccumulator()
    for lo in range(0, n, batch):
        hi = min(lo + batch, n)
        acc.update(**{c: arrs[c][lo:hi] for c in COLS})
    got = acc.finalize()
    tag = f"batch={batch}"
    print(f"\n== {tag} ({got['batches']} batches) ==")

    shared = set(ref_checks) & set(got["tick_checks"])
    for k in sorted(shared):
        a, b = ref_checks[k], got["tick_checks"][k]
        ok = (
            abs(a - b) <= 1e-9 * max(1.0, abs(a))
            if isinstance(a, float)
            else a == b
        )
        if not ok:
            FAILS.append(f"{tag}:tick_checks.{k}")
            print(f"  [FAIL] tick_checks.{k}: batch={a!r} stream={b!r}")
    print(f"  tick_checks: {len(shared)} claves comparadas, "
          f"{sum(1 for f in FAILS if f.startswith(tag + ':tick_checks'))} fallos")

    if got["activity"]["trade_dates"] != ref_act["trade_dates"]:
        FAILS.append(f"{tag}:activity.trade_dates")
    nd = 0
    for day, ref in ref_act["by_trade_date"].items():
        cur = got["activity"]["by_trade_date"].get(int(day))
        if cur is None:
            FAILS.append(f"{tag}:activity.missing.{day}")
            continue
        for k in ("ticks", "ticks_in_maintenance", "minutes_active", "first_minute",
                  "last_minute", "ts_min_ns", "ts_max_ns", "volume", "gap_max_seconds"):
            if k in ref and ref[k] != cur.get(k):
                FAILS.append(f"{tag}:activity.{day}.{k}")
                print(f"  [FAIL] {day}.{k}: batch={ref[k]!r} stream={cur.get(k)!r}")
            nd += 1
    print(f"  activity: {len(ref_act['by_trade_date'])} dias, {nd} claves comparadas")

    rs, gs = ref_seal.to_dict(), got["seal"]
    for k in ("rows_in", "rows_kept", "rows_cut_holdout", "rows_cut_after_holdout",
              "rows_leaked_by_naive_utc_cut", "first_trade_date_kept",
              "last_trade_date_kept", "first_trade_date_cut", "last_trade_date_cut",
              "kept_trade_dates", "cut_rows_by_trade_date"):
        if rs.get(k) != gs.get(k):
            FAILS.append(f"{tag}:seal.{k}")
            print(f"  [FAIL] seal.{k}: batch={rs.get(k)!r} stream={gs.get(k)!r}")
    print(f"  seal: rows_kept={gs['rows_kept']} cut_holdout={gs['rows_cut_holdout']} "
          f"leak_utc={gs['rows_leaked_by_naive_utc_cut']}")
    results[tag] = {"batches": got["batches"], "seal": gs}

out = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "file": "6E_09-26_ticks.parquet",
    "rows": int(n),
    "reference_tick_checks": ref_checks,
    "reference_seal": ref_seal.to_dict(),
    "streaming_runs": results,
    "failures": FAILS,
}
identity.write_json("/data/p16/kaggle_streaming_parity.json", out)
print("\n== RESULTADO ==")
print("FAILS:", FAILS if FAILS else "ninguno")
sys.exit(1 if FAILS else 0)
