from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


HOLDOUT_BOUNDARY_NS = 1_782_856_800_000_000_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_COSTS = frozenset({
    "commission_roundturn",
    "exchange_fees_roundturn",
    "spread_ticks",
    "slippage_ticks_base",
    "slippage_ticks_stress",
    "latency_model",
})


class EconomicPreflightError(RuntimeError):
    """Raised when an economic campaign attempts to execute before G0.5 passes."""


@dataclass(frozen=True)
class EconomicPreflightReport:
    campaign_id: str
    executable: bool
    blockers: tuple[str, ...]


def _is_nonnegative_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def evaluate_economic_campaign(manifest: Mapping[str, Any]) -> EconomicPreflightReport:
    """Evaluate G0.5 without reading outcomes or data files."""
    blockers: list[str] = []
    campaign_id = str(manifest.get("campaign_id") or "")
    if not campaign_id:
        blockers.append("CAMPAIGN_ID_MISSING")

    boundary = int(manifest.get("holdout_boundary_ns", HOLDOUT_BOUNDARY_NS))
    discovery_end = manifest.get("discovery_end_ns")
    validation_end = manifest.get("validation_end_ns")
    if discovery_end is None or int(discovery_end) >= boundary:
        blockers.append("DISCOVERY_WINDOW_NOT_STRICTLY_PREHOLDOUT")
    if validation_end is None or int(validation_end) >= boundary:
        blockers.append("VALIDATION_WINDOW_NOT_STRICTLY_PREHOLDOUT")

    hashes = list(manifest.get("input_hashes") or [])
    if not hashes:
        blockers.append("INPUT_HASHES_MISSING")
    elif any(not isinstance(value, str) or SHA256_RE.fullmatch(value) is None for value in hashes):
        blockers.append("INPUT_HASH_INVALID")

    semantics = manifest.get("signal_semantics")
    if not isinstance(semantics, Mapping) or semantics.get("status") != "CERTIFIED":
        blockers.append("SIGNAL_SEMANTICS_NOT_CERTIFIED")
    elif not semantics.get("formation_spec") or not semantics.get("available_at_contract"):
        blockers.append("SIGNAL_SEMANTICS_INCOMPLETE")

    fill_policy = manifest.get("fill_policy") or {}
    if fill_policy.get("provenance") != "OBSERVED_FIRST_EXECUTABLE_TICK_OR_ABSTAIN":
        blockers.append("FILL_POLICY_NOT_OBSERVED_OR_ABSTAIN")

    costs = manifest.get("cost_model") or {}
    missing_costs = sorted(REQUIRED_COSTS - set(costs))
    if missing_costs:
        blockers.append("COST_MODEL_INCOMPLETE:" + ",".join(missing_costs))
    for key in (
        "commission_roundturn",
        "exchange_fees_roundturn",
        "spread_ticks",
        "slippage_ticks_base",
    ):
        if key in costs and not _is_nonnegative_number(costs[key]):
            blockers.append(f"COST_COMPONENT_INVALID:{key}")
    stress = costs.get("slippage_ticks_stress")
    if stress is not None and (
        not isinstance(stress, list)
        or not stress
        or any(not _is_nonnegative_number(value) for value in stress)
    ):
        blockers.append("COST_COMPONENT_INVALID:slippage_ticks_stress")
    latency = costs.get("latency_model")
    if latency is not None and (
        not isinstance(latency, str)
        or not latency.strip()
        or latency.startswith("TO_")
    ):
        blockers.append("COST_COMPONENT_INVALID:latency_model")

    multiplicity = manifest.get("multiplicity") or {}
    if not multiplicity.get("family_id"):
        blockers.append("MULTIPLICITY_FAMILY_MISSING")
    count = multiplicity.get("effective_hypothesis_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        blockers.append("EFFECTIVE_HYPOTHESIS_COUNT_INVALID")
    if not multiplicity.get("correction_method"):
        blockers.append("MULTIPLICITY_CORRECTION_MISSING")

    if manifest.get("outcomes_enabled") is not True:
        blockers.append("OUTCOMES_DISABLED")
    if manifest.get("human_authorized") is not True:
        blockers.append("HUMAN_AUTHORIZATION_MISSING")

    unique = tuple(dict.fromkeys(blockers))
    return EconomicPreflightReport(
        campaign_id=campaign_id,
        executable=not unique,
        blockers=unique,
    )


def assert_economic_campaign_executable(manifest: Mapping[str, Any]) -> EconomicPreflightReport:
    report = evaluate_economic_campaign(manifest)
    if not report.executable:
        raise EconomicPreflightError("G0.5 blocked: " + "; ".join(report.blockers))
    return report
