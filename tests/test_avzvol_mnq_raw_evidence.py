"""Frozen documentary consistency checks, not a fresh data-quality certification."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PATH = 'config/research/avzvol_mnq_raw_quality_review_20261010.json'

def read(path=PATH):
    return json.loads((ROOT / path).read_text())

def test_structural_pass_never_scientific_or_economic_approval():
    e = read()
    assert e['status'] == 'PASS_RAW_STRUCTURE_ONLY_SOURCE_QUALITY_REVIEW_OPEN'
    for flag in ('research_authorized', 'promotion_allowed', 'economic_outcomes_computed',
                 'original_bytes_or_outputs_modified', 'historical_runtime_consumption_verified',
                 'calendar_certified', 'clock_independently_certified', 'continuity_certified',
                 'liquidity_certified', 'quote_aggressor_provenance_verified', 'price_outcomes_computed'):
        assert e[flag] is False
    assert e['price_quote_payload_read_for_structural_qa'] is True
    assert e['global_preflight_before_any_payload'] and e['all_files_strictly_preholdout']
    assert e['new_market_trials'] == 0
    assert e['holdout_first_trade_date'] == '2026-10-01'
    assert e['strict_preholdout_utc_cutoff'] == '2026-09-30T22:00:00Z'

def test_six_measured_pins_agree_with_earlier_declarations_not_history():
    e = read(); prior = read('config/research/avzvol_lineage_candidates_20261010.json')
    assert len(e['files']) == len({r['candidate_contract'] for r in e['files']}) == 6
    for r in e['files']:
        s = r['structural_audit']; c = next(x for x in prior['candidate_inputs'] if x['contract'] == r['candidate_contract'])
        assert r['physical_bytes_sha256_verified_now'] and r['producer_pins_match']
        assert s['sha256'] == c['producer_declared_file_sha256']
        assert re.fullmatch('[a-f0-9]{64}', s['sha256'])
        assert s['dataset_ref'] == c['dataset_ref'] and s['dataset_version'] == c['candidate_dataset_version']
        assert s['dataset_file'] == c['file']
        assert s['rows'] == r['footer_preflight']['rows'] == r['timestamp_coverage_audit']['rows_timestamp_scanned']
        assert s['bytes'] > 0 and s['status'] == 'PASS_RAW_STRUCTURE_ONLY'
        assert all(v == 0 for v in s['errors'].values())
        assert r['footer_preflight']['all_groups_strictly_preholdout']
        assert not s['historical_runtime_consumption_verified']
        assert not c['raw_bytes_rehashed']  # Preserve the earlier snapshot.

def test_report_totals_match_per_file_evidence():
    e = read(); rows = e['files']; totals = e['totals']
    assert totals['rows'] == sum(r['structural_audit']['rows'] for r in rows) == 485596960
    assert totals['structural_error_count'] == 0
    for k, v in totals['warnings'].items():
        assert v == sum(r['structural_audit']['warnings'][k] for r in rows)
    assert totals['clock_band_16_to_17_CT_trade_rows'] == 47
    assert totals['weekly_regular_closed_reference_rows'] == 69
    assert totals['approved_weekly_regular_closed_reference_rows'] == 4
    assert totals['approved_resolver_trade_count_discrepancies'] == 0

def test_gap_definition_review_is_not_missing_data_adjudication():
    e = read(); g = e['gap_definition_review']
    assert g['cases_checked'] == len(g['cases']) == 16
    assert g['unfiltered_summary_differences_before_definition_review'] == 12
    assert g['cases_not_matching_declared_under_candidate_definition'] == 0
    assert all(c['matches_declared_under_candidate_builder_definition'] for c in g['cases'])
    assert not g['candidate_builder_is_proven_historical_producer']
    assert not g['calendar_or_clock_certified'] and not g['research_allowed']
    assert not g['tolerance_is_quality_acceptance_threshold']
    assert 'original adjacent differences' in g['right_endpoint_predicate']
    assert all(r['timestamp_coverage_audit']['timestamps_only_payload'] for r in e['files'])
    assert all(not r['timestamp_coverage_audit']['continuity_certified'] for r in e['files'])

def test_four_original_proposals_and_explicit_economic_ban():
    p = read('config/research/avzvol_followup_proposals_v1.json')
    assert [r['id'] for r in p['proposals']] == ['P1', 'P2', 'P3', 'P4']
    assert [r['phase_refs'] for r in p['proposals']] == [['A'], ['B'], ['C'], ['E']]
    assert p['replication_gate']['phase_ref'] == 'D'
    assert not p['replication_gate']['is_additional_proposal_replacing_original_four']
    assert p['user_instruction_no_economic_outcomes'] and p['economic_scope_requires_new_explicit_user_authorization']
    assert not p['research_authorized'] and not p['economic_execution_authorized']
    assert all(not r['market_execution_done'] and not r['new_inference_done'] for r in p['proposals'])
    assert p['proposals'][3]['status'] == 'DOCUMENTED_ONLY_USER_FORBIDS_ECONOMIC_OUTCOMES'
    assert p['raw_quality_evidence_ref'] == PATH

def test_design_keeps_reviewed_pins_and_authority_unfilled():
    s = read('specs/research/avzvol_incremental_design_v1.json')
    assert s['candidate_raw_quality_evidence_ref'] == PATH
    assert not s['candidate_raw_quality_is_certification']
    assert s['reviewed_input_pins'] is None and s['source_quality_review_refs'] is None
    assert s['match_policy'] is None and s['formal_family_and_budget'] is None
    assert not s['research_authorized'] and not s['pnl_allowed']
    assert s['economic_scope_requires_new_explicit_user_authorization']
    assert 'user explicitly forbids' in s['phases'][-1]['market_execution']

def test_no_private_urls_paths_or_credentials_in_evidence():
    text = (ROOT / PATH).read_text()
    for token in ('/data/', 'X-Goog-', 'X-Amz-', 'kaggle.json', 'access_token', 'api_key', 'signed_url'):
        assert token not in text

def test_report_accessible_and_ci_covers_future_documentary_changes():
    for name in ('docs/ESTADO_Y_PENDIENTES.md', 'docs/KAGGLE_START_HERE.md',
                 'docs/DATA_CONSUMER_MATRIX.md', 'docs/research/AVZVOL_SIGUIENTE_ETAPA_20261010.md'):
        assert 'AVZVOL_MNQ_RAW_QUALITY_20261010.md' in (ROOT / name).read_text()
    assert 'config/research/avzvol_*.json' in (ROOT / '.github/workflows/cpu-runtime.yml').read_text()
