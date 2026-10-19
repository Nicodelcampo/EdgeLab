# -*- coding: utf-8 -*-
"""Fail-closed AVolCluster NQ lifecycle and episode-contract primitives.

This module has no data loader, future-path scanner, outcome runner or P&L code.
It validates draft/frozen policies, classifies one caller-supplied observation,
and can collapse creation-only zone rows after the episode policy is frozen.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from edgelab.research.event_store_contract import (
    canonical_sha256,
    normalize_rows,
    stamp_identity,
)

LIFECYCLE_DRAFT = "DRAFT_DECISIONS_REQUIRED_FAIL_CLOSED"
LIFECYCLE_FROZEN = "FROZEN_LIFECYCLE_FIRST_TOUCH_CONTRACT"
EPISODE_DRAFT = "DRAFT_DECISIONS_REQUIRED_FAIL_CLOSED"
EPISODE_FROZEN = "FROZEN_EPISODE_COLLAPSE_CONTRACT"
LIFECYCLE_EVENT_SCHEMA = "avolcluster_nq_lifecycle_event_v1"
EPISODE_EVENT_SCHEMA = "avolcluster_nq_episode_membership_v1"


class LifecycleContractError(ValueError):
    def __init__(self, message: str, label: str = "ABSTAIN_AVOL_LIFECYCLE_CONTRACT"):
        super().__init__(message)
        self.label = label


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise LifecycleContractError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise LifecycleContractError(f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def dotted_get(value: Mapping[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise LifecycleContractError(f"missing decision path: {path}")
        current = current[part]
    return current


def dotted_set(value: dict[str, Any], path: str, replacement: Any) -> None:
    current: dict[str, Any] = value
    parts = path.split(".")
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            raise LifecycleContractError(f"missing decision path: {path}")
        current = child
    if parts[-1] not in current:
        raise LifecycleContractError(f"missing decision path: {path}")
    current[parts[-1]] = replacement


def _policy_payload(spec: Mapping[str, Any]) -> dict[str, Any]:
    excluded = {
        "status", "authorization", "frozen_at_utc", "frozen_commit",
        "frozen_policy_payload_sha256",
    }
    return {key: value for key, value in spec.items() if key not in excluded}


def policy_payload_sha256(spec: Mapping[str, Any]) -> str:
    return canonical_sha256(_policy_payload(spec))


def _validate_decisions(spec: Mapping[str, Any]) -> list[str]:
    paths = spec.get("decision_paths")
    unresolved = spec.get("unresolved_decisions")
    evidence = spec.get("decision_evidence")
    candidates = spec.get("candidate_values_not_selected", {})
    if not isinstance(paths, list) or not paths or len(paths) != len(set(paths)):
        raise LifecycleContractError("decision_paths must be a unique non-empty list")
    if not isinstance(unresolved, list) or len(unresolved) != len(set(unresolved)):
        raise LifecycleContractError("unresolved_decisions must be a unique list")
    if not isinstance(evidence, Mapping) or set(evidence) != set(paths):
        raise LifecycleContractError("decision_evidence keys must equal decision_paths")
    actual_unresolved: list[str] = []
    for path in paths:
        selected = dotted_get(spec, path)
        proof = evidence[path]
        if selected is None:
            actual_unresolved.append(path)
            if proof is not None:
                raise LifecycleContractError(f"unresolved decision has evidence: {path}")
            continue
        if not isinstance(proof, Mapping):
            raise LifecycleContractError(f"resolved decision lacks evidence: {path}")
        for required in ("decision_id", "authority", "decided_at", "source_reference"):
            if not isinstance(proof.get(required), str) or not proof[required]:
                raise LifecycleContractError(f"decision evidence incomplete for {path}: {required}")
        allowed = candidates.get(path)
        if isinstance(allowed, list) and allowed and selected not in allowed:
            raise LifecycleContractError(f"selected value is outside registered candidates: {path}")
    if actual_unresolved != unresolved:
        raise LifecycleContractError("unresolved_decisions does not match null decision fields")
    return actual_unresolved


def _validate_no_execution_authority(spec: Mapping[str, Any]) -> None:
    auth = spec.get("authorization")
    if not isinstance(auth, Mapping):
        raise LifecycleContractError("missing authorization object")
    if auth.get("execution_authorized") is not False or auth.get("execution_token") is not None:
        raise LifecycleContractError("this package cannot authorize execution")
    if auth.get("future_path_capability") is not False:
        raise LifecycleContractError("future-path capability must remain false")


def validate_lifecycle_spec(spec: Mapping[str, Any]) -> list[str]:
    if spec.get("status") not in {LIFECYCLE_DRAFT, LIFECYCLE_FROZEN}:
        raise LifecycleContractError("unsupported lifecycle spec status")
    population = spec.get("population", {})
    if population.get("instrument") != "NQ" or population.get("tick_size") != 0.25:
        raise LifecycleContractError("lifecycle contract is bound to NQ tick_size=0.25")
    if population.get("config_id") != "tick_120_W5_M20_C4_P950":
        raise LifecycleContractError("AVol configuration drift")
    if population.get("creation_bar_eligible_for_first_touch") is not False:
        raise LifecycleContractError("creation bar must be ineligible for first touch")
    source = spec.get("source_creation_store", {})
    if source.get("status") != "COMPLETE_TARGET_FREE_ZONE_CREATION_STORE":
        raise LifecycleContractError("source creation store is not complete")
    if source.get("rows") != 5876 or source.get("checkpoint_files") != 234:
        raise LifecycleContractError("source creation-store counts drift")
    firewall = spec.get("firewall", {})
    required_false = [
        "RAW_TICK_DECODE_ALLOWED", "LIFECYCLE_EXECUTION_ALLOWED", "FIRST_TOUCH_BUILD_ALLOWED",
        "FUTURE_PRICE_PATH_ACCESSED", "MFE_MAE_ACCESSED", "FIRST_PASSAGE_ACCESSED",
        "PNL_ACCESSED", "HOLDOUT_TOUCHED", "EDGE_DECLARED", "PROMOTION_ELIGIBLE",
    ]
    if firewall.get("DESIGN_ONLY") is not True or any(firewall.get(key) is not False for key in required_false):
        raise LifecycleContractError("lifecycle firewall is not fully closed")
    _validate_no_execution_authority(spec)
    missing = _validate_decisions(spec)
    normalize_rows([], spec["lifecycle_row_contract"])
    auth = spec["authorization"]
    if spec["status"] == LIFECYCLE_DRAFT:
        if auth.get("freeze_authorized") is not False or auth.get("freeze_token") is not None:
            raise LifecycleContractError("draft lifecycle contract cannot be freeze-authorized")
        if spec.get("frozen_policy_payload_sha256") is not None:
            raise LifecycleContractError("draft lifecycle contract cannot carry a frozen payload hash")
    else:
        if missing:
            raise LifecycleContractError("frozen lifecycle contract has unresolved decisions")
        if auth.get("freeze_authorized") is not True or not auth.get("freeze_token"):
            raise LifecycleContractError("frozen lifecycle contract lacks freeze evidence")
        if spec.get("frozen_policy_payload_sha256") != policy_payload_sha256(spec):
            raise LifecycleContractError("frozen lifecycle policy hash mismatch")
    return missing


def validate_episode_spec(spec: Mapping[str, Any]) -> list[str]:
    if spec.get("status") not in {EPISODE_DRAFT, EPISODE_FROZEN}:
        raise LifecycleContractError("unsupported episode spec status")
    if spec.get("resolved_rules", {}).get("primary_anchor") != "FIRST_ELIGIBLE_EVENT_WINS":
        raise LifecycleContractError("episode primary anchor drift")
    if spec.get("resolved_rules", {}).get("episode_builder_may_use_future_path") is not False:
        raise LifecycleContractError("episode collapse must remain creation-only")
    population = spec.get("population", {})
    if population.get("instrument") != "NQ" or population.get("config_id") != "tick_120_W5_M20_C4_P950":
        raise LifecycleContractError("episode population drift")
    firewall = spec.get("firewall", {})
    required_false = [
        "EPISODE_BUILD_ALLOWED", "FIRST_TOUCH_ACCESSED", "FUTURE_PRICE_PATH_ACCESSED",
        "MFE_MAE_ACCESSED", "FIRST_PASSAGE_ACCESSED", "PNL_ACCESSED", "HOLDOUT_TOUCHED",
        "EDGE_DECLARED", "PROMOTION_ELIGIBLE",
    ]
    if firewall.get("DESIGN_ONLY") is not True or any(firewall.get(key) is not False for key in required_false):
        raise LifecycleContractError("episode firewall is not fully closed")
    _validate_no_execution_authority(spec)
    missing = _validate_decisions(spec)
    normalize_rows([], spec["episode_membership_contract"])
    auth = spec["authorization"]
    if spec["status"] == EPISODE_DRAFT:
        if auth.get("freeze_authorized") is not False or auth.get("freeze_token") is not None:
            raise LifecycleContractError("draft episode contract cannot be freeze-authorized")
        if spec.get("frozen_policy_payload_sha256") is not None:
            raise LifecycleContractError("draft episode contract cannot carry a frozen payload hash")
    else:
        if missing:
            raise LifecycleContractError("frozen episode contract has unresolved decisions")
        if auth.get("freeze_authorized") is not True or not auth.get("freeze_token"):
            raise LifecycleContractError("frozen episode contract lacks freeze evidence")
        if spec.get("frozen_policy_payload_sha256") != policy_payload_sha256(spec):
            raise LifecycleContractError("frozen episode policy hash mismatch")
    return missing


def _require_frozen_lifecycle(spec: Mapping[str, Any]) -> None:
    missing = validate_lifecycle_spec(spec)
    if spec.get("status") != LIFECYCLE_FROZEN or missing:
        raise LifecycleContractError("lifecycle operations require a frozen fully resolved policy")


def _require_frozen_episode(spec: Mapping[str, Any]) -> None:
    missing = validate_episode_spec(spec)
    if spec.get("status") != EPISODE_FROZEN or missing:
        raise LifecycleContractError("episode operations require a frozen fully resolved policy")


def classify_touch_observation(
    zone: Mapping[str, Any], observation: Mapping[str, Any], spec: Mapping[str, Any]
) -> str | None:
    """Classify one supplied observation. It does not scan a path or load market data."""
    _require_frozen_lifecycle(spec)
    touch = spec["touch"]
    if touch["price_field"] != "trade_price_tick":
        raise LifecycleContractError("implemented primitive supports trade_price_tick only")
    if touch["contact_definition"] != "TRADE_TICK_INTERSECTS_ZONE":
        raise LifecycleContractError("implemented primitive supports trade-tick intersection only")
    if touch["interval_boundary_policy"] != "INCLUSIVE_BOTH":
        raise LifecycleContractError("implemented primitive supports inclusive zone bounds only")
    ts = observation.get("ts_utc_ns")
    price = observation.get("trade_price_tick")
    if isinstance(ts, bool) or not isinstance(ts, int):
        raise LifecycleContractError("observation ts_utc_ns must be int")
    if isinstance(price, bool) or not isinstance(price, int):
        raise LifecycleContractError("observation trade_price_tick must be int")
    availability = zone.get("availability_ts_utc_ns")
    if isinstance(availability, bool) or not isinstance(availability, int):
        raise LifecycleContractError("zone availability_ts_utc_ns must be int")
    if ts < availability:
        raise LifecycleContractError("creation-bar or pre-availability observation rejected")
    lower, upper = zone.get("lower_tick"), zone.get("upper_tick")
    if not isinstance(lower, int) or not isinstance(upper, int) or upper < lower:
        raise LifecycleContractError("invalid zone geometry")
    if price < lower or price > upper:
        return None
    if lower == upper:
        return "SINGLE_TICK_ZONE"
    if price == lower:
        return "LOWER_EDGE"
    if price == upper:
        return "UPPER_EDGE"
    return "INTERIOR"


def validate_lifecycle_rows(
    rows: Iterable[Mapping[str, Any]],
    creation_rows_by_id: Mapping[str, Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Validate caller-supplied rows; no future path is read by this function."""
    _require_frozen_lifecycle(spec)
    normalized = normalize_rows(rows, spec["lifecycle_row_contract"])
    holdout = str(spec["population"]["holdout_session_min_inclusive"])
    policy_hash = policy_payload_sha256(spec)
    for row in normalized:
        source = creation_rows_by_id.get(row["zone_event_id"])
        if not isinstance(source, Mapping):
            raise LifecycleContractError("lifecycle row references unknown creation event")
        if source.get("event_type") != "ZONE_CREATED":
            raise LifecycleContractError("lifecycle source must be a creation event")
        forbidden_source = ("first_touch", "mfe", "mae", "pnl", "first_passage", "forward_return", "future_price")
        if any(any(token in str(key).lower() for token in forbidden_source) for key in source):
            raise LifecycleContractError("lifecycle source row contains outcome fields")
        bindings = {
            "zone_identity_sha256": "identity_sha256",
            "instrument": "instrument", "contract": "contract", "session_id": "session_id",
            "config_id": "config_id", "session_ordinal": "session_ordinal",
            "created_ts_utc_ns": "created_ts_utc_ns", "availability_ts_utc_ns": "availability_ts_utc_ns",
            "lower_tick": "lower_tick", "upper_tick": "upper_tick", "width_ticks": "width_ticks",
        }
        for target, source_key in bindings.items():
            if row[target] != source.get(source_key):
                raise LifecycleContractError(f"creation binding mismatch: {target}")
        if row["session_id"] >= holdout:
            raise LifecycleContractError("holdout lifecycle row rejected", "ABSTAIN_HOLDOUT_FIREWALL")
        if row["policy_payload_sha256"] != policy_hash:
            raise LifecycleContractError("lifecycle policy hash mismatch")
        if row["pnl_accessed"] is not False or row["holdout_touched"] is not False:
            raise LifecycleContractError("P&L and holdout flags must remain false")
        if row["future_price_path_accessed"] is not True:
            raise LifecycleContractError("actual lifecycle row must honestly attest future-path access")
        touched = row["first_touch_observed"]
        touch_fields = [
            "first_touch_ts_utc_ns", "first_touch_tick", "first_touch_source_row",
            "first_touch_age_observations", "first_touch_age_ns", "contact_class", "penetration_ticks",
        ]
        if touched:
            if row["lifecycle_status"] != "FIRST_TOUCH" or any(row[key] is None for key in touch_fields):
                raise LifecycleContractError("first-touch row has incomplete touch fields")
            if row["first_touch_ts_utc_ns"] < row["availability_ts_utc_ns"]:
                raise LifecycleContractError("first touch precedes causal availability")
            origin = row["availability_ts_utc_ns"] if spec["clock"]["age_origin"] == "AVAILABILITY_TS" else row["created_ts_utc_ns"]
            if row["first_touch_age_ns"] != row["first_touch_ts_utc_ns"] - origin:
                raise LifecycleContractError("first_touch_age_ns mismatch")
            if row["first_touch_age_observations"] < 0 or row["penetration_ticks"] < 0:
                raise LifecycleContractError("touch age/penetration cannot be negative")
            expected_class = classify_touch_observation(
                source,
                {"ts_utc_ns": row["first_touch_ts_utc_ns"], "trade_price_tick": row["first_touch_tick"]},
                spec,
            )
            if expected_class != row["contact_class"]:
                raise LifecycleContractError("contact_class does not match frozen touch rule")
            if spec["touch"]["penetration_definition"] == "ZERO_AT_FIRST_ENTRY" and row["penetration_ticks"] != 0:
                raise LifecycleContractError("ZERO_AT_FIRST_ENTRY requires zero penetration")
        else:
            if any(row[key] is not None for key in touch_fields):
                raise LifecycleContractError("untouched lifecycle row contains touch fields")
            if row["lifecycle_status"] == "FIRST_TOUCH":
                raise LifecycleContractError("untouched row cannot have FIRST_TOUCH status")
        if row["expired_without_touch"] and touched:
            raise LifecycleContractError("touched row cannot expire untouched")
        if row["invalidation_observed"] and row["invalidation_ts_utc_ns"] is None:
            raise LifecycleContractError("invalidation flag requires timestamp")
        if not row["invalidation_observed"] and row["invalidation_ts_utc_ns"] is not None:
            raise LifecycleContractError("invalidation timestamp requires flag")
    return normalized


