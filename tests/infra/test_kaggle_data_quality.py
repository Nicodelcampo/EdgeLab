"""Invented fixtures only: real Arrow and real causal gate, no market outcomes."""
import copy,importlib.util,json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest
from edgelab.kaggle.aggregate_audit import AggregateAuditError,audit_aggregate_store,digest
from edgelab.kaggle.research_access import require_research_store,load_research_bars,CAUSAL_SELECTION_POLICY
from edgelab.data.research_data_gate import DataEligibilityError,seal,REQUIRED_CHECKS
from edgelab.data.contract_regime import build_contract_regime

ms=importlib.util.spec_from_file_location('synthetic_infra',Path(__file__).with_name('test_kaggle_spec_v2.py'))
m=importlib.util.module_from_spec(ms);ms.loader.exec_module(m)


@pytest.fixture
def store(tmp_path):
    spec,ed,plan,catalog,root,ticks=m.fixture.__wrapped__(tmp_path)
    shard=tmp_path/'shard';out=tmp_path/'store'
    assert m.f.execute(plan,'k01',catalog,root,shard)==0
    m.f.merge(plan,[shard],out)
    return out,catalog/'RESOLVER.json',plan


def audit_args(store):
    out,resolver,_=store
    return {'store':out,'resolver':resolver,'expected_manifest_sha256':digest(out/'manifest.json'),
            'expected_resolver_sha256':digest(resolver),'batch_size':2}


def repin(out,name):
    p=out/'manifest.json';d=json.loads(p.read_text())
    for x in d['files']:
        if x['path']==name:x.update(sha256=digest(out/name),bytes=(out/name).stat().st_size)
    p.write_text(json.dumps(d))


def test_structure_pass_is_not_research_authority(store):
    report,totals=audit_aggregate_store(**audit_args(store))
    assert report['status']=='PASS_AGGREGATE_STRUCTURE_ONLY'
    assert report['research_allowed'] is False and report['liquidity_certified'] is False
    assert report['raw_ticks_audited'] is False
    assert len(report['files'])==3
    assert totals[('ES',1)]['2026-01-05']['trades']==5
    assert totals[('ES',1)]['2026-01-05']['volume']==20
    assert report['files'][0]['warnings']['missing_quote_rows']==1


@pytest.mark.parametrize('column,value,reason',[
    ('volume',-1,'negative_volume_rows'),('trades',0,'nonpositive_trades_rows'),
    ('close',0,'nonpositive_price_rows'),('high',0,'invalid_ohlc_rows'),
    ('buy_volume',999,'volume_decomposition_rows'),('signed_volume',999,'signed_volume_rows'),
    ('bid_ticks',999,'crossed_quote_rows'),('ask_ticks',0,'nonpositive_quote_rows'),
    ('ask_ticks',1.5,'fractional_quote_rows'),('ask_ticks',float('inf'),'nonfinite_quote_rows'),
    ('available_utc_ns',0,'invalid_bar_time_rows')])
def test_corrupt_rows_do_not_pass(store,column,value,reason):
    out,_,_=store;p=out/'ES__1s.parquet';t=pd.read_parquet(p)
    t.loc[0,column]=value;t.to_parquet(p,index=False);repin(out,p.name)
    report,_=audit_aggregate_store(**audit_args(store))
    assert report['status']=='FAIL_AGGREGATE_STRUCTURE' and report['errors'][reason]>0


def spy_payload(monkeypatch):
    real=pq.ParquetFile;calls=[]
    class Spy:
        def __init__(self,*a,**k):self.p=real(*a,**k)
        def __getattr__(self,k):return getattr(self.p,k)
        def iter_batches(self,*a,**k):calls.append('rows');yield from self.p.iter_batches(*a,**k)
    monkeypatch.setattr(pq,'ParquetFile',Spy);return calls


@pytest.mark.parametrize('problem',['holdout_day','holdout_last','holdout_first','missing_stats','bad_identity','noninteger_schema'])
def test_footer_or_schema_rejects_before_any_deserialization(store,monkeypatch,problem):
    out,_,_=store;p=out/'ES__1s.parquet';t=pd.read_parquet(p);kwargs={}
    if problem=='holdout_day':t.loc[0,'session_date']='2026-10-01'
    elif problem in ('holdout_last','holdout_first'):
        t.loc[0,'last_ts_utc_ns' if problem=='holdout_last' else 'first_ts_utc_ns']=pd.Timestamp('2026-09-30 22:00',tz='UTC').value
    elif problem=='missing_stats':kwargs['write_statistics']=False
    elif problem=='bad_identity':t.loc[0,'contract']=None
    elif problem=='noninteger_schema':t['volume']=t.volume.astype(float)
    t.to_parquet(p,index=False,**kwargs);repin(out,p.name);calls=spy_payload(monkeypatch)
    with pytest.raises(AggregateAuditError):audit_aggregate_store(**audit_args(store))
    assert calls==[]


