# -*- coding: utf-8 -*-
"""Kaggle-only, fail-closed creation sweep for BigTrap2 NQ V2.

The kernel accepts only a frozen campaign, a private Kaggle input package that
physically excludes the holdout, and an output below /kaggle/working. It never
uses the raw custody registry as its execution registry.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import load_canonical_parquet
from edgelab.bridge.bars import build_time_bars, build_tick_bars, build_footprints
from edgelab.bridge.indicators.bigtrap2_creation_only import detect_creations_only
from tools.build_event_store_all5_v2 import expand_sessions

CT = ZoneInfo("America/Chicago")
HOLDOUT_CUTOFF_UTC_NS = 1782856800000000000
KAGGLE_INPUT_ROOT = Path("/kaggle/input")
KAGGLE_WORKING_ROOT = Path("/kaggle/working")
PACKAGE_SCHEMA = "edgelab_kaggle_research_package_v1"


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _is_hex64(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"[FAIL_CLOSED] Invalid or missing JSON: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"[FAIL_CLOSED] JSON root must be an object: {path}")
    return value


def _safe_child(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if not relative or rel.is_absolute() or ".." in rel.parts:
        raise RuntimeError(f"[FAIL_CLOSED] Unsafe package-relative path: {relative!r}")
    root_resolved = root.resolve()
    candidate = (root_resolved / rel).resolve()
    if not candidate.is_relative_to(root_resolved):
        raise RuntimeError(f"[FAIL_CLOSED] Package path escapes data root: {relative!r}")
    return candidate


def validate_kaggle_runtime(
    data_dir: Path,
    output_json: Path,
    *,
    input_root: Path = KAGGLE_INPUT_ROOT,
    working_root: Path = KAGGLE_WORKING_ROOT,
    environment: Mapping[str, str] | None = None,
) -> tuple[Path, Path]:
    """Require a genuine Kaggle path layout and keep all output in working."""
    env = os.environ if environment is None else environment
    if not input_root.is_dir() or not working_root.is_dir():
        raise RuntimeError("[FAIL_CLOSED] Kaggle runtime roots are unavailable")
    if not (env.get("KAGGLE_KERNEL_RUN_TYPE") or env.get("KAGGLE_URL_BASE")):
        raise RuntimeError("[FAIL_CLOSED] Kaggle runtime attestation is unavailable")

    input_resolved = input_root.resolve()
    working_resolved = working_root.resolve()
    data_resolved = data_dir.resolve()
    output_resolved = output_json.resolve()

    if not data_resolved.is_dir() or not data_resolved.is_relative_to(input_resolved):
        raise RuntimeError(
            f"[FAIL_CLOSED] --data-dir must be an existing directory below {input_root}"
        )
    if not output_resolved.is_relative_to(working_resolved):
        raise RuntimeError(
            f"[FAIL_CLOSED] --output-json must be below {working_root}"
        )
    if output_resolved == working_resolved or output_resolved.is_symlink():
        raise RuntimeError("[FAIL_CLOSED] --output-json must name a non-symlink file")
    return data_resolved, output_resolved


def cme_session_to_utc_bounds_ns(session_id: str) -> tuple[int, int]:
    """Convert a YYYYMMDD CME trade date to its DST-aware [open, close) UTC bounds."""
    close_ct = datetime.strptime(session_id, "%Y%m%d").replace(
        hour=16, minute=0, second=0, microsecond=0, tzinfo=CT
    )
    open_ct = (close_ct - timedelta(days=1)).replace(
        hour=17, minute=0, second=0, microsecond=0
    )
    return (
        int(open_ct.astimezone(timezone.utc).timestamp() * 1_000_000_000),
        int(close_ct.astimezone(timezone.utc).timestamp() * 1_000_000_000),
    )


def cme_session_dates(ts_ns: np.ndarray) -> np.ndarray:
    seconds = ts_ns // 1_000_000_000
    local = pd.to_datetime(seconds, unit="s", utc=True).tz_convert("America/Chicago")
    trade_date = local + pd.to_timedelta(np.where(local.hour >= 17, 1, 0), unit="D")
    return trade_date.strftime("%Y%m%d").to_numpy()


def verify_git_clean_and_head(expected_commit: str) -> dict[str, Any]:
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
    except Exception as exc:
        raise RuntimeError(f"[FAIL_CLOSED] Failed to query Git state: {exc}") from exc
    if status:
        raise RuntimeError(f"[FAIL_CLOSED] Working tree is dirty:\n{status}")
    if head != expected_commit:
        raise RuntimeError(
            f"[FAIL_CLOSED] HEAD {head} does not match expected commit {expected_commit}"
        )
    return {"head": head, "dirty": False}


def verify_runtime_execution_gates(
    spec: dict[str, Any], expected_commit: str, execution_token: str | None
) -> None:
    if spec.get("status") != "FROZEN_PREFLIGHT_READY":
        raise PermissionError(
            "[FAIL_CLOSED] Spec status must be FROZEN_PREFLIGHT_READY; "
            "draft specs remain non-executable regardless of token"
        )
    if spec.get("execution_authorized") is not True:
        raise PermissionError("[FAIL_CLOSED] execution_authorized must be true")
    if not execution_token or execution_token != spec.get("execution_token"):
        raise PermissionError("[FAIL_CLOSED] Invalid or missing campaign token")
    if spec.get("frozen_commit") != expected_commit:
        raise RuntimeError("[FAIL_CLOSED] frozen_commit differs from --expected-commit")

    platform = spec.get("execution_platform") or {}
    if (
        platform.get("platform") != "KAGGLE"
        or platform.get("kaggle_only") is not True
        or platform.get("local_heavy_execution_allowed") is not False
    ):
        raise RuntimeError("[FAIL_CLOSED] Spec does not freeze the Kaggle-only policy")

    binding = spec.get("binding") or {}
    for key in ("package_manifest_sha256", "effective_input_registry_sha256"):
        if not _is_hex64(binding.get(key)):
            raise RuntimeError(f"[FAIL_CLOSED] Frozen spec requires a physical {key}")
    verify_git_clean_and_head(expected_commit)


def verify_inputs_fail_closed(
    data_dir: Path, input_registry: dict[str, Any]
) -> dict[str, Path]:
    contracts = input_registry.get("contracts")
    if not isinstance(contracts, dict) or not contracts:
        raise RuntimeError("[FAIL_CLOSED] Effective input registry has no contracts")
    verified: dict[str, Path] = {}
    for contract, entry in contracts.items():
        filename = entry.get("parquet_file")
        if not isinstance(filename, str):
            raise RuntimeError(f"[FAIL_CLOSED] Missing parquet_file for {contract}")
        path = _safe_child(data_dir, filename)
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(f"[FAIL_CLOSED] Required input Parquet missing: {path}")
        if path.stat().st_size != int(entry.get("bytes", -1)):
            raise RuntimeError(f"[FAIL_CLOSED] Size mismatch for {contract}")
        if compute_sha256(path) != entry.get("parquet_sha256"):
            raise RuntimeError(f"[FAIL_CLOSED] SHA-256 mismatch for {contract}")
        verified[contract] = path
    return verified


def verify_package_and_effective_registry(
    data_dir: Path, spec: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Bind the physical package, effective registry and packaged Parquets."""
    binding = spec["binding"]
    manifest_path = _safe_child(data_dir, binding["package_manifest_file"])
    expected_manifest_sha = binding["package_manifest_sha256"]
    actual_manifest_sha = compute_sha256(manifest_path)
    if actual_manifest_sha != expected_manifest_sha:
        raise RuntimeError("[FAIL_CLOSED] Package manifest file SHA-256 mismatch")

    manifest = _load_json_object(manifest_path)
    if manifest.get("schema_version") != PACKAGE_SCHEMA:
        raise RuntimeError("[FAIL_CLOSED] Unsupported package manifest schema")
    payload = manifest.get("payload_sha256")
    body = {key: value for key, value in manifest.items() if key != "payload_sha256"}
    if not _is_hex64(payload) or canonical_sha256(body) != payload:
        raise RuntimeError("[FAIL_CLOSED] Package manifest payload hash mismatch")
    if manifest.get("holdout_open_utc_ns") != HOLDOUT_CUTOFF_UTC_NS:
        raise RuntimeError("[FAIL_CLOSED] Package holdout boundary mismatch")
    if manifest.get("research_dataset_holdout_present") is not False:
        raise RuntimeError("[FAIL_CLOSED] Package does not certify physical holdout absence")
    if manifest.get("visibility") != "private_only":
        raise RuntimeError("[FAIL_CLOSED] Package visibility must be private_only")
    if (
        manifest.get("source_input_registry_file_sha256")
        != binding["source_input_registry_sha256"]
    ):
        raise RuntimeError("[FAIL_CLOSED] Package source registry lineage mismatch")

    effective_name = manifest.get("effective_input_registry_file")
    if effective_name != binding["effective_input_registry_file"]:
        raise RuntimeError("[FAIL_CLOSED] Effective registry filename mismatch")
    effective_path = _safe_child(data_dir, effective_name)
    effective_sha = compute_sha256(effective_path)
    if (
        effective_sha != manifest.get("effective_input_registry_file_sha256")
        or effective_sha != binding["effective_input_registry_sha256"]
    ):
        raise RuntimeError("[FAIL_CLOSED] Effective registry SHA-256 mismatch")
    effective = _load_json_object(effective_path)

    expected_contracts = set(spec["universe"]["contracts"])
    effective_contracts = effective.get("contracts") or {}
    if set(effective_contracts) != expected_contracts:
        raise RuntimeError("[FAIL_CLOSED] Effective registry contract universe mismatch")

    package_records = manifest.get("files")
    if not isinstance(package_records, list):
        raise RuntimeError("[FAIL_CLOSED] Package manifest files must be an array")
    by_contract = {
        record.get("contract"): record
        for record in package_records
        if isinstance(record, dict) and isinstance(record.get("contract"), str)
    }
    if set(by_contract) != expected_contracts:
        raise RuntimeError("[FAIL_CLOSED] Package manifest contract universe mismatch")

    for contract in sorted(expected_contracts):
        record = by_contract[contract]
        entry = effective_contracts[contract]
        if (
            record.get("file") != entry.get("parquet_file")
            or record.get("bytes") != entry.get("bytes")
            or record.get("sha256") != entry.get("parquet_sha256")
        ):
            raise RuntimeError(f"[FAIL_CLOSED] Package/effective registry mismatch: {contract}")
        max_ns = record.get("ts_max_utc_ns")
        if not isinstance(max_ns, int) or max_ns >= HOLDOUT_CUTOFF_UTC_NS:
            raise RuntimeError(f"[FAIL_CLOSED] Packaged input reaches holdout: {contract}")

    verified_paths = verify_inputs_fail_closed(data_dir, effective)
    provenance = {
        "package_manifest_file_sha256": actual_manifest_sha,
        "package_manifest_payload_sha256": payload,
        "effective_input_registry_file_sha256": effective_sha,
        "physical_holdout_absence": True,
        "verified_contracts": sorted(verified_paths),
    }
    return manifest, effective, provenance


