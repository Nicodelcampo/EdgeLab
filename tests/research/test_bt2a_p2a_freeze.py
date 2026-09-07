from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from edgelab.research.bt2a_event_store import canonical_sha256
from edgelab.research.bt2a_p2a_freeze import (
    classify_mechanism,
    validate_canonical_event_store,
    validate_p2a_session_checkpoint,
)


def decision_spec():
    return {
        "p2a": {"barriers_ticks": [5, 9, 18, 30], "primary_horizons_ticks": [25, 50, 100, 250]},
        "decision_rule": {"primary_contrast": "K_ABS_MINUS_N_RAND", "familywise_alpha": 0.05},
    }


def family(overrides=None):
    overrides = overrides or {}
    rows = []
    for barrier in (5, 9, 18, 30):
        for horizon in (25, 50, 100, 250):
            values = {"point": 0.01, "lower": -0.02, "upper": 0.04, "p_holm_16": 0.8}
            values.update(overrides.get((barrier, horizon), {}))
            rows.append({"barrier_ticks": barrier, "horizon_ticks": horizon, "contrasts": {"K_ABS_minus_N_RAND": values}})
    return rows


def test_mechanism_supported_requires_familywise_positive_cell():
    got = classify_mechanism(family({(9, 100): {"point": 0.12, "lower": 0.03, "upper": 0.21, "p_holm_16": 0.04}}), decision_spec())
    assert got["label"] == "P2_DIAGNOSTIC_MECHANISM_SUPPORTED"
    assert got["positive_cells"] == [{"barrier_ticks": 9, "horizon_ticks": 100}]
    assert not got["winner_selected"] and not got["edge_declared"]


def test_mechanism_not_supported_means_threshold_not_met():
    got = classify_mechanism(family(), decision_spec())
    assert got["label"] == "P2_DIAGNOSTIC_MECHANISM_NOT_SUPPORTED"
    assert got["positive_cells"] == []


def test_conflicting_familywise_cells_are_inconclusive():
    got = classify_mechanism(
        family({
            (5, 25): {"point": 0.2, "lower": 0.05, "upper": 0.3, "p_holm_16": 0.01},
            (30, 250): {"point": -0.2, "lower": -0.3, "upper": -0.05, "p_holm_16": 0.01},
        }),
        decision_spec(),
    )
    assert got["label"] == "P2_DIAGNOSTIC_INCONCLUSIVE"


def test_nonfinite_primary_cell_is_inconclusive():
    got = classify_mechanism(family({(5, 25): {"point": float("nan")}}), decision_spec())
    assert got["label"] == "P2_DIAGNOSTIC_INCONCLUSIVE"
    assert got["reason"] == "INVALID_PRIMARY_CELL"


def event(event_id: str, arm: str, contract: str, session: str, direction: int):
    value = {"event_id": event_id, "arm": arm, "contract": contract, "cme_session": session, "direction": direction}
    value["identity_sha256"] = canonical_sha256(value)
    return value


def write_store(tmp_path: Path):
    events_all = []
    (tmp_path / "checkpoints").mkdir()
    for index in range(2):
        events = [event(f"A{index}", "K_ABS", "GC", f"S{index}", 1), event(f"B{index}", "K_BT2", "GC", f"S{index}", -1)]
        events_all.extend(events)
        checkpoint = {
            "schema": "bt2a_gate1_canonical_event_store_session_v1",
            "status": "COMPLETE",
            "session_index": index,
            "contract": "GC",
            "cme_session": f"S{index}",
            "runtime_sha256": "runtime",
            "canonical_gate1_commit": "gate1",
            "sample_registry_payload_sha256": "sample",
            "input_registry_payload_sha256": "input",
            "counts": {"K_ABS": 1, "K_BT2": 1},
            "events": events,
            "events_sha256": canonical_sha256(events),
        }
        (tmp_path / "checkpoints" / f"session_{index:03d}.json").write_text(json.dumps(checkpoint))
    parquet = tmp_path / "events.parquet"
    parquet.write_bytes(b"not a real parquet; identity test only")
    digest = hashlib.sha256(parquet.read_bytes()).hexdigest()
    manifest = {
        "status": "COMPLETE_RECONCILED_WITH_GATE1_ALL5",
        "n_sessions": 2,
        "n_events": 4,
        "events_payload_sha256": canonical_sha256(events_all),
        "runtime_sha256": "runtime",
        "input_registry_payload_sha256": "input",
        "sample_registry_payload_sha256": "sample",
        "counts": {"GC": {"K_ABS": 2, "K_BT2": 2}},
        "builder_git": {"commit": "commit", "branch": "branch", "dirty": False},
        "canonical_gate1_commit": "gate1",
        "parquet": {"path": parquet.name, "sha256": digest},
    }
    (tmp_path / "run_manifest.json").write_text(json.dumps(manifest))
    spec = {
        "input": {"required_manifest_status": "COMPLETE_RECONCILED_WITH_GATE1_ALL5"},
        "canonical_event_store": {
            "n_sessions": 2,
            "n_events": 4,
            "events_payload_sha256": canonical_sha256(events_all),
            "runtime_sha256": "runtime",
            "input_registry_payload_sha256": "input",
            "sample_registry_payload_sha256": "sample",
            "counts_by_contract": {"GC": {"K_ABS": 2, "K_BT2": 2}},
            "counts_total": {"K_ABS": 2, "K_BT2": 2},
            "builder_git_commit": "commit",
            "builder_git_branch": "branch",
            "builder_git_dirty": False,
            "canonical_gate1_commit": "gate1",
            "parquet_sha256": digest,
        },
    }
    return spec


