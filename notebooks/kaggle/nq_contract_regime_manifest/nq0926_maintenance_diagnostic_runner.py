#!/usr/bin/env python3
"""Run the authorized target-free NQ 09-26 maintenance diagnostic."""
from __future__ import annotations

import argparse, csv, hashlib, json, subprocess, sys
from pathlib import Path

EXPECTED_PARQUET_SHA256 = "1030715b216210e9443077212fd2e26303966c031243167d097d8465f81fb64f"
REQUIRED = ["ts_utc_ns", "ts_local_ns", "sequence", "volume", "source_file", "source_row"]
REPO = Path("/kaggle/working/EdgeLab")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def checkout(commit):
    if len(commit) != 40: raise SystemExit("full --expected-code-commit required")
    if not (REPO / ".git").exists():
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
            "https://github.com/Nicodelcampo/EdgeLab.git", str(REPO)], check=True)
        subprocess.run(["git", "sparse-checkout", "set", "--no-cone", "edgelab/**"], cwd=REPO, check=True)
    subprocess.run(["git", "fetch", "origin", commit, "--depth", "200"], cwd=REPO, check=True)
    subprocess.run(["git", "checkout", "-B", "nq0926_diag", commit], cwd=REPO, check=True)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if actual != commit or subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO, text=True).strip():
        raise SystemExit("code provenance gate failed")
    sys.path.insert(0, str(REPO)); return actual


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--expected-code-commit", required=True)
    p.add_argument("--input-root", type=Path, default=Path("/kaggle/input"))
    p.add_argument("--output-dir", type=Path, default=Path("/kaggle/working/nq0926_maintenance_diag"))
    args = p.parse_args(); commit = checkout(args.expected_code_commit)
    import numpy as np, pyarrow.parquet as pq
    from edgelab.kaggle.inventory import footer_census
    from edgelab.kaggle.seal import HOLDOUT_START_YMD
    from edgelab.kaggle.sessions_cme import is_maintenance_break, minutes_since_session_open, session_bounds_utc_ns, trade_date_ymd
    from edgelab.research.nq0926_maintenance_diagnostic import MaintenanceAccumulator, flattened_minute_rows

    hits = sorted(args.input_root.rglob("NQ_09-26_ticks.parquet"))
    if len(hits) != 1: raise RuntimeError(f"expected one NQ 09-26 parquet, got {len(hits)}")
    path = hits[0]; footer = footer_census(str(path))
    missing = [x for x in REQUIRED if x not in footer["column_names"]]
    if missing: raise RuntimeError(f"missing columns: {missing}")
    holdout_ns, _ = session_bounds_utc_ns(HOLDOUT_START_YMD)
    if int(footer["ts_max_ns"]) >= holdout_ns: raise RuntimeError("physical holdout intersection")
    digest = sha256_file(path)
    if digest != EXPECTED_PARQUET_SHA256: raise RuntimeError("NQ 09-26 hash mismatch")

    acc = MaintenanceAccumulator(); pf = pq.ParquetFile(path)
    for batch in pf.iter_batches(batch_size=1 << 20, columns=REQUIRED):
        cols = {name: np.asarray(batch.column(i)) for i, name in enumerate(REQUIRED)}
        ts = cols["ts_utc_ns"].astype(np.int64)
        acc.update(**cols, trade_date=trade_date_ymd(ts),
            minute_since_open=minutes_since_session_open(ts),
            maintenance_mask=is_maintenance_break(ts))
    report = acc.finalize()
    if report["total_rows"] != int(footer["rows"]): raise RuntimeError("row-count mismatch")
    report.update({"code_commit": commit, "parquet_sha256": digest,
        "outcomes_accessed": False, "holdout_accessed": False,
        "execution_status": "COMPLETE", "scientific_status": report.pop("status")})
    out = args.output_dir; out.mkdir(parents=True, exist_ok=True)
    json_path = out / "nq0926_maintenance_diagnostic_v1.json"; write_json(json_path, report)
    csv_path = out / "nq0926_maintenance_by_minute_v1.csv"
    rows = flattened_minute_rows(report)
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["trade_date", "minute_since_session_open", "tick_count"])
        w.writeheader(); w.writerows(rows)
    write_json(out / "sha256_manifest.json", {json_path.name: sha256_file(json_path), csv_path.name: sha256_file(csv_path)})
    print(json.dumps({"execution_status": "COMPLETE", "maintenance_tick_count": report["maintenance_tick_count"], "root_cause_status": "UNRESOLVED"}, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