def run_creation_grid_for_contract(
    pq_path: Path,
    contract: str,
    min_start_ns: int,
    max_end_ns: int,
    valid_sessions: set[str],
    bar_series_types: dict[str, Any],
    grid_configs: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    effective_end = min(max_end_ns, HOLDOUT_CUTOFF_UTC_NS)
    ticks = load_canonical_parquet(
        path=pq_path,
        contract=contract,
        start_utc_ns=min_start_ns,
        end_utc_ns=effective_end,
        instrument="NQ",
    )
    if np.any(ticks.ts_ns >= HOLDOUT_CUTOFF_UTC_NS):
        raise RuntimeError(f"[FAIL_CLOSED] Holdout tick decoded for {contract}")

    events: dict[str, list[dict[str, Any]]] = {
        config["cfg_id"]: [] for config in grid_configs
    }
    for bar_type, bar_info in bar_series_types.items():
        configs = [config for config in grid_configs if config["bar_type"] == bar_type]
        if not configs:
            continue
        bars = (
            build_time_bars(ticks, bar_info["param"])
            if bar_info["kind"] == "time"
            else build_tick_bars(ticks, bar_info["param"], reiniciar_por_sesion=True)
        )
        footprints = build_footprints(ticks, bars)
        session_ids = cme_session_dates(bars.end_ns)
        for config in configs:
            zones = detect_creations_only(
                ticks,
                bars,
                footprints,
                params={
                    "imbalance_ratio": config["imbalance_ratio"],
                    "min_trap_volume": config["min_trap_volume"],
                    "min_export_volume": config["min_trap_volume"],
                    "use_wick_filter": False,
                },
            )
            for zone in zones:
                bar_index = zone["bar_idx"]
                if (
                    0 <= bar_index < len(session_ids)
                    and session_ids[bar_index] in valid_sessions
                ):
                    events[config["cfg_id"]].append(
                        {
                            "contract": contract,
                            "session_id": session_ids[bar_index],
                            "bar_time_ns": zone["bar_time_ns"],
                            "side": zone["side"],
                            "top": zone["top"],
                            "bottom": zone["bottom"],
                            "width_ticks": zone["width_ticks"],
                            "bar_idx": bar_index,
                        }
                    )
        del bars, footprints, session_ids
        gc.collect()
    del ticks
    gc.collect()
    return events


def _atomic_write_json(path: Path, value: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(raw, encoding="utf-8", newline="\n")
    os.replace(temporary, path)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--execution-token")
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args(argv)

    data_dir, output_json = validate_kaggle_runtime(args.data_dir, args.output_json)
    spec = _load_json_object(args.spec)
    execution_token = args.execution_token or os.environ.get("EDGELAB_AUTHORIZATION_TOKEN")
    verify_runtime_execution_gates(spec, args.expected_commit, execution_token)

    binding = spec["binding"]
    session_registry_path = REPO_ROOT / binding["session_registry_path"]
    source_registry_path = REPO_ROOT / binding["source_input_registry_path"]
    if compute_sha256(session_registry_path) != binding["session_registry_sha256"]:
        raise RuntimeError("[FAIL_CLOSED] Session registry SHA-256 mismatch")
    if compute_sha256(source_registry_path) != binding["source_input_registry_sha256"]:
        raise RuntimeError("[FAIL_CLOSED] Source input registry SHA-256 mismatch")

    _, effective_registry, package_provenance = verify_package_and_effective_registry(
        data_dir, spec
    )
    verified_paths = verify_inputs_fail_closed(data_dir, effective_registry)
    session_registry = _load_json_object(session_registry_path)
    expanded = expand_sessions(session_registry)

    sessions_by_contract: dict[str, set[str]] = {}
    bounds_by_contract: dict[str, tuple[int, int]] = {}
    for row in expanded:
        contract = row["contract"]
        session_id = row["cme_session_id"]
        sessions_by_contract.setdefault(contract, set()).add(session_id)
        start_ns, end_ns = cme_session_to_utc_bounds_ns(session_id)
        if end_ns > HOLDOUT_CUTOFF_UTC_NS:
            raise RuntimeError("[FAIL_CLOSED] Registered session reaches holdout")
        if contract not in bounds_by_contract:
            bounds_by_contract[contract] = (start_ns, end_ns)
        else:
            current_start, current_end = bounds_by_contract[contract]
            bounds_by_contract[contract] = (
                min(current_start, start_ns),
                max(current_end, end_ns),
            )

    total_sessions = sum(len(values) for values in sessions_by_contract.values())
    if total_sessions != 234:
        raise RuntimeError(f"[FAIL_CLOSED] Expected 234 sessions, found {total_sessions}")

    grid_configs = []
    for bar_type in spec["grid"]["bar_series_types"]:
        for imbalance_ratio in spec["grid"]["imbalance_ratios"]:
            for minimum_volume in spec["grid"]["min_trap_volumes"]:
                grid_configs.append(
                    {
                        "cfg_id": (
                            f"{bar_type}_IMB{int(imbalance_ratio * 10)}_VOL{minimum_volume}"
                        ),
                        "bar_type": bar_type,
                        "imbalance_ratio": imbalance_ratio,
                        "min_trap_volume": minimum_volume,
                    }
                )
    if len(grid_configs) != spec["grid"]["total_configurations"]:
        raise RuntimeError("[FAIL_CLOSED] Grid cardinality mismatch")

    all_events = {config["cfg_id"]: [] for config in grid_configs}
    started = time.time()
    for contract in session_registry["selection"]["contracts"]:
        contract_events = run_creation_grid_for_contract(
            pq_path=verified_paths[contract],
            contract=contract,
            min_start_ns=bounds_by_contract[contract][0],
            max_end_ns=bounds_by_contract[contract][1],
            valid_sessions=sessions_by_contract[contract],
            bar_series_types=spec["grid"]["bar_series_types"],
            grid_configs=grid_configs,
        )
        for config_id, rows in contract_events.items():
            all_events[config_id].extend(rows)

    results = []
    for config in grid_configs:
        rows = all_events[config["cfg_id"]]
        count = len(rows)
        sessions = len({row["session_id"] for row in rows})
        buyers = sum(row["side"] == "B" for row in rows)
        widths = [row["width_ticks"] for row in rows] or [0]
        results.append(
            {
                **config,
                "total_events": count,
                "sessions_with_events": sessions,
                "coverage_pct": round(sessions / total_sessions * 100.0, 2),
                "buy_events": buyers,
                "sell_events": count - buyers,
                "buy_ratio": round(buyers / count, 4) if count else 0.0,
                "events_per_session": round(count / total_sessions, 2),
                "mean_width_ticks": round(float(np.mean(widths)), 2),
                "median_width_ticks": round(float(np.median(widths)), 2),
                "p95_width_ticks": (
                    round(float(np.percentile(widths, 95)), 2) if rows else 0.0
                ),
            }
        )
    results.sort(key=lambda row: row["total_events"], reverse=True)

    result = {
        "schema_version": "bigtrap2_nq_tickframes_sweep_v2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_commit": args.expected_commit,
        "spec_file_sha256": compute_sha256(args.spec),
        "input_provenance": package_provenance,
        "total_configs": len(grid_configs),
        "total_cme_sessions": total_sessions,
        "elapsed_seconds": round(time.time() - started, 1),
        "firewalls": {
            "future_price_path_accessed": False,
            "first_touch_accessed": False,
            "mfe_mae_accessed": False,
            "pnl_accessed": False,
            "holdout_rows_decoded": False,
            "holdout_touched": False,
            "winner_selected": False,
            "edge_declared": False,
            "promotion_eligible": False,
        },
        "results": results,
    }
    result_sha = _atomic_write_json(output_json, result)
    attestation = {
        "schema_version": "bt2_nq_v2_execution_attestation_v1",
        "result_file": output_json.name,
        "result_file_sha256": result_sha,
        "future_price_path_accessed": False,
        "first_touch_accessed": False,
        "pnl_accessed": False,
        "holdout_touched": False,
        "holdout_rows_decoded": False,
    }
    _atomic_write_json(output_json.parent / "execution_attestation.json", attestation)

    # Output is external, so this check now proves code identity instead of self-aborting.
    verify_git_clean_and_head(args.expected_commit)
    print(json.dumps({"status": "COMPLETE_TARGET_FREE_KAGGLE_SWEEP", "result": str(output_json), "sha256": result_sha}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
