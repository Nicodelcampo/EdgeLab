"""Synthetic non-economic response from an observed confirmation, no loader.

Endpoints are completed-bar observations as-of explicit clock deadlines, not
continuous tick-path extremes or executions. No market defaults or inference.
"""
from dataclasses import dataclass
from .avzvol_reactions import Band, Bar


@dataclass(frozen=True)
class Decision:
    bar_id: str
    band_snapshot_id: str
    trigger_policy_id: str
    session: str
    available_ns: int
    end_sequence: int
    close_ticks: int
    exit_side: int
    branch: str


@dataclass(frozen=True)
class ResponseBar:
    bar_id: str
    session: str
    start_ns: int
    end_ns: int
    available_ns: int
    start_sequence: int
    end_sequence: int
    high_ticks: int
    low_ticks: int
    close_ticks: int
    history_complete: bool


@dataclass(frozen=True)
class ResponsePolicy:
    policy_id: str
    horizons_ns: tuple[int, ...]
    distance_ticks: int
    normalizer_ticks: int


def _int(x):
    return type(x) is int


def decision_from_synthetic_trace(band: Band, bars: list[Bar], trace: dict) -> Decision:
    if trace.get("scope") != "SYNTHETIC_CLASSIFICATION_ONLY" or trace.get("state") not in (
            "CONTINUATION_TRIGGER", "FAILED_BREAK_TRIGGER"):
        raise ValueError("an observed synthetic confirmation is required")
    event = trace["events"][-1]
    hits = [b for b in bars if b.bar_id == event["bar_id"]]
    if len(hits) != 1:
        raise ValueError("decision bar identity is missing or ambiguous")
    bar = hits[0]
    if (event["band_snapshot_id"] != band.snapshot_id or
        trace["band_snapshot_id"] != band.snapshot_id or
        event["available_ns"] != bar.available_ns or
        event["end_sequence"] != bar.end_sequence or
        event["state"] != trace["state"] or not bar.history_complete):
        raise ValueError("decision trace identity mismatch")
    return Decision(bar.bar_id, band.snapshot_id, trace["policy_id"], bar.session,
                    bar.available_ns, bar.end_sequence, bar.close,
                    event["exit_side_observed"], trace["state"])


