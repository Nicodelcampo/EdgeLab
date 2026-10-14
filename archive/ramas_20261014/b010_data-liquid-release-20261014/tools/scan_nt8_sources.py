#!/usr/bin/env python3
"""Pase 1 de la release líquida: escanea TODOS los exports NT8 de texto y guarda evidencia por (fuente, fecha cruda, hora).

No asume huso, no calcula retornos, no lee holdout (corte en bytes; archivos B con día >= 20261001 ni se abren).
Reanudable: cada fuente escribe su parte en <out>/parts/<id>.parquet y su ficha en <out>/parts/<id>.json.

Uso: python tools/scan_nt8_sources.py --out D:/edgelab_release_work/scan [--workers 2] [--only ES]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

A_ROOT = Path(r"E:\EdgeLab\data\nt8")
B_ROOTS = [Path(r"E:\DatosNT8") / d for d in (
    "tick_history", "tick_history_reexport_20261004", "tick_history_nt8_solape", "tick_history_MGC_20261002",
    "tick_history_completar_20261001", "tick_history_explo_20261006")]
CUTOFF_UTC_PREFIX = b"20260930 220000"       # trade-date >= 2026-10-01 empieza 22:00Z (17:00 CDT) del 30-sep
HOLDOUT_FIRST_DAY_NT = "20261001"            # día NT-local (ART) cuyo contenido es 100 % posterior al corte

# tamaños de tick de las especificaciones CME, verificados contra la grilla de los datos (columnas off_*)
TICK = {"ES": 0.25, "NQ": 0.25, "MES": 0.25, "MNQ": 0.25, "YM": 1.0, "MYM": 1.0, "ZB": 0.03125, "GC": 0.1, "MGC": 0.1,
        "RTY": 0.1, "6E": 0.00005, "6B": 0.0001, "6J": 0.0000005, "MBT": 5.0}
A_FILE = re.compile(r"^([A-Z0-9]+) (\d\d-\d\d)\.Last\.txt$")
B_FILE = re.compile(r"^(\d{8})\.Last\.utc\.txt$")


def enumerate_sources(only=None):
    srcs = []
    for d in sorted(A_ROOT.iterdir()):
        if not d.is_dir() or d.name.endswith("_parquet") or d.name.startswith("6E_prev") or d.name in ("BTC",):
            continue
        kind = "A2" if d.name == "Nuevo mbt" else "A"
        for f in sorted(d.iterdir()):
            m = A_FILE.match(f.name)
            if m and f.stat().st_size > 0:
                srcs.append(dict(kind=kind, root=str(A_ROOT), path=str(f), instrument=m.group(1),
                                 contract=f"{m.group(1)} {m.group(2)}", day=None))
    for root in B_ROOTS:
        if not root.exists():
            continue
        for cdir in sorted(root.iterdir()):
            if not cdir.is_dir() or "_" not in cdir.name:
                continue
            inst, mm = cdir.name.split("_", 1)
            for f in sorted(cdir.iterdir()):
                m = B_FILE.match(f.name)
                if m and f.stat().st_size > 0:
                    srcs.append(dict(kind="B", root=str(root), path=str(f), instrument=inst,
                                     contract=f"{inst} {mm}", day=m.group(1)))
    out = []
    for s in srcs:
        s["id"] = re.sub(r"[^A-Za-z0-9_.-]", "_", f"{s['kind']}__{Path(s['root']).name}__{s['contract']}__{s['day'] or 'all'}")
        s["bytes"] = Path(s["path"]).stat().st_size
        if only and s["instrument"] not in only:
            continue
        out.append(s)
    return out


def scan_one(src, parts):
    import pandas as pd
    from edgelab.data.liquid_release.hourly_scan import scan_file
    pid = parts / (src["id"] + ".json")
    if pid.exists():
        return src["id"], "cached", 0.0
    t0 = time.time()
    tick = TICK[src["instrument"]]
    if src["kind"] == "B":
        if src["day"] >= HOLDOUT_FIRST_DAY_NT:
            rec = dict(src, skipped="holdout_day_not_opened", elapsed_s=0.0)
            pid.write_text(json.dumps(rec), encoding="utf-8")
            return src["id"], "skip_holdout", 0.0
        cutoff = CUTOFF_UTC_PREFIX if src["day"] >= "20260930" else None
        chunk = 8 << 20
    else:
        cutoff = b"20260930 000000"       # A no debería llegar ni cerca; si llega, se corta y se avisa
        chunk = 64 << 20
    df, info = scan_file(src["path"], tick, cutoff_prefix=cutoff, chunk_bytes=chunk)
    if len(df):
        df.insert(0, "source_id", src["id"])
        df.to_parquet(parts / (src["id"] + ".parquet"), index=False)
    rec = dict(src, **info, elapsed_s=round(time.time() - t0, 1), tick=tick, cutoff=None if cutoff is None else cutoff.decode())
    pid.write_text(json.dumps(rec), encoding="utf-8")
    return src["id"], "ok", rec["elapsed_s"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    out = Path(a.out)
    parts = out / "parts"
    parts.mkdir(parents=True, exist_ok=True)
    srcs = enumerate_sources(set(a.only) if a.only else None)
    # los archivos grandes primero (mejor reparto entre procesos)
    srcs.sort(key=lambda s: -s["bytes"])
    (out / "sources.json").write_text(json.dumps(srcs, indent=1), encoding="utf-8")
    print(f"{len(srcs)} fuentes, {sum(s['bytes'] for s in srcs) / 1e9:.1f} GB", flush=True)
    t0 = time.time()
    done = 0
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(scan_one, s, parts): s for s in srcs}
        for f in as_completed(futs):
            s = futs[f]
            try:
                sid, st, el = f.result()
            except Exception as e:                       # una fuente rota no frena el resto: queda registrada
                (parts / (s["id"] + ".error.json")).write_text(json.dumps(dict(s, error=repr(e))), encoding="utf-8")
                sid, st, el = s["id"], f"ERROR {e!r}", 0.0
            done += 1
            if done % 25 == 0 or s["bytes"] > 5e8 or st.startswith("ERROR"):
                print(f"[{done}/{len(srcs)}] {sid} {st} {el}s  total {time.time() - t0:.0f}s", flush=True)
    print("FIN", time.time() - t0, flush=True)


if __name__ == "__main__":
    main()
