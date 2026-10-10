"""Metadata-only eligibility checks. Integrity is not permission or adjudication.

An external campaign authority must pin independently reviewed evidence and limits.
This module opens no files and cannot authenticate that authority. Existing readers
are NOT protected by importing it. See docs/COMPONENT_DATA.md.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
from collections.abc import Mapping
from edgelab.data.contract_regime import validate_contract_regime, ContractRegimeError

REQUIRED_CHECKS = ("schema", "source_sha256", "timezone_dst", "tick_grid",
    "timestamp_sequence", "duplicate_identity", "bid_ask", "volume_semantics",
    "session_coverage", "contract_identity")

class DataEligibilityError(ValueError):
    """Missing, inconsistent or non-eligible evidence; never silently bypass."""


def seal(value):
    """Canonical finite JSON hash, NOT signature, approval or sanitizer."""
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise DataEligibilityError("evidence must be finite JSON") from exc
    return hashlib.sha256(raw).hexdigest()


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _map(value, name):
    if not isinstance(value, Mapping):
        raise DataEligibilityError(name + ": expected object")
    return value


def _day(value):
    if isinstance(value, bool) or not isinstance(value, int) or len(str(value)) != 8:
        raise DataEligibilityError("trade date must be integer YYYYMMDD")
    try:
        datetime.strptime(str(value), "%Y%m%d")
    except ValueError:
        raise DataEligibilityError("invalid trade date") from None
    return value


def _number(value, name, *, zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DataEligibilityError(name + ": expected numeric measurement")
    try:
        n = float(value)
    except OverflowError:
        raise DataEligibilityError(name + ": overflow") from None
    if not math.isfinite(n) or n < 0 or (not zero and n == 0):
        raise DataEligibilityError(name + ": invalid measurement")
    return n


def require_research_eligibility(*, certificate, regime_manifest, root, trade_date,
        liquidity_limits, expected_certificate_sha256, expected_regime_sha256,
        expected_liquidity_limits_sha256):
    """Validate one requested session using caller-pinned, reviewed evidence.

    No universal liquidity floor, calendar, holdout boundary or review is invented.
    SANITIZED_VERIFIED is an input assertion, not a verdict emitted by this code.
    All three hashes must come from external approved campaign metadata, NOT be
    recalculated from arbitrary current inputs by a production caller.
    """
    certificate = _map(certificate, "certificate")
    regime_manifest = _map(regime_manifest, "regime manifest")
    liquidity_limits = _map(liquidity_limits, "liquidity limits")
    for obj, expected, label in (
        (certificate, expected_certificate_sha256, "certificate"),
        ({k:v for k,v in regime_manifest.items() if k != "manifest_sha256"}, expected_regime_sha256, "regime"),
        (liquidity_limits, expected_liquidity_limits_sha256, "liquidity limits"),
    ):
        if not _sha(expected) or seal(obj) != expected:
            raise DataEligibilityError(label + ": unpinned/mismatched hash")
    try:
        validate_contract_regime(regime_manifest)
    except (ContractRegimeError, KeyError, TypeError, ValueError, OverflowError) as exc:
        raise DataEligibilityError("invalid causal regime manifest") from exc
    if not isinstance(root, str) or not root or root != root.strip().upper():
        raise DataEligibilityError("root must be explicit canonical uppercase")
    if type(regime_manifest.get("signal_lag_sessions")) is not int:
        raise DataEligibilityError("signal lag must be integer one")
    day = _day(trade_date)
    if certificate.get("status") != "SANITIZED_VERIFIED":
        raise DataEligibilityError("data lacks reviewed sanitation assertion")
    checks = _map(certificate.get("checks"), "checks")
    if any(checks.get(k) != "PASS" for k in REQUIRED_CHECKS):
        raise DataEligibilityError("missing/failed sanitation checks")
    identity = certificate.get("source_identity")
    if not isinstance(identity, Mapping) or not identity or identity != regime_manifest.get("source_identity"):
        raise DataEligibilityError("source identity mismatch")
    boundary = _day(certificate.get("holdout_first_trade_date"))
    allowed = certificate.get("allowed_trade_dates")
    if not isinstance(allowed, list) or not allowed:
        raise DataEligibilityError("missing approved trade dates")
    allowed = [_day(d) for d in allowed]
    if allowed != sorted(set(allowed)) or any(d >= boundary for d in allowed):
        raise DataEligibilityError("invalid approved trade dates / holdout conflict")
    if day >= boundary or day not in allowed:
        raise DataEligibilityError("holdout/unapproved trade date")
    calendar = regime_manifest.get("calendar_trade_dates")
    if not isinstance(calendar, list) or not calendar:
        raise DataEligibilityError("missing full trading calendar")
    calendar = [_day(d) for d in calendar]
    if calendar != sorted(set(calendar)) or day not in calendar:
        raise DataEligibilityError("invalid full trading calendar")
    if liquidity_limits.get("root") != root or liquidity_limits.get("frozen_before_strategy") is not True:
        raise DataEligibilityError("missing root-specific frozen limits")
    min_vol = _number(liquidity_limits.get("min_previous_session_volume"), "minimum volume")
    max_spread = _number(liquidity_limits.get("max_previous_session_spread_p99_ticks"), "maximum spread", zero=True)
    rows = regime_manifest.get("daily_assignments")
    if not isinstance(rows, list) or any(not isinstance(x, Mapping) for x in rows):
        raise DataEligibilityError("invalid daily assignments")
    for assignment in rows:
        _day(assignment.get("trade_date"))
    matches = [x for x in rows if x.get("root") == root and x.get("trade_date") == day]
    if len(matches) != 1:
        raise DataEligibilityError("no unique contract assignment")
    row = matches[0]
    if row.get("eligible") is not True or not row.get("active_contract") or not row.get("regime_id"):
        raise DataEligibilityError("ineligible/unlabeled regime")
    prior = _day(row.get("signal_trade_date"))
    index = calendar.index(day)
    if index == 0 or calendar[index - 1] != prior:
        raise DataEligibilityError("selection must use previous calendar session")
    contract = row["active_contract"]
    sessions = _map(certificate.get("sessions"), "sessions")
    session = _map(sessions.get(f"{root}|{contract}|{prior}"), "prior session")
    if session.get("complete_session") is not True or session.get("status") != "PASS":
        raise DataEligibilityError("prior session incomplete/not audited")
    quantity = _number(session.get("trade_quantity"), "observed previous volume")
    spread = _number(session.get("spread_p99_ticks"), "observed prior spread", zero=True)
    if quantity < min_vol or spread > max_spread:
        raise DataEligibilityError("insufficient observed liquidity")
    if row.get("decision") not in ("INITIALIZE_FROM_PRIOR_VOLUME", "HOLD", "ROLL_FORWARD"):
        raise DataEligibilityError("unknown eligible decision")
    reported = row.get("leader_volume") if row["decision"] == "ROLL_FORWARD" else row.get("current_volume")
    if _number(reported, "selected volume") != quantity:
        raise DataEligibilityError("volume evidence mismatch")
    target = _map(sessions.get(f"{root}|{contract}|{day}"), "target session")
    if target.get("status") != "PASS" or target.get("complete_session") is not True:
        raise DataEligibilityError("target coverage incomplete/not audited")
    return {"root": root, "contract": contract, "trade_date": day,
            "regime_id": row["regime_id"], "roll_schedule_sha256": expected_regime_sha256,
            "data_certificate_sha256": expected_certificate_sha256,
            "liquidity_limits_sha256": expected_liquidity_limits_sha256,
            "promotion_allowed": False, "authority_authenticated": False}
