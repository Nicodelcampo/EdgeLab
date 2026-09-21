#!/usr/bin/env python3
"""Fail-closed, target-free Kaggle access probe result classifier.

This module never reads credential values. It classifies sanitized HTTP/network
observations and emits a RUN-LEARNING-PACKET suitable for review and ingestion.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FORBIDDEN_OUTPUT_KEYS = {"token", "api_token", "api_key", "authorization", "kaggle_api_token"}


@dataclass(frozen=True)
class ProbeObservation:
    status: int | None
    json_shape_valid: bool
    network_error: str | None = None


def classify(observation: ProbeObservation) -> tuple[str, bool]:
    if observation.network_error:
        return "ABSTAIN_NETWORK", False
    if observation.status == 200 and observation.json_shape_valid:
        return "AUTHENTICATED_ENDPOINT_ONLY", True
    if observation.status == 200:
        return "ABSTAIN_RESPONSE_SHAPE", False
    if observation.status in {400, 401, 403}:
        return "ABSTAIN_AUTH_OR_ENDPOINT", False
    return "ABSTAIN_UNCLASSIFIED", False


def assert_redacted(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_OUTPUT_KEYS:
                raise ValueError(f"forbidden secret-bearing output key: {key}")
            assert_redacted(child)
    elif isinstance(value, list):
        for child in value:
            assert_redacted(child)


def learning_packet(observation: ProbeObservation, run_id: str) -> dict[str, Any]:
    verdict, connected = classify(observation)
    packet = {
        "packet_type": "RUN-LEARNING-PACKET",
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "work_id": "CYCLE-001-C-KAGGLE-ACCESS-001",
        "construct_id": "KAGGLE-ACCESS-CERTIFICATION-V1",
        "observation": asdict(observation),
        "verdict": verdict,
        "connected": connected,
        "dataset_verified": False,
        "hashes_verified": False,
        "outcomes_inspected": False,
        "holdout_enabled": False,
        "preexisting_outcome_exposure": True,
        "holdout_contaminated_for_this_hypothesis": True,
        "promotion_ceiling": "LESSON_CANDIDATE",
        "next_action": "independent endpoint/auth review by Agent D",
    }
    assert_redacted(packet)
    return packet


def self_test() -> None:
    cases = [
        (ProbeObservation(200, True), "AUTHENTICATED_ENDPOINT_ONLY", True),
        (ProbeObservation(200, False), "ABSTAIN_RESPONSE_SHAPE", False),
        (ProbeObservation(400, False), "ABSTAIN_AUTH_OR_ENDPOINT", False),
        (ProbeObservation(401, False), "ABSTAIN_AUTH_OR_ENDPOINT", False),
        (ProbeObservation(403, False), "ABSTAIN_AUTH_OR_ENDPOINT", False),
        (ProbeObservation(None, False, "timeout"), "ABSTAIN_NETWORK", False),
        (ProbeObservation(500, False), "ABSTAIN_UNCLASSIFIED", False),
    ]
    for index, (observation, expected_verdict, expected_connected) in enumerate(cases):
        packet = learning_packet(observation, f"SELFTEST-{index}")
        assert packet["verdict"] == expected_verdict
        assert packet["connected"] is expected_connected
        assert packet["dataset_verified"] is False
        assert packet["holdout_enabled"] is False
    try:
        assert_redacted({"authorization": "secret"})
    except ValueError:
        pass
    else:
        raise AssertionError("secret-bearing key was not rejected")
    print(f"PASS: {len(cases)} status cases + secret-key rejection")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--status", type=int)
    parser.add_argument("--json-shape-valid", action="store_true")
    parser.add_argument("--network-error")
    parser.add_argument("--run-id", default="manual")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    packet = learning_packet(
        ProbeObservation(args.status, args.json_shape_valid, args.network_error),
        args.run_id,
    )
    rendered = json.dumps(packet, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
