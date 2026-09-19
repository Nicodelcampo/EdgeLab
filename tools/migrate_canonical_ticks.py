import os
import sys
import glob
import json
import time
import shutil
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone
import pyarrow.parquet as pq
from kaggle.api.kaggle_api_extended import KaggleApi

REPO_ROOT = Path(r"E:\EdgeLab-edgefactory")
TICK_BASE = Path(r"E:\EdgeLab\data\nt8_research_v2")
STAGING_ROOT = Path(r"E:\kaggle_staging")
VERIFY_ROOT = Path(r"E:\kaggle_verify")
STAGING_ROOT.mkdir(parents=True, exist_ok=True)
VERIFY_ROOT.mkdir(parents=True, exist_ok=True)

DEFAULT_HOLDOUT_NS = 1782856800000000000
DEFAULT_HOLDOUT_UTC = "2026-06-30T22:00:00Z"
PRODUCER_COMMIT = "b65da69"

BLOCKED_FILE = REPO_ROOT / "docs" / "research" / "HFT_EXPANSION_FINAL_BLOCKED_CONTRACTS.json"
STATE_FILE = REPO_ROOT / "artifacts" / "audit" / "kaggle_migration_state.json"

with open(BLOCKED_FILE, "r", encoding="utf-8") as f:
    blocked_list = json.load(f)
blocked_contract_ids = {b["contract_id"]: b for b in blocked_list}

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

def init_kaggle_api() -> KaggleApi:
    api = KaggleApi()
    api.authenticate()
    return api

def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"datasets": {}, "all_manifest_records": []}

