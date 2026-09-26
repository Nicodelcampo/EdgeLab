# -*- coding: utf-8 -*-
"""Osler-style geometric interruption. No returns, no P&L."""
from __future__ import annotations

H_INT = 5


def classify_after_contact(anchor_tick, lo, hi, is_bull, contact_bar, close_t, high_t, low_t, n, h=H_INT):
    """Classify the path after first contact.

    through: close crosses the far edge, away from the creator close.
    bounce: an excursion of at least the zone width moves back toward the anchor.
    stay: neither happens inside the next h bars.
    """
    if contact_bar is None or contact_bar < 0:
        return "no_contact"
    width = int(hi) - int(lo)
    if width < 1:
        width = 1
    far = int(hi) if is_bull else int(lo)
    toward = -1 if is_bull else 1
    last = min(n - 1, int(contact_bar) + int(h))
    for b in range(int(contact_bar) + 1, last + 1):
        cl = int(close_t[b])
        if is_bull and cl > far:
            return "through"
        if (not is_bull) and cl < far:
            return "through"
        if is_bull and int(low_t[b]) <= int(anchor_tick) - width:
            return "bounce"
        if (not is_bull) and int(high_t[b]) >= int(anchor_tick) + width:
            return "bounce"
        _ = toward
    return "stay"
