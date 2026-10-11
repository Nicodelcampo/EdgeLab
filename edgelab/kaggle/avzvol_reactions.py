"""Causal reaction classifier prototype. Synthetic tests only, no market loader.

A trigger is an observation, not a profitable entry or an outcome. Band and
policy are supplied explicitly; no research defaults or threshold search.
"""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Band:
    snapshot_id: str
    low: int
    high: int
    known_ns: int
    known_sequence: int


@dataclass(frozen=True)
class Bar:
    bar_id: str
    session: str
    end_ns: int
    available_ns: int
    end_sequence: int
    high: int
    low: int
    close: int
    history_complete: bool


@dataclass(frozen=True)
class Policy:
    policy_id: str
    buffer_ticks: int
    confirmation_closes: int
    max_bars_after_exit: int
    boundary_close: Literal["inside", "unclassified"]
    confirmation_order: Literal["strictly_later_bar"]
    session_boundary: Literal["terminate_unknown"]


def _integer(value):
    return type(value) is int


def classify_synthetic_reaction(band: Band, bars: list[Bar], *, policy: Policy,
                                cohort: str, purpose: str) -> dict:
    """Return prefix-only first interaction classification, never future response.

    Counts are synthetic policy choices, not approved scientific parameters.
    Exact edge intersection is the prototype retest observation. A later-bar
    close is required by this conservative prototype policy; it does not
    reconstruct multiple intrabar traversals or test immediate confirmation.
    Both cohorts use the same algorithm; control eligibility is NOT certified.
    """
    if purpose != "synthetic":
        raise ValueError("STOP: market execution not authorized or implemented")
    if cohort not in ("zone_candidate", "geometry_control_candidate"):
        raise ValueError("unknown cohort")
    if not band.snapshot_id or not all(_integer(x) for x in
            (band.low, band.high, band.known_ns, band.known_sequence)) or band.low > band.high:
        raise ValueError("invalid frozen band")
    if (not policy.policy_id or not all(_integer(x) for x in
        (policy.buffer_ticks, policy.confirmation_closes, policy.max_bars_after_exit))
        or policy.buffer_ticks < 0 or policy.confirmation_closes < 1
        or policy.max_bars_after_exit < 1 or policy.boundary_close not in ("inside", "unclassified")
        or policy.confirmation_order != "strictly_later_bar"
        or policy.session_boundary != "terminate_unknown"):
        raise ValueError("explicit supported policy required")
    events = []
    state = "NO_OBSERVED_EXIT"
    side = 0
    exit_index = None
    retest_index = None
    streak_state = None
    streak = 0
    prior = None
    ids = set()
    first_session = None
    inside_baseline_seen = False

    def emit(name, bar):
        events.append({"state": name, "bar_id": bar.bar_id,
                       "available_ns": bar.available_ns, "end_sequence": bar.end_sequence,
                       "exit_side_observed": side, "band_snapshot_id": band.snapshot_id})

    for index, bar in enumerate(bars):
        if (not bar.bar_id or not bar.session or type(bar.history_complete) is not bool
            or not all(_integer(x) for x in (bar.end_ns, bar.available_ns, bar.end_sequence,
                                           bar.high, bar.low, bar.close))
            or bar.available_ns < bar.end_ns or not bar.low <= bar.close <= bar.high):
            raise ValueError("invalid completed bar")
        key = (bar.available_ns, bar.end_sequence)
        if bar.bar_id in ids or (prior is not None and
                (key <= prior or bar.end_sequence <= prior[1])):
            raise ValueError("bars must have unique identities and increasing source order")
        ids.add(bar.bar_id)
        prior = key
        # Snapshot must exist by bar completion; later arrival cannot backfill it.
        if (bar.end_ns, bar.end_sequence) <= (band.known_ns, band.known_sequence):
            raise ValueError("band was not known before this completed bar")
        if not bar.history_complete:
            state = "UNKNOWN_HISTORY"
            emit(state, bar)
            break
        if first_session is None:
            first_session = bar.session
        elif first_session != bar.session:
            state = "UNKNOWN_SESSION_BOUNDARY"
            emit(state, bar)
            break
        if exit_index is not None and index - exit_index > policy.max_bars_after_exit:
            state = "UNCONFIRMED_TIMEOUT"
            emit(state, bar)
            break
        close_side = (1 if bar.close > band.high + policy.buffer_ticks else
                      -1 if bar.close < band.low - policy.buffer_ticks else 0)
        inside = band.low < bar.close < band.high
        if policy.boundary_close == "inside":
            inside = band.low <= bar.close <= band.high
        if exit_index is None:
            if not inside_baseline_seen:
                if inside:
                    inside_baseline_seen = True
                    state = "NO_OBSERVED_EXIT"
                    emit("INSIDE_BASELINE_OBSERVED", bar)
                elif close_side:
                    state = "OUTSIDE_WITHOUT_OBSERVED_EXIT"
                    emit(state, bar)
                continue
            if close_side:
                side = close_side
                exit_index = index
                state = "EXIT_OBSERVED"
                emit(state, bar)
            continue
        if retest_index is None:
            edge = band.high if side == 1 else band.low
            if bar.low <= edge <= bar.high:
                retest_index = index
                state = "RETEST_OBSERVED"
                emit(state, bar)
                # Explicit later-bar policy; not a claim that immediate
                # completed-bar confirmation is inherently unobservable.
                continue
            if close_side == -side:
                state = "OPPOSITE_EXIT_WITHOUT_RETEST_OBSERVED"
                emit(state, bar)
                break
            continue
        observed = ("CONTINUATION_TRIGGER" if close_side == side else
                    "FAILED_BREAK_TRIGGER" if inside else
                    "OPPOSITE_EXIT_AFTER_RETEST" if close_side == -side else None)
        if observed == "OPPOSITE_EXIT_AFTER_RETEST":
            state = observed
            emit(state, bar)
            break
        if observed is None:
            streak = 0
            streak_state = None
            continue
        streak = streak + 1 if streak_state == observed else 1
        streak_state = observed
        if streak >= policy.confirmation_closes:
            state = observed
            emit(state, bar)
            break
    return {"scope": "SYNTHETIC_CLASSIFICATION_ONLY", "cohort": cohort,
            "policy_id": policy.policy_id, "band_snapshot_id": band.snapshot_id,
            "state": state, "events": events, "future_response_computed": False,
            "control_eligibility_certified": False, "entry_rule_validated": False,
            "market_execution_authorized": False}
