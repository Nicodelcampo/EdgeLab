#!/usr/bin/env python3
"""Preflight or execute one frozen EdgeLab campaign in Kaggle/cloud."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.kaggle.execution import (
    KaggleContractError,
    atomic_write_json,
    build_artifact_manifest,
    deterministic_zip,
    git_state,
    load_execution_spec,
    load_json,
    render_argv,
    require_authorized,
    resource_snapshot,
    sha256_file,
    verify_package_manifest,
)

ATTESTATION_FIELDS = (
    "future_price_path_accessed",
    "first_touch_accessed",
    "pnl_accessed",
    "holdout_touched",
)


def validate_attestation(path: Path, authorizations: dict) -> dict:
    attestation = load_json(path)
    for field in ATTESTATION_FIELDS:
        if not isinstance(attestation.get(field), bool):
            raise KaggleContractError(f"firewall attestation requires boolean {field}")
    auth_map = {
        "future_price_path_accessed": "future_price_path_authorized",
        "first_touch_accessed": "first_touch_authorized",
        "pnl_accessed": "pnl_authorized",
        "holdout_touched": "holdout_authorized",
    }
    breaches = [
        field
        for field, auth_field in auth_map.items()
        if attestation[field] and authorizations.get(auth_field) is not True
    ]
    return {"values": attestation, "breaches": breaches, "sha256": sha256_file(path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--authorization-token")
    parser.add_argument("--archive", type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight-only", action="store_true")
    modes.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    execution_started = False
    package_verified = False
    try:
        spec = load_execution_spec(args.spec)
        outputs_cfg = spec.get("outputs") or {}
        required_paths = outputs_cfg.get("required_paths")
        attestation_relative = outputs_cfg.get("firewall_attestation_path")
        if not isinstance(required_paths, list) or not all(
            isinstance(x, str) and x for x in required_paths
        ):
            raise KaggleContractError("outputs.required_paths must be a string array")
        if (
            not isinstance(attestation_relative, str)
            or not attestation_relative
            or attestation_relative not in required_paths
        ):
            raise KaggleContractError(
                "firewall_attestation_path must be declared and required"
            )
        state_start = git_state(REPO_ROOT)
        package_cfg = spec["input_package"]
        manifest_path = args.data_dir / package_cfg["manifest_file"]
        package = verify_package_manifest(
            manifest_path,
            args.data_dir,
            expected_file_sha256=package_cfg.get("manifest_sha256")
            if spec["status"] == "FROZEN_PREFLIGHT_READY"
            else None,
            holdout_open_utc_ns=package_cfg["holdout_open_utc_ns"],
        )
        package_verified = True
        base = {
            "schema_version": "edgelab_kaggle_job_status_v1",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "campaign_id": spec["campaign_id"],
            "spec_file_sha256": sha256_file(args.spec),
            "git_state_start": state_start,
            "resource_snapshot": resource_snapshot(),
            "input_verification": package,
            "firewall_authorizations": spec["firewalls"],
        }
        if args.preflight_only:
            result = {
                **base,
                "status": "KAGGLE_PREFLIGHT_PASS"
                if spec["status"] == "FROZEN_PREFLIGHT_READY"
                else "KAGGLE_DRAFT_PREFLIGHT",
                "run_capability": bool(spec["authorization"]["run_capability"]),
                "execution_started": False,
                "future_price_path_accessed": False,
                "first_touch_accessed": False,
                "pnl_accessed": False,
                "holdout_touched": False,
            }
            atomic_write_json(args.output_dir / "preflight.json", result)
            print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
            return 0

        require_authorized(
            spec,
            authorization_token=args.authorization_token,
            expected_commit=args.expected_commit,
            state=state_start,
        )
        job_dir = args.output_dir / "job"
        job_dir.mkdir(parents=True, exist_ok=True)
        command = render_argv(
            spec["execution"]["argv"],
            {
                "data_dir": str(args.data_dir.resolve()),
                "output_dir": str(job_dir.resolve()),
                "expected_commit": args.expected_commit,
            },
        )
        env = os.environ.copy()
        max_workers = int(spec["execution"]["parallelism"]["max_workers"])
        env["EDGELAB_MAX_WORKERS"] = str(max_workers)
        for key, value in (spec["execution"].get("thread_env") or {}).items():
            env[str(key)] = str(value)
        env["EDGELAB_AUTHORIZATION_TOKEN"] = args.authorization_token or ""
        stdout_path = args.output_dir / "job.stdout.log"
        stderr_path = args.output_dir / "job.stderr.log"
        started = datetime.now(timezone.utc).isoformat()
        execution_started = True
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr:
            proc = subprocess.run(
                command,
                cwd=REPO_ROOT,
                env=env,
                stdout=stdout,
                stderr=stderr,
                shell=False,
                timeout=int(spec["execution"]["timeout_seconds"]),
                check=False,
            )
        ended = datetime.now(timezone.utc).isoformat()
        state_end = git_state(REPO_ROOT)
        if state_end["commit"] != state_start["commit"] or state_end["dirty"]:
            raise KaggleContractError("code identity changed during execution")

        missing = []
        for relative in required_paths:
            path = (job_dir / relative).resolve()
            if not path.is_relative_to(job_dir.resolve()) or not path.is_file():
                missing.append(relative)
        attestation = None
        attestation_error = None
        if attestation_relative not in missing:
            try:
                attestation = validate_attestation(
                    job_dir / attestation_relative, spec["firewalls"]
                )
            except KaggleContractError as exc:
                attestation_error = str(exc)

        status = "COMPLETE_KAGGLE_FROZEN_JOB"
        if proc.returncode != 0:
            status = "ABSTAIN_KAGGLE_JOB_FAILED"
        elif missing or attestation_error:
            status = "ABSTAIN_KAGGLE_OUTPUT_INCOMPLETE"
        elif attestation and attestation["breaches"]:
            status = "ABSTAIN_KAGGLE_FIREWALL_BREACH"

        actual = attestation["values"] if attestation else {
            field: None for field in ATTESTATION_FIELDS
        }
        run_status = {
            **base,
            **actual,
            "status": status,
            "execution_started": True,
            "started_utc": started,
            "ended_utc": ended,
            "argv": command,
            "shell": False,
            "max_workers": max_workers,
            "process_returncode": proc.returncode,
            "missing_required_outputs": missing,
            "firewall_attestation_error": attestation_error,
            "firewall_breaches": attestation["breaches"] if attestation else [],
            "firewall_attestation_sha256": attestation["sha256"] if attestation else None,
            "git_state_end": state_end,
        }
        atomic_write_json(args.output_dir / "run_status.json", run_status)
        artifact_manifest = build_artifact_manifest(
            args.output_dir,
            {
                "campaign_id": spec["campaign_id"],
                "head_start": state_start["commit"],
                "head_end": state_end["commit"],
                "code_dirty": state_end["dirty"],
                "spec_file_sha256": base["spec_file_sha256"],
                "input_package_manifest_sha256": package["manifest_file_sha256"],
            },
        )
        archive = args.archive or Path(outputs_cfg["archive_path"])
        zip_result = deterministic_zip(args.output_dir, archive)
        summary = {
            "status": status,
            "artifact_manifest_payload_sha256": artifact_manifest["payload_sha256"],
            "archive": zip_result,
        }
        print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
        return 0 if status == "COMPLETE_KAGGLE_FROZEN_JOB" else 2
    except (KaggleContractError, subprocess.TimeoutExpired) as exc:
        label = getattr(exc, "label", "ABSTAIN_KAGGLE_TIMEOUT")
        unknown = None if execution_started else False
        error = {
            "schema_version": "edgelab_kaggle_job_status_v1",
            "status": label,
            "message": str(exc),
            "execution_started": execution_started,
            "execution_complete": False,
            "input_package_verified": package_verified,
            "future_price_path_accessed": unknown,
            "first_touch_accessed": unknown,
            "pnl_accessed": unknown,
            "holdout_touched": False if package_verified else unknown,
        }
        atomic_write_json(args.output_dir / "error.json", error)
        print(json.dumps(error, indent=2, sort_keys=True, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
