#!/usr/bin/env python3
"""Audit an event store directory against the five defect criteria.

Checks:
  1. Holdout: any rows with session_id >= 20260701?
  2. Provenance: does a run_manifest exist with git state and hashes?
  3. Gate 1 reconciliation: compare event counts per session against Gate 1 CSVs.
  4. Metadata: are metadata_json fields all-zero placeholders?
  5. Duplicates: exact-row and key-level duplicates, especially HFTZones2.

Usage::

    python tools/audit_event_store.py \\
        --store-dir E:\\DatosNT8\\event_store_gc_all5 \\
        --session-registry specs/bt2_absorption_gate1_all5_sessions_2026-08-26.json \\
        [--gate1-csv-dir path/to/gate1/csvs]  \\
        [--output-json audit_result.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

# ── Helpers ───────────────────────────────────────────────────────────

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

HOLDOUT_CUTOFF = "20260701"

CHECKS = {}

def check(name):
    def decorator(fn):
        CHECKS[name] = fn
        return fn
    return decorator


# ── Check 1: Holdout ──────────────────────────────────────────────────

@check("1_holdout_trimming")
def check_holdout(ctx):
    """Count rows with session_id >= holdout cutoff."""
    results = {}
    total_violations = 0
    for contract, df in ctx["dataframes"].items():
        if "session_id" not in df.columns:
            results[contract] = {"status": "SKIP", "reason": "no session_id column"}
            continue
        sessions = df["session_id"].astype(str)
        violations = sessions[sessions >= HOLDOUT_CUTOFF]
        n = len(violations)
        total_violations += n
        pct = n / len(df) * 100 if len(df) > 0 else 0.0
        if n > 0:
            offending = sorted(violations.unique().tolist())
            results[contract] = {
                "status": "FAIL",
                "n_violations": n,
                "pct_of_contract": round(pct, 1),
                "offending_sessions": offending[:20],
            }
        else:
            results[contract] = {"status": "PASS", "n_violations": 0}

    return {
        "status": "FAIL" if total_violations > 0 else "PASS",
        "total_violations": total_violations,
        "by_contract": results,
    }


# ── Check 2: Provenance ──────────────────────────────────────────────

@check("2_provenance")
def check_provenance(ctx):
    """Check if manifest exists and has required provenance fields."""
    store_dir = ctx["store_dir"]
    manifests = list(store_dir.glob("*manifest*.json"))
    if not manifests:
        return {
            "status": "FAIL",
            "reason": "no manifest file found",
            "required_fields_present": False,
        }

    # Read the manifest(s)
    results = []
    for mp in manifests:
        try:
            data = json.loads(mp.read_text(encoding="utf-8"))
        except Exception as e:
            results.append({"file": mp.name, "status": "FAIL",
                            "reason": f"parse error: {e}"})
            continue

        required = ["schema", "generated_utc", "total_events_across_contracts"]
        provenance = ["git_state", "builder", "session_registry",
                       "input_registry"]
        present = {k: k in data for k in required + provenance}
        has_git = "git_state" in data
        has_commit = (has_git and data["git_state"].get("commit") is not None)
        has_dirty = (has_git and "dirty" in data["git_state"])

        results.append({
            "file": mp.name,
            "sha256": file_sha256(mp),
            "schema": data.get("schema", "MISSING"),
            "fields_present": present,
            "has_git_commit": has_commit,
            "has_dirty_flag": has_dirty,
            "dirty_at_generation": data.get("git_state", {}).get("dirty"),
            "status": "PASS" if has_commit and not data.get("git_state", {}).get("dirty")
                      else "WARN" if has_commit else "FAIL",
        })

    overall = "PASS" if all(r["status"] == "PASS" for r in results) else (
              "WARN" if any(r["status"] != "FAIL" for r in results) else "FAIL")
    return {"status": overall, "manifests": results}


# ── Check 3: Gate 1 reconciliation ────────────────────────────────────

@check("3_gate1_reconciliation")
def check_gate1_reconciliation(ctx):
    """Compare event store counts per session to Gate 1 session registry."""
    sess_reg = ctx.get("session_registry")
    if sess_reg is None:
        return {"status": "SKIP", "reason": "no session registry provided"}

    expected_counts = sess_reg.get("contract_session_counts", {})
    windows = sess_reg["selection"]["contract_windows"]

    results = {}
    for contract, df in ctx["dataframes"].items():
        if "session_id" not in df.columns:
            results[contract] = {"status": "SKIP"}
            continue

        # Filter to only sessions within the registry window
        w = windows.get(contract)
        if w is None:
            results[contract] = {"status": "SKIP",
                                 "reason": "contract not in registry"}
            continue

        sessions_in_df = df["session_id"].astype(str)
        in_window = sessions_in_df[
            (sessions_in_df >= w["start"]) & (sessions_in_df <= w["end"])
        ]
        out_of_window = sessions_in_df[
            (sessions_in_df < w["start"]) | (sessions_in_df > w["end"])
        ]

        expected_n_sessions = expected_counts.get(contract, 0)
        actual_n_sessions = in_window.nunique()

        # Count by indicator for BT2/BT2A only (Gate 1 comparison)
        bt2_mask = df["indicator"].isin(["BigTrap2", "BigTrap2Absorption"])
        bt2_in_window = df[bt2_mask & (
            (sessions_in_df >= w["start"]) & (sessions_in_df <= w["end"])
        )]

        results[contract] = {
            "status": "PASS" if len(out_of_window) == 0
                      else "FAIL",
            "expected_sessions": expected_n_sessions,
            "actual_sessions_in_window": int(actual_n_sessions),
            "rows_outside_window": int(len(out_of_window)),
            "total_rows_in_window": int(len(in_window)),
            "bt2_bt2a_in_window": int(len(bt2_in_window)),
            "by_indicator_in_window": (
                bt2_in_window["indicator"].value_counts().to_dict()
                if not bt2_in_window.empty else {}
            ),
        }

    overall = "PASS" if all(
        r.get("status") in ("PASS", "SKIP") for r in results.values()
    ) else "FAIL"
    return {"status": overall, "by_contract": results}


# ── Check 4: Metadata placeholders ────────────────────────────────────

@check("4_metadata_placeholders")
def check_metadata(ctx):
    """Check for all-zero metadata_json fields."""
    results = {}
    total_all_zero = 0
    total_rows = 0

    for contract, df in ctx["dataframes"].items():
        if "metadata_json" not in df.columns:
            results[contract] = {"status": "SKIP", "reason": "no metadata_json"}
            continue

        n = len(df)
        total_rows += n
        n_all_zero = 0
        n_parse_error = 0
        sample_zero = None
        sample_real = None

        for _, row in df.head(min(n, 50000)).iterrows():
            try:
                md = json.loads(row["metadata_json"])
            except (json.JSONDecodeError, TypeError):
                n_parse_error += 1
                continue
            numeric_vals = [v for v in md.values()
                           if isinstance(v, (int, float))]
            if numeric_vals and all(v == 0 for v in numeric_vals):
                n_all_zero += 1
                if sample_zero is None:
                    sample_zero = md
            elif sample_real is None and numeric_vals:
                sample_real = md

        # Scale estimate if we sampled
        if n > 50000:
            scale = n / 50000
            n_all_zero = int(n_all_zero * scale)

        pct = n_all_zero / n * 100 if n > 0 else 0.0
        total_all_zero += n_all_zero

        by_indicator = {}
        for ind in df["indicator"].unique():
            sub = df[df["indicator"] == ind]
            ind_zero = 0
            for _, row in sub.head(min(len(sub), 10000)).iterrows():
                try:
                    md = json.loads(row["metadata_json"])
                except Exception:
                    continue
                nums = [v for v in md.values() if isinstance(v, (int, float))]
                if nums and all(v == 0 for v in nums):
                    ind_zero += 1
            by_indicator[ind] = {
                "sampled": min(len(sub), 10000),
                "all_zero": ind_zero,
                "pct": round(ind_zero / max(min(len(sub), 10000), 1) * 100, 1),
            }

        results[contract] = {
            "status": "FAIL" if pct > 50 else ("WARN" if pct > 5 else "PASS"),
            "total_rows": n,
            "all_zero_count": n_all_zero,
            "all_zero_pct": round(pct, 1),
            "parse_errors": n_parse_error,
            "sample_zero": sample_zero,
            "sample_real": sample_real,
            "by_indicator": by_indicator,
        }

    overall_pct = total_all_zero / max(total_rows, 1) * 100
    return {
        "status": "FAIL" if overall_pct > 50 else ("WARN" if overall_pct > 5
                                                     else "PASS"),
        "total_all_zero": total_all_zero,
        "total_rows": total_rows,
        "overall_pct": round(overall_pct, 1),
        "by_contract": results,
    }


# ── Check 5: Duplicates ──────────────────────────────────────────────

@check("5_duplicates")
def check_duplicates(ctx):
    """Check for exact duplicates and key-level duplicates."""
    results = {}
    total_exact = 0
    total_key = 0

    for contract, df in ctx["dataframes"].items():
        n = len(df)
        # Exact row duplicates
        exact_dupes = df.duplicated(keep=False).sum()
        exact_pairs = exact_dupes // 2

        # Key-level duplicates (ts_utc_ns, source_row, indicator, direction)
        key_cols = ["ts_utc_ns", "source_row", "indicator", "direction"]
        existing_keys = [c for c in key_cols if c in df.columns]
        if len(existing_keys) == len(key_cols):
            key_dupes = df.duplicated(subset=key_cols, keep=False).sum()
            key_pairs = key_dupes // 2
        else:
            key_dupes = -1
            key_pairs = -1

        # HFTZones2-specific: duplicates with zone_width=0
        hft_dupes = 0
        if "indicator" in df.columns and "metadata_json" in df.columns:
            hft = df[df["indicator"] == "HFTZones2"]
            if not hft.empty:
                hft_dup_mask = hft.duplicated(
                    subset=["ts_utc_ns", "source_row", "direction"], keep=False)
                hft_dupes = int(hft_dup_mask.sum())

        total_exact += exact_pairs
        total_key += (key_pairs if key_pairs >= 0 else 0)

        results[contract] = {
            "status": "FAIL" if exact_pairs > 0 or (key_pairs > 0)
                      else "PASS",
            "total_rows": n,
            "exact_duplicate_rows": int(exact_dupes),
            "exact_duplicate_pairs": int(exact_pairs),
            "key_duplicate_rows": int(key_dupes) if key_dupes >= 0 else "N/A",
            "key_duplicate_pairs": int(key_pairs) if key_pairs >= 0 else "N/A",
            "hftzones2_duplicate_rows": hft_dupes,
        }

    overall = "PASS" if total_exact == 0 and total_key == 0 else "FAIL"
    return {
        "status": overall,
        "total_exact_pairs": total_exact,
        "total_key_pairs": total_key,
        "by_contract": results,
    }


# ── Fill causality ────────────────────────────────────────────────────

@check("6_fill_causality")
def check_fill_causality(ctx):
    """Ensure fill is strictly after signal."""
    results = {}
    total_violations = 0
    for contract, df in ctx["dataframes"].items():
        if not {"ts_utc_ns", "fill_ts_utc_ns", "source_row",
                "fill_source_row"}.issubset(df.columns):
            results[contract] = {"status": "SKIP"}
            continue
        violations = df[
            (df["fill_ts_utc_ns"] < df["ts_utc_ns"]) |
            ((df["fill_ts_utc_ns"] == df["ts_utc_ns"]) &
             (df["fill_source_row"] <= df["source_row"]))
        ]
        n = len(violations)
        total_violations += n
        results[contract] = {
            "status": "FAIL" if n > 0 else "PASS",
            "violations": n,
        }
    return {
        "status": "FAIL" if total_violations > 0 else "PASS",
        "total_violations": total_violations,
        "by_contract": results,
    }


# ── Runner ────────────────────────────────────────────────────────────

def load_store(store_dir: Path) -> dict[str, "pd.DataFrame"]:
    import pandas as pd
    dfs = {}
    for pf in sorted(store_dir.glob("*_event_store.parquet")):
        # Extract contract name from filename
        name = pf.stem.replace("_event_store", "").replace("_", " ")
        df = pd.read_parquet(pf)
        dfs[name] = df
    return dfs


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--store-dir", type=Path, required=True)
    ap.add_argument("--session-registry", type=Path, default=None)
    ap.add_argument("--output-json", type=Path, default=None)
    args = ap.parse_args()

    import pandas as pd

    print(f"Auditing event store: {args.store_dir}")
    dfs = load_store(args.store_dir)
    if not dfs:
        raise SystemExit(f"No *_event_store.parquet found in {args.store_dir}")

    total_rows = sum(len(df) for df in dfs.values())
    print(f"  Contracts: {list(dfs.keys())}")
    print(f"  Total rows: {total_rows:,}")
    for name, df in dfs.items():
        print(f"    {name}: {len(df):,} rows, "
              f"indicators = {sorted(df['indicator'].unique().tolist()) if 'indicator' in df.columns else '?'}")

    # Load session registry if provided
    sess_reg = None
    if args.session_registry and args.session_registry.is_file():
        sess_reg = json.loads(
            args.session_registry.read_text(encoding="utf-8"))

    ctx = {
        "dataframes": dfs,
        "store_dir": args.store_dir,
        "session_registry": sess_reg,
    }

    # Run all checks
    results = {}
    print(f"\n{'=' * 60}")
    for name, fn in sorted(CHECKS.items()):
        print(f"\n--- {name} ---")
        result = fn(ctx)
        results[name] = result
        status = result.get("status", "?")
        icon = "[OK]" if status == "PASS" else ("[??]" if status in ("WARN", "SKIP")
                                                else "[!!]")
        print(f"  {icon} {status}")
        # Print key details
        for k, v in result.items():
            if k in ("status", "by_contract"):
                continue
            if isinstance(v, (int, float, str, bool)):
                print(f"    {k}: {v}")

    print(f"\n{'=' * 60}")
    print("SUMMARY:")
    for name, result in sorted(results.items()):
        s = result["status"]
        icon = "[OK]" if s == "PASS" else ("[??]" if s in ("WARN", "SKIP") else "[!!]")
        print(f"  {icon} {name}: {s}")

    overall = "PASS" if all(r["status"] in ("PASS", "SKIP")
                            for r in results.values()) else "FAIL"
    print(f"\nOVERALL: {overall}")

    if args.output_json:
        out = {
            "audit_target": str(args.store_dir),
            "total_rows": total_rows,
            "contracts": list(dfs.keys()),
            "checks": results,
            "overall": overall,
        }
        args.output_json.write_text(
            json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8")
        print(f"Results written to: {args.output_json}")

    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
