#!/usr/bin/env python3
"""TICKBAR-001 classifier v2: separates bar cuts from event attribution.

This file is versioned instead of silently rewriting the spent v1 classifier.
H2 is measured from primary-bar OHLC identity. `n_events`, seq_first/last and
footprint digest belong to attribution (H3), never to the bar-cut gate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO, "tools")
sys.path.insert(0, REPO)
sys.path.insert(0, TOOLS)

from tickbar_diag import read_ledger, stream_digest, fp_digest  # noqa: E402
from edgelab.bridge import bars as bars_mod, ticks as ticks_mod  # noqa: E402


def _ns(iso):
    return int(dt.datetime.fromisoformat(iso[:26]).replace(
        tzinfo=dt.timezone.utc).timestamp() * 1e9)


def ohlc_equal(nt_bar, py_bars, j):
    return (nt_bar["o"] == int(py_bars.open_t[j])
            and nt_bar["h"] == int(py_bars.high_t[j])
            and nt_bar["l"] == int(py_bars.low_t[j])
            and nt_bar["c"] == int(py_bars.close_t[j]))


def align_by_ohlc(nt_bars, py_bars, probe=200, max_offset=5000):
    """Return deterministic OHLC alignment and its score.

    The smallest offset wins ties and ambiguity is reported. Callers must not
    interpret a partial score as equal cuts.
    """
    if not nt_bars or len(py_bars) == 0:
        return 0, 0, 0
    limit = min(max_offset, max(0, len(py_bars) - 1))
    scored = []
    for off in range(limit + 1):
        m = min(len(nt_bars), len(py_bars) - off, probe)
        if m <= 0:
            continue
        score = sum(ohlc_equal(nt_bars[i], py_bars, off + i) for i in range(m))
        scored.append((score, off))
    best_score = max((x[0] for x in scored), default=0)
    winners = [off for score, off in scored if score == best_score]
    return min(winners, default=0), best_score, len(winners)


def classify(stream_ok, cuts_ok, attribution_ok):
    signatures = []
    if not stream_ok:
        signatures.append("STREAM")
    if stream_ok and not cuts_ok:
        signatures.append("BAR_BUILDER")
    if stream_ok and cuts_ok and attribution_ok is False:
        signatures.append("ATTRIBUTION")
    if not signatures:
        return "NO_MISMATCH"
    return "MIXED_MISMATCH" if len(signatures) > 1 else signatures[0] + "_MISMATCH"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("ledger")
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--tick-n", required=True, type=int)
    ap.add_argument("--tz-shift-hours", default=0.0, type=float)
    a = ap.parse_args(argv)

    ev, nt_bars, meta = read_ledger(a.ledger)
    if not ev or not nt_bars:
        print("FRENAR: ledger incompleto")
        return 1
    if meta.get("bars_period") != "Tick" or str(meta.get("bars_value")) != str(a.tick_n):
        print("FRENAR: resolucion del ledger incompatible")
        return 1

    shift = int(a.tz_shift_hours * 3600 * 1e9)
    w0 = _ns(ev[0]["ts_iso"]) + shift
    w1 = _ns(ev[-1]["ts_iso"]) + shift + 1
    tk = ticks_mod.load_canonical_parquet(a.parquet, contract=a.contract,
                                          start_utc_ns=w0, end_utc_ns=w1)
    py_p = tk.price_ticks.astype(np.int64)
    py_v = np.round(tk.volume * 100).astype(np.int64)
    nt_p = np.asarray([e["price_tick"] for e in ev], dtype=np.int64)
    nt_v = np.asarray([e["vol_int"] for e in ev], dtype=np.int64)
    n = min(len(py_p), len(nt_p))
    stream_ok = (len(py_p) == len(nt_p)
                 and np.array_equal(py_p[:n], nt_p[:n])
                 and np.array_equal(py_v[:n], nt_v[:n])
                 and stream_digest(py_p[:n], py_v[:n]) == ev[-1]["digest"])

    py_bars = bars_mod.build_tick_bars(tk, a.tick_n)
    off, probe_score, ties = align_by_ohlc(nt_bars, py_bars)
    m = min(len(nt_bars), len(py_bars) - off)
    cuts_equal = sum(ohlc_equal(nt_bars[i], py_bars, off + i) for i in range(m))
    cuts_ok = m > 0 and cuts_equal == m

    attribution_diff = 0
    if stream_ok and cuts_ok:
        fps = bars_mod.build_footprints(tk, py_bars)
        for i in range(m):
            j = off + i
            if fp_digest(fps.ask[j], fps.bid[j]) != nt_bars[i]["digest_fp"]:
                attribution_diff += 1
        attribution_ok = attribution_diff == 0
    else:
        attribution_ok = None

    verdict = classify(stream_ok, cuts_ok, attribution_ok)
    print("TICKBAR-001 classifier_contract=v2_ohlc_cuts")
    print("alignment_offset=%d probe_score=%d ambiguity=%d" % (off, probe_score, ties))
    print("H1 stream      : %s" % ("OK" if stream_ok else "MISMATCH"))
    print("H2 cortes OHLC : %s (%d/%d)" % ("OK" if cuts_ok else "MISMATCH", cuts_equal, m))
    print("H3 atribucion  : %s" % ("no evaluable" if attribution_ok is None else
                                      ("OK" if attribution_ok else "MISMATCH %d/%d" % (attribution_diff, m))))
    print("CLASIFICACION: %s" % verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
