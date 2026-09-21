"""Target-free causal policy engine for the YM/BigTrap2Absorption Kaggle pilot.

This module intentionally computes no PnL, returns, MFE, MAE, targets, stops,
or winner selection. Prices are integer half-ticks and tick identity is
(ts_ns, sequence). Execution remains fail-closed until custody and effective
signal semantics are resolved.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from typing import Iterable

HOLDOUT_BOUNDARY_NS = 1782856800000000000
SEMANTICS = {"M5_FORMATION", "TICK_BUCKET_FORMATION"}

@dataclass(frozen=True, order=True)
class Tick:
    ts_ns: int
    sequence: int
    price_half_ticks: int
    session_id: str

@dataclass(frozen=True)
class ZoneEvent:
    event_id: str
    instrument: str
    contract: str
    source_barspec: str
    formation_start_ns: int
    formation_end_ns: int
    available_at_ns: int
    available_sequence: int
    signal_price_half_ticks: int
    zone_lo_half_ticks: int
    zone_hi_half_ticks: int
    direction: str
    semantics: str
    indicator_parameters_hash: str
    source_data_hash: str
    code_commit: str
    session_id: str

@dataclass(frozen=True)
class Policy:
    policy_id: str
    mode: str
    wait_ticks: int = 0
    departure_ticks: int = 0
    depth: float = 0.0
    max_wait_ticks: int = 0

@dataclass(frozen=True)
class Decision:
    event_id: str
    policy_id: str
    state: str
    entry_ts_ns: int | None
    entry_sequence: int | None
    entry_price_half_ticks: int | None
    armed_ts_ns: int | None
    armed_sequence: int | None
    ticks_observed: int
    censor_reason: str | None
    trigger_ts_ns: int | None = None
    trigger_sequence: int | None = None


def canonical_hash(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(raw.encode()).hexdigest()


def _ceil_even(value: float) -> int:
    integer = math.ceil(value)
    return integer if integer % 2 == 0 else integer + 1


def _floor_even(value: float) -> int:
    integer = math.floor(value)
    return integer if integer % 2 == 0 else integer - 1


def validate_event(e: ZoneEvent, *, custody_verified: bool, semantics_resolved: bool) -> None:
    if not custody_verified:
        raise ValueError("BLOCKED_BY_CUSTODY")
    if not semantics_resolved:
        raise ValueError("BLOCKED_BY_SIGNAL_SEMANTICS")
    if e.semantics not in SEMANTICS:
        raise ValueError("unknown signal semantics")
    if e.direction not in {"long", "short"}:
        raise ValueError("direction must be long or short")
    if not e.formation_start_ns <= e.formation_end_ns <= e.available_at_ns:
        raise ValueError("formation_start <= formation_end <= available_at required")
    if e.available_at_ns >= HOLDOUT_BOUNDARY_NS:
        raise ValueError("HOLDOUT_FORBIDDEN")
    if e.zone_lo_half_ticks > e.zone_hi_half_ticks:
        raise ValueError("inverted zone")
    for field in ("indicator_parameters_hash", "source_data_hash"):
        value = getattr(e, field)
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError(f"invalid {field}")


def validate_ticks(ticks: Iterable[Tick]) -> list[Tick]:
    out = list(ticks)
    identities = [(t.ts_ns, t.sequence) for t in out]
    if identities != sorted(identities):
        raise ValueError("ticks not ordered by (ts_ns, sequence)")
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate tick identity")
    if any(t.ts_ns >= HOLDOUT_BOUNDARY_NS for t in out):
        raise ValueError("HOLDOUT_FORBIDDEN")
    return out


def policies_v1() -> list[Policy]:
    out = [Policy("P0_IMMEDIATE", "IMMEDIATE"), Policy("P1_WAIT_25", "WAIT_TICKS", wait_ticks=25), Policy("P2_WAIT_100", "WAIT_TICKS", wait_ticks=100)]
    index = 3
    for departure in (2, 4):
        for depth in (0.0, 0.5, 1.0):
            for max_wait in (250, 1000):
                out.append(Policy(f"P{index}_RETEST_D{departure}_Z{int(depth * 100)}_W{max_wait}", "RETEST", departure_ticks=departure, depth=depth, max_wait_ticks=max_wait))
                index += 1
    assert len(out) == 15
    return out


def evaluate_policy(event: ZoneEvent, ticks: Iterable[Tick], policy: Policy, *, custody_verified: bool, semantics_resolved: bool) -> Decision:
    validate_event(event, custody_verified=custody_verified, semantics_resolved=semantics_resolved)
    ordered = validate_ticks(ticks)
    available_id = (event.available_at_ns, event.available_sequence)
    eligible = [t for t in ordered if (t.ts_ns, t.sequence) > available_id and t.session_id == event.session_id]
    if not eligible:
        return Decision(event.event_id, policy.policy_id, "CENSORED", None, None, None, None, None, 0, "NO_POST_AVAILABILITY_TICK")
    if policy.mode == "IMMEDIATE":
        t = eligible[0]
        return Decision(event.event_id, policy.policy_id, "ENTERED", t.ts_ns, t.sequence, t.price_half_ticks, None, None, 1, None)
    if policy.mode == "WAIT_TICKS":
        if policy.wait_ticks < 1:
            raise ValueError("wait_ticks must be positive")
        if len(eligible) <= policy.wait_ticks:
            return Decision(event.event_id, policy.policy_id, "CENSORED", None, None, None, None, None, len(eligible), "SESSION_END_BEFORE_WAIT")
        t = eligible[policy.wait_ticks]
        return Decision(event.event_id, policy.policy_id, "ENTERED", t.ts_ns, t.sequence, t.price_half_ticks, None, None, policy.wait_ticks + 1, None)
    if policy.mode != "RETEST":
        raise ValueError("unknown policy mode")
    if policy.departure_ticks < 0 or not 0 <= policy.depth <= 1 or policy.max_wait_ticks < 1:
        raise ValueError("invalid retest policy")
    departure2 = 2 * policy.departure_ticks
    lo, hi = event.zone_lo_half_ticks, event.zone_hi_half_ticks
    raw_target = hi - policy.depth * (hi - lo) if event.direction == "long" else lo + policy.depth * (hi - lo)
    target = _ceil_even(raw_target) if event.direction == "long" else _floor_even(raw_target)
    armed_tick = None
    window = eligible[:policy.max_wait_ticks]
    for observed, tick in enumerate(window, start=1):
        price = tick.price_half_ticks
        if armed_tick is None:
            armed = price >= hi + departure2 if event.direction == "long" else price <= lo - departure2
            if armed:
                armed_tick = tick
            continue
        reached = lo <= price <= target if event.direction == "long" else target <= price <= hi
        if reached:
            if observed >= len(window):
                reason = "NO_EXECUTABLE_FILL_BEFORE_EXPIRY" if len(eligible) >= policy.max_wait_ticks else "NO_EXECUTABLE_FILL_AVAILABLE"
                return Decision(event.event_id, policy.policy_id, "CENSORED", None, None, None, armed_tick.ts_ns, armed_tick.sequence, observed, reason, trigger_ts_ns=tick.ts_ns, trigger_sequence=tick.sequence)
            fill = window[observed]
            return Decision(event.event_id, policy.policy_id, "ENTERED", fill.ts_ns, fill.sequence, fill.price_half_ticks, armed_tick.ts_ns, armed_tick.sequence, observed + 1, None, trigger_ts_ns=tick.ts_ns, trigger_sequence=tick.sequence)
    expired = len(eligible) >= policy.max_wait_ticks
    if armed_tick:
        reason = "NO_RETEST_BEFORE_EXPIRY" if expired else "SESSION_END_BEFORE_RETEST"
    else:
        reason = "NO_DEPARTURE_BEFORE_EXPIRY" if expired else "SESSION_END_BEFORE_DEPARTURE"
    return Decision(event.event_id, policy.policy_id, "CENSORED", None, None, None, armed_tick.ts_ns if armed_tick else None, armed_tick.sequence if armed_tick else None, min(len(eligible), policy.max_wait_ticks), reason)


def decision_record(decision: Decision) -> dict:
    data = asdict(decision)
    data["record_sha256"] = canonical_hash(data)
    return data


def assert_target_free(record: dict) -> None:
    forbidden = ("pnl", "return", "mfe", "mae", "profit", "loss", "target", "stop", "win_rate")
    bad = [key for key in record if any(term in key.lower() for term in forbidden)]
    if bad:
        raise ValueError(f"outcome fields forbidden: {bad}")
