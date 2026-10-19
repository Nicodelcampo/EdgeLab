#!/usr/bin/env python3
"""Verify canonical Parquets and build a private, physically pre-holdout package.

The source files are checked against both docs/datos_manifiesto.json and the
campaign input registry. Files crossing the seal are recut by a custody step;
the research package receives a new effective registry and dual lineage hashes.
No upload is performed by this tool.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.kaggle.execution import atomic_write_json, canonical_sha256, sha256_file
from tools.build_kaggle_bundle import evaluate_license, parse_license_gate

HOLDOUT_OPEN_NS = 1782856800000000000
BUILD_TOKEN = "AUTHORIZE_BUILD_KAGGLE_RESEARCH_DATASET_V1"


def registry_records(registry: dict) -> list[tuple[str, dict]]:
    contracts = registry.get("contracts")
    if not isinstance(contracts, dict) or not contracts:
        raise RuntimeError("input registry has no contracts")
    selected = registry.get("selected_contracts") or list(contracts)
    if set(selected) != set(contracts):
        raise RuntimeError("selected contracts and registry contracts differ")
    return [(name, contracts[name]) for name in selected]


def manifest_by_filename(data_manifest: dict) -> dict[str, dict]:
    candidates: dict[str, list[tuple[bool, dict]]] = {}
    for declared_path, record in (data_manifest.get("archivos") or {}).items():
        name = Path(declared_path).name
        is_quarantine = any(
            part.startswith(("6E_dirty", "6E_prev", "quarantine", "dirty"))
            for part in Path(declared_path).parts
        )
        candidates.setdefault(name, []).append((is_quarantine, record))

    out: dict[str, dict] = {}
    for name, entries in candidates.items():
        clean = [r for is_q, r in entries if not is_q]
        active = clean if clean else [r for _, r in entries]
        first = active[0]
        if any(r != first for r in active[1:]):
            raise RuntimeError(f"ambiguous data manifest filename: {name}")
        out[name] = first
    return out


def footer_bounds(path: Path, ts_column: str = "ts_utc_ns") -> tuple[int, int, int]:
    pf = pq.ParquetFile(path)
    try:
        column_index = pf.schema_arrow.names.index(ts_column)
    except ValueError as exc:
        raise RuntimeError(f"missing {ts_column}: {path.name}") from exc
    mins, maxs = [], []
    for i in range(pf.metadata.num_row_groups):
        stats = pf.metadata.row_group(i).column(column_index).statistics
        if stats is None or not stats.has_min_max:
            raise RuntimeError(f"missing timestamp statistics: {path.name}")
        mins.append(int(stats.min))
        maxs.append(int(stats.max))
    return min(mins), max(maxs), int(pf.metadata.num_rows)


def verify_sources(source_dir: Path, registry: dict, data_manifest: dict) -> list[dict]:
    declared = manifest_by_filename(data_manifest)
    verified = []
    for contract, entry in registry_records(registry):
        filename = entry["parquet_file"]
        path = source_dir / filename
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"missing source Parquet: {filename}")
        dm = declared.get(filename)
        if dm is None:
            raise RuntimeError(f"source absent from docs/datos_manifiesto.json: {filename}")
        actual_bytes = path.stat().st_size
        actual_sha = sha256_file(path)
        expected_sha = entry["parquet_sha256"]
        expected_bytes = int(entry["bytes"])
        if actual_sha != expected_sha or actual_bytes != expected_bytes:
            raise RuntimeError(f"input registry mismatch: {filename}")
        if actual_sha != dm.get("sha256") or actual_bytes != int(dm.get("bytes", -1)):
            raise RuntimeError(f"datos_manifiesto mismatch: {filename}")
        ts_min, ts_max, rows = footer_bounds(path)
        verified.append(
            {
                "contract": contract,
                "file": filename,
                "path": path,
                "bytes": actual_bytes,
                "sha256": actual_sha,
                "rows": rows,
                "ts_min_utc_ns": ts_min,
                "ts_max_utc_ns": ts_max,
                "crosses_holdout": ts_max >= HOLDOUT_OPEN_NS,
            }
        )
    return verified


def recut_parquet(
    source: Path,
    destination: Path,
    *,
    start_utc_ns: int | None,
    end_utc_ns: int,
    batch_rows: int,
) -> dict:
    pf = pq.ParquetFile(source)
    schema = pf.schema_arrow
    ts_index = schema.get_field_index("ts_utc_ns")
    if ts_index < 0:
        raise RuntimeError(f"missing ts_utc_ns: {source.name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    writer = pq.ParquetWriter(tmp, schema, compression="zstd", use_dictionary=True)
    rows_in = rows_out = 0
    min_out = max_out = None
    try:
        for batch in pf.iter_batches(batch_size=batch_rows):
            rows_in += batch.num_rows
            ts = batch.column(ts_index)
            mask = pc.less(ts, pa.scalar(end_utc_ns, type=ts.type))
            if start_utc_ns is not None:
                mask = pc.and_(mask, pc.greater_equal(ts, pa.scalar(start_utc_ns, type=ts.type)))
            kept = batch.filter(mask)
            if kept.num_rows:
                vals = kept.column(ts_index)
                current_min = int(pc.min(vals).as_py())
                current_max = int(pc.max(vals).as_py())
                min_out = current_min if min_out is None else min(min_out, current_min)
                max_out = current_max if max_out is None else max(max_out, current_max)
                writer.write_table(pa.Table.from_batches([kept], schema=schema))
                rows_out += kept.num_rows
    finally:
        writer.close()
    if rows_out == 0 or max_out is None or max_out >= end_utc_ns:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"recut produced no certifiable research rows: {source.name}")
    os.replace(tmp, destination)
    return {
        "rows_source": rows_in,
        "rows_packaged": rows_out,
        "rows_removed": rows_in - rows_out,
        "ts_min_utc_ns": min_out,
        "ts_max_utc_ns": max_out,
        "custody_recut": True,
    }


def build_package(args: argparse.Namespace, registry: dict, verified: list[dict], license_info: dict) -> dict:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    effective = copy.deepcopy(registry)
    packaged = []
    custody_accessed = False
    for record in verified:
        source = record["path"]
        destination = args.output_dir / record["file"]
        within_lower = args.start_utc_ns is None or record["ts_min_utc_ns"] >= args.start_utc_ns
        if within_lower and record["ts_max_utc_ns"] < HOLDOUT_OPEN_NS:
            shutil.copy2(source, destination)
            details = {
                "rows_source": record["rows"],
                "rows_packaged": record["rows"],
                "rows_removed": 0,
                "ts_min_utc_ns": record["ts_min_utc_ns"],
                "ts_max_utc_ns": record["ts_max_utc_ns"],
                "custody_recut": False,
            }
        else:
            details = recut_parquet(
                source,
                destination,
                start_utc_ns=args.start_utc_ns,
                end_utc_ns=HOLDOUT_OPEN_NS,
                batch_rows=args.batch_rows,
            )
            custody_accessed = True
        package_sha = sha256_file(destination)
        package_bytes = destination.stat().st_size
        if details["ts_max_utc_ns"] >= HOLDOUT_OPEN_NS:
            raise RuntimeError(f"packaged file still reaches holdout: {record['file']}")
        entry = effective["contracts"][record["contract"]]
        entry["source_parquet_sha256"] = record["sha256"]
        entry["source_bytes"] = record["bytes"]
        entry["parquet_sha256"] = package_sha
        entry["bytes"] = package_bytes
        entry["rows"] = details["rows_packaged"]
        entry["research_recut_end_utc_ns_exclusive"] = HOLDOUT_OPEN_NS
        packaged.append(
            {
                "contract": record["contract"],
                "file": record["file"],
                "bytes": package_bytes,
                "sha256": package_sha,
                "ts_min_utc_ns": details["ts_min_utc_ns"],
                "ts_max_utc_ns": details["ts_max_utc_ns"],
                "rows": details["rows_packaged"],
                "rows_removed": details["rows_removed"],
                "source_bytes": record["bytes"],
                "source_sha256": record["sha256"],
                "custody_recut": details["custody_recut"],
            }
        )
    effective_path = args.output_dir / "effective_input_registry.json"
    effective_sha = atomic_write_json(effective_path, effective)
    package = {
        "schema_version": "edgelab_kaggle_research_package_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_id": args.dataset_id,
        "visibility": "private_only",
        "source_input_registry_file_sha256": sha256_file(args.input_registry),
        "source_data_manifest_file_sha256": sha256_file(args.data_manifest),
        "effective_input_registry_file": effective_path.name,
        "effective_input_registry_file_sha256": effective_sha,
        "holdout_open_utc_ns": HOLDOUT_OPEN_NS,
        "research_max_trade_date": 20260630,
        "research_dataset_holdout_present": False,
        "custody_process_holdout_rows_may_have_been_decoded_for_recut": custody_accessed,
        "license_gate_sha256": sha256_file(args.license_doc),
        "license_status": license_info.get("status"),
        "files": packaged,
    }
    package["payload_sha256"] = canonical_sha256(package)
    manifest_path = args.output_dir / "kaggle_research_package_manifest.json"
    atomic_write_json(manifest_path, package)
    checksums = [f"{x['sha256']}  {x['file']}" for x in packaged]
    checksums.extend(
        [
            f"{sha256_file(effective_path)}  {effective_path.name}",
            f"{sha256_file(manifest_path)}  {manifest_path.name}",
        ]
    )
    (args.output_dir / "files.sha256").write_text(
        "\n".join(checksums) + "\n", encoding="utf-8", newline="\n"
    )
    metadata = {
        "title": f"EdgeLab {registry.get('instrument', 'research')} pre-holdout ticks",
        "id": args.dataset_id,
        "isPrivate": True,
        "licenses": [{"name": license_info.get("kaggle_license_name") or "other"}],
        "description": (
            "Private EdgeLab research input. Physically excludes the holdout beginning "
            "2026-06-30T22:00:00Z. Redistribution and public visibility are forbidden."
        ),
    }
    atomic_write_json(args.output_dir / "dataset-metadata.json", metadata)
    return package


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-registry", type=Path, required=True)
    parser.add_argument("--data-manifest", type=Path, default=REPO_ROOT / "docs/datos_manifiesto.json")
    parser.add_argument("--license-doc", type=Path, default=REPO_ROOT / "docs/research/DATA_LICENSE_DECISION.md")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--start-utc-ns", type=int)
    parser.add_argument("--batch-rows", type=int, default=1_000_000)
    parser.add_argument("--authorization-token")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--build", action="store_true")
    args = parser.parse_args(argv)
    try:
        registry = json.loads(args.input_registry.read_text(encoding="utf-8"))
        data_manifest = json.loads(args.data_manifest.read_text(encoding="utf-8"))
        verified = verify_sources(args.source_dir, registry, data_manifest)
        license_info = evaluate_license(parse_license_gate(args.license_doc))
        preflight = {
            "schema_version": "edgelab_kaggle_dataset_preflight_v1",
            "status": "KAGGLE_DATASET_PREFLIGHT_PASS" if license_info["ok"] else "ABSTAIN_LICENSE",
            "source_files_verified": len(verified),
            "source_bytes_verified": sum(x["bytes"] for x in verified),
            "files_requiring_recut": [x["file"] for x in verified if x["crosses_holdout"]],
            "holdout_open_utc_ns": HOLDOUT_OPEN_NS,
            "license": license_info,
            "build_executed": False,
            "upload_executed": False,
        }
        if args.preflight_only:
            print(json.dumps(preflight, indent=2, sort_keys=True, ensure_ascii=False))
            return 0 if license_info["ok"] else 2
        if not license_info["ok"]:
            raise RuntimeError("ABSTAIN_LICENSE: license decision is not approved")
        if args.authorization_token != BUILD_TOKEN:
            raise RuntimeError("missing or invalid dataset build authorization token")
        package = build_package(args, registry, verified, license_info)
        print(json.dumps({"status": "COMPLETE_PRIVATE_RESEARCH_PACKAGE", "manifest": package}, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "ABSTAIN_KAGGLE_DATASET", "message": str(exc), "upload_executed": False}, indent=2, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
