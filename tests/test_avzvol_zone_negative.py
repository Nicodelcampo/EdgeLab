"""Invented detector tape only; never loads bars, ticks or outcomes."""
import pytest
from edgelab.kaggle.avzvol_zone_negative import classify_detector_window, ZoneNegativeError

def block(end=9, **changes):
    return {'session': '2026-09-21', 'block_end_bar': end, 'available_bar': end,
        'threshold': 2.0, 'calibration_samples': 20,
        'baseline_last_session': '2026-09-18', 'detected_zone_count': 0, **changes}

def classify(rows, **changes):
    return classify_detector_window(rows, **{'session': '2026-09-21',
        'session_first_bar': 0, 'window_first_bar': 0, 'anchor_bar': 19,
        'holdout_start': '2026-10-01', 'block_bars': 10,
        'minimum_calibration_samples': 20, **changes})

def test_complete_calibrated_zero_is_negative_not_market_certification():
    r = classify([block(), block(19)])
    assert r['classification'] == 'DETECTOR_NEGATIVE'
    assert r['racimo_absence'] == 'NOT_ASSESSED'
    assert r['expected_block_count'] == r['usable_block_count'] == 2
    for k in ['consolidation_geometry_verified', 'source_quality_certified',
              'tape_authenticity_verified', 'census_completeness_verified',
              'scientific_rule_approved', 'research_authorized', 'outcomes_computed',
              'holdout_utc_boundary_verified']:
        assert r[k] is False

@pytest.mark.parametrize('changes', [{'threshold': -1}, {'threshold': 0},
    {'threshold': None}, {'threshold': float('nan')}, {'threshold': float('inf')},
    {'threshold': True}, {'calibration_samples': 19}, {'calibration_samples': None},
    {'baseline_last_session': None}, {'baseline_last_session': '2026-09-21'},
    {'baseline_last_session': '2026-09-22'}, {'available_bar': 20},
    {'available_bar': 8}, {'detected_zone_count': None}, {'detected_zone_count': -1}])
def test_unknown_or_unavailable_block_never_becomes_negative(changes):
    assert classify([block(**changes), block(19)])['classification'] == 'UNKNOWN'

def test_missing_block_retained_not_imputed():
    r = classify([block(19)])
    assert r['classification'] == 'UNKNOWN'
    assert r['expected_block_count'] == 2 and r['observed_in_window_block_count'] == 1
    assert 'MISSING_DETECTOR_BLOCK' in r['unknown_reasons']

def test_observed_zone_does_not_require_racimo_or_final_zone_state():
    r = classify([block(detected_zone_count=1), block(19)])
    assert r['classification'] == 'DETECTED_ZONE'
    assert r['known_detected_zone_count'] == 1
    assert r['racimo_absence'] == 'NOT_ASSESSED'

def test_positive_with_missing_coverage_retains_unknown_reasons():
    r = classify([block(detected_zone_count=1)])
    assert r['classification'] == 'DETECTED_ZONE'
    assert 'MISSING_DETECTOR_BLOCK' in r['unknown_reasons']

def test_future_append_cannot_backdate_classification():
    rows = [block(), block(19)]
    assert classify(rows) == classify(rows + [block(29, detected_zone_count=99),
        block(9, session='2026-10-01', detected_zone_count=99)])

def test_other_session_does_not_fill_missing_current_block():
    r = classify([block(session='2026-09-18'), block(19)])
    assert r['classification'] == 'UNKNOWN'

@pytest.mark.parametrize('changes', [{'window_first_bar': 1}, {'anchor_bar': 18},
    {'session_first_bar': 10}, {'anchor_bar': 0}])
def test_partial_or_cross_session_windows_never_negative(changes):
    rows = [] if changes.get('session_first_bar') else [block()]
    assert classify(rows, **changes)['classification'] == 'UNKNOWN'

@pytest.mark.parametrize('rows', [[block(), block()], [block(8)], [block(o5=1)],
    [block(state=2)], [block(racimo_id=1)]])
def test_duplicates_offschedule_outcomes_and_final_state_rejected(rows):
    with pytest.raises(ZoneNegativeError):
        classify(rows)

@pytest.mark.parametrize('changes', [{'session': '2026-10-01'}, {'block_bars': 0},
    {'minimum_calibration_samples': 0}, {'anchor_bar': True}, {'window_first_bar': 20}])
def test_invalid_or_reserved_window_stops(changes):
    with pytest.raises(ZoneNegativeError):
        classify([], **changes)
