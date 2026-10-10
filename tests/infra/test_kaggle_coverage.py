"""Synthetic timestamps only; missing observation never means zero activity."""
import copy
import json
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from edgelab.kaggle.aggregate_audit import AggregateAuditError, digest
from edgelab.kaggle.coverage_inventory import build_daily_inventory, nominal_bounds, absent_runs, audit_coverage
from edgelab.kaggle.research_access import require_requested_coverage, load_research_bars
from edgelab.data.research_data_gate import DataEligibilityError, seal

ms = importlib.util.spec_from_file_location('quality_fixture', Path(__file__).with_name('test_kaggle_data_quality.py'))
m = importlib.util.module_from_spec(ms); ms.loader.exec_module(m)
store = m.store


def metadata(store):
    out, resolver, _ = store
    plan = json.loads((out/'plan.json').read_text())
    r = json.loads(resolver.read_text())
    c = {'holdout_first_trade_date':'2026-10-01','instruments':{'ES':{
        'first_date':'2026-01-05','last_date':'2026-01-05',
        'ineligible_low_volume':{'ranges':['2026-01-03..2026-01-04']},
        'leader_sessions_below_25pct_of_instrument_median':{'ranges':[]}}}}
    return plan, r, c


def test_inventory_covers_omitted_dates_and_exclusions(store):
    p, r, c = metadata(store); p['spec']['requests'][0].update(start='2026-01-01',end='2026-01-06')
    rows = build_daily_inventory(plan=p,resolver=r,catalog=c)
    assert len(rows)==6
    assert [x['state'] for x in rows] == ['NOT_OBSERVED_CALENDAR_UNVERIFIED']*2 + ['EXCLUDED_BY_CATALOG']*2 + ['MATERIALIZED_NOT_CERTIFIED','REJECTED_BY_RESOLVER']
    assert all(x['calendar_reviewed'] is False for x in rows)
    assert 'outside_catalog_observed_span' in rows[0]['reasons']


@pytest.mark.parametrize('problem',['duplicate_plan','duplicate_resolver','holdout','overlap','wrong_primary','approval','excluded','out_of_range'])
def test_metadata_reconciliation_failures(store,problem):
    p, r, c=metadata(store)
    if problem=='duplicate_plan':p['shards'][0]['sessions']*=2
    elif problem=='duplicate_resolver':r['instruments']['ES']['sessions']*=2
    elif problem=='holdout':p['spec']['requests'][0]['end']='2026-10-01'
    elif problem=='overlap':p['spec']['requests']*=2
    elif problem=='wrong_primary':p['shards'][0]['sessions'][0]['file']='other.parquet'
    elif problem=='approval':r['instruments']['ES']['sessions'][0]['approved']=False
    elif problem=='excluded':c['instruments']['ES']['ineligible_low_volume']['ranges']=['2026-01-05']
    elif problem=='out_of_range':p['spec']['requests'][0].update(start='2026-01-06',end='2026-01-06')
    with pytest.raises(AggregateAuditError):build_daily_inventory(plan=p,resolver=r,catalog=c)


def test_rejected_not_zero_or_missing(store):
    p,r,c=metadata(store);r['instruments']['ES']['sessions'][0].update(approved=False,reason='liquidez_baja');p['shards'][0]['sessions']=[]
    row=build_daily_inventory(plan=p,resolver=r,catalog=c)[0]
    assert row['state']=='REJECTED_BY_RESOLVER' and 'liquidez_baja' in row['reasons']


@pytest.mark.parametrize('day,minutes',[('2026-03-08',1380),('2026-11-01',1500),('2026-01-05',1440)])
def test_nominal_dst_label_not_exchange_calendar(day,minutes):
    a,b=nominal_bounds(day);assert (b-a)//(60*10**9)==minutes


def test_run_encoding_no_zeros_or_false_closures():
    runs=absent_runs([False,False,True,False],100)
    assert [(x['start_utc_ns'],x['end_utc_ns']) for x in runs]==[(100,120000000100),(180000000100,240000000100)]
    assert all(x['classification']=='UNOBSERVED_ACTIVITY_UNKNOWN' for x in runs)
    assert absent_runs([],100)==[]


def coverage_args(store):
    p,r,c=metadata(store);out,resolver,_=store;cp=out/'catalog.json';cp.write_text(json.dumps(c))
    return dict(store=out,resolver=resolver,catalog=cp,expected_manifest_sha256=digest(out/'manifest.json'),
                expected_resolver_sha256=digest(resolver),expected_catalog_sha256=digest(cp),batch_size=2)


