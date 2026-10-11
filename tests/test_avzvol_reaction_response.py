from dataclasses import replace
import pytest
from edgelab.kaggle.avzvol_reaction_response import (
    Decision, ResponseBar, ResponsePolicy, measure_synthetic_response,
    decision_from_synthetic_trace)
from edgelab.kaggle.avzvol_reactions import Band, Bar, Policy, classify_synthetic_reaction

D = Decision("D", "SYNTHETIC-BAND", "SYNTHETIC-TRIGGER", "A", 100, 10, 113, 1, "CONTINUATION_TRIGGER")
P = ResponsePolicy("SYNTHETIC-NOT-MARKET", (20, 40), 5, 10)


def bar(n, high, low, close, **kw):
    return replace(ResponseBar(str(n), "A", 101 + (n - 1)*10, 110 + (n - 1)*10,
          110 + (n - 1)*10, 11 + (n - 1)*10, 20 + (n - 1)*10, high, low, close, True), **kw)


def measure(bars, d=D, p=P, watermark=140, reason="WINDOW_END"):
    return measure_synthetic_response(d, bars, policy=p, observed_until_ns=watermark,
                                      termination_reason=reason, purpose="synthetic")


def test_response_from_decision_not_band_edge():
    row = measure([bar(1, 120, 112, 118)])["results"][0]
    assert row["signed_close_response_exit_ticks"] == 5
    assert row["signed_close_response_normalized"] == .5


def test_no_invented_fill_or_profit():
    r = measure([bar(1, 120, 112, 118)])
    assert not r["entry_fill_or_pnl_computed"] and not r["new_market_outcomes_computed"]


def test_both_barriers_same_bar_preserved_unordered():
    row = measure([bar(1, 120, 105, 118)])["results"][0]
    assert row["first_distance_observation"]["classification"] == "BOTH_SAME_BAR_UNORDERED"


def test_exit_first_not_changed_by_later_reverse():
    row = measure([bar(1, 120, 112, 118), bar(2, 119, 100, 104)])["results"][0]
    assert row["first_distance_observation"]["classification"] == "EXIT_SIDE_FIRST_OBSERVED"
    assert row["signed_close_response_exit_ticks"] == -9


def test_opposite_side_first():
    row = measure([bar(1, 114, 105, 107)])["results"][0]
    assert row["first_distance_observation"]["classification"] == "OPPOSITE_SIDE_FIRST_OBSERVED"


def test_downward_exit_orientation():
    row = measure([bar(1, 114, 105, 107)], d=replace(D, exit_side=-1))["results"][0]
    assert row["signed_close_response_exit_ticks"] == 6


def test_failed_break_not_automatically_flipped_to_win():
    a = measure([bar(1, 120, 112, 118)])
    b = measure([bar(1, 120, 112, 118)], d=replace(D, branch="FAILED_BREAK_TRIGGER"))
    assert a["results"] == b["results"]


def test_right_censoring_not_zero():
    row = measure([bar(1, 120, 112, 118)], watermark=115)["results"][0]
    assert row["status"] == "RIGHT_CENSORED"
    assert row["signed_close_response_exit_ticks"] is None
    assert row["observed_prefix_signed_close_exit_ticks"] == 5
    assert row["distance_status"] == "OBSERVED"


def test_censored_no_hit_unknown_not_no_hit():
    row = measure([bar(1, 114, 112, 113)], watermark=115)["results"][0]
    assert row["distance_status"] == "UNKNOWN_OR_CENSORED"


def test_no_completed_bar_not_zero():
    row = measure([])["results"][0]
    assert row["status"] == "NO_POSTDECISION_COMPLETED_BAR"
    assert row["signed_close_response_exit_ticks"] is None


def test_clock_deadlines_not_bar_counts():
    rows = measure([bar(1, 120, 112, 118), bar(3, 121, 115, 120)])["results"]
    assert [r["completed_bars_used"] for r in rows] == [1, 2]
    assert rows[0]["last_close_staleness_ns"] == 10


