#!/usr/bin/env python3
"""Fail-closed, target-free Kaggle access observation classifier.

Credential values and raw exception text are never persisted. A nominal HTTP
200 authenticates only when this module validates a sanitized payload against a
known endpoint schema; caller-supplied booleans are legacy, untrusted input.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DENIED_KEY_FAMILIES = (
    "authorization",
    "token",
    "apikey",
    "password",
    "secret",
    "cookie",
    "credential",
)
SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(authorization\s*:|bearer\s+\S+|(?:api[_\- ]?key|token|password|secret|credential)\s*[=:])"
)
ALLOWED_ENDPOINTS = {"kaggle.datasets.list.v1"}
ALLOWED_NETWORK_ERRORS = {"timeout", "dns", "tls", "connection", "http_client"}


@dataclass(frozen=True)
class ProbeObservation:
    status: int | None
    json_shape_valid: bool | None = None  # Legacy caller assertion; never authoritative.
    network_error: str | None = None
    endpoint_id: str | None = None
    response_payload: Any = None


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.strip().lower())


def assert_redacted(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = _normalize_key(str(key))
            if any(family in normalized for family in DENIED_KEY_FAMILIES):
                raise ValueError(f"forbidden secret-bearing output key: {key}")
            assert_redacted(child)
    elif isinstance(value, list):
        for child in value:
            assert_redacted(child)
    elif isinstance(value, str) and SECRET_VALUE_PATTERN.search(value):
        raise ValueError("forbidden secret-bearing output value")


def validate_response_shape(endpoint_id: str | None, payload: Any) -> bool:
    if endpoint_id not in ALLOWED_ENDPOINTS:
        return False
    if endpoint_id == "kaggle.datasets.list.v1":
        if not isinstance(payload, list):
            return False
        return all(
            isinstance(item, dict)
            and isinstance(item.get("ref"), str)
            and isinstance(item.get("title"), str)
            for item in payload
        )
    return False


def _network_error_class(raw_error: str | None) -> str | None:
    if raw_error is None:
        return None
    assert_redacted(raw_error)
    normalized = raw_error.strip().lower()
    if normalized in ALLOWED_NETWORK_ERRORS:
        return normalized
    if "timeout" in normalized:
        return "timeout"
    if "dns" in normalized:
        return "dns"
    if "tls" in normalized or "certificate" in normalized:
        return "tls"
    if "connect" in normalized:
        return "connection"
    return "http_client"


def classify(observation: ProbeObservation) -> tuple[str, bool]:
    if observation.network_error:
        _network_error_class(observation.network_error)
        return "ABSTAIN_NETWORK", False
    shape_valid = validate_response_shape(
        observation.endpoint_id, observation.response_payload
    )
    if observation.status == 200 and shape_valid:
        return "AUTHENTICATED_ENDPOINT_ONLY", True
    if observation.status == 200:
        return "ABSTAIN_RESPONSE_SHAPE_UNVERIFIED", False
    if observation.status in {400, 401, 403}:
        return "ABSTAIN_AUTH_OR_ENDPOINT", False
    return "ABSTAIN_UNCLASSIFIED", False


def learning_packet(observation: ProbeObservation, run_id: str) -> dict[str, Any]:
    if not run_id.strip():
        raise ValueError("run_id must be non-empty")
    assert_redacted(observation.response_payload)
    network_error_class = _network_error_class(observation.network_error)
    verdict, connected = classify(observation)
    shape_valid = validate_response_shape(
        observation.endpoint_id, observation.response_payload
    )
    packet = {
        "packet_type": "RUN-LEARNING-PACKET",
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "work_id": "CYCLE-001-C-KAGGLE-ACCESS-001",
        "construct_id": "KAGGLE-ACCESS-CERTIFICATION-V1",
        "observation": {
            "status": observation.status,
            "endpoint_id": observation.endpoint_id,
            "response_shape_validated_internally": shape_valid,
            "network_error_class": network_error_class,
        },
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
    valid_payload = [{"ref": "owner/dataset", "title": "Dataset"}]
    cases = [
        (
            ProbeObservation(200, endpoint_id="kaggle.datasets.list.v1", response_payload=valid_payload),
            "AUTHENTICATED_ENDPOINT_ONLY",
            True,
        ),
        (ProbeObservation(200, True), "ABSTAIN_RESPONSE_SHAPE_UNVERIFIED", False),
        (ProbeObservation(200, endpoint_id="unknown", response_payload=[]), "ABSTAIN_RESPONSE_SHAPE_UNVERIFIED", False),
        (ProbeObservation(400), "ABSTAIN_AUTH_OR_ENDPOINT", False),
        (ProbeObservation(401), "ABSTAIN_AUTH_OR_ENDPOINT", False),
        (ProbeObservation(403), "ABSTAIN_AUTH_OR_ENDPOINT", False),
        (ProbeObservation(None, network_error="timeout"), "ABSTAIN_NETWORK", False),
        (ProbeObservation(500), "ABSTAIN_UNCLASSIFIED", False),
    ]
    for index, (observation, expected_verdict, expected_connected) in enumerate(cases):
        packet = learning_packet(observation, f"SELFTEST-{index}")
        assert packet["verdict"] == expected_verdict
        assert packet["connected"] is expected_connected
        assert packet["dataset_verified"] is False
        assert packet["holdout_enabled"] is False
    for key in ("Authorization ", "api-key", "Kaggle-Api-Token", "session_cookie"):
        try:
            assert_redacted({key: "redacted"})
        except ValueError:
            pass
        else:
            raise AssertionError(f"secret-bearing key was not rejected: {key}")
    try:
        learning_packet(ProbeObservation(None, network_error="Authorization: Bearer REDACT_ME"), "SECRET")
    except ValueError:
        pass
    else:
        raise AssertionError("secret-bearing network error was not rejected")
    print(f"PASS: {len(cases)} status cases + normalized secret redaction")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--status", type=int)
    parser.add_argument("--json-shape-valid", action="store_true", help="legacy untrusted input")
    parser.add_argument("--endpoint-id")
    parser.add_argument("--response-json")
    parser.add_argument("--network-error")
    parser.add_argument("--run-id", default="manual")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    payload = json.loads(args.response_json) if args.response_json else None
    packet = learning_packet(
        ProbeObservation(
            status=args.status,
            json_shape_valid=args.json_shape_valid,
            network_error=args.network_error,
            endpoint_id=args.endpoint_id,
            response_payload=payload,
        ),
        args.run_id,
    )
    rendered = json.dumps(packet, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