def _episode_anchor_ns(row: Mapping[str, Any], spec: Mapping[str, Any]) -> int:
    key = spec["temporal"]["anchor_field"]
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise LifecycleContractError(f"episode anchor field must be int: {key}")
    return value


def _temporal_link(a: Mapping[str, Any], b: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    delta = abs(_episode_anchor_ns(a, spec) - _episode_anchor_ns(b, spec))
    value = spec["temporal"]["window_value"]
    unit = spec["temporal"]["window_unit"]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LifecycleContractError("episode temporal window must be a non-negative int")
    if unit == "SECONDS":
        limit = value * 1_000_000_000
    elif unit == "NANOSECONDS":
        limit = value
    else:
        raise LifecycleContractError("implemented episode primitive supports seconds/nanoseconds only")
    policy = spec["temporal"]["interval_boundary_policy"]
    if policy == "INCLUSIVE":
        return delta <= limit
    if policy == "EXCLUSIVE":
        return delta < limit
    raise LifecycleContractError("unsupported temporal interval policy")


def _spatial_link(a: Mapping[str, Any], b: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    alo, ahi, blo, bhi = int(a["lower_tick"]), int(a["upper_tick"]), int(b["lower_tick"]), int(b["upper_tick"])
    overlap = max(0, min(ahi, bhi) - max(alo, blo) + 1)
    gap = max(0, max(alo, blo) - min(ahi, bhi) - 1)
    smaller = min(ahi - alo + 1, bhi - blo + 1)
    fraction = overlap / smaller
    rule = spec["spatial"]["link_rule"]
    min_ticks = spec["spatial"]["minimum_overlap_ticks"]
    min_fraction = spec["spatial"]["minimum_overlap_fraction_of_smaller_zone"]
    max_gap = spec["spatial"]["maximum_adjacency_gap_ticks"]
    if not isinstance(min_ticks, int) or not isinstance(max_gap, int):
        raise LifecycleContractError("episode tick thresholds must be ints")
    if not isinstance(min_fraction, (int, float)) or isinstance(min_fraction, bool):
        raise LifecycleContractError("episode overlap fraction must be numeric")
    if rule == "ANY_INCLUSIVE_OVERLAP":
        return overlap >= 1
    if rule == "MINIMUM_OVERLAP_TICKS":
        return overlap >= min_ticks
    if rule == "MINIMUM_OVERLAP_FRACTION":
        return overlap > 0 and fraction >= float(min_fraction)
    if rule == "OVERLAP_OR_MAXIMUM_GAP":
        return overlap > 0 or gap <= max_gap
    raise LifecycleContractError("unsupported episode spatial link rule")


def collapse_creation_episodes(
    creation_rows: Iterable[Mapping[str, Any]], spec: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Pure creation-only collapse. The current draft cannot call it until frozen."""
    _require_frozen_episode(spec)
    if spec["grouping"]["algorithm"] != "CONNECTED_COMPONENTS":
        raise LifecycleContractError("implemented episode primitive supports CONNECTED_COMPONENTS only")
    if spec["grouping"]["transitivity_policy"] != "TRANSITIVE_CONNECTED_COMPONENTS":
        raise LifecycleContractError("connected-components algorithm requires transitive policy")
    if spec["grouping"]["cross_session_policy"] != "NEVER" or spec["grouping"]["cross_contract_policy"] != "NEVER":
        raise LifecycleContractError("implemented episode primitive forbids cross-session/contract links")
    if spec["anchor"]["eligibility_definition"] != "ALL_PRIMARY_CONFIG_CREATION_EVENTS":
        raise LifecycleContractError("unsupported anchor eligibility definition")
    if spec["anchor"]["tie_break_policy"] != "ANCHOR_TS_THEN_ZONE_EVENT_ID":
        raise LifecycleContractError("unsupported anchor tie-break policy")
    if spec["anchor"]["anchor_replacement_policy"] != "NEVER":
        raise LifecycleContractError("primary anchor replacement must be NEVER")
    partition_keys = spec["grouping"]["partition_keys"]
    if not isinstance(partition_keys, list) or not partition_keys:
        raise LifecycleContractError("episode partition_keys must be a non-empty list")
    rows = [dict(row) for row in creation_rows]
    seen: set[str] = set()
    holdout = str(spec["population"]["holdout_session_min_inclusive"])
    for row in rows:
        required = [
            "event_id", "identity_sha256", "event_type", "instrument", "contract", "session_id", "config_id",
            "created_ts_utc_ns", "availability_ts_utc_ns", "lower_tick", "upper_tick",
        ]
        if any(key not in row for key in required):
            raise LifecycleContractError("creation row lacks episode source fields")
        if row["event_id"] in seen:
            raise LifecycleContractError("duplicate source zone_event_id")
        seen.add(row["event_id"])
        if row["event_type"] != "ZONE_CREATED":
            raise LifecycleContractError("episode source must be a creation event")
        forbidden_source = ("first_touch", "mfe", "mae", "pnl", "first_passage", "forward_return", "future_price")
        if any(any(token in str(key).lower() for token in forbidden_source) for key in row):
            raise LifecycleContractError("episode source row contains outcome fields")
        if row["instrument"] != "NQ" or row["config_id"] != spec["population"]["config_id"]:
            raise LifecycleContractError("episode source population drift")
        if str(row["session_id"]) >= holdout:
            raise LifecycleContractError("holdout source zone rejected", "ABSTAIN_HOLDOUT_FIREWALL")
        if int(row["upper_tick"]) < int(row["lower_tick"]):
            raise LifecycleContractError("invalid source zone geometry")
    by_partition: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        try:
            key = tuple(row[name] for name in partition_keys)
        except KeyError as exc:
            raise LifecycleContractError(f"missing episode partition field: {exc.args[0]}") from exc
        by_partition[key].append(row)
    policy_hash = policy_payload_sha256(spec)
    membership: list[dict[str, Any]] = []
    for partition in sorted(by_partition, key=lambda x: tuple(str(v) for v in x)):
        group = sorted(by_partition[partition], key=lambda row: (_episode_anchor_ns(row, spec), row["event_id"]))
        parent = list(range(len(group)))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i: int, j: int) -> None:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[max(ri, rj)] = min(ri, rj)

        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if _temporal_link(group[i], group[j], spec) and _spatial_link(group[i], group[j], spec):
                    union(i, j)
        components: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for i, row in enumerate(group):
            components[find(i)].append(row)
        for component in components.values():
            ordered = sorted(component, key=lambda row: (_episode_anchor_ns(row, spec), row["event_id"]))
            anchor = ordered[0]
            episode_id = canonical_sha256({
                "policy_payload_sha256": policy_hash,
                "partition": list(partition),
                "anchor_zone_event_id": anchor["event_id"],
            })
            for rank, row in enumerate(ordered):
                out = {
                    "schema_version": EPISODE_EVENT_SCHEMA,
                    "episode_id": episode_id,
                    "identity_sha256": "",
                    "zone_event_id": row["event_id"],
                    "zone_identity_sha256": row["identity_sha256"],
                    "instrument": row["instrument"],
                    "contract": row["contract"],
                    "session_id": str(row["session_id"]),
                    "config_id": row["config_id"],
                    "created_ts_utc_ns": int(row["created_ts_utc_ns"]),
                    "availability_ts_utc_ns": int(row["availability_ts_utc_ns"]),
                    "lower_tick": int(row["lower_tick"]),
                    "upper_tick": int(row["upper_tick"]),
                    "episode_anchor_zone_event_id": anchor["event_id"],
                    "is_primary_anchor": rank == 0,
                    "member_rank": rank,
                    "membership_reason": "CONNECTED_BY_FROZEN_CREATION_GEOMETRY",
                    "policy_payload_sha256": policy_hash,
                    "future_price_path_accessed": False,
                    "pnl_accessed": False,
                    "holdout_touched": False,
                }
                membership.append(stamp_identity(out, spec["episode_membership_contract"]))
    return normalize_rows(membership, spec["episode_membership_contract"])