def test_real_projection_missing_minutes_remain_unknown(store,monkeypatch):
    args=coverage_args(store)
    calls=m.spy_payload(monkeypatch)
    summary,daily=audit_coverage(**args)
    assert calls and summary['research_allowed'] is False
    assert summary['files'][0]['payload_columns']==['session_date','contract','bucket_utc_ns']
    assert summary['files'][0]['price_payload_columns_read']==0
    assert daily[0]['minutes_with_observations']>0 and daily[0]['minutes_without_observations']>0
    assert daily[0]['unobserved_intervals'][0]['classification']=='UNOBSERVED_ACTIVITY_UNKNOWN'


@pytest.mark.parametrize('failure',['manifest_pin','resolver_pin','catalog_pin','holdout_last','holdout_bucket','no_stats','null_identity'])
def test_coverage_rejects_before_payload(store,monkeypatch,failure):
    args=coverage_args(store);out=args['store'];path=out/'ES__1s.parquet'
    if failure.endswith('_pin'):args['expected_'+failure[:-4]+'_sha256']='0'*64
    else:
        t=pd.read_parquet(path);kw={}
        if failure=='holdout_last':t.loc[0,'last_ts_utc_ns']=pd.Timestamp('2026-09-30 22:00',tz='UTC').value
        elif failure=='holdout_bucket':t.loc[0,'bucket_utc_ns']=pd.Timestamp('2026-09-30 22:00',tz='UTC').value
        elif failure=='no_stats':kw['write_statistics']=False
        else:t.loc[0,'contract']=None
        t.to_parquet(path,index=False,**kw);m.repin(out,path.name);args['expected_manifest_sha256']=digest(out/'manifest.json')
    calls=m.spy_payload(monkeypatch)
    with pytest.raises(AggregateAuditError):audit_coverage(**args)
    assert calls==[]


def reviewed():
    return {'coverage_review':{'schema':'edgelab_reviewed_daily_coverage_v1',
        'calendar_sha256':'a'*64,'interval_evidence_sha256':'b'*64,'dates':[
        {'instrument':'ES','date':'2026-01-04','status':'VERIFIED_SCHEDULED_CLOSED','evidence_sha256':'c'*64},
        {'instrument':'ES','date':'2026-01-05','status':'VERIFIED_OPEN_COMPLETE','evidence_sha256':'d'*64,'interval_review':'PASS','unresolved_intervals':0}]}}


def test_explicit_closed_day_not_silent_missing_session():
    c=reviewed();assert require_requested_coverage(certificate=c,instrument='ES',start='2026-01-04',end='2026-01-05',materialized_dates={'2026-01-05'})==['2026-01-04','2026-01-05']


@pytest.mark.parametrize('failure',['no_review','missing_day','duplicate','unknown','missing_open','closure_conflict','unknown_intervals','bool_count','missing_ref','calendar_ref','wrong_root'])
def test_requested_coverage_fail_closed(failure):
    c=reviewed();rows=c['coverage_review']['dates'];dates={'2026-01-05'}
    if failure=='no_review':c={}
    elif failure=='missing_day':rows.pop(0)
    elif failure=='duplicate':rows.append(copy.deepcopy(rows[0]))
    elif failure=='unknown':rows[0]['status']='UNKNOWN'
    elif failure=='missing_open':dates=set()
    elif failure=='closure_conflict':dates.add('2026-01-04')
    elif failure=='unknown_intervals':rows[1]['unresolved_intervals']=1
    elif failure=='bool_count':rows[1]['unresolved_intervals']=False
    elif failure=='missing_ref':rows[0].pop('evidence_sha256')
    elif failure=='calendar_ref':c['coverage_review']['calendar_sha256']='invalid'
    elif failure=='wrong_root':rows[0]['instrument']='NQ'
    with pytest.raises(DataEligibilityError):require_requested_coverage(certificate=c,instrument='ES',start='2026-01-04',end='2026-01-05',materialized_dates=dates)


def test_missing_window_review_before_price_hash_or_deserialization(store,monkeypatch):
    args=m.research_args(store);m.future_fixture(store,args);args['certificate'].pop('coverage_review');args['expected_certificate_sha256']=seal(args['certificate'])
    import edgelab.kaggle.research_access as ra
    real=ra.digest
    def no_price(path):
        assert not str(path).endswith('.parquet'), 'price bytes hashed before coverage guard'
        return real(path)
    monkeypatch.setattr(ra,'digest',no_price)
    monkeypatch.setattr(pd,'read_parquet',lambda *a,**k:pytest.fail('price deserialized'))
    with pytest.raises(DataEligibilityError,match='daily coverage'):load_research_bars(start='2026-01-05',end='2026-01-05',seconds=1,**args)
