"""Invented fixtures only. No market source, review or certification produced."""
import hashlib
from pathlib import Path
import pytest
import pyarrow as pa
import pyarrow.parquet as pq
from edgelab.data.contract_regime import build_contract_regime
from edgelab.data.continuous_contract import ContinuousContractError, build_continuous_series
from edgelab.data.research_data_gate import DataEligibilityError, REQUIRED_CHECKS, seal
from edgelab.data.research_window import read_research_window

DAYS = [20260327, 20260330, 20260331, 20260401]
WINDOW = dict(start_trade_date=20260330, end_trade_date_exclusive=20260401)


def write_shard(tmp_path, day, *, ts0):
    path = tmp_path / f'MNQ_{day}.parquet'
    table = pa.table({'root': ['MNQ'] * 2, 'contract': ['MNQ_06-26'] * 2,
        'trade_date': pa.array([day] * 2, type=pa.int64()),
        'ts_utc_ns': pa.array([ts0 + 1, ts0], type=pa.int64()), 'sequence': [0, 0], 'last': [100, 101]})
    pq.write_table(table, path, row_group_size=1)
    return path, {'basename': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                  'size_bytes': path.stat().st_size, 'rows': 2}


def window_fixture(tmp_path):
    r = build_contract_regime(contracts=[{'root': 'MNQ', 'contract': 'MNQ_06-26', 'expiry_ordinal': 202606,
        'first_trade_date': DAYS[0], 'last_trade_date': DAYS[-1]}],
        daily_volumes=[{'root': 'MNQ', 'contract': 'MNQ_06-26', 'trade_date': d, 'volume': 2000,
                        'complete_session': True} for d in DAYS],
        calendar_trade_dates=DAYS, source_identity={'dataset': 'SYNTHETIC_TEST_ONLY', 'version': 1})
    sessions = {f'MNQ|MNQ_06-26|{d}': {'status': 'PASS', 'complete_session': True,
                                        'trade_quantity': 2000, 'spread_p99_ticks': 1} for d in DAYS[:3]}
    paths = {}
    for i, day in enumerate(DAYS[1:3]):
        paths[day], sessions[f'MNQ|MNQ_06-26|{day}']['shard'] = write_shard(tmp_path, day, ts0=(i + 1) * 1000)
    c = {'status': 'SANITIZED_VERIFIED', 'checks': dict.fromkeys(REQUIRED_CHECKS, 'PASS'),
         'source_identity': r['source_identity'], 'holdout_first_trade_date': 20260401,
         'allowed_trade_dates': DAYS[1:3], 'sessions': sessions}
    limits = {'root': 'MNQ', 'frozen_before_strategy': True, 'min_previous_session_volume': 1000,
              'max_previous_session_spread_p99_ticks': 2}
    return paths, pin({'certificate': c, 'regime_manifest': r, 'root': 'MNQ', 'liquidity_limits': limits})


def pin(f):
    f['expected_certificate_sha256'] = seal(f['certificate'])
    r = f['regime_manifest']; r.pop('manifest_sha256', None); r['manifest_sha256'] = seal(r)
    f['expected_regime_sha256'] = r['manifest_sha256']
    f['expected_liquidity_limits_sha256'] = seal(f['liquidity_limits'])
    return f


def test_window_reads_every_session_sorted_with_evidence(tmp_path):
    paths, f = window_fixture(tmp_path)
    table, e = read_research_window(shard_paths=paths, **WINDOW, **f)
    assert table['ts_utc_ns'].to_pylist() == [1000, 1001, 2000, 2001]
    assert table['state_reset_flag'].to_pylist() == [True, False, False, False]
    assert [s['trade_date'] for s in e['sessions']] == [20260330, 20260331]
    assert e['promotion_allowed'] is False and e['authority_authenticated'] is False


def test_declared_exclusion_is_not_read_and_is_reported(tmp_path):
    paths, f = window_fixture(tmp_path)
    del paths[20260331]
    table, e = read_research_window(shard_paths=paths, declared_exclusions={20260331: 'roll review'},
                                    **WINDOW, **f)
    assert len(table) == 2 and e['declared_exclusions'] == {20260331: 'roll review'}


@pytest.mark.parametrize('reason', ['missing_shard', 'extra_shard', 'holdout_window', 'one_bad_session',
    'blank_exclusion', 'exclusion_outside', 'all_excluded', 'inverted', 'pin'])
def test_window_rejects_before_any_source_open(tmp_path, monkeypatch, reason):
    paths, f = window_fixture(tmp_path)
    kw = dict(WINDOW)
    if reason == 'missing_shard': del paths[20260331]
    elif reason == 'extra_shard': paths[20260327] = tmp_path / 'x.parquet'
    elif reason == 'holdout_window': kw['end_trade_date_exclusive'] = 20260402; paths[20260401] = tmp_path / 'h.parquet'
    elif reason == 'one_bad_session':
        f['certificate']['sessions']['MNQ|MNQ_06-26|20260331']['status'] = 'FAIL'; pin(f)
    elif reason == 'blank_exclusion': del paths[20260331]; kw['declared_exclusions'] = {20260331: ' '}
    elif reason == 'exclusion_outside': kw['declared_exclusions'] = {20260327: 'x'}
    elif reason == 'all_excluded': paths.clear(); kw['declared_exclusions'] = {20260330: 'x', 20260331: 'x'}
    elif reason == 'inverted': kw['end_trade_date_exclusive'] = 20260330
    elif reason == 'pin': f['expected_certificate_sha256'] = 'a' * 64
    def fail(*a, **k): raise AssertionError('source opened before rejection')
    monkeypatch.setattr(Path, 'open', fail)
    monkeypatch.setattr(pq, 'ParquetFile', fail)
    with pytest.raises(DataEligibilityError):
        read_research_window(shard_paths=paths, **kw, **f)


def test_overlapping_sessions_rejected(tmp_path):
    paths, f = window_fixture(tmp_path)
    p, shard = write_shard(tmp_path, 20260331, ts0=1000)
    f['certificate']['sessions']['MNQ|MNQ_06-26|20260331']['shard'] = shard; pin(f)
    with pytest.raises(DataEligibilityError):
        read_research_window(shard_paths=paths, **WINDOW, **f)


def test_legacy_builder_requires_acknowledgement_before_reading(monkeypatch):
    def fail(*a, **k): raise AssertionError('legacy source read without acknowledgement')
    monkeypatch.setattr(pq, 'read_table', fail)
    with pytest.raises(ContinuousContractError, match='acknowledge_unaudited_legacy'):
        build_continuous_series(root='MNQ', regime_manifest={}, contract_source_paths={'MNQ_06-26': 'x'})
