"""Fail-closed registry for indicator onboarding.

This module never executes indicators or outcomes. It validates that source,
parity, parameter classes and allowed next actions are explicit before a
candidate can enter a campaign.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any, Iterable

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "config" / "indicator_registry_v1.json"
EXPECTED_IDS = frozenset({"gaps2","bigtrap2","hftzones2","voltickspoc2","avolcellpoi2","aacloseopendiffs","lux_imb_og_vi","avolclusterpoi","tickbardiag","captureeventprobev2"})
ALLOWED_ROLES = frozenset({"research_indicator", "diagnostic"})
ALLOWED_STAGES = frozenset({"target_free_ready","target_free_ready_limited","blocked","active_pr","source_pinned","diagnostic_only"})
READY_PARITY = frozenset({"exact", "exact_limited"})
PARAM_GROUPS = ("target_free", "lifecycle", "visual", "outcome")

@dataclass(frozen=True)
class RegistryCheck:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    @property
    def ok(self) -> bool:
        return not self.errors

def load_registry(path: str | Path = REGISTRY_PATH) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)

def by_id(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in registry["indicators"]}

def _duplicates(values: Iterable[str]) -> set[str]:
    seen, dups = set(), set()
    for value in values:
        (dups if value in seen else seen).add(value)
    return dups

def validate_registry(registry: dict[str, Any], repo_root: str | Path | None = None) -> RegistryCheck:
    errors, warnings = [], []
    if registry.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    policy = registry.get("policy", {})
    if policy.get("outcome_search") != "blocked_until_explicit_campaign_approval":
        errors.append("outcome search must remain fail-closed")
    if policy.get("holdout") != "sealed":
        errors.append("holdout must remain sealed")
    if policy.get("visual_parameters_optimizable") is not False:
        errors.append("visual parameters must never be optimizable")
    indicators = registry.get("indicators")
    if not isinstance(indicators, list) or not indicators:
        return RegistryCheck(tuple(errors + ["indicators must be a non-empty list"]), tuple(warnings))
    ids = [item.get("id") for item in indicators]
    if None in ids:
        errors.append("every indicator needs an id")
    dups = _duplicates(str(x) for x in ids)
    if dups:
        errors.append(f"duplicate indicator ids: {sorted(dups)}")
    missing = EXPECTED_IDS - set(ids)
    if missing:
        errors.append(f"known indicators missing: {sorted(missing)}")
    if set(registry.get("legacy_core_ids", [])) != {"gaps2","bigtrap2","hftzones2","voltickspoc2","avolcellpoi2"}:
        errors.append("legacy_core_ids must be exactly the original five")
    root = Path(repo_root) if repo_root is not None else None
    for entry in indicators:
        ident, role, stage = entry.get("id", "<missing>"), entry.get("role"), entry.get("stage")
        if role not in ALLOWED_ROLES:
            errors.append(f"{ident}: invalid role {role!r}")
        if stage not in ALLOWED_STAGES:
            errors.append(f"{ident}: invalid stage {stage!r}")
        if entry.get("outcome_search_enabled") is not False:
            errors.append(f"{ident}: outcome search must be disabled")
        source, kernel, parity = entry.get("source", {}), entry.get("kernel", {}), entry.get("parity", {})
        if source.get("status") in {"canonical","reviewed_reference","drift_pending","pinned_incoming","active_pr"} and not source.get("sha256"):
            errors.append(f"{ident}: pinned/active source requires sha256")
        if stage in {"target_free_ready", "target_free_ready_limited"}:
            if parity.get("status") not in READY_PARITY:
                errors.append(f"{ident}: ready stage without exact parity")
            if kernel.get("status") != "integrated":
                errors.append(f"{ident}: ready stage without integrated kernel")
        if role == "diagnostic" and (stage != "diagnostic_only" or parity.get("status") != "not_applicable"):
            errors.append(f"{ident}: diagnostic entered research lifecycle")
        contract, groups = entry.get("parameter_contract", {}), {}
        for group in PARAM_GROUPS:
            value = contract.get(group, [])
            if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
                errors.append(f"{ident}: {group} must be a string list")
                value = []
            groups[group] = value
        overlap = _duplicates(p for values in groups.values() for p in values)
        if overlap:
            errors.append(f"{ident}: parameters in multiple groups: {sorted(overlap)}")
        if root is not None:
            paths = [("source", source.get("path")), ("prepared source", source.get("prepared_path")), ("kernel", kernel.get("path"))]
            for label, path in paths:
                if path and source.get("status") != "active_pr" and not (root / path).exists():
                    errors.append(f"{ident}: {label} path missing: {path}")
            for path in entry.get("tests", []):
                if not (root / path).exists():
                    errors.append(f"{ident}: test path missing: {path}")
        if role == "research_indicator" and not entry.get("next_actions"):
            warnings.append(f"{ident}: no next action")
    index = by_id(registry)
    avol = index.get("avolclusterpoi", {})
    if avol.get("source", {}).get("sha256") != "3420519de9b4a1456f812040b62af419b0c323486281424a84aaaab126100c98":
        errors.append("aVolClusterPOI hash differs from received artifact")
    if avol.get("stage") != "source_pinned":
        errors.append("aVolClusterPOI cannot advance before compile/kernel/parity")
    if index.get("lux_imb_og_vi", {}).get("stage") != "active_pr":
        errors.append("LUX must remain owned by PR #6")
    return RegistryCheck(tuple(errors), tuple(warnings))
