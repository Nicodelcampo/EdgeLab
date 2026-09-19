import os
import sys
import glob
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import pyarrow.parquet as pq

DEFAULT_HOLDOUT_NS = 1782856800000000000
DEFAULT_HOLDOUT_UTC = "2026-06-30T22:00:00Z"

TICK_BASE = Path(r"E:\EdgeLab\data\nt8_research_v2")
BLOCKED_FILE = Path(r"E:\EdgeLab-edgefactory\docs\research\HFT_EXPANSION_FINAL_BLOCKED_CONTRACTS.json")
REMOTE_META = Path(r"E:\EdgeLab-edgefactory\artifacts\audit\remote_datasets_metadata.json")
MIGRATION_STATE = Path(r"E:\EdgeLab-edgefactory\artifacts\audit\kaggle_migration_state.json")

# Load blocked contracts
with open(BLOCKED_FILE, "r", encoding="utf-8") as f:
    blocked_list = json.load(f)
blocked_contracts = {b["contract_id"]: b for b in blocked_list}

# Load remote metadata
with open(REMOTE_META, "r", encoding="utf-8") as f:
    remote_meta = json.load(f)

# Parse remote sha mappings: {filename: (dataset, sha256)}
remote_shas = {}
for ds_slug, ds_data in remote_meta.items():
    if "files_sha256" in ds_data:
        for line in ds_data["files_sha256"].strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                remote_shas[parts[1].strip()] = (ds_slug, parts[0].strip())

# Also load state file for 6B, 6J, MNQ
with open(MIGRATION_STATE, "r", encoding="utf-8") as f:
    migration_state = json.load(f)

for rec in migration_state.get("all_manifest_records", []):
    if rec.get("semantic_role") == "CANONICAL_PREHOLDOUT_RAW_TICKS":
        remote_shas[rec["file_name"]] = (rec["dataset_ref"].split("/")[-1], rec["sha256"])

print(f"Loaded {len(remote_shas)} remote file hash mappings.")

# Instrument directories mapping
inst_dirs = {
    "6B": TICK_BASE / "6B_parquet",
    "6E": TICK_BASE / "6E",
    "6J": TICK_BASE / "6J_parquet",
    "ES": TICK_BASE / "ES_parquet",
    "GC": TICK_BASE / "GC_parquet",
    "MBT": TICK_BASE / "MBT_parquet",
    "MES": TICK_BASE / "MES_parquet",
    "MNQ": TICK_BASE / "MNQ_parquet",
    "NQ": TICK_BASE / "NQ_parquet",
    "YM": TICK_BASE / "YM_parquet",
    "ZB": TICK_BASE / "ZB"
}

def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

inventory_results = []
summary_counts = {
    "REMOTE_VERIFIED": 0,
    "REMOTE_PRESENT_NOT_VERIFIED": 0,
    "LOCAL_ONLY_READY_TO_UPLOAD": 0,
    "BLOCKED_BY_CUSTODY": 0,
    "DUPLICATE_OR_SUPERSEDED": 0,
    "HOLDOUT_REJECTED": 0
}

for inst, p_dir in inst_dirs.items():
    print(f"\n--- Scanning {inst} in {p_dir.name} ---")
    if not p_dir.exists():
        print(f"Directory {p_dir} does not exist!")
        continue
    
    parquet_files = sorted(p_dir.glob("*.parquet"))
    for pf_path in parquet_files:
        fn = pf_path.name
        sz = pf_path.stat().st_size
        sha = get_file_sha256(pf_path)
        
        pf = pq.ParquetFile(pf_path)
        meta = pf.metadata
        schema = pf.schema_arrow
        rows = meta.num_rows

        # Read timestamps
        ts_arr = pf.read(columns=["ts_utc_ns"]).column("ts_utc_ns").to_numpy()
        min_ts = int(ts_arr.min())
        max_ts = int(ts_arr.max())
        holdout_violations = int((ts_arr >= DEFAULT_HOLDOUT_NS).sum())

        parts = pf_path.stem.split("_")
        contract = f"{inst} {parts[1]}" if len(parts) > 1 else inst
        cid = f"{inst}_{parts[1]}" if len(parts) > 1 else inst

        # Classification
        status = None
        reasons = []

        if holdout_violations > 0:
            status = "HOLDOUT_REJECTED"
            reasons.append(f"{holdout_violations} ticks exceed holdout boundary")
        elif cid in blocked_contracts:
            status = "BLOCKED_BY_CUSTODY"
            reasons.append(blocked_contracts[cid].get("motivo", "BLOCKED_BY_CUSTODY"))
        elif fn in remote_shas:
            rem_ds, rem_sha = remote_shas[fn]
            if rem_sha == sha:
                # If verified in migration_state (downloaded and verified)
                if rem_ds in ["edgelab-ticks-6b-preholdout", "edgelab-ticks-6j-preholdout", "edgelab-ticks-mnq-preholdout"]:
                    status = "REMOTE_VERIFIED"
                    reasons.append(f"Remote dataset {rem_ds} hash verified via post-download assertion")
                else:
                    status = "REMOTE_PRESENT_NOT_VERIFIED"
                    reasons.append(f"Remote dataset {rem_ds} contains identical SHA-256 in manifest; download verification pending")
            else:
                status = "LOCAL_ONLY_READY_TO_UPLOAD"
                reasons.append(f"Hash mismatch with remote ({rem_sha} vs {sha})")
        else:
            status = "LOCAL_ONLY_READY_TO_UPLOAD"
            reasons.append("File not found in any remote Kaggle dataset")

        summary_counts[status] += 1

        print(f"[{status}] {contract} ({fn}): {rows:,} rows, {sz/1024/1024:.2f}MB, sha={sha[:12]}...")

        schema_cols = []
        for i in range(len(schema.names)):
            fld = schema.field(i)
            schema_cols.append({"name": fld.name, "type": str(fld.type)})

        inventory_results.append({
            "instrument": inst,
            "contract": contract,
            "contract_id": cid,
            "file_name": fn,
            "file_path": str(pf_path),
            "size_bytes": sz,
            "size_mb": round(sz / 1024 / 1024, 2),
            "row_count": rows,
            "min_timestamp_ns": min_ts,
            "max_timestamp_ns": max_ts,
            "holdout_violations": holdout_violations,
            "source_sha256": sha,
            "remote_status": status,
            "status_details": reasons,
            "schema_fingerprint": schema_cols
        })

print("\n==================================================")
print("INVENTORY SUMMARY COUNTS:")
for k, v in summary_counts.items():
    print(f"  {k}: {v}")
print(f"Total contracts/files audited: {len(inventory_results)}")
print("==================================================")

out_file = Path(r"E:\EdgeLab-edgefactory\artifacts\audit\CANONICAL_TICKS_LOCAL_INVENTORY.json")
with open(out_file, "w", encoding="utf-8") as f:
    json.dump({
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "holdout_boundary_ns": DEFAULT_HOLDOUT_NS,
        "holdout_boundary_utc": DEFAULT_HOLDOUT_UTC,
        "summary": summary_counts,
        "total_files": len(inventory_results),
        "inventory": inventory_results
    }, f, indent=2)

print(f"Saved inventory to {out_file}")
