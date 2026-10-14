#!/usr/bin/env python3
"""Construye el censo por sesión de la release líquida a partir de uno o más directorios de escaneo.

Salidas en <out>: tz_groups.csv, dup_blocks.parquet, annotated_bins.parquet, session_census.parquet, summary.json.
Uso: python tools/build_census.py --scan D:/.../scan2 [--scan D:/.../scanP] --out D:/.../census
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.data.liquid_release.calendar_tz import violation_by_offset  # noqa: E402
from edgelab.data.liquid_release.census import annotate, load_scan, merge_group_bins, session_census  # noqa: E402


def tz_verdicts(merged: pd.DataFrame) -> pd.DataFrame:
    """Huso por grupo: con >= 5.000 ticks, UTC se acepta si la violación del calendario CME es <= 0,5 % y ART (-3) viola
    >= 2 pp más; los trimestres con >= 5.000 ticks y violación > 0,5 % quedan listados."""
    rows = []
    for grp, b in merged.groupby("group"):
        agg = b[["raw_date", "raw_hour", "n"]]
        v = violation_by_offset(agg)
        best = min(v, key=v.get)
        d = dict(group=grp, instrument=b["instrument"].iloc[0], contract=b["contract"].iloc[0], kind=b["kind"].iloc[0],
                 rows=int(agg["n"].sum()), best_offset_h=best, viol_best=v[best], viol_utc=v[0], viol_art=v[-3])
        q = pd.to_datetime(agg["raw_date"].astype(str)).dt.to_period("Q").astype(str)
        badq = {}
        for qq, bq in agg.groupby(q):
            if bq["n"].sum() < 5000:
                continue
            vq = violation_by_offset(bq, offsets=(0,))
            if vq[0] > 0.005:
                badq[qq] = round(vq[0], 5)
        d["quarters_off_schedule"] = json.dumps(badq)
        if d["rows"] < 5000:
            d["verdict"] = "INSUFFICIENT_EVIDENCE"
        elif v[0] <= 0.005 and v[-3] - v[0] >= 0.02 and not badq:
            d["verdict"] = "UTC_VERIFIED"
        elif v[0] <= 0.05 and best == 0:
            d["verdict"] = "UTC_WITH_ANOMALIES"
        else:
            d["verdict"] = "NOT_VERIFIED"
        rows.append(d)
    out = pd.DataFrame(rows)
    out.loc[out["verdict"] == "INSUFFICIENT_EVIDENCE", "best_offset_h"] = 0
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="append", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    inv, bins = load_scan(*a.scan)
    merged = merge_group_bins(bins)
    tz = tz_verdicts(merged)
    tz.to_csv(out / "tz_groups.csv", index=False)
    ann, dups = annotate(merged, tz)
    if len(dups):
        dups.to_parquet(out / "dup_blocks.parquet", index=False)
    ann.drop(columns=["spread_hist"]).to_parquet(out / "annotated_bins.parquet", index=False)
    cen = session_census(ann)
    cen.to_parquet(out / "session_census.parquet", index=False)
    summ = dict(sources=int(len(inv)), groups=int(len(tz)), tz=tz["verdict"].value_counts().to_dict(),
                dup_blocks=int(len(dups)), dup_verdicts=dups["verdict"].value_counts().to_dict() if len(dups) else {},
                dup_copy_ticks=int(ann.loc[ann["dup_copy"], "n"].sum()), sessions=int(len(cen)))
    (out / "summary.json").write_text(json.dumps(summ, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    main()
