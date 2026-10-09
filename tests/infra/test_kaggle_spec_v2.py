"""Synthetic infrastructure tests; no market outcomes and no real holdout access."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

RUNNER = Path(__file__).resolve().parents[2] / 'tools' / 'kaggle_spec_v2.py'
ms = importlib.util.spec_from_file_location('framework', RUNNER)
f = importlib.util.module_from_spec(ms); ms.loader.exec_module(f)


@pytest.fixture
def fixture(tmp_path):
    catalog = tmp_path / 'catalog'; catalog.mkdir()
    rows = [dict(date='2026-01-05', contract='ES_03-26', dataset='fixture-ticks', file='ticks.parquet', approved=True, trades=5, volume=20),
            dict(date='2026-01-06', contract='ES_03-26', dataset='fixture-ticks', file='ticks.parquet', approved=False)]
    resolver = dict(holdout_first_trade_date=f.HOLDOUT, instruments={'ES': {'tick_size': .25, 'sessions': rows}})
    f.write_json(catalog / 'RESOLVER.json', resolver)
    (catalog / 'edgelab_data.py').write_text('''import json
from pathlib import Path
import pandas as pd
RESOLVER=json.loads((Path(__file__).parent/'RESOLVER.json').read_text())
def sessions(inst,start,end):
 s=pd.DataFrame(RESOLVER['instruments'][inst]['sessions'])
 return s[(s.date>=start)&(s.date<=end)&s.approved]
def _session_date(ts):
 lab=(ts//60_000_000_000+1)*60_000_000_000-1
 ix=pd.to_datetime(lab,unit='ns',utc=True).tz_convert('America/Chicago')+pd.Timedelta(hours=7)
 return ix.strftime('%Y-%m-%d').to_numpy()
''')
    spec = dict(schema=f.SCHEMA, run_id='fixture', mode='aggregate', hypothesis='Data integrity only',
                metrics=['input_integrity','bar_conservation'], verdict_rule='PASS_INTEGRITY_NOT_EDGE',
                holdout_first_trade_date=f.HOLDOUT, frequencies_seconds=[1,30,60], max_shards=3,
                requests=[{'instrument':'ES','start':'2026-01-05','end':'2026-01-06'}],
                catalog={'ref':'test/catalog/1','sha256':{n:f.digest(catalog/n) for n in ('edgelab_data.py','RESOLVER.json')}},
                dataset_versions={'fixture-ticks':'test/fixture-ticks/1'})
    ed = f.load_catalog(spec,catalog); plan = f.make_plan(spec,ed)
    root=tmp_path/'input'; (root/'fixture-ticks').mkdir(parents=True)
    base=pd.Timestamp('2026-01-05 15:00',tz='UTC').value
    ticks=pd.DataFrame(dict(ts_utc_ns=[base,base+400_000_000,base+1_000_000_000,base+29_900_000_000,base+30_000_000_000],
          price_ticks=[100,102,101,99,105],volume=[2,3,4,5,6],aggressor=['buy','sell','unclassified','buy','sell'],
          contract=['ES 03-26']*5,bid_ticks=[99,101,100,98,None],ask_ticks=[101,103,102,100,None]))
    pq.write_table(pa.Table.from_pandas(ticks,preserve_index=False),root/'fixture-ticks'/'ticks.parquet',row_group_size=2)
    return spec,ed,plan,catalog,root,ticks


def test_plan_repeatable_approved_only(fixture):
    spec,ed,plan,*_=fixture
    assert plan==f.make_plan(spec,ed)
    assert plan['selected_sessions']==1
    assert plan['shards'][0]['sessions'][0]['date']=='2026-01-05'


@pytest.mark.parametrize('change', ['holdout','start','mode','verdict','pins','hash','shards','freq'])
def test_invalid_specs(fixture,change):
    s=copy.deepcopy(fixture[0])
    if change=='holdout':s['requests'][0]['end']='2026-10-01'
    if change=='start':s['requests'][0]['start']='2026-02-01'
    if change=='mode':s['mode']='pnl'
    if change=='verdict':s['verdict_rule']='EDGE'
    if change=='pins':s['dataset_versions']['fixture-ticks']='test/fixture-ticks'
    if change=='hash':s['catalog']['sha256']['RESOLVER.json']='bad'
    if change=='shards':s['max_shards']=True
    if change=='freq':s['frequencies_seconds']=[60]
    with pytest.raises(ValueError):f.validate(s)


def test_hash_mismatch(fixture):
    spec,ed,plan,catalog,*_=fixture
    (catalog/'RESOLVER.json').write_text('{}')
    with pytest.raises(ValueError):f.load_catalog(spec,catalog)


def test_overlap_requests_dedup(fixture):
    s,ed,*_=fixture;s=copy.deepcopy(s);s['requests']*=2
    assert f.make_plan(s,ed)['selected_sessions']==1


def test_contract_indivisible_balanced(fixture):
    spec,ed,*_=fixture
    ed.RESOLVER['instruments']['ES']['sessions'] += [
        dict(date='2026-01-06',contract='ES_06-26',dataset='fixture-ticks',file='two.parquet',approved=True)]
    plan=f.make_plan(spec,ed)
    assert len(plan['shards'])==2
    assert [s['id'] for s in plan['shards']]==['k01','k02']
    assert all(len({r['contract'] for r in s['sessions']})==1 for s in plan['shards'])


def test_end_to_end_conservation_and_quotes(fixture,tmp_path):
    spec,ed,plan,catalog,root,ticks=fixture
    out=tmp_path/'out'
    assert f.execute(plan,'k01',catalog,root,out)==0
    result=json.loads((out/'results.json').read_text())
    assert result['status']=='PASS_INTEGRITY_NOT_EDGE'
    assert len(result['bars'])==3
    for b in result['bars']:
        bars=pd.read_parquet(out/b['file'])
        assert bars.trades.sum()==5
        assert bars.volume.sum()==20
        assert bars.signed_volume.sum()==-2
        assert bars.unknown_volume.sum()==4
        assert (bars.available_utc_ns==bars.bucket_utc_ns+b['seconds']*10**9).all()
        assert pd.isna(bars.bid_ticks.iloc[-1]) # no stale quote substitution
    bars=pd.read_parquet(out/result['bars'][2]['file'])
    assert bars.iloc[0]['open']==100 and bars.iloc[0]['close']==105
    assert bars.iloc[0]['high']==105 and bars.iloc[0]['low']==99
    assert f.digest(out/'output.zip')==(out/'output.zip.sha256').read_text().split()[0]
    with zipfile.ZipFile(out/'output.zip') as z:
        assert {'results.json','attestation.json','manifest.json','plan.json'}<=set(z.namelist())
    merged=tmp_path/'merged';f.merge(plan,[out],merged)
    assert len(json.loads((merged/'results.json').read_text())['bars'])==3
    cached=f.load_bars(merged,'ES','2026-01-05','2026-01-05',60)
    assert cached.trades.sum()==5
    with pytest.raises(ValueError):f.load_bars(merged,'ES','2026-01-01','2026-01-05',60)
    with pytest.raises(ValueError):f.load_bars(merged,'ES','2026-01-05','2026-10-01',60)
    (merged/'ES__60s.parquet').write_bytes(b'corrupted')
    with pytest.raises(ValueError):f.load_bars(merged,'ES','2026-01-05','2026-01-05',60)


def test_missing_input_has_standard_error_package(fixture,tmp_path):
    _,_,plan,catalog,_,_=fixture
    out=tmp_path/'missing'
    assert f.execute(plan,'k01',catalog,tmp_path/'empty',out)==2
    assert json.loads((out/'results.json').read_text())['status']=='ABSTAIN'
    assert json.loads((out/'attestation.json').read_text())['holdout_touched'] is None
    assert (out/'output.zip.sha256').is_file()


def test_plan_tamper_refused(fixture,tmp_path):
    _,_,plan,catalog,root,_=fixture;plan=copy.deepcopy(plan)
    plan['shards'][0]['sessions'][0]['date']='2026-01-06'
    assert f.execute(plan,'k01',catalog,root,tmp_path/'tampered')==2


def test_holdout_row_group_blocked_before_read(fixture,tmp_path):
    _,_,plan,catalog,root,ticks=fixture
    # Synthetic timestamp only: ensure mixed row group is refused BEFORE loading its values.
    t=ticks.copy();t.loc[len(t)]=t.iloc[-1];t.loc[len(t)-1,'ts_utc_ns']=pd.Timestamp('2026-10-01',tz='UTC').value
    pq.write_table(pa.Table.from_pandas(t,preserve_index=False),root/'fixture-ticks'/'ticks.parquet',row_group_size=99)
    out=tmp_path/'firewall'
    assert f.execute(plan,'k01',catalog,root,out)==2
    assert 'sealed holdout' in json.loads((out/'results.json').read_text())['error']
    assert not list(out.glob('*.parquet'))


def test_no_timestamp_stats_blocked(fixture,tmp_path):
    _,_,plan,catalog,root,ticks=fixture
    pq.write_table(pa.Table.from_pandas(ticks,preserve_index=False),root/'fixture-ticks'/'ticks.parquet',write_statistics=False)
    assert f.execute(plan,'k01',catalog,root,tmp_path/'nostats')==2


@pytest.mark.parametrize('failure',['duplicate','tamper','missing','breach'])
def test_merge_refuses_bad_shards(fixture,tmp_path,failure):
    _,_,plan,catalog,root,_=fixture
    out=tmp_path/'out'; assert f.execute(plan,'k01',catalog,root,out)==0
    dirs=[out]
    if failure=='duplicate':dirs=[out,out]
    if failure=='tamper':(out/'results.json').write_text('{}')
    if failure=='missing':dirs=[]
    if failure=='breach':
        a=json.loads((out/'attestation.json').read_text());a['holdout_touched']=True
        f.write_json(out/'attestation.json',a);f.package(out)
    with pytest.raises(ValueError):f.merge(plan,dirs,tmp_path/'merge')


def test_generate_selfcontained_offline(fixture,tmp_path):
    _,_,plan,*_=fixture
    f.generate(plan,tmp_path/'generated')
    meta=json.loads((tmp_path/'generated/k01/kernel-metadata.json').read_text())
    assert meta['enable_internet'] is False and meta['is_private'] is True
    assert meta['dataset_sources']==['test/catalog/1','test/fixture-ticks/1']
    code=(tmp_path/'generated/k01/entry.py').read_text()
    compile(code,'entry.py','exec')
    assert 'runpy.run_path' in code and 'git clone' not in code


def test_unknown_aggressor_and_unsorted(fixture):
    t=fixture[-1].copy();t['session_date']='2026-01-05'
    t.loc[0,'aggressor']='mystery'
    with pytest.raises(ValueError):f.aggregate_frame(t,1)
    t['aggressor']='buy';t=t.iloc[::-1]
    with pytest.raises(ValueError):f.aggregate_frame(t,1)


def test_deterministic_package(fixture,tmp_path):
    _,_,plan,catalog,root,_=fixture
    out=tmp_path/'out';f.execute(plan,'k01',catalog,root,out)
    before=f.digest(out/'output.zip');f.package(out)
    assert f.digest(out/'output.zip')==before


def test_catalog_counts_mismatch(fixture,tmp_path):
    spec,ed,plan,catalog,root,ticks=fixture
    ticks=ticks.iloc[:4]
    pq.write_table(pa.Table.from_pandas(ticks,preserve_index=False),root/'fixture-ticks'/'ticks.parquet')
    out=tmp_path/'truncated'
    assert f.execute(plan,'k01',catalog,root,out)==2
    assert 'source totals differ' in json.loads((out/'results.json').read_text())['error']


def hip_adapter():
    ms=importlib.util.spec_from_file_location('hip_adapter',RUNNER.with_name('kaggle_hippocampus_ingest.py'))
    mod=importlib.util.module_from_spec(ms);ms.loader.exec_module(mod)
    return mod


def test_hippocampus_idempotent_verified_ingest(fixture,tmp_path):
    _,_,plan,catalog,root,_=fixture
    shard=tmp_path/'shard'; assert f.execute(plan,'k01',catalog,root,shard)==0
    store=tmp_path/'store';f.merge(plan,[shard],store)
    adapter=hip_adapter();ledger=tmp_path/'hip/aggregate.jsonl'
    r=adapter.ingest(store,ledger,recorded_at_utc='2026-10-09T23:00:00Z')
    assert r['records']==5 and not r['idempotent']
    before=ledger.read_bytes();again=adapter.ingest(store,ledger)
    assert again['idempotent'] and again['tip']==r['tip'] and ledger.read_bytes()==before
    _,sm=adapter.modules();memory=sm.DurableHippocampus(ledger,expected_tip_hash=r['tip'])
    assert len(memory.memory.episodes)==1 and not memory.trials
    assert memory.memory.episodes[r['episode_id']].outcomes_inspected is False
    assert memory.memory.lessons[r['episode_id']][0].confidence=='LOW'


def test_hippocampus_bad_evidence_never_writes(fixture,tmp_path):
    _,_,plan,catalog,root,_=fixture
    shard=tmp_path/'shard';f.execute(plan,'k01',catalog,root,shard)
    store=tmp_path/'store';f.merge(plan,[shard],store)
    adapter=hip_adapter();ledger=tmp_path/'hip.jsonl'
    (store/'attestation.json').write_text('{}')
    with pytest.raises(ValueError):adapter.ingest(store,ledger)
    assert not ledger.exists()


def test_hippocampus_existing_ledger_preserved(fixture,tmp_path):
    _,_,plan,catalog,root,_=fixture
    shard=tmp_path/'shard';f.execute(plan,'k01',catalog,root,shard)
    store=tmp_path/'store';f.merge(plan,[shard],store)
    adapter=hip_adapter();h,sm=adapter.modules();ledger=tmp_path/'hip.jsonl'
    old=sm.DurableHippocampus(ledger);old.register_episode(h.AnalysisEpisode(episode_id='PREEXISTING',goal='preserve'))
    original=ledger.read_bytes();receipt=adapter.ingest(store,ledger)
    assert ledger.read_bytes().startswith(original)
    assert receipt['records']==6
    assert sm.DurableHippocampus(ledger).verify()==receipt['tip']