def test_latency_does_not_backfill_unavailable_close():
    rows = measure([bar(1, 120, 112, 118, available_ns=130)])["results"]
    assert rows[0]["last_completed_bar_id"] is None
    assert rows[1]["signed_close_response_exit_ticks"] == 5


def test_partial_bar_not_used_for_predecision_extreme():
    row = measure([bar(1, 999, 0, 118, start_ns=90, start_sequence=9)])["results"][0]
    assert row["status"] == "UNKNOWN_PARTIAL_POSTDECISION_BAR"
    assert row["observed_prefix_max_exit_excursion_ticks"] is None


def test_session_boundary_not_negative_outcome():
    row = measure([bar(1, 120, 112, 118, session="B")])["results"][0]
    assert row["status"] == "SESSION_BOUNDARY" and row["signed_close_response_exit_ticks"] is None


def test_declared_session_end_censored():
    assert measure([], watermark=115, reason="SESSION_END")["results"][0]["status"] == "SESSION_BOUNDARY"


def test_history_gap_unknown():
    row = measure([bar(1, 120, 112, 118, history_complete=False)])["results"][0]
    assert row["status"] == "UNKNOWN_HISTORY"


def test_duplicate_future_bar_rejected():
    with pytest.raises(ValueError, match="repeated"):
        measure([bar(1, 120, 112, 118)] * 2)


def test_decision_bar_excluded():
    with pytest.raises(ValueError, match="decision bar"):
        measure([bar(1, 120, 112, 118, bar_id="D")])


def test_predecision_bar_rejected():
    with pytest.raises(ValueError, match="predecision"):
        measure([bar(1, 120, 112, 118, start_ns=70, end_ns=80, available_ns=80)])


def test_future_beyond_window_does_not_change_result():
    tape = [bar(1, 120, 112, 118)]
    assert measure(tape) == measure(tape + [bar(10, 999, 0, 1)])


def test_policy_no_duplicate_horizons():
    with pytest.raises(ValueError, match="explicit"):
        measure([], p=replace(P, horizons_ns=(20, 20)))


def test_market_rejected():
    with pytest.raises(ValueError, match="STOP"):
        measure_synthetic_response(D, [], policy=P, observed_until_ns=140,
                                   termination_reason="WINDOW_END", purpose="research")


def test_unknown_watermark_rejected():
    with pytest.raises(ValueError, match="watermark"):
        measure([], watermark=99)


def test_decision_derived_from_observed_trace():
    band = Band("SYNTHETIC-BAND", 100, 110, -1, -1)
    bars = [Bar(str(n), "A", n*10, n*10, n, h, l, c, True)
            for n, (h,l,c) in enumerate([(109,101,105),(115,111,114),(113,109,112),(114,111,113)])]
    trace = classify_synthetic_reaction(band, bars, policy=Policy("SYNTHETIC",0,1,10,"inside",
                "strictly_later_bar","terminate_unknown"), cohort="zone_candidate", purpose="synthetic")
    decision = decision_from_synthetic_trace(band, bars, trace)
    assert decision.close_ticks == 113 and decision.available_ns == 30


def test_touch_without_confirmation_cannot_be_measurement_origin():
    with pytest.raises(ValueError, match="confirmation"):
        decision_from_synthetic_trace(Band("B",100,110,-1,-1), [],
                                     {"scope":"SYNTHETIC_CLASSIFICATION_ONLY","state":"RETEST_OBSERVED"})


def test_bar_crossing_deadline_not_used_for_envelope():
    row = measure([bar(1, 999, 0, 118, end_ns=125, available_ns=125)])["results"][0]
    assert row["observed_prefix_max_exit_excursion_ticks"] is None


def test_independent_excursion_arithmetic():
    row = measure([bar(1, 120, 112, 118)])["results"][0]
    assert row["observed_prefix_max_exit_excursion_ticks"] == 120 - 113
    assert row["observed_prefix_max_opposite_excursion_ticks"] == 113 - 112


def test_source_order_before_decision_not_hidden_by_later_clock():
    row = measure([bar(1, 999, 0, 118, start_sequence=9)])["results"][0]
    assert row["status"] == "UNKNOWN_PARTIAL_POSTDECISION_BAR"