def test_event_store_identity_recomputes_every_checkpoint(tmp_path: Path):
    spec = write_store(tmp_path)
    assert validate_canonical_event_store(tmp_path, spec)["ready"]
    (tmp_path / "checkpoints" / "session_000.json").write_text("not-json")
    bad = validate_canonical_event_store(tmp_path, spec)
    assert not bad["ready"]
    assert not bad["checks"]["checkpoint_payloads_valid"]


def test_self_consistent_checkpoint_tamper_breaks_aggregate_payload(tmp_path: Path):
    spec = write_store(tmp_path)
    path = tmp_path / "checkpoints" / "session_000.json"
    value = json.loads(path.read_text())
    value["events"][0]["direction"] = -1
    body = {k: v for k, v in value["events"][0].items() if k != "identity_sha256"}
    value["events"][0]["identity_sha256"] = canonical_sha256(body)
    value["events_sha256"] = canonical_sha256(value["events"])
    path.write_text(json.dumps(value))
    bad = validate_canonical_event_store(tmp_path, spec)
    assert not bad["ready"]
    assert not bad["checks"]["actual_events_payload_sha256"]


def p2a_checkpoint():
    cells = []
    for barrier in (5, 9, 18, 30):
        for kind, horizons in (("ticks", (25, 50, 100, 250)), ("seconds", (5, 30, 120))):
            for horizon in horizons:
                cells.append({
                    "barrier_ticks": barrier,
                    "horizon_type": kind,
                    "horizon_value": horizon,
                    "contrasts": {
                        "K_ABS_minus_N_RAND": 0.1,
                        "K_ABS_minus_K_ABS_SHUFFLE": 0.1,
                        "K_ABS_minus_K_BT2": 0.1,
                    },
                })
    value = {
        "schema": "bt2a_gate2_p2a_session_v1",
        "status": "COMPLETE_POST_OUTCOME_DIAGNOSTIC_SESSION",
        "session_index": 0,
        "contract": "GC",
        "cme_session": "S0",
        "spec_payload_sha256": "spec",
        "source_event_checkpoint_sha256": "source",
        "control_replications": 10000,
        "cells": cells,
        "CAMPAIGN_OUTCOMES_OPENED": True,
        "EDGE_DECLARED": False,
        "confirmatory_eligible": False,
    }
    value["payload_sha256"] = canonical_sha256(value)
    return value


def validate_session(value):
    return validate_p2a_session_checkpoint(
        value,
        expected_index=0,
        expected_contract="GC",
        expected_session="S0",
        expected_spec_payload_sha256="spec",
        expected_source_event_checkpoint_sha256="source",
        expected_control_replications=10000,
        barriers=(5, 9, 18, 30),
        tick_horizons=(25, 50, 100, 250),
        clock_horizons=(5, 30, 120),
    )


def test_p2a_checkpoint_is_bound_to_spec_event_store_and_payload():
    value = p2a_checkpoint()
    assert validate_session(value)["ready"]
    bad = copy.deepcopy(value)
    bad["source_event_checkpoint_sha256"] = "other"
    bad["payload_sha256"] = canonical_sha256({k: v for k, v in bad.items() if k != "payload_sha256"})
    assert not validate_session(bad)["ready"]


def load_runner_module():
    path = Path("tools/run_bt2a_gate2_p2a.py")
    spec = importlib.util.spec_from_file_location("bt2a_runner", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_full_spec_hash_and_previously_unchecked_fields_are_enforced():
    runner = load_runner_module()
    spec = json.loads(Path("specs/bt2a_gate2_first_passage_v1.json").read_text())
    assert all(runner.frozen_constant_checks(spec).values())
    mutated = copy.deepcopy(spec)
    mutated["inference"]["method"] = "NOT_WEBB"
    mutated["inference"]["confidence"] = 0.5
    mutated["p2a"]["aggregation"] = "EVENT_IID"
    mutated["freeze"]["execution_authorization_token"] = "WRONG"
    checks = runner.frozen_constant_checks(mutated)
    assert not checks["spec_payload_sha256"]
    assert not checks["inference_method"]
    assert not checks["confidence"]
    assert not checks["aggregation"]
    assert not checks["authorization_token"]


def test_validate_only_not_ready_returns_nonzero(tmp_path: Path):
    run = subprocess.run(
        [sys.executable, "tools/run_bt2a_gate2_p2a.py", "--event-store-dir", str(tmp_path / "missing"), "--validate-only"],
        text=True,
        capture_output=True,
    )
    assert run.returncode == 2
    assert json.loads(run.stdout)["status"] == "NOT_READY"
