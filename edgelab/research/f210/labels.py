# -*- coding: utf-8 -*-
"""F2.10 labels. Target-free. Stamp is S1, not the kernel."""
from __future__ import annotations

MIN_SESSIONS = 30
MIN_RESOLVED = 200


def support_ok(n_sessions: int, n_resolved: int) -> bool:
    return int(n_sessions) >= MIN_SESSIONS and int(n_resolved) >= MIN_RESOLVED


def is_s1(range_ticks: int, upper_frac: float, lower_frac: float, volume: float, vol_median: float) -> bool:
    return (
        int(range_ticks) >= 3
        and max(float(upper_frac), float(lower_frac)) >= 0.30
        and float(volume) >= float(vol_median)
    )


def is_t1(bar_index: int, stamp_bars: set[int], session_first: int, session_last: int) -> bool:
    prev_bar = int(bar_index) - 1
    return session_first <= prev_bar <= session_last and prev_bar in stamp_bars


def _ci_pos(block: dict) -> bool:
    return float(block.get("ci95_lower", 0)) > 0


def _ci_neg(block: dict) -> bool:
    return float(block.get("ci95_upper", 1)) < 0


def _ci_zero(block: dict) -> bool:
    return float(block.get("ci95_lower", 1)) <= 0 <= float(block.get("ci95_upper", -1))


def decide_labels(report: dict) -> list[str]:
    labels = []
    arms = report.get("arms", {})
    contrasts = report.get("contrasts", {})
    t1_not = arms.get("T1_not_S1", {})
    t1_and = arms.get("T1_and_S1", {})
    t1_minus_p1 = contrasts.get("T1_not_S1_minus_P1", {})
    k0_minus_s1 = contrasts.get("T1_after_K0_minus_T1_after_S1", {})
    tm1 = arms.get("T_minus1", {})
    tm1_minus_p = contrasts.get("T_minus1_minus_P_minus1", {})

    t1_not_ok = support_ok(t1_not.get("n_sessions", 0), t1_not.get("n_resolved", 0))
    t1_and_ok = support_ok(t1_and.get("n_sessions", 0), t1_and.get("n_resolved", 0))

    if t1_not_ok and _ci_pos(t1_not) and _ci_pos(t1_minus_p1):
        labels.append("OPEN_POST_STAMP_WINDOW")
    if t1_and_ok and _ci_pos(t1_and) and _ci_zero(t1_not):
        labels.append("OPEN_CLUSTER_ONLY")
    if support_ok(k0_minus_s1.get("n_sessions", 0), k0_minus_s1.get("n_resolved", t1_not.get("n_resolved", 0))) and _ci_pos(k0_minus_s1):
        labels.append("KEEP_KERNEL_FOR_WINDOW")
    if (
        support_ok(tm1.get("n_sessions", 0), tm1.get("n_resolved", 0))
        and _ci_neg(tm1)
        and _ci_neg(tm1_minus_p)
    ):
        labels.append("OPEN_PRE_STAMP_REVERSAL")

    opens = [x for x in labels if x.startswith("OPEN_") or x.startswith("KEEP_")]
    if not opens and report.get("underpowered"):
        labels.append("CONTINUE_AMBIGUOUS")
    elif not opens:
        labels.append("CLOSE_WINDOW")
    return labels
