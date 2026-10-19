#!/usr/bin/env python3
"""FASE 4: barrido de FASE de la particion de barras de tick.

Fases previas:
  F2  desalineacion de barras REFUTADA (offset 0 al 99,98%, dt mediano 0 ns).
  F3  filtro Low[0]/High[0] REFUTADO (descarta 0 ticks; A=B=C identicos).
      Pero correr la asignacion un tick hacia adelante (variante E) llevo los
      bloques con celdas exactas de 16 a 2118 (x132). Hay un off-by-one real.

E era un re-etiquetado, no una re-particion: movia ticks de barra sin conservar
las 120 por barra. Este kernel prueba la version correcta -- una FASE k en el
conteo de ticks por barra, aplicada DENTRO de cada sesion (build_tick_bars
reinicia el contador por sesion, TICKBAR-001).

    bucket = (rank_en_sesion - k) // 120

k=0 es el kernel actual. Si algun k != 0 dispara los bloques exactos, la causa
de la no-paridad es que NT8 empieza a contar la barra en un tick distinto del
primero que ve el parquet -- y eso se corrige en el kernel Python, sin tocar
el .cs.

Que los timestamps coincidieran perfecto en F2 NO contradice esto: el 51% de
los ticks de NQ comparte timestamp, asi que una barra desfasada por pocos ticks
cierra en el MISMO nanosegundo.

Target-free. No modifica el .cs ni el kernel.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
EXPECTED_COMMIT = "706c4fe261eec3f856cf84cc66f6d3d31f0f6680"
REPO_DIR = Path("/kaggle/working/EdgeLab")
KAGGLE_INPUT = Path("/kaggle/input")
DIAG_CSV = "data/nt8_oracles/avolcluster_v05_NQ0626_120t_DIAG_20260901.csv"
ART_TO_UTC_NS = 3 * 3600 * 10**9
TICKS_PER_BAR = 120
WINDOW_BARS = 10
OUT = Path("/kaggle/working/avolcluster_phase")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def checkout(commit: str) -> str:
    if len(commit) != 40:
        raise SystemExit("EXPECTED_COMMIT debe ser SHA de 40 chars")
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    if not (REPO_DIR / ".git").exists():
        last = None
        for attempt in range(4):
            r = subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
                                REPO_URL, str(REPO_DIR)], env=env)
            if r.returncode == 0:
                break
            last = r.returncode
            subprocess.run(["rm", "-rf", str(REPO_DIR)])
            time.sleep(5 * (attempt + 1))
        else:
            raise SystemExit(f"git clone fallo tras 4 intentos (rc={last})")
        subprocess.run(["git", "sparse-checkout", "set", "--no-cone",
                        "edgelab/**", "data/nt8_oracles/**"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "fetch", "origin", commit, "--depth", "200"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "checkout", "-B", "lowhigh", commit], cwd=REPO_DIR, check=True)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
    if actual != commit:
        raise SystemExit("code provenance gate failed")
    sys.path.insert(0, str(REPO_DIR))
    return actual


def parse_cells(text):
    out = {}
    for part in (text or "").split("|"):
        if not part:
            continue
        t, _, v = part.partition(":")
        try:
            out[int(t)] = float(v)
        except ValueError:
            pass
    return out


def parse_iso_ns(s):
    import datetime as dt
    s = s.strip().replace("/", "-")
    for f in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
              "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return int(dt.datetime.strptime(s, f).replace(
                tzinfo=dt.timezone.utc).timestamp() * 10**9)
        except ValueError:
            continue
    raise ValueError(s)




PHASES = list(range(-6, 7))


def main() -> int:
    t0 = time.time()
    commit = checkout(EXPECTED_COMMIT)
    print("repo_commit=", commit, flush=True)
    import numpy as np
    from edgelab.bridge import bars as bars_mod, ticks as ticks_mod
    from edgelab.bridge.ticks import TickSeries

    csv_path = REPO_DIR / DIAG_CSV
    with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = [l for l in f if not l.startswith("# meta")]
    nt8 = []
    for r in csv.DictReader(lines):
        try:
            ts = parse_iso_ns(r["bar_close_time"]) + ART_TO_UTC_NS
        except ValueError:
            continue
        c = parse_cells(r.get("cells"))
        if c:
            nt8.append({"ts": ts, "cells": c, "vol": sum(c.values())})
    print("NT8 bloques=", len(nt8), flush=True)
    lo_ns, hi_ns = min(x["ts"] for x in nt8), max(x["ts"] for x in nt8)

    hits = sorted(KAGGLE_INPUT.rglob("NQ_06-26_ticks.parquet"))
    full = ticks_mod.load_canonical_parquet(str(hits[0]))
    idx = np.flatnonzero((full.ts_ns >= lo_ns - 3 * 86400 * 10**9)
                         & (full.ts_ns <= hi_ns + 86400 * 10**9))
    t = TickSeries(ts_ns=full.ts_ns[idx], price_ticks=full.price_ticks[idx],
                   volume=full.volume[idx],
                   bid_ticks=full.bid_ticks[idx] if full.bid_ticks is not None else None,
                   ask_ticks=full.ask_ticks[idx] if full.ask_ticks is not None else None,
                   sequence=full.sequence[idx], tick_size=full.tick_size,
                   instrument=full.instrument, contract=full.contract, source=full.source)
    px = t.price_ticks.astype(np.int64)
    vol = t.volume.astype(np.float64)
    n = len(px)

    # misma nocion de sesion que build_tick_bars (TICKBAR-001)
    sess = bars_mod.session_ids(t.ts_ns).astype(np.int64)
    first_of_sess = np.flatnonzero(np.concatenate(([True], sess[1:] != sess[:-1])))
    rank = np.arange(n, dtype=np.int64) - np.repeat(
        first_of_sess, np.diff(np.concatenate((first_of_sess, [n]))))
    print("ticks=", n, "sesiones=", len(first_of_sess), flush=True)

    span = int(px.max() - px.min()) + 1
    base = int(px.min())
    ts_arr = np.array([x["ts"] for x in nt8], dtype=np.int64)

    results = {}
    for k in PHASES:
        bucket = np.floor_divide(rank - k, TICKS_PER_BAR)
        bar_id = sess * 10**9 + (bucket - bucket.min())
        newbar = np.concatenate(([True], bar_id[1:] != bar_id[:-1]))
        bstart = np.flatnonzero(newbar)
        nb = len(bstart)
        bidx = np.cumsum(newbar) - 1
        bend_ns = t.ts_ns[np.concatenate((bstart[1:] - 1, [n - 1]))]

        key = bidx * span + (px - base)
        o = np.argsort(key, kind="stable")
        ks, vs = key[o], vol[o]
        e = np.flatnonzero(np.concatenate(([True], ks[1:] != ks[:-1])))
        sums = np.add.reduceat(vs, e)
        ub = (ks[e] // span).astype(np.int64)
        up = (ks[e] % span + base).astype(np.int64)
        st = np.searchsorted(ub, np.arange(nb), side="left")
        en = np.searchsorted(ub, np.arange(nb), side="right")

        pos = np.searchsorted(bend_ns, ts_arr)
        exact_cells = exact_vol = matched = 0
        sad = 0.0
        for i in range(len(nt8)):
            p = int(pos[i]); best = None; bd = None
            for c in (p - 1, p, p + 1):
                if 0 <= c < nb:
                    d = abs(int(bend_ns[c]) - int(ts_arr[i]))
                    if bd is None or d < bd:
                        bd, best = d, c
            if best is None or bd > 10**9 or best - WINDOW_BARS + 1 < 0:
                continue
            matched += 1
            pc = {}
            for b in range(best - WINDOW_BARS + 1, best + 1):
                for j in range(st[b], en[b]):
                    kk = int(up[j]); pc[kk] = pc.get(kk, 0.0) + float(sums[j])
            nc = nt8[i]["cells"]
            sad += sum(abs(pc.get(x, 0.0) - nc.get(x, 0.0)) for x in (set(pc) | set(nc)))
            if abs(sum(pc.values()) - nt8[i]["vol"]) < 1e-9:
                exact_vol += 1
            if pc == nc or (set(pc) == set(nc) and all(abs(pc[x] - nc[x]) < 1e-9 for x in pc)):
                exact_cells += 1
        results[str(k)] = {"matched": matched, "n_bars": int(nb),
                           "exact_cells": exact_cells, "exact_volume": exact_vol,
                           "exact_cells_pct": round(exact_cells / matched, 6) if matched else None,
                           "sum_abs_diff": round(sad, 1)}
        print("k=", k, results[str(k)], "t=", round(time.time() - t0, 1), flush=True)

    best_k = min(results, key=lambda z: results[z]["sum_abs_diff"])
    report = {
        "schema": "avolclusterpoi_bar_phase_sweep_v1",
        "status": "DIAGNOSTIC_NO_CODE_CHANGED",
        "code_commit": commit, "nt8_csv_sha256": sha256(csv_path),
        "n_nt8_blocks": len(nt8), "phases": results,
        "best_phase_by_sad": best_k,
        "best_phase_by_exact": max(results, key=lambda z: results[z]["exact_cells"]),
        "baseline_phase_0": results["0"],
        "elapsed_seconds": round(time.time() - t0, 1),
        "outcomes_accessed": False, "holdout_accessed": False, "code_modified": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "phase_report_v1.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
