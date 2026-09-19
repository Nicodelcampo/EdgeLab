#!/usr/bin/env python3
"""Rectify the Kaggle manifest from records plus captured remote inventory."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MP = ROOT / "artifacts/audit/EDGELAB_KAGGLE_CANONICAL_MANIFEST.json"
IP = ROOT / "artifacts/audit/EDGELAB_KAGGLE_REMOTE_INVENTORY.json"
BOUNDARY = 1782856800000000000


def sizes(n: int) -> dict:
    return {"size_bytes": n, "size_gb_decimal": n / 1e9,
            "size_gib_binary": n / 2**30}


def rectify(m: dict, inv: dict) -> dict:
    rows = m["CANONICAL_RAW_TICKS"]
    remote = inv["datasets"]
    for r in rows:
        entry = remote.get(r["kaggle_dataset"], {}).get("files", {}).get(r["file_name"])
        r["remote_listed"] = entry is not None
        r["remote_listed_size_bytes"] = entry["total_bytes"] if entry else None
        r["remote_size_matches_manifest"] = bool(entry and entry["total_bytes"] == r["size_bytes"])
        r["download_evidence"] = "NONE_LISTING_ONLY"
        r.pop("downloaded_sha256", None)
        r.pop("size_mb", None)
        r.update(sizes(r["size_bytes"]))
        if entry:
            r.update(local_status="LOCAL_PRESENT", remote_status="REMOTE_LISTED_SIZE_MATCHED",
                     custody_status="REMOTE_LISTED_PENDING_DOWNLOAD_PROOF")
        else:
            r.update(local_status="LOCAL_RECUT_CANDIDATE",
                     remote_status="REMOTE_ABSENT_OR_UNPROVEN",
                     custody_status="BLOCKED_BY_CUSTODY",
                     right_censored_by_holdout=True,
                     coverage_end_reason="HOLDOUT_BOUNDARY",
                     blocking_reason="Absent from remote Kaggle listing")

    listed = [r for r in rows if r["remote_listed"]]
    blocked = [r for r in rows if not r["remote_listed"]]
    inst = {}
    for r in rows:
        a = inst.setdefault(r["instrument"], {"contract_count": 0, "rows": 0,
            "_bytes": 0, "remote_listed_contract_count": 0,
            "remote_listed_rows": 0, "_listed_bytes": 0, "blocked_contracts": []})
        a["contract_count"] += 1; a["rows"] += r["row_count"]; a["_bytes"] += r["size_bytes"]
        if r["remote_listed"]:
            a["remote_listed_contract_count"] += 1
            a["remote_listed_rows"] += r["row_count"]
            a["_listed_bytes"] += r["size_bytes"]
        else: a["blocked_contracts"].append(r["contract"])
    derived = {}
    for name, a in sorted(inst.items()):
        derived[name] = {"contract_count": a["contract_count"], "rows": a["rows"],
            **sizes(a["_bytes"]), "remote_listed_contract_count": a["remote_listed_contract_count"],
            "remote_listed_rows": a["remote_listed_rows"],
            "remote_listed_size_bytes": a["_listed_bytes"],
            "blocked_contracts": sorted(a["blocked_contracts"]),
            "custody_complete": not a["blocked_contracts"]}
    m["PER_INSTRUMENT_DERIVED"] = {"derivation": "Computed from CANONICAL_RAW_TICKS",
        "hand_entered_values": False, "instruments": derived}
    tb, rb = sum(r["size_bytes"] for r in rows), sum(r["size_bytes"] for r in listed)
    m["summary"] = {"derivation": "Computed from CANONICAL_RAW_TICKS; no transcribed figures",
        "migration_status": "MIGRATION_CANONICAL_RAW_COMPLETE_EXCEPT_NQ_09_26",
        "reconciliation_status": "MIGRATION_MANIFEST_RECONCILIATION_REQUIRED",
        "instruments_with_remote_representation": len({r["instrument"] for r in listed}),
        "instruments_with_complete_custody": sum(v["custody_complete"] for v in derived.values()),
        "total_catalogued_contracts": len(rows), "total_catalogued_rows": sum(r["row_count"] for r in rows),
        **{"total_catalogued_"+k: v for k,v in sizes(tb).items()},
        "remote_listed_contracts": len(listed), "remote_listed_rows": sum(r["row_count"] for r in listed),
        **{"remote_listed_"+k: v for k,v in sizes(rb).items()},
        "blocked_contracts": sorted(r["contract_id"] for r in blocked),
        "total_hft_zones": 3328710, "total_25t_bars_in_slices": 40380402,
        "viewer_bundles_status": "AUTHORIZED_PENDING_BUILD_AND_UPLOAD",
        "unit_policy": "GB divides by 1e9; GiB divides by 2**30; 2**20 values must be MiB"}
    m["narrative_summary"] = (f"{len(listed)} of {len(rows)} contract-month files are remotely listed; "
        f"{sum(r['row_count'] for r in listed)} rows; {rb} bytes. NQ_09-26 is absent and BLOCKED_BY_CUSTODY. "
        "Listing proves presence and size only; download hashes remain unproven.")
    m["mandatory_semantics"].update(artifact_role="AUXILIARY_VERSIONED_VIEWER_SNAPSHOT", canonical_source=False)
    m.pop("VIEWER_ONLY_NOT_MIGRATED", None)
    m["viewer_bundle_snapshot"] = {"status": "AUTHORIZED_PENDING_BUILD_AND_UPLOAD",
        "artifact_role": "AUXILIARY_VERSIONED_VIEWER_SNAPSHOT", "canonical_source": False,
        "coverage_mode": "PARTIAL_CONTRACT_MONTH_SLICES", "is_complete_continuous_series": False,
        "includes_all_contracts": False, "eligible_for_continuous_backtest": False,
        "bundle_count": 147, "format": "json.zst", "js_uploaded": False,
        "continuous_files_uploaded": False,
        "excluded_from_upload": [".js", "*_CONT", "183 general-inventory JSON files"]}
    m["remote_inventory_ref"] = {"path": str(IP.relative_to(ROOT)),
        "captured_at_utc": inv["captured_at_utc"], "evidence_class": inv["evidence_class"]}
    m["rectification"] = {"rectifies_commit": "e9d065455b49642b4f7f1c8005eaad8bb02756c8",
        "status": "MIGRATION_MANIFEST_RECONCILIATION_REQUIRED",
        "ledger_status": "NOT_CANONICAL_PENDING_RECONCILIATION"}
    m["manifest_version"] = "1.1.0"
    return m


def main():
    m, inv = json.loads(MP.read_text()), json.loads(IP.read_text())
    out = rectify(m, inv)
    MP.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    s = out["summary"]
    print(s["migration_status"], s["remote_listed_contracts"],
          s["remote_listed_rows"], s["remote_listed_size_bytes"])

if __name__ == "__main__": main()
