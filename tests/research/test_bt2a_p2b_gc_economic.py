from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "tools" / "run_bt2a_p2b_gc_economic.py"
SPEC_PATH = ROOT / "specs" / "bt2a_p2b_gc_economic_v1.json"
SPEC = importlib.util.spec_from_file_location("bt2a_p2b_gc_economic", RUNNER_PATH)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)


def _signal(event_id="E1", entry_idx=1, direction=1, signal_ts=0):
    return {
        "event_id": event_id,
        "entry_idx": entry_idx,
        "direction": direction,
        "signal_ts_utc_ns": signal_ts,
    }


def test_spec_freezes_full_family_costs_and_firewall():
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    family = spec["primary_family"]
    cells = {(b, h) for b in family["barriers_ticks"] for h in family["horizons_ticks"]}
    assert len(cells) == family["n_cells"] == 16
    assert family["cross_cell_winner_selection_allowed"] is False
    positives = {(row["barrier_ticks"], row["horizon_ticks"])
                 for row in family["p2a_positive_cells_annotation_only"]}
    assert positives == {(9, 25), (30, 100), (30, 250)}
    assert spec["costs"]["scenarios"]["base"]["all_in_friction_ticks_including_spread"] == 3.5
    assert spec["costs"]["scenarios"]["adverse"]["all_in_friction_ticks_including_spread"] == 5.5
    assert spec["firewall"]["P2B_RUN"] is False
    assert spec["firewall"]["HOLDOUT_TOUCHED"] is False
    assert spec["firewall"]["WINNER_SELECTED"] is False
    assert spec["firewall"]["EDGE_DECLARED"] is False


def test_frozen_constant_checks_all_pass():
    checks = runner.frozen_checks(runner.load_spec(ROOT))
    assert checks and all(checks.values()), checks


def test_cost_additivity_base_and_adverse():
    base_ticks, base_usd = runner.apply_cost(10.0, "base")
    adverse_ticks, adverse_usd = runner.apply_cost(10.0, "adverse")
    assert base_ticks == 6.5
    assert base_usd == 65.0
    assert adverse_ticks == 4.5
    assert adverse_usd == 45.0
    assert runner.scenario_cost("base")["all_in_ticks"] == 1.0 + 2.0 + 0.5


def test_target_stop_gap_and_timeout_are_deterministic():
    ts = np.array([0, 150_000_000, 300_000_000, 450_000_000], dtype=np.int64)
    target = runner.simulate_cell(
        signals=[_signal()], ts_ns=ts, price_ticks=[100, 100, 105, 105],
        barrier_ticks=5, horizon_ticks=2, scenario="base", macro_intervals=[],
    )
    assert target["trades"][0]["exit_reason"] == "target"
    assert target["trades"][0]["gross_ticks"] == 5.0
    assert target["trades"][0]["net_ticks"] == 1.5

    stop = runner.simulate_cell(
        signals=[_signal()], ts_ns=ts, price_ticks=[100, 100, 94, 94],
        barrier_ticks=5, horizon_ticks=2, scenario="base", macro_intervals=[],
    )
    assert stop["trades"][0]["exit_reason"] == "stop"
    assert stop["trades"][0]["gross_ticks"] == -6.0
    assert stop["trades"][0]["net_ticks"] == -9.5

    timeout = runner.simulate_cell(
        signals=[_signal()], ts_ns=ts, price_ticks=[100, 100, 102, 103],
        barrier_ticks=5, horizon_ticks=2, scenario="base", macro_intervals=[],
    )
    assert timeout["trades"][0]["exit_reason"] == "timeout"
    assert timeout["trades"][0]["gross_ticks"] == 3.0
    assert timeout["trades"][0]["net_ticks"] == -0.5
    replay = runner.simulate_cell(
        signals=[_signal()], ts_ns=ts, price_ticks=[100, 100, 102, 103],
        barrier_ticks=5, horizon_ticks=2, scenario="base", macro_intervals=[],
    )
    assert replay["summary"]["trade_digest"] == timeout["summary"]["trade_digest"]


def test_macro_blackout_is_half_open_and_concurrency_is_persisted():
    start = 100
    end = start + 5 * 60 * 1_000_000_000
    assert runner.is_macro_excluded(start, [(start, end)])
    assert runner.is_macro_excluded(end - 1, [(start, end)])
    assert not runner.is_macro_excluded(end, [(start, end)])

    ts = np.array([0, 150_000_000, 300_000_000, 450_000_000, 600_000_000], dtype=np.int64)
    result = runner.simulate_cell(
        signals=[_signal("E1", 1), _signal("E2", 2)],
        ts_ns=ts, price_ticks=[100, 100, 101, 102, 103],
        barrier_ticks=10, horizon_ticks=3, scenario="base", macro_intervals=[],
    )
    assert result["summary"]["n_trades"] == 1
    assert result["summary"]["n_concurrency_rejected"] == 1
    assert any(row["reason"] == "position_open" for row in result["rejected"])


def test_macro_calendar_requires_exact_hash_and_rejects_holdout(tmp_path):
    calendar = {
        "schema": "bt2a_macro_calendar_v1",
        "events": [{
            "event_id": "CPI-1", "event_type": "CPI",
            "release_utc": "2026-06-10T12:30:00Z",
        }],
    }
    path = tmp_path / "macro.json"
    path.write_text(json.dumps(calendar), encoding="utf-8")
    digest = runner.file_sha256(path)
    loaded, intervals = runner.load_macro_calendar(path, digest)
    assert loaded == calendar
    assert len(intervals) == 1
    with pytest.raises(RuntimeError, match="SHA256"):
        runner.load_macro_calendar(path, "0" * 64)

    calendar["events"][0]["release_utc"] = "2026-07-01T00:00:00Z"
    path.write_text(json.dumps(calendar), encoding="utf-8")
    with pytest.raises(RuntimeError, match="HOLDOUT"):
        runner.load_macro_calendar(path, runner.file_sha256(path))


def test_preflight_and_authorization_are_fail_closed(tmp_path):
    with pytest.raises(SystemExit, match="ABSTAIN_MISSING_EXPLICIT_P2B_AUTHORIZATION"):
        runner.require_authorization(None)
    empty_event_store = tmp_path / "event_store"
    empty_data = tmp_path / "data"
    empty_event_store.mkdir()
    empty_data.mkdir()
    macro = tmp_path / "missing.json"
    result = runner.preflight(
        ROOT, empty_event_store, empty_data, macro, "", check_git=False,
    )
    assert result["status"] == "NOT_READY"
    assert result["P2B_RUN"] is False
    assert result["PNL_ACCESSED"] is False
    assert result["FUTURE_PRICE_PATH_ACCESSED"] is False
    assert result["HOLDOUT_TOUCHED"] is False


def test_holm_is_monotone_in_sorted_pvalues():
    adjusted = runner.holm([0.001, 0.02, 0.2, 0.8])
    assert all(0 <= value <= 1 for value in adjusted)
    ordered = sorted(zip([0.001, 0.02, 0.2, 0.8], adjusted))
    assert [value for _, value in ordered] == sorted(value for _, value in ordered)
