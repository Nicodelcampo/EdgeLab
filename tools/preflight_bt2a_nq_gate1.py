#!/usr/bin/env python3
"""Target-free readiness preflight for BT2A NQ Gate 1.

This module deliberately has no outcome execution mode and never imports the
Gate 1 outcome engine. It verifies that the package, selected BT2A Event Store,
BigTrap2 comparator, macro calendar and power inputs are all frozen before a
separate runner may be implemented or authorized.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(ROOT))

from edgelab.kaggle.execution import atomic_write_json, load_json, sha256_file, verify_package_manifest
from tools.build_bt2a_nq_creation_event_store import validate_store
from tools.sweep_bigtrap2_nq_tickframes_v2 import validate_kaggle_runtime, verify_git_clean_and_head
from tools.bt2a_nq_gate1_contracts import (
    load_json as load_contract_json, power_missing, validate_macro_policy, validate_runner_contract,
)

DEFAULT_SPEC = ROOT / "specs" / "bt2a_nq_gate1_v1.draft.json"
INPUT_ROOT = Path("/kaggle/input")


def _hex64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _safe_input_dir(path: Path, input_root: Path = INPUT_ROOT) -> Path:
    root = input_root.resolve()
    resolved = path.resolve()
    if not root.is_dir() or not resolved.is_dir() or not resolved.is_relative_to(root):
        raise RuntimeError(f"input directory must be below {input_root}")
    return resolved


def validate_spec(spec: dict[str, Any]) -> None:
    if spec.get("schema_version") != "bt2a_nq_gate1_v1":
        raise RuntimeError("unexpected BT2A NQ Gate 1 schema")
    if spec.get("status") not in {"DRAFT_DESIGN_ONLY_PREAUTHORIZATION", "FROZEN_PREFLIGHT_READY"}:
        raise RuntimeError("invalid Gate 1 status")
    if spec.get("execution_platform") != "KAGGLE_ONLY":
        raise RuntimeError("Gate 1 must remain Kaggle-only")
    universe = spec.get("universe") or {}
    if universe.get("instrument") != "NQ" or int(universe.get("contract_sessions", -1)) != 234:
        raise RuntimeError("unexpected Gate 1 universe")
    if len(universe.get("contracts") or []) != 5 or int(universe.get("holdout_open_utc_ns", -1)) != 1782856800000000000:
        raise RuntimeError("Gate 1 contract or holdout mismatch")
    family = spec.get("outcome_family") or {}
    barriers = family.get("first_passage_barriers_ticks") or []
    horizons = family.get("first_passage_horizons_observations") or []
    if barriers != [5, 9, 18, 30] or horizons != [25, 50, 100, 250]:
        raise RuntimeError("Gate 1 family drift")
    if int(family.get("family_size", -1)) != 16 or family.get("evaluate_full_family") is not True:
        raise RuntimeError("Gate 1 full family is not frozen")
    if family.get("gc_results_may_reduce_nq_family") is not False:
        raise RuntimeError("GC results cannot reduce the NQ family")
    if spec.get("arms", {}).get("comparators") != ["K_BT2", "N_RAND", "K_ABS_SHUFFLE"]:
        raise RuntimeError("Gate 1 comparator family drift")
    inference = spec.get("inference") or {}
    if inference.get("cluster_unit") != "CME_SESSION" or inference.get("minimum_event_count_alone_is_power_proof") is not False:
        raise RuntimeError("Gate 1 inference contract drift")
    firewall = spec.get("firewall") or {}
    if any(firewall.get(name) is not False for name in (
        "GATE1_RUN", "OUTCOMES_ACCESSED", "FUTURE_PRICE_PATH_ACCESSED",
        "FIRST_PASSAGE_ACCESSED", "MFE_MAE_ACCESSED", "PNL_ACCESSED",
        "HOLDOUT_TOUCHED", "WINNER_SELECTED", "EDGE_DECLARED", "PROMOTION_ELIGIBLE",
    )):
        raise RuntimeError("Gate 1 firewall is open")
    auth = spec.get("authorization") or {}
    if spec["status"].startswith("DRAFT") and (
        auth.get("execution_authorized") is not False or auth.get("active_token") is not None
    ):
        raise RuntimeError("draft Gate 1 cannot carry execution capability")


def missing_bindings(spec: dict[str, Any]) -> list[str]:
    deps = spec["dependencies"]
    missing = []
    for name in (
        "selected_configuration_file_sha256",
        "bt2a_creation_event_store_manifest_sha256",
        "private_package_manifest_sha256",
        "effective_input_registry_sha256",
        "bt2_v2_result_file_sha256",
        "macro_calendar_sha256",
        "power_design_file_sha256",
        "runner_contract_file_sha256",
    ):
        if not _hex64(deps.get(name)):
            missing.append(name)
    for name in ("bt2_comparator_config_id", "macro_calendar_file", "power_design_file", "runner_contract_file"):
        if not isinstance(deps.get(name), str) or not deps[name]:
            missing.append(name)
    power = spec["power_design"]
    mde = power.get("mde_ticks")
    icc = power.get("icc")
    sessions = power.get("effective_sessions_required")
    if not isinstance(mde, (int, float)) or mde <= 0:
        missing.append("power_design.mde_ticks")
    if not isinstance(icc, (int, float)) or not 0 <= icc < 1:
        missing.append("power_design.icc")
    if not isinstance(sessions, int) or sessions < int(spec["inference"]["minimum_effective_sessions"]):
        missing.append("power_design.effective_sessions_required")
    deps = spec["dependencies"]
    power_file = deps.get("power_design_file")
    if isinstance(power_file, str) and _hex64(deps.get("power_design_file_sha256")):
        try:
            path = _verify_file(ROOT, power_file, deps["power_design_file_sha256"])
            missing.extend(power_missing(load_contract_json(path), require_frozen=True))
        except Exception:
            missing.append("power_design.contract_invalid")
    runner_file = deps.get("runner_contract_file")
    if isinstance(runner_file, str) and _hex64(deps.get("runner_contract_file_sha256")):
        try:
            path = _verify_file(ROOT, runner_file, deps["runner_contract_file_sha256"])
            missing.extend(validate_runner_contract(load_contract_json(path)))
        except Exception:
            missing.append("runner_contract.invalid")
    return sorted(set(missing))


def _verify_file(root: Path, name: str, expected: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file() or path.is_symlink():
        raise RuntimeError(f"missing or unsafe input artifact: {name}")
    if sha256_file(path) != expected:
        raise RuntimeError(f"input artifact SHA-256 mismatch: {name}")
    return path


def preflight(spec_path: Path, data_dir: Path, event_store_dir: Path, bt2_dir: Path,
              output_dir: Path, expected_commit: str) -> dict[str, Any]:
    validate_kaggle_runtime(data_dir, output_dir / "bt2a_nq_gate1_preflight.json")
    event_store_dir = _safe_input_dir(event_store_dir)
    bt2_dir = _safe_input_dir(bt2_dir)
    spec = load_json(spec_path)
    validate_spec(spec)
    git = verify_git_clean_and_head(expected_commit)
    missing = missing_bindings(spec)
    evidence = {}
    errors = []
    if not missing:
        deps = spec["dependencies"]
        try:
            manifest_path = _verify_file(
                data_dir, deps["private_package_manifest_file"], deps["private_package_manifest_sha256"]
            )
            evidence["package"] = verify_package_manifest(
                manifest_path, data_dir, expected_file_sha256=deps["private_package_manifest_sha256"]
            )
            _verify_file(data_dir, deps["effective_input_registry_file"], deps["effective_input_registry_sha256"])
        except Exception as exc:
            errors.append(f"package: {exc}")
        try:
            store_manifest = _verify_file(
                event_store_dir,
                deps["bt2a_creation_event_store_manifest_file"],
                deps["bt2a_creation_event_store_manifest_sha256"],
            )
            evidence["event_store"] = validate_store(event_store_dir, store_manifest.name)
            if evidence["event_store"]["manifest_file_sha256"] != deps["bt2a_creation_event_store_manifest_sha256"]:
                raise RuntimeError("Event Store manifest binding mismatch")
        except Exception as exc:
            errors.append(f"event_store: {exc}")
        try:
            bt2_path = _verify_file(bt2_dir, deps["bt2_v2_result_file"], deps["bt2_v2_result_file_sha256"])
            bt2 = load_json(bt2_path)
            ids = {row.get("cfg_id") for row in bt2.get("results", [])}
            if deps["bt2_comparator_config_id"] not in ids:
                raise RuntimeError("frozen K_BT2 comparator absent from V2 result")
            evidence["bt2_comparator_config_id"] = deps["bt2_comparator_config_id"]
        except Exception as exc:
            errors.append(f"bt2: {exc}")
        try:
            macro = _verify_file(ROOT, deps["macro_calendar_file"], deps["macro_calendar_sha256"])
            macro_missing = validate_macro_policy(load_contract_json(macro), require_frozen=True)
            if macro_missing:
                raise RuntimeError("macro policy is not frozen")
            evidence["macro_calendar_file_sha256"] = sha256_file(macro)
        except Exception as exc:
            errors.append(f"macro: {exc}")
    ready = not missing and not errors and len(evidence) == 4
    result = {
        "schema_version": "bt2a_nq_gate1_preflight_v1",
        "status": "PASS_READY_FOR_GATE1_FREEZE" if ready else "NOT_READY",
        "spec_file_sha256": sha256_file(spec_path),
        "spec_status": spec["status"],
        "git": git,
        "missing_bindings": missing,
        "errors": errors,
        "evidence": evidence,
        "GATE1_RUN": False,
        "OUTCOMES_ACCESSED": False,
        "FUTURE_PRICE_PATH_ACCESSED": False,
        "FIRST_PASSAGE_ACCESSED": False,
        "MFE_MAE_ACCESSED": False,
        "PNL_ACCESSED": False,
        "HOLDOUT_TOUCHED": False,
    }
    atomic_write_json(output_dir / "bt2a_nq_gate1_preflight.json", result)
    return result


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__)
    out.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    out.add_argument("--data-dir", type=Path)
    out.add_argument("--event-store-dir", type=Path)
    out.add_argument("--bt2-artifact-dir", type=Path)
    out.add_argument("--output-dir", type=Path, required=True)
    out.add_argument("--expected-commit")
    mode = out.add_mutually_exclusive_group(required=True)
    mode.add_argument("--contract-only", action="store_true")
    mode.add_argument("--preflight-only", action="store_true")
    return out


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    spec = load_json(args.spec)
    validate_spec(spec)
    if args.contract_only:
        result = {
            "status": "PASS_GATE1_DRAFT_CONTRACT",
            "missing_bindings": missing_bindings(spec),
            "GATE1_RUN": False,
            "OUTCOMES_ACCESSED": False,
        }
    else:
        if any(value is None for value in (
            args.data_dir, args.event_store_dir, args.bt2_artifact_dir, args.expected_commit
        )):
            raise SystemExit("all input directories and --expected-commit are required")
        result = preflight(
            args.spec, args.data_dir, args.event_store_dir, args.bt2_artifact_dir,
            args.output_dir, args.expected_commit,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if str(result["status"]).startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
