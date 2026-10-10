"""Metadata-only eligibility checks. Integrity is not permission or adjudication.

An external campaign authority must pin independently reviewed evidence and limits.
This module opens no files and cannot authenticate that authority. Existing readers
are NOT protected by importing it. See docs/COMPONENT_DATA.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
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


def _aware_time(value, name):
    if not isinstance(value, str):
        raise DataEligibilityError(name + ": explicit timezone-aware timestamp required")
    try:
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise DataEligibilityError(name + ": invalid timestamp") from None
    if value.tzinfo is None or value.utcoffset() is None:
        raise DataEligibilityError(name + ": timezone required")
    return value.astimezone(timezone.utc)


def _require_prior_challengers(certificate, manifest, root, day, prior, row):
    """Consistency of external D-1 evidence, NOT a calendar/universe certificate.

    Require every covered contract, including zero-volume or backward-expiry
    challengers. Zero must be observed/reviewed, not substituted for missing.
    No full-sample medians, prices, files, implicit floors or inferred availability.
    An external reviewer must attest universe and clock/cutoff truth; hashes do
    not authenticate them. Existing legacy loaders remain outside this gate.
    """
    review = _map(certificate.get("selection_review"), "selection review")
    if review.get("schema") != "edgelab_reviewed_prior_challengers_v1":
        raise DataEligibilityError("missing reviewed prior-challenger evidence")
    if review.get("root") != root:
        raise DataEligibilityError("challenger review root mismatch")
    for field in ("calendar_evidence_sha256", "universe_evidence_sha256"):
        if not _sha(review.get(field)):
            raise DataEligibilityError("missing external " + field)
    if any(review.get(k) != "PASS" for k in
           ("universe_review", "calendar_review", "asof_review")):
        raise DataEligibilityError("unreviewed universe/calendar/as-of selection")
    contracts = manifest.get("contracts")
    if not isinstance(contracts, list) or any(not isinstance(c, Mapping) for c in contracts):
        raise DataEligibilityError("invalid challenger universe")
    meta = [c for c in contracts if c.get("root") == root]
    if not meta:
        raise DataEligibilityError("missing challenger contract")
    for c in meta:
        if not isinstance(c.get("contract"), str) or not c["contract"]:
            raise DataEligibilityError("invalid challenger identity")
        if type(c.get("expiry_ordinal")) is not int:
            raise DataEligibilityError("invalid challenger expiry")
        if _day(c.get("first_trade_date")) > _day(c.get("last_trade_date")):
            raise DataEligibilityError("reversed challenger coverage")
    if len({c["contract"] for c in meta}) != len(meta):
        raise DataEligibilityError("duplicate challenger contract")
    if manifest.get("strict_crossover") is not True or manifest.get("monotonic_expiry") is not True:
        raise DataEligibilityError("challenger policy flags must be explicit booleans")
    if any(manifest.get(k) != v for k, v in {
            "tie_rule": "KEEP_CURRENT_ELSE_EARLIEST_EXPIRY",
            "volume_definition": "sum_trade_quantity_by_cme_trade_date",
            "timezone": "America/Chicago"}.items()):
        raise DataEligibilityError("unsupported or inconsistent challenger policy")
    if review.get("contract_metadata_sha256") != seal(sorted(meta, key=lambda c: c["contract"])):
        raise DataEligibilityError("challenger universe metadata mismatch")
    decisions = _map(review.get("decisions"), "selection decisions")
    proof = _map(decisions.get(f"{root}|{day}"), "selection decision")
    if not _sha(proof.get("evidence_sha256")) or proof.get("cutoff_review") != "PASS":
        raise DataEligibilityError("missing reviewed decision-cutoff evidence")
    if _day(proof.get("trade_date")) != day or _day(proof.get("signal_trade_date")) != prior:
        raise DataEligibilityError("challenger evidence not from D-1")
    close = _aware_time(proof.get("previous_session_close_utc"), "prior close")
    opened = _aware_time(proof.get("target_session_open_utc"), "target open")
    cutoff = _aware_time(proof.get("decision_cutoff_utc"), "decision cutoff")
    universe_available = _aware_time(proof.get("contract_metadata_available_at_utc"), "universe available at")
    if universe_available > cutoff:
        raise DataEligibilityError("challenger universe not available as-of decision")
    if not close <= cutoff <= opened or close >= opened:
        raise DataEligibilityError("decision cutoff outside reviewed close/open order")
    covered = [c for c in meta if c["first_trade_date"] <= prior <= c["last_trade_date"]]
    candidates = proof.get("candidate_contracts")
    if (not isinstance(candidates, list) or any(not isinstance(c, str) for c in candidates)
            or len(candidates) != len(set(candidates))
            or set(candidates) != {c["contract"] for c in covered} or not covered):
        raise DataEligibilityError("incomplete/extra/duplicate D-1 challenger census")
    sessions = _map(certificate.get("sessions"), "sessions")
    observed = {}
    for c in covered:
        name = c["contract"]
        measure = _map(sessions.get(f"{root}|{name}|{prior}"), "prior challenger " + name)
        if measure.get("status") != "PASS" or measure.get("complete_session") is not True:
            raise DataEligibilityError("prior challenger incomplete/not reviewed")
        if not _sha(measure.get("evidence_sha256")):
            raise DataEligibilityError("missing prior challenger evidence reference")
        available = _aware_time(measure.get("available_at_utc"), "measurement available at")
        if not close <= available <= cutoff:
            raise DataEligibilityError("prior challenger not available as-of decision")
        observed[name] = _number(measure.get("trade_quantity"), "challenger volume", zero=True)
    previous = [r for r in manifest["daily_assignments"]
                if r.get("root") == root and r.get("trade_date") == prior]
    if len(previous) != 1:
        raise DataEligibilityError("missing unique prior contract state")
    current = previous[0].get("active_contract")
    expiry = {c["contract"]: c["expiry_ordinal"] for c in covered}
    if current is not None and current not in observed:
        raise DataEligibilityError("prior active contract not covered")
    forward = covered if current is None else [c for c in covered if c["expiry_ordinal"] >= expiry[current]]
    maximum = max(observed[c["contract"]] for c in forward)
    tied = [c for c in forward if observed[c["contract"]] == maximum]
    leader = current if current in {c["contract"] for c in tied} else min(
        tied, key=lambda c: (c["expiry_ordinal"], c["contract"]))["contract"]
    if current is None:
        selected = leader; decision = "INITIALIZE_FROM_PRIOR_VOLUME"
        current_volume = observed[leader]
    elif expiry[leader] > expiry[current] and observed[leader] > observed[current]:
        selected = leader; decision = "ROLL_FORWARD"; current_volume = observed[current]
    else:
        selected = current; decision = "HOLD"; current_volume = observed[current]
    if observed[selected] <= 0:
        raise DataEligibilityError("no positive selected D-1 volume")
    if (row.get("active_contract") != selected or row.get("leader_contract") != leader
            or row.get("decision") != decision
            or _number(row.get("current_volume"), "reported current volume", zero=True) != current_volume
            or _number(row.get("leader_volume"), "reported leader volume", zero=True) != observed[leader]):
        raise DataEligibilityError("D-1 challenger evidence disagrees with causal selection")
    return proof["evidence_sha256"]


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
    selection_ref = _require_prior_challengers(certificate, regime_manifest, root, day, prior, row)
    target = _map(sessions.get(f"{root}|{contract}|{day}"), "target session")
    if target.get("status") != "PASS" or target.get("complete_session") is not True:
        raise DataEligibilityError("target coverage incomplete/not audited")
    return {"root": root, "contract": contract, "trade_date": day,
            "regime_id": row["regime_id"], "roll_schedule_sha256": expected_regime_sha256,
            "data_certificate_sha256": expected_certificate_sha256,
            "liquidity_limits_sha256": expected_liquidity_limits_sha256,
            "selection_review_evidence_sha256": selection_ref,
            "promotion_allowed": False, "authority_authenticated": False}
