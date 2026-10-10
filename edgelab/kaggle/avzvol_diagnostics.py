"""Target-free AVZVOL design diagnostics; no file/network access or acceptance.

All rows are declarations. This cannot verify zone absence, census completeness,
source quality or causal feature construction. Callers need external permission
BEFORE supplying market-derived covariates. An own-census OUTCOME benchmark is
not implemented by descriptive pre-anchor covariate comparisons.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from fractions import Fraction
import math

from edgelab.kaggle.avzvol_design import (
    AVZVOLDesignError, FEATURES, STRATA, _utc, plan_covariate_matches,
)


def _finite(value):
    if not math.isfinite(value):
        raise AVZVOLDesignError('diagnostic overflow; no clipping or imputation')
    return value


def _normalized(weights):
    total = sum(weights.values(), Fraction())
    return {key: weight / total for key, weight in sorted(weights.items())} if total else {}


def _uniform(ids):
    ids = sorted(ids)
    return {key: Fraction(1, len(ids)) for key in ids} if ids else {}


def _mean(rows, weights, feature):
    try:
        return _finite(math.fsum(float(w) * rows[key]['features'][feature]
                                for key, w in weights.items()))
    except OverflowError as exc:
        raise AVZVOLDesignError('diagnostic overflow; no clipping or imputation') from exc


def _ecdf_gap(rows, left, right, feature):
    """Descriptive maximum weighted ECDF gap, ties advanced together; NOT KS test."""
    increments = defaultdict(lambda: [Fraction(), Fraction()])
    for key, weight in left.items():
        increments[rows[key]['features'][feature]][0] += weight
    for key, weight in right.items():
        increments[rows[key]['features'][feature]][1] += weight
    a = b = maximum = Fraction()
    for value in sorted(increments):
        da, db = increments[value]
        a += da; b += db
        maximum = max(maximum, abs(a - b))
    return float(maximum)


def _comparison(rows, left, right, scales):
    left, right = _normalized(left), _normalized(right)
    if not left or not right:
        return {'status': 'NOT_COMPUTABLE_EMPTY_POPULATION', 'left_unique_events': len(left),
                'right_unique_events': len(right), 'features': {f: None for f in FEATURES}}
    features = {}
    for f in FEATURES:
        lm, rm = _mean(rows, left, f), _mean(rows, right, f)
        features[f] = {
            'left_mean': lm, 'right_mean': rm,
            'mean_gap_in_external_scale_units': _finite((lm - rm) / scales[f]),
            'maximum_weighted_ecdf_gap': _ecdf_gap(rows, left, right, f),
        }
    return {'status': 'DESCRIPTIVE_ONLY_NO_ACCEPTANCE', 'left_unique_events': len(left),
            'right_unique_events': len(right), 'features': features}


def describe_control_census(real_rows, candidate_rows, *, policy, holdout_start):
    """Recompute deterministic matching; do not trust editable supplied pairs/weights.

    Compare within EXACT strata: all vs supported reals, supported reals vs
    analysis-weighted controls, selected UNIQUE controls vs declared census,
    and analysis-weighted controls vs that same census. No pooled own-census
    comparison, empirical SD, acceptance threshold, p/CI/ESS or outcome endpoint.
    Candidate census is not restricted to chosen controls or loosened calipers.
    Known real-anchor aliases in the candidate census cause STOP rather than
    silently deleting them from this diagnostic's reference population.
    """
    plan = plan_covariate_matches(real_rows, candidate_rows, policy=policy,
                                  holdout_start=holdout_start)
    anchors = {(r['contract'], r['session'], _utc(r['anchor_utc'])) for r in real_rows}
    if any((r['contract'], r['session'], _utc(r['anchor_utc'])) in anchors for r in candidate_rows):
        raise AVZVOLDesignError('own-census reference contains a known real-anchor alias')
    rows = {r['event_id']: r for r in real_rows + candidate_rows}
    real_strata, control_strata = defaultdict(list), defaultdict(list)
    for r in real_rows:
        real_strata[tuple(r[k] for k in STRATA)].append(r['event_id'])
    for r in candidate_rows:
        control_strata[tuple(r[k] for k in STRATA)].append(r['event_id'])
    supported = {g['real_id'] for g in plan['groups'] if g['status'] == 'SUPPORTED'}
    count = Counter(p['real_id'] for p in plan['pairs'])
    control_mass = defaultdict(Fraction)
    pair_mass = []
    for p in plan['pairs']:
        weight = Fraction(1, len(supported)) * Fraction(1, count[p['real_id']])
        control_mass[p['control_id']] += weight
        pair_mass.append((p, weight))
    # Fractions derive from the equal-real design, not rounded pair float weights.
    if pair_mass and sum((w for _, w in pair_mass), Fraction()) != 1:
        raise AVZVOLDesignError('internal analysis weights do not sum to one')
    per_stratum = []
    for key in sorted(set(real_strata) | set(control_strata)):
        reals, census = sorted(real_strata[key]), sorted(control_strata[key])
        supported_ids = [r for r in reals if r in supported]
        selected = [c for c in census if c in control_mass]
        analysis = {c: control_mass[c] for c in selected}
        per_stratum.append({
            'stratum': dict(zip(STRATA, key)),
            'real_events': len(reals), 'supported_real_events': len(supported_ids),
            'unsupported_real_events': len(reals) - len(supported_ids),
            'support_fraction': len(supported_ids) / len(reals) if reals else None,
            'declared_candidate_census_events': len(census),
            'selected_unique_controls': len(selected),
            'unselected_candidate_events': len(census) - len(selected),
            'analysis_mass': float(sum(analysis.values(), Fraction())),
            'comparisons': {
                'supported_reals_vs_all_reals': _comparison(rows, _uniform(supported_ids),
                    _uniform(reals), policy['scales']),
                'supported_reals_vs_analysis_controls': _comparison(rows, _uniform(supported_ids),
                    analysis, policy['scales']),
                'selected_unique_controls_vs_declared_census': _comparison(rows, _uniform(selected),
                    _uniform(census), policy['scales']),
                'analysis_controls_vs_declared_census': _comparison(rows, analysis,
                    _uniform(census), policy['scales']),
            },
        })
    pair_gaps = {}
    for feature in FEATURES:
        if not pair_mass:
            pair_gaps[feature] = None
            continue
        scaled = [(_finite((rows[p['real_id']]['features'][feature] -
                    rows[p['control_id']]['features'][feature]) / policy['scales'][feature]), w)
                  for p, w in pair_mass]
        try:
            pair_gaps[feature] = {
                'mean_signed_gap': _finite(math.fsum(g * float(w) for g, w in scaled)),
                'mean_absolute_gap': _finite(math.fsum(abs(g) * float(w) for g, w in scaled)),
                'maximum_absolute_gap': max(abs(g) for g, _ in scaled),
            }
        except OverflowError as exc:
            raise AVZVOLDesignError('diagnostic overflow; no clipping or imputation') from exc
    normalized = _normalized(control_mass)
    return {
        'schema': 'edgelab_avzvol_control_census_diagnostic_v1',
        'status': 'DESCRIPTIVE_COVARIATE_DESIGN_ONLY_UNADJUDICATED',
        'policy_sha256': plan['policy_sha256'],
        'declared_input_sha256': plan['declared_input_sha256'],
        'declared_holdout_start': plan['declared_holdout_start'],
        'real_event_count': plan['real_event_count'],
        'declared_candidate_census_count': plan['candidate_census_count'],
        'matched_real_event_count': len(supported),
        'unsupported_real_event_count': plan['unsupported_real_event_count'],
        'selected_unique_control_count': len(control_mass),
        'control_reuse_counts': plan['control_reuse_counts'],
        'control_analysis_weights': {c: float(w) for c, w in normalized.items()},
        'maximum_control_analysis_weight': float(max(normalized.values())) if normalized else None,
        'control_weight_concentration_sum_squares': float(sum((w*w for w in normalized.values()),
                                                            Fraction())) if normalized else None,
        'per_stratum': per_stratum,
        'pair_gaps_in_external_scale_units': pair_gaps,
        'own_census_population': 'FULL_DECLARED_CANDIDATE_CENSUS_WITHIN_EACH_EXACT_STRATUM',
        'reference_census_is_matching_eligible_subset': False,
        'matched_population': 'SUPPORTED_REALS_ONLY_NOT_ALL_REALS',
        'ecdf_metric_is_hypothesis_test': False,
        'scale_metric_is_standardized_mean_difference': False,
        'weight_concentration_is_independent_sample_size': False,
        'balance_accepted': False, 'support_accepted': False,
        'zone_absence_verified': False, 'census_completeness_verified': False,
        'source_quality_certified': False, 'research_authorized': False,
        'own_census_outcome_benchmark_implemented': False,
        'inference_implemented': False, 'outcomes_read': False, 'pnl_computed': False,
        'economic_outcomes_computed': False, 'bias_adjudicated': False,
    }
