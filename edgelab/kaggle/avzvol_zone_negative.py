"""Proposed causal detector-negative tape classifier, NOT a market census.

Inputs are declarations, not verified coverage, clock, detector or liquidity.
No loader, outcomes, matcher, research permission or scientific acceptance.
"""
from __future__ import annotations
from datetime import date
import math

class ZoneNegativeError(ValueError):
    pass

KEYS = {'session', 'block_end_bar', 'available_bar', 'threshold',
        'calibration_samples', 'baseline_last_session', 'detected_zone_count'}

def _integer(x, name):
    if type(x) is not int or x < 0:
        raise ZoneNegativeError(f'{name}: nonnegative integer required')
    return x

def _date(x):
    try:
        d = date.fromisoformat(x)
    except (TypeError, ValueError) as exc:
        raise ZoneNegativeError('canonical ISO session date required') from exc
    if x != d.isoformat():
        raise ZoneNegativeError('canonical ISO session date required')
    return d

def classify_detector_window(observations, *, session, session_first_bar,
        window_first_bar, anchor_bar, holdout_start, block_bars,
        minimum_calibration_samples):
    """Proposed conservative rule; classification of a DECLARED tape only.

    A negative requires ALL scheduled fully contained blocks, prior-session
    calibration and as-of zero zone counts. Missing, partial, unavailable or
    uncalibrated blocks yield UNKNOWN. A valid observed zone yields DETECTED_ZONE
    even with unknown coverage. Future records cannot change a prior decision.
    Without a detected zone here is NOT without a racimo at anchor, not physical
    absence and not proof of consolidation. Holdout trade-date guard ONLY.
    """
    reserved, target = _date(holdout_start), _date(session)
    if target >= reserved:
        raise ZoneNegativeError('reserved trade date')
    for name, value in [('session_first_bar', session_first_bar),
            ('window_first_bar', window_first_bar), ('anchor_bar', anchor_bar),
            ('block_bars', block_bars),
            ('minimum_calibration_samples', minimum_calibration_samples)]:
        _integer(value, name)
    if block_bars == 0 or minimum_calibration_samples == 0:
        raise ZoneNegativeError('explicit positive block/calibration sizes required')
    if anchor_bar < window_first_bar:
        raise ZoneNegativeError('window cannot end before it starts')
    if not isinstance(observations, list):
        raise ZoneNegativeError('explicit list of observations required')
    reasons = []
    if window_first_bar < session_first_bar:
        reasons.append('WINDOW_CROSSES_DECLARED_SESSION_START')
    aligned = (window_first_bar >= session_first_bar
        and (window_first_bar-session_first_bar) % block_bars == 0
        and (anchor_bar-session_first_bar+1) % block_bars == 0)
    if not aligned:
        reasons.append('PARTIAL_DETECTOR_BLOCK_AT_WINDOW_BOUNDARY')
    # Every completed block intersecting the window, not a convenient subset.
    expected = [b for b in range(session_first_bar+block_bars-1, anchor_bar+1,
        block_bars) if b >= window_first_bar and b-block_bars+1 <= anchor_bar]
    if not expected:
        reasons.append('NO_COMPLETE_BLOCK_COVERAGE')
    indexed = {}
    for row in observations:
        if not isinstance(row, dict) or set(row) != KEYS:
            raise ZoneNegativeError('exact detector-only schema; no outcomes/final states')
        row_session = _date(row['session'])
        end = _integer(row['block_end_bar'], 'block_end_bar')
        if row_session > target or (row_session == target and end > anchor_bar):
            continue
        if row_session != target or end < window_first_bar:
            continue
        if end not in expected:
            raise ZoneNegativeError('off-schedule detector block in declared window')
        if end in indexed:
            raise ZoneNegativeError('duplicate block; no silent deduplication')
        indexed[end] = row
    details, known_zone_count = [], 0
    for end in expected:
        row, problems = indexed.get(end), []
        if row is None:
            problems.append('MISSING_DETECTOR_BLOCK')
        else:
            available = row['available_bar']
            if type(available) is not int or available < end or available > anchor_bar:
                problems.append('DECISION_NOT_AVAILABLE_AT_ANCHOR')
            samples = row['calibration_samples']
            if type(samples) is not int or samples < minimum_calibration_samples:
                problems.append('INSUFFICIENT_OR_UNKNOWN_CALIBRATION')
            threshold = row['threshold']
            if (type(threshold) not in (int, float)
                    or not math.isfinite(threshold) or threshold <= 0):
                problems.append('NONPOSITIVE_OR_UNKNOWN_THRESHOLD')
            baseline = row['baseline_last_session']
            if baseline is None:
                problems.append('BASELINE_ASOF_UNKNOWN')
            elif _date(baseline) >= target:
                problems.append('BASELINE_NOT_PRIOR_SESSION')
            count = row['detected_zone_count']
            if type(count) is not int or count < 0:
                problems.append('ZONE_COUNT_UNKNOWN')
            if not problems:
                known_zone_count += count
        details.append({'block_end_bar': end,
            'observation_usable_as_declared': not problems,
            'unknown_reasons': problems})
        reasons.extend(problems)
    status = ('DETECTED_ZONE' if known_zone_count > 0
              else 'UNKNOWN' if reasons else 'DETECTOR_NEGATIVE')
    return {'schema': 'edgelab_avzvol_detector_negative_window_v1',
        'classification': status, 'session': session,
        'window_first_bar': window_first_bar, 'anchor_bar': anchor_bar,
        'block_bars': block_bars,
        'minimum_calibration_samples': minimum_calibration_samples,
        'expected_block_count': len(expected),
        'observed_in_window_block_count': len(indexed),
        'usable_block_count': sum(x['observation_usable_as_declared'] for x in details),
        'known_detected_zone_count': known_zone_count,
        'unknown_reasons': sorted(set(reasons)), 'blocks': details,
        'racimo_absence': 'NOT_ASSESSED',
        **{k: False for k in ['consolidation_geometry_verified',
            'source_quality_certified', 'tape_authenticity_verified',
            'census_completeness_verified', 'scientific_rule_approved',
            'research_authorized', 'outcomes_computed',
            'holdout_utc_boundary_verified']}}
