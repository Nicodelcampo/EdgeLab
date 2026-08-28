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
                "cells": [{
                    "barrier_ticks": 9,
                    "horizon_ticks": 25,
                    "K_ABS_minus_N_RAND": effect,
                }],
            })
        rows.append({"session_index": index, "phases": phases})
    return rows


def test_heterogeneity_family_uses_holm_and_never_selects_winner():
    result = aggregate_clock_family(
        synthetic_rows(130, 0.20),
        parent_cells=[(9, 25)],
        replications=400,
        base_seed=7,
        min_other_phases=2,
        min_sessions=117,
    )
    assert result["status"] == "COMPLETE"
    assert len(result["family"]) == 4
    assert result["decision"]["label"] == "P2A_POST_SELECTION_CLOCK_HETEROGENEITY_SIGNAL"
    assert result["decision"]["passing_contrasts"]
    assert result["decision"]["winner_selected"] is False
    assert result["decision"]["edge_declared"] is False
    assert all(row["p_holm_12"] is not None for row in result["family"])


def test_equal_phase_effects_do_not_create_clock_signal():
    rows = synthetic_rows(130, 0.0)
    result = aggregate_clock_family(
        rows,
        parent_cells=[(9, 25)],
        replications=300,
        base_seed=8,
        min_other_phases=2,
        min_sessions=117,
    )
    assert result["decision"]["label"] == "P2A_POST_SELECTION_NO_CLOCK_HETEROGENEITY_SIGNAL"


def test_coverage_failure_is_inconclusive_not_silently_dropped():
    result = aggregate_clock_family(
        synthetic_rows(50, 0.20),
        parent_cells=[(9, 25)],
        replications=100,
        base_seed=9,
        min_other_phases=2,
        min_sessions=117,
    )
    assert result["status"] == "INCOMPLETE"
    assert result["decision"]["label"] == "P2A_CLOCK_HETEROGENEITY_INCONCLUSIVE"


def load_runner():
    path = ROOT / "tools" / "run_bt2a_p2a_gc_clock_heterogeneity.py"
    spec = importlib.util.spec_from_file_location("clock_runner", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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


def test_spec_freezes_post_selection_interpretation_and_12_cell_family():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert spec["source_p2a"]["confirmatory_eligible"] is False
    assert len(spec["source_p2a"]["parent_cells_selected_post_outcome"]) == 3
    assert len(spec["phases"]["definitions"]) == 4
    assert spec["inference"]["primary_family"] == "12_PHASE_VS_REST_CONTRASTS"
    assert spec["inference"]["multiplicity"] == "HOLM_OVER_12"
    assert spec["decision_rule"]["winner_selection_allowed"] is False
    assert spec["decision_rule"]["p2b_rule_change_allowed"] is False
    assert "BEST_WINDOW" in spec["forbidden_labels"]