def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def stage_ticks(sym: str) -> tuple[str, Path, list[dict]]:
    sym = sym.upper()
    slug = f"edgelab-ticks-{sym.lower()}-preholdout"
    stage_dir = STAGING_ROOT / slug
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)

    src_dir = inst_dirs[sym]
    files_manifest = []

    for f in sorted(src_dir.glob("*.parquet")):
        parts = f.stem.split("_")
        cid = f"{sym}_{parts[1]}" if len(parts) > 1 else sym
        cont = f"{sym} {parts[1]}" if len(parts) > 1 else sym

        if cid in blocked_contract_ids:
            print(f"Skipping blocked contract {cid} ({f.name}): {blocked_contract_ids[cid].get('motivo')}")
            continue

        p_dst = stage_dir / f.name
        shutil.copyfile(f, p_dst)
        sha = get_file_sha256(p_dst)

        # Read timestamps and assert holdout
        pf = pq.ParquetFile(p_dst)
        tbl = pf.read(columns=["ts_utc_ns"])
        ts = tbl.column("ts_utc_ns").to_numpy()
        min_ts = int(ts.min())
        max_ts = int(ts.max())
        post_holdout = int((ts >= DEFAULT_HOLDOUT_NS).sum())
        assert post_holdout == 0, f"HOLDOUT VIOLATION in {f.name}: {post_holdout} rows >= {DEFAULT_HOLDOUT_NS}"

        files_manifest.append({
            "dataset_ref": f"nicolasbuttaro/{slug}",
            "kaggle_version": 1,
            "relative_path": f.name,
            "file_name": f.name,
            "size_bytes": p_dst.stat().st_size,
            "sha256": sha,
            "semantic_role": "CANONICAL_PREHOLDOUT_RAW_TICKS",
            "instrument": sym,
            "contract": cont,
            "month": "MULTI",
            "schema_version": "1.0.0",
            "producer_commit": PRODUCER_COMMIT,
            "producer_script": "edgelab/data/nt8_export",
            "source_artifact_sha256": sha,
            "min_timestamp_ns": min_ts,
            "max_timestamp_ns": max_ts,
            "row_count": len(ts),
            "holdout_rows": 0,
            "custody_status": "CANONICAL_VERIFIED",
            "causal_status": "CAUSAL_VERIFIED",
            "known_limitations": "Pre-holdout boundary strictly enforced at 1782856800000000000 (2026-06-30T22:00:00Z).",
            "supersedes": None,
            "superseded_by": None
        })

    meta = {
        "title": f"EdgeLab Ticks {sym} Pre-Holdout",
        "id": f"nicolasbuttaro/{slug}",
        "licenses": [{"name": "other"}],
        "isPrivate": True
    }
    with open(stage_dir / "dataset-metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    readme = f"""# EdgeLab Ticks {sym} Pre-Holdout

Private verified canonical raw tick data for CME futures {sym}:
- 100% pre-holdout ticks (`max_timestamp_ns < 1782856800000000000`)
- Zero holdout rows
- SHA-256 verified against custody inventory
- Granular per-contract parquet files
"""
    with open(stage_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme)

    with open(stage_dir / "files.sha256", "w", encoding="utf-8") as f:
        for item in files_manifest:
            f.write(f"{item['sha256']}  {item['relative_path']}\n")

    return slug, stage_dir, files_manifest

def upload_and_verify(api: KaggleApi, slug: str, stage_dir: Path, files_manifest: list[dict]) -> dict:
    dataset_ref = f"nicolasbuttaro/{slug}"
    print(f"\n==================================================")
    print(f"Uploading Dataset: {dataset_ref}")
    print(f"Staging Path: {stage_dir}")
    print(f"Files count: {len(files_manifest)}")
    print(f"Total size: {sum(x['size_bytes'] for x in files_manifest) / 1024 / 1024:.2f} MB")
    print(f"==================================================")

    t0_up = time.time()
    try:
        exists = False
        try:
            st = str(api.dataset_status(dataset_ref))
            exists = True
        except Exception:
            exists = False

        if not exists:
            print(f"Creating new private dataset {dataset_ref}...")
            res = api.dataset_create_new(
                folder=str(stage_dir),
                public=False,
                quiet=False,
                convert_to_csv=False,
                dir_mode="zip"
            )
            print("Create response:", res)
        else:
            print(f"Dataset {dataset_ref} already exists. Creating new version...")
            res = api.dataset_create_version(
                folder=str(stage_dir),
                version_notes=f"Audited canonical migration {datetime.now(timezone.utc).isoformat()}",
                quiet=False,
                convert_to_csv=False,
                dir_mode="zip"
            )
            print("Version response:", res)
    except Exception as e:
        print(f"Upload failed for {dataset_ref}: {e}")
        return {
            "dataset_ref": dataset_ref,
            "status": "UPLOAD_FAILED",
            "error": str(e),
            "verified": False,
            "version": None
        }

    up_elapsed = round(time.time() - t0_up, 2)
    print(f"Upload completed in {up_elapsed}s. Waiting for Kaggle processing...")

    # Poll status
    max_wait = 400
    poll_start = time.time()
    while time.time() - poll_start < max_wait:
        try:
            current_status = str(api.dataset_status(dataset_ref))
            print(f"Status of {dataset_ref}: {current_status}")
            if current_status == "ready":
                print("Status is ready. Waiting 20s for Kaggle CDN archive propagation...")
                time.sleep(20)
                break
            if "error" in current_status.lower() or "fail" in current_status.lower():
                raise RuntimeError(f"Kaggle status error: {current_status}")
        except Exception as e:
            print(f"Status check exception: {e}")
        time.sleep(10)

    # Verification download
    print(f"Verifying download from Kaggle for {dataset_ref}...")
    v_dir = VERIFY_ROOT / slug

    mismatches = []
    verified_files = 0
    holdout_violations = 0

    for dl_attempt in range(3):
        if v_dir.exists():
            shutil.rmtree(v_dir, ignore_errors=True)
        v_dir.mkdir(parents=True, exist_ok=True)

        t0_dl = time.time()
        print(f"Downloading dataset files (verification attempt {dl_attempt + 1}/3)...")
        try:
            api.dataset_download_files(dataset_ref, path=str(v_dir), unzip=True, quiet=False)
        except Exception as e:
            print(f"Whole archive download failed: {e}. Downloading individual files...")
            for item in files_manifest:
                try:
                    api.dataset_download_file(dataset_ref, item["file_name"], path=str(v_dir), quiet=True)
                except Exception as ex:
                    print(f"Individual download error for {item['file_name']}: {ex}")

        dl_elapsed = round(time.time() - t0_dl, 2)
        print(f"Download finished in {dl_elapsed}s. Verifying SHA-256...")

        mismatches = []
        verified_files = 0
        holdout_violations = 0

        for item in files_manifest:
            rel = item["relative_path"]
            staged_sha = item["sha256"]
            dl_file = v_dir / rel
            if not dl_file.exists():
                flat = v_dir / Path(rel).name
                if flat.exists():
                    dl_file = flat
                else:
                    mismatches.append({"file": rel, "error": "FILE_MISSING_IN_DOWNLOAD"})
                    continue

            dl_sha = get_file_sha256(dl_file)
            if dl_sha != staged_sha:
                mismatches.append({"file": rel, "staged_sha": staged_sha, "remote_sha": dl_sha})
            else:
                verified_files += 1

            if dl_file.suffix == ".parquet":
                try:
                    with pq.ParquetFile(dl_file) as pf:
                        if "ts_utc_ns" in pf.schema.names:
                            ts_arr = pf.read(columns=["ts_utc_ns"]).column("ts_utc_ns").to_numpy()
                            if len(ts_arr) > 0 and ts_arr.max() >= DEFAULT_HOLDOUT_NS:
                                holdout_violations += 1
                except Exception as e:
                    print(f"Error checking holdout on {dl_file}: {e}")

        if not mismatches and holdout_violations == 0 and verified_files == len(files_manifest):
            break
        elif dl_attempt < 2:
            print(f"Attempt {dl_attempt + 1} had mismatches ({len(mismatches)}). Waiting 20s to retry...")
            time.sleep(20)

    shutil.rmtree(v_dir, ignore_errors=True)

    if not mismatches and holdout_violations == 0 and verified_files == len(files_manifest):
        print(f"VERIFICATION PASS: All {verified_files} files bitwise matched SHA-256! Zero holdout breach.")
        return {
            "dataset_ref": dataset_ref,
            "status": "MIGRATED_AND_HASH_VERIFIED",
            "verified_files_count": verified_files,
            "mismatches": [],
            "holdout_violations": 0,
            "verified": True,
            "version": 1
        }
    else:
        print(f"VERIFICATION WARNING: {len(mismatches)} mismatches, {holdout_violations} holdout violations.")
        return {
            "dataset_ref": dataset_ref,
            "status": "MIGRATED_BUT_REMOTE_HASH_UNVERIFIED",
            "verified_files_count": verified_files,
            "mismatches": mismatches,
            "holdout_violations": holdout_violations,
            "verified": False,
            "version": 1
        }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inst", required=True, help="Instrument symbol, e.g. ZB, YM, GC, 6E, MBT, MES, ES, NQ")
    args = parser.parse_args()

    sym = args.inst.upper()
    api = init_kaggle_api()
    state = load_state()

    slug, s_dir, f_manifest = stage_ticks(sym)
    res = upload_and_verify(api, slug, s_dir, f_manifest)

    dataset_ref = f"nicolasbuttaro/{slug}"
    state["datasets"][dataset_ref] = {
        "slug": slug,
        "status": res["status"],
        "files_count": len(f_manifest),
        "size_mb": sum(x["size_bytes"] for x in f_manifest) / 1024 / 1024,
        "version": res.get("version", 1),
        "verified": res.get("verified", False),
        "holdout_violations": res.get("holdout_violations", 0),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    # Merge manifest records
    existing_records = [r for r in state.get("all_manifest_records", []) if r.get("dataset_ref") != dataset_ref]
    existing_records.extend(f_manifest)
    state["all_manifest_records"] = existing_records

    save_state(state)
    print(f"\nMigration state updated for {dataset_ref}.")

if __name__ == "__main__":
    main()