def measure_synthetic_response(decision: Decision, bars: list[ResponseBar], *,
        policy: ResponsePolicy, observed_until_ns: int, termination_reason: str,
        purpose: str) -> dict:
    if purpose != "synthetic":
        raise ValueError("STOP: new market outcomes not authorized or implemented")
    if (not decision.bar_id or not decision.band_snapshot_id or not decision.trigger_policy_id
        or not decision.session or not all(_int(x) for x in (decision.available_ns,
            decision.end_sequence, decision.close_ticks, decision.exit_side))
        or decision.exit_side not in (-1, 1)
        or decision.branch not in ("CONTINUATION_TRIGGER", "FAILED_BREAK_TRIGGER")):
        raise ValueError("invalid observed decision")
    if (not policy.policy_id or not isinstance(policy.horizons_ns, tuple)
        or not policy.horizons_ns or any(not _int(h) or h <= 0 for h in policy.horizons_ns)
        or tuple(sorted(set(policy.horizons_ns))) != policy.horizons_ns
        or not _int(policy.distance_ticks) or policy.distance_ticks <= 0
        or not _int(policy.normalizer_ticks) or policy.normalizer_ticks <= 0):
        raise ValueError("explicit unique positive response policy required")
    if (not _int(observed_until_ns) or observed_until_ns < decision.available_ns
        or termination_reason not in ("WINDOW_END", "SESSION_END", "HISTORY_GAP")):
        raise ValueError("explicit observation watermark and termination required")
    # Validate only the requested analysis window. Later bars cannot change it.
    relevant = [b for b in bars if b.start_ns <= decision.available_ns + policy.horizons_ns[-1]]
    prior = None
    identities = set()
    for b in relevant:
        if (not b.bar_id or not b.session or type(b.history_complete) is not bool or
            not all(_int(x) for x in (b.start_ns, b.end_ns, b.available_ns,
                b.start_sequence, b.end_sequence, b.high_ticks, b.low_ticks, b.close_ticks))
            or not b.start_ns <= b.end_ns <= b.available_ns
            or b.start_sequence > b.end_sequence
            or not b.low_ticks <= b.close_ticks <= b.high_ticks):
            raise ValueError("invalid response bar")
        if b.bar_id == decision.bar_id or b.bar_id in identities:
            raise ValueError("decision bar or repeated bar cannot be a future observation")
        if prior and (b.start_sequence <= prior.end_sequence or
                      b.start_ns < prior.end_ns or b.available_ns < prior.available_ns):
            raise ValueError("response bars must be nonoverlapping and ordered")
        if b.end_sequence <= decision.end_sequence or b.end_ns < decision.available_ns:
            raise ValueError("predecision response data")
        identities.add(b.bar_id)
        prior = b
    outputs = []
    for h in policy.horizons_ns:
        deadline = decision.available_ns + h
        coverage = min(deadline, observed_until_ns)
        status = "COMPLETE_CLOCK_WINDOW"
        if deadline > observed_until_ns:
            status = {"WINDOW_END": "RIGHT_CENSORED", "SESSION_END": "SESSION_BOUNDARY",
                      "HISTORY_GAP": "UNKNOWN_HISTORY"}[termination_reason]
        used = []
        issue = None
        for b in relevant:
            if b.start_ns > coverage:
                break
            if b.session != decision.session:
                issue = "SESSION_BOUNDARY"
                break
            if not b.history_complete:
                issue = "UNKNOWN_HISTORY"
                break
            if b.start_ns < decision.available_ns or b.start_sequence <= decision.end_sequence:
                issue = "UNKNOWN_PARTIAL_POSTDECISION_BAR"
                break
            if b.available_ns <= coverage:
                used.append(b)
        if issue:
            status = issue
        if not used and status == "COMPLETE_CLOCK_WINDOW":
            status = "NO_POSTDECISION_COMPLETED_BAR"
        origin = decision.close_ticks
        side = decision.exit_side
        first = None
        max_exit = None
        max_opposite = None
        for b in used:
            toward = (b.high_ticks - origin) if side == 1 else (origin - b.low_ticks)
            opposite = (origin - b.low_ticks) if side == 1 else (b.high_ticks - origin)
            max_exit = max(0, toward, max_exit or 0)
            max_opposite = max(0, opposite, max_opposite or 0)
            if first is None and (toward >= policy.distance_ticks or opposite >= policy.distance_ticks):
                first = {"bar_id": b.bar_id, "available_ns": b.available_ns,
                         "classification": ("BOTH_SAME_BAR_UNORDERED" if toward >= policy.distance_ticks
                             and opposite >= policy.distance_ticks else "EXIT_SIDE_FIRST_OBSERVED"
                             if toward >= policy.distance_ticks else "OPPOSITE_SIDE_FIRST_OBSERVED")}
        full = status == "COMPLETE_CLOCK_WINDOW"
        last = used[-1] if used else None
        prefix_close = side * (last.close_ticks - origin) if last else None
        outputs.append({"horizon_ns": h, "deadline_ns": deadline, "status": status,
            "completed_bars_used": len(used), "last_completed_bar_id": last.bar_id if last else None,
            "last_close_staleness_ns": deadline - last.end_ns if last else None,
            "signed_close_response_exit_ticks": prefix_close if full else None,
            "signed_close_response_normalized": prefix_close / policy.normalizer_ticks if full else None,
            "observed_prefix_signed_close_exit_ticks": prefix_close,
            "observed_prefix_max_exit_excursion_ticks": max_exit,
            "observed_prefix_max_opposite_excursion_ticks": max_opposite,
            "first_distance_observation": first,
            "distance_status": "OBSERVED" if first else "NO_COMPLETED_BAR_HIT_OBSERVED" if full
                                  else "UNKNOWN_OR_CENSORED"})
    return {"scope": "SYNTHETIC_NON_ECONOMIC_RESPONSE_ONLY", "decision_bar_id": decision.bar_id,
            "decision_origin_close_ticks": decision.close_ticks,
            "decision_available_ns": decision.available_ns, "exit_side_observed": decision.exit_side,
            "branch": decision.branch, "band_snapshot_id": decision.band_snapshot_id,
            "trigger_policy_id": decision.trigger_policy_id, "response_policy_id": policy.policy_id,
            "normalizer_ticks": policy.normalizer_ticks, "distance_ticks": policy.distance_ticks,
            "measurement_convention": "completed_bar_envelope_and_last_completed_close_asof_deadline",
            "continuous_tick_path_measured": False, "results": outputs,
            "new_market_outcomes_computed": False, "entry_fill_or_pnl_computed": False}
