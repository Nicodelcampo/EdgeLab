"""Synthetic mount fixtures; no market payload or credentials."""
import hashlib
import json
from pathlib import Path

import pytest
from edgelab.kaggle import discovery as d


def test_frozen_inventory_is_explicitly_not_ready():
    c = d.consumption_plan()
    assert c['status'] == 'BLOCKED_FOR_RESEARCH'
    assert c['research_allowed'] is False and c['promotion_allowed'] is False
    assert len(c['datasets']) == 6
    assert sum(len(x['files']) for x in c['datasets']) == 31
    assert sum(len(x['files']) for x in c['datasets'] if x['role'] == 'raw_qa') == 18
    assert c['holdout']['first_trade_date'] == '2026-10-01'
    for dataset in c['datasets']:
        assert len(dataset['version_ref'].split('/')) == 3
        assert int(dataset['version_ref'].split('/')[-1]) > 0
        assert dataset['files']
        assert len({f['path'] for f in dataset['files']}) == len(dataset['files'])
        for f in dataset['files']:
            assert len(f['sha256']) == 64
            assert f['bytes'] > 0


def test_loading_returns_fresh_snapshot():
    c = d.load_discovery(); c['research_allowed'] = True
    assert d.load_discovery()['research_allowed'] is False


def test_research_stops_before_mount_file_is_opened(monkeypatch, capsys):
    original = Path.read_text
    def forbidden(path, *a, **k):
        if str(path) == '/never/open':
            raise AssertionError('mount metadata accessed before research STOP')
        return original(path, *a, **k)
    monkeypatch.setattr(Path, 'read_text', forbidden)
    assert d.main(['--purpose', 'research', '--verify-mounts', '/never/open']) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'STOP'


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    root = tmp_path/'mounted'; root.mkdir()
    (root/'nested').mkdir(); p=root/'nested/file.bin'; p.write_bytes(b'synthetic-not-market')
    c={'allowed_purposes':['discovery','structural_qa'], 'blockers':[{'id':'NOT_CERTIFIED'}],
       'datasets':[{'version_ref':'test/invented/1','files':[{'path':'nested/file.bin',
           'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]}]}
    monkeypatch.setattr(d,'load_discovery',lambda:c)
    return c, {'test/invented/1':str(root)}, p


def test_byte_pass_still_never_authorizes_research(synthetic):
    c,m,p=synthetic
    result=d.verify_mounts(m)
    assert result['status']=='PASS_INPUT_BYTES_ONLY' and result['files_checked']==1
    assert not result['research_allowed'] and not result['promotion_allowed']
    with pytest.raises(d.DiscoveryError):d.consumption_plan('research')


@pytest.mark.parametrize('problem',['version','extra','missing','size','hash','traversal','symlink'])
def test_bad_mounts_stop_without_fallback(synthetic, problem, tmp_path):
    c,m,p=synthetic
    if problem=='version':m['test/invented/2']=m.pop('test/invented/1')
    if problem=='extra':m['test/unlisted/1']=str(tmp_path)
    if problem=='missing':p.rename(p.parent.parent/'file.bin')  # basename fallback forbidden
    if problem=='size':p.write_bytes(b'x')
    if problem=='hash':p.write_bytes(b'x'*p.stat().st_size)
    if problem=='traversal':c['datasets'][0]['files'][0]['path']='../file.bin'
    if problem=='symlink':
        outside=tmp_path/'outside.bin';p.rename(outside);p.symlink_to(outside)
    with pytest.raises((d.DiscoveryError,OSError)):d.verify_mounts(m)


def test_cli_discovery_without_mounts(capsys):
    assert d.main([])==0
    assert json.loads(capsys.readouterr().out)['entrypoint']=='nicolasbuttaro/edgelab-data-catalog'
