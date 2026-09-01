"""Exit-rule simulation for the BT2A GC/NQ SL/TP + breakeven campaign
(specs/bt2a_gc_exitlogic_sltp_breakeven_campaign_v1.draft.json,
docs/research/BT2A_NQ_SLTP_BREAKEVEN_DESIGN_V1_2026-08-31.md).

Pure mechanics only -- no real GC/NQ data touched by design. This is
target-free simulation code: given any price path (synthetic or real), it
answers "which barrier would this exit rule have hit first", nothing more.
Running it does not itself cross the STOP gate; feeding it real GC/NQ ticks
to draw a conclusion would.

Mirrors edgelab/research/bt2a_gate2_first_passage.py::first_passage's
reference-loop shape (asymmetric target_ticks/stop_ticks already covers the
REF and ASIM families unchanged) and adds the third family: BE breakeven-
trigger. On first touch of +G (trigger_ticks) in the favorable direction,
the stop moves to exact entry (scrape ~0 before costs) -- one execution per
signal, no re-entry, matching the campaign's declared mechanics.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from edgelab.research.bt2a_gate2_first_passage import _arrays, horizon_endpoint

OUTCOME_TP_FIRST = "TP_FIRST"
OUTCOME_SL_FIRST = "SL_FIRST"
OUTCOME_BE_STOP = "BE_STOP"
OUTCOME_TIMEOUT = "TIMEOUT"


@dataclass(frozen=True)
class ExitResult:
    outcome: str
    score_ticks: int  # signed R in ticks, causal: TP=+target, SL=-stop, BE=0, TIMEOUT=mark-to-market at end
    fill_idx: int
    end_idx: int
    cap_driver: str
    target_level_ticks: int
    stop_level_ticks: int
    trigger_level_ticks: int | None
    triggered: bool
    touch_idx: int | None

    def to_dict(self):
        return asdict(self)


def simulate_exit(
    price, ts, source, sessions, *,
    fill_idx, direction, target_ticks, stop_ticks,
    trigger_ticks=None, tick_cap=None, clock_cap_seconds=None,
):
    """One event, one exit. trigger_ticks=None -> REF (target_ticks==stop_ticks)
    or ASIM (target_ticks!=stop_ticks), no breakeven. trigger_ticks set ->
    BE: once price moves trigger_ticks in favor, stop becomes entry price.

    Structural constraint from the design (G < TP always): trigger_ticks
    must be strictly less than target_ticks, or this raises -- a trigger
    at or past target is a different rule, not this hypothesis.
    """
    p, t, r, s = _arrays(price, ts, source, sessions)
    i, d = int(fill_idx), int(direction)
    if d not in (-1, 1) or min(int(target_ticks), int(stop_ticks)) < 1:
        raise ValueError("invalid event")
    if trigger_ticks is not None and not (0 < int(trigger_ticks) < int(target_ticks)):
        raise ValueError("trigger_ticks must satisfy 0 < G < target_ticks")

    end, driver = horizon_endpoint(t, s, fill_idx=i, tick_cap=tick_cap, clock_cap_seconds=clock_cap_seconds)
    entry = int(p[i])
    target = entry + d * int(target_ticks)
    stop = entry - d * int(stop_ticks)
    trigger = entry + d * int(trigger_ticks) if trigger_ticks is not None else None

    triggered = False
    active_stop = stop
    for j in range(i + 1, end + 1):
        px = int(p[j])
        favorable = (px - entry) * d

        if trigger is not None and not triggered and favorable >= int(trigger_ticks):
            triggered = True
            active_stop = entry  # scrape ~0, before costs

        hit_t = px >= target if d > 0 else px <= target
        hit_s = px <= active_stop if d > 0 else px >= active_stop

        if hit_t:
            return ExitResult(OUTCOME_TP_FIRST, int(target_ticks), i, end, driver,
                               target, stop, trigger, triggered, j)
        if hit_s:
            if triggered and active_stop == entry:
                return ExitResult(OUTCOME_BE_STOP, 0, i, end, driver,
                                   target, stop, trigger, triggered, j)
            return ExitResult(OUTCOME_SL_FIRST, -int(stop_ticks), i, end, driver,
                               target, stop, trigger, triggered, j)

    mtm = int((int(p[end]) - entry) * d)
    return ExitResult(OUTCOME_TIMEOUT, mtm, i, end, driver, target, stop, trigger, triggered, None)
