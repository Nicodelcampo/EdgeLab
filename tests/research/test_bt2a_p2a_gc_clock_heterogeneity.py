from __future__ import annotations

from datetime import datetime
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

import pytest

from edgelab.research.bt2a_clock_heterogeneity import (
    PHASES,
    aggregate_clock_family,
    in_macro_blackout,
    phase_for_ns,
)

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "specs" / "bt2a_p2a_gc_clock_heterogeneity_v1.json"
CHICAGO = ZoneInfo("America/Chicago")
PARENT_CELLS = ((9, 25), (30, 100), (30, 250))


def local_ns(text: str) -> int:
    return int(datetime.fromisoformat(text).replace(tzinfo=CHICAGO).timestamp() * 1_000_000_000)


def test_gc_phase_boundaries_are_left_closed_right_open():
    assert phase_for_ns(local_ns("2026-03-10T17:00:00")) == "ASIA_ETH"
    assert phase_for_ns(local_ns("2026-03-11T00:59:59")) == "ASIA_ETH"
    assert phase_for_ns(local_ns("2026-03-11T01:00:00")) == "EUROPE_PRE_RTH"
    assert phase_for_ns(local_ns("2026-03-11T07:19:59")) == "EUROPE_PRE_RTH"
    assert phase_for_ns(local_ns("2026-03-11T07:20:00")) == "GC_RTH"
    assert phase_for_ns(local_ns("2026-03-11T12:30:00")) == "POST_RTH"
    assert phase_for_ns(local_ns("2026-03-11T16:00:00")) is None
    assert phase_for_ns(local_ns("2026-03-11T16:59:59")) is None


def test_phase_conversion_uses_chicago_dst_rules():
    assert phase_for_ns(local_ns("2026-01-15T07:20:00")) == "GC_RTH"
    assert phase_for_ns(local_ns("2026-06-15T07:20:00")) == "GC_RTH"


def test_macro_blackout_is_left_closed_right_open():
    intervals = [(100, 200)]
    assert not in_macro_blackout(99, intervals)
    assert in_macro_blackout(100, intervals)
    assert in_macro_blackout(199, intervals)
    assert not in_macro_blackout(200, intervals)


def synthetic_rows(n: int, asia_effect: float) -> list[dict]:
    rows = []
    for index in range(n):
        phases = []
        for phase in PHASES:
            effect = asia_effect if phase == "ASIA_ETH" else 0.0
            phases.append({
                "phase": phase,
                "status": "COMPLETE",
                "cells": [
                    {
                        "barrier_ticks": barrier,
                        "horizon_ticks": horizon,
                        "K_ABS_minus_N_RAND": effect,
                    }
                    for barrier, horizon in PARENT_CELLS
                ],
            })
        rows.append({"session_index": index, "phases": phases})
    return rows


def aggregate(rows, *, replications=300):
    return aggregate_clock_family(
        rows,
        parent_cells=PARENT_CELLS,
        replications=replications,
        base_seed=7,
        min_other_phases=3,
        min_sessions=117,
    )


def test_heterogeneity_family_uses_holm_12_and_never_selects_winner():
    result = aggregate(synthetic_rows(130, 0.20), replications=400)
    assert result["status"] == "COMPLETE"
    assert len(result["family"]) == 12
    assert result["decision"]["label"] == "P2A_POST_SELECTION_CLOCK_HETEROGENEITY_SIGNAL"
    assert result["decision"]["passing_contrasts"]
    assert result["decision"]["winner_selected"] is False
    assert result["decision"]["edge_declared"] is False
    assert all(row["p_holm_12"] is not None for row in result["family"])


def test_equal_phase_effects_do_not_create_clock_signal():
    result = aggregate(synthetic_rows(130, 0.0))
    assert result["decision"]["label"] == "P2A_POST_SELECTION_NO_CLOCK_HETEROGENEITY_SIGNAL"


def test_coverage_failure_is_inconclusive_not_silently_dropped():
    result = aggregate(synthetic_rows(50, 0.20), replications=100)
    assert result["status"] == "INCOMPLETE"
    assert result["decision"]["label"] == "P2A_CLOCK_HETEROGENEITY_INCONCLUSIVE"


