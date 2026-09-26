# -*- coding: utf-8 -*-
"""F2.8 labels and stratum gates. Target-free. No outcomes, no P&L."""
from __future__ import annotations

from typing import Iterable

STRATA = ("d<=2", "3<=d<=5", "d>=6")
MIN_SESSIONS = 30
MIN_RESOLVED = 200


def distance_stratum(distance_ticks: int) -> str:
    d = int(distance_ticks)
    if d <= 2:
        return "d<=2"
    if d <= 5:
        return "3<=d<=5"
    return "d>=6"


def occupancy_union(intervals: Iterable[tuple[int, int]]) -> int:
    """Covered tick count of inclusive [lo, hi] unions."""
    ordered = sorted((int(lo), int(hi)) for lo, hi in intervals if hi >= lo)
    if not ordered:
        return 0
    total = 0
    cur_lo, cur_hi = ordered[0]
    for lo, hi in ordered[1:]:
        if lo <= cur_hi + 1:
            cur_hi = max(cur_hi, hi)
        else:
            total += cur_hi - cur_lo + 1
            cur_lo, cur_hi = lo, hi
    return total + (cur_hi - cur_lo + 1)


def isolated(zone: tuple[int, int], others: Iterable[tuple[int, int]]) -> bool:
    lo, hi = zone
    for olo, ohi in others:
        if not (ohi < lo or olo > hi):
            return False
    return True


def support_ok(n_sessions: int, n_resolved: int) -> bool:
    return int(n_sessions) >= MIN_SESSIONS and int(n_resolved) >= MIN_RESOLVED


def decide_labels(report: dict) -> list[str]:
    """Apply the preregistered F2.8 decision rules. Multiple labels may fire."""
    labels = []
    far = report.get("strata", {}).get("d>=6", {})
    near = report.get("strata", {}).get("d<=2", {})
    contrast = report.get("bt2_minus_control", {})
    occ = report.get("occupancy", {})
    holes = report.get("holes", {})
    fade = report.get("fade_cuts", {})
    interruption = report.get("interruption", {})

    far_ok = support_ok(far.get("n_sessions", 0), far.get("n_resolved", 0))
    if (
        far_ok
        and far.get("ci95_lower", 0) > 0
        and contrast.get("d>=6", {}).get("ci95_lower", 0) > 0
    ):
        labels.append("OPEN_FAR_ZONE_FAMILY")

    global_or_near_pos = (
        report.get("global", {}).get("ci95_lower", 0) > 0
        or near.get("ci95_lower", 0) > 0
    )
    contrast_zero = contrast.get("global", {}).get("ci95_lower", 1) <= 0 and contrast.get(
        "global", {}
    ).get("ci95_upper", -1) >= 0
    if global_or_near_pos and contrast_zero:
        labels.append("OPEN_BAR_CLASSIFIER")

    if occ.get("p50_visited", 0) >= 0.50 and holes.get("first_passage_edge", False):
        labels.append("OPEN_HOLE_FAMILY")

    if any(cut.get("ci95_upper", 1) < 0 and support_ok(cut.get("n_sessions", 0), cut.get("n_resolved", 0)) for cut in fade.values()):
        labels.append("OPEN_FADE_MIRROR")

    if interruption.get("ci95_lower", 0) > 0:
        labels.append("OPEN_INTERRUPTION_FAMILY")

    if occ.get("p50_visited", 0) > 0.80 or occ.get("isolated_rate", 1) < 0.10:
        labels.append("OPEN_DENSITY_FEATURES")

    opens = [x for x in labels if x.startswith("OPEN_")]
    underpowered = report.get("underpowered", False)
    if not opens and underpowered:
        labels.append("CONTINUE_AMBIGUOUS")
    elif not opens:
        labels.append("CLOSE_ZONE_ATTRACTION")
    return labels
