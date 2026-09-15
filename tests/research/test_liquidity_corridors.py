from __future__ import annotations

import pytest

from edgelab.research.liquidity_corridors import (
    CorridorContractError, CorridorDefinition, CorridorSignal, MatchObservation,
    MatchedPair, TradeTick, campaign_audit, deterministic_matched_pairs,
    holm_adjust, ohlc_bar_touch_state, paired_session_inference, resolve_first_passage,
    select_non_overlapping, validate_signal,
)


def signal(**changes):
    base = dict(
        event_id="e1", root="6E", contract="6EM6", trade_date="2026-06-15",
        regime_id="r1", session_id="s1", direction=1, created_ns=10,
        available_ns=20, decision_ns=20, reference_tick=100,
        forward_density=0.20, backstop_density=0.80, width_ticks=6,
        time_bucket="RTH_OPEN", volatility_bin="V2", impulse_bin="I1",
    )
    base.update(changes)
    return CorridorSignal(**base)


def ticks(prices):
    return [TradeTick(21 + i, p, "6EM6", "2026-06-15", "r1", i) for i, p in enumerate(prices)]


def test_definition_is_frozen_and_boundary_inclusive():
    d = CorridorDefinition(0.28, 0.70, 4, 7)
    assert d.qualifies(forward_density=0.28, backstop_density=0.70, width_ticks=7)
    assert not d.qualifies(forward_density=0.281, backstop_density=0.70, width_ticks=7)


def test_rejects_lookahead_and_holdout():
    with pytest.raises(CorridorContractError, match="not yet available"):
        validate_signal(signal(available_ns=21, decision_ns=20))
    with pytest.raises(CorridorContractError, match="holdout"):
        validate_signal(signal(trade_date="2026-07-01"))


def test_non_overlap_is_deterministic_and_outcome_free():
    xs = [signal(event_id="b", decision_ns=25), signal(event_id="a", decision_ns=20),
          signal(event_id="c", decision_ns=31)]
    kept = select_non_overlapping(xs, cooldown_ns=10)
    assert [x.event_id for x in kept] == ["a", "c"]


def test_first_passage_enters_after_decision_and_preserves_tick_order():
    out = resolve_first_passage(signal(), ticks([100, 99, 102, 104]),
                                target_ticks=4, stop_ticks=3, horizon_ns=100,
                                friction_ticks_round_turn=1.5)
    assert out.status == "TARGET"
    assert out.entry_ns == 21
    assert out.gross_ticks == 4
    assert out.net_ticks == 2.5
    assert out.net_r == pytest.approx(2.5 / 3)


def test_first_passage_stop_wins_when_seen_first():
    out = resolve_first_passage(signal(), ticks([100, 97, 105]),
                                target_ticks=4, stop_ticks=3, horizon_ns=100,
                                friction_ticks_round_turn=0)
    assert out.status == "STOP"
    assert out.gross_ticks == -3


def test_no_same_tick_entry_outcome_and_no_bar_ambiguity():
    out = resolve_first_passage(signal(), ticks([100]), target_ticks=1, stop_ticks=1,
                                horizon_ns=100, friction_ticks_round_turn=0)
    assert out.status == "TIMEOUT"
    assert out.gross_ticks == 0


def test_ohlc_same_bar_is_explicitly_ambiguous():
    assert ohlc_bar_touch_state(direction=1, high_tick=105, low_tick=96,
                                entry_tick=100, target_ticks=4, stop_ticks=3) == "AMBIGUOUS_BOTH"


def test_regime_boundary_fails_closed():
    bad = [TradeTick(21, 100, "6EM6", "2026-06-15", "r1"),
           TradeTick(22, 101, "6EU6", "2026-06-15", "r2")]
    with pytest.raises(CorridorContractError, match="boundary"):
        resolve_first_passage(signal(), bad, target_ticks=4, stop_ticks=3,
                              horizon_ns=100, friction_ticks_round_turn=0)


def obs(event_id, is_candidate, score, net_r, session="s1", vol="V2"):
    return MatchObservation(event_id, session, "6EM6", 1, "OPEN", vol, "I1", "D1",
                            score, net_r, is_candidate)


def test_matching_is_exact_strata_nearest_and_without_replacement():
    pairs = deterministic_matched_pairs([
        obs("c1", True, 0.10, 1.0), obs("c2", True, 0.12, 0.5),
        obs("p1", False, 0.11, 0.0), obs("p2", False, 0.30, -0.5),
        obs("wrong", False, 0.10, 9.0, vol="V9"),
    ])
    assert [(p.candidate_id, p.control_id) for p in pairs] == [("c1", "p1"), ("c2", "p2")]


def test_matching_caliper_abstains_instead_of_forcing_bad_match():
    pairs = deterministic_matched_pairs([obs("c", True, 0.1, 1), obs("p", False, 0.9, 0)],
                                        score_caliper=0.2)
    assert pairs == []


def test_session_inference_uses_sessions_not_raw_events():
    pairs = [MatchedPair(f"c{i}", f"p{i}", f"s{i // 2}", 0.5) for i in range(40)]
    inf = paired_session_inference(pairs, n_resamples=1000, seed=7)
    assert inf.n_pairs == 40
    assert inf.n_sessions == 20
    assert inf.mean_delta_net_r == pytest.approx(0.5)
    assert inf.ci_low > 0


def test_holm_adjustment_is_monotone_in_sorted_p_values():
    adjusted = holm_adjust({"a": 0.01, "b": 0.03, "c": 0.50})
    assert adjusted == {"a": 0.03, "b": 0.06, "c": 0.5}


def test_audit_blocks_when_placebo_beats_candidate_or_ledger_is_short():
    findings = campaign_audit(candidate_mean_net_r=0.09, control_mean_net_r=0.12,
                              n_declared_variants=2, n_reported_variants=3,
                              inference=None)
    assert "FAIL_NO_INCREMENTAL_EDGE_OVER_MATCHED_CONTROL" in findings
    assert "FAIL_HYPOTHESIS_BUDGET_UNDERCOUNTS_REPORTED_VARIANTS" in findings
    assert "ABSTAIN_NO_SESSION_LEVEL_INFERENCE" in findings