@pytest.mark.parametrize('pin',['expected_manifest_sha256','expected_resolver_sha256'])
def test_bad_external_pin(store,pin,monkeypatch):
    a=audit_args(store);a[pin]='a'*64;calls=spy_payload(monkeypatch)
    with pytest.raises(AggregateAuditError):audit_aggregate_store(**a)
    assert calls==[]


def research_args(store):
    out,resolver,plan=store
    r=build_contract_regime(contracts=[{'root':'ES','contract':'ES_03-26','expiry_ordinal':202603,
       'first_trade_date':20260102,'last_trade_date':20260105}],daily_volumes=[
       {'root':'ES','contract':'ES_03-26','trade_date':d,'volume':20,'complete_session':True}
       for d in (20260102,20260105)],calendar_trade_dates=[20260102,20260105],
       source_identity={'dataset':'SYNTHETIC_TEST_ONLY'})
    limits={'root':'ES','frozen_before_strategy':True,'min_previous_session_volume':10,
            'max_previous_session_spread_p99_ticks':2}
    c={'status':'SANITIZED_VERIFIED','checks':dict.fromkeys(REQUIRED_CHECKS,'PASS'),
       'source_identity':r['source_identity'],'holdout_first_trade_date':20261001,
       'allowed_trade_dates':[20260105],'aggregate_store_manifest_sha256':digest(out/'manifest.json'),
       'aggregate_structural_status':'PASS',
       'coverage_review':{'schema':'edgelab_reviewed_daily_coverage_v1',
          'calendar_sha256':'a'*64,'interval_evidence_sha256':'b'*64,
          'dates':[{'instrument':'ES','date':'2026-01-05','status':'VERIFIED_OPEN_COMPLETE',
                    'evidence_sha256':'c'*64,'interval_review':'PASS','unresolved_intervals':0}]},
       'sessions':{
       'ES|ES_03-26|20260102':{'status':'PASS','complete_session':True,'trade_quantity':20,'spread_p99_ticks':1},
       'ES|ES_03-26|20260105':{'status':'PASS','complete_session':True}}}
    return {'store':out,'resolver':resolver,'instrument':'ES',
        'expected_manifest_sha256':digest(out/'manifest.json'),'expected_resolver_sha256':digest(resolver),
        'certificate':c,'regime_manifest':r,'liquidity_limits':limits,
        'expected_certificate_sha256':seal(c),'expected_regime_sha256':r['manifest_sha256'],
        'expected_liquidity_limits_sha256':seal(limits)}


def future_fixture(store,args):
    p=args['resolver'];d=json.loads(p.read_text());d['selection_policy_id']=CAUSAL_SELECTION_POLICY
    p.write_text(json.dumps(d));args['expected_resolver_sha256']=digest(p)


def test_legacy_catalog_approved_does_not_unlock_research(store,monkeypatch):
    args=research_args(store)
    monkeypatch.setattr(pd,'read_parquet',lambda *a,**k:pytest.fail('price opened before guard'))
    with pytest.raises(DataEligibilityError,match='SELECTION_MASK'):
        load_research_bars(start='2026-01-05',end='2026-01-05',seconds=1,**args)


def test_future_synthetic_causal_evidence_can_use_real_consumer(store):
    args=research_args(store);future_fixture(store,args)
    assert len(require_research_store(**args))==1
    t=load_research_bars(start='2026-01-05',end='2026-01-05',seconds=1,**args)
    assert t.trades.sum()==5


@pytest.mark.parametrize('failure',['zero_volume','unapproved_day','bad_limit_pin','missing_target','wrong_artifact',
                                   'unreviewed_structure','source_conflict','wrong_contract'])
def test_guard_failure_before_price_reads(store,monkeypatch,failure):
    args=research_args(store);future_fixture(store,args);c=args['certificate']
    if failure=='zero_volume':c['sessions']['ES|ES_03-26|20260102']['trade_quantity']=0
    elif failure=='unapproved_day':c['allowed_trade_dates']=[20260102]
    elif failure=='bad_limit_pin':args['expected_liquidity_limits_sha256']='a'*64
    elif failure=='missing_target':del c['sessions']['ES|ES_03-26|20260105']
    elif failure=='wrong_artifact':c['aggregate_store_manifest_sha256']='a'*64
    elif failure=='unreviewed_structure':c['aggregate_structural_status']='UNKNOWN'
    elif failure=='source_conflict':
        p=args['resolver'];d=json.loads(p.read_text());d['instruments']['ES']['sessions'][0]['caveat']='fuente_en_conflicto';p.write_text(json.dumps(d));args['expected_resolver_sha256']=digest(p)
    elif failure=='wrong_contract':
        p=args['store']/'plan.json';d=json.loads(p.read_text());d['shards'][0]['sessions'][0]['contract']='ES_06-26';p.write_text(json.dumps(d));repin(args['store'],'plan.json');args['expected_manifest_sha256']=digest(args['store']/'manifest.json');c['aggregate_store_manifest_sha256']=args['expected_manifest_sha256']
    args['expected_certificate_sha256']=seal(c)
    monkeypatch.setattr(pd,'read_parquet',lambda *a,**k:pytest.fail('price opened before guard'))
    with pytest.raises(DataEligibilityError):
        load_research_bars(start='2026-01-05',end='2026-01-05',seconds=1,**args)


