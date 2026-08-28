"""Scientific primitives for the BT2A GC time-of-day heterogeneity diagnostic."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from edgelab.research.bt2a_gate2_first_passage import holm_adjust, wild_cluster_test

CHICAGO = ZoneInfo("America/Chicago")
PHASES = ("ASIA_ETH", "EUROPE_PRE_RTH", "GC_RTH", "POST_RTH")


def phase_for_ns(ts_utc_ns: int) -> str | None:
    """Classify a causal fill timestamp into a frozen GC phase."""
    local = datetime.fromtimestamp(int(ts_utc_ns) / 1_000_000_000, tz=timezone.utc).astimezone(CHICAGO)
    second = local.hour * 3600 + local.minute * 60 + local.second
    if second >= 17 * 3600 or second < 1 * 3600:
        return "ASIA_ETH"
    if 1 * 3600 <= second < 7 * 3600 + 20 * 60:
        return "EUROPE_PRE_RTH"
    if 7 * 3600 + 20 * 60 <= second < 12 * 3600 + 30 * 60:
        return "GC_RTH"
    if 12 * 3600 + 30 * 60 <= second < 16 * 3600:
        return "POST_RTH"
    return None


def in_macro_blackout(ts_utc_ns: int, intervals: Sequence[tuple[int, int]]) -> bool:
    """Left-closed, right-open macro blackout membership."""
    value = int(ts_utc_ns)
    return any(int(start) <= value < int(end) for start, end in intervals)


def _effect_map(row: Mapping[str, Any]) -> dict[tuple[int, int, str], float]:
    effects: dict[tuple[int, int, str], float] = {}
    for phase_row in row.get("phases", []):
        if phase_row.get("status") != "COMPLETE":
            continue
        phase = str(phase_row.get("phase"))
        for cell in phase_row.get("cells", []):
            key = (int(cell["barrier_ticks"]), int(cell["horizon_ticks"]), phase)
            if key in effects:
                raise ValueError(f"duplicate session phase cell: {key}")
            effects[key] = float(cell["K_ABS_minus_N_RAND"])
    return effects


def aggregate_clock_family(
    rows: Sequence[Mapping[str, Any]],
    *,
    parent_cells: Sequence[tuple[int, int]],
    phases: Sequence[str] = PHASES,
    replications: int,
    base_seed: int,
    min_other_phases: int,
    min_sessions: int,
) -> dict[str, Any]:
    """Build 12 preregistered phase-vs-rest contrasts with session-clustered inference."""
    if len(set(phases)) != len(phases) or set(phases) != set(PHASES):
        raise ValueError("phase family must contain the four frozen phases")
    if len(set(parent_cells)) != len(parent_cells):
        raise ValueError("duplicate parent cell")
    if not 1 <= int(min_other_phases) < len(phases):
        raise ValueError("invalid min_other_phases")
    if int(min_sessions) < 2:
        raise ValueError("min_sessions must be >=2")

    session_effects = [_effect_map(row) for row in rows]
    descriptive: list[dict[str, Any]] = []
    family: list[dict[str, Any]] = []

    def infer(values: list[float], label: str) -> dict[str, Any] | None:
        if len(values) < 2:
            return None
        seed = int.from_bytes(
            __import__("hashlib").sha256(f"{base_seed}|{label}".encode()).digest()[:8],
            "little",
        ) % (2**32 - 1)
        return wild_cluster_test(values, replications=int(replications), seed=seed)

    for barrier, horizon in parent_cells:
        for phase in phases:
            phase_values = [
                effects[(barrier, horizon, phase)]
                for effects in session_effects
                if (barrier, horizon, phase) in effects
            ]
            phase_inference = infer(phase_values, f"phase|{barrier}|{horizon}|{phase}")
            descriptive.append({
                "barrier_ticks": int(barrier),
                "horizon_ticks": int(horizon),
                "phase": phase,
                "n_sessions": len(phase_values),
                "status": "DESCRIPTIVE_COMPLETE" if phase_inference else "DESCRIPTIVE_INSUFFICIENT",
                "K_ABS_minus_N_RAND": phase_inference,
                "can_select_window": False,
            })

            heterogeneity_values: list[float] = []
            for effects in session_effects:
                key = (barrier, horizon, phase)
                if key not in effects:
                    continue
                other = [
                    effects[(barrier, horizon, candidate)]
                    for candidate in phases
                    if candidate != phase and (barrier, horizon, candidate) in effects
                ]
                if len(other) == len(phases) - 1 and len(other) >= int(min_other_phases):
                    heterogeneity_values.append(effects[key] - sum(other) / len(other))
            inference = infer(
                heterogeneity_values,
                f"heterogeneity|{barrier}|{horizon}|{phase}",
            )
            family.append({
                "barrier_ticks": int(barrier),
                "horizon_ticks": int(horizon),
                "phase": phase,
                "estimand": "SESSION_PHASE_EFFECT_MINUS_MEAN_ALL_THREE_OTHER_PHASE_EFFECTS",
                "n_sessions": len(heterogeneity_values),
                "status": "COMPLETE" if inference is not None and len(heterogeneity_values) >= int(min_sessions) else "INSUFFICIENT_COVERAGE",
                "phase_minus_rest": inference,
                "p_holm_12": None,
                "familywise_signal": False,
            })

    expected = len(parent_cells) * len(phases)
    if len(family) != expected or any(row["status"] != "COMPLETE" for row in family):
        return {
            "status": "INCOMPLETE",
            "family_size": expected,
            "family": family,
            "phase_estimates_descriptive": descriptive,
            "decision": {
                "label": "P2A_CLOCK_HETEROGENEITY_INCONCLUSIVE",
                "reason": "INCOMPLETE_PREREGISTERED_FAMILY_OR_COVERAGE",
                "passing_contrasts": [],
                "winner_selected": False,
                "edge_declared": False,
                "promotion_eligible": False,
            },
        }

    adjusted = holm_adjust([row["phase_minus_rest"]["p_two_sided"] for row in family])
    passing: list[dict[str, Any]] = []
    for row, p_holm in zip(family, adjusted):
        row["p_holm_12"] = float(p_holm)
        estimate = row["phase_minus_rest"]
        row["familywise_signal"] = bool(
            p_holm <= 0.05 and (estimate["lower"] > 0 or estimate["upper"] < 0)
        )
        if row["familywise_signal"]:
            passing.append({
                "barrier_ticks": row["barrier_ticks"],
                "horizon_ticks": row["horizon_ticks"],
                "phase": row["phase"],
                "direction_vs_rest": "ABOVE" if estimate["point"] > 0 else "BELOW",
            })

    label = (
        "P2A_POST_SELECTION_CLOCK_HETEROGENEITY_SIGNAL"
        if passing
        else "P2A_POST_SELECTION_NO_CLOCK_HETEROGENEITY_SIGNAL"
    )
    return {
        "status": "COMPLETE",
        "family_size": expected,
        "family": family,
        "phase_estimates_descriptive": descriptive,
        "decision": {
            "label": label,
            "reason": "AT_LEAST_ONE_HOLM_12_PHASE_VS_REST_CONTRAST" if passing else "ZERO_HOLM_12_PHASE_VS_REST_CONTRASTS",
            "passing_contrasts": passing,
            "post_selection": True,
            "confirmatory_eligible": False,
            "winner_selected": False,
            "edge_declared": False,
            "promotion_eligible": False,
        },
    }
