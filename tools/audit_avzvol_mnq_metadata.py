#!/usr/bin/env python3
"""Read-only AVZVOL candidate MNQ metadata review. NEVER a quality/research PASS.

Reads JSON only. No ticks, prices, outcomes, loader import, network or new kernel.
Source summaries and a resolver can agree and both be wrong upstream.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

CT = ZoneInfo('America/Chicago')
UTC = timezone.utc
HOLDOUT = '2026-10-01'


class MetadataReviewError(ValueError):
    pass


def _unique(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise MetadataReviewError('duplicate JSON key')
        obj[key] = value
    return obj


def _metadata_path(path):
    p = Path(path)
    if p.suffix.lower() != '.json' or not p.is_file() or p.stat().st_size > 16 * 1024 * 1024:
        raise MetadataReviewError('bounded JSON metadata file required')
    return p


def read_json(path):
    return json.loads(_metadata_path(path).read_text(), object_pairs_hook=_unique)


def _day(text):
    if not isinstance(text, str):
        raise MetadataReviewError('non-string date')
    try:
        d = date.fromisoformat(text)
    except ValueError as exc:
        raise MetadataReviewError('invalid ISO date') from exc
    if d.isoformat() != text:
        raise MetadataReviewError('noncanonical ISO date')
    return d


def _ns(dt):
    delta = dt.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return (delta.days * 86400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1000


def historical_window(first_date, last_date):
    """Exactly legacy pandas absolute 45-day/16-hour arithmetic, including DST."""
    first = datetime.combine(_day(first_date), datetime.min.time(), CT).astimezone(UTC)
    last = datetime.combine(_day(last_date), datetime.min.time(), CT).astimezone(UTC)
    cutoff = datetime(2026, 9, 30, 22, tzinfo=UTC)
    return _ns(first - timedelta(days=45)), _ns(first), min(_ns(last + timedelta(hours=16)), _ns(cutoff))


def validate_summaries(summaries):
    if not isinstance(summaries, dict) or not summaries:
        raise MetadataReviewError('source summaries must be a nonempty date map')
    cutoff = _ns(datetime(2026, 9, 30, 22, tzinfo=UTC))
    for key, row in summaries.items():
        if not isinstance(key, str) or len(key) != 8 or not key.isdigit():
            raise MetadataReviewError('invalid source date label')
        _day(f'{key[:4]}-{key[4:6]}-{key[6:]}')
        if not isinstance(row, dict):
            raise MetadataReviewError('invalid source summary')
        for field in ('ticks', 'first', 'last'):
            if type(row.get(field)) is not int:
                raise MetadataReviewError('summary integer required')
        if row['ticks'] <= 0 or not 0 < row['first'] <= row['last'] < cutoff:
            raise MetadataReviewError('invalid/holdout-overlapping source summary')
        gap = row.get('max_gap_s')
        if type(gap) not in (int, float) or not math.isfinite(gap) or gap < 0:
            raise MetadataReviewError('invalid declared gap')


def review_metadata(resolver, catalog, lineage, summaries_by_contract):
    if resolver.get('holdout_first_trade_date') != HOLDOUT:
        raise MetadataReviewError('unexpected resolver holdout')
    inputs = lineage.get('candidate_inputs')
    if not isinstance(inputs, list) or len(inputs) != 6:
        raise MetadataReviewError('six frozen candidate contracts required')
    contracts = [r.get('contract') for r in inputs]
    if len(set(contracts)) != 6 or set(contracts) != set(summaries_by_contract):
        raise MetadataReviewError('duplicate/missing/unexpected candidate contract')
    rows = resolver['instruments']['MNQ']['sessions']
    if not isinstance(rows, list):
        raise MetadataReviewError('resolver sessions must be rows')
    selected = []
    seen = set()
    for r in rows:
        d = _day(r['date'])
        if type(r.get('approved')) is not bool or type(r.get('trades')) is not int or r['trades'] < 0:
            raise MetadataReviewError('invalid resolver approval/count')
        if r['date'] in seen:
            raise MetadataReviewError('duplicate resolver session date')
        seen.add(r['date'])
        if r['approved'] and '2025-07-01' <= d.isoformat() < HOLDOUT:
            selected.append(r)
    if {r['contract'] for r in selected} != set(contracts):
        raise MetadataReviewError('resolver candidate universe changed')
    results = []
    for candidate in inputs:
        contract = candidate['contract']; s = summaries_by_contract[contract]
        validate_summaries(s)
        chosen = [r for r in selected if r['contract'] == contract]
        counts = Counter((r['dataset'], r['file']) for r in chosen)
        pair = min(counts, key=lambda p: (-counts[p], p))
        if pair != (candidate['chosen_dataset'], candidate['file']):
            raise MetadataReviewError('candidate source choice changed')
        first, last = min(r['date'] for r in chosen), max(r['date'] for r in chosen)
        a, midnight, b = historical_window(first, last)
        missing = [r['date'] for r in chosen if r['date'].replace('-', '') not in s]
        mismatches = [r['date'] for r in chosen if r['date'].replace('-', '') in s and
                      r['trades'] != s[r['date'].replace('-', '')]['ticks']]
        intersect = {k: v for k, v in s.items() if v['last'] >= a and v['first'] < b}
        warm = {k: v for k, v in intersect.items() if v['first'] < midnight}
        approved_keys = {r['date'].replace('-', '') for r in chosen}
        extra = [k for k in intersect if k not in approved_keys]
        # A summary intersecting a boundary does not identify ticks inside that boundary.
        first_declared = min((v['first'] for v in intersect.values()), default=None)
        results.append({
            'contract': contract, 'candidate_dataset_ref': candidate['dataset_ref'],
            'candidate_version': candidate['candidate_dataset_version'],
            'approved_session_count': len(chosen), 'missing_approved_summary_dates': missing,
            'approved_trade_count_mismatch_dates': mismatches,
            'source_summary_tick_total': sum(v['ticks'] for v in s.values()),
            'legacy_read_window_start_utc_ns': a, 'first_approved_midnight_utc_ns': midnight,
            'legacy_read_window_end_utc_ns_exclusive': b,
            'warmup_intersecting_summary_count': len(warm),
            'unapproved_or_warmup_summary_labels_in_read_window': extra,
            'leading_no_declared_observation_ns': None if first_declared is None else max(0, first_declared - a),
            'boundary_straddling_summary_labels': [k for k, v in intersect.items() if v['first'] < a or v['last'] >= b],
            'declared_gap_review_required': True, 'complete_session_certified': False,
            'warmup_liquidity_certified': False, 'historical_consumption_verified': False,
        })
    rolls = catalog['instruments']['MNQ']['rolls']
    roll_review = []
    for r in rolls:
        d = _day(r['previous_session'])
        values = (r['volume_old'], r['volume_new'])
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
            raise MetadataReviewError('invalid declared roll volume')
        roll_review.append({'from': r['from'], 'to': r['to'], 'previous_session': d.isoformat(),
                            'previous_label_weekday': d.weekday(), 'declared_previous_volumes_positive': all(v > 0 for v in values),
                            'complete_previous_session_verified': False, 'all_challenger_sources_verified': False,
                            'liquid_roll_certified': False})
    return {'schema': 'edgelab_avzvol_mnq_metadata_review_v1',
            'status': 'REQUIRES_SOURCE_QUALITY_REVIEW', 'research_authorized': False,
            'raw_quality_certified': False, 'historical_bias_adjudicated': False,
            'calendar_certified': False, 'clock_certified': False, 'liquidity_certified': False,
            'new_market_trials': 0, 'price_payload_read': False,
            'method': 'Source-declared session summaries vs candidate resolver; legacy absolute warmup boundaries; no raw scan or historical mount proof. Label != reviewed exchange session; extra labels are NOT a measured number of detector-contaminating sessions.',
            'metadata_grain': 'one producer-declared source date label per contract, not independent trades or certified exchange sessions',
            'selection_rules_declared_by_resolver': resolver['rules'],
            'selection_rule_asof_review_required': True,
            'detector_before_approved_mask_source_review': 'v1 source calls zp2_run before appr = isin; existing code inspected, impact NOT quantified',
            'contracts': results, 'rolls': roll_review,
            'required_reviews': ['physical raw-byte pin and structure', 'historical calendar and source UTC conversion',
                                 'all read dates including warmup/rejected dates and intraday gaps',
                                 'full prior-session challenger census and complete-session evidence',
                                 'ex-ante eligibility thresholds rather than full-sample masks',
                                 'historical consumption and exposure, distinct from fresh data approval']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('resolver', 'catalog', 'lineage', 'sessions-index', 'out'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    try:
        index = read_json(args.sessions_index)
        if not isinstance(index, list):
            raise MetadataReviewError('sessions index must be a list')
        protected = {Path(p).resolve() for p in (args.resolver, args.catalog, args.lineage, args.sessions_index)}
        protected.update(Path(row['path']).resolve() for row in index)
        if Path(args.out).resolve() in protected:
            raise MetadataReviewError('output must not overwrite an input document')
        summaries = {}; pins = []
        for row in index:
            if row['contract'] in summaries:
                raise MetadataReviewError('duplicate indexed contract')
            path = _metadata_path(row['path']); raw = path.read_bytes()
            actual = hashlib.sha256(raw).hexdigest()
            if actual != row['sha256']:
                raise MetadataReviewError('source metadata byte pin mismatch')
            summaries[row['contract']] = read_json(path)
            pins.append({'contract': row['contract'], 'artifact': path.name, 'measured_sha256': actual,
                         'downloaded_bytes': len(raw), 'historic_mount_verified': False})
        report = review_metadata(read_json(args.resolver), read_json(args.catalog), read_json(args.lineage), summaries)
        report['source_summary_metadata_pins'] = pins
        report['document_input_pins'] = [{'role': role, 'measured_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}
                                        for role, path in [('resolver', args.resolver), ('catalog', args.catalog), ('lineage', args.lineage)]]
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        print(json.dumps({'status': report['status'], 'research_authorized': False,
                          'meaning_of_exit_0': 'metadata review completed, NEVER quality/research approval'}))
        return 0
    except (MetadataReviewError, ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'status': 'STOP_METADATA_REVIEW', 'research_authorized': False, 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
