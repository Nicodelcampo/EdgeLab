from dataclasses import replace
import pytest
from edgelab.kaggle.avzvol_reactions import Band, Bar, Policy, classify_synthetic_reaction

BAND = Band("SYNTHETIC-BAND", 100, 110, -1, -1)
POLICY = Policy("SYNTHETIC-NOT-MARKET-POLICY", 0, 1, 10, "inside",
                "strictly_later_bar", "terminate_unknown")


def bar(n, low, high, close, session="A", complete=True):
    return Bar(str(n), session, n * 10, n * 10, n, high, low, close, complete)


def run(bars, policy=POLICY, cohort="zone_candidate", band=BAND):
    tape = [bar(0, 101, 109, 105)] + bars if bars else []
    return classify_synthetic_reaction(band, tape, policy=policy, cohort=cohort, purpose="synthetic")


def test_continuation_requires_three_observations():
    r = run([bar(1, 111, 115, 114), bar(2, 109, 113, 112), bar(3, 111, 114, 113)])
    assert [x["state"] for x in r["events"]] == ["INSIDE_BASELINE_OBSERVED", "EXIT_OBSERVED", "RETEST_OBSERVED", "CONTINUATION_TRIGGER"]
    assert r["events"][-1]["bar_id"] == "3"


def test_failed_break_after_later_inside_close():
    assert run([bar(1, 111, 115, 114), bar(2, 109, 113, 112), bar(3, 104, 109, 105)])["state"] == "FAILED_BREAK_TRIGGER"


def test_touch_is_not_trigger():
    assert run([bar(1, 111, 115, 114), bar(2, 109, 113, 112)])["state"] == "RETEST_OBSERVED"


def test_inside_on_retest_bar_does_not_infer_intrabar_order():
    assert run([bar(1, 111, 115, 114), bar(2, 105, 113, 106)])["state"] == "RETEST_OBSERVED"


def test_downward_mirror():
    r = run([bar(1, 95, 99, 96), bar(2, 98, 102, 99), bar(3, 95, 99, 96)])
    assert r["state"] == "CONTINUATION_TRIGGER" and r["events"][-1]["exit_side_observed"] == -1


def test_no_future_data_needed_prefix_same_trigger():
    prefix = [bar(1, 111, 115, 114), bar(2, 109, 113, 112), bar(3, 111, 114, 113)]
    assert run(prefix) == run(prefix + [bar(4, 50, 200, 51)])


def test_exit_bar_cannot_supply_its_own_retest():
    assert run([bar(1, 105, 115, 114)])["state"] == "EXIT_OBSERVED"


def test_unknown_history_not_negative():
    assert run([bar(1, 101, 108, 105, complete=False)])["state"] == "UNKNOWN_HISTORY"


def test_session_boundary_terminates_unknown():
    assert run([bar(1, 111, 115, 114), bar(2, 109, 113, 112, session="B")])["state"] == "UNKNOWN_SESSION_BOUNDARY"


def test_late_band_cannot_backfill():
    with pytest.raises(ValueError, match="not known"):
        run([bar(1, 111, 115, 114)], band=replace(BAND, known_ns=15))


def test_increasing_order_required():
    with pytest.raises(ValueError, match="increasing"):
        run([bar(2, 101, 108, 105), bar(1, 101, 108, 105)])


def test_equal_timestamp_source_order_resolves():
    a = bar(1, 111, 115, 114)
    b = replace(bar(2, 109, 113, 112), end_ns=10, available_ns=10)
    assert run([a, b])["state"] == "RETEST_OBSERVED"


def test_same_geometry_control_same_algorithm_not_certified():
    bars = [bar(1, 111, 115, 114), bar(2, 109, 113, 112), bar(3, 104, 109, 105)]
    a = run(bars); b = run(bars, cohort="geometry_control_candidate")
    assert a["events"] == b["events"] and not b["control_eligibility_certified"]


def test_no_observed_exit_not_success_or_negative_outcome():
    assert run([bar(1, 101, 108, 105)])["state"] == "NO_OBSERVED_EXIT"


def test_opposite_exit_not_relabelled_continuation():
    assert run([bar(1, 111, 115, 114), bar(2, 90, 99, 95)])["state"] == "OPPOSITE_EXIT_WITHOUT_RETEST_OBSERVED"


def test_exact_boundary_is_explicit_policy():
    bars = [bar(1, 111, 115, 114), bar(2, 109, 113, 112), bar(3, 108, 112, 110)]
    assert run(bars)["state"] == "FAILED_BREAK_TRIGGER"
    assert run(bars, replace(POLICY, boundary_close="unclassified"))["state"] == "RETEST_OBSERVED"


def test_confirmation_streak_switch_resets():
    bars = [bar(1, 111, 115, 114), bar(2, 109, 113, 112), bar(3, 111, 115, 114),
            bar(4, 104, 109, 105), bar(5, 104, 109, 105)]
    r = run(bars, replace(POLICY, confirmation_closes=2))
    assert r["state"] == "FAILED_BREAK_TRIGGER" and r["events"][-1]["bar_id"] == "5"


def test_timeout_preserved():
    bars = [bar(1, 111, 115, 114), bar(2, 111, 115, 114), bar(3, 109, 113, 112)]
    assert run(bars, replace(POLICY, max_bars_after_exit=1))["state"] == "UNCONFIRMED_TIMEOUT"


def test_market_execution_stops():
    with pytest.raises(ValueError, match="STOP"):
        classify_synthetic_reaction(BAND, [], policy=POLICY, cohort="zone_candidate", purpose="research")


def test_invalid_ohlc_rejected():
    with pytest.raises(ValueError, match="completed bar"):
        run([bar(1, 100, 110, 120)])


def test_buffer_not_optimized_or_defaulted():
    assert run([bar(1, 111, 115, 111)], replace(POLICY, buffer_ticks=2))["state"] == "NO_OBSERVED_EXIT"


def test_invalid_policy_rejected():
    with pytest.raises(ValueError, match="explicit"):
        run([], replace(POLICY, confirmation_closes=0))


def test_initial_outside_not_invented_exit():
    r = classify_synthetic_reaction(BAND, [bar(1, 111, 115, 114)], policy=POLICY,
                                    cohort="zone_candidate", purpose="synthetic")
    assert r["state"] == "OUTSIDE_WITHOUT_OBSERVED_EXIT"
    assert all(e["exit_side_observed"] == 0 for e in r["events"])


def test_initial_outside_then_inside_then_exit_can_arm():
    bars = [bar(1, 111, 115, 114), bar(2, 101, 109, 105), bar(3, 111, 115, 114)]
    r = classify_synthetic_reaction(BAND, bars, policy=POLICY,
                                    cohort="zone_candidate", purpose="synthetic")
    assert r["state"] == "EXIT_OBSERVED" and r["events"][-1]["bar_id"] == "3"
