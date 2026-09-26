"""Canonical futures-contract regime for all downstream EdgeLab analysis.

The policy is deliberately causal: contract selection for CME trade date D uses
only total traded volume from the previous complete trade date. A later-dated
contract becomes active on D when it was the strict volume leader on D-1.
Once the chain advances it never rolls backwards.

This module does not splice or back-adjust prices. It assigns the actual
contract that would have been tradable, and exposes fail-closed guards so every
tick, bar, event, zone and trade can prove which regime it belongs to.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

SCHEMA_VERSION = "contract_regime_manifest_v1"
POLICY_ID = "previous_complete_session_volume_leader_monotonic_v1"
TIMEZONE = "America/Chicago"
SESSION_TEMPLATE = "CME_GLOBEX_17:00_TO_16:00_CT"
VOLUME_DEFINITION = "sum_trade_quantity_by_cme_trade_date"


class ContractRegimeError(ValueError):
    """Raised when contract identity or roll evidence is incomplete/invalid."""


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _ymd(value: Any, field: str) -> int:
    try:
        out = int(value)
    except (TypeError, ValueError) as exc:
        raise ContractRegimeError(f"{field} must be YYYYMMDD integer") from exc
    text = str(out)
    if len(text) != 8:
        raise ContractRegimeError(f"{field} must be YYYYMMDD integer")
    return out


def _normalize_contracts(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in rows:
        required = {
            "root", "contract", "expiry_ordinal", "first_trade_date", "last_trade_date"
        }
        missing = required - set(raw)
        if missing:
            raise ContractRegimeError(f"contract metadata missing {sorted(missing)}")
        root = str(raw["root"]).strip().upper()
        contract = str(raw["contract"]).strip()
        if not root or not contract:
            raise ContractRegimeError("root and contract must be non-empty")
        key = (root, contract)
        if key in seen:
            raise ContractRegimeError(f"duplicate contract metadata: {key}")
        seen.add(key)
        first = _ymd(raw["first_trade_date"], "first_trade_date")
        last = _ymd(raw["last_trade_date"], "last_trade_date")
        if first > last:
            raise ContractRegimeError(f"contract coverage is reversed: {key}")
        expiry = int(raw["expiry_ordinal"])
        if expiry < 190001 or expiry > 299912:
            raise ContractRegimeError(f"invalid expiry_ordinal for {key}: {expiry}")
        out.append(
            {
                "root": root,
                "contract": contract,
                "expiry_ordinal": expiry,
                "first_trade_date": first,
                "last_trade_date": last,
            }
        )
    if not out:
        raise ContractRegimeError("at least one contract is required")
    return sorted(out, key=lambda x: (x["root"], x["expiry_ordinal"], x["contract"]))


def _normalize_volumes(
    rows: Iterable[Mapping[str, Any]],
) -> dict[tuple[str, str, int], dict[str, Any]]:
    out: dict[tuple[str, str, int], dict[str, Any]] = {}
    for raw in rows:
        required = {"root", "contract", "trade_date", "volume", "complete_session"}
        missing = required - set(raw)
        if missing:
            raise ContractRegimeError(f"daily volume row missing {sorted(missing)}")
        root = str(raw["root"]).strip().upper()
        contract = str(raw["contract"]).strip()
        trade_date = _ymd(raw["trade_date"], "trade_date")
        key = (root, contract, trade_date)
        if key in out:
            raise ContractRegimeError(f"duplicate daily volume row: {key}")
        volume = float(raw["volume"])
        if volume < 0 or volume != volume:
            raise ContractRegimeError(f"invalid volume for {key}: {volume}")
        complete = raw["complete_session"]
        if not isinstance(complete, bool):
            raise ContractRegimeError(f"complete_session must be boolean for {key}")
        out[key] = {"volume": volume, "complete_session": complete}
    return out


def _leader(
    candidates: Sequence[dict[str, Any]],
    volumes: Mapping[str, float],
    current: str | None,
) -> str:
    max_volume = max(volumes[c["contract"]] for c in candidates)
    tied = [c for c in candidates if volumes[c["contract"]] == max_volume]
    if current is not None and any(c["contract"] == current for c in tied):
        return current
    return min(tied, key=lambda c: (c["expiry_ordinal"], c["contract"]))["contract"]


def _segments(
    daily: list[dict[str, Any]], calendar_index: Mapping[int, int]
) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    previous_date: int | None = None
    for row in daily:
        if not row["eligible"]:
            if current is not None:
                current["end_trade_date_exclusive"] = row["trade_date"]
                segments.append(current)
                current = None
            previous_date = row["trade_date"]
            continue
        contiguous = (
            previous_date is not None
            and calendar_index[row["trade_date"]] == calendar_index[previous_date] + 1
        )
        same = current is not None and current["contract"] == row["active_contract"]
        if current is None or not contiguous or not same:
            if current is not None:
                current["end_trade_date_exclusive"] = row["trade_date"]
                segments.append(current)
            current = {
                "root": row["root"],
                "contract": row["active_contract"],
                "start_trade_date": row["trade_date"],
                "end_trade_date_exclusive": None,
                "roll_in_signal_trade_date": row["signal_trade_date"],
                "left_censored": not bool(segments),
                "right_censored": False,
            }
        previous_date = row["trade_date"]
    if current is not None:
        current["right_censored"] = True
        segments.append(current)
    for segment in segments:
        segment["regime_id"] = canonical_sha256(
            {
                "policy_id": POLICY_ID,
                "root": segment["root"],
                "contract": segment["contract"],
                "start_trade_date": segment["start_trade_date"],
                "roll_in_signal_trade_date": segment["roll_in_signal_trade_date"],
            }
        )
    return segments


def build_contract_regime(
    *,
    contracts: Iterable[Mapping[str, Any]],
    daily_volumes: Iterable[Mapping[str, Any]],
    calendar_trade_dates: Sequence[int],
    source_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Build an immutable, causal contract schedule.

    `calendar_trade_dates` must be the complete ordered research calendar.
    Contract coverage must be rectangular: for every date between each
    contract's declared first/last trade dates there must be one daily row,
    including explicit zero volume. Missing or incomplete rows make the next
    date ineligible rather than silently choosing another contract.
    """
    meta = _normalize_contracts(contracts)
    volumes = _normalize_volumes(daily_volumes)
    calendar = [_ymd(d, "calendar_trade_date") for d in calendar_trade_dates]
    if not calendar or calendar != sorted(set(calendar)):
        raise ContractRegimeError("calendar_trade_dates must be unique and ascending")
    if not source_identity:
        raise ContractRegimeError("source_identity is required")
    calendar_index = {d: i for i, d in enumerate(calendar)}
    metadata_keys = {(c["root"], c["contract"]) for c in meta}
    unknown = sorted({(r, c) for r, c, _d in volumes} - metadata_keys)
    if unknown:
        raise ContractRegimeError(f"volume rows reference unknown contracts: {unknown}")

    by_root: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for contract in meta:
        by_root[contract["root"]].append(contract)

    all_daily: list[dict[str, Any]] = []
    all_intervals: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for root, chain in sorted(by_root.items()):
        current: str | None = None
        expiry = {c["contract"]: c["expiry_ordinal"] for c in chain}
        root_daily: list[dict[str, Any]] = []
        for i, trade_date in enumerate(calendar):
            if i == 0:
                root_daily.append(
                    {
                        "root": root,
                        "trade_date": trade_date,
                        "signal_trade_date": None,
                        "active_contract": None,
                        "eligible": False,
                        "decision": "NO_PRIOR_SESSION",
                        "leader_contract": None,
                        "current_volume": None,
                        "leader_volume": None,
                        "leader_over_current": None,
                    }
                )
                continue
            signal_date = calendar[i - 1]
            covered = [
                c for c in chain
                if c["first_trade_date"] <= signal_date <= c["last_trade_date"]
            ]
            missing = [
                c["contract"] for c in covered
                if (root, c["contract"], signal_date) not in volumes
                or not volumes[(root, c["contract"], signal_date)]["complete_session"]
            ]
            if not covered or missing:
                decision = "NO_CONTRACT_COVERAGE" if not covered else "SOURCE_INCOMPLETE"
                root_daily.append(
                    {
                        "root": root,
                        "trade_date": trade_date,
                        "signal_trade_date": signal_date,
                        "active_contract": current,
                        "eligible": False,
                        "decision": decision,
                        "leader_contract": None,
                        "current_volume": None,
                        "leader_volume": None,
                        "leader_over_current": None,
                    }
                )
                diagnostics.append(
                    {
                        "root": root,
                        "trade_date": trade_date,
                        "signal_trade_date": signal_date,
                        "code": decision,
                        "contracts": sorted(missing),
                    }
                )
                continue
            observed = {
                c["contract"]: volumes[(root, c["contract"], signal_date)]["volume"]
                for c in covered
            }
            if current is None:
                lead = _leader(covered, observed, None)
                current = lead
                decision = "INITIALIZE_FROM_PRIOR_VOLUME"
                current_volume = observed[current]
                leader_volume = current_volume
                ratio = None
            else:
                current_meta = next((c for c in covered if c["contract"] == current), None)
                if current_meta is None:
                    root_daily.append(
                        {
                            "root": root,
                            "trade_date": trade_date,
                            "signal_trade_date": signal_date,
                            "active_contract": current,
                            "eligible": False,
                            "decision": "CURRENT_CONTRACT_NOT_COVERED",
                            "leader_contract": None,
                            "current_volume": None,
                            "leader_volume": None,
                            "leader_over_current": None,
                        }
                    )
                    diagnostics.append(
                        {
                            "root": root,
                            "trade_date": trade_date,
                            "signal_trade_date": signal_date,
                            "code": "CURRENT_CONTRACT_NOT_COVERED",
                            "contracts": [current],
                        }
                    )
                    continue
                forward = [c for c in covered if c["expiry_ordinal"] >= expiry[current]]
                lead = _leader(forward, observed, current)
                current_volume = observed[current]
                leader_volume = observed[lead]
                ratio = None if current_volume == 0 else leader_volume / current_volume
                if expiry[lead] > expiry[current] and leader_volume > current_volume:
                    current = lead
                    decision = "ROLL_FORWARD"
                else:
                    decision = "HOLD"
            root_daily.append(
                {
                    "root": root,
                    "trade_date": trade_date,
                    "signal_trade_date": signal_date,
                    "active_contract": current,
                    "eligible": True,
                    "decision": decision,
                    "leader_contract": lead,
                    "current_volume": current_volume,
                    "leader_volume": leader_volume,
                    "leader_over_current": ratio,
                }
            )
        intervals = _segments(root_daily, calendar_index)
        for row in root_daily:
            row["regime_id"] = None
            if row["eligible"]:
                for interval in intervals:
                    start = interval["start_trade_date"]
                    end = interval["end_trade_date_exclusive"]
                    if interval["contract"] == row["active_contract"] and start <= row["trade_date"] and (
                        end is None or row["trade_date"] < end
                    ):
                        row["regime_id"] = interval["regime_id"]
                        break
                if row["regime_id"] is None:
                    raise ContractRegimeError("internal interval assignment failure")
        all_daily.extend(root_daily)
        all_intervals.extend(intervals)

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "policy_id": POLICY_ID,
        "timezone": TIMEZONE,
        "session_template": SESSION_TEMPLATE,
        "volume_definition": VOLUME_DEFINITION,
        "signal_lag_sessions": 1,
        "strict_crossover": True,
        "monotonic_expiry": True,
        "tie_rule": "KEEP_CURRENT_ELSE_EARLIEST_EXPIRY",
        "price_adjustment": "NONE_ACTUAL_TRADED_PRICES",
        "state_boundary": "RESET_AT_CONTRACT_ROLL",
        "source_identity": dict(source_identity),
        "calendar_trade_dates": calendar,
        "contracts": meta,
        "daily_assignments": all_daily,
        "intervals": all_intervals,
        "diagnostics": diagnostics,
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    validate_contract_regime(manifest)
    return manifest


