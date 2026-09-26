#!/usr/bin/env python3
"""Verifica la hipotesis del ruido de valor por celda en la paridad de aVolClusterPOI.

El cruce completo (docs/research/avolcluster_parity_full_20260902/) mostro que
mas del 75% de las discrepancias NO viene del filtro Low/High sino de RUIDO DE
VALOR: el volumen por celda difiere entre NT8 y Python en el 82% de los
bloques, y solo 16 de 22.200 bloques tienen celdas identicas.

HIPOTESIS: el .cs acumula sobre una subserie de "1 tick" de NT8
(Closes[1][0], Volumes[1][0]). Esa serie no es un tick individual: NT8
consolida trades con el MISMO timestamp en una sola barra, asignando el
volumen sumado a UN solo precio. Python (build_footprints) asigna el volumen
de cada tick a SU propio precio.

TEST: construir footprints alternativos con esa regla y ver cual coincide
mejor con las celdas reales de NT8.

  A_python_actual     : cada tick -> su precio (lo que hace hoy build_footprints)
  B_consolidado_last  : ticks con ts identico -> volumen total al precio del ULTIMO
  C_consolidado_first : idem, al precio del PRIMERO

Si B (o C) reduce mucho el ruido, la hipotesis queda confirmada y el fix queda
identificado. Si ninguna mejora, la causa es otra.

Target-free. NO modifica el .cs ni el kernel Python: computa variantes solo
dentro de este diagnostico.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
EXPECTED_COMMIT = "2f14636b89fbc8b9703049dd1f050bd87aa64481"
REPO_DIR = Path("/kaggle/working/EdgeLab")
KAGGLE_INPUT = Path("/kaggle/input")
DIAG_CSV = "data/nt8_oracles/avolcluster_v05_NQ0626_120t_DIAG_20260901.csv"
ART_TO_UTC_NS = 3 * 3600 * 10**9
TICKS_PER_BAR = 120
WINDOW_BARS = 10
TOL_NS = 2 * 10**9
OUT = Path("/kaggle/working/avolcluster_footprint_hypo")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def checkout(commit: str) -> str:
    if len(commit) != 40:
        raise SystemExit("EXPECTED_COMMIT debe ser SHA de 40 chars")
    if not (REPO_DIR / ".git").exists():
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
                        REPO_URL, str(REPO_DIR)], check=True)
        subprocess.run(["git", "sparse-checkout", "set", "--no-cone",
                        "edgelab/**", "data/nt8_oracles/**"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "fetch", "origin", commit, "--depth", "200"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "checkout", "-B", "fp_hypo", commit], cwd=REPO_DIR, check=True)
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


def main() -> int:
    commit = checkout(EXPECTED_COMMIT)
    print("repo_commit=", commit, flush=True)
    import numpy as np
    from edgelab.bridge import bars as bars_mod, ticks as ticks_mod
    from edgelab.bridge.ticks import TickSeries

    csv_path = REPO_DIR / DIAG_CSV
    with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = [ln for ln in f if not ln.startswith("# meta")]
    nt8 = []
    for r in csv.DictReader(lines):
        try:
            ts = parse_iso_ns(r["bar_close_time"]) + ART_TO_UTC_NS
        except ValueError:
            continue
        nt8.append({"ts": ts, "cells": parse_cells(r.get("cells"))})
    print("NT8 bloques=", len(nt8), flush=True)
    lo, hi = min(x["ts"] for x in nt8), max(x["ts"] for x in nt8)

    hits = sorted(KAGGLE_INPUT.rglob("NQ_06-26_ticks.parquet"))
    full = ticks_mod.load_canonical_parquet(str(hits[0]))
    idx = np.flatnonzero((full.ts_ns >= lo - 86400 * 10**9) & (full.ts_ns <= hi + 86400 * 10**9))
    t = TickSeries(ts_ns=full.ts_ns[idx], price_ticks=full.price_ticks[idx],
                   volume=full.volume[idx],
                   bid_ticks=full.bid_ticks[idx] if full.bid_ticks is not None else None,
                   ask_ticks=full.ask_ticks[idx] if full.ask_ticks is not None else None,
                   sequence=full.sequence[idx], tick_size=full.tick_size,
                   instrument=full.instrument, contract=full.contract, source=full.source)
    bars = bars_mod.build_tick_bars(t, TICKS_PER_BAR)
    print("ticks=", len(t.ts_ns), "bars=", len(bars.close_t), flush=True)

    ts = t.ts_ns
    px = t.price_ticks.astype(np.int64)
    vol = t.volume.astype(np.float64)
    bidx = bars.tick_bar_idx.astype(np.int64)

    same_ts = np.zeros(len(ts), bool)
    same_ts[1:] = ts[1:] == ts[:-1]
    n_same = int(same_ts.sum())
    new_bar = np.zeros(len(ts), bool)
    new_bar[0] = True
    new_bar[1:] = bidx[1:] != bidx[:-1]
    grp_start = (~same_ts) | new_bar
    gid = np.cumsum(grp_start) - 1
    n_groups = int(gid[-1]) + 1
    counts = np.bincount(gid)
    n_multi = int(np.sum(counts > 1))

    order = np.argsort(gid, kind="stable")
    starts = np.concatenate(([0], np.cumsum(counts)[:-1]))
    price_varies = 0
    for g in np.flatnonzero(counts > 1):
        seg = px[order[starts[g]:starts[g] + counts[g]]]
        if seg.min() != seg.max():
            price_varies += 1
    print("ts_repetidos=", n_same, "grupos=", n_groups,
          "multi=", n_multi, "con_precio_variable=", price_varies, flush=True)

    nb = len(bars.close_t)
    A = [dict() for _ in range(nb)]
    B = [dict() for _ in range(nb)]
    C = [dict() for _ in range(nb)]
    for i in range(len(ts)):
        b = int(bidx[i])
        k = int(px[i])
        A[b][k] = A[b].get(k, 0.0) + float(vol[i])
    for g in range(n_groups):
        sl = order[starts[g]:starts[g] + counts[g]]
        b = int(bidx[sl[0]])
        v = float(vol[sl].sum())
        pl = int(px[sl[-1]])
        pf = int(px[sl[0]])
        B[b][pl] = B[b].get(pl, 0.0) + v
        C[b][pf] = C[b].get(pf, 0.0) + v

    def block_cells(fpl, first_bar):
        out = {}
        for b in range(first_bar, first_bar + WINDOW_BARS):
            for k, v in fpl[b].items():
                out[k] = out.get(k, 0.0) + v
        return out

    end_ns = bars.end_ns
    block_end = []
    block_first = []
    for s in range(0, nb - WINDOW_BARS + 1, WINDOW_BARS):
        block_first.append(s)
        block_end.append(int(end_ns[s + WINDOW_BARS - 1]))
    block_end_arr = np.array(block_end)

    names = ("A", "B", "C")
    stats = {k: {"blocks_identical": 0, "sum_abs_diff": 0.0, "n_val_diff": 0,
                 "n_only_py": 0, "n_only_nt8": 0} for k in names}
    matched = 0
    for r in nt8:
        pos = int(np.searchsorted(block_end_arr, r["ts"]))
        best = None
        bd = None
        for k in (pos - 1, pos, pos + 1):
            if 0 <= k < len(block_end_arr):
                d = abs(int(block_end_arr[k]) - r["ts"])
                if bd is None or d < bd:
                    bd, best = d, k
        if best is None or bd > TOL_NS:
            continue
        matched += 1
        nc = r["cells"]
        for name, fpl in zip(names, (A, B, C)):
            pc = block_cells(fpl, block_first[best])
            only_py = set(pc) - set(nc)
            only_nt8 = set(nc) - set(pc)
            shared = set(pc) & set(nc)
            dv = [k for k in shared if abs(pc[k] - nc[k]) > 1e-9]
            s = stats[name]
            s["n_only_py"] += len(only_py)
            s["n_only_nt8"] += len(only_nt8)
            s["n_val_diff"] += len(dv)
            s["sum_abs_diff"] += sum(abs(pc[k] - nc[k]) for k in dv)
            if not only_py and not only_nt8 and not dv:
                s["blocks_identical"] += 1

    for k in names:
        stats[k]["sum_abs_diff"] = round(stats[k]["sum_abs_diff"], 3)

    report = {
        "schema": "avolclusterpoi_footprint_hypothesis_v1",
        "status": "DIAGNOSTIC_NO_CODE_CHANGED",
        "code_commit": commit,
        "nt8_csv_sha256": sha256(csv_path),
        "n_matched_blocks": matched,
        "tick_timestamp_structure": {
            "n_ticks": int(len(ts)),
            "ticks_sharing_ts_with_previous": n_same,
            "pct_sharing_ts": round(float(n_same) / len(ts), 6),
            "n_groups": n_groups,
            "n_multi_tick_groups": n_multi,
            "n_multi_groups_with_price_variation": price_varies},
        "variants": {
            "A_python_actual": stats["A"],
            "B_consolidado_precio_ultimo": stats["B"],
            "C_consolidado_precio_primero": stats["C"]},
        "interpretation": ("si B o C sube mucho blocks_identical y baja n_val_diff frente a A, "
                           "la consolidacion de trades simultaneos explica el ruido y el fix "
                           "queda identificado; si las tres son parecidas, la causa es otra"),
        "outcomes_accessed": False,
        "holdout_accessed": False,
        "code_modified": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "footprint_hypothesis_v1.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
