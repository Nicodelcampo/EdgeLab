#!/usr/bin/env python3
"""Set-based comparison of ledger vs parquet ticks in the shift=+3h window.

Task 1 (auditor order 025/026): find whether the ~3-tick STREAM_MISMATCH is
a reordering/interleaving artifact or genuinely different content, before
touching the classifier's alignment logic.
"""
from __future__ import annotations

import datetime as dt
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
EXPECTED_COMMIT = "eb40171c947a9b7273a56307309a48136cf58a56"
REPO_DIR = Path("/kaggle/working/EdgeLab")
DATA_DIR = "/kaggle/input/datasets/nicolasbuttaro/edgelab-ticks-nq-preholdout"
LEDGER_PATH = "/kaggle/input/datasets/nicolasbuttaro/edgelab-tickbar-diag-nq0626/tickbar_diag_NQ0626__Tick120.csv"


def _ns(iso):
    return int(dt.datetime.fromisoformat(iso[:26]).replace(tzinfo=dt.timezone.utc).timestamp() * 1e9)


def main():
    if not (REPO_DIR / ".git").exists():
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(REPO_DIR)], check=True)
    subprocess.run(["git", "fetch", "origin", EXPECTED_COMMIT, "--depth", "200"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "checkout", "-B", "setcmp", EXPECTED_COMMIT], cwd=REPO_DIR, check=True)

    sys.path.insert(0, str(REPO_DIR))
    sys.path.insert(0, str(REPO_DIR / "tools"))
    from tickbar_diag import read_ledger
    from edgelab.bridge import ticks as ticks_mod

    ev, nt_bars, meta = read_ledger(LEDGER_PATH)
    print("n_events=", len(ev), flush=True)

    shift = int(3 * 3600 * 1e9)
    w0 = _ns(ev[0]["ts_iso"]) + shift
    w1 = _ns(ev[-1]["ts_iso"]) + shift + 1

    parquet_hits = list(Path(DATA_DIR).rglob("NQ_06-26_ticks.parquet"))
    tk = ticks_mod.load_canonical_parquet(str(parquet_hits[0]), contract="NQ 06-26",
                                          start_utc_ns=w0, end_utc_ns=w1)
    n = len(tk.ts_ns)
    print("n_parquet_ticks=", n, flush=True)

    ledger_pairs = Counter((int(e["price_tick"]), int(e["vol_int"])) for e in ev)
    py_pairs = Counter(zip(tk.price_ticks.tolist(), (tk.volume * 100).round().astype(int).tolist()))

    only_ledger = ledger_pairs - py_pairs
    only_py = py_pairs - ledger_pairs
    print("n_distinct_pairs_ledger=", len(ledger_pairs), flush=True)
    print("n_distinct_pairs_py=", len(py_pairs), flush=True)
    print("sum_only_in_ledger=", sum(only_ledger.values()), flush=True)
    print("sum_only_in_py=", sum(only_py.values()), flush=True)
    print("only_ledger sample:", list(only_ledger.items())[:10], flush=True)
    print("only_py sample:", list(only_py.items())[:10], flush=True)

    # Where in the parquet window (start or end) do the extras concentrate?
    # Tag each parquet tick position with whether its (price,vol) pair is
    # "extra" (appears more times in py than in ledger).
    remaining = Counter(only_py)
    extra_positions = []
    for i, (p, v) in enumerate(zip(tk.price_ticks.tolist(), (tk.volume * 100).round().astype(int).tolist())):
        key = (p, v)
        if remaining.get(key, 0) > 0:
            extra_positions.append(i)
            remaining[key] -= 1
    print("extra_py_tick_positions (of", n, "):", extra_positions[:20], flush=True)
    if extra_positions:
        print("first extra ts=", int(tk.ts_ns[extra_positions[0]]), "last extra ts=", int(tk.ts_ns[extra_positions[-1]]), flush=True)
        print("window ts range=", int(tk.ts_ns[0]), int(tk.ts_ns[-1]), flush=True)


if __name__ == "__main__":
    main()