def validate_contract_regime(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ContractRegimeError("wrong contract regime schema")
    if manifest.get("policy_id") != POLICY_ID:
        raise ContractRegimeError("wrong rollover policy")
    if manifest.get("signal_lag_sessions") != 1:
        raise ContractRegimeError("rollover must use exactly one prior complete session")
    if manifest.get("price_adjustment") != "NONE_ACTUAL_TRADED_PRICES":
        raise ContractRegimeError("microstructure regime cannot back-adjust prices")
    if manifest.get("state_boundary") != "RESET_AT_CONTRACT_ROLL":
        raise ContractRegimeError("state must reset at a contract roll")
    expected = canonical_sha256({k: v for k, v in manifest.items() if k != "manifest_sha256"})
    if manifest.get("manifest_sha256") != expected:
        raise ContractRegimeError("manifest hash mismatch")
    expiry = {
        (c["root"], c["contract"]): int(c["expiry_ordinal"])
        for c in manifest.get("contracts", [])
    }
    last_expiry: dict[str, int] = {}
    seen_dates: set[tuple[str, int]] = set()
    for row in manifest.get("daily_assignments", []):
        key = (row["root"], int(row["trade_date"]))
        if key in seen_dates:
            raise ContractRegimeError(f"duplicate daily assignment: {key}")
        seen_dates.add(key)
        if row["eligible"]:
            contract = row.get("active_contract")
            if not contract or not row.get("regime_id"):
                raise ContractRegimeError(f"eligible assignment lacks identity: {key}")
            exp = expiry[(row["root"], contract)]
            prior = last_expiry.get(row["root"])
            if prior is not None and exp < prior:
                raise ContractRegimeError(f"contract chain rolled backwards: {key}")
            last_expiry[row["root"]] = exp


def contract_for_trade_date(
    manifest: Mapping[str, Any], root: str, trade_date: int
) -> dict[str, str]:
    validate_contract_regime(manifest)
    root = str(root).upper()
    trade_date = _ymd(trade_date, "trade_date")
    matches = [
        row for row in manifest["daily_assignments"]
        if row["root"] == root and int(row["trade_date"]) == trade_date
    ]
    if len(matches) != 1:
        raise ContractRegimeError(f"no unique regime for {(root, trade_date)}")
    row = matches[0]
    if not row["eligible"]:
        raise ContractRegimeError(
            f"ineligible regime for {(root, trade_date)}: {row['decision']}"
        )
    return {
        "contract": row["active_contract"],
        "regime_id": row["regime_id"],
        "roll_manifest_sha256": manifest["manifest_sha256"],
    }


def assert_rows_follow_regime(
    rows: Iterable[Mapping[str, Any]], manifest: Mapping[str, Any]
) -> None:
    """Fail if any downstream row uses the wrong or an unlabeled contract."""
    for index, row in enumerate(rows):
        required = {"root", "contract", "trade_date", "regime_id", "roll_manifest_sha256"}
        missing = required - set(row)
        if missing:
            raise ContractRegimeError(f"row {index} missing regime fields {sorted(missing)}")
        expected = contract_for_trade_date(manifest, row["root"], row["trade_date"])
        observed = {key: row[key] for key in ("contract", "regime_id", "roll_manifest_sha256")}
        if observed != expected:
            raise ContractRegimeError(
                f"row {index} contract regime mismatch: {observed} != {expected}"
            )


def assert_run_manifest_uses_regime(
    run_manifest: Mapping[str, Any], regime_manifest: Mapping[str, Any]
) -> None:
    """Require every analytical run to pin the exact contract-roll schedule."""
    validate_contract_regime(regime_manifest)
    expected = regime_manifest["manifest_sha256"]
    observed = run_manifest.get("roll_schedule_sha256")
    if observed != expected:
        raise ContractRegimeError(
            f"run manifest roll_schedule_sha256 mismatch: {observed!r} != {expected}"
        )
