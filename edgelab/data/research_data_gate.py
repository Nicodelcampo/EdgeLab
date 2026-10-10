"""Fail-closed research gate, not a sanitizer. Call BEFORE market-data reads.
Existing callers are NOT automatically rewired by adding this module.
"""
from __future__ import annotations
import hashlib
import json
import math

REQUIRED_CHECKS = ('schema', 'source_sha256', 'timezone_dst', 'tick_grid',
    'timestamp_sequence', 'duplicate_identity', 'bid_ask', 'volume_semantics',
    'session_coverage', 'contract_identity')

class DataEligibilityError(ValueError):
    pass

def seal(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()

def _positive(value, name):
    if isinstance(value, bool):
        raise DataEligibilityError(name + ': boolean is not a measurement')
    try:
        n = float(value)
    except (ValueError, TypeError):
        raise DataEligibilityError(name + ': missing/non-numeric') from None
    if not math.isfinite(n) or n <= 0:
        raise DataEligibilityError(name + ': must be positive and finite')
    return n

def _day(value):
    from datetime import datetime
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataEligibilityError('trade date must be integer YYYYMMDD')
    try:
        datetime.strptime(str(value), '%Y%m%d')
    except ValueError:
        raise DataEligibilityError('invalid trade date') from None
    return value

def _sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)

def require_research_eligibility(*, certificate, regime_manifest, root,
        trade_date, liquidity_limits, expected_certificate_sha256,
        expected_regime_sha256):
    """Check measured data quality and D-1 liquidity under frozen per-root limits.

    Hashes provide integrity, NOT authentication or independent adjudication.
    Certificates must be produced and reviewed by an independent data audit.
    A caller must additionally run validate_contract_regime on its manifest.
    No absolute liquidity threshold or verified certificate is fabricated here.
    """
    if not _sha(expected_certificate_sha256) or not _sha(expected_regime_sha256):
        raise DataEligibilityError('expected evidence hashes must be pinned')
    if seal(certificate) != expected_certificate_sha256:
        raise DataEligibilityError('certificate hash mismatch')
    if not isinstance(regime_manifest, dict):
        raise DataEligibilityError('missing regime manifest')
    body = {k:v for k,v in regime_manifest.items() if k != 'manifest_sha256'}
    if seal(body) != expected_regime_sha256 or regime_manifest.get('manifest_sha256') != expected_regime_sha256:
        raise DataEligibilityError('regime hash mismatch')
    if regime_manifest.get('policy_id') != 'previous_complete_session_volume_leader_monotonic_v1':
        raise DataEligibilityError('non-causal/unrecognized roll policy')
    if regime_manifest.get('signal_lag_sessions') != 1 or regime_manifest.get('price_adjustment') != 'NONE_ACTUAL_TRADED_PRICES' or regime_manifest.get('state_boundary') != 'RESET_AT_CONTRACT_ROLL':
        raise DataEligibilityError('invalid execution/reset policy')
    if certificate.get('status') != 'SANITIZED_VERIFIED':
        raise DataEligibilityError('data is not independently verified sanitized')
    checks = certificate.get('checks', {})
    if any(checks.get(k) != 'PASS' for k in REQUIRED_CHECKS):
        raise DataEligibilityError('missing/failed sanitation checks')
    if not certificate.get('source_identity') or certificate.get('source_identity') != regime_manifest.get('source_identity'):
        raise DataEligibilityError('source identity mismatch')
    day = _day(trade_date)
    allowed = certificate.get('allowed_trade_dates', [])
    boundary = _day(certificate.get('holdout_first_trade_date'))
    if day >= boundary or day not in allowed:
        raise DataEligibilityError('holdout/unapproved trade date')
    if liquidity_limits.get('root') != root or liquidity_limits.get('frozen_before_strategy') is not True:
        raise DataEligibilityError('missing root-specific preregistered liquidity limits')
    min_vol = _positive(liquidity_limits.get('min_previous_session_volume'), 'min volume')
    max_spread = _positive(liquidity_limits.get('max_previous_session_spread_p99_ticks'), 'max spread')
    matches = [x for x in regime_manifest.get('daily_assignments', [])
               if x.get('root') == root and x.get('trade_date') == day]
    if len(matches) != 1:
        raise DataEligibilityError('no unique daily contract assignment')
    row = matches[0]
    if row.get('eligible') is not True or not row.get('active_contract') or not row.get('regime_id'):
        raise DataEligibilityError('ineligible/unlabeled regime')
    prior = _day(row.get('signal_trade_date'))
    calendar = regime_manifest.get('calendar_trade_dates', [])
    if not calendar or calendar != sorted(set(calendar)) or day not in calendar:
        raise DataEligibilityError('invalid full trading calendar')
    index = calendar.index(day)
    if index == 0 or calendar[index - 1] != prior:
        raise DataEligibilityError('selection is not based on the prior calendar session')
    contract = row['active_contract']
    key = f'{root}|{contract}|{prior}'
    session = certificate.get('sessions', {}).get(key, {})
    if session.get('complete_session') is not True or session.get('status') != 'PASS':
        raise DataEligibilityError('previous session incomplete/not audited')
    quantity = _positive(session.get('trade_quantity'), 'observed previous volume')
    try:
        spread = float(session['spread_p99_ticks'])
    except (KeyError, ValueError, TypeError):
        raise DataEligibilityError('missing prior spread measurement') from None
    if not math.isfinite(spread) or spread < 0 or quantity < min_vol or spread > max_spread:
        raise DataEligibilityError('insufficient observed liquidity')
    reported = row.get('leader_volume') if row.get('decision') == 'ROLL_FORWARD' else row.get('current_volume')
    if _positive(reported, 'regime selected volume') != quantity:
        raise DataEligibilityError('volume evidence mismatch')
    current_key = f'{root}|{contract}|{day}'
    if certificate.get('sessions', {}).get(current_key, {}).get('status') != 'PASS':
        raise DataEligibilityError('target session data coverage unverified')
    return {'root': root, 'contract': contract, 'trade_date': day,
            'regime_id': row['regime_id'], 'roll_schedule_sha256': expected_regime_sha256,
            'data_certificate_sha256': expected_certificate_sha256,
            'liquidity_limits_sha256': seal(liquidity_limits)}
