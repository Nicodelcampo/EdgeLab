"""Invented canonical ticks; no dedup by price/time and no upstream claims."""
import pandas as pd
import pyarrow.parquet as pq
import pytest
from edgelab.kaggle.aggregate_audit import AggregateAuditError,digest
from edgelab.kaggle.raw_tick_audit import audit_canonical_tick_file


@pytest.fixture
def raw(tmp_path):
    ns=pd.Timestamp('2026-06-01 12:00',tz='UTC').value
    t=pd.DataFrame({'ts_utc_ns':[ns,ns,ns+100,ns+200,ns+300],
        'ts_local_ns':[ns,ns,ns+100,ns+200,ns+300],
        'sequence':[0,1,2,3,4],'price_ticks':[100]*5,'bid_ticks':[99]*5,'ask_ticks':[101]*5,
        'volume':[1]*5,'aggressor':['buy','sell','buy','sell','unclassified'],
        'tick_type':['trade']*5,'instrument':['ES']*5,'contract':['ES 09-26']*5,
        'source_file':['a','a','b','b','a'],'source_row':[0,1,0,1,2]})
    p=tmp_path/'ticks.parquet';t.to_parquet(p,index=False,row_group_size=2)
    return p


def args(path):
    return dict(path=path,expected_sha256=digest(path),expected_bytes=path.stat().st_size,
                expected_rows=5,instrument='ES',contract='ES 09-26',batch_size=2)


def test_exact_identity_not_timestamp_dedup(raw):
    r,t=audit_canonical_tick_file(**args(raw))
    assert r['status']=='PASS_RAW_STRUCTURE_ONLY'
    assert r['warnings']['repeated_timestamps_legitimate']==1
    assert r['errors']['duplicate_source_identity']==0
    assert t['2026-06-01']=={'trades':5,'volume':5}
    assert r['research_allowed'] is False and r['exchange_continuity_verified'] is False
    assert r['timezone_independently_verified'] is False


@pytest.mark.parametrize('field,value,error',[
    ('source_row',1,'duplicate_source_identity'),('sequence',1,'nonincreasing_local_sequence'),
    ('bid_ticks',102,'crossed_book'),('price_ticks',0,'nonpositive_price_or_quote'),
    ('volume',0,'nonpositive_trade_volume'),('aggressor','invented','invalid_aggressor')])
def test_corruption_is_reported_not_repaired(raw,field,value,error):
    t=pd.read_parquet(raw);t.loc[4,field]=value;t.to_parquet(raw,index=False,row_group_size=2)
    before=raw.read_bytes();r,_=audit_canonical_tick_file(**args(raw))
    assert r['status']=='FAIL_RAW_STRUCTURE' and r['errors'][error]>0
    assert raw.read_bytes()==before


@pytest.mark.parametrize('issue',['holdout','missing_stats','null_time','mixed_contract','float_price','bad_sha','bad_rows'])
def test_footer_rejects_before_tick_payload(raw,monkeypatch,issue):
    t=pd.read_parquet(raw);kw={}
    if issue=='holdout':t.loc[4,'ts_utc_ns']=pd.Timestamp('2026-09-30 22:00',tz='UTC').value
    elif issue=='missing_stats':kw['write_statistics']=False
    elif issue=='null_time':t.loc[4,'ts_utc_ns']=None
    elif issue=='mixed_contract':t.loc[4,'contract']='NQ 09-26'
    elif issue=='float_price':t['price_ticks']=t.price_ticks.astype(float)
    t.to_parquet(raw,index=False,row_group_size=2,**kw);a=args(raw)
    if issue=='bad_sha':a['expected_sha256']='a'*64
    elif issue=='bad_rows':a['expected_rows']=6
    real=pq.ParquetFile;calls=[]
    class Spy:
        def __init__(self,*a,**k):self.p=real(*a,**k)
        def __getattr__(self,k):return getattr(self.p,k)
        def iter_batches(self,*a,**k):calls.append('payload');yield from self.p.iter_batches(*a,**k)
    monkeypatch.setattr(pq,'ParquetFile',Spy)
    with pytest.raises(AggregateAuditError):audit_canonical_tick_file(**a)
    assert calls==[]


def test_identity_bitmap_handles_nonadjacent_collision(raw):
    t=pd.read_parquet(raw);t.loc[4,'source_row']=0;t.to_parquet(raw,index=False,row_group_size=2)
    r,_=audit_canonical_tick_file(**args(raw));assert r['errors']['duplicate_source_identity']==1


def test_timestamp_backward_not_sorted_away(raw):
    t=pd.read_parquet(raw);t.loc[4,'ts_utc_ns']=t.loc[0,'ts_utc_ns']-100;t.to_parquet(raw,index=False,row_group_size=2)
    r,_=audit_canonical_tick_file(**args(raw));assert r['errors']['backward_timestamps']==1
