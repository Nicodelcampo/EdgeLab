#!/usr/bin/env python3
"""Kaggle-only target-free configuration selection for BT2A on NQ.

Planning is metadata-only. Contract partitions and finalization require a frozen
spec, a private physically pre-holdout package, exact Git identity, genuine
Kaggle runtime evidence and the campaign token. The runner writes only creation
coordinates; it never follows the price path after an event.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(ROOT))

from edgelab.kaggle.execution import atomic_write_json, canonical_sha256, sha256_file
from edgelab.research.all5_runtime.bigtrap2absorption import DEFAULTS, run as run_bt2a
from edgelab.research.all5_runtime.ticks import load_canonical_parquet
from tools.build_event_store_all5_v2 import expand_sessions
from tools.sweep_bigtrap2_nq_tickframes_v2 import (
    cme_session_dates,
    cme_session_to_utc_bounds_ns,
    compute_sha256,
    validate_kaggle_runtime,
    verify_git_clean_and_head,
    verify_package_and_effective_registry,
    verify_runtime_execution_gates,
)

DEFAULT_SPEC = ROOT / "specs" / "bt2a_nq_target_free_selection_v1.draft.json"
AUTH_TOKEN = "AUTHORIZE_RUN_BT2A_NQ_TARGET_FREE_SELECTION_V1"
HOLDOUT_NS = 1782856800000000000
DRAFT = "DRAFT_PREAUTHORIZATION"
FROZEN = "FROZEN_PREFLIGHT_READY"
COORDINATE_COLUMNS = [
    "config_id", "contract", "cme_session_id", "event_time_ns", "source_row",
    "direction", "signal_price_ticks", "a_score", "a_threshold", "event_key",
]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")
    return value


def _hex64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _full_params(spec: dict[str, Any], updates: dict[str, Any] | None = None) -> dict[str, Any]:
    params = dict(spec["baseline"])
    params.update(spec["fixed_parameters"])
    params.update(updates or {})
    if int(params["MinHistoryBuckets"]) > int(params["AbsorptionLookback"]):
        params["MinHistoryBuckets"] = int(params["AbsorptionLookback"])
    return params


def config_id(params: dict[str, Any]) -> str:
    return "bt2a_nq_" + canonical_sha256(params)[:16]


def validate_spec(spec: dict[str, Any]) -> None:
    if spec.get("schema_version") != "bt2a_nq_target_free_selection_v1":
        raise RuntimeError("unexpected BT2A NQ selection schema")
    if spec.get("status") not in {DRAFT, FROZEN}:
        raise RuntimeError("invalid BT2A NQ selection status")
    if spec.get("north_star_sha256") != "d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1":
        raise RuntimeError("North Star binding mismatch")
    platform = spec.get("execution_platform") or {}
    if platform.get("platform") != "KAGGLE" or platform.get("kaggle_only") is not True:
        raise RuntimeError("Kaggle-only policy is not frozen")
    if platform.get("local_heavy_execution_allowed") is not False:
        raise RuntimeError("local heavy execution must remain forbidden")
    universe = spec.get("universe") or {}
    if universe.get("instrument") != "NQ" or int(universe.get("contract_sessions", -1)) != 234:
        raise RuntimeError("unexpected NQ universe")
    if len(universe.get("contracts") or []) != 5 or int(universe.get("holdout_open_utc_ns", -1)) != HOLDOUT_NS:
        raise RuntimeError("universe or holdout boundary mismatch")
    baseline = spec.get("baseline") or {}
    levels = spec.get("candidate_levels") or {}
    if set(baseline) != set(levels):
        raise RuntimeError("every candidate axis requires one baseline value")
    for name, values in levels.items():
        if baseline[name] not in values or not values:
            raise RuntimeError(f"baseline absent from candidate levels: {name}")
    params = _full_params(spec)
    if set(params) != set(DEFAULTS):
        raise RuntimeError("candidate and fixed parameters must cover runtime DEFAULTS exactly")
    if int(spec["design"]["interaction_rows"]) < 1:
        raise RuntimeError("interaction design must be non-empty")
    firewall = spec.get("firewall") or {}
    required_false = [
        "LIFECYCLE_ACCESSED", "FIRST_TOUCH_ACCESSED", "FUTURE_PRICE_PATH_ACCESSED",
        "FIRST_PASSAGE_ACCESSED", "MFE_MAE_ACCESSED", "RETURNS_ACCESSED",
        "PNL_ACCESSED", "HOLDOUT_ROWS_DECODED", "HOLDOUT_TOUCHED", "EDGE_DECLARED",
    ]
    if firewall.get("TARGET_FREE") is not True or any(firewall.get(k) is not False for k in required_false):
        raise RuntimeError("target-free firewall is open")
    if spec.get("status") == DRAFT:
        if spec.get("execution_authorized") is not False or spec.get("execution_token") is not None:
            raise RuntimeError("draft cannot carry run capability")
    else:
        if spec.get("execution_authorized") is not True or spec.get("execution_token") != AUTH_TOKEN:
            raise RuntimeError("frozen spec requires exact authorization capability")


def _balanced(values: list[Any], n: int, rng: np.random.Generator) -> list[Any]:
    repeated = (list(values) * math.ceil(n / len(values)))[:n]
    order = rng.permutation(n)
    return [repeated[int(i)] for i in order]


def expand_configs(spec: dict[str, Any]) -> list[dict[str, Any]]:
    validate_spec(spec)
    configs: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(updates: dict[str, Any], stage: str, axis: str | None = None) -> None:
        params = _full_params(spec, updates)
        cid = config_id(params)
        if cid not in seen:
            seen.add(cid)
            configs.append({"config_id": cid, "stage": stage, "axis": axis, "params": params})

    add({}, "headline")
    for name, values in spec["candidate_levels"].items():
        for value in values:
            if value != spec["baseline"][name]:
                add({name: value}, "oat", name)

    design = spec["design"]
    n = int(design["interaction_rows"])
    axes = list(spec["candidate_levels"])
    rng = np.random.default_rng(int(design["seed"]))
    columns = {name: _balanced(list(spec["candidate_levels"][name]), n, rng) for name in axes}
    for row in range(n):
        add({name: columns[name][row] for name in axes}, "interaction")

    if len(configs) < int(design["minimum_unique_configurations"]):
        raise RuntimeError(f"expanded grid too small: {len(configs)}")
    return configs


def expanded_grid(spec: dict[str, Any]) -> dict[str, Any]:
    configs = expand_configs(spec)
    body = {
        "schema_version": "bt2a_nq_expanded_grid_v1",
        "target_free": True,
        "n_configurations": len(configs),
        "configs": configs,
    }
    body["payload_sha256"] = canonical_sha256(body)
    return body


def _repo_binding_checks(spec: dict[str, Any]) -> dict[str, bool]:
    binding = spec["binding"]
    session_path = ROOT / binding["session_registry_path"]
    source_path = ROOT / binding["source_input_registry_path"]
    return {
        "session_registry_exists": session_path.is_file(),
        "session_registry_sha256": session_path.is_file() and compute_sha256(session_path) == binding["session_registry_sha256"],
        "source_registry_exists": source_path.is_file(),
        "source_registry_sha256": source_path.is_file() and compute_sha256(source_path) == binding["source_input_registry_sha256"],
    }


def preflight(spec_path: Path, data_dir: Path, output_dir: Path, expected_commit: str) -> dict[str, Any]:
    _, status_path = validate_kaggle_runtime(data_dir, output_dir / "preflight.json")
    spec = load_json(spec_path)
    validate_spec(spec)
    git = verify_git_clean_and_head(expected_commit)
    repo_checks = _repo_binding_checks(spec)
    binding = spec["binding"]
    bound = _hex64(binding.get("package_manifest_sha256")) and _hex64(binding.get("effective_input_registry_sha256"))
    package = None
    package_error = None
    if bound:
        try:
            _, _, package = verify_package_and_effective_registry(data_dir, spec)
        except Exception as exc:
            package_error = str(exc)
    session_registry = load_json(ROOT / binding["session_registry_path"])
    sessions = expand_sessions(session_registry)
    universe_ok = (
        len(sessions) == 234
        and {row["contract"] for row in sessions} == set(spec["universe"]["contracts"])
        and max(row["cme_session_id"] for row in sessions) <= "20260630"
    )
    ready = all(repo_checks.values()) and bound and package is not None and universe_ok
    result = {
        "schema_version": "bt2a_nq_target_free_preflight_v1",
        "status": "PASS_READY_FOR_FREEZE_OR_EXECUTION" if ready else "NOT_READY",
        "spec_status": spec["status"],
        "spec_file_sha256": sha256_file(spec_path),
        "git": git,
        "repo_bindings": repo_checks,
        "package_bound": bound,
        "package": package,
        "package_error": package_error,
        "n_sessions": len(sessions),
        "universe_ok": universe_ok,
        "heavy_kernel_executed": False,
        "outcomes_accessed": False,
        "future_price_path_accessed": False,
        "holdout_touched": False,
    }
    atomic_write_json(status_path, result)
    return result


def require_execution(spec: dict[str, Any], expected_commit: str, token: str | None) -> None:
    validate_spec(spec)
    verify_runtime_execution_gates(spec, expected_commit, token)


def _contract_filename(contract: str) -> str:
    return contract.replace(" ", "_").replace("/", "_")


def _coordinate_path(output_dir: Path, config: dict[str, Any], contract: str) -> Path:
    return output_dir / "coordinates" / config["config_id"] / f"{_contract_filename(contract)}.parquet"


def _checkpoint_path(output_dir: Path, config: dict[str, Any], contract: str) -> Path:
    return output_dir / "checkpoints" / config["config_id"] / f"{_contract_filename(contract)}.json"


def creation_event_key(contract: str, session: str, direction: int, event_time_ns: int, source_row: int) -> str:
    return canonical_sha256({
        "contract": contract,
        "cme_session_id": session,
        "direction": int(direction),
        "event_time_ns": int(event_time_ns),
        "source_row": int(source_row),
    })


def _resume_valid(checkpoint: Path, coordinate: Path, spec_sha: str, config: dict[str, Any]) -> bool:
    if not checkpoint.is_file() or not coordinate.is_file():
        return False
    try:
        value = load_json(checkpoint)
        return (
            value.get("status") == "COMPLETE_TARGET_FREE_PARTITION"
            and value.get("spec_file_sha256") == spec_sha
            and value.get("params_sha256") == canonical_sha256(config["params"])
            and value.get("coordinate_file_sha256") == sha256_file(coordinate)
        )
    except Exception:
        return False


def run_contract(spec_path: Path, data_dir: Path, output_dir: Path, expected_commit: str,
                 token: str | None, contract: str, resume: bool) -> dict[str, Any]:
    readiness = preflight(spec_path, data_dir, output_dir, expected_commit)
    if readiness["status"] != "PASS_READY_FOR_FREEZE_OR_EXECUTION":
        raise RuntimeError("ABSTAIN_BT2A_NQ_PREFLIGHT_NOT_READY")
    spec = load_json(spec_path)
    require_execution(spec, expected_commit, token)
    if contract not in spec["universe"]["contracts"]:
        raise RuntimeError(f"unknown contract partition: {contract}")
    _, effective, provenance = verify_package_and_effective_registry(data_dir, spec)
    registry = load_json(ROOT / spec["binding"]["session_registry_path"])
    session_rows = [row for row in expand_sessions(registry) if row["contract"] == contract]
    valid_sessions = {row["cme_session_id"] for row in session_rows}
    if not valid_sessions:
        raise RuntimeError("empty contract session partition")
    first_warmup = registry["initial_warmup_session"][contract]
    start_ns = cme_session_to_utc_bounds_ns(first_warmup)[0]
    end_ns = max(cme_session_to_utc_bounds_ns(row["cme_session_id"])[1] for row in session_rows)
    if end_ns > HOLDOUT_NS:
        raise RuntimeError("registered partition reaches holdout")
    entry = effective["contracts"][contract]
    parquet = data_dir / entry["parquet_file"]
    ticks = load_canonical_parquet(
        parquet, contract=contract, instrument="NQ", start_utc_ns=start_ns, end_utc_ns=end_ns
    )
    if len(ticks) == 0 or np.any(np.asarray(ticks.ts_ns, dtype=np.int64) >= HOLDOUT_NS):
        raise RuntimeError("empty partition or holdout tick decoded")
    labels = cme_session_dates(np.asarray(ticks.ts_ns, dtype=np.int64))
    configs = expand_configs(spec)
    grid = expanded_grid(spec)
    atomic_write_json(output_dir / "expanded_grid.json", grid)
    spec_sha = sha256_file(spec_path)
    completed = skipped = 0
    for config in configs:
        coordinate = _coordinate_path(output_dir, config, contract)
        checkpoint = _checkpoint_path(output_dir, config, contract)
        if resume and _resume_valid(checkpoint, coordinate, spec_sha, config):
            skipped += 1
            continue
        result = run_bt2a(ticks, params=config["params"])
        rows = []
        for zone in result.get("zones", []):
            index = int(zone["sig_idx"])
            if index < 0 or index >= len(ticks.ts_ns):
                raise RuntimeError("BT2A creation index outside decoded partition")
            session = str(labels[index])
            if session not in valid_sessions:
                continue
            direction = 1 if str(zone["dir"]) == "long" else -1
            event_time = int(ticks.ts_ns[index])
            source_row = int(ticks.sequence[index])
            rows.append({
                "config_id": config["config_id"],
                "contract": contract,
                "cme_session_id": session,
                "event_time_ns": event_time,
                "source_row": source_row,
                "direction": direction,
                "signal_price_ticks": int(ticks.price_ticks[index]),
                "a_score": float(zone["a_score"]),
                "a_threshold": float(zone["a_thr"]),
                "event_key": creation_event_key(contract, session, direction, event_time, source_row),
            })
        frame = pd.DataFrame(rows, columns=COORDINATE_COLUMNS)
        if len(frame):
            frame = frame.sort_values(
                ["cme_session_id", "event_time_ns", "source_row", "direction", "event_key"], kind="stable"
            )
            if frame["event_key"].duplicated().any():
                raise RuntimeError("duplicate creation event identity")
        coordinate.parent.mkdir(parents=True, exist_ok=True)
        temp = coordinate.with_suffix(".parquet.tmp")
        frame.to_parquet(temp, index=False, compression="zstd")
        os.replace(temp, coordinate)
        body = {
            "schema_version": "bt2a_nq_target_free_partition_v1",
            "status": "COMPLETE_TARGET_FREE_PARTITION",
            "config_id": config["config_id"],
            "contract": contract,
            "spec_file_sha256": spec_sha,
            "params_sha256": canonical_sha256(config["params"]),
            "coordinate_file": coordinate.relative_to(output_dir).as_posix(),
            "coordinate_file_sha256": sha256_file(coordinate),
            "coordinate_file_bytes": coordinate.stat().st_size,
            "n_events": len(frame),
            "n_sessions_with_events": int(frame["cme_session_id"].nunique()) if len(frame) else 0,
            "event_set_sha256": canonical_sha256(frame["event_key"].tolist()),
            "package_provenance": provenance,
            "firewall": {
                "target_free": True, "lifecycle_accessed": False, "future_price_path_accessed": False,
                "first_touch_accessed": False, "first_passage_accessed": False,
                "mfe_mae_accessed": False, "pnl_accessed": False, "holdout_touched": False,
            },
        }
        body["payload_sha256"] = canonical_sha256(body)
        atomic_write_json(checkpoint, body)
        completed += 1
    verify_git_clean_and_head(expected_commit)
    status = {
        "status": "COMPLETE_TARGET_FREE_CONTRACT_PARTITION",
        "contract": contract,
        "configs_completed": completed,
        "configs_resumed": skipped,
        "total_configs": len(configs),
        "outcomes_accessed": False,
        "holdout_touched": False,
    }
    atomic_write_json(output_dir / f"contract_status_{_contract_filename(contract)}.json", status)
    return status


def _jaccard(left: set[str], right: set[str]) -> float:
    union = len(left | right)
    return len(left & right) / union if union else 1.0


def _distance(a: dict[str, Any], b: dict[str, Any], axes: list[str]) -> float:
    return sum(a[name] != b[name] for name in axes) / len(axes)


def rank_summaries(summaries: list[dict[str, Any]], spec: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    eligible = [row for row in summaries if row["eligible"]]
    if not eligible:
        return "ABSTAIN_NO_STABLE_NQ_CONFIGURATION", None
    chosen = sorted(
        eligible,
        key=lambda row: (-row["structural_score"], row["distance_to_gc_anchor"], row["config_id"]),
    )[0]
    return "SELECTED_STABLE_NQ_CONFIGURATION", chosen


def finalize(spec_path: Path, data_dir: Path, output_dir: Path, expected_commit: str,
             token: str | None) -> dict[str, Any]:
    readiness = preflight(spec_path, data_dir, output_dir, expected_commit)
    if readiness["status"] != "PASS_READY_FOR_FREEZE_OR_EXECUTION":
        raise RuntimeError("ABSTAIN_BT2A_NQ_PREFLIGHT_NOT_READY")
    spec = load_json(spec_path)
    require_execution(spec, expected_commit, token)
    configs = expand_configs(spec)
    contracts = list(spec["universe"]["contracts"])
    spec_sha = sha256_file(spec_path)
    event_sets: dict[str, set[str]] = {}
    counters: dict[str, dict[str, Counter]] = {}
    coordinate_files = []
    for config in configs:
        events: set[str] = set()
        contract_counts: Counter = Counter()
        session_counts: Counter = Counter()
        direction_counts: Counter = Counter()
        for contract in contracts:
            coordinate = _coordinate_path(output_dir, config, contract)
            checkpoint = _checkpoint_path(output_dir, config, contract)
            if not _resume_valid(checkpoint, coordinate, spec_sha, config):
                raise RuntimeError(f"missing or stale partition: {config['config_id']} {contract}")
            frame = pd.read_parquet(
                coordinate, columns=["contract", "cme_session_id", "direction", "event_key"]
            )
            if len(frame) and (set(frame["contract"]) != {contract} or frame["event_key"].duplicated().any()):
                raise RuntimeError("coordinate partition identity failure")
            keys = set(map(str, frame["event_key"].tolist()))
            if events & keys:
                raise RuntimeError("duplicate event across contract partitions")
            events |= keys
            contract_counts.update(map(str, frame["contract"].tolist()))
            session_counts.update(f"{contract}|{session}" for session in frame["cme_session_id"].tolist())
            direction_counts.update(map(int, frame["direction"].tolist()))
            coordinate_files.append({
                "config_id": config["config_id"], "contract": contract,
                "path": coordinate.relative_to(output_dir).as_posix(),
                "bytes": coordinate.stat().st_size, "sha256": sha256_file(coordinate),
            })
        event_sets[config["config_id"]] = events
        counters[config["config_id"]] = {
            "contracts": contract_counts, "sessions": session_counts, "directions": direction_counts,
        }
    axes = list(spec["candidate_levels"])
    by_id = {config["config_id"]: config for config in configs}
    k = int(spec["eligibility"]["minimum_nearest_neighbors"])
    summaries = []
    for config in configs:
        cid = config["config_id"]
        events = event_sets[cid]
        counts = counters[cid]
        n = len(events)
        contract_values = list(counts["contracts"].values())
        shares = [value / n for value in contract_values] if n else []
        hhi = sum(value * value for value in shares) if shares else 1.0
        session_values = list(counts["sessions"].values())
        maximum_session_share = max(session_values) / n if session_values and n else 1.0
        neighbors = sorted(
            (other for other in configs if other["config_id"] != cid),
            key=lambda other: (_distance(config["params"], other["params"], axes), other["config_id"]),
        )[:k]
        jaccards = [_jaccard(events, event_sets[row["config_id"]]) for row in neighbors]
        count_stability = [
            max(0.0, 1.0 - abs(math.log((n + 1) / (len(event_sets[row["config_id"]]) + 1))) / math.log(10.0))
            for row in neighbors
        ]
        median_jaccard = statistics.median(jaccards) if jaccards else 0.0
        median_count_stability = statistics.median(count_stability) if count_stability else 0.0
        coverage = len(counts["sessions"]) / int(spec["universe"]["contract_sessions"])
        rules = spec["eligibility"]
        is_eligible = (
            n >= int(rules["minimum_events"])
            and len(counts["sessions"]) >= int(rules["minimum_sessions_with_events"])
            and len(counts["contracts"]) >= int(rules["minimum_contracts_with_events"])
            and hhi <= float(rules["maximum_contract_hhi"])
            and maximum_session_share <= float(rules["maximum_single_session_share"])
            and median_jaccard >= float(rules["minimum_neighbor_median_exact_jaccard"])
        )
        score = 0.45 * median_jaccard + 0.25 * coverage + 0.20 * (1.0 - hhi) + 0.10 * median_count_stability
        long_count = counts["directions"].get(1, 0)
        short_count = counts["directions"].get(-1, 0)
        summaries.append({
            "config_id": cid,
            "stage": config["stage"],
            "axis": config["axis"],
            "params": config["params"],
            "n_events": n,
            "n_sessions_with_events": len(counts["sessions"]),
            "n_contracts_with_events": len(counts["contracts"]),
            "session_coverage": coverage,
            "contract_hhi": hhi,
            "maximum_session_share": maximum_session_share,
            "direction_balance": (2.0 * min(long_count, short_count) / n) if n else 0.0,
            "neighbor_ids": [row["config_id"] for row in neighbors],
            "neighbor_median_exact_jaccard": median_jaccard,
            "neighbor_count_ratio_stability": median_count_stability,
            "distance_to_gc_anchor": _distance(config["params"], _full_params(spec), axes),
            "structural_score": score,
            "eligible": is_eligible,
            "event_set_sha256": canonical_sha256(sorted(events)),
        })
    classification, selected = rank_summaries(summaries, spec)
    coordinate_manifest = {
        "schema_version": "bt2a_nq_coordinate_manifest_v1",
        "spec_file_sha256": spec_sha,
        "n_files": len(coordinate_files),
        "files": sorted(coordinate_files, key=lambda row: (row["config_id"], row["contract"])),
        "target_free": True,
        "holdout_touched": False,
    }
    coordinate_manifest["payload_sha256"] = canonical_sha256(coordinate_manifest)
    coordinate_manifest_sha = atomic_write_json(output_dir / "coordinate_manifest.json", coordinate_manifest)
    selected_value = None
    if selected is not None:
        selected_value = {
            "schema_version": "bt2a_nq_selected_configuration_v1",
            "status": classification,
            "config_id": selected["config_id"],
            "params": selected["params"],
            "structural_metrics": {key: value for key, value in selected.items() if key not in {"params"}},
            "spec_file_sha256": spec_sha,
            "coordinate_manifest_file_sha256": coordinate_manifest_sha,
            "target_free": True,
        }
        selected_value["payload_sha256"] = canonical_sha256(selected_value)
        atomic_write_json(output_dir / "selected_configuration.json", selected_value)
    result = {
        "schema_version": "bt2a_nq_target_free_selection_result_v1",
        "status": classification,
        "spec_file_sha256": spec_sha,
        "frozen_commit": expected_commit,
        "n_configurations": len(configs),
        "n_eligible_configurations": sum(row["eligible"] for row in summaries),
        "selected_config_id": selected["config_id"] if selected else None,
        "coordinate_manifest_file_sha256": coordinate_manifest_sha,
        "summaries": sorted(summaries, key=lambda row: row["config_id"]),
        "firewall": {
            "target_free": True, "lifecycle_accessed": False, "future_price_path_accessed": False,
            "first_touch_accessed": False, "first_passage_accessed": False,
            "mfe_mae_accessed": False, "returns_accessed": False, "pnl_accessed": False,
            "holdout_rows_decoded": False, "holdout_touched": False,
            "economic_winner_selected": False, "edge_declared": False,
        },
    }
    result["payload_sha256"] = canonical_sha256(result)
    result_sha = atomic_write_json(output_dir / "selection_result.json", result)
    attestation = {
        "schema_version": "bt2a_nq_target_free_execution_attestation_v1",
        "result_file_sha256": result_sha,
        "coordinate_manifest_file_sha256": coordinate_manifest_sha,
        "future_price_path_accessed": False,
        "first_touch_accessed": False,
        "pnl_accessed": False,
        "holdout_rows_decoded": False,
        "holdout_touched": False,
    }
    atomic_write_json(output_dir / "execution_attestation.json", attestation)
    verify_git_clean_and_head(expected_commit)
    return result


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__)
    out.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    out.add_argument("--data-dir", type=Path)
    out.add_argument("--output-dir", type=Path, required=True)
    out.add_argument("--expected-commit")
    out.add_argument("--execution-token")
    mode = out.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan-only", action="store_true")
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--contract", choices=["NQ 09-25", "NQ 12-25", "NQ 03-26", "NQ 06-26", "NQ 09-26"])
    mode.add_argument("--finalize", action="store_true")
    out.add_argument("--resume", action="store_true")
    return out


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    spec = load_json(args.spec)
    validate_spec(spec)
    if args.plan_only:
        value = expanded_grid(spec)
        atomic_write_json(args.output_dir / "expanded_grid.json", value)
        print(json.dumps({"status": "PLAN_TARGET_FREE", "n_configurations": value["n_configurations"]}, indent=2))
        return 0
    if args.data_dir is None or not args.expected_commit:
        raise SystemExit("--data-dir and --expected-commit are required outside --plan-only")
    token = args.execution_token or os.environ.get("EDGELAB_AUTHORIZATION_TOKEN")
    if args.preflight_only:
        result = preflight(args.spec, args.data_dir, args.output_dir, args.expected_commit)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"].startswith("PASS") else 2
    if args.contract:
        result = run_contract(args.spec, args.data_dir, args.output_dir, args.expected_commit, token, args.contract, args.resume)
    else:
        result = finalize(args.spec, args.data_dir, args.output_dir, args.expected_commit, token)
    print(json.dumps({key: value for key, value in result.items() if key != "summaries"}, indent=2, sort_keys=True))
    return 0 if str(result["status"]).startswith(("COMPLETE", "SELECTED")) else 3


if __name__ == "__main__":
    raise SystemExit(main())
