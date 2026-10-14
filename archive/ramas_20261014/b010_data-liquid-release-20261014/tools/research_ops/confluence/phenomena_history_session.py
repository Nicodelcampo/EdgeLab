"""New history experiment's preparation; existing frozen pilots unchanged.

Feature history is updated BEFORE response.label, and before ANY filtering
based on a future outcome. Market calls only from a bounded Kaggle runner.
Returns PRIVATE arrays; exported callers must whitelist aggregate summaries.
"""
import math
import time
import numpy as np
from .asof_intersections import Clock
from .phenomena import ClockMeasurements
from .phenomena_response import SecondsResponse
from .phenomena_models import state, features, phase_key
from .phenomena_science_pilot import USABLE, add
from .phenomena_history import CausalHistory, HISTORY_NAMES


def session_data(st, date, plan, calibration, started):
    dates = tuple(plan["research_dates"])
    tape = st.ticks
    measurements = ClockMeasurements(
        max_ticks=plan["max_session_ticks"], max_anchors=plan["max_anchors"],
        wall_seconds=plan["wall_seconds"], max_gap_ns=plan["max_gap_ns"])
    response = SecondsResponse(
        tape.ts_ns, tape.sequence, tape.bid_ticks, tape.ask_ticks,
        max_ticks=plan["max_session_ticks"], max_anchors=plan["max_anchors"],
        max_scan_elements=plan["max_scan_elements_per_session"],
        wall_seconds=plan["wall_seconds"], max_gap_ns=plan["max_gap_ns"])
    history = CausalHistory(research_dates=dates, max_anchors=plan["max_anchors"])
    bases, capacities, extras, targets, keys, states, thin, clocks = ([] for _ in range(8))
    census, excluded, labels = {}, {}, {}
    transitions = {"A_TO_E": 0, "E_TO_A": 0}
    observed = 0
    for row in measurements.measure(
            tape.ts_ns, tape.sequence, tape.price_ticks, tape.volume,
            tape.bid_ticks, tape.ask_ticks, trade_date=date):
        if time.monotonic() - started > plan["wall_seconds"]:
            raise TimeoutError("whole history experiment wall cap")
        observed += 1
        s = state(row, calibration, research_dates=dates)["state"]
        add(census, s)
        ctx = row["windows"]["60"]["current"]
        current = None
        barrier = None
        if s != "UNKNOWN" and ctx["status"] == "OBSERVABLE":
            barrier = max(4, math.ceil(.5 * ctx["range_midpoint_ticks"]))
            current, _ = features(row, barrier, research_dates=dates)
        direction = row["windows"]["20"]["direction_from_prior"]
        direction = direction if type(direction) is int and direction in (-1, 1) else None
        clock = Clock(row["timestamp_ns"], row["sequence"])
        # DO NOT move this below label(), continue, or the scoring filter.
        prefix = history.push(clock, date, s, direction=direction, continuous=current)
        transition = prefix["path"]["transition_observed_now"]
        if transition is not None:
            transitions[transition] += 1
        if s == "UNKNOWN":
            add(excluded, "CLASSIFICATION_UNKNOWN")
            continue
        if current is None:
            add(excluded, "ORIGIN_60S_CONTEXT_UNKNOWN")
            continue
        # Clock-only purge/embargo AFTER advancing all observed history and
        # BEFORE computing any outcome. Existing callers without bounds unchanged.
        bound = plan.get("scoring_bounds", {}).get(date)
        if bound is not None and not bound["lower_ns"] <= clock.ns < bound["upper_ns"]:
            add(excluded, "CLOCK_ONLY_PURGE_EMBARGO")
            continue
        i = int(np.searchsorted(tape.sequence, row["sequence"]))
        if (i >= len(tape.sequence) or int(tape.sequence[i]) != row["sequence"] or
                int(tape.ts_ns[i]) != row["timestamp_ns"]):
            raise ValueError("feature/anchor identity")
        label = response.label(i, direction=direction, distance_ticks=barrier)
        add(labels, label["status"])
        if not label["usable"]:
            add(excluded, label["status"])
            continue
        if label["status"] not in USABLE:
            raise ValueError("fixed usable first-passage labels")
        bases.append(prefix["base"]); capacities.append(prefix["capacity"])
        extras.append(prefix["extras"]); targets.append(USABLE.index(label["status"]))
        keys.append(phase_key(row, research_dates=dates)); states.append(s)
        thin.append(prefix["retained_for_60s_sensitivity"]); clocks.append(clock)
    if observed != history.count or observed != sum(census.values()) or observed != len(targets) + sum(excluded.values()):
        raise ValueError("all observed history/scored population crossfoot")
    n = len(targets)
    summary = {
        "trade_date": date, "ticks": len(tape.ts_ns), "observed_anchors": observed,
        "history_updates": history.count, "common_usable_anchors": n,
        "state_counts_before_labels": census, "excluded_counts": excluded,
        "response_counts": labels, "observed_transition_counts_before_labels": transitions,
        "thin_60s_usable_anchors": sum(thin), "measurement": measurements.summary,
        "response_scanned_elements": response.scanned,
        "history_advanced_before_outcomes": True, "raw_exported": False,
        "clock_only_purge_embargo_applied": date in plan.get("scoring_bounds", {}),
    }
    return {
        "base": np.asarray(bases, float).reshape(n, len(HISTORY_NAMES)),
        "capacity": np.asarray(capacities, float).reshape(n, 6),
        "extras": np.asarray(extras, float).reshape(n, 6),
        "y": np.asarray(targets, int), "keys": np.asarray(keys), "states": np.asarray(states),
        "thin_60s": np.asarray(thin, bool), "clocks": tuple(clocks), "summary": summary,
    }