# -*- coding: utf-8 -*-
"""Read an aVolClusterPOI NT8 event log. Structural only.

Ignores outcome, mfe, mae, quality_score for any decision.
"""
from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

IGNORE_FOR_DECISIONS = {
    "quality_score", "direction", "outcome", "mfe_ticks", "mae_ticks",
    "touch_bar", "anomaly_ratio", "cluster_share", "density", "burst_count",
}


def load_log(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("# meta"):
        raise SystemExit("falta la linea # meta")
    meta = {}
    for part in lines[0][1:].split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            meta[k.strip()] = v.strip()
    header_i = next(i for i, line in enumerate(lines) if line.startswith("event_seq"))
    rows = list(csv.DictReader(lines[header_i:]))
    return meta, rows


def summarize(meta, rows):
    created = [r for r in rows if r.get("event_type") == "ZONE_CREATED"]
    by_session = defaultdict(list)
    widths = []
    buckets = Counter()
    for row in created:
        session = row.get("session_index") or ""
        by_session[session].append(row)
        try:
            widths.append(int(row["upper_tick"]) - int(row["lower_tick"]) + 1)
        except (TypeError, ValueError):
            pass
        if row.get("bucket"):
            buckets[row["bucket"]] += 1
    n = len(created)
    n_sess = len(by_session)
    per = [len(v) for v in by_session.values()]
    return dict(
        meta_percentile=meta.get("percentile"),
        meta_min_samples=meta.get("min_samples"),
        meta_filter=meta.get("predictive_filter"),
        n_created=n,
        n_sessions_with_zone=n_sess,
        zones_per_session_p50=sorted(per)[len(per) // 2] if per else 0,
        width_p50=sorted(widths)[len(widths) // 2] if widths else None,
        n_buckets_used=len(buckets),
        ignored_fields=sorted(IGNORE_FOR_DECISIONS),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    args = ap.parse_args()
    meta, rows = load_log(Path(args.csv_path))
    print(summarize(meta, rows))


if __name__ == "__main__":
    main()
