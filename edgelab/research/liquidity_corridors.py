"""Audit-first measurement primitives for liquidity-corridor research.

This module deliberately does not define the winning corridor. It enforces the
parts that must not move after outcomes are observed: causal availability,
exact first-passage on ordered ticks, deterministic matched controls, session-
level inference, multiple-testing correction, and explicit trading friction.

It contains no data paths and never opens the holdout by itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping, Sequence

import numpy as np

HOLDOUT_START = date(2026, 7, 1)


class CorridorContractError(ValueError):
    """Input violates the causal measurement contract."""


@dataclass(frozen=True)
class CorridorDefinition:
    forward_density_max: float
    backstop_density_min: float
    min_width_ticks: int
    max_width_ticks: int

    def __post_init__(self) -> None:
        if not 0.0 <= self.forward_density_max <= 1.0:
            raise CorridorContractError("forward_density_max must be in [0, 1]")
        if not 0.0 <= self.backstop_density_min <= 1.0:
            raise CorridorContractError("backstop_density_min must be in [0, 1]")
        if self.min_width_ticks < 1 or self.max_width_ticks < self.min_width_ticks:
            raise CorridorContractError("invalid width interval")

    def qualifies(self, *, forward_density: float, backstop_density: float,
                  width_ticks: int) -> bool:
        return (
            forward_density <= self.forward_density_max
            and backstop_density >= self.backstop_density_min
            and self.min_width_ticks <= width_ticks <= self.max_width_ticks
        )


@dataclass(frozen=True)
class CorridorSignal:
    event_id: str
    root: str
    contract: str
    trade_date: str
    regime_id: str
    session_id: str
    direction: int
    created_ns: int
    available_ns: int
    decision_ns: int
    reference_tick: int
    forward_density: float
    backstop_density: float
    width_ticks: int
    time_bucket: str
    volatility_bin: str
    impulse_bin: str


@dataclass(frozen=True)
class TradeTick:
    ts_ns: int
    price_tick: int
    contract: str
    trade_date: str
    regime_id: str
    sequence: int = 0


@dataclass(frozen=True)
class FirstPassageOutcome:
    event_id: str
    status: str
    entry_ns: int | None
    exit_ns: int | None
    entry_tick: int | None
    exit_tick: int | None
    gross_ticks: float | None
    net_ticks: float | None
    net_r: float | None


@dataclass(frozen=True)
class MatchObservation:
    event_id: str
    session_id: str
    contract: str
    direction: int
    time_bucket: str
    volatility_bin: str
    impulse_bin: str
    distance_bin: str
    score: float
    net_r: float
    is_candidate: bool


@dataclass(frozen=True)
class MatchedPair:
    candidate_id: str
    control_id: str
    session_id: str
    delta_net_r: float


@dataclass(frozen=True)
class PairedInference:
    n_pairs: int
    n_sessions: int
    mean_delta_net_r: float
    ci_low: float
    ci_high: float
    p_sign_flip: float


def validate_signal(signal: CorridorSignal) -> None:
    """Fail closed on future information, invalid identity, or holdout access."""
    if signal.direction not in (-1, 1):
        raise CorridorContractError("direction must be -1 or +1")
    if not signal.event_id or not signal.contract or not signal.regime_id:
        raise CorridorContractError("event, contract and regime identity are required")
    try:
        td = date.fromisoformat(signal.trade_date)
    except ValueError as exc:
        raise CorridorContractError("trade_date must be YYYY-MM-DD") from exc
    if td >= HOLDOUT_START:
        raise CorridorContractError("development signal touches sealed holdout")
    if signal.created_ns > signal.available_ns:
        raise CorridorContractError("feature cannot be available before it is created")
    if signal.available_ns > signal.decision_ns:
        raise CorridorContractError("decision uses a feature not yet available")
    if not 0.0 <= signal.forward_density <= 1.0:
        raise CorridorContractError("forward density outside [0, 1]")
    if not 0.0 <= signal.backstop_density <= 1.0:
        raise CorridorContractError("backstop density outside [0, 1]")
    if signal.width_ticks < 1:
        raise CorridorContractError("width_ticks must be positive")


def select_non_overlapping(signals: Iterable[CorridorSignal], *, cooldown_ns: int) -> list[CorridorSignal]:
    """Deterministic one-signal-per-episode selection, before outcomes exist."""
    if cooldown_ns < 0:
        raise CorridorContractError("cooldown_ns must be non-negative")
    selected: list[CorridorSignal] = []
    last: dict[tuple[str, str, int], int] = {}
    for signal in sorted(signals, key=lambda x: (x.decision_ns, x.event_id)):
        validate_signal(signal)
        key = (signal.contract, signal.session_id, signal.direction)
        previous = last.get(key)
        if previous is not None and signal.decision_ns - previous < cooldown_ns:
            continue
        selected.append(signal)
        last[key] = signal.decision_ns
    return selected


def resolve_first_passage(
    signal: CorridorSignal,
    ticks: Sequence[TradeTick],
    *,
    target_ticks: int,
    stop_ticks: int,
    horizon_ns: int,
    friction_ticks_round_turn: float,
) -> FirstPassageOutcome:
    """Resolve target/stop in true tick order with next-tick entry.

    Entry is the first executable trade strictly after ``decision_ns``. Ticks
    with a different contract, trade date, or regime are rejected rather than
    silently crossed. No OHLC tie-breaking is possible or needed.
    """
    validate_signal(signal)
    if target_ticks <= 0 or stop_ticks <= 0 or horizon_ns <= 0:
        raise CorridorContractError("target, stop and horizon must be positive")
    if friction_ticks_round_turn < 0:
        raise CorridorContractError("friction cannot be negative")

    ordered = sorted(ticks, key=lambda x: (x.ts_ns, x.sequence))
    eligible: list[TradeTick] = []
    for tick in ordered:
        if tick.ts_ns <= signal.decision_ns:
            continue
        if tick.ts_ns > signal.decision_ns + horizon_ns:
            break
        if (tick.contract, tick.trade_date, tick.regime_id) != (
            signal.contract, signal.trade_date, signal.regime_id
        ):
            raise CorridorContractError("tick crosses contract/date/regime boundary")
        eligible.append(tick)

    if not eligible:
        return FirstPassageOutcome(signal.event_id, "DATA_EDGE", None, None, None, None, None, None, None)

    entry = eligible[0]
    exit_tick = eligible[-1]
    status = "TIMEOUT"
    for tick in eligible[1:]:
        signed_move = signal.direction * (tick.price_tick - entry.price_tick)
        if signed_move >= target_ticks:
            status = "TARGET"
            exit_tick = tick
            break
        if signed_move <= -stop_ticks:
            status = "STOP"
            exit_tick = tick
            break

    gross = float(signal.direction * (exit_tick.price_tick - entry.price_tick))
    net = gross - float(friction_ticks_round_turn)
    return FirstPassageOutcome(
        event_id=signal.event_id,
        status=status,
        entry_ns=entry.ts_ns,
        exit_ns=exit_tick.ts_ns,
        entry_tick=entry.price_tick,
        exit_tick=exit_tick.price_tick,
        gross_ticks=gross,
        net_ticks=net,
        net_r=net / float(stop_ticks),
    )


def ohlc_bar_touch_state(*, direction: int, high_tick: int, low_tick: int,
                         entry_tick: int, target_ticks: int, stop_ticks: int) -> str:
    """Classify OHLC first-passage information without inventing intrabar order."""
    if direction not in (-1, 1) or target_ticks <= 0 or stop_ticks <= 0:
        raise CorridorContractError("invalid OHLC barrier arguments")
    target = entry_tick + direction * target_ticks
    stop = entry_tick - direction * stop_ticks
    hit_target = high_tick >= target if direction == 1 else low_tick <= target
    hit_stop = low_tick <= stop if direction == 1 else high_tick >= stop
    if hit_target and hit_stop:
        return "AMBIGUOUS_BOTH"
    if hit_target:
        return "TARGET_ONLY"
    if hit_stop:
        return "STOP_ONLY"
    return "NEITHER"


def _stratum(o: MatchObservation) -> tuple[str, int, str, str, str, str]:
    return (o.contract, o.direction, o.time_bucket, o.volatility_bin, o.impulse_bin, o.distance_bin)


def deterministic_matched_pairs(observations: Iterable[MatchObservation], *,
                                score_caliper: float | None = None) -> list[MatchedPair]:
    """One-to-one matching without replacement inside predeclared exact strata."""
    obs = list(observations)
    candidates = sorted((x for x in obs if x.is_candidate), key=lambda x: x.event_id)
    controls_by_stratum: dict[tuple[str, int, str, str, str, str], list[MatchObservation]] = {}
    for control in sorted((x for x in obs if not x.is_candidate), key=lambda x: x.event_id):
        controls_by_stratum.setdefault(_stratum(control), []).append(control)

    used: set[str] = set()
    pairs: list[MatchedPair] = []
    for candidate in candidates:
        pool = [x for x in controls_by_stratum.get(_stratum(candidate), []) if x.event_id not in used]
        if not pool:
            continue
        control = min(pool, key=lambda x: (abs(x.score - candidate.score), x.event_id))
        if score_caliper is not None and abs(control.score - candidate.score) > score_caliper:
            continue
        used.add(control.event_id)
        pairs.append(MatchedPair(
            candidate_id=candidate.event_id,
            control_id=control.event_id,
            session_id=candidate.session_id,
            delta_net_r=float(candidate.net_r - control.net_r),
        ))
    return pairs


def paired_session_inference(pairs: Sequence[MatchedPair], *, n_resamples: int = 5000,
                             seed: int = 0, alpha: float = 0.05) -> PairedInference:
    """Bootstrap and sign-flip at the session level, the independent unit."""
    if not pairs:
        raise CorridorContractError("at least one matched pair is required")
    if n_resamples < 100:
        raise CorridorContractError("n_resamples must be at least 100")
    if not 0.0 < alpha < 1.0:
        raise CorridorContractError("alpha must be in (0, 1)")

    grouped: dict[str, list[float]] = {}
    for pair in pairs:
        grouped.setdefault(pair.session_id, []).append(pair.delta_net_r)
    session_means = np.array([np.mean(grouped[k]) for k in sorted(grouped)], dtype=float)
    rng = np.random.default_rng(seed)
    n_sessions = len(session_means)

    boot = np.empty(n_resamples, dtype=float)
    perm = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        boot[i] = float(np.mean(rng.choice(session_means, size=n_sessions, replace=True)))
        signs = rng.choice(np.array([-1.0, 1.0]), size=n_sessions, replace=True)
        perm[i] = float(np.mean(session_means * signs))

    observed = float(np.mean(session_means))
    p = (1.0 + float(np.sum(perm >= observed))) / (n_resamples + 1.0)
    return PairedInference(
        n_pairs=len(pairs),
        n_sessions=n_sessions,
        mean_delta_net_r=observed,
        ci_low=float(np.quantile(boot, alpha / 2.0)),
        ci_high=float(np.quantile(boot, 1.0 - alpha / 2.0)),
        p_sign_flip=p,
    )


def holm_adjust(p_values: Mapping[str, float]) -> dict[str, float]:
    """Holm family-wise-error adjustment for every reported variant."""
    items = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(items)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, p) in enumerate(items):
        if not 0.0 <= p <= 1.0:
            raise CorridorContractError("p-values must be in [0, 1]")
        running = max(running, min(1.0, (m - rank) * p))
        adjusted[name] = running
    return adjusted


def campaign_audit(*, candidate_mean_net_r: float, control_mean_net_r: float,
                   n_declared_variants: int, n_reported_variants: int,
                   inference: PairedInference | None) -> list[str]:
    """Return blocking/warning labels; never turn diagnostics into certification."""
    findings: list[str] = []
    if n_declared_variants < n_reported_variants:
        findings.append("FAIL_HYPOTHESIS_BUDGET_UNDERCOUNTS_REPORTED_VARIANTS")
    if candidate_mean_net_r <= control_mean_net_r:
        findings.append("FAIL_NO_INCREMENTAL_EDGE_OVER_MATCHED_CONTROL")
    if inference is None:
        findings.append("ABSTAIN_NO_SESSION_LEVEL_INFERENCE")
    else:
        if inference.n_sessions < 20:
            findings.append("ABSTAIN_TOO_FEW_INDEPENDENT_SESSIONS")
        if inference.ci_low <= 0.0:
            findings.append("FAIL_PAIRED_CI_NOT_ABOVE_ZERO")
    return findings