def test_resolved_caveat_requires_pinned_review_not_silent_source_swap(store):
    args=research_args(store);future_fixture(store,args);p=args['resolver'];d=json.loads(p.read_text())
    d['instruments']['ES']['sessions'][0]['caveat']='fuente_en_conflicto';p.write_text(json.dumps(d));args['expected_resolver_sha256']=digest(p)
    args['certificate']['sessions']['ES|ES_03-26|20260105']['source_conflict_resolution']='PASS'
    args['expected_certificate_sha256']=seal(args['certificate'])
    assert len(require_research_store(**args))==1


def test_every_file_session_must_be_authorized_even_outside_request_window(store,monkeypatch):
    args=research_args(store);future_fixture(store,args)
    p=args['store']/'plan.json';d=json.loads(p.read_text())
    extra=copy.deepcopy(d['shards'][0]['sessions'][0]);extra['date']='2026-01-06';d['shards'][0]['sessions'].append(extra)
    p.write_text(json.dumps(d));repin(args['store'],'plan.json');args['expected_manifest_sha256']=digest(args['store']/'manifest.json')
    args['certificate']['aggregate_store_manifest_sha256']=args['expected_manifest_sha256'];args['expected_certificate_sha256']=seal(args['certificate'])
    monkeypatch.setattr(pd,'read_parquet',lambda *a,**k:pytest.fail('whole-file unauthorized read'))
    with pytest.raises(DataEligibilityError):load_research_bars(start='2026-01-05',end='2026-01-05',seconds=1,**args)


@pytest.mark.parametrize('name',['aggregates_smoke_v2_20261009.json','aggregates_es_nq_full_v2_20261009.json'])
def test_frozen_specs_remain_target_free_and_version_pinned(name):
    root=Path(__file__).resolve().parents[2]
    spec=json.loads((root/'specs/kaggle'/name).read_text())
    assert m.f.validate(spec)['verdict_rule']=='PASS_INTEGRITY_NOT_EDGE'


def test_generation_does_not_overwrite_frozen_plan(store,tmp_path):
    plan=store[2];dest=tmp_path/'generated'
    m.f.generate(plan,dest);before=(dest/'generation.json').read_bytes()
    with pytest.raises(ValueError,match='preserve frozen plans'):m.f.generate(plan,dest)
    assert (dest/'generation.json').read_bytes()==before


def test_new_technical_results_explicitly_refuse_certification(store):
    result=json.loads((store[0]/'results.json').read_text())
    assert result['research_allowed'] is False and result['raw_sanitation_certified'] is False
    assert result['causal_liquidity_certified'] is False


def test_known_unresolved_frozen_source_cannot_be_relabelled_by_certificate(store,monkeypatch):
    args=research_args(store);future_fixture(store,args)
    # Synthetic fixture borrows only the blocked immutable source identifiers.
    p=args['store']/'plan.json';plan=json.loads(p.read_text());row=plan['shards'][0]['sessions'][0]
    row.update(dataset='edgelab-ticks-nq-preholdout',file='NQ_09-26_ticks.parquet')
    plan['spec']['dataset_versions'][row['dataset']]='nicolasbuttaro/edgelab-ticks-nq-preholdout/6'
    p.write_text(json.dumps(plan));repin(args['store'],'plan.json');args['expected_manifest_sha256']=digest(args['store']/'manifest.json')
    args['certificate']['aggregate_store_manifest_sha256']=args['expected_manifest_sha256'];args['expected_certificate_sha256']=seal(args['certificate'])
    monkeypatch.setattr(pd,'read_parquet',lambda *a,**k:pytest.fail('quarantined source opened'))
    with pytest.raises(DataEligibilityError,match='KNOWN_UNRESOLVED_SOURCE_TIME_DISCREPANCY'):
        load_research_bars(start='2026-01-05',end='2026-01-05',seconds=1,**args)


@pytest.mark.parametrize('version,file,blocked',[
    ('nicolasbuttaro/edgelab-ticks-nq-preholdout/6','NQ_09-26_ticks.parquet',True),
    ('nicolasbuttaro/edgelab-ticks-nq-preholdout/7','NQ_09-26_ticks.parquet',False),
    ('nicolasbuttaro/edgelab-ticks-nq-preholdout/6','NQ_06-26_ticks.parquet',False)])
def test_quarantine_is_version_file_specific_not_general_permission(version,file,blocked):
    from edgelab.kaggle.research_access import _reject_known_unresolved_sources
    plan={'spec':{'dataset_versions':{'fixture':version}}};rows=[{'dataset':'fixture','file':file}]
    if blocked:
        with pytest.raises(DataEligibilityError):_reject_known_unresolved_sources(plan,rows)
    else:
        # No quarantine hit is NOT research approval; all other gates still apply.
        assert _reject_known_unresolved_sources(plan,rows) is None
