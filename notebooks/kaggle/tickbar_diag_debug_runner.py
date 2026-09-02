#!/usr/bin/env python3
"""Debug: compare raw price sequences from ledger vs parquet directly.

Not the classifier -- just enough to see whether the window slice (tz-shift)
landed on the same real-world moment, or on genuinely different data.
"""
from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
EXPECTED_COMMIT = "6920801062f303f69278d78803c658d7ae017985"
REPO_DIR = Path("/kaggle/working/EdgeLab")
DATA_DIR = "/kaggle/input/datasets/nicolasbuttaro/edgelab-ticks-nq-preholdout"
LEDGER_PATH = "/kaggle/input/datasets/nicolasbuttaro/edgelab-tickbar-diag-nq0626/tickbar_diag_NQ0626__Tick120.csv"

if not (REPO_DIR / ".git").exists():
    subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(REPO_DIR)], check=True)
subprocess.run(["git", "fetch", "origin", EXPECTED_COMMIT, "--depth", "200"], cwd=REPO_DIR, check=True)
subprocess.run(["git", "checkout", "-B", "debug", EXPECTED_COMMIT], cwd=REPO_DIR, check=True)

sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(REPO_DIR / "tools"))
from tickbar_diag import read_ledger  # noqa: E402
from edgelab.bridge import ticks as ticks_mod  # noqa: E402


def _ns(iso):
    return int(dt.datetime.fromisoformat(iso[:26]).replace(tzinfo=dt.timezone.utc).timestamp() * 1e9)


ev, nt_bars, meta = read_ledger(LEDGER_PATH)
print("n_events=", len(ev), "n_nt_bars=", len(nt_bars), flush=True)
print("first ev ts_iso=", ev[0]["ts_iso"], "last ev ts_iso=", ev[-1]["ts_iso"], flush=True)

parquet_hits = list(Path(DATA_DIR).rglob("NQ_06-26_ticks.parquet"))
parquet_path = parquet_hits[0]

for shift_h in (0, 3, -3, 2, -2, 5, -5):
    shift = int(shift_h * 3600 * 1e9)
    w0 = _ns(ev[0]["ts_iso"]) + shift
    w1 = _ns(ev[-1]["ts_iso"]) + shift + 1
    w0_utc = dt.datetime.fromtimestamp(w0 / 1e9, tz=dt.timezone.utc)
    w1_utc = dt.datetime.fromtimestamp(w1 / 1e9, tz=dt.timezone.utc)
    try:
        tk = ticks_mod.load_canonical_parquet(str(parquet_path), contract="NQ 06-26",
                                              start_utc_ns=w0, end_utc_ns=w1)
        n = len(tk.ts_ns)
    except Exception as exc:
        print(f"shift={shift_h:+.0f}h window_utc=[{w0_utc},{w1_utc}) ERROR={exc}", flush=True)
        continue
    py_p = tk.price_ticks[:5].tolist() if n else []
    print(f"shift={shift_h:+.0f}h window_utc=[{w0_utc},{w1_utc}) n_ticks={n} first_prices={py_p}", flush=True)

nt_p = [e["price_tick"] for e in ev[:5]]
print("ledger first price_ticks=", nt_p, flush=True)
print("ledger tick_size=", meta.get("tick_size"), flush=True)
