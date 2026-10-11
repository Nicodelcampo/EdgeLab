#!/usr/bin/env python3
"""Pinned exposed-export FOOTER audit; no price/outcome payload or market replay."""
from pathlib import Path
import argparse
import hashlib
import json
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
AUDIT_SHA = '1611277b3dc6f6393e0c6f280201359f488b8352e80a23bf9c77149e8152192e'
CRITICAL_GROUPS = {
    'causal_band_identity': ['band_snapshot_id', 'band_known_utc_ns', 'band_known_sequence'],
    'retest_observation': ['retest_bar_id', 'retest_available_utc_ns'],
    'confirmation_decision': ['decision_bar_id', 'decision_available_utc_ns', 'trigger_policy_id'],
    'decision_close': ['close_ticks', 'bar_available_utc_ns'],
    'decision_context_identity': ['context_snapshot_id', 'context_available_utc_ns'],
    'independent_control_identity': ['own_census_id', 'negative_classification_asof_id'],
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def capture_gaps(names):
    """Literal field inventory, NOT semantic certification or row-level validation."""
    return {group: [key for key in keys if key not in set(names)]
            for group, keys in CRITICAL_GROUPS.items()}


def footer_summary(pf):
    names = pf.schema_arrow.names
    require(len(names) == len(set(names)) and 'session' in names, 'ambiguous schema/session')
    require(set(pf.schema.names) == set(names), 'nested or inconsistent schema unsupported')
    session_column = names.index('session')
    sessions = []
    group_rows = []
    for i in range(pf.num_row_groups):
        rg = pf.metadata.row_group(i)
        stats = rg.column(session_column).statistics
        require(stats is not None and stats.has_min_max and stats.has_null_count,
                'unknown session partition')
        require(stats.null_count == 0 and stats.min >= 19000101 and stats.max < 20261001,
                'reserved or unknown partition; STOP before payload')
        group_rows.append(rg.num_rows)
        sessions.append([int(stats.min), int(stats.max)])
    require(sum(group_rows) == pf.metadata.num_rows and pf.metadata.num_rows > 0,
            'footer row-count cross-foot failed')
    return {'rows': pf.metadata.num_rows, 'row_groups': pf.num_row_groups,
            'row_group_sum_independent': sum(group_rows),
            'session_min': min(x[0] for x in sessions),
            'session_max': max(x[1] for x in sessions),
            'columns': names, 'capture_gaps': capture_gaps(names),
            'literal_capture_fields_complete': not any(capture_gaps(names).values())}


def run(inventory, out_dir):
    ref = ROOT / 'docs/infra/AVZVOL_AUDIT_20261010.json'
    require(digest(ref) == AUDIT_SHA, 'export reference changed')
    pins = {x['file']: x for x in json.loads(ref.read_text())['covariate_audit']['files']}
    inv = json.loads(Path(inventory).read_text())
    paths = {Path(x['file']).name: Path(x['file']) for x in inv}
    require(len(inv) == len(paths) == 6 and set(paths) == set(pins), 'exact six-export universe required')
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    plan = {'scope': 'FOOTER_ONLY_EXPOSED_EXPORT_OBSERVABILITY_NOT_STATE_REPLAY',
            'payload_columns_read': [], 'critical_field_groups': CRITICAL_GROUPS,
            'selection': 'all six originally pinned exposed exports, all rows retained',
            'missingness': 'schema-wide unavailable field, NOT row null or invalid historical outcome',
            'independent_count_check': 'sum row-group footer counts vs file footer vs original pin',
            'decision': 'cannot directly evaluate a new H2 confirmation from legacy export schema',
            'scientific_policy_chosen': False,
            'comparison_plan': [{'grain': 'schema availability across pinned files',
                                 'disposition': 'prose',
                                 'reason': 'uniform absence of event trace; no effect, rate or temporal chart'}]}
    (out / 'analysis-plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    files = []
    for name in sorted(paths):
        file = paths[name]
        require(digest(file) == pins[name]['sha256'], 'export hash mismatch: ' + name)
        summary = footer_summary(pq.ParquetFile(file))
        require(summary['rows'] == pins[name]['rows'], 'pinned footer row mismatch')
        files.append({'file': name, 'sha256': pins[name]['sha256'], **summary})
    rows = sum(x['rows'] for x in files)
    require(rows == sum(p['rows'] for p in pins.values()), 'independent pin total mismatch')
    evidence = {'schema': 'edgelab_avzvol_trigger_observability_audit_v1',
                'status': 'CAPTURE_GAPS_CONFIRMED_NOT_NEW_MARKET_EFFECT',
                'source_export_reference_sha256': AUDIT_SHA,
                'recipe_sha256': digest(__file__), 'plan': plan,
                'files': files, 'rows_represented_by_footers': rows,
                'files_with_complete_literal_capture_fields': sum(x['literal_capture_fields_complete'] for x in files),
                'rows_in_files_with_complete_literal_capture_fields': sum(x['rows'] for x in files if x['literal_capture_fields_complete']),
                'independent_footer_count_checks_completed': True,
                'capture_requirements_ref': 'config/research/avzvol_interaction_capture_v1.json',
                'interpretation': 'Missing exact capture fields are inventory evidence, not a complete semantic validator. Historical endpoints remain valid for their original descriptive questions. New confirmation outcomes remain unmeasured.',
                **{key: False for key in ['payload_read', 'outcome_columns_read', 'raw_price_payload_read',
                    'market_census_built', 'new_market_outcomes_computed', 'economic_outcomes_computed',
                    'holdout_payload_read', 'source_quality_certified', 'controls_zone_free_certified',
                    'research_release_authorized', 'entry_rule_promoted', 'historical_outputs_modified']}}
    (out / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--allow-exposed-footer-audit', action='store_true', required=True)
    args = parser.parse_args()
    try:
        e = run(args.inventory, args.out_dir)
        print(json.dumps({key: e[key] for key in ['status', 'rows_represented_by_footers',
              'files_with_complete_literal_capture_fields', 'payload_read']}))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'STOP', 'reason': str(exc)}))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
