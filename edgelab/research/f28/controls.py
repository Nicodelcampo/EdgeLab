# -*- coding: utf-8 -*-
"""Creator-bar controls. Target-free."""
from __future__ import annotations


def same_side_interval(anchor, d, width, is_bull):
    if is_bull:
        lo = int(anchor) + int(d)
        hi = lo + int(width) - 1
    else:
        hi = int(anchor) - int(d)
        lo = hi - int(width) + 1
    return lo, hi


def eligible_control(anchor, lo, hi, occupied):
    if lo > hi:
        return False
    if hi >= int(anchor) and lo <= int(anchor):
        return False
    for olo, ohi in occupied:
        if not (hi < olo or lo > ohi):
            return False
    return True


def match_nontrap_bar(candidate_bars, created_bar, occupied_by_bar):
    """Pick the closest earlier-or-equal non-trap bar by clock index."""
    if not candidate_bars:
        return None
    ordered = sorted(candidate_bars, key=lambda b: (abs(int(b) - int(created_bar)), int(b)))
    for b in ordered:
        if b != created_bar:
            return int(b)
    return None
