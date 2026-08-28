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
    assert result["FUTURE_PRICE_PATH_ACCESSED_BY_PREFLIGHT"] is False
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
