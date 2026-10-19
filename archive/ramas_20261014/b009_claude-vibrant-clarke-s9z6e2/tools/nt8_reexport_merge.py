#!/usr/bin/env python3
r"""Fusiona la re-exportación NT8 del 2026-10-04/05 (AddOn EdgeLab Tick History) con el parquet canónico previo de
cada contrato, contrato por contrato y en streaming (16 GB de RAM).

Regla de fusión (declarada antes de mirar resultados):
- Un día local de NT8 (hora argentina, [d 03:00Z, d+1 03:00Z)) re-exportado con estado OK reemplaza por completo a los
  ticks del parquet viejo en ese intervalo. Los días sin re-exportación (o NO_DATA) conservan los ticks viejos.
- Ventana: desde la apertura de la sesión CME del 1-jul-2025 (2025-06-30 22:00Z) hasta antes de la sesión del
  2026-10-01 (holdout). Nada del holdout entra.
- Precios en la grilla del tick del instrumento (falla si no cae en la grilla). Esquema canonical_tick_v1.
- No borra ni modifica nada existente: escribe en <out>\<INST>\<C>_ticks_ext.parquet + manifest + sessions.

    .venv\Scripts\python tools\nt8_reexport_merge.py [--out E:\EdgeLab\data\nt8_reexport_20261005] [CONTRATO ...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from edgelab.kaggle.sessions_cme import is_maintenance_break, trade_date_ymd  # noqa: E402

SRC = Path(r"E:\DatosNT8\tick_history_reexport_20261004")
START_NS = 1_751_320_800 * 1_000_000_000      # 2025-06-30 22:00Z = apertura sesión CME del 1-jul-2025
END_NS = 1_790_805_600 * 1_000_000_000        # 2026-09-30 22:00Z = apertura sesión del 1-oct-2026 (holdout)
TICKS = {"ES": 0.25, "NQ": 0.25, "MES": 0.25, "MNQ": 0.25, "MYM": 1.0, "YM": 1.0, "RTY": 0.1, "GC": 0.1, "MGC": 0.1,
         "ZB": 1 / 32, "MBT": 5.0, "6E": 0.00005}
OLD_DIRS = [Path(r"E:\EdgeLab\data\nt8_2025_2026q3"), Path(r"E:\EdgeLab\data\nt8_ext_2026q3"),
            Path(r"E:\EdgeLab\data\nt8_overlap_2025_2026"), Path(r"E:\EdgeLab\data\nt8")]
CATS = ["buy", "sell", "unknown"]
COLS = ["ts_utc_ns", "price_ticks", "bid_ticks", "ask_ticks", "volume"]
DAY_NS = 86_400 * 10**9
ART_NS = 3 * 3600 * 10**9                     # día local NT8 (UTC-3) empieza a las 03:00Z


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def old_parquet(c):
    """Primer parquet viejo del contrato con las columnas canónicas (orden de preferencia de OLD_DIRS)."""
    for d in OLD_DIRS:
        for p in sorted(d.glob(f"*/{c}_ticks*.parquet")):
            if set(COLS) <= set(pq.ParquetFile(p).schema_arrow.names):
                return p
    return None


def day_bounds(day):
    d = np.datetime64(f"{day[:4]}-{day[4:6]}-{day[6:]}", "ns").astype(np.int64)
    return d + ART_NS, d + ART_NS + DAY_NS


def parse_txt(f, tick):
    for ch in pd.read_csv(f, sep=";", header=None, dtype={0: str}, chunksize=500_000, names=range(5), on_bad_lines="skip"):
        t = ch[0].astype(str)
        base = pd.to_datetime(t.str.slice(0, 15), format="%Y%m%d %H%M%S", errors="coerce")
        frac = pd.to_numeric(t.str.slice(16, 23), errors="coerce")
        ok = (base.notna() & frac.notna()).values
        ts = base.values[ok].astype("datetime64[ns]").astype(np.int64) + frac.values[ok].astype(np.int64) * 100
        arr = [np.round(ch[k].values[ok].astype(np.float64) / tick) for k in (1, 2, 3)]
        for k in (1, 2, 3):
            if np.abs(ch[k].values[ok].astype(np.float64) / tick - arr[k - 1]).max(initial=0) > 1e-6:
                raise ValueError(f"grilla de precios rota en {f}")
        yield ts, *(a.astype(np.int64) for a in arr), ch[4].values[ok].astype(np.int32), int((~ok).sum())


def build(c, out):
    inst = c.split("_")[0]; tick = TICKS[inst]; contract = c.replace("_", " ")
    man_new = [json.loads(l) for l in open(SRC / c / "manifest.jsonl", encoding="utf-8")]
    ok_days = sorted({r["day_nt_local"] for r in man_new if r["status"] == "OK" and (SRC / c / f"{r['day_nt_local']}.Last.utc.txt").exists()})
    repl = [day_bounds(d) for d in ok_days]
    old = old_parquet(c)
    # piezas en orden temporal: (inicio, tipo, dato)
    pieces = [(b[0], "new", d) for d, b in zip(ok_days, repl)]
    if old is not None:
        pieces.append((-1, "old", None))
    od = out / inst; od.mkdir(parents=True, exist_ok=True)
    dst = od / f"{c}_ticks_ext.parquet"; tmp = dst.with_suffix(".partial")
    w = None; n = 0; nonmono = 0; last = None; bad = 0; kept_old = 0
    per = defaultdict(lambda: dict(ticks=0, first=None, last=None, max_gap_s=0.0))
    rs = np.array([a for a, _ in repl], dtype=np.int64); re_ = np.array([b for _, b in repl], dtype=np.int64)

    def emit(ts, px, bd, ak, vol, src):
        nonlocal w, n, nonmono, last
        keep = (ts >= START_NS) & (ts < END_NS)
        ts, px, bd, ak, vol = ts[keep], px[keep], bd[keep], ak[keep], vol[keep]
        if not len(ts):
            return
        if last is not None and ts[0] < last:
            nonmono += 1
        nonmono += int((np.diff(ts) < 0).sum())
        td = trade_date_ymd(ts); mb = is_maintenance_break(ts)
        gap = (ts - np.r_[last if last is not None else ts[0], ts[:-1]]) / 1e9
        for d in np.unique(td):
            m = td == d; s = per[int(d)]; s["ticks"] += int(m.sum())
            s["first"] = int(ts[m][0]) if s["first"] is None else s["first"]; s["last"] = int(ts[m][-1])
            g = gap[m & ~mb]
            if s["first"] == int(ts[m][0]):           # el primer tick de la sesión no tiene hueco previo dentro de ella
                g = g[1:]
            if len(g):
                s["max_gap_s"] = max(s["max_gap_s"], float(g.max()))
        last = int(ts[-1]); k = len(ts); seq = np.arange(n, n + k, dtype=np.int64)
        cod = np.where(px >= ak, 0, np.where(px <= bd, 1, 2)).astype(np.int8)
        t = pa.table({"ts_utc_ns": ts, "ts_local_ns": ts, "sequence": seq, "price_ticks": px, "bid_ticks": bd, "ask_ticks": ak,
                      "volume": vol.astype(np.int32),
                      "aggressor": pa.DictionaryArray.from_arrays(pa.array(cod, pa.int8()), pa.array(CATS)).cast(pa.string()),
                      "tick_type": pa.array(["trade"] * k), "instrument": pa.array([inst] * k),
                      "contract": pa.array([contract] * k), "source_file": pa.array([src] * k), "source_row": seq})
        if w is None:
            w = pq.ParquetWriter(tmp, t.schema, compression="zstd")
        w.write_table(t, row_group_size=2_000_000); n += k

    # recorrido mezclado: los row groups viejos (filtrando intervalos reemplazados) intercalados con los días nuevos
    new_iter = iter(zip(ok_days, repl))
    nxt = next(new_iter, None)

    def flush_new_until(t_lim):
        nonlocal nxt, bad
        while nxt is not None and nxt[1][0] < t_lim:
            d, _ = nxt
            for ts, px, bd, ak, vol, b in parse_txt(SRC / c / f"{d}.Last.utc.txt", tick):
                bad += b; emit(ts, px, bd, ak, vol, f"reexport_20261004/{c}/{d}.Last.utc.txt")
            nxt = next(new_iter, None)

    if old is not None:
        f = pq.ParquetFile(old)
        for i in range(f.num_row_groups):
            t = f.read_row_group(i, columns=COLS)
            ts = t["ts_utc_ns"].to_numpy()
            if not len(ts):
                continue
            # emitir días nuevos que empiezan antes del primer tick viejo de este bloque
            # (se procesa en sub-bloques separados por los intervalos nuevos para mantener el orden)
            cuts = sorted(set([int(x) for x in rs if ts[0] < x <= ts[-1]] + [int(x) for x in re_ if ts[0] < x <= ts[-1]]))
            idx = np.searchsorted(ts, cuts)
            bounds = [0, *idx.tolist(), len(ts)]
            for a, b in zip(bounds[:-1], bounds[1:]):
                if a == b:
                    continue
                flush_new_until(int(ts[a]) + 1)
                seg = slice(a, b)
                tts = ts[seg]
                j = np.searchsorted(rs, tts, side="right") - 1
                inside = (j >= 0) & (tts < np.where(j >= 0, re_[np.clip(j, 0, None)], 0))
                m = ~inside
                kept_old += int(m.sum())
                emit(tts[m], *(t[k].to_numpy()[seg][m] for k in ("price_ticks", "bid_ticks", "ask_ticks")),
                     t["volume"].to_numpy()[seg][m], str(old))
    flush_new_until(np.iinfo(np.int64).max)
    if w is None:
        return dict(contract=c, rows=0)
    w.close(); tmp.replace(dst)
    sessions = {str(k): v for k, v in sorted(per.items())}
    (od / f"{c}_sessions_ext.json").write_text(json.dumps(sessions, indent=1), encoding="utf-8")
    man = dict(schema_version="canonical_tick_v1", tool="tools/nt8_reexport_merge.py", generated_utc=datetime.now(timezone.utc).isoformat(),
               instrument=inst, contract=contract, rows=n, tick_size=tick, window_utc_ns=[START_NS, END_NS],
               old_source=str(old) if old else None, old_rows_kept=kept_old, reexport_days_ok=len(ok_days),
               reexport_days_no_data=sorted({r["day_nt_local"] for r in man_new if r["status"] == "NO_DATA"} - set(ok_days)),
               non_monotonic=nonmono, unparsed_lines=bad, parquet_sha256=sha(dst))
    (od / f"{c}_manifest_ext.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    return man


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=r"E:\EdgeLab\data\nt8_reexport_20261005"); ap.add_argument("contracts", nargs="*")
    a = ap.parse_args(); out = Path(a.out)
    cs = a.contracts or sorted(p.name for p in SRC.iterdir() if p.is_dir() and (p / "manifest.jsonl").exists())
    for c in cs:
        m = build(c, out)
        print(c, m.get("rows"), "viejas", m.get("old_rows_kept"), "no_monot", m.get("non_monotonic"), flush=True)


if __name__ == "__main__":
    main()
