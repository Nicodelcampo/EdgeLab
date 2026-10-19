"""Invented footer fixtures; no payload/research/market prices."""
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
from types import SimpleNamespace as S
import json
import subprocess
import sys
import pytest
spec = spec_from_file_location('obs', Path(__file__).resolve().parents[1] / 'tools/audit_avzvol_trigger_observability.py')
m = module_from_spec(spec)
spec.loader.exec_module(m)


def fixture(rows=(3, 7), maximum=20260930, nulls=0):
    stats = S(has_min_max=True, has_null_count=True, min=20250901, max=maximum, null_count=nulls)
    groups = [S(num_rows=n, column=lambda i: S(statistics=stats)) for n in rows]
    class FooterOnly:
        schema_arrow = S(names=['session', 't0', 'L', 'H', 'te', 'o3a', 'o3b'])
        schema = S(names=schema_arrow.names)
        num_row_groups = len(groups)
        metadata = S(num_rows=sum(rows), row_group=lambda i: groups[i])
        def read(self, *args, **kwargs):
            raise AssertionError('payload must never be opened')
    return FooterOnly()


def test_footer_only_missing_is_not_invalid_historical_outcome():
    q = m.footer_summary(fixture())
    assert q['rows'] == q['row_group_sum_independent'] == 10
    assert not q['literal_capture_fields_complete']
    assert q['capture_gaps']['retest_observation'] == ['retest_bar_id', 'retest_available_utc_ns']


@pytest.mark.parametrize('maximum,nulls', [(20261001, 0), (20261002, 0), (20260930, 1)])
def test_reserved_or_unknown_partition_stops(maximum, nulls):
    with pytest.raises(ValueError, match='reserved or unknown'):
        m.footer_summary(fixture(maximum=maximum, nulls=nulls))


def test_rowgroup_count_disagreement_stops():
    f = fixture(); f.metadata.num_rows = 11
    with pytest.raises(ValueError, match='cross-foot'):
        m.footer_summary(f)


def test_field_presence_is_only_literal_inventory():
    names = [k for keys in m.CRITICAL_GROUPS.values() for k in keys]
    assert not any(m.capture_gaps(names).values())
    assert m.capture_gaps(names[:-1])['independent_control_identity']


def test_capture_does_not_choose_scientific_rules_or_grant_authority():
    c = json.loads((m.ROOT / 'config/research/avzvol_interaction_capture_v1.json').read_text())
    assert all(x is None for x in c['unapproved_scientific_policy'].values())
    for key in ['market_replay_implemented', 'technical_capture_is_source_certification',
                'technical_capture_is_authorization', 'new_market_outcomes_authorized',
                'holdout_access_authorized', 'economic_execution_authorized', 'entry_rule_promoted']:
        assert c[key] is False
    assert c['entry_fill_or_stop_target_model'] is None


def test_cli_without_optin_stops_before_input(tmp_path):
    r = subprocess.run([sys.executable, '-O', m.__file__, '--inventory', str(tmp_path/'missing'),
                        '--out-dir', str(tmp_path/'out')], capture_output=True, text=True)
    assert r.returncode == 2 and not (tmp_path/'out').exists()


def test_wrong_input_universe_stops_before_output(tmp_path):
    f = tmp_path/'inventory.json'; f.write_text('[]')
    with pytest.raises(ValueError, match='six-export'):
        m.run(f, tmp_path/'out')
    assert not (tmp_path/'out').exists()