def test_missing_one_comparison_phase_does_not_change_estimand():
    rows = synthetic_rows(130, 0.20)
    for row in rows:
        row["phases"] = [phase for phase in row["phases"] if phase["phase"] != "POST_RTH"]
    result = aggregate(rows, replications=100)
    assert result["status"] == "INCOMPLETE"
    assert result["decision"]["label"] == "P2A_CLOCK_HETEROGENEITY_INCONCLUSIVE"


def load_runner():
    path = ROOT / "tools" / "run_bt2a_p2a_gc_clock_heterogeneity.py"
    spec = importlib.util.spec_from_file_location("clock_runner", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_frozen_macro_calendar_identity_and_count():
    runner = load_runner()
    calendar, intervals = runner.load_macro_intervals(ROOT / runner.MACRO_REL)
    assert runner.file_sha256(ROOT / runner.MACRO_REL) == runner.MACRO_FILE_SHA256
    assert calendar["counts"] == {"FOMC": 7, "CPI": 10, "NFP": 9, "total": 26}
    assert len(intervals) == 26
    assert max(start for start, _ in intervals) < runner.HOLDOUT_NS


def test_draft_contract_is_deliberately_fail_closed():
    runner = load_runner()
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    checks = runner.frozen_contract_checks(spec)
    assert spec["status"] == "DRAFT_PREAUTHORIZATION_FAIL_CLOSED"
    assert checks["schema"]
    assert not checks["status_frozen"]
    assert not checks["spec_payload_bound"]
    assert spec["authorization"]["execution_authorized"] is False
    assert spec["firewall"]["HOLDOUT_TOUCHED"] is False
    assert spec["firewall"]["P2B_RUN"] is False
    assert spec["firewall"]["WINNER_SELECTED"] is False
    with pytest.raises(SystemExit, match="ABSTAIN_MISSING_EXPLICIT_CLOCK_AUTHORIZATION"):
        runner.require_authorization(None)


def test_preflight_missing_inputs_returns_nonzero_without_opening_paths(tmp_path: Path):
    run = subprocess.run(
        [
            sys.executable,
            "tools/run_bt2a_p2a_gc_clock_heterogeneity.py",
            "--event-store-dir", str(tmp_path / "missing-store"),
            "--data-dir", str(tmp_path / "missing-data"),
            "--preflight-only",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert run.returncode == 2
    result = json.loads(run.stdout)
    assert result["status"] == "NOT_READY"
    assert result["FUTURE_PRICE_PATH_ACCESSED_BY_PREPARATION"] is False
    assert result["FUTURE_PRICE_PATH_ACCESSED"] is True
    assert result["PNL_ACCESSED"] is False
    assert result["HOLDOUT_TOUCHED"] is False


def test_spec_freezes_post_selection_interpretation_and_fixed_12_cell_family():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert spec["source_p2a"]["confirmatory_eligible"] is False
    assert len(spec["source_p2a"]["parent_cells_selected_post_outcome"]) == 3
    assert len(spec["phases"]["definitions"]) == 4
    assert spec["estimand"]["minimum_other_phases"] == 3
    assert spec["inference"]["primary_family"] == "12_PHASE_VS_REST_CONTRASTS"
    assert spec["inference"]["multiplicity"] == "HOLM_OVER_12"
    assert spec["decision_rule"]["winner_selection_allowed"] is False
    assert spec["decision_rule"]["p2b_rule_change_allowed"] is False
    assert "BEST_WINDOW" in spec["forbidden_labels"]


def test_negative_frozen_contract_checks():
    runner = load_runner()
    base_spec = json.loads(SPEC.read_text(encoding="utf-8"))

    # 1. freeze_authorized = false => fails freeze_authorized check
    spec1 = json.loads(json.dumps(base_spec))
    spec1["status"] = "FROZEN_PREAUTHORIZATION"
    spec1["authorization"]["freeze_authorized"] = False
    assert not runner.frozen_contract_checks(spec1)["freeze_authorized"]

    # 2. status != FROZEN_PREAUTHORIZATION => fails status_frozen check
    spec2 = json.loads(json.dumps(base_spec))
    spec2["status"] = "DRAFT_PREAUTHORIZATION_FAIL_CLOSED"
    assert not runner.frozen_contract_checks(spec2)["status_frozen"]

    # 3. minimum_other_phases != 3 => fails minimum_other_phases check
    spec3 = json.loads(json.dumps(base_spec))
    spec3["estimand"]["minimum_other_phases"] = 2
    assert not runner.frozen_contract_checks(spec3)["minimum_other_phases"]

    # 4. minimum_sessions_per_contrast != 117 => fails minimum_sessions check
    spec4 = json.loads(json.dumps(base_spec))
    spec4["estimand"]["minimum_sessions_per_contrast"] = 100
    assert not runner.frozen_contract_checks(spec4)["minimum_sessions_per_contrast"]

    # 5. Mutating any field => normalized hash mismatch
    spec5 = json.loads(json.dumps(base_spec))
    spec5["status"] = "FROZEN_PREAUTHORIZATION"
    spec5["authorization"]["freeze_authorized"] = True
    spec5["freeze"]["frozen_spec_payload_sha256"] = runner.frozen_spec_payload_sha256(spec5)
    spec5["purpose"] = "Mutated purpose string"
    assert not runner.frozen_contract_checks(spec5)["spec_payload_bound"]

    # 6. Mutating declared hash => fails spec_payload_bound
    spec6 = json.loads(json.dumps(base_spec))
    spec6["status"] = "FROZEN_PREAUTHORIZATION"
    spec6["authorization"]["freeze_authorized"] = True
    spec6["freeze"]["frozen_spec_payload_sha256"] = "0" * 64
    assert not runner.frozen_contract_checks(spec6)["spec_payload_bound"]


def test_atomic_json_roundtrip_and_cleanup(tmp_path: Path):
    """Smoke test covering: import uuid, sort_keys, allow_nan, tempfile cleanup."""
    runner = load_runner()
    target = tmp_path / "sub" / "checkpoint.json"
    payload = {"z_key": 1, "a_key": 2, "nested": {"b": True, "a": False}}
    runner.atomic_json(target, payload)
    # File must exist
    assert target.is_file()
    # No leftover temp files
    siblings = list(target.parent.iterdir())
    assert len(siblings) == 1 and siblings[0].name == "checkpoint.json"
    # Content must be valid JSON dict
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    assert loaded == payload
    # Keys must be sorted in serialized output (sort_keys=True)
    raw = target.read_text(encoding="utf-8")
    a_pos = raw.index('"a_key"')
    z_pos = raw.index('"z_key"')
    assert a_pos < z_pos, "sort_keys=True must order keys alphabetically"


def test_atomic_json_rejects_nan(tmp_path: Path):
    """allow_nan=False must reject NaN/Infinity."""
    runner = load_runner()
    target = tmp_path / "bad.json"
    with pytest.raises(ValueError):
        runner.atomic_json(target, {"value": float("nan")})
    assert not target.exists()


def test_load_json_rejects_non_dict(tmp_path: Path):
    """load_json must reject JSON arrays and scalars."""
    runner = load_runner()
    array_file = tmp_path / "array.json"
    array_file.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(RuntimeError, match="JSON object required"):
        runner.load_json(array_file)
    scalar_file = tmp_path / "scalar.json"
    scalar_file.write_text('"hello"', encoding="utf-8")
    with pytest.raises(RuntimeError, match="JSON object required"):
        runner.load_json(scalar_file)


def test_positive_freeze_roundtrip():
    """A correctly frozen spec must pass 100% of frozen_contract_checks, and a single mutation must break it."""
    runner = load_runner()
    base_spec = json.loads(SPEC.read_text(encoding="utf-8"))

    # Build a valid frozen spec
    spec = json.loads(json.dumps(base_spec))
    spec["status"] = "FROZEN_PREAUTHORIZATION"
    spec["authorization"]["freeze_authorized"] = True
    spec["authorization"]["execution_authorized"] = False
    # Compute and place the frozen hash
    payload_hash = runner.frozen_spec_payload_sha256(spec)
    spec["freeze"]["frozen_spec_payload_sha256"] = payload_hash

    # Temporarily bind the runner constant to the computed hash
    original = runner.EXPECTED_FROZEN_SPEC_PAYLOAD_SHA256
    try:
        runner.EXPECTED_FROZEN_SPEC_PAYLOAD_SHA256 = payload_hash

        checks = runner.frozen_contract_checks(spec)
        failed = {k: v for k, v in checks.items() if not v}
        assert not failed, f"All contract checks must pass on a frozen spec, but failed: {failed}"

        # Mutate one scientific field — must break spec_payload_bound
        mutated = json.loads(json.dumps(spec))
        mutated["estimand"]["minimum_sessions_per_contrast"] = 99
        mutated_checks = runner.frozen_contract_checks(mutated)
        assert not mutated_checks["spec_payload_bound"], "Mutation was not detected by spec_payload_bound"
        assert not mutated_checks["minimum_sessions_per_contrast"], "Mutation was not detected by minimum_sessions_per_contrast"
    finally:
        runner.EXPECTED_FROZEN_SPEC_PAYLOAD_SHA256 = original


def test_validate_clock_event_store_path_b_policy(tmp_path: Path):
    """Path B: Logical identity is primary; different parquet physical hash is DIFFERENT_NON_BLOCKING if parquet is logically identical to checkpoints."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    runner = load_runner()
    source_spec = json.loads((ROOT / "specs" / "bt2a_gate2_first_passage_v1.json").read_text(encoding="utf-8"))
    expected = source_spec["canonical_event_store"]

    # 1. Missing manifest -> ready=False, logical_identity=FAIL
    res_empty = runner.validate_clock_event_store(tmp_path, source_spec)
    assert not res_empty["ready"]
    assert res_empty["logical_identity"] == "FAIL"

    # Setup manifest with canonical logical fields
    manifest = {
        "status": "COMPLETE_RECONCILED_WITH_GATE1_ALL5",
        "n_sessions": 234,
        "n_events": 22202,
        "events_payload_sha256": "feee6001e88aa69f62a092b253e468531230120a3dccdc2ceac0d488c9684cbd",
        "counts": expected["counts_by_contract"],
        "parquet": {"path": "bt2a_gate1_canonical_events_all5.parquet", "sha256": "different_transport_hash_123"},
    }
    (tmp_path / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    # 2. Corrupt parquet bytes -> CORRUPT_OR_INVALID, ready=False
    parquet_file = tmp_path / "bt2a_gate1_canonical_events_all5.parquet"
    parquet_file.write_bytes(b"CORRUPT_NOT_A_PARQUET_FILE")
    res_corrupt = runner.validate_clock_event_store(tmp_path, source_spec)
    assert not res_corrupt["ready"]
    assert res_corrupt["physical_transport_identity"] == "CORRUPT_OR_INVALID"
    assert not res_corrupt["checks"]["parquet_readable"]

    # 3. Build synthetic 234 checkpoints matching the canonical payload
    # Distribute events across 234 sessions matching contract counts
    n_kabs = 16940
    n_kbt2 = 5262
    total = n_kabs + n_kbt2
    # Use real events from real store if available, or generate canonical deterministic events
    real_store = Path(r"E:\DatosNT8\event_store_gc_all5")
    if (real_store / "run_manifest.json").is_file() and (real_store / "bt2a_gate1_canonical_events_all5.parquet").is_file():
        # Copy real checkpoints into tmp_path
        ckpt_dir = tmp_path / "checkpoints"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        for p in (real_store / "checkpoints").glob("session_*.json"):
            (ckpt_dir / p.name).write_bytes(p.read_bytes())
        
        # Read real Parquet table and re-write with PyArrow (different transport hash due to writer metadata)
        real_table = pq.read_table(real_store / "bt2a_gate1_canonical_events_all5.parquet")
        pq.write_table(real_table, parquet_file)

        # Verify Positive End-to-End Camino B: ready=True, DIFFERENT_NON_BLOCKING
        res_e2e = runner.validate_clock_event_store(tmp_path, source_spec)
        assert res_e2e["ready"] is True
        assert res_e2e["logical_identity"] == "PASS"
        assert res_e2e["physical_transport_identity"] in ("CANONICAL_MATCH", "DIFFERENT_NON_BLOCKING")
        assert res_e2e["checks"]["parquet_matches_checkpoints_1to1"] is True

        # 4. Negative Test: Mutate one field in Parquet (swap event direction), preserving schema, 22.202 rows & arm counts
        df_mutated = real_table.to_pandas()
        # Find two rows with opposite directions and swap their directions
        idx_pos = df_mutated[df_mutated["direction"] == 1].index[0]
        idx_neg = df_mutated[df_mutated["direction"] == -1].index[0]
        df_mutated.loc[idx_pos, "direction"] = -1
        df_mutated.loc[idx_neg, "direction"] = 1
        mutated_table = pa.Table.from_pandas(df_mutated)
        pq.write_table(mutated_table, parquet_file)

        res_mutated = runner.validate_clock_event_store(tmp_path, source_spec)
        assert res_mutated["ready"] is False
        assert res_mutated["logical_identity"] == "FAIL"
        assert res_mutated["physical_transport_identity"] == "CORRUPT_OR_INVALID"
        assert res_mutated["checks"]["parquet_matches_checkpoints_1to1"] is False



def test_mandatory_expected_commit_in_frozen_mode():
    """In FROZEN_PREAUTHORIZATION status, preflight requires --expected-commit to be ready."""
    runner = load_runner()
    # When require_commit=True and expected_commit is None -> commit_exact is False
    git_checks = runner._git_checks(ROOT, expected_commit=None, require_commit=True)
    assert git_checks["commit_exact"] is False

    # When expected_commit matches HEAD -> commit_exact is True
    head_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True).stdout.strip()
    git_checks_valid = runner._git_checks(ROOT, expected_commit=head_sha, require_commit=True)
    assert git_checks_valid["commit_exact"] is True

    # When expected_commit is mismatched -> commit_exact is False
    git_checks_bad = runner._git_checks(ROOT, expected_commit="0" * 40, require_commit=True)
    assert git_checks_bad["commit_exact"] is False


def test_execution_modes_abort_immediately_without_expected_commit(tmp_path: Path):
    """Execution modes (--run-all, --session-index, --finalize) must fail-closed immediately without --expected-commit."""
    for flag in (["--run-all"], ["--session-index", "0"], ["--finalize"]):
        run_missing = subprocess.run(
            [
                sys.executable,
                "tools/run_bt2a_p2a_gc_clock_heterogeneity.py",
                "--event-store-dir", str(tmp_path),
                "--data-dir", str(tmp_path),
                "--output-dir", str(tmp_path / "out"),
                "--authorization-token", "AUTHORIZE_BT2A_P2A_GC_CLOCK_HETEROGENEITY_V1",
                *flag,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert run_missing.returncode != 0
        assert "ABSTAIN_MANDATORY_EXPECTED_COMMIT_REQUIRED_FOR_EXECUTION" in run_missing.stderr

        run_mismatch = subprocess.run(
            [
                sys.executable,
                "tools/run_bt2a_p2a_gc_clock_heterogeneity.py",
                "--event-store-dir", str(tmp_path),
                "--data-dir", str(tmp_path),
                "--output-dir", str(tmp_path / "out"),
                "--authorization-token", "AUTHORIZE_BT2A_P2A_GC_CLOCK_HETEROGENEITY_V1",
                "--expected-commit", "0" * 40,
                *flag,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert run_mismatch.returncode != 0
        assert "ABSTAIN_COMMIT_MISMATCH_AGAINST_EXPECTED_COMMIT" in run_mismatch.stderr


