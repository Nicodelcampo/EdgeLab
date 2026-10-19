#!/usr/bin/env python3
"""Audit pinned preholdout AVZVOL event covariates; no tests/returns/controls.

Requires the exact six-file output inventory with file paths and sha256.
Parquet metadata is checked before hashing/deserializing event columns.
Does not authenticate caller pins or certify raw sources.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

from edgelab.kaggle.avzvol_audit import (
    ACTIVITY, AVZVOLAuditError, CONFIRMATION, DISCOVERY,
    audit_covariates, require_baseline_reproduction,
)


def audit_inventory(inventory):
    import pandas as pd
    import pyarrow.parquet as pq
    if not isinstance(inventory, list) or len(inventory) != 6:
        raise AVZVOLAuditError("exact six-file inventory required")
    expected = {c + "_avzp2racgrid.parquet" for c in DISCOVERY + CONFIRMATION}
    names = [Path(r["file"]).name for r in inventory]
    if len(set(names)) != 6 or set(names) != expected:
        raise AVZVOLAuditError("output universe differs or is duplicated")
    tables, verified = [], []
    columns = ["contract", "cell", "kind", "session", "occ", "amp", *ACTIVITY]
    # Validate ALL file partitions before reading ANY event-column payload.
    files = []
    for row in inventory:
        p = Path(row["file"])
        if not isinstance(row.get("sha256"), str) or not re.fullmatch("[0-9a-f]{64}", row["sha256"]):
            raise AVZVOLAuditError("missing output hash pin")
        pf = pq.ParquetFile(p)
        if not set(columns) <= set(pf.schema_arrow.names) or pf.metadata.num_rows == 0:
            raise AVZVOLAuditError("missing event schema or empty output")
        idx = pf.schema_arrow.names.index("session")
        for group in range(pf.num_row_groups):
            s = pf.metadata.row_group(group).column(idx).statistics
            if not s or not s.has_min_max or s.null_count != 0 or s.max >= 20261001:
                raise AVZVOLAuditError("missing partition proof or reserved output")
        files.append((row, p, pf))
    for row, p, pf in files:
        with p.open("rb") as stream:
            sha = hashlib.file_digest(stream, "sha256").hexdigest()
        if sha != row["sha256"]:
            raise AVZVOLAuditError("output bytes differ from pin")
        t = pf.read(columns=columns).to_pandas()
        if set(t["contract"]) != {p.name.removesuffix("_avzp2racgrid.parquet")}:
            raise AVZVOLAuditError("contract/file mismatch")
        tables.append(t)
        verified.append({"file": p.name, "sha256": sha, "rows": len(t),
                         "all_session_groups_preholdout": True})
    result = audit_covariates(pd.concat(tables, ignore_index=True))
    result["files"] = verified
    result["columns_read"] = columns
    result["baseline_reproduction_status"] = "NOT_VERIFIED_NO_CONTROL_RESULTS_OPENED"
    result["raw_input_quality_certified"] = False
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--allow-preholdout-covariate-audit", action="store_true", required=True)
    parser.add_argument("--published-baseline", type=Path)
    parser.add_argument("--reproduced-baseline", type=Path)
    args = parser.parse_args(argv)
    try:
        if bool(args.published_baseline) != bool(args.reproduced_baseline):
            raise AVZVOLAuditError("both baseline artifacts required")
        result = audit_inventory(json.loads(args.inventory.read_text()))
        if args.published_baseline:
            result["baseline_comparison"] = require_baseline_reproduction(
                published=json.loads(args.published_baseline.read_text()),
                reproduced=json.loads(args.reproduced_baseline.read_text()))
            result["baseline_reproduction_status"] = result["baseline_comparison"]["status"]
        # Never overwrite an original artifact, baseline, inventory or report.
        with args.out.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"status": result["status"], "report": str(args.out),
                          "research_authorized": False}))
        return 2  # Lineage/raw quality/pairing still require independent review.
    except (AVZVOLAuditError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "STOP_AVZVOL_AUDIT", "error": str(exc), "research_authorized": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())