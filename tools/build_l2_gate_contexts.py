#!/usr/bin/env python3
"""Build causal GC L2 GATE contexts from paired nt8_l1/l2 v2 Parquets.

Outputs are target-free and local-only. The separate *.Last.parquet is never
accepted because it has no source_row and its clock reference is unresolved.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from edgelab.context.l2_gate import (extract_minute_features, fit_regime4_model,
                                     label_regime4, target_free_report)


def hash_file(path):
    h = sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 22), b""): h.update(block)
    return h.hexdigest()


def git_state():
    def run(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    return {"head": run("rev-parse", "HEAD"),
            "status": run("status", "--porcelain=v1", "--untracked-files=all")}


def read_manifest(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("status") != "COMPLETE_FORMAT_CONVERSION":
        raise ValueError(f"{path}: conversion not complete")
    if value.get("instrument") != "GC 06-26": raise ValueError(f"{path}: wrong instrument")
    return value


def load_parquet(path, columns):
    try: import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("canonical run requires PyArrow from the repository lockfile") from exc
    return pq.read_table(path, columns=columns).to_pandas()


def write_parquet(frame, path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), temporary,
                   compression="zstd", compression_level=7)
    os.replace(temporary, path)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--l2-dir", type=Path, required=True)
    parser.add_argument("--l1-dir", type=Path, required=True)
    parser.add_argument("--manifests-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--train-through", default="20260617")
    parser.add_argument("--exclude", action="append", default=["20260618"])
    parser.add_argument("--strict-book", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args(argv)
    start = git_state()
    if start["status"] and not args.allow_dirty:
        raise RuntimeError("worktree is dirty; commit/stash before formal extraction")
    manifest_paths = sorted(args.manifests_dir.glob("*.manifest.json"))
    if not manifest_paths: raise FileNotFoundError("no conversion manifests")
    excluded = set(args.exclude); features_all = []; session_reports = []; sources = []
    for manifest_path in manifest_paths:
        manifest = read_manifest(manifest_path); session = str(manifest["session_name"])
        if session in excluded: continue
        l2_path = args.l2_dir / f"{session}.parquet"; l1_path = args.l1_dir / f"{session}.parquet"
        for path, key in ((l2_path, "l2_depth"), (l1_path, "l1_quotes")):
            expected = manifest["outputs"][key]
            if path.stat().st_size != int(expected["bytes"]) or hash_file(path) != expected["sha256"]:
                raise ValueError(f"{path}: identity mismatch against conversion manifest")
        l2 = load_parquet(l2_path, ["side", "operation", "level", "price_tick", "size", "source_row", "ts_us"])
        l1 = load_parquet(l1_path, ["side", "price_tick", "size", "source_row", "ts_us"])
        features, report = extract_minute_features(l2, l1, session=session, strict_book=args.strict_book)
        write_parquet(features, args.out_dir / "features" / f"{session}.parquet")
        features_all.append(features); session_reports.append(report)
        sources.append({"session": session, "manifest_sha256": hash_file(manifest_path),
                        "l2_sha256": manifest["outputs"]["l2_depth"]["sha256"],
                        "l1_sha256": manifest["outputs"]["l1_quotes"]["sha256"]})
        print(f"{session}: source={report['source_rows_total']:,} eligible_minutes={report['eligible_minutes']:,}")
    combined = pd.concat(features_all, ignore_index=True)
    sessions = sorted(combined["cme_session"].astype(str).unique())
    train_sessions = [v for v in sessions if v <= args.train_through]
    evaluation_sessions = [v for v in sessions if v > args.train_through]
    model = fit_regime4_model(combined, train_sessions=train_sessions, code_identity=start["head"])
    labels = label_regime4(combined, model, evaluation_sessions=evaluation_sessions)
    report = target_free_report(labels); args.out_dir.mkdir(parents=True, exist_ok=True)
    write_parquet(labels, args.out_dir / "gate_l2_context_labels.parquet")
    (args.out_dir / "gate_l2_context_model.json").write_text(json.dumps(model, indent=2, sort_keys=True) + "\n")
    (args.out_dir / "gate_l2_target_free_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    end = git_state()
    if end["head"] != start["head"]: raise RuntimeError("HEAD changed during extraction")
    if end["status"] != start["status"]: raise RuntimeError("worktree status changed during extraction")
    run_manifest = {"schema": "edgelab.context.l2_gate_run/1.0.0",
        "status": "COMPLETE_TARGET_FREE_CONTEXT_EXTRACTION", "instrument": "GC 06-26",
        "instrument_role": "NON_FRONT_MONTH_DIAGNOSTIC", "sessions": sessions,
        "excluded_sessions": sorted(excluded), "train_sessions": train_sessions,
        "evaluation_sessions": evaluation_sessions, "sources": sources,
        "session_reports": session_reports, "model_id": model["model_id"],
        "code_commit_start": start["head"], "code_commit_end": end["head"],
        "dirty_start": bool(start["status"]), "dirty_end": bool(end["status"]),
        "clock_reference_resolved": False, "joined_external_last_parquet": False,
        "CAMPAIGN_OUTCOMES_OPENED": False, "PREEXISTING_OUTCOME_EXPOSURE": "YES",
        "EDGE_DECLARED": False}
    (args.out_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2, sort_keys=True) + "\n")
    print(f"model={model['model_id']} labels={len(labels):,} evaluation_sessions={evaluation_sessions}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
