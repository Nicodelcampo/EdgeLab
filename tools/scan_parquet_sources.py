#!/usr/bin/env python3
"""Escanea los parquets derivados locales (canonical_tick_v1) con el MISMO formato de evidencia por hora que el escaneo de
texto, para compararlos exactamente contra los originales y usarlos como respaldo marcado cuando falta el original.

Holdout: se leen sólo row groups cuyo ts máximo es < cutoff (por estadísticas). Un row group sin estadísticas o que cruce
el cutoff NO se lee y queda registrado (no se deserializa nada reservado).
Uso: python tools/scan_parquet_sources.py --out D:/edgelab_release_work/scanP [--workers 2]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOTS = [Path(r"E:\EdgeLab\data") / d for d in (
    "nt8_2025_2026q3", "nt8_overlap_2025_2026", "nt8_ext_2026q3", "nt8_reexport_20261005")]
CUTOFF_UTC_NS = 1_790_805_600_000_000_000      # 2026-09-30T22:00:00Z  (trade-date >= 2026-10-01 empieza acá)
NAME = re.compile(r"^([A-Z0-9]+)_(\d\d-\d\d)_ticks_ext\.parquet$")
TICK = {"ES": 0.25, "NQ": 0.25, "MES": 0.25, "MNQ": 0.25, "YM": 1.0, "MYM": 1.0, "ZB": 0.03125, "GC": 0.1, "MGC": 0.1,
        "RTY": 0.1, "6E": 0.00005, "6B": 0.0001, "6J": 0.0000005, "MBT": 5.0}


def enumerate_sources():
    out = []
    for root in ROOTS:
        for p in sorted(root.rglob("*_ticks_ext.parquet")):
            m = NAME.match(p.name)
            if not m:
                continue
            out.append(dict(kind="P", root=str(root), path=str(p), instrument=m.group(1), contract=f"{m.group(1)} {m.group(2)}",
                            day=None, bytes=p.stat().st_size,
                            id=re.sub(r"[^A-Za-z0-9_.-]", "_", f"P__{root.name}__{m.group(1)}_{m.group(2)}__all")))
    return out


def scan_one(src, parts):
    import numpy as np
    import pyarrow.parquet as pq
    from edgelab.data.liquid_release.hourly_scan import HourlyAccumulator
    pid = parts / (src["id"] + ".json")
    if pid.exists():
        return src["id"], "cached"
    t0 = time.time()
    tick = TICK[src["instrument"]]
    pf = pq.ParquetFile(src["path"])
    names = pf.schema_arrow.names
    cols = ["ts_utc_ns", "price_ticks", "bid_ticks", "ask_ticks", "volume"] + (["tick_type"] if "tick_type" in names else [])
    ci = names.index("ts_utc_ns")
    acc = HourlyAccumulator(tick)
    rows = skipped_groups = mixed_groups = nostats = 0
    for g in range(pf.metadata.num_row_groups):
        st = pf.metadata.row_group(g).column(ci).statistics
        if st is None or not st.has_min_max:
            nostats += 1
            continue
        if int(st.min) >= CUTOFF_UTC_NS:
            skipped_groups += 1
            continue
        if int(st.max) >= CUTOFF_UTC_NS:
            mixed_groups += 1
            continue
        t = pf.read_row_group(g, columns=cols)
        if "tick_type" in t.schema.names:
            import pyarrow.compute as pc
            t = t.filter(pc.equal(pc.cast(t["tick_type"], "string"), "trade"))
        ts = t["ts_utc_ns"].to_numpy()
        d = ts.astype("datetime64[ns]")
        day = d.astype("datetime64[D]")
        date = (day.astype("datetime64[Y]").astype(int) + 1970) * 10000 \
            + ((day.astype("datetime64[M]").astype(int) % 12) + 1) * 100 + (day - day.astype("datetime64[M]")).astype(int) + 1
        hour = ((d - day).astype("timedelta64[h]")).astype(int)
        bidt = t["bid_ticks"].to_numpy()
        askt = t["ask_ticks"].to_numpy()
        acc.add(dict(ts_raw_ns=ts, date=date.astype(np.int64), hour=hour.astype(np.int64),
                     last=t["price_ticks"].to_numpy() * tick, bid=np.where(bidt > 0, bidt * tick, 0.0),
                     ask=np.where(askt > 0, askt * tick, 0.0), vol=t["volume"].to_numpy().astype(np.int64)))
        rows += len(ts)
    df = acc.frame()
    if len(df):
        df.insert(0, "source_id", src["id"])
        df.to_parquet(parts / (src["id"] + ".parquet"), index=False)
    h = hashlib.sha256()
    with open(src["path"], "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    rec = dict(src, rows_ok=rows, rows_invalid_shape=0, rows_invalid_ts=0, rows_unparseable=0, nonmonotonic=acc.nonmono,
               dup_consecutive=acc.dup_consecutive, min_ts_raw_ns=None if acc.min_ts is None else int(acc.min_ts),
               max_ts_raw_ns=None if acc.max_ts is None else int(acc.max_ts), sha256=h.hexdigest(), sha256_complete=True,
               truncated_at_cutoff=bool(mixed_groups or skipped_groups), row_groups_reserved_skipped=skipped_groups,
               row_groups_mixed_not_read=mixed_groups, row_groups_without_stats=nostats, tick=tick,
               elapsed_s=round(time.time() - t0, 1), invalid_samples=[])
    pid.write_text(json.dumps(rec), encoding="utf-8")
    return src["id"], f"ok rows={rows}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    out = Path(a.out)
    parts = out / "parts"
    parts.mkdir(parents=True, exist_ok=True)
    srcs = sorted(enumerate_sources(), key=lambda s: -s["bytes"])
    (out / "sources.json").write_text(json.dumps(srcs, indent=1), encoding="utf-8")
    print(len(srcs), "parquets,", round(sum(s["bytes"] for s in srcs) / 1e9, 1), "GB", flush=True)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(scan_one, s, parts): s for s in srcs}
        for i, f in enumerate(as_completed(futs), 1):
            s = futs[f]
            try:
                print(f"[{i}/{len(srcs)}] {f.result()} {time.time() - t0:.0f}s", flush=True)
            except Exception as e:
                (parts / (s["id"] + ".error.json")).write_text(json.dumps(dict(s, error=repr(e))), encoding="utf-8")
                print(f"[{i}/{len(srcs)}] ERROR {s['id']} {e!r}", flush=True)
    print("FIN", time.time() - t0, flush=True)


if __name__ == "__main__":
    main()
