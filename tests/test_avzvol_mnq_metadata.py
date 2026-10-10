"""Synthetic documentary QA only; no prices, ticks or adjudication."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import hashlib
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mnq_metadata', ROOT / 'tools/audit_avzvol_mnq_metadata.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def fixture():
    inputs, rows, sources = [], [], {}
    for i in range(6):
        contract = f'MNQ_SYNTHETIC_{i}'
        d = (datetime(2026, 1, 5) + timedelta(days=i * 7)).date().isoformat()
        ns = m._ns(datetime.fromisoformat(d).replace(tzinfo=timezone.utc))
        inputs.append({'contract': contract, 'chosen_dataset': 'synthetic-source', 'file': f'{contract}.json',
                       'dataset_ref': 'synthetic/source', 'candidate_dataset_version': 1})
        rows.append({'date': d, 'contract': contract, 'dataset': 'synthetic-source', 'file': f'{contract}.json',
                     'approved': True, 'trades': 10})
        sources[contract] = {d.replace('-', ''): {'ticks': 10, 'first': ns, 'last': ns + 1000, 'max_gap_s': 0.}}
    resolver = {'holdout_first_trade_date': m.HOLDOUT, 'rules': 'synthetic undeclared as-of rules',
                'instruments': {'MNQ': {'sessions': rows}}}
    catalog = {'instruments': {'MNQ': {'rolls': [{'from': inputs[0]['contract'], 'to': inputs[1]['contract'],
                                              'previous_session': '2026-01-09', 'volume_old': 10., 'volume_new': 20.}]}}}
    return resolver, catalog, {'candidate_inputs': inputs}, sources


def test_consistency_never_quality_approval():
    args = fixture(); before = copy.deepcopy(args); r = m.review_metadata(*args)
    assert args == before and r['status'] == 'REQUIRES_SOURCE_QUALITY_REVIEW'
    assert r['new_market_trials'] == 0 and len(r['contracts']) == 6
    assert all(not r[k] for k in ('research_authorized', 'raw_quality_certified', 'historical_bias_adjudicated',
                                 'calendar_certified', 'clock_certified', 'liquidity_certified', 'price_payload_read'))
    assert all(not c['complete_session_certified'] for c in r['contracts'])
    assert not r['rolls'][0]['liquid_roll_certified']


def test_missing_and_mismatched_approved_summaries_stay_visible():
    resolver, catalog, lineage, sources = fixture()
    c = lineage['candidate_inputs'][0]['contract']; key = next(iter(sources[c]))
    sources[c][key]['ticks'] = 9
    r = m.review_metadata(resolver, catalog, lineage, sources)
    assert r['contracts'][0]['approved_trade_count_mismatch_dates'] == [resolver['instruments']['MNQ']['sessions'][0]['date']]
    row = sources[c].pop(key); sources[c]['20260104'] = row
    r = m.review_metadata(resolver, catalog, lineage, sources)
    assert len(r['contracts'][0]['missing_approved_summary_dates']) == 1
    assert not r['research_authorized']


def test_sparse_warmup_is_not_approved_and_boundaries_are_not_actual_ticks():
    args = fixture(); c = args[2]['candidate_inputs'][0]['contract']
    a, midnight, b = m.historical_window('2026-01-05', '2026-01-05')
    args[3][c]['20251201'] = {'ticks': 1, 'first': a - 10, 'last': a + 10, 'max_gap_s': 0}
    r = m.review_metadata(*args)['contracts'][0]
    assert '20251201' in r['boundary_straddling_summary_labels']
    assert r['leading_no_declared_observation_ns'] == 0  # NOT completeness proof
    assert not r['warmup_liquidity_certified']


def test_dst_warmup_uses_absolute_45_days_not_naive_calendar_subtraction():
    a, midnight, b = m.historical_window('2025-12-17', '2026-03-16')
    assert midnight - a == 45 * 86400 * 1_000_000_000
    assert a == m._ns(datetime(2025, 11, 2, 6, tzinfo=timezone.utc))


@pytest.mark.parametrize('field,value', [('ticks', True), ('ticks', 0), ('first', 1.5), ('last', None),
                                         ('max_gap_s', True), ('max_gap_s', -1), ('max_gap_s', float('nan'))])
def test_malformed_source_summary_stops(field, value):
    args = fixture(); c = next(iter(args[3])); key = next(iter(args[3][c])); args[3][c][key][field] = value
    with pytest.raises(m.MetadataReviewError):
        m.review_metadata(*args)


def test_holdout_overlapping_summary_stops_before_any_market_data():
    args = fixture(); c = next(iter(args[3])); row = next(iter(args[3][c].values()))
    row['last'] = m._ns(datetime(2026, 9, 30, 22, tzinfo=timezone.utc))
    with pytest.raises(m.MetadataReviewError):
        m.review_metadata(*args)


def test_duplicate_resolver_dates_and_candidate_change_stop():
    args = fixture(); args[0]['instruments']['MNQ']['sessions'] *= 2
    with pytest.raises(m.MetadataReviewError):
        m.review_metadata(*args)
    args = fixture(); args[2]['candidate_inputs'][0]['file'] = 'changed'
    with pytest.raises(m.MetadataReviewError):
        m.review_metadata(*args)


def test_duplicate_json_keys_are_not_silently_overwritten(tmp_path):
    p = tmp_path / 'duplicate.json'; p.write_text('{"a": 1, "a": 2}')
    with pytest.raises(m.MetadataReviewError):
        m.read_json(p)


def test_cli_exit_zero_is_review_not_pass_and_pin_mismatch_stops(tmp_path, capsys):
    resolver, catalog, lineage, sources = fixture(); paths = []
    for name, value in [('resolver', resolver), ('catalog', catalog), ('lineage', lineage)]:
        p = tmp_path / (name + '.json'); p.write_text(json.dumps(value)); paths.extend(['--' + name, str(p)])
    index = []
    for c, s in sources.items():
        p = tmp_path / (c + '.json'); p.write_text(json.dumps(s)); index.append({'contract': c, 'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    p = tmp_path / 'index.json'; p.write_text(json.dumps(index)); out = tmp_path / 'out.json'
    argv = paths + ['--sessions-index', str(p), '--out', str(out)]
    assert m.main(argv) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'REQUIRES_SOURCE_QUALITY_REVIEW'
    before = out.read_bytes(); index[0]['sha256'] = 'a' * 64; p.write_text(json.dumps(index))
    assert m.main(argv) == 2 and out.read_bytes() == before
    assert json.loads(capsys.readouterr().out)['status'] == 'STOP_METADATA_REVIEW'


def test_published_snapshot_preserves_blockers_and_unreviewed_pins():
    p = ROOT / 'config/research/avzvol_mnq_metadata_review_20261010.json'
    evidence = json.loads(p.read_text())
    assert evidence['approved_session_count'] == sum(c['approved_session_count'] for c in evidence['contracts']) == 261
    assert evidence['missing_approved_summaries'] == evidence['approved_trade_count_mismatches'] == 0
    assert not evidence['raw_quality_certified'] and not evidence['research_authorized']
    assert not evidence['historical_outputs_rewritten']
    assert all(c['source_summary_total_matches_producer_manifest_rows'] for c in evidence['contracts'])
    assert len(evidence['canonical_manifest_hash_identity_notes']) == 3
    assert all(not h['raw_byte_or_semantic_equivalence_independently_verified'] for h in evidence['canonical_manifest_hash_identity_notes'])
    design = json.loads((ROOT / 'specs/research/avzvol_incremental_design_v1.json').read_text())
    assert design['reviewed_input_pins'] is design['source_quality_review_refs'] is design['match_policy'] is None
    assert not design['candidate_metadata_quality_is_certification']
    text = p.read_text()
    for forbidden in ('X-Goog-', 'storage.googleapis.com', 'session-file://', '/data/raw/'):
        assert forbidden not in text


def test_non_json_market_file_is_rejected_before_bytes(tmp_path):
    p = tmp_path / 'ticks.parquet'; p.write_bytes(b'NOT READ AS METADATA')
    with pytest.raises(m.MetadataReviewError):
        m.read_json(p)


def test_output_cannot_overwrite_source_metadata(tmp_path, capsys):
    resolver, catalog, lineage, sources = fixture(); paths = []
    for name, value in [('resolver', resolver), ('catalog', catalog), ('lineage', lineage)]:
        p = tmp_path / (name + '.json'); p.write_text(json.dumps(value)); paths.extend(['--' + name, str(p)])
    index = []
    for c, source in sources.items():
        p = tmp_path / (c + '.json'); p.write_text(json.dumps(source))
        index.append({'contract': c, 'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    p = tmp_path / 'index.json'; p.write_text(json.dumps(index)); before = p.read_bytes()
    assert m.main(paths + ['--sessions-index', str(p), '--out', str(p)]) == 2
    assert p.read_bytes() == before
    assert json.loads(capsys.readouterr().out)['status'] == 'STOP_METADATA_REVIEW'
