#!/usr/bin/env python3
"""Reconstruct exact NT8 history counts from the existing all-block CSV.

The old exporter wrote hist_samples=0 whenever the minimum was not met. This
script recovers the actual 0..19 count without changing or rerunning the frozen
indicator: one score per block (maximum candidate score, or zero), prior
complete sessions only, FIFO by LookbackSessions and bucket.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def candidate_score(clusters):
    if not clusters:
        return 0.0
    return max(float(token.split(":")[2]) for token in clusters.split("|") if token)


def reconstruct(rows, lookback_sessions=20, min_samples=20):
    by_session_bucket = defaultdict(list)
    seen_seq = set()
    previous_seq = None
    for row in rows:
        seq = int(row["diag_seq"])
        if seq in seen_seq:
            raise RuntimeError("diag_seq duplicado: {}".format(seq))
        if previous_seq is not None and seq <= previous_seq:
            raise RuntimeError("diag_seq fuera de orden: {} despues de {}".format(seq, previous_seq))
        seen_seq.add(seq)
        previous_seq = seq
        session = int(row["session_index"])
        bucket = int(row["bucket"])
        by_session_bucket[(session, bucket)].append(candidate_score(row.get("clusters", "")))

    output = []
    validation_mismatches = []
    for row in rows:
        session = int(row["session_index"])
        bucket = int(row["bucket"])
        lower_session = session - int(lookback_sessions)
        history = [score
                   for (hist_session, hist_bucket), scores in by_session_bucket.items()
                   if hist_bucket == bucket and lower_session <= hist_session < session
                   for score in scores]
        reconstructed = len(history)
        logged = int(row.get("hist_samples") or 0)
        threshold_available = row.get("threshold") not in (None, "")
        if threshold_available and logged != reconstructed:
            validation_mismatches.append({"diag_seq": int(row["diag_seq"]),
                                          "logged": logged,
                                          "reconstructed": reconstructed})
        output.append({"diag_seq": int(row["diag_seq"]),
                       "bar_index": int(row["bar_index"]),
                       "bar_close_time": row["bar_close_time"],
                       "session_index": session, "bucket": bucket,
                       "decision": row.get("decision"),
                       "best_candidate_score": candidate_score(row.get("clusters", "")),
                       "logged_hist_samples": logged,
                       "reconstructed_hist_samples": reconstructed,
                       "history_ready": reconstructed >= int(min_samples),
                       "logged_count_was_censored": not threshold_available})
    if validation_mismatches:
        raise RuntimeError("reconstruccion no coincide con {} filas no censuradas; primera={}".format(
            len(validation_mismatches), validation_mismatches[0]))
    return output


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("diag_csv", type=Path)
    parser.add_argument("--lookback-sessions", type=int, default=20)
    parser.add_argument("--min-samples", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("nt8_history_reconstructed.json"))
    args = parser.parse_args(argv)
    with args.diag_csv.open(encoding="utf-8", newline="") as fh:
        meta = fh.readline().rstrip("\n")
        rows = list(csv.DictReader(fh))
    reconstructed = reconstruct(rows, args.lookback_sessions, args.min_samples)
    decisions = Counter(r["decision"] for r in reconstructed)
    no_history_counts = Counter(r["reconstructed_hist_samples"] for r in reconstructed
                                if r["decision"] == "ABSTAIN_NO_HISTORY")
    payload = {"source_meta": meta,
               "method": "prior_complete_sessions_same_bucket_fifo",
               "lookback_sessions": args.lookback_sessions,
               "min_samples": args.min_samples,
               "n_rows": len(reconstructed),
               "decision_counts": dict(decisions),
               "no_history_reconstructed_count_distribution": dict(sorted(no_history_counts.items())),
               "rows": reconstructed}
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("n_rows=", len(reconstructed))
    print("no_history_counts=", dict(sorted(no_history_counts.items())))
    print("output=", args.output)


if __name__ == "__main__":
    main()
