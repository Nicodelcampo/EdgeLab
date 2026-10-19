# -*- coding: utf-8 -*-
"""F2.9 labels and canonical probe side. Target-free."""
from __future__ import annotations

MIN_SESSIONS = 30
MIN_RESOLVED = 200


def support_ok(n_sessions: int, n_resolved: int) -> bool:
    return int(n_sessions) >= MIN_SESSIONS and int(n_resolved) >= MIN_RESOLVED


def wick_fracs(high: int, low: int, close: int, open_: int | None = None):
    rng = max(1, int(high) - int(low))
    upper = (int(high) - int(close)) / rng
    lower = (int(close) - int(low)) / rng
    close_loc = (int(close) - int(low)) / rng
    return dict(range_ticks=rng, upper_wick_frac=upper, lower_wick_frac=lower, close_loc=close_loc)


def probe_side(high: int, low: int, close: int) -> str:
    w = wick_fracs(high, low, close)
    return "bull" if w["upper_wick_frac"] >= w["lower_wick_frac"] else "bear"


def probe_interval(close: int, side: str, d: int = 2, width: int = 1) -> tuple[int, int]:
    c = int(close)
    if side == "bull":
        lo = c + int(d)
        return lo, lo + int(width) - 1
    hi = c - int(d)
    return hi - int(width) + 1, hi


def _ci_pos(block: dict) -> bool:
    return float(block.get("ci95_lower", 0)) > 0


def _ci_zero(block: dict) -> bool:
    return float(block.get("ci95_lower", 1)) <= 0 <= float(block.get("ci95_upper", -1))


def decide_labels(report: dict) -> list[str]:
    labels = []
    k0 = report.get("rungs", {}).get("K0", {})
    s1 = report.get("rungs", {}).get("S1", {})
    f0 = report.get("rungs", {}).get("F0", {})
    n0 = report.get("rungs", {}).get("N0", {})
    k0_s1 = report.get("contrasts", {}).get("K0_minus_S1", {})
    k0_n0 = report.get("contrasts", {}).get("K0_minus_N0", {})
    f0_s1 = report.get("contrasts", {}).get("F0_minus_S1", {})
    k0_f0 = report.get("contrasts", {}).get("K0_minus_F0", {})
    zone_res = report.get("zone_residual", {})
    persist = report.get("persistence", {})

    s1_ok = support_ok(s1.get("n_sessions", 0), s1.get("n_resolved", 0))
    k0_ok = support_ok(k0.get("n_sessions", 0), k0.get("n_resolved", 0))
    f0_ok = support_ok(f0.get("n_sessions", 0), f0.get("n_resolved", 0))

    if s1_ok and _ci_pos(s1) and _ci_zero(k0_s1):
        labels.append("OPEN_SIMPLE_BAR_RULE")
    if f0_ok and _ci_pos(f0) and (_ci_zero(s1) or (_ci_pos(f0_s1) and _ci_zero(k0_f0))):
        labels.append("OPEN_FOOTPRINT_OBJECT")
    if support_ok(zone_res.get("n_sessions", 0), zone_res.get("n_resolved", 0)) and _ci_pos(zone_res):
        labels.append("OPEN_ZONE_RESIDUAL")

    plus1 = persist.get("+1", {})
    plus2 = persist.get("+2", {})
    if (support_ok(plus1.get("n_sessions", 0), plus1.get("n_resolved", 0)) and _ci_pos(plus1)) or (
        support_ok(plus2.get("n_sessions", 0), plus2.get("n_resolved", 0)) and _ci_pos(plus2)
    ):
        labels.append("OPEN_REGIME_WINDOW")
    elif (k0_ok and _ci_pos(k0) or s1_ok and _ci_pos(s1)) and _ci_zero(plus1) and _ci_zero(plus2):
        labels.append("OPEN_SINGLE_BAR_STAMP")

    if k0_ok and _ci_pos(k0_s1) and _ci_pos(k0_n0):
        labels.append("KEEP_BT2_AS_DETECTOR")

    opens = [x for x in labels if x.startswith("OPEN_") or x.startswith("KEEP_")]
    if not opens and report.get("underpowered"):
        labels.append("CONTINUE_AMBIGUOUS")
    elif not opens:
        labels.append("CLOSE_BAR_OBJECT")
    return labels
