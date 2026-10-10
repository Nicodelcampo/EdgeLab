"""Frozen documentary evidence contracts, NOT raw QA or historic-run attestation."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'config/research/avzvol_lineage_candidates_20261010.json'


def load():
    return json.loads(EVIDENCE.read_text())


def test_recovered_candidates_never_certify_research_or_history():
    e = load()
    assert e['status'] == 'CANDIDATE_ARTIFACTS_RECOVERED_RUNTIME_CONSUMPTION_UNVERIFIED'
    assert e['candidate_versions_are_not_reviewed_input_pins']
    assert e['new_market_trials'] == 0
    for flag in ('research_authorized', 'historical_bias_adjudicated',
                 'original_outputs_modified', 'raw_price_payload_read'):
        assert e[flag] is False
    assert len(e['remaining_blockers']) >= 4


def test_raw_declarations_are_not_measured_consumption():
    inputs = load()['candidate_inputs']
    assert len(inputs) == len({r['contract'] for r in inputs}) == 6
    for r in inputs:
        assert re.fullmatch(r'[a-f0-9]{64}', r['producer_declared_file_sha256'])
        assert r['declarations_agree'] and len(r['declaration_sources']) == 2
        assert r['candidate_dataset_version'] in (1, 2)
        assert not r['raw_bytes_rehashed']
        assert not r['historical_consumption_verified']
        assert not r['source_quality_certified']
        assert r['file'].startswith('MNQ/')


def test_measured_artifact_hashes_do_not_imply_historic_mount():
    artifacts = load()['measured_artifacts']
    assert len({a['artifact'] for a in artifacts}) == len(artifacts)
    for a in artifacts:
        assert a['downloaded_bytes'] > 0
        assert re.fullmatch(r'[a-f0-9]{64}', a['measured_sha256'])
        assert not a['historical_consumption_verified']
    resolver = next(a for a in artifacts if a['artifact'] == 'catalog.v15.RESOLVER.json')
    assert resolver['retrieved_version'] == 15
    assert resolver['measured_sha256'] == '9b21eeff751d4397465fcc6831ea615b7dd401a5605a5997f52c8bfd9248117c'


def test_static_code_identity_distinguishes_bytes_and_newlines():
    comparison = load()['static_code_comparison']
    assert 'excludes dynamic imports and external libraries' in comparison['method']
    assert not comparison['unresolved_seed_modules']
    modules = comparison['modules']
    assert len(modules) == len({m['path'] for m in modules}) == 22
    assert sum(m['byte_equal'] for m in modules) == 8
    assert all(m['equal_after_CRLF_to_LF'] for m in modules)
    for m in modules:
        assert m['byte_equal'] == (m['bundle_sha256'] == m['repo_sha256'])


def test_notebook_contracts_have_candidates_not_import_attestations():
    e = load()
    notebooks = e['notebooks']
    assert [n['output_run_id'] for n in notebooks] == ['356884473', '356884479', '356884484']
    assert {c for n in notebooks for c in n['contracts']} == {i['contract'] for i in e['candidate_inputs']}
    for n in notebooks:
        assert n['notebook_version'] == 1
        assert re.fullmatch(r'[a-f0-9]{64}', n['source_sha256'])
        assert not n['attached_sources_have_exact_versions']
        assert not n['runtime_import_paths_and_hashes_recorded']


def test_future_spec_still_requires_reviewed_pins_and_policy():
    spec = json.loads((ROOT / 'specs/research/avzvol_incremental_design_v1.json').read_text())
    assert spec['status'] == 'BLOCKED_FOR_MARKET_EXECUTION'
    assert not spec['research_authorized'] and not spec['candidate_lineage_is_runtime_attestation']
    assert spec['reviewed_input_pins'] is None and spec['match_policy'] is None
    assert ROOT / spec['candidate_lineage_evidence_ref'] == EVIDENCE


def test_documentation_links_and_no_secret_download_routes():
    doc = ROOT / 'docs/infra/AVZVOL_LINEAGE_RECOVERY_20261010.md'
    for _, link in re.findall(r'\[([^\]]+)\]\(([^)]+)\)', doc.read_text()):
        if '://' not in link:
            assert (doc.parent / link).exists()
    text = EVIDENCE.read_text()
    for forbidden in ('X-Goog-', 'storage.googleapis.com', 'session-file://', 'E:\\\\'):
        assert forbidden not in text
    assert 'AVZVOL_LINEAGE_RECOVERY_20261010.md' in (ROOT / 'docs/ESTADO_Y_PENDIENTES.md').read_text()
