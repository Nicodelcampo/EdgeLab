"""Opt-in AVZVOL covariate match design; no loader, outcomes or authorization.

Inputs are declarations, not proof of clock/coverage/approval. A caller must
obtain reviewed source lineage and permissions BEFORE constructing these rows.
This module never authenticates data and never runs a scientific contrast.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
import hashlib
import json
import math

FEATURES = ('occ', 'amp', 'trend_magnitude', 'momentum',
            'vol_occ', 'vol_100', 'dur_occ', 'dur_100')
STRATA = ('contract', 'session', 'cell', 'clock_bucket', 'trend_sign')
ROW_KEYS = {'event_id', *STRATA, 'anchor_utc', 'feature_asof_utc',
            'prewindow_complete', 'features'}
POLICY_KEYS = {'schema', 'calipers', 'scales', 'min_controls', 'max_controls',
               'minimum_separation_seconds'}


class AVZVOLDesignError(ValueError):
    pass


def _number(value, *, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise AVZVOLDesignError('finite numeric value required')
    if (positive and value <= 0) or (not positive and value < 0):
        raise AVZVOLDesignError('invalid nonnegative/positive bound')
    return float(value)


def _utc(value):
    if not isinstance(value, str):
        raise AVZVOLDesignError('explicit UTC timestamp required')
    try:
        ts = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise AVZVOLDesignError('invalid UTC timestamp') from exc
    if ts.utcoffset() is None or ts.utcoffset().total_seconds() != 0:
        raise AVZVOLDesignError('UTC timestamp, not implicit local time')
    return ts.astimezone(timezone.utc)


def _policy(policy):
    if not isinstance(policy, dict) or set(policy) != POLICY_KEYS or policy['schema'] != 'edgelab_avzvol_match_policy_v1':
        raise AVZVOLDesignError('exact externally frozen policy required')
    for key in ('calipers', 'scales'):
        if not isinstance(policy[key], dict) or set(policy[key]) != set(FEATURES):
            raise AVZVOLDesignError('all covariate bounds/scales must be explicit')
        for value in policy[key].values():
            _number(value, positive=key == 'scales')
    low, high = policy['min_controls'], policy['max_controls']
    if type(low) is not int or type(high) is not int or not 1 <= low <= high:
        raise AVZVOLDesignError('explicit positive min/max controls required')
    _number(policy['minimum_separation_seconds'])
    return hashlib.sha256(json.dumps(policy, sort_keys=True, allow_nan=False,
                                    separators=(',', ':')).encode()).hexdigest()


def _rows(rows, holdout_start):
    if not isinstance(rows, list) or not rows:
        raise AVZVOLDesignError('nonempty real and full candidate declarations required')
    parsed = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != ROW_KEYS:
            raise AVZVOLDesignError('exact covariate-only row schema; no outcome fields')
        for key in ('event_id', 'contract', 'cell', 'clock_bucket'):
            if not isinstance(row[key], str) or not row[key].strip():
                raise AVZVOLDesignError('missing identity/stratum')
        if type(row['trend_sign']) is not int or row['trend_sign'] not in (-1, 0, 1):
            raise AVZVOLDesignError('invalid frozen trend sign')
        try:
            session = date.fromisoformat(row['session'])
        except (ValueError, TypeError) as exc:
            raise AVZVOLDesignError('ISO trade date required') from exc
        if row['session'] != session.isoformat() or session >= holdout_start:
            raise AVZVOLDesignError('reserved or noncanonical trade date')
        anchor, asof = _utc(row['anchor_utc']), _utc(row['feature_asof_utc'])
        # Conservative UTC boundary in addition to trade date. No claim that
        # this models CME's earlier evening session boundary; upstream must.
        if anchor.date() >= holdout_start or asof > anchor:
            raise AVZVOLDesignError('reserved anchor or future feature declaration')
        if row['prewindow_complete'] is not True:
            raise AVZVOLDesignError('incomplete prewindow; no silent repair/drop')
        if not isinstance(row['features'], dict) or set(row['features']) != set(FEATURES):
            raise AVZVOLDesignError('exact finite pre-anchor covariates required')
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in row['features'].values()):
            raise AVZVOLDesignError('no covariate imputation/nonfinite values')
        parsed.append((row, anchor))
    return parsed


def plan_covariate_matches(real_rows, candidate_rows, *, policy, holdout_start):
    """Deterministic design with equal weight per SUPPORTED real event.

    Candidates can be reused across reals, not duplicated within one set.
    Full supplied candidate census is kept; no population absence inferred.
    Disjoint session inference and population gate are NOT implemented here.
    No automatic caliper relaxation, weights by available count or promotion.
    """
    digest = _policy(policy)
    try:
        reserved = date.fromisoformat(holdout_start)
    except (ValueError, TypeError) as exc:
        raise AVZVOLDesignError('campaign-specific holdout required') from exc
    reals, candidates = _rows(real_rows, reserved), _rows(candidate_rows, reserved)
    ids = [r['event_id'] for r, _ in reals + candidates]
    if len(set(ids)) != len(ids):
        raise AVZVOLDesignError('duplicate IDs across/within real and candidate census')
    declared_input_digest = hashlib.sha256(json.dumps(
        {'real': sorted(real_rows, key=lambda r: r['event_id']),
         'candidates': sorted(candidate_rows, key=lambda r: r['event_id'])},
        sort_keys=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest()
    real_anchors = {(r['contract'], r['session'], t) for r, t in reals}
    pool = defaultdict(list)
    for row, ts in candidates:
        pool[tuple(row[k] for k in STRATA)].append((row, ts))
    groups, pairs, reuse, supported = [], [], Counter(), []
    for real, ts in sorted(reals, key=lambda x: x[0]['event_id']):
        valid = []
        for control, ct in pool[tuple(real[k] for k in STRATA)]:
            if (control['contract'], control['session'], ct) in real_anchors:
                continue  # Never a real anchor relabelled as a control.
            if abs((ct-ts).total_seconds()) < policy['minimum_separation_seconds']:
                continue
            diffs = {f: abs(control['features'][f]-real['features'][f]) for f in FEATURES}
            if any(diffs[f] > policy['calipers'][f] for f in FEATURES):
                continue
            distance = math.fsum(diffs[f]/policy['scales'][f] for f in FEATURES)
            if not math.isfinite(distance):
                raise AVZVOLDesignError('nonfinite distance from extreme covariates/scales')
            valid.append((distance, control['event_id'], control))
        chosen = sorted(valid, key=lambda x: (x[0], x[1]))[:policy['max_controls']]
        status = 'SUPPORTED' if len(chosen) >= policy['min_controls'] else 'UNSUPPORTED_NO_CALIPER_RELAXATION'
        used = chosen if status == 'SUPPORTED' else []
        groups.append({'real_id': real['event_id'], 'status': status,
                       'eligible_candidate_count': len(valid), 'controls_used': len(used)})
        if used:
            means = {f: math.fsum(c['features'][f]/len(used) for _, _, c in used) for f in FEATURES}
            supported.append((real, means))
        for distance, control_id, _ in used:
            pair_id = hashlib.sha256(json.dumps([digest, declared_input_digest, real['event_id'], control_id],
                                               separators=(',', ':')).encode()).hexdigest()
            pairs.append({'pair_id': pair_id, 'real_id': real['event_id'], 'control_id': control_id,
                          'distance': distance, 'within_real_control_weight': 1/len(used)})
            reuse[control_id] += 1
    matched = len(supported)
    for pair in pairs:
        pair['real_weight'] = 1/matched
        pair['analysis_weight'] = pair['real_weight']*pair['within_real_control_weight']
    balance = {f: (math.fsum((r['features'][f]-m[f])/policy['scales'][f]
                           for r, m in supported)/matched if matched else None) for f in FEATURES}
    return {'schema': 'edgelab_avzvol_match_design_v1', 'status': 'DESIGN_ONLY_UNADJUDICATED',
            'policy_sha256': digest, 'declared_input_sha256': declared_input_digest,
            'declared_holdout_start': holdout_start,
            'real_event_count': len(reals), 'candidate_census_count': len(candidates),
            'matched_real_event_count': matched, 'unsupported_real_event_count': len(reals)-matched,
            'support_fraction': matched/len(reals), 'groups': groups, 'pairs': pairs,
            'candidate_census_ids': sorted(r['event_id'] for r, _ in candidates),
            'control_reuse_counts': dict(sorted(reuse.items())),
            'mean_covariate_gap_in_frozen_scale_units': balance,
            'population': 'SUPPORTED_REALS_ONLY_NOT_ALL_REALS',
            'balance_accepted': False, 'source_quality_certified': False,
            'census_completeness_verified': False, 'inference_implemented': False,
            'research_authorized': False, 'outcomes_read': False,
            'pnl_computed': False, 'bias_adjudicated': False}
